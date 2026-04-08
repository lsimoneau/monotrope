#!/usr/bin/env bash
set -euo pipefail

# deploy.sh — Build and deploy monotrope.au to the production droplet

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load .env if present
if [[ -f "$SCRIPT_DIR/.env" ]]; then
  # shellcheck disable=SC1091
  source "$SCRIPT_DIR/.env"
fi

MONOTROPE_HOST="${MONOTROPE_HOST:-}"
DEPLOY_USER="deploy"
REMOTE_DIR="/var/www/monotrope"

if [[ -z "$MONOTROPE_HOST" ]]; then
  echo "Error: MONOTROPE_HOST is not set."
  echo "Set it in your environment or in a .env file at the repo root."
  exit 1
fi

echo "==> Building site"
cd "$SCRIPT_DIR/site"
hugo --minify

echo "==> Deploying to ${DEPLOY_USER}@${MONOTROPE_HOST}:${REMOTE_DIR}"
rsync -avz --delete "$SCRIPT_DIR/site/public/" \
  "${DEPLOY_USER}@${MONOTROPE_HOST}:${REMOTE_DIR}/"

echo ""
echo "==> Done. Live at https://monotrope.au"
