# Monotrope

Personal blog and server infrastructure for monotrope.au.

## Project Structure

```
monotrope/
  site/           # Hugo site (content, templates, config)
  infra/          # Server setup scripts and config files
  deploy.sh       # Build + rsync to production
  Makefile        # Common tasks
```

## Tech Stack

- **Static site generator:** Hugo
- **Web server:** Caddy (automatic HTTPS via Let's Encrypt)
- **Hosting:** DigitalOcean droplet (Sydney region, Ubuntu 24.04 LTS)
- **Deployment:** `hugo build` then `rsync` to server
- **Future services:** Docker Compose for anything beyond the blog

## Setup Tasks

### 1. Initialise the repo

- Create the directory structure above
- `git init` with a sensible `.gitignore` (Hugo output dir `public/`, `.env`, etc.)
- Initialise a new Hugo site inside `site/`
- Use a minimal theme or no theme — we'll build templates from scratch later
- Hugo config should set `baseURL = "https://monotrope.au"`

### 2. Create a minimal Hugo site

- A single layout (`layouts/_default/baseof.html`, `single.html`, `list.html`)
- Minimal, clean CSS — no framework. Readable prose typography, dark mode support via `prefers-color-scheme`
- A sample first post in `site/content/posts/` so we can test the build
- RSS feed enabled (Hugo does this by default)
- No JavaScript unless strictly necessary

### 3. Server provisioning script

Create `infra/setup.sh` — a bash script intended to be run once on a fresh Ubuntu 24.04 droplet via SSH. It should:

- Update packages
- Install Caddy via the official apt repo
- Create a `www` user with no login shell to own the site files
- Create `/var/www/monotrope` owned by `www`
- Install a Caddyfile at `/etc/caddy/Caddyfile` that:
  - Serves `monotrope.au` from `/var/www/monotrope`
  - Enables gzip/zstd compression
  - Sets sensible cache headers for static assets
  - Handles `www.monotrope.au` redirect to apex
- Enable and start the Caddy service
- Set up UFW: allow SSH, HTTP, HTTPS, deny everything else
- Install Docker and Docker Compose (for future use, not needed yet)
- Create a deploy user with SSH key auth and permission to write to `/var/www/monotrope`

Also create `infra/Caddyfile` as a standalone config file that the setup script copies into place.

### 4. Deploy script

Create `deploy.sh` at the repo root:

- Run `hugo --minify` in `site/`
- `rsync -avz --delete site/public/ deploy@<DROPLET_IP>:/var/www/monotrope/`
- Print the URL on success

The droplet IP should come from an environment variable `MONOTROPE_HOST` or a `.env` file (not committed).

### 5. Makefile

Targets:
- `make build` — build the site locally
- `make serve` — `hugo server` for local dev with live reload
- `make deploy` — run `deploy.sh`
- `make ssh` — SSH into the droplet as the deploy user
- `make setup` — run the provisioning script on a fresh droplet

## Conventions

- All shell scripts should use `set -euo pipefail`
- Prefer clarity over cleverness in all scripts
- No unnecessary dependencies — this should stay simple
- Australian English in all content and comments
- Markdown content lives in `site/content/`; one subdirectory per content type (e.g. `posts/`, `pages/`)

## DNS

The user will configure DNS separately via their registrar. The server expects:
- `monotrope.au` → droplet IP (A record)
- `www.monotrope.au` → droplet IP (A record)

Caddy will handle certificate provisioning automatically once DNS is pointed.

## What This Is Not

- No CI/CD pipeline — deploy is manual via `make deploy`
- No containerisation of the blog itself — it's static files
- No database
- No analytics (for now)
- No comments system (for now)
