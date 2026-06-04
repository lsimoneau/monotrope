# libro_ingest

Libro.fm → Audiobookshelf ingestion sidecar. Runs on the **apps** LXC
(`192.168.0.97`) as a long-lived container
(`libro-ingest-libro-ingest-1`) so a host-side systemd timer can
`docker exec` the sweep daily without paying container-start overhead.

The sweep lists the Libro.fm library via the `librofm` package,
downloads anything missing under `/audiobooks/<Author>/<Title>/`, and
writes state to `/var/lib/libro-ingest/state.json` keyed by ISBN. The
loop is idempotent across runs.

Format handling:

- **M4B preferred** — `librofm` first asks for the packaged M4B and
  falls back to a per-part MP3 manifest. Both arrive as DRM-free
  downloads.
- **Folder contains `*.m4b` or `*.mp3`** — `looks_complete()` returns
  True and the loop skips the book on subsequent sweeps. A folder
  with non-audio residue is treated as incomplete and wiped before
  re-downloading (librofm's skip-if-exists would otherwise leave
  partial files in place).

## First-time auth (once per install)

`librofm` uses Libro.fm's OAuth password flow. The credentials are
rendered to `/opt/libro-ingest/.env` from the vault at deploy time.

Add them to the vault and re-run the role:

```bash
ansible-vault edit infra/ansible/group_vars/all/vault.yml
make home LIMIT=apps TAGS=libro_ingest
```

The `.env` is bind-mounted into the container at
`/var/lib/libro-ingest/.env:ro`, and the script reads it explicitly
on each sweep.

## Manually trigger a sweep

Fire the systemd unit (uses the timer's env vars — `MAX_PER_RUN=25`,
jitter 30–90s):

```bash
ssh root@192.168.0.97 systemctl start libro-ingest.service
journalctl -u libro-ingest.service -f
```

Or run the script directly with custom throttle, e.g. one book, no
sleep:

```bash
ssh root@192.168.0.97 \
  docker exec -e MAX_PER_RUN=1 -e SLEEP_MIN=0 -e SLEEP_MAX=0 \
    libro-ingest-libro-ingest-1 /opt/libro-venv/bin/libro-ingest
```

Unset `MAX_PER_RUN` (or set it empty) to drain the whole library —
but the daily 25-cap exists for a reason, so prefer the timer for
bulk imports.

## Inspect / debug

```bash
# What's the timer doing?
ssh root@192.168.0.97 systemctl list-timers libro-ingest.timer

# State (per-ISBN status: imported / pinned)
ssh root@192.168.0.97 \
  docker exec libro-ingest-libro-ingest-1 \
    cat /var/lib/libro-ingest/state.json | jq
```

## Knobs

Defaults live in `defaults/main.yml`:

- `libro_ingest_max_per_run: 25` — drip-feed cap per sweep
- `libro_ingest_sleep_min/max: 30/90` — jittered inter-download sleep
- `libro_ingest_oncalendar: "*-*-* 06:30:00"` — timer cadence

Change those, then `make home LIMIT=apps TAGS=libro_ingest` to
redeploy.

## Pinning a book to skip it

If a title is mis-tagged on Libro.fm (or you don't want it ingested),
edit `state.json` and set `"status": "pinned"` for the ISBN. The
`TERMINAL` set in `files/libro-ingest` includes `pinned`, so the loop
will skip it as long as the folder exists and contains an audio file.

## Re-downloading a book

Delete its ISBN entry from `state.json` (or set `"status":
"pending"`) and re-run the sweep. The script will wipe any partial
files in the folder and download fresh.
