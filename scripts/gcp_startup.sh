#!/usr/bin/env bash
# GCP Compute Engine STARTUP SCRIPT for the forward paper trader.
# Paste this into "Create instance > Advanced > Automation > Startup script".
# It runs as ROOT at boot -- no interactive sudo needed.
#
# Image: Debian 12 (or Ubuntu 22.04), default settings. Machine: e2-small
# (e2-micro's 1 GB RAM can be tight installing pandas/numpy).
#
# SECURITY: the token below is stored in the VM's instance metadata (visible to
# anyone with project access) and may appear in serial-console logs. Use a
# FINE-GRAINED token with READ-ONLY access to ONLY this repo, and revoke it
# after the VM is up. (We also scrub it from the on-disk git config below.)
# This box needs NO exchange API keys -- paper trading is read-only.
set -euo pipefail   # NOTE: deliberately no `set -x` so the token isn't echoed

# ============ EDIT THESE TWO ============
GH_USER="YOUR_GITHUB_USERNAME"
GH_TOKEN="YOUR_GITHUB_TOKEN"          # fine-grained PAT, read-only, this repo
# ========================================
REPO="akshaythakur125/perfecttradingstrategy"
BRANCH="claude/repository-overview-pyuhhj"
DEST="/opt/perfecttradingstrategy"
SENTINEL="$DEST/.vm_setup_done"

export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y git python3 python3-pip python3-venv

# Clone once (token only used here, then scrubbed from git config).
if [ ! -d "$DEST/.git" ]; then
  git clone --branch "$BRANCH" \
    "https://${GH_USER}:${GH_TOKEN}@github.com/${REPO}.git" "$DEST"
  git -C "$DEST" remote set-url origin "https://github.com/${REPO}.git"
fi

# Build venv + install deps once (skip on later reboots for fast restart).
if [ ! -f "$SENTINEL" ]; then
  python3 -m venv "$DEST/.venv"
  "$DEST/.venv/bin/pip" install --upgrade pip wheel
  "$DEST/.venv/bin/pip" install -r "$DEST/backend/requirements.txt"
  # Reachability + field-parse check; result saved for you to inspect.
  "$DEST/.venv/bin/python" "$DEST/scripts/verify_bingx.py" \
    > /var/log/bingx_check.log 2>&1 || true
  touch "$SENTINEL"
fi

# Install + start the paper trader as a self-restarting service.
cat >/etc/systemd/system/paper-trader.service <<EOF
[Unit]
Description=Perfect Trading Strategy paper trader
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$DEST
ExecStart=$DEST/.venv/bin/python $DEST/scripts/paper_trade.py \
  --top 60 --min-volume 50000000 --risk 0.02 --max-concurrent 5 --loop 900
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now paper-trader.service
