from __future__ import annotations

from collections import deque
import logging
from typing import Any, Iterable

from app.config import get_settings
from models.event_log_model import EventLog
from utils.helpers import new_event_id, now_utc_iso


logger = logging.getLogger(__name__)


class InMemoryEventLogger:
    def __init__(self, maxlen: int) -> None:
        logger.debug("event_logger init maxlen=%d", maxlen)
        self._events: deque[EventLog] = deque(maxlen=maxlen)

    def log(self, event_type: str, status: str, payload: dict[str, Any] | None = None) -> EventLog:
        logger.debug(
            "event_logger.log start event_type=%s status=%s payload_keys=%d",
            event_type,
            status,
            len((payload or {}).keys()),
        )
        event = EventLog(
            id=new_event_id(),
            timestamp=now_utc_iso(),
            event_type=event_type,
            status=status,
            payload=payload or {},
        )
        self._events.append(event)
        logger.debug("event_logger.log ok size=%d", len(self._events))
        return event

    def recent(self, limit: int = 50) -> list[EventLog]:
        logger.debug("event_logger.recent start limit=%d", limit)
        if limit <= 0:
            return []
        result = list(self._events)[-limit:]
        logger.debug("event_logger.recent ok returned=%d", len(result))
        return result

    def iter_all(self) -> Iterable[EventLog]:
        logger.debug("event_logger.iter_all start")
        return iter(self._events)

    def size(self) -> int:
        size = len(self._events)
        logger.debug("event_logger.size ok size=%d", size)
        return size


event_logger = InMemoryEventLogger(maxlen=get_settings().event_log_buffer_size)
