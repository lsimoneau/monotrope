---
name: homelab-ops
description: >-
  Diagnose and remediate homelab services via the apps_ops and pve_ops brokers.
  Use when asked to check service health, read logs, diagnose errors, restart
  services, retrigger timer-driven ingests, or troubleshoot connectivity (Caddy,
  Tailscale, DNS). Covers the apps LXC (Calibre-Web, Audiobookshelf, KoInsight,
  Miniflux, ingest jobs) and the PVE host (Caddy reverse proxy, NIC tuning,
  restic backup).
version: 1.1.0
platforms: [linux]
metadata:
  hermes:
    category: homelab
    tags: [ops, logs, homelab, troubleshooting, restart]
    # Only surface this skill when the broker is actually connected.
    requires_toolsets: [apps_ops]
---
# Homelab ops (apps + pve hosts)

The `apps_ops` and `pve_ops` brokers are the **only** way to inspect or
remediate services on those hosts from here. They expose a fixed, allowlisted
menu — no arbitrary shell. Every call is audited. The catalogue of named
services (docker containers + systemd units) and which actions are permitted on
each (read-only / restartable / triggerable) come from the broker config and
are the source of truth.

## Discovering what's available

**Trust the broker, not this skill.** Tool names, parameters, and per-service
capabilities are advertised by the broker itself and can change without this
file being updated. Always:

1. Call `list_services` first to get the current catalogue, exact names, and
   each service's `restartable` / `triggerable` flags. Never assume a name.
2. Read the tool descriptions on `list_services` / `service_status` / `get_logs`
   / `restart_service` / `start_service` (and any others the broker exposes) to
   learn the current parameters and any rate limits.
3. Run `/reload-mcp` if a tool you expect is missing — Hermes caches the
   broker's tool list at gateway startup and only refreshes on demand.

## Procedure

1. `list_services` to get exact names + which are restartable / triggerable.
2. `get_logs` on the relevant service (widen with `since` / `lines` if needed)
   and read the actual error before acting.
3. Pick the right remediation tool — `restart_service` for a long-running
   process that's wedged, `start_service` for a timer-driven oneshot you want
   to fire on demand (ingest sweeps). Respect each service's permission flags
   and the broker's rate limits.
4. Confirm recovery with `service_status` (and a fresh `get_logs` if useful).
5. Report what you saw and what you did — concisely, with the key log lines.

## Pitfalls

- **Never loop remediations.** If one attempt doesn't fix it, stop and tell
  Louis what the logs show — don't keep bouncing the service (the broker
  rate-limits you anyway).
- Services with `restartable: false` (e.g. `miniflux-db` postgres) are
  off-limits by design. Same for `triggerable: false` oneshots — don't try to
  work around it.
- The brokers only manage **apps** and **pve**. They can't see other LXCs.
- Logs are capped/tailed; if you need more history, use `since` rather than
  asking for a huge `lines` value.
- The broker manages containers on a **remote host**, not the current machine.
  Docker / podman / crictl are not available in this terminal. All container
  inspection must go through the broker tools.
- Silent service (no logs but `status: running`): the container's PID 1 may
  emit no stdout/stderr at all, or the log driver may be misrouted. Try
  `get_logs` with a wider `since` window before declaring the broker broken.

## Verification

A remediation worked if `service_status` shows the service running/active (or
the oneshot having finished cleanly) and a fresh `get_logs` is clean. If not,
escalate to Louis with the evidence.
