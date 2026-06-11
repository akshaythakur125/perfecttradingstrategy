#!/usr/bin/env python3
"""Multi-asset, multi-month portfolio backtest using live BingX data.

Runs the active strategy on the top-K perpetuals across one or more past 30-day
windows (walk-forward), each as a SINGLE shared account with a max-concurrent
cap. The per-window table is the robustness check: a real edge holds up across
months; a lucky month shows up as one good window among weak ones.

Run in Codespaces / a machine with internet (no API key needed):
    python scripts/live_backtest.py --top 100 --months 3 --risk 0.02 --max-concurrent 5
    python scripts/live_backtest.py --top 150 --months 1 --min-volume 50000000   # liquid only

Read-only market data only.
"""
import sys, os, asyncio, json, argparse
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from engines.exchange_clients import BingXClient

MS_15M = 15 * 60 * 1000
DAY_MS = 86400 * 1000


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


async def fetch_symbol(client, symbol, months, window_days, sem):
    """Fetch just enough 4H + 15M history to cover all windows (+ warmup)."""
    async with sem:
        try:
            span_days = months * window_days
            need_4h = (span_days + 45) * 6        # window span + ~45d warmup for EMA200
            need_15m = (span_days + 5) * 96
            df_4h = await fetch_paged(client, symbol, "4h", min(need_4h, 1440))
            df_15m = await fetch_paged(client, symbol, "15m", max(need_15m, 1440))
        except Exception:
            return symbol, None, None
    if df_4h is None or df_15m is None or len(df_4h) < 210 or len(df_15m) < 250:
        return symbol, None, None
    for df in (df_4h, df_15m):
        df["symbol"] = symbol
        df["exchange"] = "BINGX"
    return symbol, df_4h, df_15m


def backtest_symbol(args):
    """ONE engine pass per symbol over all windows; tag each trade with entry_ts.
    Runs in a worker process (CPU-bound)."""
    symbol, df_4h, df_15m, oldest_start = args
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
    from engines.backtest_engine import BacktestEngine
    try:
        res = BacktestEngine().run_backtest(df_4h, df_15m, 10000.0, trade_start_ts=oldest_start)
    except Exception:
        return []
    trades = []
    for t in res["trades"]:
        dr = t.get("dollar_risk", 0) or 0
        if dr <= 0:
            continue
        et = int(t["entry_time"]) if str(t["entry_time"]).isdigit() else 0
        trades.append({"symbol": symbol, "R": t["pnl"] / dr,
                       "entry_ts": et, "exit_ts": et + int(t.get("holding_bars", 0)) * MS_15M})
    return trades


def portfolio_sim(all_trades, risk, max_concurrent):
    """Event-driven shared-account sim with a concurrency cap. PnL realized at exit."""
    events = []
    for tr in all_trades:
        events.append((tr["entry_ts"], 0, tr))
        events.append((tr["exit_ts"], 1, tr))
    events.sort(key=lambda e: (e[0], e[1]))
    capital, eq, open_count, pending, taken = 10000.0, [10000.0], 0, {}, 0
    for ts, typ, tr in events:
        if typ == 0:
            if open_count < max_concurrent:
                pending[id(tr)] = tr["R"] * capital * risk
                open_count += 1; taken += 1
        elif id(tr) in pending:
            capital += pending.pop(id(tr)); open_count -= 1; eq.append(capital)
    eq = np.array(eq)
    peak = np.maximum.accumulate(eq)
    dd = float(((peak - eq) / peak).max() * 100) if len(eq) > 1 else 0.0
    return eq, dd, taken


def window_stats(trades, risk, max_concurrent):
    if not trades:
        return None
    eq, dd, taken = portfolio_sim(sorted(trades, key=lambda t: t["entry_ts"]), risk, max_concurrent)
    Rs = [t["R"] for t in trades]
    w = [r for r in Rs if r > 0]; l = [r for r in Rs if r <= 0]
    return {"signals": len(Rs), "taken": taken,
            "win": round(100 * len(w) / len(Rs), 1),
            "pf": round(sum(w) / abs(sum(l)), 2) if l and sum(l) != 0 else 99.0,
            "ret": round((eq[-1] / 10000 - 1) * 100, 1), "dd": round(dd, 1)}


