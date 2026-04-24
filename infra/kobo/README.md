# Kobo client-side patches

Files to sideload onto the Kobo running KOReader. Not managed by Ansible
(Ansible handles server infra; the Kobo is a hand-touched device).

## `patches/2-silence-wifi-popups.lua`

Targeted KOReader user patch that replaces the centred "Connecting to Wi-Fi…"
/ "Turning on Wi-Fi…" / "Turning off Wi-Fi…" modal with a small
auto-dismissing Notification (toast). Keeps the page visible and touchable
during wifi transitions. See
<https://github.com/koreader/koreader/issues/11098> — upstream has marked the
issue "can't fix".

Only three `NetworkMgr` methods are overridden (`toggleWifiOn`,
`toggleWifiOff`, `turnOnWifiAndWaitForConnection`); nothing else in KOReader
is touched. This is the narrow alternative to the
[brugsbells nuclear patch](https://github.com/brugsbells/Koreader-Patches)
which hooks `UIManager:show` globally with a substring filter and also
swallows error dialogs.

The 45-second connection-timeout error popup ("Error connecting to the
network") is preserved — failures still surface, only the progress indicator
is quieted.

Deploy: copy to `<kobo root>/.adds/koreader/patches/2-silence-wifi-popups.lua`
(create the `patches/` directory if it does not exist). Loaded automatically
at KOReader startup; no config UI.

Revert: delete the file, restart KOReader.

## `koinsight.koplugin/`

Patched version of the KoInsight plugin (<https://github.com/georgesg/koinsight>)
adding a `sync_on_network_connected` option.

### Why

On Kobo, wifi is unconditionally killed *before* plugin `onSuspend` handlers
run — see `Device:onPowerEvent` in KOReader's `frontend/device/generic/device.lua`
(it calls `disableWifi` with comment "suspend will at best fail, and at worst
deadlock the system if Wi-Fi is on"). By the time KoInsight's `onSuspend`
fires, the radio is off.

Consequences for upstream KoInsight:

- **Normal mode** (`sync_on_suspend` without `aggressive_suspend_sync`) sees
  wifi off and returns without syncing. Effectively never syncs on Kobo.
- **Aggressive mode** re-enables wifi, blocks the suspend sequence for up to
  `suspend_connect_timeout_s` seconds waiting for reconnect, syncs, then
  disables wifi. Works, but blocks suspend and surfaces KOReader's blocking
  "Connecting to Wi-Fi…" modal via `NetworkMgr:turnOnWifi`. See
  <https://github.com/koreader/koreader/issues/11098>.

### What the patch adds

A new setting: **Sync when Wi-Fi connects (recommended for Kobo)**.

When enabled, KoInsight listens for KOReader's `NetworkConnected` event
(broadcast by `NetworkMgr` after a successful connectivity check) and runs
a debounced, non-blocking background sync. On Kobo this fires after
`auto_restore_wifi` silently brings wifi up on resume, so the sync happens
after wake rather than before sleep — no blocking, no popup.

Guards:

- Debounced to one sync per 30 seconds (`NETWORK_CONNECTED_SYNC_DEBOUNCE_S`).
- Concurrency-safe via an in-progress flag.
- Deferred by one UIManager tick so the event dispatch isn't blocked.
- Respects the existing `server_url` setting.

Default is **off** — existing users see no behavioural change until they
toggle it on.

### Recommended companion settings

- KOReader → Network → **Restore Wi-Fi connection on resume**: on
- KOReader → Network → **Disable Wi-Fi connection when inactive**: off
- KoInsight → **Sync on suspend**: off (the new setting supersedes it on Kobo)
- KoInsight → **Sync when Wi-Fi connects**: on

### What's in the directory

Snapshot of plugin **v0.2.2** (the latest tagged release — `:latest` Docker
image tracks this, not `main`). Patched files:

- `main.lua` — patched (adds `onNetworkConnected`, new menu item, debounce constant)
- `settings.lua` — patched (adds `sync_on_network_connected` getter/toggle)

Other files (`upload.lua`, `call_api.lua`, `annotation_reader.lua`,
`db_reader.lua`, `const.lua`, `_meta.lua`) are verbatim v0.2.2 so the plugin
stays in sync with the server.

**Important:** upstream `main` (version `0.3.0`) is not yet released. It
changed `upload.lua` from returning a bare function (`onUpload(url, silent)`)
to returning a table with methods (`KoInsightUpload.syncCurrentBook`,
`.syncAllBooks`). If the server is upgraded past v0.2.2, this bundle needs
to be rebased onto the matching plugin source — see the git history below.

### Deployment

Over USB, mount the Kobo and replace the **entire** plugin directory:

```
<kobo root>/.adds/koreader/plugins/koinsight.koplugin/
```

with the contents of this folder. Copying only the patched files risks
API mismatch with internal-version-inconsistent `upload.lua`.

Then either power-cycle the Kobo or use KOReader's "Restart KOReader" menu
entry. New toggle appears under **Tools → KoInsight**.

### Reverting

Re-install the stock plugin from
<https://github.com/georgesg/koinsight/releases> — it overwrites these files.
The `sync_on_network_connected` key in the plugin's settings file is simply
ignored by the stock version.

### Upstreaming

This is a candidate for a PR to `georgesg/koinsight`. A PR-ready version of
the patch rebased onto upstream `main` (plugin `0.3.0`, unreleased) lives
at `koinsight-pr-v0.3.0/` — **not** deployed to the Kobo, kept separately
so the PR diff is clean against upstream head. Once upstream merges and
cuts a release, the server image catches up, and this override can be
deleted.
