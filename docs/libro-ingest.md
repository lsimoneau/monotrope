# Libro.fm sync

Plan for adding a `libro_ingest` role to the apps LXC, mirroring
`audible_ingest` so Libro.fm purchases land under `/library/audiobooks`
for Audiobookshelf to scan.

## Status (as of 2026-06-06)

**Working.** A full sweep authenticates, lists the library, downloads
new M4Bs under `/audiobooks/<Author>/<Title>/`, and writes
`state.json` cleanly (`downloaded=N already=0 errors=0`).

Two real bugs were fixed before this; both are still the most likely
failure modes if the role breaks again, so they're documented here:

1. **`User-Agent` + `X-LibroFm-AppVer` required at the ELB.** `librofm`
   (last release 2025-06-16) doesn't send either header, and Libro.fm
   started rejecting every payload shape at the load balancer in late
   2025 — *before* the request ever reaches the OAuth backend. The
   `401` with an empty body that came back was the ELB's
   "you're not a real app" response, not a credential problem. We
   monkey-patch `LibroFMClient.headers` in
   `infra/ansible/roles/libro_ingest/files/libro-ingest` to inject
   `User-Agent: okhttp/5.3.2` and `X-LibroFm-AppVer: 7.34.8` (the
   values reverse-engineered from the official Android client and
   kept in sync with
   [`jedwards1230/libro-client`](https://github.com/jedwards1230/libro-client)'s
   `APIHandler.ts`). Both are env-var overridable
   (`LIBROFM_USER_AGENT`, `LIBROFM_APP_VER`) so the operator can
   rotate them without a code change when Libro.fm bumps the app
   version. **Keep these in sync with the upstream reference if
   Libro.fm rotates them.**

2. **Raw-response logging on auth failure.** A prior fix
   (`e44d8e6 fix(libro_ingest): log raw Libro.fm response on
   auth/API failure`) wrapped `LibroFMClient._do_post` so a non-JSON
   4xx body is logged at WARNING with the status code + first 500
   chars, instead of a useless `JSONDecodeError`. This is what made
   the empty-body 401 above visible in the first place.

A secondary `state.tmp` permission error (the Dockerfile's `mkdir`
ran as root but the container runs as UID 1028) is fixed at the same
time by `chown 1028:1028 /var/lib/libro-ingest` in the Dockerfile —
but that only takes effect on *new* image → new volume. Existing
installs need a one-time host-side chown (see the role README's
"Upgrading an existing install" section).

## Decisions (resolved)

- **Acquisition source**: the `librofm` Python package (PyPI, released
  2025-06-16, MIT, Python 3.10+). Wraps Libro.fm's real OAuth-password
  API (`/oauth/token`, `/api/v7/library`, `/api/v9/download-manifest`,
  `/api/v10/audiobooks/{isbn}/packaged_m4b`). No public OPDS feed was
  found at the usual paths; the private API is the de-facto standard
  and the package is actively maintained.
- **Folder layout**: flat, same as `audible_ingest` —
  `/audiobooks/<Author>/<Title>/`. `librofm` does not auto-organise, so
  the script creates the dir and passes it as `output_dir`.
- **Schedule**: `OnCalendar=*-*-* 06:30:00` (same minute as
  `audible_ingest`; libro-ingest is light enough that contention is
  negligible).
- **State key**: ISBN (int) — `librofm` exposes it as the stable
  per-book identifier.

## Open question

- Stagger the timers? Both at 06:30 is the current default. If strict
  serialisation is preferred, move `libro-ingest.timer` to 06:15.
  Trivial change at deploy time.

## New role: `infra/ansible/roles/libro_ingest/`

```
libro_ingest/
├── defaults/main.yml            # knobs (image, paths, schedule, throttle)
├── tasks/main.yml               # build image, render compose + .env, install unit+timer
├── README.md                    # operator manual (mirrors audible_ingest/README.md)
├── files/
│   ├── Dockerfile               # python:3.12-slim + pip install librofm
│   └── libro-ingest             # the Python sweep
└── templates/
    ├── compose.yml.j2           # tail -f sidecar, env_file picks up .env
    ├── libro-ingest.service.j2  # oneshot, docker exec
    └── libro-ingest.timer.j2    # OnCalendar=*-*-* 06:30:00, Persistent=true
```

### `defaults/main.yml` (proposed knobs)

```yaml
---
libro_ingest_dir: /opt/libro-ingest
libro_ingest_tz: Australia/Sydney
libro_ingest_image: libro-ingest:latest
libro_ingest_audiobooks_path: /library/audiobooks
# Match the audiobookshelf NAS user so files written into /audiobooks
# show up as homelab:homelab on the NAS.
libro_ingest_puid: 1028
libro_ingest_pgid: 1028
# Daily sweep — same cadence as audible_ingest.
libro_ingest_oncalendar: "*-*-* 06:30:00"
# Drip-feed caps. With ~25/day, a 200-book initial library catches up in
# ~8 days; once steady-state, new purchases are 1-2/run and the cap is
# irrelevant. Sleep is jittered uniformly between min and max.
libro_ingest_max_per_run: 25
libro_ingest_sleep_min: 30
libro_ingest_sleep_max: 90
```

### Sweep script (`files/libro-ingest`, ~120 lines)

1. Load `/var/lib/libro-ingest/state.json` (keyed by ISBN).
2. `LibroFMClient(username, password).get_library()` paginated.
3. For each book: skip if `state[isbn].status == "imported"` and folder
   is non-empty; otherwise call `client.download(book, folder)` and
   mark imported. No "not downloadable" branch (every owned book has
   a download URL). No decrypt step.
4. Throttle: `time.sleep(random.uniform(SLEEP_MIN, SLEEP_MAX))` between
   downloads; `MAX_PER_RUN` cap; same env-var contract as
   audible-ingest.
5. Atomic `state.json` write; exit 1 on errors.

### `files/Dockerfile` (proposed)

```dockerfile
FROM python:3.12-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# librofm in an isolated uv venv — same pattern as audible-ingest, so
# future Python bumps don't break it. Deps: requests, pydantic,
# pydantic-settings.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
RUN uv venv /opt/libro-venv \
 && uv pip install --python /opt/libro-venv/bin/python --no-cache librofm \
 && mkdir -p /var/lib/libro-ingest

COPY libro-ingest /opt/libro-venv/bin/libro-ingest
RUN chmod +x /opt/libro-venv/bin/libro-ingest
```

The script's shebang is `#!/opt/libro-venv/bin/python` so it picks up
`librofm` from the venv.

### `templates/compose.yml.j2` (proposed)

```yaml
services:
  libro-ingest:
    image: {{ libro_ingest_image }}
    pull_policy: never
    restart: unless-stopped
    user: "{{ libro_ingest_puid }}:{{ libro_ingest_pgid }}"
    volumes:
      - libro_state:/var/lib/libro-ingest
      - {{ libro_ingest_audiobooks_path }}:/audiobooks
      - ./.env:/var/lib/libro-ingest/.env:ro
    environment:
      TZ: "{{ libro_ingest_tz }}"
    # Long-running so the timer can `docker exec` daily without paying
    # container-start overhead per sweep.
    command: ["tail", "-f", "/dev/null"]

volumes:
  libro_state:
```

### `templates/libro-ingest.service.j2` (proposed)

```ini
[Unit]
Description=Libro.fm→Audiobookshelf ingestion sweep
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
ExecStart=/usr/bin/docker exec \
  -e MAX_PER_RUN={{ libro_ingest_max_per_run }} \
  -e SLEEP_MIN={{ libro_ingest_sleep_min }} \
  -e SLEEP_MAX={{ libro_ingest_sleep_max }} \
  libro-ingest-libro-ingest-1 /opt/libro-venv/bin/libro-ingest
```

### `templates/libro-ingest.timer.j2` (proposed)

```ini
[Unit]
Description=Libro.fm→Audiobookshelf ingestion sweep

[Timer]
OnCalendar={{ libro_ingest_oncalendar }}
Persistent=true

[Install]
WantedBy=timers.target
```

## Auth — vault + rendered .env

`docker exec` does not inherit the container's env, and we don't want
credentials on the systemd unit's command line, so the script reads
`/var/lib/libro-ingest/.env` directly (a 6-line stdlib loader) and
constructs `LibroFMClient(username, password)` explicitly.

- `vault.yml` adds `vault_libro_ingest_username` +
  `vault_libro_ingest_password` (you run `ansible-vault edit` to fill
  values).
- `group_vars/all/vars.yml` indirection lines for the two above.
- `templates/env.j2` (new), rendered to `/opt/libro-ingest/.env` mode
  0600, `no_log: true`, mirroring miniflux's pattern:

  ```
  LIBROFM_USERNAME={{ libro_ingest_username }}
  LIBROFM_PASSWORD={{ libro_ingest_password }}
  ```

- The compose file bind-mounts the host's `/opt/libro-ingest/.env` into
  the container at `/var/lib/libro-ingest/.env:ro`.

## Wiring changes

| File | Change |
|---|---|
| `infra/ansible/home.yml` | Add `role: libro_ingest` to apps LXC roles (right after `audible_ingest`) |
| `infra/ansible/inventories/home/hosts.yml` | `ops_broker_services`: `libro-ingest: {source: journal, target: libro-ingest.service, restartable: false}` (same pattern as audible). `ops_broker_files`: `libro-state: {container: libro-ingest-libro-ingest-1, path: /var/lib/libro-ingest/state.json}` |
| `infra/ansible/group_vars/all/vault.yml` | Add `vault_libro_ingest_username` + `vault_libro_ingest_password` |
| `infra/ansible/group_vars/all/vars.yml` | Indirection lines for the two above |
| `infra/ansible/roles/restic_backup/defaults/main.yml` | New backup set `libro-ingest` (vmid 103, `var/lib/docker/volumes/libro-ingest_libro_state/_data`, tags `[libro-ingest, critical, apps]`) — only the state volume, no config volume |

## What changes vs. audible_ingest

| | audible_ingest | libro_ingest |
|---|---|---|
| Image deps | ffmpeg + audible-cli + uv venv | librofm in uv venv |
| Container size | ~500 MB | ~200 MB |
| Auth | Interactive OAuth (`audible quickstart`) in named volume | Username/password in rendered .env |
| Decryption | AAXC voucher + AAX activation bytes | None (DRM-free) |
| Per-book state key | ASIN | ISBN (int) |
| Skipped-status logic | Yes (Plus catalogue streaming-only) | No |
| Volumes | `audible_config` + `audible_state` | `libro_state` only |

## Deploy

```sh
ansible-vault edit infra/ansible/group_vars/all/vault.yml  # add the two values
make home LIMIT=apps TAGS=libro_ingest
```

The first sweep runs at the next 06:30 (or on `systemctl start
libro-ingest.service` for an immediate one-off).

## Operator notes (for the role README)

- Inspect state: `docker exec libro-ingest-libro-ingest-1 cat /var/lib/libro-ingest/state.json | jq`
- Re-run a single book: delete its ISBN entry from `state.json`, then
  `systemctl start libro-ingest.service`.
- Force re-import: set `"status": "pending"` (or just delete the
  entry).
- Change password: `ansible-vault edit` to update the password, then
  `make home LIMIT=apps TAGS=libro_ingest` to re-render `.env` and
  recreate the container.
