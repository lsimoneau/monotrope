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
            "category_id": {
                "type": "integer",
                "description": "Filter to a specific category. Omit for all categories.",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of entries to return. Defaults to 20.",
            },
        },
        "required": [],
    },
}

GET_ENTRY = {
    "name": "get_entry",
    "description": (
        "Get a single entry from Miniflux by ID, including its full content. "
        "Use this to read an article's text."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "entry_id": {
                "type": "integer",
                "description": "The entry ID to retrieve.",
            },
        },
        "required": ["entry_id"],
    },
}

TOGGLE_BOOKMARK = {
    "name": "toggle_bookmark",
    "description": "Toggle the bookmark/star status of a Miniflux entry.",
    "parameters": {
        "type": "object",
        "properties": {
            "entry_id": {
                "type": "integer",
                "description": "The entry ID to bookmark or unbookmark.",
            },
        },
        "required": ["entry_id"],
    },
}

UPDATE_FEED_FILTERS = {
    "name": "update_feed_filters",
    "description": (
        "Update the keep or block filter rules on a Miniflux feed. "
        "Rules are case-insensitive regexes matched against entry titles and URLs. "
        "keeplist_rules: only entries matching are kept. "
        "blocklist_rules: entries matching are excluded. "
        "Pass an empty string to clear a rule."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "feed_id": {
                "type": "integer",
                "description": "The feed ID to update.",
            },
            "keeplist_rules": {
                "type": "string",
                "description": "Regex pattern. Only matching entries are kept. Omit to leave unchanged.",
            },
            "blocklist_rules": {
                "type": "string",
                "description": "Regex pattern. Matching entries are excluded. Omit to leave unchanged.",
            },
        },
        "required": ["feed_id"],
    },
}

MARK_AS_READ = {
    "name": "mark_as_read",
    "description": "Mark one or more Miniflux entries as read.",
    "parameters": {
        "type": "object",
        "properties": {
            "entry_ids": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "List of entry IDs to mark as read.",
            },
        },
        "required": ["entry_ids"],
    },
}
