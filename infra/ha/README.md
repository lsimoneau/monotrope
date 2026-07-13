# Home Assistant config

HAOS itself is unmanaged (closed appliance VM, hand-configured at
`192.168.0.86`). Pieces of HA state we care about as source-of-truth live
here.

## Dashboards

`dashboards/<url_path>.yaml` is the canonical Lovelace config for the
dashboard at `https://<haos>/<url_path>`. Push with:

```sh
HA_TOKEN=… uv run infra/ha/sync_dashboards.py            # push all
HA_TOKEN=… uv run infra/ha/sync_dashboards.py home       # push one
```

The script creates the dashboard with `mode: storage` if it doesn't exist
yet, then overwrites its config with the YAML on disk. It does **not**
pull state back — if you edit a dashboard via the HA UI, dump it before
re-running this script or your changes will be clobbered:

```sh
HA_TOKEN=… uv run infra/ha/sync_dashboards.py --dump home > infra/ha/dashboards/home.yaml
```

(Dump mode TBD — for now use `lovelace/config` over the websocket API.)

## Automations

`automations/<file>.yaml` is a list of automation configs (each with a stable
`id`). Push with:

```sh
HA_TOKEN=… uv run infra/ha/sync_automations.py                # push all
HA_TOKEN=… uv run infra/ha/sync_automations.py water_heater   # push one file
```

The script POSTs each automation to `/api/config/automation/config/<id>` (which
writes HA's managed `automations.yaml` and reloads), so it works on HAOS without
filesystem access. It's one-way (repo → HA): if you edit an automation in the UI,
copy it back into the YAML or the next push will clobber it.

- `water_heater.yaml` — heat-pump hot water: daytime solar-window timer, a
  cold-tank failsafe, and a summer surplus-solar boost. Retire the Emerald app's
  own timer once this is live, or they'll fight.

## Areas, devices, entities

These live in HAOS's own registry storage and are not source-controlled.
Bulk reassignments are scripted ad-hoc against the websocket API rather
than declared here, because the registry is keyed on opaque IDs that the
integration layer creates.
