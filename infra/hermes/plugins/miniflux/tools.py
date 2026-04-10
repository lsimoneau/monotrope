import json
import os
import urllib.request
import urllib.error

MINIFLUX_BASE = os.environ.get("MINIFLUX_BASE_URL", "http://miniflux:8080")
MINIFLUX_KEY = os.environ.get("MINIFLUX_API_KEY", "")


def _request(path):
    """Make an authenticated GET request to the Miniflux API."""
    url = f"{MINIFLUX_BASE}/v1{path}"
    req = urllib.request.Request(url, headers={"X-Auth-Token": MINIFLUX_KEY})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def list_feeds(args: dict, **kwargs) -> str:
    try:
        feeds = _request("/feeds")
        counters = _request("/feeds/counters")
        unreads = counters.get("reads", {})  # keyed by feed id
        unread_map = counters.get("unreads", {})

        result = []
        for f in feeds:
            fid = str(f["id"])
            result.append({
                "id": f["id"],
                "title": f["title"],
                "site_url": f.get("site_url", ""),
                "unread": unread_map.get(fid, 0),
            })
        result.sort(key=lambda x: x["unread"], reverse=True)
        return json.dumps({"feeds": result, "total": len(result)})
    except Exception as e:
        return json.dumps({"error": str(e)})


def get_unread_entries(args: dict, **kwargs) -> str:
    try:
        limit = args.get("limit", 20)
        feed_id = args.get("feed_id")

        if feed_id:
            path = f"/feeds/{feed_id}/entries?status=unread&limit={limit}&direction=desc&order=published_at"
        else:
            path = f"/entries?status=unread&limit={limit}&direction=desc&order=published_at"

        data = _request(path)
        entries = []
        for e in data.get("entries", []):
            entries.append({
                "id": e["id"],
                "title": e["title"],
                "url": e.get("url", ""),
                "feed": e.get("feed", {}).get("title", ""),
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
