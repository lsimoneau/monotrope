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

BROKER = os.environ.get("OPS_BROKER_NAME", "apps-ops")
configure_audit(BROKER)

_CONFIG = json.load(open(os.environ["OPS_BROKER_CONFIG"], encoding="utf-8"))
SERVICES: dict[str, dict] = _CONFIG["services"]
FILES: dict[str, dict] = _CONFIG.get("files", {})
_LIMITS: dict = _CONFIG.get("limits", {})
MAX_LINES = int(_LIMITS.get("max_lines", 1000))
MAX_FILE_BYTES = int(_LIMITS.get("max_file_bytes", 256 * 1024))
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


# Properties that capture the *last run*'s outcome for a systemd unit — the
# signal that tells a oneshot which exited non-zero from one that's merely
# inactive between timer firings (where `is-active` alone says little).
_UNIT_PROPS = (
    "ActiveState,SubState,Result,ExecMainStatus,"
    "ExecMainStartTimestamp,ExecMainExitTimestamp,NRestarts"
)


def _unit_health(unit: str) -> dict:
    res = run_argv(["systemctl", "show", unit, "--property=" + _UNIT_PROPS], timeout=10)
    props: dict[str, str] = {}
    for line in res.output.splitlines():
        key, _, value = line.partition("=")
        props[key] = value
    return {
        "status": props.get("ActiveState", "unknown"),
        "sub_state": props.get("SubState", ""),
        "result": props.get("Result", ""),  # 'success', 'exit-code', ...
        "exit_code": props.get("ExecMainStatus", ""),
        "started_at": props.get("ExecMainStartTimestamp", ""),
        "finished_at": props.get("ExecMainExitTimestamp", ""),
        "restarts": props.get("NRestarts", ""),
    }


def _docker_health(target: str) -> dict:
    # One inspect call: restart count (top-level) + the whole State object,
    # tab-separated. State carries ExitCode/OOMKilled/timestamps and, if the
    # image declares a HEALTHCHECK, a nested Health.Status.
    res = run_argv(
        ["docker", "inspect", "-f", "{{.RestartCount}}\t{{json .State}}", target],
        timeout=10,
    )
    if res.returncode != 0:
        return {"status": "unknown", "error": res.output.strip()}
    restarts, _, state_json = res.output.strip().partition("\t")
    try:
        state = json.loads(state_json)
    except json.JSONDecodeError:
        return {"status": "unknown"}
    health = state["Health"]["Status"] if isinstance(state.get("Health"), dict) else ""
    return {
        "status": state.get("Status", "unknown"),
        "exit_code": state.get("ExitCode", ""),
        "started_at": state.get("StartedAt", ""),
        "finished_at": state.get("FinishedAt", ""),
        "restarts": restarts,
        "health": health,
        "oom_killed": bool(state.get("OOMKilled", False)),
    }


def _read_tail(path: str, max_bytes: int) -> tuple[str, bool, int]:
    """Read the trailing ``max_bytes`` of a host-readable file, no subprocess."""
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as fh:
            if size > max_bytes:
                fh.seek(-max_bytes, os.SEEK_END)
            data = fh.read(max_bytes)
        return data.decode("utf-8", "replace"), size > max_bytes, 0
    except OSError as exc:
        return str(exc), False, 1


@mcp.tool(
    name="list_services",
    description=(
        "List the services this host's broker manages, with each one's type "
        "(docker/journal), live status, and whether a restart or trigger is permitted."
    ),
)
def list_services() -> str:
    services = [
        {
            "service": name,
            "source": entry["source"],
            "restartable": bool(entry.get("restartable")),
            "triggerable": bool(entry.get("triggerable")),
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
            "triggerable": bool(entry.get("triggerable")),
            "status": status,
        }
    )


@mcp.tool(
    name="service_health",
    description=(
        "Deeper health for one managed service than service_status: the last "
        "run's result and exit code, when it last started/finished, restart "
        "count, and (docker) health-check + OOM state. Use this to tell a "
        "service that merely *exists* from one whose last run failed — e.g. a "
        "timer-driven sweep whose container is 'up' but which exited non-zero."
    ),
)
def service_health(service: str) -> str:
    entry = SERVICES.get(service)
    if not entry:
        audit("service_health", {"service": service}, "deny", reason="unknown service")
        return _err(f"unknown service '{service}'")
    health = _docker_health(entry["target"]) if entry["source"] == "docker" else _unit_health(entry["target"])
    audit("service_health", {"service": service}, "allow", status=health.get("status"))
    return json.dumps({"service": service, "source": entry["source"], **health})


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
    name="list_files",
    description=(
        "List the diagnostic files this broker can read, by friendly name. For "
        "state/log files that live outside journald and docker logs (e.g. inside "
        "a container volume). The agent never names a raw path — only these keys."
    ),
)
def list_files() -> str:
    names = sorted(FILES)
    audit("list_files", {}, "allow", count=len(names))
    return json.dumps({"files": names})


