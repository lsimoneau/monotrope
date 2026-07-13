#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "PyYAML",
#     "requests",
# ]
# ///
"""Push automations from `infra/ha/automations/*.yaml` to Home Assistant.

Each YAML file is a list of automation configs, each carrying an `id`. We POST
each to `/api/config/automation/config/<id>`, which writes it into HA's managed
`automations.yaml` and reloads - the automation analogue of `sync_dashboards.py`,
and like it this works on HAOS without filesystem/SSH access.

This is one-way (repo -> HA). If you edit an automation in the HA UI, copy it
back into the YAML here or the next push will clobber it.

Auth: set `HA_BASE_URL` (default `http://192.168.0.86:8123`) and `HA_TOKEN`
(a long-lived access token from Profile -> Security).

Run:
    HA_TOKEN=... uv run infra/ha/sync_automations.py                # push all
    HA_TOKEN=... uv run infra/ha/sync_automations.py water_heater   # one file
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import requests
import yaml

AUTOMATIONS_DIR = Path(__file__).parent / "automations"
DEFAULT_BASE = "http://192.168.0.86:8123"


def push(base: str, token: str, only: str | None) -> int:
    files = sorted(AUTOMATIONS_DIR.glob("*.yaml"))
    if only:
        files = [f for f in files if f.stem == only]
        if not files:
            print(f"No automation YAML for {only}", file=sys.stderr)
            return 1

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    pushed = 0
    for path in files:
        items = yaml.safe_load(path.read_text()) or []
        for cfg in items:
            aid = cfg.get("id")
            if not aid:
                print(f"{path.name}: automation missing 'id': {cfg.get('alias')!r}",
                      file=sys.stderr)
                return 1
            r = requests.post(
                f"{base}/api/config/automation/config/{aid}",
                headers=headers,
                json=cfg,
                timeout=15,
            )
            if not r.ok:
                print(f"push {aid} failed: {r.status_code} {r.text}", file=sys.stderr)
                return 1
            print(f"pushed {aid} ({cfg.get('alias')})")
            pushed += 1

    # Reload so the changes take effect without restarting HA.
    r = requests.post(
        f"{base}/api/services/automation/reload", headers=headers, timeout=15
    )
    if not r.ok:
        print(f"reload failed: {r.status_code} {r.text}", file=sys.stderr)
        return 1
    print(f"pushed {pushed} automations, reloaded")
    return 0


def main() -> int:
    token = os.environ.get("HA_TOKEN")
    if not token:
        print("HA_TOKEN not set", file=sys.stderr)
        return 1
    base = os.environ.get("HA_BASE_URL", DEFAULT_BASE).rstrip("/")
    only = sys.argv[1] if len(sys.argv) > 1 else None
    return push(base, token, only)


if __name__ == "__main__":
    sys.exit(main())
