from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BoundingBox:
    x: int
    y: int
    width: int
    height: int
    label: str | None = None
    score: float | None = None


def detect_ui_elements(_: str | None = None) -> list[BoundingBox]:
    raise RuntimeError("vision dependencies are not installed or not configured")
