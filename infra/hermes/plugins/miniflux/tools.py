import json
from pathlib import Path

import requests

_PLUGIN_DIR = Path(__file__).parent
with open(_PLUGIN_DIR / "config.json") as _f:
    _CONFIG = json.loads(_f.read())

_BASE = _CONFIG.get("base_url", "http://miniflux:8080").rstrip("/")
_HEADERS = {"X-Auth-Token": _CONFIG.get("api_key", "")}


def _get(path, **params):
    resp = requests.get(f"{_BASE}/v1{path}", headers=_HEADERS, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _put(path, body):
    resp = requests.put(f"{_BASE}/v1{path}", headers=_HEADERS, json=body, timeout=10)
    resp.raise_for_status()
    return resp


def list_feeds(args: dict, **kwargs) -> str:
    try:
        feeds = _get("/feeds")
        counters = _get("/feeds/counters")
        unreads = counters.get("unreads", {})

        result = []
        for f in feeds:
            result.append({
                "id": f["id"],
                "title": f["title"],
                "site_url": f.get("site_url", ""),
                "category": f.get("category", {}).get("title", ""),
                "unread": unreads.get(str(f["id"]), 0),
            })
        result.sort(key=lambda x: x["unread"], reverse=True)
        return json.dumps({"feeds": result, "total": len(result)})
    except Exception as e:
        return json.dumps({"error": str(e)})


def get_unread_entries(args: dict, **kwargs) -> str:
    try:
        params = {
            "status": "unread",
            "limit": args.get("limit", 20),
            "direction": "desc",
            "order": "published_at",
        }
        if args.get("feed_id"):
            path = f"/feeds/{args['feed_id']}/entries"
        elif args.get("category_id"):
            path = f"/categories/{args['category_id']}/entries"
        else:
            path = "/entries"

        data = _get(path, **params)
        entries = []
        for e in data.get("entries", []):
            entries.append({
                "id": e["id"],
                "title": e["title"],
                "url": e.get("url", ""),
                "feed": e.get("feed", {}).get("title", ""),
                "category": e.get("feed", {}).get("category", {}).get("title", ""),
                "author": e.get("author", ""),
                "published_at": e.get("published_at", ""),
                "reading_time": e.get("reading_time", 0),
            })
        return json.dumps({
            "entries": entries,
            "total": data.get("total", len(entries)),
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


def get_entry(args: dict, **kwargs) -> str:
    try:
        entry = _get(f"/entries/{args['entry_id']}")
        return json.dumps({
            "id": entry["id"],
            "title": entry["title"],
            "url": entry.get("url", ""),
            "author": entry.get("author", ""),
            "feed": entry.get("feed", {}).get("title", ""),
            "category": entry.get("feed", {}).get("category", {}).get("title", ""),
            "published_at": entry.get("published_at", ""),
            "reading_time": entry.get("reading_time", 0),
            "content": entry.get("content", ""),
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


def toggle_bookmark(args: dict, **kwargs) -> str:
    try:
        _put(f"/entries/{args['entry_id']}/bookmark", {})
        return json.dumps({"ok": True, "entry_id": args["entry_id"]})
    except Exception as e:
        return json.dumps({"error": str(e)})


def update_feed_filters(args: dict, **kwargs) -> str:
    try:
        feed_id = args["feed_id"]
        body = {}
        if "keeplist_rules" in args:
            body["keeplist_rules"] = args["keeplist_rules"]
        if "blocklist_rules" in args:
            body["blocklist_rules"] = args["blocklist_rules"]
        if not body:
            return json.dumps({"error": "Provide keeplist_rules and/or blocklist_rules"})
        resp = requests.put(
            f"{_BASE}/v1/feeds/{feed_id}",
            headers=_HEADERS, json=body, timeout=10,
        )
        resp.raise_for_status()
        feed = resp.json()
        return json.dumps({
            "ok": True,
            "feed_id": feed["id"],
            "title": feed["title"],
            "keeplist_rules": feed.get("keeplist_rules", ""),
            "blocklist_rules": feed.get("blocklist_rules", ""),
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


def mark_as_read(args: dict, **kwargs) -> str:
    try:
        entry_ids = args.get("entry_ids", [])
        if not entry_ids:
            return json.dumps({"error": "No entry_ids provided"})
        _put("/entries", {"entry_ids": entry_ids, "status": "read"})
        return json.dumps({"ok": True, "marked_read": entry_ids})
    except Exception as e:
        return json.dumps({"error": str(e)})
