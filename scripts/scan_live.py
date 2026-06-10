#!/usr/bin/env python3
"""Live scan of the top-N BingX perpetuals with the active strategy
(sweep + BOS + FVG/OB confluence). Read-only: no API key required.

Usage (in Codespaces / a machine with internet):
    python scripts/scan_live.py --top 150
"""
import sys, os, asyncio, json, argparse
from datetime import datetime, timezone
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from engines.scanner import ScannerEngine


async def main(top_n: int, exchange: str):
    scanner = ScannerEngine()
    print(f"Scanning top {top_n} {exchange} perpetuals... (this can take a couple of minutes)")
    signals = await scanner.scan_top_perpetuals(exchange=exchange, top_n=top_n)
    await scanner.data_collector.binance.close()
    await scanner.data_collector.okx.close()
    await scanner.data_collector.bingx.close()

    print(f"\n{len(signals)} signal(s) found:\n")
    for s in signals:
        print(f"  {s['symbol']:14} {s['direction']:5} conf={s.get('confidence_score',0):5} "
              f"entry={s.get('entry_price')} stop={s.get('stop_loss')} "
              f"tp1={s.get('take_profit_1')} tp2={s.get('take_profit_2')} "
              f"R:R(3R target)")
    out = {"timestamp": datetime.now(timezone.utc).isoformat(),
           "exchange": exchange, "top_n": top_n, "count": len(signals), "signals": signals}
    path = os.path.join(os.path.dirname(__file__), "..", "live_signals.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\nSaved: {path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=150)
    ap.add_argument("--exchange", default="BINGX")
    args = ap.parse_args()
    asyncio.run(main(args.top, args.exchange))
