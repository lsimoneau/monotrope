"""broker_core — the audited scaffold every capability broker reuses.

A "broker" is a tiny MCP server that runs *on a managed host* and exposes a
fixed, hand-written menu of operations to Hermes Agent over the LAN. The core
provides everything that must be uniform across brokers — stateless streamable
HTTP transport, bearer auth, no-shell command execution, an audit trail, and a
rate limiter — and knows nothing about any specific tool. Instances (e.g.
ops_broker) import this, register their own validated handlers, then call
``serve``.

Security model: the broker is the privilege boundary. Hermes only ever sends it
MCP requests; it can invoke nothing outside the registered handlers. Keep
handlers narrow and parameter-validated — never build a generic "run this
command" tool on top of this.
"""

from .audit import audit, configure_audit
from .core import build_server, serve
from .exec import ExecResult, run_argv
from .ratelimit import RateLimiter

__all__ = [
    "audit",
    "configure_audit",
    "build_server",
    "serve",
    "ExecResult",
    "run_argv",
    "RateLimiter",
]
