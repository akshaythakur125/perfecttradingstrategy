#!/usr/bin/env bash
# Activate the venv and run the forward paper trader (top-60 liquid, 15-min ticks).
# Edit the flags here to change the profile.
set -euo pipefail
cd "$(dirname "$0")/.."
# shellcheck disable=SC1091
. .venv/bin/activate
exec python scripts/paper_trade.py --top 60 --min-volume 50000000 --risk 0.02 --max-concurrent 5 --loop 900
