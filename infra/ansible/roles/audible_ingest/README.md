# audible_ingest

Audible → Audiobookshelf ingestion sidecar. Runs on the **apps** LXC
(`192.168.0.97`) as a long-lived container (`audible-ingest-audible-ingest-1`)
so a host-side systemd timer can `docker exec` the sweep daily without paying
container-start overhead.

The sweep lists the Audible library via `audible-cli`, downloads anything
missing under `/audiobooks/<Author>/<Title>/`, decrypts it, and writes state to
`/var/lib/audible-ingest/state.json` keyed by ASIN.

Format handling:

- **AAXC** is preferred (better quality; ships a per-book `.voucher` whose
  key/iv decrypts it). This covers the vast majority of titles.
- **AAX fallback** — a minority of older titles have no AAXC asset (the API
  404s on asset details) but still offer legacy AAX. The sweep retries those
  with `--aax` and decrypts with the account-wide `activation_bytes`. (Note:
  `audible`'s own `--aax-fallback` flag *prefers* AAX, which we don't want — so
  the role does its own AAXC-first, AAX-second passes.)
- **Series / multi-part** titles are nested by `audible-cli` in a per-title
  subfolder, so the layout match and the `.aaxc`/`.aax` search are recursive.
- **Not downloadable** — titles Audible serves only as a stream (Plus catalogue)
  fail to download in either format. These are recorded once as
  `"status": "skipped"` and not retried as an error every sweep (which would
  otherwise leave the service permanently `failed`). Delete the ASIN's entry
  from `state.json` to re-check it — e.g. after buying a credit to own it.

## First-time auth (once per install)

`audible-cli` needs an OAuth token before any sweep will work. Run interactively
inside the container:

```bash
ssh root@192.168.0.97
docker exec -it audible-ingest-audible-ingest-1 audible quickstart
```

Choose the **AU** marketplace, follow the login prompts. The config lands in
the `audible_config` named volume at `/var/lib/audible-cli` so it survives
container recreation.

After quickstart, re-run the chown task so the new files are owned by uid 1028,
not root:

```bash
make home LIMIT=apps TAGS=audible_ingest
```

## Manually trigger a sweep

Fire the systemd unit (uses the timer's env vars — `MAX_PER_RUN=25`, jitter
30–90s):

```bash
ssh root@192.168.0.97 systemctl start audible-ingest.service
journalctl -u audible-ingest.service -f
```

Or run the script directly with custom throttle, e.g. one book, no sleep:

```bash
ssh root@192.168.0.97 \
  docker exec -e MAX_PER_RUN=1 -e SLEEP_MIN=0 -e SLEEP_MAX=0 \
    audible-ingest-audible-ingest-1 /usr/local/bin/audible-ingest
```

Unset `MAX_PER_RUN` (or set it empty) to drain the whole library — but the
daily 25-cap exists for a reason, so prefer the timer for bulk imports.

## Inspect / debug

```bash
# What's the timer doing?
ssh root@192.168.0.97 systemctl list-timers audible-ingest.timer

# State (per-ASIN status: imported / pinned / skipped)
ssh root@192.168.0.97 \
  docker exec audible-ingest-audible-ingest-1 \
    cat /var/lib/audible-ingest/state.json | jq

# What does Audible think is in the library?
ssh root@192.168.0.97 \
  docker exec audible-ingest-audible-ingest-1 \
    audible library list | head
```

## Knobs

Defaults live in `defaults/main.yml`:

- `audible_ingest_max_per_run: 25` — drip-feed cap per sweep
- `audible_ingest_sleep_min/max: 30/90` — jittered inter-download sleep
- `audible_ingest_oncalendar: "*-*-* 06:30:00"` — timer cadence

Change those, then `make home LIMIT=apps TAGS=audible_ingest` to redeploy.

## Pinning a book to skip it

If a title is mis-tagged on Audible (or you don't want it ingested), edit
`state.json` and set `"status": "pinned"` for the ASIN. The `TERMINAL` set in
`files/audible-ingest` includes `pinned`, so the loop will skip it as long as
the folder exists (or is empty — `pinned` just means "leave alone").
