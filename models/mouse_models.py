from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class MousePositionResponse(BaseModel):
    x: int = Field(..., ge=0)
    y: int = Field(..., ge=0)


class MoveMouseRequest(BaseModel):
    x: int = Field(..., ge=0)
    y: int = Field(..., ge=0)


class MouseClickRequest(BaseModel):
    button: Literal["left", "right", "middle"] = "left"
