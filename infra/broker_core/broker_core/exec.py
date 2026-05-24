"""No-shell subprocess execution with output caps.

Every broker action that touches the host runs through here. Commands are
*argument lists* — ``shell=True`` is never used — so a validated parameter that
somehow contained shell metacharacters still cannot inject a command.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass

DEFAULT_TIMEOUT = 20
DEFAULT_MAX_BYTES = 64 * 1024


@dataclass
class ExecResult:
    returncode: int
    output: str
    truncated: bool


def run_argv(
    argv: list[str],
    *,
    timeout: int = DEFAULT_TIMEOUT,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> ExecResult:
    """Run ``argv`` and return combined stdout+stderr, capped to the most recent
    ``max_bytes`` (logs are most useful at the tail)."""
    try:
        proc = subprocess.run(
            argv, capture_output=True, text=True, timeout=timeout, check=False
        )
    except subprocess.TimeoutExpired:
        return ExecResult(returncode=124, output=f"timed out after {timeout}s", truncated=False)
    except FileNotFoundError as exc:
        return ExecResult(returncode=127, output=str(exc), truncated=False)

    out = proc.stdout or ""
    if proc.stderr:
        sep = "\n" if out and not out.endswith("\n") else ""
        out = f"{out}{sep}{proc.stderr}"

    raw = out.encode("utf-8", "replace")
    truncated = len(raw) > max_bytes
    if truncated:
        out = raw[-max_bytes:].decode("utf-8", "replace")
    return ExecResult(returncode=proc.returncode, output=out, truncated=truncated)
