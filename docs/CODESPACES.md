# Running in GitHub Codespaces

This sandbox-friendly guide gets the live scanner and the multi-asset backtest
running in a Codespace, where (unlike some restricted environments) BingX's
public API is reachable.

> All steps below are **read-only market data** — no API key is required.
> Only set `BINGX_API_KEY` / `BINGX_SECRET_KEY` (in a local `.env`, never in
> code or chat) if you later add live order placement.

## 1. Open a Codespace
From the GitHub repo: **Code ▸ Codespaces ▸ Create codespace on
`claude/repository-overview-pyuhhj`**. The devcontainer installs Python deps
automatically (`pip install -r backend/requirements.txt`).

## 2. Verify BingX is reachable (do this first)
```bash
python scripts/verify_bingx.py
```
- Prints contract count, top-volume symbols, sample klines, funding/OI.
- **200 / data printed** → good to go.
- **403 / 451 / empty** → Codespaces' Azure IP is geo-blocked by BingX. Use a
  small VPS in an allowed region instead (same commands).

## 3. Scan the top 150 perpetuals live
```bash
python scripts/scan_live.py --top 150
```
Prints current sweep+BOS signals and writes `live_signals.json`.

## 4. Multi-asset portfolio backtest — last 30 days, top 150
```bash
python scripts/live_backtest.py --top 150 --days 30 --risk 0.02 --max-concurrent 5
```
Runs the strategy on each symbol, then simulates **one shared account** across
all of them with a concurrency cap (a realistic portfolio, not 150 separate
accounts). Reports pooled win rate, profit factor, portfolio return, max
drawdown, trades/month, and the most active symbols. Writes
`live_backtest_results.json`.

Tune: `--risk` (per-trade fraction), `--max-concurrent` (open positions cap),
`--days`, `--top`.

## Honest notes
- The strategy was validated **on BTC only**. This backtest is the first look
  at how it behaves across alts — treat the first run as evidence-gathering,
  not a guarantee. Expect per-symbol quality to vary.
- Backtest fills are simulated (fees + slippage included, stop counted before
  target on a bar). Live results will differ.
- Codespaces is ephemeral (idles out) — fine for scans/backtests, **not** for
  an unattended 24/7 live bot. Use a persistent server for that.