async def main(top_n, months, window_days, risk, max_concurrent, min_volume, exchange):
    client = BingXClient()
    print(f"Fetching top {top_n} {exchange} perps "
          f"(min 24h volume ${min_volume:,.0f})...")
    symbols = await client.get_top_pairs_by_volume(top_n=top_n, min_quote_volume=min_volume)
    print(f"  {len(symbols)} symbols. Fetching {months} x {window_days}d of history each...")
    sem = asyncio.Semaphore(8)
    fetched = await asyncio.gather(*[fetch_symbol(client, s, months, window_days, sem) for s in symbols])
    await client.close()
    data = [(s, d4, d15) for s, d4, d15 in fetched if d4 is not None]
    print(f"  {len(data)} symbols with usable history. Backtesting in parallel...")

    now = max(int(d4["timestamp"].iloc[-1]) for _, d4, _ in data)
    oldest_start = now - months * window_days * DAY_MS
    jobs = [(s, d4, d15, oldest_start) for s, d4, d15 in data]
    all_trades = []
    with ProcessPoolExecutor(max_workers=max(1, (os.cpu_count() or 2))) as ex:
        for trades in ex.map(backtest_symbol, jobs):
            all_trades.extend(trades)
    print(f"  {len(all_trades)} trades across all symbols/windows.")

    windows = [(now - (w + 1) * window_days * DAY_MS, now - w * window_days * DAY_MS)
               for w in range(months)]
    rows, pooled, pos = [], [], 0
    for ws, we in windows:
        wt = [t for t in all_trades if ws <= t["entry_ts"] < we]
        st = window_stats(wt, risk, max_concurrent)
        label = (datetime.utcfromtimestamp(ws / 1000).strftime("%Y-%m-%d") + " .. " +
                 datetime.utcfromtimestamp(we / 1000).strftime("%Y-%m-%d"))
        rows.append((label, st))
        if st:
            pooled.extend(wt)
            pos += 1 if st["ret"] > 0 else 0

    print("\n" + "=" * 78)
    print(f"WALK-FORWARD — top {top_n} {exchange} perps, {window_days}d windows, "
          f"risk {risk*100:.0f}%, max-concurrent {max_concurrent}")
    print("=" * 78)
    print(f"  {'window':26} {'sig':>4} {'win%':>6} {'PF':>6} {'ret%':>8} {'maxDD%':>7}")
    for label, st in rows:
        if not st:
            print(f"  {label:26} {'— no trades':>26}"); continue
        print(f"  {label:26} {st['signals']:>4} {st['win']:>6} {st['pf']:>6} "
              f"{st['ret']:>+8} {st['dd']:>7}")
    n_win = sum(1 for _, st in rows if st)
    if pooled:
        Rs = [t["R"] for t in pooled]
        w = [r for r in Rs if r > 0]; l = [r for r in Rs if r <= 0]
        print("-" * 78)
        print(f"  POOLED across {n_win} window(s): signals={len(Rs)}  "
              f"win={100*len(w)/len(Rs):.1f}%  "
              f"PF={sum(w)/abs(sum(l)):.2f}  "
              f"positive windows={pos}/{n_win}")

    out = {"timestamp": datetime.now(timezone.utc).isoformat(), "exchange": exchange,
           "top_n": top_n, "months": months, "window_days": window_days, "risk": risk,
           "max_concurrent": max_concurrent, "min_volume": min_volume,
           "windows": [{"window": lbl, **(st or {})} for lbl, st in rows],
           "positive_windows": pos, "total_windows": n_win}
    path = os.path.join(os.path.dirname(__file__), "..", "live_backtest_results.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\nSaved: {path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=100)
    ap.add_argument("--months", type=int, default=3, help="number of past 30d windows to walk")
    ap.add_argument("--days", type=int, default=30, help="window length in days")
    ap.add_argument("--risk", type=float, default=0.02)
    ap.add_argument("--max-concurrent", type=int, default=5)
    ap.add_argument("--min-volume", type=float, default=0.0, help="min 24h quote volume (USD) filter")
    ap.add_argument("--exchange", default="BINGX")
    args = ap.parse_args()
    asyncio.run(main(args.top, args.months, args.days, args.risk,
                     args.max_concurrent, args.min_volume, args.exchange))
