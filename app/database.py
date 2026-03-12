from __future__ import annotations

from dataclasses import dataclass
import logging

from app.config import get_settings


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DatabaseHandle:
    mongodb_uri: str
    mongodb_db: str


def get_database() -> DatabaseHandle | None:
    logger.debug("get_database start")
    settings = get_settings()
    if not settings.mongodb_uri or not settings.mongodb_db:
        logger.debug("get_database ok configured=false")
        return None
    logger.debug("get_database ok configured=true db=%s", settings.mongodb_db)
    return DatabaseHandle(mongodb_uri=settings.mongodb_uri, mongodb_db=settings.mongodb_db)
