#!/usr/bin/env python3
"""Forward paper-trading logger for the active strategy (no real orders).

Each "tick" (one invocation, or looped):
  1. Scans the top-N liquid BingX perps for fresh signals.
  2. Opens PAPER positions as resting limit orders (limit_entry_price).
  3. Advances every open/pending position against real 15M candles since it was
     last checked -- fill / cancel / stop / TP1+breakeven / TP2 / time stop --
     using the SAME rules as the backtest, so forward results are comparable.
  4. Persists everything to a state JSON and prints a running scoreboard.

This is the honest test the backtest cannot do: real fills and execution
friction over forward time. Read-only market data -- NO API KEY, NO real money.

Run once (cron every ~15 min) or continuously:
    python scripts/paper_trade.py --top 60 --min-volume 50000000
    python scripts/paper_trade.py --loop 900            # tick every 15 min

Needs a persistent host (VPS / always-on machine), NOT an ephemeral Codespace.
"""
import sys, os, json, time, asyncio, argparse, uuid
from datetime import datetime, timezone
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from engines.exchange_clients import BingXClient
from engines.signal_engine import SignalEngine

FEE = 0.0004
MAX_HOLD = 64            # 15M bars (~16h), matches the backtest time stop
STATE_DEFAULT = os.path.join(os.path.dirname(__file__), "..", "paper_state.json")


def load_state(path, start_capital):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {"started": datetime.now(timezone.utc).isoformat(), "last_run": None,
            "start_capital": start_capital, "equity": start_capital, "peak": start_capital,
            "open": [], "closed": []}


def save_state(path, state):
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    with open(path, "w") as f:
        json.dump(state, f, indent=2, default=str)


def eff_risk(state, base_risk, dd_level=0.05, dd_factor=0.4):
    peak = max(state["peak"], 1e-9)
    dd = (peak - state["equity"]) / peak
    return base_risk * dd_factor if dd > dd_level else base_risk


def advance_position(p, bars):
    """Walk 15M bars (list of dicts, ascending, ts > p['last_ts']) and update the
    paper position in place. Returns (closed: bool, realized_R_delta accumulates in p)."""
    d = p["dir"]
    for b in bars:
        ts, hi, lo, cl = int(b["timestamp"]), b["high"], b["low"], b["close"]
        if ts <= p["last_ts"]:
            continue
        p["last_ts"] = ts

        if p["status"] == "pending":
            p["bars_waited"] += 1
            touched = (d == "LONG" and lo <= p["limit_px"]) or (d == "SHORT" and hi >= p["limit_px"])
            if touched:
                p["status"] = "open"
                p["entry_px"] = p["limit_px"]
                p["entry_ts"] = ts
                p["risk_price"] = abs(p["entry_px"] - p["stop"])
                p["realized_R"] -= p["entry_px"] * FEE / max(p["risk_price"], 1e-12)  # entry fee
            elif p["bars_waited"] >= p["expiry"]:
                p["status"] = "cancelled"
                return True
            continue

        if p["status"] != "open":
            continue

        rp = max(p["risk_price"], 1e-12)
        p["bars_held"] += 1
        hit_stop = lo <= p["stop"] if d == "LONG" else hi >= p["stop"]
        hit_tp1 = hi >= p["tp1"] if d == "LONG" else lo <= p["tp1"]
        hit_tp2 = hi >= p["tp2"] if d == "LONG" else lo <= p["tp2"]
        sgn = 1 if d == "LONG" else -1

        if hit_stop:
            p["realized_R"] += sgn * (p["stop"] - p["entry_px"]) / rp * p["remaining"] \
                - p["stop"] * FEE / rp * p["remaining"]
            p["remaining"] = 0.0
            p["exit_reason"] = "stop" if not p["breakeven"] else "breakeven"
            p["status"] = "closed"; p["exit_ts"] = ts
            return True
        if not p["breakeven"] and hit_tp1:
            p["realized_R"] += sgn * (p["tp1"] - p["entry_px"]) / rp * 0.5 - p["tp1"] * FEE / rp * 0.5
            p["remaining"] -= 0.5
            p["stop"] = p["entry_px"]; p["breakeven"] = True
        if p["breakeven"] and p["remaining"] > 0 and hit_tp2:
            p["realized_R"] += sgn * (p["tp2"] - p["entry_px"]) / rp * p["remaining"] \
                - p["tp2"] * FEE / rp * p["remaining"]
            p["remaining"] = 0.0
            p["exit_reason"] = "tp2"; p["status"] = "closed"; p["exit_ts"] = ts
            return True
        if p["bars_held"] >= MAX_HOLD:
            p["realized_R"] += sgn * (cl - p["entry_px"]) / rp * p["remaining"] - cl * FEE / rp * p["remaining"]
            p["remaining"] = 0.0
            p["exit_reason"] = "time"; p["status"] = "closed"; p["exit_ts"] = ts
            return True
    return False


