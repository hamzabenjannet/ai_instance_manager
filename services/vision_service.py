from __future__ import annotations

import base64
import os
from dataclasses import dataclass, field
from pathlib import Path


SCREENSHOTS_DIR = Path("output/screenshots")
ANNOTATED_DIR = Path("output/annotated")


@dataclass(frozen=True)
class BoundingBox:
    x: int           # top-left x
    y: int           # top-left y
    width: int
    height: int
    label: str | None = None
    score: float | None = None
    center_x: int = 0
    center_y: int = 0
    source: str = "yolo"   # "yolo" | "cv2_heuristic"

    def to_dict(self) -> dict:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "center_x": self.center_x,
            "center_y": self.center_y,
            "label": self.label,
            "score": round(self.score, 4) if self.score is not None else None,
            "source": self.source,
        }


def _make_box(x1: int, y1: int, x2: int, y2: int, label: str, score: float, source: str = "yolo") -> BoundingBox:
    w = x2 - x1
    h = y2 - y1
    return BoundingBox(
        x=x1,
        y=y1,
        width=w,
        height=h,
        label=label,
        score=score,
        center_x=x1 + w // 2,
        center_y=y1 + h // 2,
        source=source,
    )


def _resolve_image_path(image_name: str) -> Path:
    """
    Resolve image_name to an absolute path.
    Accepts:
      - bare filename:  "screenshot_2026-03-10_14-44-52.png"
      - relative path:  "output/screenshots/screenshot_....png"
      - absolute path:  "/config/workspace/.../screenshot_....png"
    """
    p = Path(image_name)
    if p.is_absolute() and p.exists():
        return p
    # try relative to cwd
    if p.exists():
        return p.resolve()
    # try inside screenshots dir
    candidate = SCREENSHOTS_DIR / p.name
    if candidate.exists():
        return candidate.resolve()
    raise FileNotFoundError(f"Image not found: {image_name!r}. Looked in cwd and {SCREENSHOTS_DIR}/")


def _yolo_detect(image_path: Path) -> list[BoundingBox]:
    """Run YOLOv8 nano on the image. Downloads weights on first run (~6 MB)."""
    try:
        from ultralytics import YOLO
    except ImportError as e:
        raise RuntimeError(
            "ultralytics is not installed. Run: pip install ultralytics"
        ) from e

    model = YOLO("yolov8n.pt")   # nano — fastest; auto-downloads on first use
    results = model(str(image_path), verbose=False)

    boxes: list[BoundingBox] = []
    for result in results:
        for box in result.boxes:
            x1, y1, x2, y2 = (int(v) for v in box.xyxy[0].tolist())
            score = float(box.conf[0])
            cls_id = int(box.cls[0])
            label = result.names.get(cls_id, str(cls_id))
            boxes.append(_make_box(x1, y1, x2, y2, label, score, source="yolo"))

    return boxes


def _cv2_ui_detect(image_path: Path) -> list[BoundingBox]:
    """
    Heuristic UI element detector using OpenCV.
    Finds rectangular regions that look like windows, panels, buttons,
    and list rows — things COCO-YOLO won't label as UI.
    """
    try:
        import cv2
        import numpy as np
    except ImportError as e:
        raise RuntimeError(
            "opencv-python is not installed. Run: pip install opencv-python-headless"
        ) from e

    img = cv2.imread(str(image_path))
    if img is None:
        raise RuntimeError(f"cv2 could not read image: {image_path}")

    h_img, w_img = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    boxes: list[BoundingBox] = []

    # ── 1. Edge-based large region detection (windows / panels) ──────────
    edges = cv2.Canny(gray, threshold1=30, threshold2=100)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    dilated = cv2.dilate(edges, kernel, iterations=2)
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area = w * h
        # filter: must cover at least 3% of screen and be reasonably rectangular
        if area < 0.03 * w_img * h_img:
            continue
        aspect = w / h if h > 0 else 0
        if aspect < 0.2 or aspect > 20:
            continue
        score = min(1.0, area / (0.5 * w_img * h_img))
        label = _classify_region(w, h, w_img, h_img)
        boxes.append(_make_box(x, y, x + w, y + h, label, score, source="cv2_region"))

    # ── 2. Horizontal stripe detection (title bars, menu bars, list rows) ─
    # Look for thin horizontal bands with high contrast at top/bottom edges
    sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    mag = np.sqrt(sobel_x ** 2 + sobel_y ** 2).astype(np.uint8)
    _, thresh = cv2.threshold(mag, 40, 255, cv2.THRESH_BINARY)

    # horizontal projection — find rows with strong horizontal edges
    h_proj = np.sum(thresh, axis=1)
    mean_proj = float(np.mean(h_proj))
    strong_rows = np.where(h_proj > mean_proj * 3)[0]

    if len(strong_rows) > 0:
        # cluster consecutive rows into stripe regions
        groups: list[list[int]] = []
        current: list[int] = [strong_rows[0]]
        for r in strong_rows[1:]:
            if r - current[-1] <= 4:
                current.append(r)
            else:
                groups.append(current)
                current = [r]
        groups.append(current)

        for grp in groups:
            y_top = grp[0]
            y_bot = grp[-1]
            stripe_h = y_bot - y_top + 1
            if stripe_h < 8 or stripe_h > h_img * 0.15:
                continue
            # horizontal extent: use full width for title/menu bars
            label = "title_bar" if y_top < h_img * 0.05 else "ui_strip"
            boxes.append(_make_box(0, y_top, w_img, y_bot, label, 0.6, source="cv2_stripe"))

    return boxes


