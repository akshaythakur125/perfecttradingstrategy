#!/usr/bin/env python3
"""
Real market data backtest sourced from a GitHub-hosted dataset.

This is a drop-in alternative to real_data_backtest.py for environments where
the live exchange APIs (Binance/OKX/etc.) are not reachable. It loads real
1-minute OHLCV candles from a local CSV (downloaded from a public GitHub repo),
resamples them into the 4H and 15M timeframes the strategy expects, and runs the
exact same BacktestEngine.

Data source: Bitstamp BTC/USD 1-minute candles
  https://github.com/ff137/bitstamp-btcusd-minute-data
  (real market data; columns: timestamp[sec],open,high,low,close,volume)

Note: open-interest and funding inputs are not present in OHLCV data, so the
signal engine scores them as neutral (as it already does for None) -- this
matches the engine's documented fallback behaviour and accounts for ~15% of the
weighted score; the other ~85% (structure/AOI/volume/RSI/OBV) is driven by the
real candles.
"""
import sys, os, json
from datetime import datetime, timezone
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from engines.backtest_engine import BacktestEngine

# Public GitHub-hosted dataset (real Bitstamp BTC/USD 1-minute candles).
# Used because live exchange APIs are not reachable in restricted/allowlisted
# network environments; raw.githubusercontent.com is generally reachable.
DATA_URL = ("https://raw.githubusercontent.com/ff137/bitstamp-btcusd-minute-data/"
            "main/data/updates/btcusd_bitstamp_1min_latest.csv")

# Mirror the warmup window sizes used by the shipped real_data_backtest.py
WARMUP_CANDLES_4H = 400      # ~66 days of 4H bars, enough for EMA200 warmup
WARMUP_CANDLES_15M = 2000    # ~21 days of 15M bars (the "live" evaluation window)

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data_cache", "btc_1min_latest.csv")
SYMBOL = "BTCUSD"
EXCHANGE = "BITSTAMP"

AGG = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}


