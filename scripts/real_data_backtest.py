#!/usr/bin/env python3
"""
Real market data backtest: last 20 days on Binance Futures.
Fetches actual OHLCV data from Binance public REST API and runs the trading strategy.
"""
import sys, os, json, time, math
from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from engines.indicators import compute_all_indicators
from engines.backtest_engine import BacktestEngine

BINANCE_FAPI = "https://fapi.binance.com"
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT", "XRPUSDT", "ADAUSDT"]
INTERVAL_4H = "4h"
INTERVAL_15M = "15m"
LOOKBACK_DAYS = 20
WARMUP_CANDLES_4H = 400  # enough for EMA200 warmup
WARMUP_CANDLES_15M = 2000

def fetch_klines(symbol, interval, limit=500, start_time=None, end_time=None):
    """Fetch OHLCV klines from Binance Futures API."""
    params = {"symbol": symbol, "interval": interval, "limit": min(limit, 1500)}
    if start_time:
        params["startTime"] = int(start_time)
    if end_time:
        params["endTime"] = int(end_time)
    
    url = f"{BINANCE_FAPI}/fapi/v1/klines"
    for attempt in range(3):
        try:
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code == 429:
                retry = int(resp.headers.get("Retry-After", 5))
                print(f"    Rate limited, waiting {retry}s...")
                time.sleep(retry)
                continue
            resp.raise_for_status()
            data = resp.json()
            if not data:
                return None
            return data
        except Exception as e:
            if attempt < 2:
                print(f"    Retry {attempt+1} after error: {e}")
                time.sleep(2 ** attempt)
            else:
                raise
    return None

def klines_to_df(raw, symbol="", exchange="BINANCE"):
    """Convert Binance klines JSON to OHLCV DataFrame."""
    rows = []
    for k in raw:
        rows.append({
            "timestamp": int(k[0]),
            "open": float(k[1]),
            "high": float(k[2]),
            "low": float(k[3]),
            "close": float(k[4]),
            "volume": float(k[5]),
        })
    df = pd.DataFrame(rows)
    df["symbol"] = symbol
    df["exchange"] = exchange
    return df

def fetch_all_klines(symbol, interval, target_count, lookback_ms):
    """Fetch enough klines by paginating if needed."""
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    start_ms = now_ms - lookback_ms
    
    all_data = []
    cursor = start_ms
    while len(all_data) < target_count:
        remaining = target_count - len(all_data)
        batch = fetch_klines(symbol, interval, limit=min(1500, remaining * 2), start_time=cursor)
        if not batch or len(batch) == 0:
            break
        all_data.extend(batch)
        cursor = batch[-1][0] + 1
        if len(batch) < 100:
            break
        time.sleep(0.1)
    
    if not all_data:
        return None
    
    return all_data

def fetch_funding_rate(symbol, limit=100):
    """Fetch historical funding rate data."""
    params = {"symbol": symbol, "limit": limit}
    url = f"{BINANCE_FAPI}/fapi/v1/fundingRate"
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return None