def _classify_region(w: int, h: int, w_img: int, h_img: int) -> str:
    """Heuristic label for a detected rectangular region."""
    area_ratio = (w * h) / (w_img * h_img)
    aspect = w / h if h > 0 else 1

    if area_ratio > 0.25:
        return "window"
    if h < h_img * 0.06 and aspect > 3:
        return "toolbar"
    if w < w_img * 0.25 and h < h_img * 0.08:
        return "button"
    if aspect > 4 and h < 40:
        return "menu_bar"
    return "panel"


def _annotate_and_save(image_path: Path, boxes: list[BoundingBox]) -> Path:
    """Draw bounding boxes on a copy of the image and save to output/annotated/."""
    try:
        import cv2
    except ImportError:
        return image_path  # skip annotation silently if cv2 not available

    ANNOTATED_DIR.mkdir(parents=True, exist_ok=True)
    img = cv2.imread(str(image_path))
    if img is None:
        return image_path

    color_map = {
        "yolo": (0, 255, 0),          # green
        "cv2_region": (255, 128, 0),  # orange
        "cv2_stripe": (0, 128, 255),  # blue
    }

    for box in boxes:
        color = color_map.get(box.source, (200, 200, 200))
        cv2.rectangle(img, (box.x, box.y), (box.x + box.width, box.y + box.height), color, 2)
        label_text = f"{box.label} {box.score:.2f}" if box.score is not None else (box.label or "")
        cv2.putText(img, label_text, (box.x, max(box.y - 5, 12)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)
        # draw center dot
        cv2.circle(img, (box.center_x, box.center_y), 3, color, -1)

    out_path = ANNOTATED_DIR / ("annotated_" + image_path.name)
    cv2.imwrite(str(out_path), img)
    return out_path


def detect_ui_elements(
    image_name: str,
    use_yolo: bool = True,
    use_cv2_heuristic: bool = True,
    confidence_threshold: float = 0.25,
    annotate: bool = True,
) -> dict:
    """
    Main entry point for vision detection.

    Args:
        image_name:           filename or path to image in output/screenshots/
        use_yolo:             run YOLOv8 detection
        use_cv2_heuristic:    run OpenCV heuristic UI detection
        confidence_threshold: minimum score to include a box
        annotate:             save annotated image to output/annotated/

    Returns:
        dict with keys: boxes (list[dict]), annotated_path (str | None), image_path (str)
    """
    image_path = _resolve_image_path(image_name)

    all_boxes: list[BoundingBox] = []
    errors: list[str] = []

    if use_yolo:
        try:
            yolo_boxes = _yolo_detect(image_path)
            all_boxes.extend(yolo_boxes)
        except RuntimeError as e:
            errors.append(f"yolo: {e}")

    if use_cv2_heuristic:
        try:
            cv2_boxes = _cv2_ui_detect(image_path)
            all_boxes.extend(cv2_boxes)
        except RuntimeError as e:
            errors.append(f"cv2: {e}")

    if not all_boxes and errors:
        raise RuntimeError("; ".join(errors))

    # filter by confidence
    filtered = [b for b in all_boxes if b.score is None or b.score >= confidence_threshold]

    annotated_path: str | None = None
    if annotate and filtered:
        try:
            ann = _annotate_and_save(image_path, filtered)
            annotated_path = str(ann)
        except Exception:
            pass  # annotation is best-effort

    return {
        "image_path": str(image_path),
        "annotated_path": annotated_path,
        "count": len(filtered),
        "boxes": [b.to_dict() for b in filtered],
        "errors": errors,
    }