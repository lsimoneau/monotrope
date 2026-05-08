from . import schemas, tools


def register(ctx):
    ctx.register_tool(
        name="list_feeds",
        toolset="miniflux",
        schema=schemas.LIST_FEEDS,
        handler=tools.list_feeds,
    )
    ctx.register_tool(
        name="get_unread_entries",
        toolset="miniflux",
        schema=schemas.GET_UNREAD_ENTRIES,
        handler=tools.get_unread_entries,
    )
    ctx.register_tool(
        name="get_entry",
        toolset="miniflux",
        schema=schemas.GET_ENTRY,
        handler=tools.get_entry,
    )
    ctx.register_tool(
        name="toggle_bookmark",
        toolset="miniflux",
        schema=schemas.TOGGLE_BOOKMARK,
        handler=tools.toggle_bookmark,
    )
    ctx.register_tool(
        name="update_feed_filters",
        toolset="miniflux",
        schema=schemas.UPDATE_FEED_FILTERS,
        handler=tools.update_feed_filters,
    )
    ctx.register_tool(
        name="mark_as_read",
        toolset="miniflux",
        schema=schemas.MARK_AS_READ,
        handler=tools.mark_as_read,
    )
