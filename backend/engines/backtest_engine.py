from typing import List, Dict, Optional, Tuple
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
        risk_mgr = RiskManager(capital)

        min_bars = 50
        max_idx_4h = len(df_4h)
        max_idx_15m = len(df_15m)

        for i in range(min_bars, max_idx_4h):
            chunk_4h = df_4h.iloc[:i + 1]
            chunk_15m = df_15m.iloc[:i * 4 + 1] if i * 4 + 1 <= max_idx_15m else df_15m

            if len(chunk_4h) < min_bars or len(chunk_15m) < min_bars:
                equity_curve.append(capital)
                continue

            open_trade = None
            entry_bar_15m_start = i * 4

            long_signal = self.signal_engine.evaluate_long_setup(chunk_4h, chunk_15m)
            short_signal = self.signal_engine.evaluate_short_setup(chunk_4h, chunk_15m)
            signal = long_signal or short_signal
            if not signal:
                equity_curve.append(capital)
                continue

            entry = signal["entry_price"]
            sl = signal["stop_loss"]
            tp1 = signal.get("take_profit_1", entry)
            tp2 = signal.get("take_profit_2")
            tp3 = signal.get("take_profit_3")
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
                "take_profit_2": tp2,
                "take_profit_3": tp3,
                "direction": direction,
                "position_size": pos_data["position_size"],
                "dollar_risk": pos_data["dollar_risk"],
                "entry_bar_15m": entry_bar_15m_start,
                "entry_time": chunk_4h.iloc[-1].get("timestamp", datetime.utcnow()),
                "confidence_score": signal.get("confidence_score", 0),
                "atr_at_entry": chunk_15m.iloc[-1]["atr"] if len(chunk_15m) > 0 else 0,
                "remaining_size": pos_data["position_size"],
                "partial_exits": [],
                "breakeven_activated": False,
                "trailing_activated": False,
                "highest_price": entry_with_slippage,
                "lowest_price": entry_with_slippage,
            }

            # Simulate this trade through 15m bars
            for j in range(entry_bar_15m_start, min(entry_bar_15m_start + 96, max_idx_15m)):
                if open_trade["remaining_size"] <= 0:
                    break

                bar = df_15m.iloc[j]
                high = bar["high"]
                low = bar["low"]
                close = bar["close"]

                if direction == "LONG":
                    open_trade["highest_price"] = max(open_trade["highest_price"], high)
                    if open_trade["trailing_activated"]:
                        atr_val = bar["atr"] if "atr" in bar else open_trade.get("atr_at_entry", 0)
                        trail_stop = open_trade["highest_price"] - (atr_val * 1.5)
                        open_trade["stop_loss"] = max(open_trade["stop_loss"], trail_stop)

                    # Check stop loss
                    if low <= open_trade["stop_loss"]:
                        exit_price = open_trade["stop_loss"]
                        pnl_raw = self._calc_pnl(open_trade["entry"], exit_price, direction, open_trade["remaining_size"])
                        fees_exit = self._calc_fees(exit_price, open_trade["remaining_size"], 1)
                        pnl = pnl_raw - fees_exit
                        capital += pnl
                        equity_curve.append(capital)
                        risk_mgr.account_balance = capital
                        open_trade["pnl"] = pnl
                        open_trade["exit_price"] = exit_price
                        open_trade["holding_bars"] = j - entry_bar_15m_start
                        open_trade["remaining_size"] = 0
                        trades.append(open_trade)
                        month_key = self._get_month_key(chunk_4h.iloc[i])
                        monthly_pnl[month_key] = monthly_pnl.get(month_key, 0) + pnl
                        break

                    # Check TP1 - exit 50%
                    if high >= open_trade["take_profit_1"]:
                        exit_price = open_trade["take_profit_1"]
                        exit_size = open_trade["remaining_size"] * 0.5
                        pnl_raw = self._calc_pnl(open_trade["entry"], exit_price, direction, exit_size)
                        fees_exit = self._calc_fees(exit_price, exit_size, 1)
                        pnl = pnl_raw - fees_exit
                        capital += pnl
                        risk_mgr.account_balance = capital
                        open_trade["partial_exits"].append({"tp": 1, "price": exit_price, "size": exit_size, "pnl": pnl})
                        open_trade["remaining_size"] -= exit_size
                        month_key = self._get_month_key(chunk_4h.iloc[i])
                        monthly_pnl[month_key] = monthly_pnl.get(month_key, 0) + pnl

                        if not open_trade["breakeven_activated"]:
                            open_trade["stop_loss"] = open_trade["entry"]
                            open_trade["breakeven_activated"] = True

                        if open_trade["take_profit_2"] and high >= open_trade["take_profit_2"]:
                            exit_size2 = open_trade["remaining_size"] * 0.6
                            pnl_raw2 = self._calc_pnl(open_trade["entry"], open_trade["take_profit_2"], direction, exit_size2)
                            fees_exit2 = self._calc_fees(open_trade["take_profit_2"], exit_size2, 1)
                            pnl2 = pnl_raw2 - fees_exit2
                            capital += pnl2
                            risk_mgr.account_balance = capital
                            open_trade["partial_exits"].append({"tp": 2, "price": open_trade["take_profit_2"], "size": exit_size2, "pnl": pnl2})
                            open_trade["remaining_size"] -= exit_size2
                            monthly_pnl[month_key] = monthly_pnl.get(month_key, 0) + pnl2

                            if not open_trade["trailing_activated"]:
                                open_trade["trailing_activated"] = True
                                atr_val = bar["atr"] if "atr" in bar else open_trade.get("atr_at_entry", 0)
                                open_trade["stop_loss"] = open_trade["take_profit_2"] - (atr_val * 2.0)

                            if open_trade["take_profit_3"] and high >= open_trade["take_profit_3"]:
                                exit_size3 = open_trade["remaining_size"]
                                pnl_raw3 = self._calc_pnl(open_trade["entry"], open_trade["take_profit_3"], direction, exit_size3)
                                fees_exit3 = self._calc_fees(open_trade["take_profit_3"], exit_size3, 1)
                                pnl3 = pnl_raw3 - fees_exit3
                                capital += pnl3
                                risk_mgr.account_balance = capital
                                open_trade["partial_exits"].append({"tp": 3, "price": open_trade["take_profit_3"], "size": exit_size3, "pnl": pnl3})
                                open_trade["remaining_size"] = 0
                                monthly_pnl[month_key] = monthly_pnl.get(month_key, 0) + pnl3
                                open_trade["pnl"] = sum(e["pnl"] for e in open_trade["partial_exits"])
                                open_trade["exit_price"] = open_trade["take_profit_3"]
                                open_trade["holding_bars"] = j - entry_bar_15m_start
                                trades.append(open_trade)
                                break

                        if open_trade["remaining_size"] <= 0:
                            open_trade["pnl"] = sum(e["pnl"] for e in open_trade["partial_exits"])
                            open_trade["exit_price"] = open_trade["take_profit_1"]
                            open_trade["holding_bars"] = j - entry_bar_15m_start
                            trades.append(open_trade)
                            break

                else:  # SHORT
                    open_trade["lowest_price"] = min(open_trade["lowest_price"], low)
                    if open_trade["trailing_activated"]:
                        atr_val = bar["atr"] if "atr" in bar else open_trade.get("atr_at_entry", 0)
                        trail_stop = open_trade["lowest_price"] + (atr_val * 1.5)
                        open_trade["stop_loss"] = min(open_trade["stop_loss"], trail_stop)

                    if high >= open_trade["stop_loss"]:
                        exit_price = open_trade["stop_loss"]
                        pnl_raw = self._calc_pnl(open_trade["entry"], exit_price, direction, open_trade["remaining_size"])
                        fees_exit = self._calc_fees(exit_price, open_trade["remaining_size"], 1)
                        pnl = pnl_raw - fees_exit
                        capital += pnl
                        equity_curve.append(capital)
                        risk_mgr.account_balance = capital
                        open_trade["pnl"] = pnl
                        open_trade["exit_price"] = exit_price
                        open_trade["holding_bars"] = j - entry_bar_15m_start
                        open_trade["remaining_size"] = 0
                        trades.append(open_trade)
                        month_key = self._get_month_key(chunk_4h.iloc[i])
                        monthly_pnl[month_key] = monthly_pnl.get(month_key, 0) + pnl
                        break

                    if low <= open_trade["take_profit_1"]:
                        exit_price = open_trade["take_profit_1"]
                        exit_size = open_trade["remaining_size"] * 0.5
                        pnl_raw = self._calc_pnl(open_trade["entry"], exit_price, direction, exit_size)
                        fees_exit = self._calc_fees(exit_price, exit_size, 1)
                        pnl = pnl_raw - fees_exit
                        capital += pnl
                        risk_mgr.account_balance = capital
                        open_trade["partial_exits"].append({"tp": 1, "price": exit_price, "size": exit_size, "pnl": pnl})
                        open_trade["remaining_size"] -= exit_size
                        month_key = self._get_month_key(chunk_4h.iloc[i])
                        monthly_pnl[month_key] = monthly_pnl.get(month_key, 0) + pnl

                        if not open_trade["breakeven_activated"]:
                            open_trade["stop_loss"] = open_trade["entry"]
                            open_trade["breakeven_activated"] = True

                        if open_trade["take_profit_2"] and low <= open_trade["take_profit_2"]:
                            exit_size2 = open_trade["remaining_size"] * 0.6
                            pnl_raw2 = self._calc_pnl(open_trade["entry"], open_trade["take_profit_2"], direction, exit_size2)
                            fees_exit2 = self._calc_fees(open_trade["take_profit_2"], exit_size2, 1)
                            pnl2 = pnl_raw2 - fees_exit2
                            capital += pnl2
                            risk_mgr.account_balance = capital
                            open_trade["partial_exits"].append({"tp": 2, "price": open_trade["take_profit_2"], "size": exit_size2, "pnl": pnl2})
                            open_trade["remaining_size"] -= exit_size2
                            monthly_pnl[month_key] = monthly_pnl.get(month_key, 0) + pnl2

                            if not open_trade["trailing_activated"]:
                                open_trade["trailing_activated"] = True
                                atr_val = bar["atr"] if "atr" in bar else open_trade.get("atr_at_entry", 0)
                                open_trade["stop_loss"] = open_trade["take_profit_2"] + (atr_val * 2.0)

                            if open_trade["take_profit_3"] and low <= open_trade["take_profit_3"]:
                                exit_size3 = open_trade["remaining_size"]
                                pnl_raw3 = self._calc_pnl(open_trade["entry"], open_trade["take_profit_3"], direction, exit_size3)
                                fees_exit3 = self._calc_fees(open_trade["take_profit_3"], exit_size3, 1)
                                pnl3 = pnl_raw3 - fees_exit3
                                capital += pnl3
                                risk_mgr.account_balance = capital
                                open_trade["partial_exits"].append({"tp": 3, "price": open_trade["take_profit_3"], "size": exit_size3, "pnl": pnl3})
                                open_trade["remaining_size"] = 0
                                monthly_pnl[month_key] = monthly_pnl.get(month_key, 0) + pnl3
                                open_trade["pnl"] = sum(e["pnl"] for e in open_trade["partial_exits"])
                                open_trade["exit_price"] = open_trade["take_profit_3"]
                                open_trade["holding_bars"] = j - entry_bar_15m_start
                                trades.append(open_trade)
                                break

                        if open_trade["remaining_size"] <= 0:
                            open_trade["pnl"] = sum(e["pnl"] for e in open_trade["partial_exits"])
                            open_trade["exit_price"] = open_trade["take_profit_1"]
                            open_trade["holding_bars"] = j - entry_bar_15m_start
                            trades.append(open_trade)
                            break

            if open_trade and open_trade["remaining_size"] > 0:
                last_idx = min(entry_bar_15m_start + 96, max_idx_15m - 1)
                last_close = df_15m.iloc[last_idx]["close"]
                pnl_raw = self._calc_pnl(open_trade["entry"], last_close, direction, open_trade["remaining_size"])
                fees = self._calc_fees(last_close, open_trade["remaining_size"], 1)
                pnl = pnl_raw - fees
                capital += pnl
                equity_curve.append(capital)
                open_trade["pnl"] = (open_trade.get("pnl", 0) or 0) + pnl
                open_trade["exit_price"] = last_close
                open_trade["holding_bars"] = 96
                open_trade["remaining_size"] = 0
                trades.append(open_trade)

        metrics = self._calculate_metrics(
            trades, initial_capital, capital, equity_curve, monthly_pnl,
            df_4h.iloc[0].get("timestamp"), df_4h.iloc[-1].get("timestamp")
        )
        return metrics

    def _get_month_key(self, row) -> str:
        ts = row.get("timestamp", datetime.utcnow())
        if isinstance(ts, (int, float, np.integer, np.floating)):
            ts = datetime.fromtimestamp(float(ts) / 1000)
        elif not isinstance(ts, datetime):
            ts = datetime.utcnow()
        return ts.strftime("%Y-%m")

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
                "total_partial_exits": 0, "breakeven_trades": 0, "trailing_activated_trades": 0,
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

        if isinstance(start_ts, (int, float, np.integer, np.floating)):
            start_dt = datetime.fromtimestamp(float(start_ts) / 1000)
        else:
            start_dt = start_ts if isinstance(start_ts, datetime) else datetime.utcnow()

        if isinstance(end_ts, (int, float, np.integer, np.floating)):
            end_dt = datetime.fromtimestamp(float(end_ts) / 1000)
        else:
            end_dt = end_ts if isinstance(end_ts, datetime) else datetime.utcnow()

        years = max((end_dt - start_dt).days / 365.25, 1 / 365.25)
        cagr = ((final / initial) ** (1 / years) - 1) * 100 if initial > 0 else 0

        avg_rr_per_trade = np.mean([
            abs(t.get("pnl", 0)) / max(t.get("dollar_risk", 1), 1)
            for t in trades if t.get("dollar_risk", 0) > 0
        ]) if trades else 0

        avg_hold = np.mean([t.get("holding_bars", 0) for t in trades]) * 15 / 60

        total_partial_exits = sum(len(t.get("partial_exits", [])) for t in trades)
        breakeven_trades = sum(1 for t in trades if t.get("breakeven_activated", False))
        trailing_trades = sum(1 for t in trades if t.get("trailing_activated", False))

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
            "total_partial_exits": total_partial_exits,
            "breakeven_trades": breakeven_trades,
            "trailing_activated_trades": trailing_trades,
        }
