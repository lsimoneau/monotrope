# KoInsight PR staging — v0.3.0 base

Same patches as the deployed `infra/kobo/koinsight.koplugin/` bundle, but
rebased onto upstream `main` (plugin version `0.3.0`, unreleased at time
of writing) so the diff is PR-ready.

**Not deployed to the Kobo** — use the sibling `koinsight.koplugin/`
directory for that. This directory is kept in sync with upstream master
so we can open a clean PR when the timing's right.

## What the PR adds

Two files changed vs upstream `main`:

- `main.lua`:
  - New `NETWORK_CONNECTED_SYNC_DEBOUNCE_S` constant (30 s).
  - New menu item under Tools → KoInsight: "Sync when Wi-Fi connects
    (recommended for Kobo)".
  - New `koinsight:onNetworkConnected()` handler. Debounced, concurrency-
    guarded, non-blocking (defers one UIManager tick), uses
    `KoInsightUpload.syncCurrentBook(server_url, true)` in silent mode.
- `settings.lua`:
  - New `sync_on_network_connected` entry in `DEFAULTS` (default `false` —
    no behavioural change for existing users).
  - New `getSyncOnNetworkConnectedEnabled` / `setSyncOnNetworkConnectedEnabled`
    / `toggleSyncOnNetworkConnected` following the existing setter/toggle
    pattern used for `sync_on_suspend` and `aggressive_suspend_sync`.

The other six files (`_meta.lua`, `annotation_reader.lua`, `call_api.lua`,
`const.lua`, `db_reader.lua`, `upload.lua`) are verbatim copies of
upstream `main` to make the directory self-contained — they should not be
included in the PR diff.

## Why this matters on Kobo specifically

Pasted from the deployed bundle's README, abbreviated:

On Kobo, wifi is unconditionally killed *before* plugin `onSuspend`
handlers run — see `Device:onPowerEvent` in KOReader's
`frontend/device/generic/device.lua` ("suspend will at best fail, and at
worst deadlock the system if Wi-Fi is on"). Consequence:

- `sync_on_suspend` without `aggressive_suspend_sync` sees wifi off and
  effectively never syncs.
- `aggressive_suspend_sync` blocks the suspend sequence for up to
  `suspend_connect_timeout_s` seconds while re-enabling wifi, and surfaces
  KOReader's blocking `Connecting to Wi-Fi…` modal. See
  <https://github.com/koreader/koreader/issues/11098>.

Listening for `NetworkConnected` (broadcast by `NetworkMgr` after a
successful connectivity check) lets sync run silently in the background
after `auto_restore_wifi` reconnects on resume — no blocking, no popup,
no churn. Trade-off is that sync shifts from "before sleep" to "after
wake", which is fine for a reading-stats plugin (no data loss, only
slight delay in visibility on the dashboard).

## Preparing the PR

```bash
# In a fresh clone of georgesg/koinsight:
git checkout -b feat/sync-on-network-connected main
cp /path/to/monotrope/infra/kobo/koinsight-pr-v0.3.0/koinsight.koplugin/main.lua \
   plugins/koinsight.koplugin/main.lua
cp /path/to/monotrope/infra/kobo/koinsight-pr-v0.3.0/koinsight.koplugin/settings.lua \
   plugins/koinsight.koplugin/settings.lua
git diff  # should match the diffs above
```

## Keeping this in sync with upstream

If upstream `main` moves, refresh the six unmodified files from the new
head and re-verify the two patched files apply cleanly (the hooks are
stable: `addToMainMenu` sub_item_table, event handler function, and
settings DEFAULTS table).
