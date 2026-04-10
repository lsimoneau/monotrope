LIST_FEEDS = {
    "name": "list_feeds",
    "description": (
        "List all subscribed RSS feeds from Miniflux. "
        "Returns feed titles, URLs, and unread counts."
    ),
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}

GET_UNREAD_ENTRIES = {
    "name": "get_unread_entries",
    "description": (
        "Get unread entries from Miniflux. "
        "Optionally filter by feed ID and limit the number of results."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "feed_id": {
                "type": "integer",
                "description": "Filter to a specific feed. Omit for all feeds.",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of entries to return. Defaults to 20.",
            },
        },
        "required": [],
    },
}