def fetch_open_interest(symbol):
    """Fetch current open interest."""
    url = f"{BINANCE_FAPI}/fapi/v1/openInterest"
    try:
        resp = requests.get(url, params={"symbol": symbol}, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return None

def fetch_open_interest_hist(symbol, period="4h", limit=100):
    """Fetch historical open interest."""
    params = {"symbol": symbol, "period": period, "limit": limit}
    url = f"{BINANCE_FAPI}/futures/data/openInterestHist"
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return None

def compute_metrics(trades):
    """Compute performance metrics from a list of trade dicts."""
    if not trades:
        return {"total_trades":0,"winning_trades":0,"losing_trades":0,"win_rate_pct":0,
                "profit_factor":0,"total_pnl":0,"avg_pnl":0,"max_win":0,"max_loss":0,
                "avg_win":0,"avg_loss":0,"expectancy":0,"max_drawdown_pct":0,
                "sharpe_ratio":0,"average_rr":0}
    
    pnls = [t.get("pnl", 0) for t in trades]
    total_pnl = sum(pnls)
    winning = [p for p in pnls if p > 0]
    losing = [p for p in pnls if p <= 0]
    n_wins = len(winning)
    n_losses = len(losing)
    win_rate = n_wins / len(trades) if trades else 0
    avg_win = np.mean(winning) if winning else 0
    avg_loss = abs(np.mean(losing)) if losing else 1
    profit_factor = sum(winning) / abs(sum(losing)) if sum(losing) != 0 else float("inf")
    expectancy = total_pnl / len(trades) if trades else 0
    
    avg_rr = np.mean([
        abs(t.get("pnl", 0)) / max(t.get("dollar_risk", 1), 1)
        for t in trades if t.get("dollar_risk", 0) > 0
    ]) if trades else 0
    
    # Simulate equity curve from trades
    equity = [10000.0]
    peaks = [10000.0]
    max_dd = 0
    for pnl in pnls:
        equity.append(equity[-1] + pnl)
        peaks.append(max(peaks[-1], equity[-1]))
        dd = (peaks[-1] - equity[-1]) / peaks[-1]
        max_dd = max(max_dd, dd)
    
    returns = np.diff(equity) / np.array(equity[:-1])
    returns = returns[~np.isnan(returns) & ~np.isinf(returns)]
    sharpe = 0
    if len(returns) > 1 and np.std(returns) > 1e-10:
        sharpe = np.mean(returns) / np.std(returns) * np.sqrt(365)
    
    return {
        "total_trades": len(trades),
        "winning_trades": n_wins,
        "losing_trades": n_losses,
        "win_rate_pct": round(win_rate * 100, 2),
        "profit_factor": round(profit_factor, 2),
        "total_pnl": round(total_pnl, 2),
        "avg_pnl": round(np.mean(pnls), 2),
        "max_win": round(max(pnls), 2) if pnls else 0,
        "max_loss": round(min(pnls), 2) if pnls else 0,
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "expectancy": round(expectancy, 2),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "sharpe_ratio": round(sharpe, 2),
        "average_rr": round(avg_rr, 2),
    }

def print_trade(t):
    """Format a single trade for display."""
    direction = t.get("direction", "?")
    pnl = t.get("pnl", 0)
    entry = t.get("entry", 0)
    sl = t.get("stop_loss", 0)
    exit_p = t.get("exit_price", 0)
    risk = t.get("dollar_risk", 1)
    rr = abs(pnl) / risk if risk > 0 else 0
    partials = t.get("partial_exits", [])
    tp_reached = ", ".join([f"TP{e['tp']}(${e['price']:.0f})" for e in partials]) if partials else "SL/TIME"
    symbol = t.get("symbol", "")
    return (
        f"  {symbol:>8} {direction:<5} Entry=${entry:<8.2f} SL=${sl:<8.2f} "
        f"Exit=${exit_p:<8.2f} PnL=${pnl:<+8.2f} RR={rr:<5.2f} [{tp_reached}]"
    )


print("=" * 100)
print("REAL MARKET DATA BACKTEST — LAST 20 DAYS")
print(f"Run time: {datetime.now(timezone.utc).isoformat()}")
print(f"Source: Binance Futures (public REST API)")
print("=" * 100)

now = datetime.now(timezone.utc)
cutoff_dt = now - timedelta(days=LOOKBACK_DAYS)
cutoff_ms = int(cutoff_dt.timestamp() * 1000)

all_asset_results = {}
trade_log = []

for sym in SYMBOLS:
    print(f"\n{'─'*100}")
    print(f"ASSET: {sym}")
    print(f"{'─'*100}")
    
    # Fetch 4H data (need ~400 bars for indicator warmup)
    print(f"  Fetching {INTERVAL_4H} data...")
    lookback_4h = WARMUP_CANDLES_4H * 4 * 3600 * 1000  # enough for warmup
    raw_4h = fetch_all_klines(sym, INTERVAL_4H, WARMUP_CANDLES_4H, lookback_4h)
    if not raw_4h:
        print(f"  ✗ FAILED to fetch {INTERVAL_4H} data")
        continue
    df_4h = klines_to_df(raw_4h, sym, "BINANCE")
    print(f"    Got {len(df_4h)} candles ({df_4h['timestamp'].min()} → {df_4h['timestamp'].max()})")
    
    # Restrict to cutoff
    df_4h_live = df_4h[df_4h["timestamp"] >= cutoff_ms].copy()
    print(f"    Last {LOOKBACK_DAYS} days: {len(df_4h_live)} candles")
    
    # Fetch 15M data
    print(f"  Fetching {INTERVAL_15M} data...")
    lookback_15m = WARMUP_CANDLES_15M * 15 * 60 * 1000
    raw_15m = fetch_all_klines(sym, INTERVAL_15M, WARMUP_CANDLES_15M, lookback_15m)
    if not raw_15m:
        print(f"  ✗ FAILED to fetch {INTERVAL_15M} data")
        continue
    df_15m = klines_to_df(raw_15m, sym, "BINANCE")
    print(f"    Got {len(df_15m)} candles ({df_15m['timestamp'].min()} → {df_15m['timestamp'].max()})")
    
    df_15m_live = df_15m[df_15m["timestamp"] >= cutoff_ms].copy()
    print(f"    Last {LOOKBACK_DAYS} days: {len(df_15m_live)} candles")
    
    # Fetch funding rate and OI
    funding = fetch_funding_rate(sym, limit=1)
    oi = fetch_open_interest(sym)
    fr_val = None
    if funding and isinstance(funding, list) and len(funding) > 0:
        try:
            fr_val = float(funding[0]["fundingRate"])
        except (TypeError, ValueError, KeyError):
            fr_val = None
    oi_hist = fetch_open_interest_hist(sym, "4h", limit=2)
    oi_change = None
    if oi_hist and len(oi_hist) >= 2:
        oi_current = float(oi_hist[-1]["sumOpenInterest"])
        oi_prev = float(oi_hist[-2]["sumOpenInterest"])
        oi_change = ((oi_current - oi_prev) / oi_prev) * 100 if oi_prev > 0 else None
    print(f"  Funding rate: {fr_val}")
    print(f"  OI change (4h): {oi_change}%")
    
    # Run backtest
    print(f"  Running backtest...")
    try:
        engine = BacktestEngine(slippage_pct=0.001, fee_pct=0.0004)
        result = engine.run_backtest(df_4h.copy(), df_15m.copy(), initial_capital=10000.0)
        
        trades = result.get("trades", [])
        n_trades = len(trades)
        metrics = compute_metrics(trades)
        metrics["n_candles_4h"] = len(df_4h)
        metrics["n_candles_15m"] = len(df_15m)
        metrics["n_candles_4h_live"] = len(df_4h_live)
        metrics["n_candles_15m_live"] = len(df_15m_live)
        metrics["funding_rate"] = fr_val
        metrics["oi_change_pct"] = oi_change
        metrics["total_partial_exits"] = result.get("total_partial_exits", 0)
        metrics["breakeven_trades"] = result.get("breakeven_trades", 0)
        metrics["trailing_activated_trades"] = result.get("trailing_activated_trades", 0)
        
        all_asset_results[sym] = metrics
        for t in trades:
            t["symbol"] = sym
        trade_log.extend(trades)
        
        print(f"  ✓ Trades: {n_trades} | Win rate: {metrics.get('win_rate_pct', 0)}% | "
              f"PnL: ${metrics.get('total_pnl', 0)} | "
              f"Sharpe: {metrics.get('sharpe_ratio', 0)} | "
              f"DD: {metrics.get('max_drawdown_pct', 0)}%")
        if n_trades > 0:
            print(f"    Partial exits: {metrics['total_partial_exits']} | "
                  f"Break-even: {metrics['breakeven_trades']} | "
                  f"Trailing: {metrics['trailing_activated_trades']}")
            print(f"    Avg RR: {metrics.get('average_rr', 0)} | "
                  f"Expectancy: ${metrics.get('expectancy', 0)}")
            print(f"    Best trade: ${metrics.get('max_win', 0)} | "
                  f"Worst trade: ${metrics.get('max_loss', 0)}")
        
    except Exception as e:
        print(f"  ✗ Backtest error: {e}")
        import traceback
        traceback.print_exc()
        continue
    
    print(f"  Done.")

# =========================================================================
# GLOBAL AGGREGATE
# =========================================================================
print("\n" + "=" * 100)
print("GLOBAL PERFORMANCE REPORT")
print("=" * 100)

all_trades_sorted = sorted(trade_log, key=lambda t: t.get("entry_time", 0))
global_metrics = compute_metrics(trade_log)
print(f"  Total assets:      {len(all_asset_results)}")
print(f"  Total trades:      {global_metrics.get('total_trades', 0)}")
print(f"  Winning trades:    {global_metrics.get('winning_trades', 0)}")
print(f"  Losing trades:     {global_metrics.get('losing_trades', 0)}")
print(f"  Win rate:          {global_metrics.get('win_rate_pct', 0)}%")
print(f"  Profit factor:     {global_metrics.get('profit_factor', 0)}")
print(f"  Net PnL:           ${global_metrics.get('total_pnl', 0)}")
print(f"  Max drawdown:      {global_metrics.get('max_drawdown_pct', 0)}%")
print(f"  Sharpe ratio:      {global_metrics.get('sharpe_ratio', 0)}")
print(f"  Average R:R:       {global_metrics.get('average_rr', 0)}")
print(f"  Expectancy:        ${global_metrics.get('expectancy', 0)}")
print(f"  Avg win:           ${global_metrics.get('avg_win', 0)}")
print(f"  Avg loss:          ${global_metrics.get('avg_loss', 0)}")
print(f"  Max win:           ${global_metrics.get('max_win', 0)}")
print(f"  Max loss:          ${global_metrics.get('max_loss', 0)}")

if all_asset_results:
    # Best/worst by PnL
    pnl_by_asset = {s: m["total_pnl"] for s, m in all_asset_results.items()}
    best = max(pnl_by_asset, key=pnl_by_asset.get)
    worst = min(pnl_by_asset, key=pnl_by_asset.get)
    print(f"\n  Best asset:        {best} (${pnl_by_asset[best]:.2f})")
    print(f"  Worst asset:       {worst} (${pnl_by_asset[worst]:.2f})")

# =========================================================================
# PER-ASSET BREAKDOWN
# =========================================================================
print(f"\n{'─'*100}")
print("PER-ASSET BREAKDOWN")
print(f"{'─'*100}")
print(f"  {'Symbol':>8} {'Trades':>6} {'WR%':>6} {'PF':>6} {'PnL':>10} {'DD%':>7} {'Sharpe':>7} {'AvgRR':>6} {'Exp':>8}")
print(f"  {'──────':>8} {'──────':>6} {'────':>6} {'────':>6} {'────':>10} {'─────':>7} {'──────':>7} {'─────':>6} {'────':>8}")
for sym in SYMBOLS:
    m = all_asset_results.get(sym)
    if m:
        print(f"  {sym:>8} {m['total_trades']:>6} {m['win_rate_pct']:>5.1f}% "
              f"{m['profit_factor']:>5.2f} ${m['total_pnl']:>+7.2f} "
              f"{m['max_drawdown_pct']:>5.1f}% {m['sharpe_ratio']:>6.2f} "
              f"{m['average_rr']:>5.2f} ${m['expectancy']:>+6.2f}")
    else:
        print(f"  {sym:>8}  FAILED")

# =========================================================================
# TRADE LOG
# =========================================================================
print(f"\n{'─'*100}")
print("TRADE LOG (chronological)")
print(f"{'─'*100}")

# Re-sort by entry time and type
trade_log_sorted = sorted(trade_log, key=lambda t: (t.get("entry_time", 0), t.get("symbol", "")))
for i, t in enumerate(trade_log_sorted):
    print(print_trade(t))

# =========================================================================
# VERDICT
# =========================================================================
print(f"\n{'='*100}")
print("VERDICT: Would this strategy have made money in the last 20 days?")
print(f"{'='*100}")

total_pnl = global_metrics.get("total_pnl", 0)
win_rate = global_metrics.get("win_rate_pct", 0)
sharpe = global_metrics.get("sharpe_ratio", 0)
pf = global_metrics.get("profit_factor", 0)
n_trades = global_metrics.get("total_trades", 0)

if total_pnl > 0 and sharpe > 0.5 and pf > 1.2:
    print(f"  ✓ YES — Strategy is profitable across {n_trades} trades")
    print(f"    Net PnL: ${total_pnl:.2f} on $10,000 capital")
elif total_pnl > 0:
    print(f"  ~ MARGINAL — Profitable but low quality")
    print(f"    Net PnL: ${total_pnl:.2f} | Sharpe: {sharpe} | PF: {pf}")
elif n_trades == 0:
    print(f"  ⚠ INCONCLUSIVE — No trades were generated across any asset")
    print(f"    The signal conditions are too strict for current market conditions")
else:
    print(f"  ✗ NO — Strategy lost money")
    print(f"    Net PnL: ${total_pnl:.2f} on $10,000 capital ({total_pnl/10000*100:.1f}%)")
    if win_rate < 50:
        print(f"    Win rate ({win_rate}%) < 50% — signals lack directional accuracy")
    if pf < 1.0:
        print(f"    Profit factor ({pf}) < 1.0 — losses outweigh gains")
    if sharpe < 0:
        print(f"    Sharpe ratio ({sharpe}) < 0 — risk-adjusted returns negative")

print(f"\n{'='*100}")
print(f"Report generated: {datetime.now(timezone.utc).isoformat()}")
print(f"{'='*100}")

# Save to JSON
output = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "symbols": SYMBOLS,
    "lookback_days": LOOKBACK_DAYS,
    "global": global_metrics,
    "per_asset": all_asset_results,
    "trades": [
        {
            "symbol": t.get("symbol"),
            "direction": t.get("direction"),
            "entry": round(t.get("entry", 0), 2),
            "stop_loss": round(t.get("stop_loss", 0), 2),
            "exit_price": round(t.get("exit_price", 0), 2),
            "pnl": round(t.get("pnl", 0), 2),
            "rr": round(abs(t.get("pnl", 0)) / max(t.get("dollar_risk", 1), 1), 2),
            "holding_bars": t.get("holding_bars", 0),
            "partial_exits": len(t.get("partial_exits", [])),
            "breakeven_activated": t.get("breakeven_activated", False),
            "confidence_score": t.get("confidence_score", 0),
        }
        for t in trade_log_sorted
    ]
}
with open("real_data_backtest_results.json", "w") as f:
    json.dump(output, f, indent=2, default=str)
print(f"\nFull results saved to real_data_backtest_results.json")
