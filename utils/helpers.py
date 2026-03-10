from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_event_id() -> str:
    return str(uuid4())
