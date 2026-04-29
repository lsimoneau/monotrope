#!/usr/bin/env bash
set -euo pipefail

# deploy.sh — Build and deploy monotrope.au to the production droplet

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

MONOTROPE_HOST="${MONOTROPE_HOST:-}"
DEPLOY_USER="deploy"
REMOTE_DIR="/var/www/monotrope"

# Fall back to reading the host from group_vars when invoked directly
# (without `make`, which would already have exported it).
if [[ -z "$MONOTROPE_HOST" ]]; then
  VARS_FILE="$SCRIPT_DIR/infra/ansible/group_vars/all/vars.yml"
  if [[ -f "$VARS_FILE" ]]; then
    MONOTROPE_HOST=$(awk -F': *' '/^monotrope_host:/ {gsub(/[" ]/, "", $2); print $2}' "$VARS_FILE")
  fi
fi

if [[ -z "$MONOTROPE_HOST" ]]; then
  echo "Error: MONOTROPE_HOST is not set and could not be read from group_vars."
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
