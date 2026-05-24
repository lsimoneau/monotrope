"""Server bootstrap: a stateless streamable-HTTP MCP app behind bearer auth."""

from __future__ import annotations

import uvicorn
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from .auth import BearerAuthMiddleware


def build_server(
    name: str, *, host: str, port: int, instructions: str | None = None
) -> FastMCP:
    """Construct a FastMCP server for a broker instance.

    ``stateless_http=True`` is mandatory: Hermes' MCP client caches a session
    id, and a stateful server hands out a new one on every restart, after which
    every call fails with "Session terminated". Stateless servers sidestep that
    entirely.

    DNS-rebinding protection stays ON (the secure default); we just allow exactly
    the host:port the client connects to. Without this the server rejects every
    non-localhost Host header with 421 Misdirected Request.
    """
    security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[f"{host}:{port}"],
        allowed_origins=[f"http://{host}:{port}"],
    )
    return FastMCP(
        name=name,
        instructions=instructions,
        stateless_http=True,
        transport_security=security,
    )


def serve(mcp: FastMCP, *, token: str, bind: str, port: int) -> None:
    """Serve the broker's streamable-HTTP app (mounted at /mcp) under uvicorn.

    Bind to a *specific* interface (the host's LAN IP), never 0.0.0.0 — the
    broker has no business being reachable beyond the trusted network. The
    bearer middleware gates HTTP requests while passing lifespan/other ASGI
    events through untouched, so FastMCP's session manager still starts.
    """
    app = mcp.streamable_http_app()
    uvicorn.run(
        BearerAuthMiddleware(app, token),
        host=bind,
        port=port,
        log_level="info",
        access_log=False,  # audit log is the record of truth; avoid double-logging
    )
