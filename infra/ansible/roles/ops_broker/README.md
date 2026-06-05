# ops-broker

A narrow, allowlisted operations surface for a host. Hermes (or any MCP client)
can observe service status, read logs, and — where explicitly permitted — restart
services, without ever getting shell access, SSH, or root.

Runs as an unprivileged system user whose only powers come from group membership
(no root, no sudo). All actions are audited to journald.

## Architecture

```
Hermes (MCP client)
  │
  │  HTTP + bearer token
  ▼
ops-broker (streamable-HTTP MCP server)
  │
  │  systemctl / journalctl / docker
  ▼
Host services
```

- **`broker_core`** (`infra/broker_core/`) — generic MCP scaffold: server setup,
  bearer auth, rate limiting, audit logging, subprocess execution. Knows nothing
  about Docker or systemd.
- **`server.py`** (`roles/ops_broker/files/server.py`) — the host-specific tool
  implementations. Translates friendly service names into real `systemctl`,
  `journalctl`, or `docker` commands.
- **`config.json`** (rendered per-host by Ansible) — the allowlist. Maps friendly
  names to real containers/units and controls which services are restartable.

This separation means `broker_core` never changes when a new host or service is
added — only the Ansible inventory and the rendered config change.

## How services are monitored

The broker supports two service sources, reflecting the two ways services run on
the homelab:

### `source: docker` — Docker containers (apps LXC)

Used for services running as Docker containers. The broker user is in the
`docker` group, giving it access to `docker inspect`, `docker logs`, and
`docker restart`.

```yaml
miniflux: {source: docker, target: miniflux-miniflux-1, restartable: true}
```

- **Status**: `docker inspect -f '{{.State.Status}}'`
- **Health**: `docker inspect` returns exit code, OOM state, health check
  result, restart count, timestamps
- **Logs**: `docker logs --tail N`
- **Restart**: `docker restart` (when `restartable: true`)

### `source: journal` — systemd units (any host)

Used for native systemd services and timer-driven oneshots. The broker user is
in the `systemd-journal` group, giving it read access to `systemctl show` and
`journalctl`.

```yaml
restic-backup: {source: journal, target: restic-backup.service, restartable: false}
```

- **Status**: `systemctl is-active`
- **Health**: `systemctl show` returns `ActiveState`, `Result` (success vs
  exit-code), `ExecMainStatus` (exit code), start/finish timestamps, restart
  count. This is especially useful for timer-driven oneshots — the service may
  be `inactive` between runs, but `Result` and `ExecMainStatus` tell you whether
  the last invocation succeeded.
- **Logs**: `journalctl -u <unit> -n N --no-pager`
- **Restart**: `systemctl restart` — not currently exposed. Trigger a re-run
  with `start_service` (oneshot units only) instead.

### Sidecar pattern

Some containers (`audible-ingest`, `kobo-ingest`) are sidecars exec'd by a host
oneshot timer. The container's PID 1 is `tail -f /dev/null` (idle), and the real
work's pass/fail lands in the unit journal. These use `source: journal` so the
broker reports the actual sweep result, not the idle container.

## Tools

| Tool | What it does |
|---|---|
| `list_services` | Returns all managed services with source type, live status, and restartability |
| `service_status` | Quick status check for one service (running/stopped/unknown) |
| `service_health` | Deep health: last run result, exit code, timestamps, restart count, OOM state |
| `get_logs` | Tail logs with optional time window (`since: "30m"`, `"2h"`, `"1d"`) |
| `list_files` | List allowlisted diagnostic files (for state outside journald/docker) |
| `read_file` | Read the tail of an allowlisted file (host path or inside a container volume) |
| `restart_service` | Restart a service (only if `restartable: true`, rate-limited) |
| `start_service` | Start a oneshot unit (only if `triggerable: true`, rate-limited) — used to fire timer-driven sweeps on demand |

## Per-host configuration

Each host defines its own service allowlist and optional file allowlist in the
Ansible inventory (`infra/ansible/inventories/home/hosts.yml`).

### Apps LXC (vmid 103)

