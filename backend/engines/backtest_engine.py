from typing import List, Dict, Optional, Tuple
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from engines.indicators import compute_all_indicators
from engines.signal_engine import SignalEngine
from engines.risk_manager import RiskManager
from config.settings import settings


class BacktestEngine:
    def __init__(self, slippage_pct: float = 0.001, fee_pct: float = 0.0004,
                 max_hold_15m: int = 64,
                 risk_per_trade: Optional[float] = 0.05,
                 dd_throttle_level: Optional[float] = 0.05,
                 dd_throttle_factor: float = 0.4,
                 daily_loss_limit: Optional[float] = None,
                 require_pa_confluence: bool = True,
                 require_liquidity_sweep: bool = True,
                 require_bos: bool = True):
        self.signal_engine = SignalEngine()
        # Entry filters (smart-money concepts).
        self.signal_engine.require_pa_confluence = require_pa_confluence
        self.signal_engine.require_liquidity_sweep = require_liquidity_sweep
        self.signal_engine.require_bos = require_bos
        self.results = {}
        self.slippage_pct = slippage_pct
        self.fee_pct = fee_pct
        # Max bars (15M) a trade is held before a time-based exit (~16h).
        self.max_hold_15m = max_hold_15m
        # --- Risk / drawdown controls (all optional, off by default) ---
        # Base fraction of equity risked per trade (falls back to settings).
        self.risk_per_trade = risk_per_trade
        # When equity is more than `dd_throttle_level` below its peak, scale
        # the per-trade risk by `dd_throttle_factor` (de-risk while underwater).
        self.dd_throttle_level = dd_throttle_level
        self.dd_throttle_factor = dd_throttle_factor
        # Pause new entries for the rest of a day once that day's realized loss
        # exceeds `daily_loss_limit` x (capital at the day's start).
        self.daily_loss_limit = daily_loss_limit

    def run_backtest(self, df_4h: pd.DataFrame, df_15m: pd.DataFrame,
                     initial_capital: float = 10000.0,
                     trade_start_ts: Optional[float] = None) -> Dict:
        """Walk-forward backtest. If `trade_start_ts` (ms) is given, all prior
        bars are used only for indicator warmup and trading begins at that
        timestamp with `initial_capital` intact."""
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
        # Align the two timeframes by timestamp (a 4H bar spans 16 x 15M bars).
        ts_15m = df_15m["timestamp"].values if "timestamp" in df_15m.columns else np.arange(max_idx_15m)
        cooldown_until_ts = -1  # block new entries until the current trade has closed

        base_risk = self.risk_per_trade if self.risk_per_trade is not None else settings.risk_per_trade
        peak_capital = capital
        cur_day = None            # simulated calendar day (ms // 1 day)
        day_start_capital = capital
        day_realized = 0.0

        for i in range(min_bars, max_idx_4h):
            chunk_4h = df_4h.iloc[:i + 1]
            bar_ts_4h = df_4h.iloc[i]["timestamp"] if "timestamp" in df_4h.columns else i
            # Index of the last 15M bar that has closed by this 4H bar's close.
            e15 = int(np.searchsorted(ts_15m, bar_ts_4h, side="right")) - 1
            chunk_15m = df_15m.iloc[:e15 + 1]

            if len(chunk_4h) < min_bars or len(chunk_15m) < min_bars or e15 < min_bars:
                equity_curve.append(capital)
                continue

            if trade_start_ts is not None and bar_ts_4h < trade_start_ts:
                equity_curve.append(capital)  # warmup region: no trading
                continue

            if bar_ts_4h < cooldown_until_ts:  # still inside a live trade
                equity_curve.append(capital)
                continue

            # Roll the simulated trading day for the daily-loss circuit breaker.
            day = int(bar_ts_4h) // (86400 * 1000)
            if day != cur_day:
                cur_day = day
                day_start_capital = capital
                day_realized = 0.0
            if (self.daily_loss_limit is not None
                    and day_realized <= -self.daily_loss_limit * day_start_capital):
                equity_curve.append(capital)
                continue

            entry_bar_15m_start = e15

            long_signal = self.signal_engine.evaluate_long_setup(chunk_4h, chunk_15m)
            short_signal = self.signal_engine.evaluate_short_setup(chunk_4h, chunk_15m)
            signal = long_signal or short_signal
            if not signal:
                equity_curve.append(capital)
                continue

            entry = signal["entry_price"]
            sl = signal["stop_loss"]
            tp1 = signal.get("take_profit_1", entry)
            tp2 = signal.get("take_profit_2", entry)
            direction = signal["direction"]

            entry_px = entry * (1 + self.slippage_pct if direction == "LONG" else 1 - self.slippage_pct)
            stop_px = sl * (1 - self.slippage_pct if direction == "LONG" else 1 + self.slippage_pct)

            # Effective risk: throttle down while in drawdown.
            eff_risk = base_risk
            if self.dd_throttle_level is not None and peak_capital > 0:
                if (peak_capital - capital) / peak_capital > self.dd_throttle_level:
                    eff_risk *= self.dd_throttle_factor

            pos_data = risk_mgr.calculate_position_size(entry_px, stop_px, eff_risk)
            if pos_data["position_size"] <= 0:
                equity_curve.append(capital)
                continue

            # Entry fee (one leg).
            capital -= self._calc_fees(entry_px, pos_data["position_size"], 1)

            open_trade = {
                "entry": entry_px,
                "stop_loss": stop_px,
                "take_profit_1": tp1,
                "take_profit_2": tp2,
                "take_profit_3": signal.get("take_profit_3"),
                "direction": direction,
                "position_size": pos_data["position_size"],
                "dollar_risk": pos_data["dollar_risk"],
                "entry_bar_15m": entry_bar_15m_start,
                "entry_time": chunk_4h.iloc[-1].get("timestamp", datetime.utcnow()),
                "confidence_score": signal.get("confidence_score", 0),
                "remaining_size": pos_data["position_size"],
                "partial_exits": [],
                "breakeven_activated": False,
                "trailing_activated": False,
            }

            month_key = self._get_month_key(chunk_4h.iloc[i])
            trade_pnl = 0.0
            closed = False

            # Simulate the trade forward through 15M bars (starting the bar after entry).
            end_j = min(entry_bar_15m_start + 1 + self.max_hold_15m, max_idx_15m)
            for j in range(entry_bar_15m_start + 1, end_j):
                bar = df_15m.iloc[j]
                high = bar["high"]
                low = bar["low"]
                hit_stop = low <= open_trade["stop_loss"] if direction == "LONG" else high >= open_trade["stop_loss"]
                hit_tp1 = high >= tp1 if direction == "LONG" else low <= tp1
                hit_tp2 = high >= tp2 if direction == "LONG" else low <= tp2

                # Stop (or break-even) exit closes ALL remaining size first.
                if hit_stop:
                    sz = open_trade["remaining_size"]
                    trade_pnl += self._calc_pnl(open_trade["entry"], open_trade["stop_loss"], direction, sz) \
                        - self._calc_fees(open_trade["stop_loss"], sz, 1)
                    open_trade["remaining_size"] = 0
                    open_trade["exit_price"] = open_trade["stop_loss"]
                    open_trade["holding_bars"] = j - entry_bar_15m_start
                    closed = True
                    break

                # First touch of TP1: bank 50% and move the stop to break-even.
                if not open_trade["breakeven_activated"] and hit_tp1:
                    sz = open_trade["remaining_size"] * 0.5
                    pnl = self._calc_pnl(open_trade["entry"], tp1, direction, sz) - self._calc_fees(tp1, sz, 1)
                    trade_pnl += pnl
                    open_trade["remaining_size"] -= sz
                    open_trade["partial_exits"].append({"tp": 1, "price": tp1, "size": sz, "pnl": pnl})
                    open_trade["stop_loss"] = open_trade["entry"]
                    open_trade["breakeven_activated"] = True

                # TP2 (full 3R target) closes the remainder.
                if open_trade["breakeven_activated"] and open_trade["remaining_size"] > 0 and hit_tp2:
                    sz = open_trade["remaining_size"]
                    pnl = self._calc_pnl(open_trade["entry"], tp2, direction, sz) - self._calc_fees(tp2, sz, 1)
                    trade_pnl += pnl
                    open_trade["remaining_size"] = 0
                    open_trade["partial_exits"].append({"tp": 2, "price": tp2, "size": sz, "pnl": pnl})
                    open_trade["exit_price"] = tp2
                    open_trade["holding_bars"] = j - entry_bar_15m_start
                    closed = True
                    break

            # Time-based exit for any size still open at the end of the window.
            if not closed:
                last_idx = min(entry_bar_15m_start + self.max_hold_15m, max_idx_15m - 1)
                last_close = df_15m.iloc[last_idx]["close"]
                sz = open_trade["remaining_size"]
                trade_pnl += self._calc_pnl(open_trade["entry"], last_close, direction, sz) \
                    - self._calc_fees(last_close, sz, 1)
                open_trade["remaining_size"] = 0
                open_trade["exit_price"] = last_close
                open_trade["holding_bars"] = last_idx - entry_bar_15m_start

            capital += trade_pnl
            risk_mgr.account_balance = capital
            equity_curve.append(capital)
            open_trade["pnl"] = trade_pnl
            trades.append(open_trade)
            monthly_pnl[month_key] = monthly_pnl.get(month_key, 0) + trade_pnl
            peak_capital = max(peak_capital, capital)
            day_realized += trade_pnl

            # Block new entries until this trade's exit bar (no overlapping positions).
            exit_idx = min(entry_bar_15m_start + open_trade["holding_bars"], len(ts_15m) - 1)
            cooldown_until_ts = ts_15m[exit_idx]

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
