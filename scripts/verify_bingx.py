#!/usr/bin/env python3
"""Verify BingX reachability and that BingXClient parses live responses.

Run this FIRST in a new environment (e.g. GitHub Codespaces):
    python scripts/verify_bingx.py

- HTTP 200 on contracts => reachable.
- HTTP 403/451 => geo-blocked (Azure/US IP); use a VPS in an allowed region.
It needs NO API key (public market data only).
"""
import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from engines.exchange_clients import BingXClient


async def main():
    c = BingXClient()
    ok = True
    try:
        print("1) contracts (perpetuals list)...")
        pairs = await c.get_usdt_pairs()
        print(f"   -> {len(pairs)} USDT perps. sample: {pairs[:5]}")
        if not pairs:
            print("   !! empty — likely geo-blocked or field names differ. Check raw response.")
            ok = False

        print("2) top 10 by 24h volume...")
        top = await c.get_top_pairs_by_volume(top_n=10)
        print(f"   -> {top}")

        sym = top[0] if top else (pairs[0] if pairs else "BTCUSDT")
        print(f"3) klines 4h for {sym}...")
        df4 = await c.get_klines(sym, "4h", limit=5)
        print(f"   -> {None if df4 is None else len(df4)} bars")
        if df4 is not None and len(df4):
            print(df4.tail(2).to_string(index=False))
        else:
            ok = False

        print(f"4) klines 15m for {sym}...")
        df15 = await c.get_klines(sym, "15m", limit=5)
        print(f"   -> {None if df15 is None else len(df15)} bars")

        print(f"5) funding + open interest for {sym}...")
        fr = await c.get_funding_rate(sym)
        oi = await c.get_open_interest(sym)
        print(f"   -> funding={fr}  open_interest={oi}")
    finally:
        await c.close()

    print("\nRESULT:", "OK — BingX reachable and parsed." if ok else
          "PROBLEM — see notes above (geo-block or field-name mismatch).")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    asyncio.run(main())
