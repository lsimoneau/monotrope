"""In-memory rate limiter for mutating operations (per-key cooldown + hourly cap).

Single-process, in-memory state — sufficient because a broker is one uvicorn
process. Guards against an agent loop thrashing a service (e.g. repeated
restarts).
"""

from __future__ import annotations

import time
from collections import defaultdict

_WINDOW = 3600  # seconds in the per-hour window


class RateLimiter:
    def __init__(self, cooldown: int, per_hour: int) -> None:
        self.cooldown = cooldown
        self.per_hour = per_hour
        self._events: dict[str, list[float]] = defaultdict(list)

    def allow(self, key: str) -> tuple[bool, str]:
        """Check and, if permitted, record an event for ``key``.

        Returns ``(allowed, reason)``; ``reason`` explains a denial.
        """
        now = time.time()
        events = self._events[key]
        events[:] = [t for t in events if now - t < _WINDOW]

        if events and now - events[-1] < self.cooldown:
            wait = int(self.cooldown - (now - events[-1]))
            return False, f"cooldown active; retry in ~{wait}s"
        if len(events) >= self.per_hour:
            return False, f"rate limit reached ({self.per_hour}/hour)"

        events.append(now)
        return True, ""
