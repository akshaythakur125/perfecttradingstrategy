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

## 4. Multi-asset walk-forward backtest (the robustness check)
```bash
# 3 separate past months, top 100 perps -- shows if the edge holds across months
python scripts/live_backtest.py --top 100 --months 3 --risk 0.02 --max-concurrent 5

# single recent month, liquid names only (realistic fills)
python scripts/live_backtest.py --top 150 --months 1 --min-volume 50000000
```
Runs the strategy on each symbol across one or more past 30-day windows, each as
**one shared account** with a concurrency cap (a realistic portfolio, not N
separate accounts). Prints a per-window table (signals, win%, PF, return, max
DD) plus a pooled summary and "positive windows / total". Writes
`live_backtest_results.json`.

**What to look for:** a real edge stays PF > 1 across *most* windows. If only
one window shines, it was a lucky month. The `--min-volume` filter removes
illiquid alts whose backtested fills are unrealistic.

Tune: `--risk`, `--max-concurrent`, `--months`, `--top`, `--min-volume`.
Heavier runs (more months/symbols) take longer — start at `--top 100 --months 3`.

## Honest notes
- The strategy was validated **on BTC only**. This backtest is the first look
  at how it behaves across alts — treat the first run as evidence-gathering,
  not a guarantee. Expect per-symbol quality to vary.
- Backtest fills are simulated (fees + slippage included, stop counted before
  target on a bar). Live results will differ.
- Codespaces is ephemeral (idles out) — fine for scans/backtests, **not** for
  an unattended 24/7 live bot. Use a persistent server for that.
