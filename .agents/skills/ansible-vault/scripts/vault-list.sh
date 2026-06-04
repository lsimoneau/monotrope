#!/usr/bin/env bash
# vault-list.sh — list Ansible Vault keys; values are always redacted
# so the output is safe to print to a session log.
#
# Usage: vault-list.sh [VAULT_PATH]
#   VAULT_PATH defaults to infra/ansible/group_vars/all/vault.yml
#
# Exit codes: ansible-vault's, or 2 if args are wrong.

set -euo pipefail

VAULT="${1:-infra/ansible/group_vars/all/vault.yml}"

if [[ ! -f "$VAULT" ]]; then
  echo "vault not found: $VAULT" >&2
  exit 2
fi

ansible-vault view --vault-password-file .vault_pass "$VAULT" \
  | grep -vE '^\s*$|^\s*#' \
  | sed 's/: .*/: <redacted>/'
