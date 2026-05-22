#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "PyYAML",
#     "websockets>=12",
# ]
# ///
"""Push every YAML in `infra/ha/dashboards/` to the Home Assistant Lovelace API.

The file's stem is used as the dashboard `url_path`. The YAML must contain
the dashboard config body — `title`, `views`, etc. — exactly as HA's
`lovelace/config` websocket message expects.

Auth: set `HA_URL` (default `ws://192.168.0.86:8123/api/websocket`) and
`HA_TOKEN` (a long-lived access token from Profile → Security).

Run:
    uv run infra/ha/sync_dashboards.py            # push all
    uv run infra/ha/sync_dashboards.py home       # push one by url_path
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import websockets
import yaml

DASHBOARDS_DIR = Path(__file__).parent / "dashboards"
DEFAULT_URL = "ws://192.168.0.86:8123/api/websocket"


async def _send(ws, **kw):
    """Send a request and read until we see a result for our id."""
    msg_id = kw["id"]
    await ws.send(json.dumps(kw))
    while True:
        r = json.loads(await ws.recv())
        if r.get("id") == msg_id and r.get("type") == "result":
            return r


async def push(url: str, token: str, only: str | None) -> int:
    files = sorted(DASHBOARDS_DIR.glob("*.yaml"))
    if only:
        files = [f for f in files if f.stem == only]
        if not files:
            print(f"No dashboard YAML for url_path={only}", file=sys.stderr)
            return 1

    async with websockets.connect(url, max_size=8 * 1024 * 1024) as ws:
        await ws.recv()
        await ws.send(json.dumps({"type": "auth", "access_token": token}))
        await ws.recv()

        listed = await _send(ws, id=1, type="lovelace/dashboards/list")
        existing = {d["url_path"]: d for d in listed["result"]}

        msg_id = 2
        for path in files:
            url_path = path.stem
            cfg = yaml.safe_load(path.read_text())
            title = cfg.get("title", url_path.replace("-", " ").title())

            if url_path not in existing:
                r = await _send(
                    ws,
                    id=msg_id,
                    type="lovelace/dashboards/create",
                    url_path=url_path,
                    title=title,
                    icon=cfg.get("icon", "mdi:view-dashboard"),
                    mode="storage",
                    show_in_sidebar=True,
                    require_admin=False,
                )
                msg_id += 1
                if not r["success"]:
                    print(f"create {url_path} failed: {r['error']}", file=sys.stderr)
                    return 1
                print(f"created {url_path}")

            r = await _send(
                ws,
                id=msg_id,
                type="lovelace/config/save",
                url_path=url_path,
                config=cfg,
            )
            msg_id += 1
            if not r["success"]:
                print(f"save {url_path} failed: {r['error']}", file=sys.stderr)
                return 1
            print(f"saved {url_path} ({len(cfg.get('views', []))} views)")
    return 0


def main() -> int:
    url = os.environ.get("HA_URL", DEFAULT_URL)
    token = os.environ.get("HA_TOKEN")
    if not token:
        print("HA_TOKEN not set", file=sys.stderr)
        return 1
    only = sys.argv[1] if len(sys.argv) > 1 else None
    return asyncio.run(push(url, token, only))


if __name__ == "__main__":
    sys.exit(main())
