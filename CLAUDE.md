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

- **Public site** (`monotrope.au`) — Hugo static site on Cloudflare Pages,
  auto-built and deployed on push to `main`. Cloudflare Web Analytics is
  injected at the edge (no template hook).
- **Personal services** — run on the OptiPlex 7090 homelab (Proxmox VE,
  several LXCs + a Home Assistant VM), reachable over Tailscale via
  `*.monotrope.au` (wildcard CNAME → Proxmox tailscale0). Caddy on the
  Proxmox host terminates TLS with a wildcard cert via Cloudflare DNS-01.

### What runs where

- **Cloudflare Pages**: Hugo static site, www → apex redirect.
- **`apps` LXC** (192.168.0.97): Calibre-Web, Audiobookshelf, KoInsight,
  Miniflux (with its own Postgres). Reachable as
  `{calibre,abs,koinsight,reader}.monotrope.au` via Caddy on Proxmox.
- **`hermes` LXC** (192.168.0.96): Hermes Agent (native install, not Docker)
  — Telegram + email gateways, MCP servers, browser automation sandbox.
- **`jellyfin` LXC**, **`media-stack` LXC**: media playback + acquisition.
- **HAOS VM**: Home Assistant.

## Conventions

- All shell scripts use `set -euo pipefail`
- All server changes go through Ansible — no one-off SSH commands
- Ansible tasks must be idempotent
- Australian English in content and comments
- Hugo deploys via Cloudflare Pages on push to `main`; `make build` /
  `make serve` are local-preview only
- Home services deploy via `make home` (optionally `LIMIT=...`, `TAGS=...`)
