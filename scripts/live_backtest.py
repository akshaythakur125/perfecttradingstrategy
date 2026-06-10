#!/usr/bin/env python3
"""Multi-asset portfolio backtest over the last N days using live BingX data.

Runs the active strategy (sweep + BOS + FVG/OB confluence, ATR stop, partial
TPs, drawdown throttle) on the top-K perpetuals, then simulates a SINGLE shared
account across all symbols with a max-concurrent-positions cap -- a realistic
portfolio view, not 150 independent accounts.

Run in Codespaces / a machine with internet (no API key needed):
    python scripts/live_backtest.py --top 150 --days 30 --risk 0.02 --max-concurrent 5

Read-only market data only.
"""
import sys, os, asyncio, json, argparse
import numpy as np
import pandas as pd
from datetime import datetime, timezone
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from engines.exchange_clients import BingXClient
from engines.backtest_engine import BacktestEngine

MS_15M = 15 * 60 * 1000


async def fetch_paged(client, symbol, interval, total):
    """Fetch ~`total` klines by paging backwards with endTime (BingX limit 1440)."""
    frames, end = [], None
    while sum(len(f) for f in frames) < total:
        df = await client.get_klines(symbol, interval, limit=1440, end_time=end)
        if df is None or len(df) == 0:
            break
        frames.append(df)
        end = int(df["timestamp"].iloc[0]) - 1
        if len(df) < 1440:
            break
    if not frames:
        return None
    out = (pd.concat(frames).drop_duplicates("timestamp")
           .sort_values("timestamp").reset_index(drop=True))
    return out.tail(total).reset_index(drop=True)


async def collect_symbol(client, symbol, days, sem):
    """Per-symbol backtest -> list of trades as R-multiples (sizing-independent)."""
    async with sem:
        try:
            need_15m = days * 96 + 300          # window + warmup
            df_4h = await fetch_paged(client, symbol, "4h", 500)
            df_15m = await fetch_paged(client, symbol, "15m", max(need_15m, 1440))
        except Exception:
            return symbol, []
    if df_4h is None or df_15m is None or len(df_4h) < 210 or len(df_15m) < 250:
        return symbol, []
    for df in (df_4h, df_15m):
        df["symbol"] = symbol
        df["exchange"] = "BINGX"
    cutoff = int(df_4h["timestamp"].iloc[-1]) - days * 86400 * 1000
    try:
        res = BacktestEngine().run_backtest(df_4h.copy(), df_15m.copy(), 10000.0,
                                            trade_start_ts=cutoff)
    except Exception:
        return symbol, []
    trades = []
    for t in res["trades"]:
        dr = t.get("dollar_risk", 0) or 0
        if dr <= 0:
            continue
        entry_ts = int(t["entry_time"]) if str(t["entry_time"]).isdigit() else 0
        trades.append({
            "symbol": symbol, "dir": t["direction"],
            "R": t["pnl"] / dr,
            "entry_ts": entry_ts,
            "exit_ts": entry_ts + int(t.get("holding_bars", 0)) * MS_15M,
        })
    return symbol, trades


def portfolio_sim(all_trades, risk, max_concurrent):
    """Event-driven shared-account sim with a concurrency cap. PnL realized at exit."""
    events = []
    for tr in all_trades:
        events.append((tr["entry_ts"], 0, tr))   # 0 = entry (processed first at a tie)
        events.append((tr["exit_ts"], 1, tr))     # 1 = exit
    events.sort(key=lambda e: (e[0], e[1]))
    capital = 10000.0
    eq = [capital]
    open_count = 0
    pending = {}     # id(tr) -> pnl to realize at exit
    taken = 0
    for ts, typ, tr in events:
        if typ == 0:
            if open_count < max_concurrent:
                risk_amt = capital * risk
                pending[id(tr)] = tr["R"] * risk_amt
                open_count += 1
                taken += 1
        else:
            if id(tr) in pending:
                capital += pending.pop(id(tr))
                open_count -= 1
                eq.append(capital)
    eq = np.array(eq)
    peak = np.maximum.accumulate(eq)
    dd = float(((peak - eq) / peak).max() * 100) if len(eq) > 1 else 0.0
    taken_trades = [t for t in all_trades if True][:taken]
    return eq, dd, taken


async def main(top_n, days, risk, max_concurrent, exchange):
    client = BingXClient()
    print(f"Fetching top {top_n} {exchange} perps by volume...")
    symbols = await client.get_top_pairs_by_volume(top_n=top_n)
    print(f"  got {len(symbols)} symbols. Backtesting last {days} days each...")
    sem = asyncio.Semaphore(8)
    results = await asyncio.gather(*[collect_symbol(client, s, days, sem) for s in symbols])
    await client.close()

    all_trades, per_symbol = [], {}
    for sym, trades in results:
        if trades:
            per_symbol[sym] = {"trades": len(trades),
                               "avg_R": round(float(np.mean([t["R"] for t in trades])), 3)}
            all_trades.extend(trades)
    all_trades.sort(key=lambda t: t["entry_ts"])

    if not all_trades:
        print("\nNo trades. If symbols were fetched but no trades fired, the strategy was "
              "simply selective this month. If 0 symbols, check verify_bingx.py (geo-block).")
        return

    eq, dd, taken = portfolio_sim(all_trades, risk, max_concurrent)
    Rs = [t["R"] for t in all_trades]
    wins = [r for r in Rs if r > 0]
    ret = (eq[-1] / 10000 - 1) * 100
    pf_w = sum(r for r in Rs if r > 0); pf_l = abs(sum(r for r in Rs if r <= 0))
    print("\n" + "=" * 70)
    print(f"PORTFOLIO BACKTEST — last {days} days, top {top_n} {exchange} perps")
    print(f"  risk/trade {risk*100:.0f}%, max concurrent {max_concurrent}")
    print("=" * 70)
    print(f"  Symbols with trades : {len(per_symbol)}")
    print(f"  Signals (all)       : {len(all_trades)}   taken (cap-limited): {taken}")
    print(f"  Pooled win rate     : {100*len(wins)/len(Rs):.1f}%")
    print(f"  Pooled profit factor: {pf_w/pf_l:.2f}" if pf_l else "  PF: inf")
    print(f"  Portfolio return    : {ret:+.1f}%  on $10,000")
    print(f"  Portfolio max DD    : {dd:.1f}%")
    print(f"  Trades / month      : {len(all_trades)/(days/30.4):.1f}")
    top_syms = sorted(per_symbol.items(), key=lambda kv: kv[1]["trades"], reverse=True)[:15]
    print("\n  Most active symbols:")
    for s, d in top_syms:
        print(f"    {s:14} trades={d['trades']:<3} avgR={d['avg_R']}")

    out = {"timestamp": datetime.now(timezone.utc).isoformat(), "exchange": exchange,
           "top_n": top_n, "days": days, "risk": risk, "max_concurrent": max_concurrent,
           "portfolio_return_pct": round(ret, 1), "portfolio_max_dd_pct": round(dd, 1),
           "signals": len(all_trades), "win_rate_pct": round(100*len(wins)/len(Rs), 1),
           "per_symbol": per_symbol}
    path = os.path.join(os.path.dirname(__file__), "..", "live_backtest_results.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\nSaved: {path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=150)
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--risk", type=float, default=0.02)
    ap.add_argument("--max-concurrent", type=int, default=5)
    ap.add_argument("--exchange", default="BINGX")
    args = ap.parse_args()
    asyncio.run(main(args.top, args.days, args.risk, args.max_concurrent, args.exchange))
