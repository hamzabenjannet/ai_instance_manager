from typing import Any

from pydantic import BaseModel, Field


class EventLog(BaseModel):
    id: str = Field(..., min_length=1)
    timestamp: str = Field(..., min_length=1)
    event_type: str = Field(..., min_length=1)
    status: str = Field(..., min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)
