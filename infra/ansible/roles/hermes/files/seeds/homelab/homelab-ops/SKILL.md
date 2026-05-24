---
name: homelab-ops
description: >-
  View logs and run known-safe remediations for the apps on the homelab via the
  apps_ops broker. Use when asked to check whether a service is healthy, read its
  logs, diagnose an error, or restart a service on the apps host (Calibre-Web,
  Audiobookshelf, KoInsight, Miniflux, ingest jobs).
version: 1.0.0
platforms: [linux]
metadata:
  hermes:
    category: homelab
    tags: [ops, logs, homelab, troubleshooting, restart]
    # Only surface this skill when the broker is actually connected.
    requires_toolsets: [apps_ops]
---
# Homelab ops (apps host)

The `apps_ops` broker exposes a **fixed, allowlisted** menu for the apps LXC. You
cannot run arbitrary commands through it — only the four tools below, against a
catalogue of named services. Every call is audited.

## When to use
- Louis asks if an app is up / healthy, or reports something is broken.
- You need to read a service's logs to diagnose an error.
- A known-safe restart is warranted.

## Tools
- `mcp_apps_ops_list_services` — the catalogue: each service's type, live status,
  and whether it may be restarted. **Always start here** — never assume a name.
- `mcp_apps_ops_service_status` — current status of one service.
- `mcp_apps_ops_get_logs` — recent logs. Args: `service` (a catalogue name),
  `lines` (default 100, capped), `since` (optional relative window like `30m`,
  `2h`, `1d`).
- `mcp_apps_ops_restart_service` — restart a service, **only** if its catalogue
  entry says `restartable: true`. Rate-limited.

## Procedure
1. `list_services` to get exact names + which are restartable.
2. `get_logs` on the relevant service (widen with `since`/`lines` if needed) and
   read for the actual error before acting.
3. If a restart is clearly warranted **and** the service is restartable, call
   `restart_service`, then confirm recovery with `service_status` (and a fresh
   `get_logs` if useful).
4. Report what you saw and what you did — concisely, with the key log lines.

## Pitfalls
- **Never loop restarts.** If one restart doesn't fix it, stop and tell Louis what
  the logs show — don't keep bouncing the service (the broker rate-limits you
  anyway).
- Services with `restartable: false` (e.g. `miniflux-db` postgres, the ingest
  jobs) are off-limits by design — don't try to work around it.
- The broker only manages the **apps** host. It can't see other LXCs.
- Logs are capped/tailed; if you need more history, use `since` rather than asking
  for a huge `lines` value.

## Verification
A remediation worked if `service_status` shows the service running/active and a
fresh `get_logs` is clean. If not, escalate to Louis with the evidence.
