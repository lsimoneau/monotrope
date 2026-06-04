#!/usr/bin/env bash
# vault-add.sh — append a placeholder key to the Ansible Vault.
# The user runs `ansible-vault edit` afterwards to fill the real value.
#
# Usage: vault-add.sh KEY [VAULT_PATH]
#   KEY       must start with the `vault_` prefix
#   VAULT_PATH defaults to infra/ansible/group_vars/all/vault.yml
#
# Decrypts to a mktemp -d directory; the temp file is shredded and the
# directory removed on exit, so plaintext never touches persistent
# storage beyond the brief decrypt window.
#
# Exit codes: ansible-vault's, 2 for argument errors.

set -euo pipefail

KEY="${1:?usage: vault-add.sh vault_<service>_<thing> [VAULT_PATH]}"
VAULT="${2:-infra/ansible/group_vars/all/vault.yml}"

if [[ "$KEY" != vault_* ]]; then
  echo "refusing to add '$KEY': expected 'vault_' prefix" >&2
  exit 2
fi

if [[ ! -f "$VAULT" ]]; then
  echo "vault not found: $VAULT" >&2
  exit 2
fi

TMP=$(mktemp -d)
# shellcheck disable=SC2064
trap "shred -u '$TMP/plain' 2>/dev/null || true; rm -rf '$TMP'" EXIT

ansible-vault view --vault-password-file .vault_pass "$VAULT" > "$TMP/plain"
printf '%s: ""\n' "$KEY" >> "$TMP/plain"
ansible-vault encrypt --vault-password-file .vault_pass \
  --output "$VAULT" "$TMP/plain"

echo "added $KEY (placeholder) — fill the value with:"
echo "  ansible-vault edit --vault-password-file .vault_pass $VAULT"
