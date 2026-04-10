# Monotrope

Personal blog and server infrastructure for monotrope.au.

## Theme & Concept

The name is a play on [monotropism](https://en.wikipedia.org/wiki/Monotropism) —
the theory of autistic cognition as deep, singular focus. The site is built around
that idea: deep attention, flow states, and resisting the fragmentation of modern
(especially AI-mediated) work. It's also an exercise in ownership — writing and
reviews live here instead of on corporate platforms.

The tone is personal and reflective. Content includes writing (posts) and book
reviews across all genres.

The terminal/CRT visual aesthetic is deliberate, not just decorative — it
reinforces the themes of simplicity, focus, and rejecting modern web bloat.
No JavaScript unless strictly necessary. No images or decorative elements beyond
CSS. The design should feel minimal, typographic, and monospaced-first.

## Hosting

DigitalOcean droplet, Sydney region, Ubuntu 24.04 LTS.

### What's on the server

- **Hugo static site** — built locally, rsynced to `/var/www/monotrope`
- **Caddy** — reverse proxy and TLS for all services
- **Miniflux** — RSS reader (Docker, PostgreSQL)
- **Gitea** — self-hosted git server (Docker, PostgreSQL, SSH on port 2222)
- **GoatCounter** — privacy-friendly analytics (native binary, SQLite)
- **Hermes Agent** — Nous Research's LLM agent (`nousresearch/hermes-agent`),
  exposed via Telegram bot. Routes through OpenRouter. Used as a personal
  assistant reachable from mobile. Docker, config in `infra/hermes/`.

## Conventions

- All shell scripts use `set -euo pipefail`
- All server changes go through Ansible — no one-off SSH commands
- Ansible tasks must be idempotent
- Australian English in content and comments
- No CI/CD — deploys are manual via `make deploy`
