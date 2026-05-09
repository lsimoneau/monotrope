# monotrope

Personal blog and server infrastructure for monotrope.au. Hugo site on
Cloudflare Pages plus a fleet of self-hosted services on a homelab
Proxmox host, all provisioned via Ansible. Background and conventions
live in `CLAUDE.md`.

## Running services

Public site (`monotrope.au`) is Hugo on Cloudflare Pages. Everything
else runs on the OptiPlex Proxmox host and is reverse-proxied by Caddy
on `pve` (binds tailscale `100.88.127.39` + LAN `192.168.0.59`).
Wildcard `*.monotrope.au` resolves to the tailscale address.

| Host        | VMID | LAN IP         | Service        | Port  | URL                               |
| ----------- | ---- | -------------- | -------------- | ----- | --------------------------------- |
| pve         | —    | 192.168.0.59   | Proxmox VE     | 8006  | —                                 |
| pve         | —    | 192.168.0.59   | Caddy (HTTPS)  | 443   | (reverse proxy front door)        |
| haos (VM)   | 100  | 192.168.0.86   | Home Assistant | 8123  | —                                 |
| jellyfin    | 101  | 192.168.0.99   | Jellyfin       | 8096  | jellyfin.monotrope.au             |
| media-stack | 102  | 192.168.0.98   | qBittorrent    | 8080  | qbit.monotrope.au                 |
| media-stack | 102  | 192.168.0.98   | Sonarr         | 8989  | sonarr.monotrope.au               |
| media-stack | 102  | 192.168.0.98   | Radarr         | 7878  | radarr.monotrope.au               |
| media-stack | 102  | 192.168.0.98   | Lidarr         | 8686  | lidarr.monotrope.au               |
| media-stack | 102  | 192.168.0.98   | Prowlarr       | 9696  | prowlarr.monotrope.au             |
| apps        | 103  | 192.168.0.97   | Calibre-Web    | 8083  | calibre.monotrope.au              |
| apps        | 103  | 192.168.0.97   | Audiobookshelf | 13378 | abs.monotrope.au                  |
| apps        | 103  | 192.168.0.97   | KoInsight      | 3001  | koinsight.monotrope.au            |
| apps        | 103  | 192.168.0.97   | Miniflux       | 8080  | reader.monotrope.au               |
| apps        | 103  | 192.168.0.97   | audible-ingest | —     | (cron sidecar; Audible → ABS)     |
| apps        | 103  | 192.168.0.97   | kobo-ingest    | —     | (cron sidecar; Kobo → calibre)    |
| hermes      | 104  | 192.168.0.96   | Hermes Agent   | —     | (Telegram + email gateways)       |

Library content (`/library/{books,audiobooks,…}`) lives on the NAS at
`192.168.0.49` and is NFS-mounted into the LXCs that need it.

Source of truth: `infra/ansible/inventories/home/hosts.yml` for IPs and
`infra/ansible/inventories/home/group_vars/proxmox_hosts.yml` for the
Caddy site → upstream map.

## Local prerequisites

For applying changes from this checkout:

- `ansible` — the playbook lives in `infra/ansible/`
- `hugo` — local preview only; Cloudflare Pages builds and deploys on
  push to `main`
- `make`, `ssh`, `git`
- An SSH key that matches `authorized_keys` on `root@pve` and the LXCs

The vault password decrypts `infra/ansible/group_vars/all/vault.yml`.
Stored in 1Password as "monotrope ansible vault"; write it to
`.vault_pass` at the repo root (gitignored), `chmod 600`:

```sh
op read "op://Personal/monotrope ansible vault/password" > .vault_pass
chmod 600 .vault_pass
```

The Makefile exports `ANSIBLE_VAULT_PASSWORD_FILE=.vault_pass`, so
every `ansible-playbook` call picks it up automatically.

## Working with it

```sh
make build                   # hugo --minify (local preview)
make serve                   # hugo server with drafts
make home                    # apply the whole homelab playbook
make home LIMIT=apps         # scope to one host or group
make enrich                  # backfill ISBN/cover for book reviews
```

`make home` is idempotent — re-running it just verifies state.
`LIMIT=` accepts any host pattern from the inventory; `TAGS=` is
plumbed through but no role currently sets ansible tags.

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
