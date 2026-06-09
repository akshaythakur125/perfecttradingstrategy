from typing import List, Dict, Optional
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from engines.indicators import compute_all_indicators
from engines.signal_engine import SignalEngine
from engines.risk_manager import RiskManager


class BacktestEngine:
    def __init__(self, slippage_pct: float = 0.001, fee_pct: float = 0.0004):
        self.signal_engine = SignalEngine()
        self.results = {}
        self.slippage_pct = slippage_pct
        self.fee_pct = fee_pct

    def run_backtest(self, df_4h: pd.DataFrame, df_15m: pd.DataFrame,
                     initial_capital: float = 10000.0) -> Dict:
        df_4h = compute_all_indicators(df_4h)
        df_15m = compute_all_indicators(df_15m)

        if "timestamp" in df_4h.columns:
            df_4h = df_4h.set_index("timestamp", drop=False)
        if "timestamp" in df_15m.columns:
            df_15m = df_15m.set_index("timestamp", drop=False)

        capital = initial_capital
        equity_curve = [capital]
        trades = []
        monthly_pnl = {}
        open_trade = None
        risk_mgr = RiskManager(capital)

        min_bars = 50
        max_idx_4h = len(df_4h)
        max_idx_15m = len(df_15m)

        for i in range(min_bars, max_idx_4h):
            if open_trade is not None:
                exit_data = self._check_exit(
                    df_15m, open_trade, open_trade["entry_bar_15m"]
                )
                if exit_data:
                    exit_price, exit_time, holding_bars = exit_data
                    pnl_raw = self._calc_pnl(
                        open_trade["entry"], exit_price,
                        open_trade["direction"], open_trade["position_size"]
                    )
                    fees = self._calc_fees(open_trade["entry"], open_trade["position_size"], 2)
                    pnl = pnl_raw - fees

                    capital += pnl
                    equity_curve.append(capital)
                    risk_mgr.account_balance = capital
                    open_trade["pnl"] = pnl
                    open_trade["exit_price"] = exit_price
                    open_trade["holding_bars"] = holding_bars
                    trades.append(open_trade)

                    month_key = df_4h.iloc[i].get("timestamp", datetime.utcnow())
                    if isinstance(month_key, (int, float)):
                        month_key = datetime.fromtimestamp(month_key / 1000)
                    month_str = month_key.strftime("%Y-%m")
                    monthly_pnl[month_str] = monthly_pnl.get(month_str, 0) + pnl

                    open_trade = None
                    continue
                else:
                    equity_curve.append(capital)
                    continue

            chunk_4h = df_4h.iloc[:i + 1]
            chunk_15m = df_15m.iloc[:i * 4 + 1] if i * 4 + 1 <= max_idx_15m else df_15m

            if len(chunk_4h) < min_bars or len(chunk_15m) < min_bars:
                equity_curve.append(capital)
                continue

            long_signal = self.signal_engine.evaluate_long_setup(chunk_4h, chunk_15m)
            short_signal = self.signal_engine.evaluate_short_setup(chunk_4h, chunk_15m)

            signal = long_signal or short_signal
            if not signal:
                equity_curve.append(capital)
                continue

            entry = signal["entry_price"]
            sl = signal["stop_loss"]
            tp1 = signal.get("take_profit_1", entry)
            direction = signal["direction"]

            entry_with_slippage = entry * (1 + self.slippage_pct if direction == "LONG" else 1 - self.slippage_pct)
            sl_with_slippage = sl * (1 - self.slippage_pct if direction == "LONG" else 1 + self.slippage_pct)

            pos_data = risk_mgr.calculate_position_size(entry_with_slippage, sl_with_slippage)
            if pos_data["position_size"] <= 0:
                equity_curve.append(capital)
                continue

            fees = self._calc_fees(entry_with_slippage, pos_data["position_size"], 1)
            capital -= fees

            open_trade = {
                "entry": entry_with_slippage,
                "stop_loss": sl_with_slippage,
                "take_profit_1": tp1,
                "take_profit_2": signal.get("take_profit_2"),
                "take_profit_3": signal.get("take_profit_3"),
                "direction": direction,
                "position_size": pos_data["position_size"],
                "dollar_risk": pos_data["dollar_risk"],
                "entry_bar_15m": i * 4,
                "entry_time": df_4h.iloc[i].get("timestamp", datetime.utcnow()),
                "confidence_score": signal.get("confidence_score", 0),
            }

        if open_trade is not None:
            last_idx = min(open_trade["entry_bar_15m"] + 96, len(df_15m) - 1)
            last_close = df_15m.iloc[last_idx]["close"]
            pnl_raw = self._calc_pnl(
                open_trade["entry"], last_close,
                open_trade["direction"], open_trade["position_size"]
            )
            fees = self._calc_fees(open_trade["entry"], open_trade["position_size"], 2)
            pnl = pnl_raw - fees
            capital += pnl
            equity_curve.append(capital)
            open_trade["pnl"] = pnl
            open_trade["exit_price"] = last_close
            open_trade["holding_bars"] = 96
            trades.append(open_trade)

        metrics = self._calculate_metrics(
            trades, initial_capital, capital, equity_curve, monthly_pnl,
            df_4h.iloc[0].get("timestamp"), df_4h.iloc[-1].get("timestamp")
        )
        return metrics

    def _check_exit(self, df: pd.DataFrame, trade: Dict, start_idx: int) -> Optional[tuple]:
        for i in range(start_idx, min(start_idx + 96, len(df))):
            high = df.iloc[i]["high"]
            low = df.iloc[i]["low"]

            if trade["direction"] == "LONG":
                if low <= trade["stop_loss"]:
                    return trade["stop_loss"], df.iloc[i].get("timestamp"), (i - start_idx)
                if high >= trade["take_profit_1"]:
                    tp_exit = trade["take_profit_1"]
                    return tp_exit, df.iloc[i].get("timestamp"), (i - start_idx)
            else:
                if high >= trade["stop_loss"]:
                    return trade["stop_loss"], df.iloc[i].get("timestamp"), (i - start_idx)
                if low <= trade["take_profit_1"]:
                    tp_exit = trade["take_profit_1"]
                    return tp_exit, df.iloc[i].get("timestamp"), (i - start_idx)
        return None

    def _calc_pnl(self, entry: float, exit_price: float, direction: str, size: float) -> float:
        if direction == "LONG":
            return (exit_price - entry) * size
        return (entry - exit_price) * size

    def _calc_fees(self, price: float, size: float, legs: int = 2) -> float:
        return price * size * self.fee_pct * legs

    def _calculate_metrics(self, trades: List[Dict], initial: float, final: float,
                           equity: List[float], monthly: Dict,
                           start_ts, end_ts) -> Dict:
        if not trades:
            return {
                "total_trades": 0, "winning_trades": 0, "losing_trades": 0,
                "win_rate": 0, "profit_factor": 0, "sharpe_ratio": 0,
                "sortino_ratio": 0, "max_drawdown": 0, "cagr": 0,
                "average_rr": 0, "average_holding_time": 0,
                "total_pnl": 0, "initial_capital": initial, "final_capital": initial,
                "equity_curve": equity, "monthly_performance": monthly, "trades": trades,
            }

        winning = [t for t in trades if t.get("pnl", 0) > 0]
        losing = [t for t in trades if t.get("pnl", 0) <= 0]
        win_rate = len(winning) / len(trades) if trades else 0

        total_gain = sum(t.get("pnl", 0) for t in winning) if winning else 0
        total_loss = abs(sum(t.get("pnl", 0) for t in losing)) if losing else 1
        profit_factor = total_gain / total_loss if total_loss > 0 else float("inf")

        returns = np.diff(equity) / np.array(equity[:-1])
        returns = returns[~np.isnan(returns) & ~np.isinf(returns)]
        sharpe = 0
        sortino = 0
        if len(returns) > 1 and np.std(returns) > 1e-10:
            sharpe = np.mean(returns) / np.std(returns) * np.sqrt(365)
            downside = returns[returns < 0]
            if len(downside) > 0 and np.std(downside) > 1e-10:
                sortino = np.mean(returns) / np.std(downside) * np.sqrt(365)

        peak = np.maximum.accumulate(equity)
        drawdown = (peak - equity) / peak
        max_dd = np.max(drawdown) if len(drawdown) > 0 else 0

        if isinstance(start_ts, (int, float)):
            start_dt = datetime.fromtimestamp(start_ts / 1000)
        else:
            start_dt = start_ts or datetime.utcnow()

        if isinstance(end_ts, (int, float)):
            end_dt = datetime.fromtimestamp(end_ts / 1000)
        else:
            end_dt = end_ts or datetime.utcnow()

        years = max((end_dt - start_dt).days / 365.25, 1 / 365.25)
        cagr = ((final / initial) ** (1 / years) - 1) * 100 if initial > 0 else 0

        avg_rr_per_trade = np.mean([
            abs(t.get("pnl", 0)) / max(t.get("dollar_risk", 1), 1)
            for t in trades if t.get("dollar_risk", 0) > 0
        ]) if trades else 0

        avg_hold = np.mean([t.get("holding_bars", 0) for t in trades]) * 15 / 60

        return {
            "total_trades": len(trades),
            "winning_trades": len(winning),
            "losing_trades": len(losing),
            "win_rate": round(win_rate * 100, 2),
            "profit_factor": round(profit_factor, 2),
            "sharpe_ratio": round(sharpe, 2),
            "sortino_ratio": round(sortino, 2),
            "max_drawdown": round(max_dd * 100, 2),
            "cagr": round(cagr, 2),
            "average_rr": round(avg_rr_per_trade, 2),
            "average_holding_time": round(avg_hold, 2),
            "total_pnl": round(final - initial, 2),
            "initial_capital": initial,
            "final_capital": round(final, 2),
            "equity_curve": [round(e, 2) for e in equity],
            "monthly_performance": {k: round(v, 2) for k, v in monthly.items()},
            "trades": trades,
        }
