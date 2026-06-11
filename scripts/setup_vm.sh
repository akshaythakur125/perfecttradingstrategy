#!/usr/bin/env bash
# One-time VM setup for the paper trader (Ubuntu/Debian).
# Run from the repo root:   bash scripts/setup_vm.sh
set -euo pipefail

echo "==> Installing system packages (python3, pip, venv, git, tmux)..."
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git tmux

echo "==> Creating virtualenv (.venv)..."
python3 -m venv .venv
# shellcheck disable=SC1091
. .venv/bin/activate
pip install --upgrade pip wheel
pip install -r backend/requirements.txt

echo "==> Verifying BingX reachability (read-only, no API key)..."
if python scripts/verify_bingx.py; then
  echo
  echo "==> Setup OK. Start the paper trader in a detachable tmux session:"
  echo "      tmux new -s paper"
  echo "      bash scripts/run_paper.sh"
  echo "    (detach: Ctrl-b then d   |   reattach: tmux attach -t paper)"
  echo
  echo "    Or install it as an always-on service (survives reboots):"
  echo "      bash scripts/install_service.sh"
else
  echo
  echo "!! BingX was NOT reachable from this host (likely a geo-block on this"
  echo "   cloud region's IP). Try another GCP region/zone, or a VPS from a"
  echo "   provider exchanges don't block (Hetzner, Contabo, DigitalOcean)."
  exit 1
fi
