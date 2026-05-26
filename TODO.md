# TODO

Project-level backlog. Things that are real but not in flight. Move to a
plan or branch when picking one up.

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