@mcp.tool(
    name="read_file",
    description=(
        "Read an allowlisted diagnostic file by its friendly name (see "
        "list_files). Read-only; returns the file's tail capped to the broker's "
        "byte limit."
    ),
)
def read_file(name: str) -> str:
    entry = FILES.get(name)
    if not entry:
        audit("read_file", {"file": name}, "deny", reason="unknown file")
        return _err(f"unknown file '{name}'")

    if entry.get("container"):
        # Read from inside a container volume. tail -c bounds the bytes the exec
        # emits, so a huge file never has to be buffered whole.
        res = run_argv(
            ["docker", "exec", entry["container"], "tail", "-c", str(MAX_FILE_BYTES), entry["path"]],
            timeout=15,
            max_bytes=MAX_FILE_BYTES,
        )
        output, rc = res.output, res.returncode
        truncated = res.truncated or len(output.encode("utf-8", "replace")) >= MAX_FILE_BYTES
    else:
        output, truncated, rc = _read_tail(entry["path"], MAX_FILE_BYTES)

    audit("read_file", {"file": name}, "allow", rc=rc)
    return json.dumps({"file": name, "returncode": rc, "truncated": truncated, "output": output})


@mcp.tool(
    name="start_service",
    description=(
        "Start (trigger) a oneshot service. Permitted only for services with "
        "triggerable=true (see list_services). Designed for timer-driven ingest "
        "sweeps — fires the unit via systemd's StartUnit D-Bus method (polkit-"
        "authorised) so the sweep runs on demand instead of waiting for the next "
        "timer tick. Rate-limited per service."
    ),
)
def start_service(service: str) -> str:
    entry = SERVICES.get(service)
    if not entry:
        audit("start_service", {"service": service}, "deny", reason="unknown service")
        return _err(f"unknown service '{service}'")
    if not entry.get("triggerable"):
        audit("start_service", {"service": service}, "deny", reason="not triggerable")
        return _err(f"service '{service}' is not triggerable")
    if entry.get("source") != "journal":
        audit("start_service", {"service": service}, "deny", reason="not a systemd unit")
        return _err(f"service '{service}' is not a systemd unit")

    allowed, reason = _restart_limiter.allow(service)
    if not allowed:
        audit("start_service", {"service": service}, "deny", reason=reason)
        return _err(reason)

    # Talk to systemd's manager over the system bus. Polkit authorises the call
    # per-unit via /etc/polkit-1/rules.d/50-ops-broker-manage-units.rules (the
    # opsbroker user, this exact unit, StartUnit only). We deliberately avoid
    # `sudo systemctl start`: the broker's unit has NoNewPrivileges=true, which
    # blocks setuid escalation, and sudo is not how this is authorised anyway.
    # busctl gives an unambiguous audit trail and is part of systemd (always
    # present on hosts that run systemd, which is every host we manage).
    argv = [
        "busctl", "call",
        "org.freedesktop.systemd1",
        "/org/freedesktop/systemd1",
        "org.freedesktop.systemd1.Manager",
        "StartUnit",
        "ss",
        entry["target"],
        "replace",
    ]

    res = run_argv(argv, timeout=120)
    decision = "allow" if res.returncode == 0 else "error"
    audit("start_service", {"service": service}, decision, rc=res.returncode)
    if res.returncode == 0:
        # busctl writes the reply as `o "/org/freedesktop/systemd1/job/N"`.
        # Surface a human-readable confirmation; the raw object path is
        # included so an operator can `journalctl` against the job if needed.
        m = re.search(r'"(/org/freedesktop/systemd1/job/\d+)"', res.output)
        job = m.group(1) if m else res.output.strip() or "queued"
        return json.dumps(
            {"service": service, "returncode": 0, "triggered": f"queued {entry['target']} ({job})"}
        )
    return json.dumps(
        {"service": service, "returncode": res.returncode, "output": res.output}
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
