import os
from functools import lru_cache

from pydantic import BaseModel


class Settings(BaseModel):
    # ── App ────────────────────────────────────────────────────────────────
    app_host: str = "0.0.0.0"
    app_port: int = 42014
    # ── MongoDB ───────────────────────────────────────────────────────────
    mongodb_uri: str | None = None
    mongodb_db: str | None = None
    # ── Event log ─────────────────────────────────────────────────────────
    event_log_buffer_size: int = 1000
    # ── SSH (VNC container talks to its own sshd on localhost) ────────────
    ssh_host: str = "127.0.0.1"
    ssh_port: int = 42012
    ssh_user: str = "root"
    ssh_key_path: str = "/root/.ssh/id_rsa"
    ssh_connect_timeout: int = 10

    @classmethod
    def load(cls) -> "Settings":
        def _int(key: str, default: int) -> int:
            return int(os.getenv(key, str(default)))

        return cls(
            app_host=os.getenv("APP_HOST", cls.model_fields["app_host"].default),
            app_port=_int("APP_PORT", cls.model_fields["app_port"].default),
            mongodb_uri=os.getenv("MONGODB_URI") or None,
            mongodb_db=os.getenv("MONGODB_DB") or None,
            event_log_buffer_size=_int(
                "EVENT_LOG_BUFFER_SIZE",
                cls.model_fields["event_log_buffer_size"].default,
            ),
            ssh_host=os.getenv("SSH_HOST", cls.model_fields["ssh_host"].default),
            ssh_port=_int("SSH_PORT", cls.model_fields["ssh_port"].default),
            ssh_user=os.getenv("SSH_USER", cls.model_fields["ssh_user"].default),
            ssh_key_path=os.getenv("SSH_KEY_PATH", cls.model_fields["ssh_key_path"].default),
            ssh_connect_timeout=_int(
                "SSH_CONNECT_TIMEOUT",
                cls.model_fields["ssh_connect_timeout"].default,
            ),
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.load()
