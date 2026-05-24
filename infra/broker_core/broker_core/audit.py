"""Structured audit logging to stdout (captured by systemd → journald).

Every tool call — allowed or denied — emits one JSON line. This is the record
of what the agent did through the broker; the systemd unit's journal is the
audit trail (no separate file logs, per the homelab journald convention).
"""

from __future__ import annotations

import json
import logging
import sys

_logger = logging.getLogger("broker.audit")
_broker_name = "broker"


def configure_audit(name: str) -> None:
    _logger.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    _logger.addHandler(handler)
    _logger.setLevel(logging.INFO)
    _logger.propagate = False
    global _broker_name
    _broker_name = name


def audit(tool: str, args: dict, decision: str, **extra) -> None:
    """Emit one structured audit line. ``decision`` is e.g. 'allow' / 'deny'."""
    record = {"broker": _broker_name, "tool": tool, "args": args, "decision": decision}
    record.update(extra)
    _logger.info(json.dumps(record, default=str, sort_keys=True))
