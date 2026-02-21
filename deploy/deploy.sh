#!/bin/bash
# Deploy BOSS to Raspberry Pi
# Usage: ./deploy/deploy.sh [hostname]
#   e.g. ./deploy/deploy.sh boss.local

set -euo pipefail

PI_HOST="${1:-boss.local}"
PI_USER="pi"
REMOTE_DIR="/opt/boss"

echo "==> Deploying BOSS to ${PI_USER}@${PI_HOST}:${REMOTE_DIR}"

rsync -avz --delete \
  --exclude '.venv' \
  --exclude '__pycache__' \
  --exclude '.git' \
  --exclude 'secrets/secrets.env' \
  --exclude 'logs/' \
  --exclude '.ruff_cache' \
  --exclude '*.pyc' \
  . "${PI_USER}@${PI_HOST}:${REMOTE_DIR}/"

echo "==> Installing dependencies"
ssh "${PI_USER}@${PI_HOST}" "cd ${REMOTE_DIR} && .venv/bin/pip install -e '.[pi]' --quiet"

echo "==> Restarting services"
ssh "${PI_USER}@${PI_HOST}" "sudo systemctl restart boss boss-kiosk"

echo "==> Done. Check status with: ssh ${PI_USER}@${PI_HOST} 'systemctl status boss'"
