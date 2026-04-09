# Monotrope

Personal blog and server infrastructure for monotrope.au.

## Project Structure

```
monotrope/
  site/                    # Hugo site (content, templates, CSS)
  infra/
    ansible/playbook.yml   # Single playbook for all server provisioning
    miniflux/              # Docker Compose for Miniflux RSS reader
    Caddyfile              # Copied to /etc/caddy/Caddyfile by Ansible
  deploy.sh                # Build + rsync to production
  Makefile                 # Common tasks
  .env                     # Local secrets (not committed)
```

## Tech Stack

- **Static site generator:** Hugo (no theme — templates built from scratch)
- **Web server:** Caddy (automatic HTTPS via Let's Encrypt)
- **Hosting:** DigitalOcean droplet (Sydney region, Ubuntu 24.04 LTS)
- **Deployment:** `hugo --minify` then `rsync` to `/var/www/monotrope`
- **Provisioning:** Ansible (`infra/ansible/playbook.yml`)

## Services

| Service     | URL                         | How it runs     | Port |
|-------------|-----------------------------|-----------------|------|
| Blog        | https://monotrope.au        | Static files    | —    |
| Miniflux    | https://reader.monotrope.au | Docker Compose  | 8080 |
| GoatCounter | https://stats.monotrope.au  | systemd binary  | 8081 |

## Ansible Playbook

**All server changes must go through Ansible.** Everything must be idempotent — no ad-hoc SSH changes.

The playbook is at `infra/ansible/playbook.yml`. Tags let individual services be re-provisioned without touching the rest.

| Tag           | What it covers                                       |
|---------------|------------------------------------------------------|
| `miniflux`    | Miniflux Docker Compose + Caddyfile update           |
| `goatcounter` | GoatCounter binary, systemd service + Caddyfile      |
| (no tag)      | Full provisioning (system, Caddy, Docker, UFW, users)|

### Secrets

Pulled from environment variables, loaded from `.env` via Makefile:

```
MONOTROPE_HOST
MINIFLUX_DB_PASSWORD
MINIFLUX_ADMIN_USER
MINIFLUX_ADMIN_PASSWORD
GOATCOUNTER_ADMIN_EMAIL
GOATCOUNTER_ADMIN_PASSWORD
```

### GoatCounter

Runs as a systemd service (not Docker) using the pre-built binary from GitHub releases.
Version is pinned via `goatcounter_version` var in the playbook.
Initial site/user creation is gated on a `/var/lib/goatcounter/.admin_created` marker file
so re-running the playbook never attempts to recreate the user.

## Makefile Targets

```
make build        # hugo --minify
make serve        # hugo server --buildDrafts (local dev)
make deploy       # build + rsync to production
make ssh          # SSH as deploy user
make setup        # Full Ansible provisioning (fresh droplet)
make miniflux     # Ansible --tags miniflux
make goatcounter  # Ansible --tags goatcounter
```

## DNS

- `monotrope.au` → droplet IP (A record)
- `www.monotrope.au` → droplet IP (A record, redirects to apex via Caddy)
- `reader.monotrope.au` → droplet IP (A record)
- `stats.monotrope.au` → droplet IP (A record)

## Site Layout

Content lives in `site/content/`:
- `posts/` — writing
- `reviews/` — book reviews
- `about.md` — about page (uses `layouts/page/single.html`)

Templates are in `site/layouts/`. No JavaScript unless strictly necessary.
The GoatCounter analytics script is injected in `baseof.html` and only loads
in production builds (`hugo.IsProduction`).

## Conventions

- All shell scripts use `set -euo pipefail`
- All server changes go through Ansible — no one-off SSH commands
- Ansible tasks must be idempotent
- Australian English in content and comments
- No CI/CD — deploys are manual via `make deploy`
