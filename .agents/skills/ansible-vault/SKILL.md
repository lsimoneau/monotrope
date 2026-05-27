---
name: ansible-vault
description: Use when you need to read or search the Ansible Vault contents in this project. Triggers on mentions of vault, secrets, encrypted vars, or vault.yml. Uses the project's .vault_pass file to decrypt.
---

# Ansible Vault Reader

The project stores encrypted secrets in `infra/ansible/group_vars/all/vault.yml` (Ansible Vault format). A vault password file exists at `.vault_pass` in the project root.

## Reading the vault

To decrypt and view the full vault:

```bash
ansible-vault view --vault-password-file .vault_pass infra/ansible/group_vars/all/vault.yml
```

This must be run from the project root directory (`/home/louis/code/monotrope`).

## Searching the vault

To search for a specific key or pattern without exposing the full contents:

```bash
ansible-vault view --vault-password-file .vault_pass infra/ansible/group_vars/all/vault.yml | grep -i <pattern>
```

## Listing key names only

To see only the top-level variable names (values redacted):

```bash
ansible-vault view --vault-password-file .vault_pass infra/ansible/group_vars/all/vault.yml | grep -v '^\s*$' | grep -v '^\s*#' | sed 's/: .*/: <redacted>/'
```

## Important

- Never output raw secret values to the user unless they explicitly ask for them.
- The vault password file (`.vault_pass`) is in `.gitignore` and must never be committed.
- Always use `--vault-password-file .vault_pass` rather than interactive password entry.
- Run commands with `workdir="/home/louis/code/monotrope"` since the `.vault_pass` path is relative.
