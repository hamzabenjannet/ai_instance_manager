from __future__ import annotations

from pydantic import BaseModel, Field


class TypeTextRequest(BaseModel):
    text: str = Field(..., min_length=1)
    interval_seconds: float = Field(default=0.05, ge=0.0)


class PressKeyRequest(BaseModel):
    key: str = Field(..., min_length=1)
    interval_seconds: float = Field(default=0.05, ge=0.0)
