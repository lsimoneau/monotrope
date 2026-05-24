"""Bearer-token ASGI middleware.

A pure ASGI wrapper (not Starlette's BaseHTTPMiddleware) so it composes with
any ASGI app and forwards non-HTTP scopes — crucially ``lifespan`` — to the
wrapped app without interference.
"""

from __future__ import annotations

import secrets


class BearerAuthMiddleware:
    def __init__(self, app, token: str) -> None:
        if not token:
            raise ValueError("broker bearer token must not be empty")
        self.app = app
        self._expected = f"Bearer {token}"

    async def __call__(self, scope, receive, send) -> None:
        if scope.get("type") == "http":
            headers = dict(scope.get("headers") or [])
            provided = headers.get(b"authorization", b"").decode("latin-1")
            # Constant-time compare to avoid leaking the token via timing.
            if not secrets.compare_digest(provided, self._expected):
                await send(
                    {
                        "type": "http.response.start",
                        "status": 401,
                        "headers": [(b"content-type", b"text/plain; charset=utf-8")],
                    }
                )
                await send({"type": "http.response.body", "body": b"unauthorized\n"})
                return
        await self.app(scope, receive, send)
