#!/usr/bin/env python3
"""ops-broker — the lifecycle/observability capability surface.

First instance of broker_core. Exposes a fixed, hand-written menu of ops tools
(list / logs / status / restart) for the services on *this host*, gated by a
rendered allowlist. The agent never names a raw container/unit/path — it picks a
friendly service key that is resolved to the real target here, server-side.

Privilege required (and granted to the service user via groups, no root/sudo):
  - docker group        → docker logs / docker inspect / docker restart
  - systemd-journal     → journalctl -u <unit> (read-only)
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import re

from broker_core import RateLimiter, audit, build_server, configure_audit, run_argv, serve

BROKER = "apps-ops"
configure_audit(BROKER)

_CONFIG = json.load(open(os.environ["OPS_BROKER_CONFIG"], encoding="utf-8"))
SERVICES: dict[str, dict] = _CONFIG["services"]
_LIMITS: dict = _CONFIG.get("limits", {})
MAX_LINES = int(_LIMITS.get("max_lines", 1000))
RESTART_COOLDOWN = int(_LIMITS.get("restart_cooldown", 60))
RESTART_PER_HOUR = int(_LIMITS.get("restart_per_hour", 6))

BIND = os.environ.get("OPS_BROKER_BIND", "127.0.0.1")
PORT = int(os.environ.get("OPS_BROKER_PORT", "9988"))

_restart_limiter = RateLimiter(RESTART_COOLDOWN, RESTART_PER_HOUR)

# `since` is accepted only as a relative duration and converted to an absolute
# time here, so docker (--since) and journalctl (--since) each get a format they
# understand — and the input surface stays a tiny, easily-validated grammar.
_DUR_RE = re.compile(r"^(\d+)([smhd])$")
_UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400}
_MAX_SINCE_SECONDS = 30 * 86400  # 30 days

mcp = build_server(
    BROKER,
    host=BIND,
    port=PORT,
    instructions=(
        "Read-mostly operations for this host's services. Use list_services to "
        "discover names and which are restartable. All actions are allowlisted "
        "and audited."
    ),
)


def _err(message: str) -> str:
    return json.dumps({"error": message})


def _status_of(entry: dict) -> str:
    if entry["source"] == "docker":
        res = run_argv(
            ["docker", "inspect", "-f", "{{.State.Status}}", entry["target"]],
            timeout=10,
        )
        return res.output.strip() if res.returncode == 0 else "unknown"
    res = run_argv(["systemctl", "is-active", entry["target"]], timeout=10)
    return res.output.strip() or "unknown"


def _since_to_dt(since: str) -> _dt.datetime | None:
    match = _DUR_RE.match(since)
    if not match:
        return None
    seconds = int(match.group(1)) * _UNIT_SECONDS[match.group(2)]
    if seconds <= 0 or seconds > _MAX_SINCE_SECONDS:
        return None
    return _dt.datetime.now() - _dt.timedelta(seconds=seconds)


@mcp.tool(
    name="list_services",
    description=(
        "List the services this host's broker manages, with each one's type "
        "(docker/journal), live status, and whether a restart is permitted."
    ),
)
def list_services() -> str:
    services = [
        {
            "service": name,
            "source": entry["source"],
            "restartable": bool(entry.get("restartable")),
            "status": _status_of(entry),
        }
        for name, entry in SERVICES.items()
    ]
    audit("list_services", {}, "allow", count=len(services))
    return json.dumps({"services": services})


@mcp.tool(
    name="service_status",
    description="Report the current status of one managed service.",
)
def service_status(service: str) -> str:
    entry = SERVICES.get(service)
    if not entry:
        audit("service_status", {"service": service}, "deny", reason="unknown service")
        return _err(f"unknown service '{service}'")
    status = _status_of(entry)
    audit("service_status", {"service": service}, "allow", status=status)
    return json.dumps(
        {
            "service": service,
            "source": entry["source"],
            "restartable": bool(entry.get("restartable")),
            "status": status,
        }
    )


@mcp.tool(
    name="get_logs",
    description=(
        "Read recent logs for a managed service. 'service' must be one returned "
        "by list_services. 'lines' is clamped to the broker's maximum. 'since' is "
        "an optional relative window: a number followed by s/m/h/d (e.g. '30m', "
        "'2h', '1d'), up to 30 days."
    ),
)
def get_logs(service: str, lines: int = 100, since: str | None = None) -> str:
    entry = SERVICES.get(service)
    if not entry:
        audit("get_logs", {"service": service}, "deny", reason="unknown service")
        return _err(f"unknown service '{service}'")

    n = max(1, min(int(lines), MAX_LINES))

    since_dt: _dt.datetime | None = None
    if since is not None:
        since_dt = _since_to_dt(str(since).strip())
        if since_dt is None:
            audit("get_logs", {"service": service, "since": since}, "deny", reason="bad since")
            return _err("invalid 'since'; use e.g. '30m', '2h', '1d' (max 30d)")

    if entry["source"] == "docker":
        argv = ["docker", "logs", "--tail", str(n)]
        if since_dt is not None:
            argv += ["--since", str(int(since_dt.timestamp()))]
        argv += [entry["target"]]
    else:
        argv = ["journalctl", "-u", entry["target"], "-n", str(n), "--no-pager"]
        if since_dt is not None:
            argv += ["--since", since_dt.strftime("%Y-%m-%d %H:%M:%S")]

    res = run_argv(argv, timeout=20)
    audit("get_logs", {"service": service, "lines": n, "since": since}, "allow", rc=res.returncode)
    return json.dumps(
        {
            "service": service,
            "returncode": res.returncode,
            "truncated": res.truncated,
            "output": res.output,
        }
    )


@mcp.tool(
    name="restart_service",
    description=(
        "Restart a managed service. Permitted only for services with "
        "restartable=true (see list_services). Rate-limited per service."
    ),
)
def restart_service(service: str) -> str:
    entry = SERVICES.get(service)
    if not entry:
        audit("restart_service", {"service": service}, "deny", reason="unknown service")
        return _err(f"unknown service '{service}'")
    if not entry.get("restartable"):
        audit("restart_service", {"service": service}, "deny", reason="not restartable")
        return _err(f"service '{service}' is not restartable")

    allowed, reason = _restart_limiter.allow(service)
    if not allowed:
        audit("restart_service", {"service": service}, "deny", reason=reason)
        return _err(reason)

    if entry["source"] == "docker":
        argv = ["docker", "restart", entry["target"]]
    else:
        # No journal/systemd service is restartable in the current catalogue;
        # this path needs a polkit/sudoers grant for the non-root service user.
        argv = ["systemctl", "restart", entry["target"]]

    res = run_argv(argv, timeout=60)
    decision = "allow" if res.returncode == 0 else "error"
    audit("restart_service", {"service": service}, decision, rc=res.returncode)
    return json.dumps(
        {"service": service, "returncode": res.returncode, "output": res.output}
    )


if __name__ == "__main__":
    serve(mcp, token=os.environ["OPS_BROKER_TOKEN"], bind=BIND, port=PORT)
