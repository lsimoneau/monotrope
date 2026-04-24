#!/bin/sh
set -eu

# First-run: register the local /vault path against the remote vault.
# Idempotent: ob sync-list-local lists already-configured local paths.
if ! ob sync-list-local 2>/dev/null | grep -q "/vault"; then
  echo "Registering /vault with remote vault \"$OBSIDIAN_VAULT_NAME\"..."
  ob sync-setup \
    --vault "$OBSIDIAN_VAULT_NAME" \
    --path /vault \
    --config-dir .obsidian-headless
fi

exec ob sync --continuous --path /vault
