from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from app.database import get_database
from app.logging_service import event_logger
from services import ssh_service


router = APIRouter(prefix="", tags=["health"])

_STARTED_AT = datetime.now(timezone.utc)


@router.get("/health")
def health() -> dict[str, object]:
    db = get_database()
    ssh_status = ssh_service.check_ssh_connection()
    return {
        "status": "ok",
        "started_at": _STARTED_AT.isoformat(),
        "mongodb_configured": db is not None,
        "event_log_size": event_logger.size(),
        "ssh": ssh_status,
        "mcp_sse_endpoint": "/mcp/sse",
        "mcp_messages_endpoint": "/mcp/messages",
    }
