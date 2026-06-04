---
name: ansible-vault
description: Use when you need to read or search the Ansible Vault contents in this project. Triggers on mentions of vault, secrets, encrypted vars, or vault.yml. Uses the project's .vault_pass file to decrypt.
---

# Ansible Vault — safe inspection

The project stores encrypted secrets in
`infra/ansible/group_vars/all/vault.yml` (Ansible Vault format). A
vault password file exists at `.vault_pass` in the project root.

## CRITICAL — never let raw secret values reach stdout

Anything you print to a `bash` tool call lands in the session log
permanently. **Never** run `ansible-vault view` against the file and
let its output reach stdout in a tool result.

- The "list keys" pattern is always redacted — values become
  `<redacted>` before they leave your process.
- To confirm a key exists or check its format, use the
  redacted-grep pattern below. The shape, not the value.
- If you genuinely need to see a plaintext secret, stop and ask the
  user to confirm in writing. The user runs `ansible-vault view`
  themselves locally if they need to copy a value somewhere.
- This rule has no exception for "just verifying" or "it'll be in the
  log anyway" — once printed, it's printed.

## Listing keys (default — redacted)

Use the helper. It pipes through `sed` so values never reach stdout
even if the underlying `view` succeeds:

```bash
./.agents/skills/ansible-vault/scripts/vault-list.sh
```

Equivalent one-liner (if the helper isn't available):

```bash
ansible-vault view --vault-password-file .vault_pass \
  infra/ansible/group_vars/all/vault.yml \
  | grep -vE '^\s*$|^\s*#' \
  | sed 's/: .*/: <redacted>/'
```

## Searching for a specific key (redacted)

```bash
ansible-vault view --vault-password-file .vault_pass \
  infra/ansible/group_vars/all/vault.yml \
  | grep -E '^vault_hermes_telegram_bot_token' \
  | sed 's/: .*/: <redacted>/'
```

## Adding a new key

Use the helper. It decrypts to a `mktemp -d` directory that gets
shredded on exit; the operator then runs `ansible-vault edit` to
fill the real value:

```bash
./.agents/skills/ansible-vault/scripts/vault-add.sh vault_libro_ingest_username
```

Equivalent manual workflow (same hygiene):

```bash
TMP=$(mktemp -d)
trap 'shred -u "$TMP/plain" 2>/dev/null || true; rm -rf "$TMP"' EXIT
ansible-vault view --vault-password-file .vault_pass \
  infra/ansible/group_vars/all/vault.yml > "$TMP/plain"
printf 'vault_libro_ingest_username: ""\n' >> "$TMP/plain"
ansible-vault encrypt --vault-password-file .vault_pass \
  --output infra/ansible/group_vars/all/vault.yml "$TMP/plain"
```

## Editing an existing key (user-driven, never agent-driven)

```bash
ansible-vault edit --vault-password-file .vault_pass \
  infra/ansible/group_vars/all/vault.yml
```

This is interactive by design — an agent should not be modifying
secrets without the user at the keyboard.

## Verification: did anything leak?

The simplest check is to grep the session log for known secret
shapes. If the user ever asks you to inspect a recent session for
leaks, don't use `vault view` for the audit — use
`scripts/vault-list.sh` (always redacted) and ask the user to share
the suspect log snippet separately.

## Important

- `.vault_pass` is in `.gitignore`; never commit it.
- Always use `--vault-password-file .vault_pass` (no interactive
  password entry — that path is logged).
- Run commands with `workdir="/home/louis/code/monotrope"` so the
  relative `.vault_pass` path resolves.
- The helper scripts under `scripts/` always redact, even when their
  internal `ansible-vault view` call produces plaintext — that output
  goes to a tempfile, never to stdout.
