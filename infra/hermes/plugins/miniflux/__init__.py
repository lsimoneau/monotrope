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