async def tick(client, eng, state, args):
    symbols = await client.get_top_pairs_by_volume(top_n=args.top, min_quote_volume=args.min_volume)
    held = {p["symbol"] for p in state["open"]}

    # 1) advance existing open/pending positions
    still_open = []
    for p in state["open"]:
        bars = await client.get_klines(p["symbol"], "15m", limit=200)
        if bars is not None and len(bars):
            closed = advance_position(p, bars.to_dict("records"))
        else:
            closed = False
        if closed and p["status"] in ("closed", "cancelled"):
            if p["status"] == "closed":
                pnl = p["realized_R"] * p["risk_amt"]
                state["equity"] += pnl
                state["peak"] = max(state["peak"], state["equity"])
                state["closed"].append({k: p[k] for k in
                    ("symbol", "dir", "signal_ts", "entry_ts", "exit_ts", "realized_R",
                     "exit_reason")} | {"pnl": round(pnl, 2)})
        else:
            still_open.append(p)
    state["open"] = still_open

    # 2) look for new signals (skip symbols already held; respect concurrency cap)
    held = {p["symbol"] for p in state["open"]}
    slots = args.max_concurrent - len(state["open"])
    new_signals = 0
    for sym in symbols:
        if slots <= 0:
            break
        if sym in held:
            continue
        df4 = await client.get_klines(sym, "4h", limit=320)
        df15 = await client.get_klines(sym, "15m", limit=320)
        if df4 is None or df15 is None or len(df4) < 250 or len(df15) < 60:
            continue
        df4["symbol"] = sym; df15["symbol"] = sym
        sig = eng.evaluate_long_setup(df4, df15) or eng.evaluate_short_setup(df4, df15)
        if not sig:
            continue
        limit_px = sig.get("limit_entry_price") or sig["entry_price"]
        risk_amt = state["equity"] * eff_risk(state, args.risk)
        state["open"].append({
            "id": uuid.uuid4().hex[:8], "symbol": sym, "dir": sig["direction"],
            "signal_ts": int(df15["timestamp"].iloc[-1]),
            "status": "pending", "limit_px": limit_px, "expiry": int(sig.get("limit_expiry_bars") or 8),
            "bars_waited": 0, "stop": sig["stop_loss"], "tp1": sig["take_profit_1"],
            "tp2": sig["take_profit_2"], "entry_px": None, "entry_ts": None,
            "risk_price": abs(sig["entry_price"] - sig["stop_loss"]),
            "remaining": 1.0, "breakeven": False, "realized_R": 0.0, "risk_amt": risk_amt,
            "bars_held": 0, "last_ts": int(df15["timestamp"].iloc[-1]),
            "confidence": sig.get("confidence_score", 0),
        })
        slots -= 1; new_signals += 1
    return new_signals


def scoreboard(state):
    closed = state["closed"]
    n = len(closed)
    wins = [c for c in closed if c["pnl"] > 0]
    gross_w = sum(c["pnl"] for c in wins)
    gross_l = abs(sum(c["pnl"] for c in closed if c["pnl"] <= 0))
    ret = (state["equity"] / state["start_capital"] - 1) * 100
    dd = (state["peak"] - state["equity"]) / max(state["peak"], 1e-9) * 100
    print(f"\n  PAPER SCOREBOARD  ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)")
    print(f"    equity ${state['equity']:.2f}  ({ret:+.1f}%)  cur DD {dd:.1f}%")
    print(f"    open/pending: {len(state['open'])}   closed: {n}")
    if n:
        print(f"    win rate {100*len(wins)/n:.1f}%   "
              f"profit factor {gross_w/gross_l:.2f}" if gross_l else "    PF inf")
    for p in state["open"]:
        tag = "PENDING" if p["status"] == "pending" else f"OPEN R={p['realized_R']:.2f}"
        print(f"      {p['symbol']:14} {p['dir']:5} {tag}")


async def run_once(args):
    client = BingXClient()
    eng = SignalEngine()   # shipped strategy defaults (sweep+BOS+confluence+limit entry)
    state = load_state(args.state, args.capital)
    try:
        new = await tick(client, eng, state, args)
    finally:
        await client.close()
    save_state(args.state, state)
    print(f"  tick done: {new} new signal(s) opened.")
    scoreboard(state)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=60)
    ap.add_argument("--min-volume", type=float, default=50_000_000, help="min 24h quote volume (USD)")
    ap.add_argument("--risk", type=float, default=0.02)
    ap.add_argument("--max-concurrent", type=int, default=5)
    ap.add_argument("--capital", type=float, default=10000.0)
    ap.add_argument("--state", default=STATE_DEFAULT)
    ap.add_argument("--loop", type=int, default=0, help="seconds between ticks (0 = single tick)")
    args = ap.parse_args()
    if args.loop > 0:
        print(f"Paper trading loop every {args.loop}s. Ctrl-C to stop. State: {args.state}")
        while True:
            try:
                asyncio.run(run_once(args))
            except Exception as e:
                print(f"  tick error: {e}")
            time.sleep(args.loop)
    else:
        asyncio.run(run_once(args))


if __name__ == "__main__":
    main()
