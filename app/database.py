from __future__ import annotations

from dataclasses import dataclass

from app.config import get_settings


@dataclass(frozen=True)
class DatabaseHandle:
    mongodb_uri: str
    mongodb_db: str


def get_database() -> DatabaseHandle | None:
    settings = get_settings()
    if not settings.mongodb_uri or not settings.mongodb_db:
        return None
    return DatabaseHandle(mongodb_uri=settings.mongodb_uri, mongodb_db=settings.mongodb_db)
