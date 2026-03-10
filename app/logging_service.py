from __future__ import annotations

from collections import deque
from typing import Any, Iterable

from app.config import get_settings
from models.event_log_model import EventLog
from utils.helpers import new_event_id, now_utc_iso


class InMemoryEventLogger:
    def __init__(self, maxlen: int) -> None:
        self._events: deque[EventLog] = deque(maxlen=maxlen)

    def log(self, event_type: str, status: str, payload: dict[str, Any] | None = None) -> EventLog:
        event = EventLog(
            id=new_event_id(),
            timestamp=now_utc_iso(),
            event_type=event_type,
            status=status,
            payload=payload or {},
        )
        self._events.append(event)
        return event

    def recent(self, limit: int = 50) -> list[EventLog]:
        if limit <= 0:
            return []
        return list(self._events)[-limit:]

    def iter_all(self) -> Iterable[EventLog]:
        return iter(self._events)

    def size(self) -> int:
        return len(self._events)


event_logger = InMemoryEventLogger(maxlen=get_settings().event_log_buffer_size)
