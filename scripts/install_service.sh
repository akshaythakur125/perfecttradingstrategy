#!/usr/bin/env bash
# Install the paper trader as a systemd service (auto-start, restart on failure,
# survives reboots). Run from the repo root after setup_vm.sh:
#   bash scripts/install_service.sh
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
USERNAME="$(whoami)"
UNIT=/etc/systemd/system/paper-trader.service

if [ ! -x "$REPO/.venv/bin/python" ]; then
  echo "No venv found at $REPO/.venv -- run 'bash scripts/setup_vm.sh' first."; exit 1
fi

echo "==> Writing $UNIT"
sudo tee "$UNIT" >/dev/null <<EOF
[Unit]
Description=Perfect Trading Strategy paper trader
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$USERNAME
WorkingDirectory=$REPO
ExecStart=$REPO/.venv/bin/python $REPO/scripts/paper_trade.py --top 60 --min-volume 50000000 --risk 0.02 --max-concurrent 5 --loop 900
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now paper-trader.service
echo "==> Started. Useful commands:"
echo "    systemctl status paper-trader        # is it running?"
echo "    journalctl -u paper-trader -f        # live scoreboard/logs"
echo "    sudo systemctl stop paper-trader     # stop"
