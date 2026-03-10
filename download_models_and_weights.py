"""
Download OmniParser V2 weights from HuggingFace.

Phase 1 — icon_detect  : YOLO fine-tuned for UI element detection (used immediately)
Phase 2 — icon_caption : Florence-2 for natural-language element description (used later)

Usage:
    python3 download_models_and_weights.py              # download everything
    python3 download_models_and_weights.py --detect-only # Phase 1 only
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from huggingface_hub import hf_hub_download


REPO = "microsoft/OmniParser-v2.0"
LOCAL_DIR = Path("weights")

ICON_DETECT_FILES = [
    "icon_detect/model.pt",
    "icon_detect/model.yaml",
    "icon_detect/train_args.yaml",
]

ICON_CAPTION_FILES = [
    "icon_caption/config.json",
    "icon_caption/generation_config.json",
    "icon_caption/model.safetensors",
]


def download_file(file_path: str) -> bool:
    dest = LOCAL_DIR / file_path
    if dest.exists():
        print(f"  [skip] {file_path}  (already exists)")
        return True

    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"  [download] {file_path}")

    try:
        hf_hub_download(
            repo_id=REPO,
            filename=file_path,
            local_dir=str(LOCAL_DIR),
            # local_dir_use_symlinks=False,
        )
        return True
    except Exception as e:
        print(f"  [error] {file_path}: {e}", file=sys.stderr)
        return False


def rename_icon_caption() -> None:
    src = LOCAL_DIR / "icon_caption"
    dst = LOCAL_DIR / "icon_caption_florence"
    if src.exists() and not dst.exists():
        src.rename(dst)
        print(f"  [rename] icon_caption → icon_caption_florence")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download OmniParser V2 weights")
    parser.add_argument(
        "--detect-only",
        action="store_true",
        help="Download Phase 1 (icon_detect) only — skip Florence-2 caption model",
    )
    args = parser.parse_args()

    files_to_download = ICON_DETECT_FILES
    if not args.detect_only:
        files_to_download = files_to_download + ICON_CAPTION_FILES

    print(f"Repo  : {REPO}")
    print(f"Target: {LOCAL_DIR.resolve()}\n")

    failed: list[str] = []
    for file_path in files_to_download:
        if not download_file(file_path):
            failed.append(file_path)

    rename_icon_caption()

    if failed:
        print(f"\n[warning] {len(failed)} file(s) failed to download:", file=sys.stderr)
        for f in failed:
            print(f"  - {f}", file=sys.stderr)
        sys.exit(1)

    print(f"\nDone. Weights saved to {LOCAL_DIR.resolve()}/")


if __name__ == "__main__":
    main()