def ensure_data(path):
    """Download the 1-minute dataset to `path` if it is not already present."""
    if os.path.exists(path) and os.path.getsize(path) > 1000:
        return
    import urllib.request
    os.makedirs(os.path.dirname(path), exist_ok=True)
    print(f"  Downloading dataset -> {path}")
    req = urllib.request.Request(DATA_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as r, open(path, "wb") as f:
        f.write(r.read())


def load_1min(path):
    ensure_data(path)
    df = pd.read_csv(path)
    # timestamp is in seconds; build a UTC DatetimeIndex for resampling
    df["dt"] = pd.to_datetime(df["timestamp"].astype(np.int64), unit="s", utc=True)
    df = df.set_index("dt").sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return df


def resample(df_1m, rule):
    out = df_1m.resample(rule).agg(AGG).dropna(subset=["open", "high", "low", "close"])
    out = out[out["volume"] >= 0]
    # engine expects a millisecond integer "timestamp" column (like Binance klines)
    out["timestamp"] = (out.index.view("int64") // 1_000_000).astype(np.int64)
    out["symbol"] = SYMBOL
    out["exchange"] = EXCHANGE
    return out.reset_index(drop=True)


def compute_metrics(trades):
    if not trades:
        return {"total_trades": 0, "winning_trades": 0, "losing_trades": 0, "win_rate_pct": 0,
                "profit_factor": 0, "total_pnl": 0, "avg_pnl": 0, "max_win": 0, "max_loss": 0,
                "avg_win": 0, "avg_loss": 0, "expectancy": 0, "max_drawdown_pct": 0,
                "sharpe_ratio": 0, "average_rr": 0}
    pnls = [t.get("pnl", 0) for t in trades]
    total_pnl = sum(pnls)
    winning = [p for p in pnls if p > 0]
    losing = [p for p in pnls if p <= 0]
    win_rate = len(winning) / len(trades)
    avg_win = np.mean(winning) if winning else 0
    avg_loss = abs(np.mean(losing)) if losing else 0
    profit_factor = sum(winning) / abs(sum(losing)) if sum(losing) != 0 else float("inf")
    expectancy = total_pnl / len(trades)
    avg_rr = np.mean([abs(t.get("pnl", 0)) / max(t.get("dollar_risk", 1), 1)
                      for t in trades if t.get("dollar_risk", 0) > 0]) if trades else 0
    equity = [10000.0]
    peaks = [10000.0]
    max_dd = 0
    for pnl in pnls:
        equity.append(equity[-1] + pnl)
        peaks.append(max(peaks[-1], equity[-1]))
        max_dd = max(max_dd, (peaks[-1] - equity[-1]) / peaks[-1])
    returns = np.diff(equity) / np.array(equity[:-1])
    returns = returns[~np.isnan(returns) & ~np.isinf(returns)]
    sharpe = 0
    if len(returns) > 1 and np.std(returns) > 1e-10:
        sharpe = np.mean(returns) / np.std(returns) * np.sqrt(365)
    return {
        "total_trades": len(trades), "winning_trades": len(winning), "losing_trades": len(losing),
        "win_rate_pct": round(win_rate * 100, 2), "profit_factor": round(profit_factor, 2),
        "total_pnl": round(total_pnl, 2), "avg_pnl": round(np.mean(pnls), 2),
        "max_win": round(max(pnls), 2), "max_loss": round(min(pnls), 2),
        "avg_win": round(avg_win, 2), "avg_loss": round(avg_loss, 2),
        "expectancy": round(expectancy, 2), "max_drawdown_pct": round(max_dd * 100, 2),
        "sharpe_ratio": round(sharpe, 2), "average_rr": round(avg_rr, 2),
    }


def main():
    print("=" * 100)
    print("REAL MARKET DATA BACKTEST  (GitHub-sourced, offline)")
    print(f"Run time: {datetime.now(timezone.utc).isoformat()}")
    print(f"Source: Bitstamp BTC/USD 1-minute candles (ff137/bitstamp-btcusd-minute-data)")
    print("=" * 100)

    df_1m = load_1min(CSV_PATH)
    print(f"  Loaded {len(df_1m):,} 1-minute candles")
    print(f"  Range: {df_1m.index.min()}  ->  {df_1m.index.max()}")

    df_4h_full = resample(df_1m, "4h")
    df_15m_full = resample(df_1m, "15min")
    print(f"  Resampled: {len(df_4h_full):,} 4H bars | {len(df_15m_full):,} 15M bars")

    # Run over the full available history (full walk-forward, no look-ahead).
    df_4h = df_4h_full.reset_index(drop=True)
    df_15m = df_15m_full.reset_index(drop=True)
    last_ts = int(df_4h["timestamp"].iloc[-1])

    print("\n  Running backtest over full history (this takes a few minutes)...")
    engine = BacktestEngine(slippage_pct=0.001, fee_pct=0.0004)
    result = engine.run_backtest(df_4h.copy(), df_15m.copy(), initial_capital=10000.0)
    trades = result.get("trades", [])
    for t in trades:
        t["symbol"] = SYMBOL

    def report(label, tr):
        m = compute_metrics(tr)
        print(f"\n  {label}")
        print(f"    Trades: {m['total_trades']}  | Win rate: {m['win_rate_pct']}%  | "
              f"Profit factor: {m['profit_factor']}")
        print(f"    Net PnL: ${m['total_pnl']} ({round(m['total_pnl']/100,2)}% on $10k)  | "
              f"Max DD: {m['max_drawdown_pct']}%  | Sharpe: {m['sharpe_ratio']}")
        print(f"    Expectancy: ${m['expectancy']}/trade  | Avg win/loss: "
              f"${m['avg_win']}/${m['avg_loss']}  | Avg R:R: {m['average_rr']}")
        return m

    print("\n" + "=" * 100)
    print("PERFORMANCE REPORT  (BTC/USD, honest full walk-forward)")
    print("=" * 100)
    m_full = report("FULL PERIOD", trades)

    cutoff = last_ts - 30 * 86400 * 1000
    last_month = [t for t in trades if int(t.get("entry_time", 0) or 0) >= cutoff]
    m_month = report("LAST 30 DAYS", last_month)

    out = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data_source": "Bitstamp BTC/USD 1m (ff137/bitstamp-btcusd-minute-data), resampled",
        "symbol": SYMBOL,
        "full_period": m_full,
        "last_30_days": m_month,
        "engine_extras": {
            "total_partial_exits": result.get("total_partial_exits", 0),
            "breakeven_trades": result.get("breakeven_trades", 0),
            "trailing_activated_trades": result.get("trailing_activated_trades", 0),
        },
    }
    out_path = os.path.join(os.path.dirname(__file__), "..", "github_data_backtest_results.json")
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()