```yaml
ops_broker_services:
  calibre-web:    {source: docker,  target: calibre-calibre-web-1,           restartable: true}
  audiobookshelf: {source: docker,  target: audiobookshelf-audiobookshelf-1, restartable: true}
  koinsight:      {source: docker,  target: koinsight-koinsight-1,           restartable: true}
  miniflux:       {source: docker,  target: miniflux-miniflux-1,             restartable: true}
  miniflux-db:    {source: docker,  target: miniflux-db-1,                   restartable: false}
  audible-ingest: {source: journal, target: audible-ingest.service,          restartable: false}
  kobo-ingest:    {source: journal, target: kobo-ingest.service,             restartable: false}
  karakeep:       {source: docker,  target: karakeep-web-1,                  restartable: true}
  karakeep-chrome: {source: docker, target: karakeep-chrome-1,               restartable: true}
  karakeep-meili: {source: docker,  target: karakeep-meilisearch-1,          restartable: false}
ops_broker_files:
  audible-state: {container: audible-ingest-audible-ingest-1, path: /var/lib/audible-ingest/state.json}
```

Groups: `docker`, `systemd-journal` — full Docker access plus journal reads.

### Proxmox host (pve)

```yaml
ops_broker_name: pve-ops
ops_broker_groups: [systemd-journal]
ops_broker_after: "network-online.target"
ops_broker_services:
  restic-backup: {source: journal, target: restic-backup.service, restartable: false}
  caddy:         {source: journal, target: caddy.service,         restartable: false}
  nic-tuning:    {source: journal, target: nic-tuning.service,    restartable: false}
```

No Docker group — journal reads only. No polkit grant, so nothing is restartable.

### Adding a new host

1. Add `ops_broker_services` (and optionally `ops_broker_files`) to the host's
   inventory vars
2. Override `ops_broker_groups`, `ops_broker_after`, `ops_broker_name` as needed
3. Add `ops_broker` role to the host's play in `home.yml`
4. Add the MCP server config in the Hermes role

The same `server.py` and `broker_core` are reused — only the config changes.

## Privilege model

The broker runs as the `opsbroker` system user (`/usr/sbin/nologin`, no home dir).
Its systemd unit sets `NoNewPrivileges=true`, so it cannot gain new privileges
(setuid, file caps) at runtime — any escalation must happen out-of-process.
The broker gets exactly the access it needs through group membership and
polkit, and nothing more:

| Capability | How it's granted |
|---|---|
| Read Docker container status/logs | `docker` group membership |
| Restart Docker containers | `docker` group membership (scoped by allowlist) |
| Read systemd unit status | `systemctl show` works for any user |
| Read journald logs | `systemd-journal` group membership |
| Start systemd units (`start_service`) | polkit rule on `org.freedesktop.systemd1.manage-units`, scoped to `opsbroker` + the specific `triggerable: true` units |

Why polkit and not sudo: the broker unit's `NoNewPrivileges=true` blocks
setuid, which is what `sudo` relies on. Polkit authorises D-Bus calls to
systemd directly — no privilege escalation in the broker process, no
setuid binary, no new-privileges flag to relax. The polkit rule file is
rendered by Ansible from the same `triggerable: true` flag the broker
config already uses, so adding a new triggerable service is one inventory
change.

The allowlist is the critical boundary. Hermes can only name keys that exist in
`ops_broker_services` — it never sees raw container names, unit paths, or file
paths. Unknown service names are rejected and audited.

## Audit trail

Every tool call is logged to journald with the tool name, parameters, and
decision (allow/deny/error):

```bash
journalctl -u ops-broker            # all broker activity
journalctl -u ops-broker -g restart  # restart attempts only
```

On the apps LXC, the broker identity is `apps-ops`. On pve, it's `pve-ops`.

## Deployment

The Ansible role handles everything: user creation, Python 3.14 install via uv
(to `/opt/uv-python`, shared and accessible to the service user), venv creation,
broker_core installation, config rendering, and systemd unit setup.

```bash
make home LIMIT=apps TAGS=ops_broker   # apps LXC
make home LIMIT=pve TAGS=ops_broker    # Proxmox host
```

### Per-host variables

| Variable | Default | Purpose |
|---|---|---|
| `ops_broker_name` | `apps-ops` | Audit identity |
| `ops_broker_groups` | `[docker, systemd-journal]` | Groups for the service user |
| `ops_broker_after` | `network-online.target docker.service` | Systemd unit ordering |
| `ops_broker_services` | `{}` | Service allowlist |
| `ops_broker_files` | `{}` | File allowlist |
| `ops_broker_python_version` | `"3.14"` | Python version (uv-managed) |
| `ops_broker_python_dir` | `/opt/uv-python` | Shared Python install location |
| `ops_broker_port` | `9988` | Listen port |
