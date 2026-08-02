from __future__ import annotations

from collections import defaultdict
from threading import Lock

from ..domain.models import StageEvent


class JobEventBuffer:
    """Thread-safe transient channel for live pipeline events from background video jobs."""

    def __init__(self) -> None:
        self._events: dict[str, list[StageEvent]] = defaultdict(list)
        self._lock = Lock()

    def append(self, job_id: str, event: StageEvent) -> None:
        with self._lock:
            self._events[job_id].append(event)

    def after(self, job_id: str, position: int) -> tuple[StageEvent, ...]:
        with self._lock:
            return tuple(self._events[job_id][position:])
