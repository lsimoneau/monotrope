# monotrope

Personal blog and server infrastructure for monotrope.au. Hugo site,
Caddy, plus a handful of personal services (Miniflux, Gitea, Hermes
agent, Calibre, KoInsight, Wallabag, Obsidian sync) provisioned via
Ansible. Background and conventions live in `CLAUDE.md`.

## First setup

On a fresh machine cloning this repo for the first time:

1. **Install prerequisites.**
   - `ansible` (provides `ansible-playbook` and `ansible-vault`)
   - `hugo` — for building the site
   - `rsync` — for `make deploy`
   - `docker` — only if you'll run `make calibre-build`
   - An SSH key at `~/.ssh/id_ed25519.pub`. The playbook reads this
     and installs it as the `deploy` user's authorized key.

2. **Drop the vault password.** The encrypted secrets in
   `infra/ansible/group_vars/all/vault.yml` are unlocked by a single
   passphrase stored in 1Password under "monotrope ansible vault".
   Write it to `.vault_pass` at the repo root:

   ```sh
   op read "op://Personal/monotrope ansible vault/password" > .vault_pass
   chmod 600 .vault_pass
   ```

   Or paste it manually. The Makefile exports
   `ANSIBLE_VAULT_PASSWORD_FILE=.vault_pass`, so every
   `ansible-playbook` call picks it up automatically. The file is
   gitignored.

3. **Confirm SSH to the host works.** `make setup` runs as root, so
   `ssh root@<host>` needs to succeed. The host IP comes from
   `infra/ansible/group_vars/all/vars.yml` (`monotrope_host`); both
   the Makefile and `deploy.sh` derive it from there.

That's it. `make setup` provisions the whole server idempotently;
individual services have their own tag (`make miniflux`, `make hermes`,
etc.). `make deploy` builds and rsyncs the static site.

## Editing secrets

```sh
ansible-vault edit infra/ansible/group_vars/all/vault.yml
```

Decrypts to a tempfile, opens `$EDITOR`, re-encrypts on save. Don't
decrypt-then-edit-then-re-encrypt by hand — too easy to commit a
plaintext copy.

To rotate the vault password:

```sh
ansible-vault rekey infra/ansible/group_vars/all/vault.yml
# then update .vault_pass and the 1Password entry to match
```
