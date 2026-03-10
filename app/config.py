import os
from functools import lru_cache

from pydantic import BaseModel


class Settings(BaseModel):
    app_host: str = "0.0.0.0"
    app_port: int = 42014
    mongodb_uri: str | None = None
    mongodb_db: str | None = None
    event_log_buffer_size: int = 1000

    @classmethod
    def load(cls) -> "Settings":
        app_host = os.getenv("APP_HOST", cls.model_fields["app_host"].default)
        app_port_raw = os.getenv("APP_PORT", str(cls.model_fields["app_port"].default))
        mongodb_uri = os.getenv("MONGODB_URI") or None
        mongodb_db = os.getenv("MONGODB_DB") or None
        event_log_buffer_size_raw = os.getenv(
            "EVENT_LOG_BUFFER_SIZE", str(cls.model_fields["event_log_buffer_size"].default)
        )

        return cls(
            app_host=app_host,
            app_port=int(app_port_raw),
            mongodb_uri=mongodb_uri,
            mongodb_db=mongodb_db,
            event_log_buffer_size=int(event_log_buffer_size_raw),
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.load()
