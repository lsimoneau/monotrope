# TODO

Project-level backlog. Things that are real but not in flight. Move to a
plan or branch when picking one up.

## Hermes config.yaml is clobbered on deploy (make config non-destructive)

`make home LIMIT=hermes` renders `roles/hermes/templates/config.yaml.j2` straight
over `/root/.hermes/config.yaml`, so anything written *on the box* gets squashed
back to our template: user edits, a `hermes` self-update migrating the config, and
especially `hermes mcp add` / `hermes tools` (which persist `mcp_servers`,
`platform_toolsets`, `known_plugin_toolsets` into that same file). The deploy should
set only the keys we own and leave everything else intact — same spirit as the
skills seeds `cp -rn` no-clobber.

This is pre-existing (config.yaml was a full `copy:` before the ops-broker change
too); the broker work just made it bite, because the box's config now legitimately
diverges from the repo.

Candidate approaches (pick when picking it up):

- **Register the broker via Hermes' own CLI instead of templating the whole file.**
  `hermes mcp add apps_ops --url …` (idempotent, non-interactive) so Hermes does the
  targeted edit, and seed `config.yaml` no-clobber for first boot only. Cleanest —
  delegates merge semantics to Hermes. Confirm: an auth-header/token flag exists, the
  add is re-runnable without dup/error, and accept that the token lands in argv.
- **Deep-merge in Ansible.** `slurp` the remote config, `combine(recursive=True)` our
  managed dict over it, write back. Keeps Ansible authoritative for our keys without
  dropping on-box additions; list merges (e.g. `tools.include`) need care.
- **Config drop-in**, if Hermes supports includes / a `config.d`. Own a separate file
  for `mcp_servers`, leave `config.yaml` unmanaged. Confirm Hermes supports layering.

## Pi-hole HA DNS (deferred — needs second physical node)

Make DNS survive the OptiPlex going down. Two Pi-hole nodes (second on
separate hardware) fronted by a keepalived/VRRP floating VIP
(`192.168.0.53`), config synced with nebula-sync. Clients get the single
VIP — no "public resolver as secondary" (that leaks and doesn't fail over).
IPv4 works regardless of router; **IPv6 filtering is blocked on the Archer
AX55** (no custom RDNSS field) and needs a router upgrade
(OPNsense/UniFi/OpenWrt) to fix. Full plan, steps, and gotchas:
`infra/ansible/roles/pihole/HA-PLAN.md`.

## Hydrawise HA integration enhancements

The bundled `hydrawise` integration drops useful fields from the
`Zone` object that pydrawise already fetches. Two easy gaps worth a
core PR; one structural ask deferred.

**Realistic to land** (low LOC, no pydrawise change needed):

- `sensor.<zone>_suspended_until` — `SensorDeviceClass.TIMESTAMP`
  sensor mirroring `Zone.status.suspended_until`. Closes the
  "is it suspended and until when?" visibility gap. Today
  `switch.<zone>_auto_watering` is the only signal, and it's a bool.
- `sensor.<zone>_last_run` — `SensorDeviceClass.TIMESTAMP` for
  `Zone.status.last_run`. Surfaces last watering time without
  needing to scrape history.

Both follow the existing `next_cycle` sensor pattern in
`homeassistant/components/hydrawise/sensor.py`. ~50 LOC + translations
+ tests. Codeowners: `@dknowles2 @thomaskistler @ptcryan`. Related
open issues: home-assistant/core#168763, home-assistant/core#160082.

**Worth doing alongside if cheap** (needs pydrawise change):

- Expose past-run detail (`Zone.last_run.duration`, water used).
  pydrawise currently calls `get_zones(skip=["past_runs"])` in
  `client.py:138` — unskipping unlocks `last_cycle_duration` and
  `last_cycle_water_use` sensors. Bigger blast radius (touches lib +
  integration), defer unless the timestamp PR lands cleanly first.

**Deferred — structural blocker**:

- Schedule / program CRUD (`createStandardProgram`,
  `updateStandardProgram`, `updateSeasonalAdjustments`, etc.) is
  available on the GraphQL endpoint but not wrapped by pydrawise,
  and HA conventions don't love config-shaped service calls. If we
  ever need this, do it as a separate custom integration rather
  than a core PR.

**Testing**: can't validate locally until spring — everything will be
suspended through to ~Oct/Nov 2026. Don't open the PR earlier; the
HA codeowners will reasonably ask "did you run this against a live
controller?".

Test path when ready: copy
`homeassistant/components/hydrawise/` from the core repo at the tag
matching the running HA version into `/config/custom_components/hydrawise/`,
bump `manifest.json:version` to a local string, restart, iterate.
Delete the override once the PR merges and we've upgraded past the release.
