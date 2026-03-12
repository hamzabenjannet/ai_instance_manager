## Status

- Current repo contains FastAPI skeleton + routes/services/models scaffolding.
- MongoDB + RabbitMQ are not implemented yet (only placeholders/stubs).
- Vision detection is implemented (YOLOv8 via `ultralytics` + optional OpenCV heuristic detection).
- Florence-2 caption enrichment is implemented but disabled by default (CPU cost).
- Mouse/keyboard/screenshot services use `pyautogui` and persist screenshots to `output/screenshots/`.
- Weights live under `weights/` and annotated images under `output/annotated/`.
- Requirements are now pinned heavily (including `pip`, `setuptools`, `wheel`, `torch+cpu`, `easyocr`, `transformers`).

## Done

- Created missing folders and files described in `folder_structure.md`.
- Registered routers in `main.py`.
- Removed `__init__.py` files (per request).
- Added `PyAutoGUI` to `requirements.txt`.
- Added screenshot persistence to `output/screenshots/`.
- Added mouse double-click support (`doubleLeft`).
- Added `output/` directories with `.gitkeep`/`.gitignore`.
- Implemented `/vision/detect` endpoint using screenshot file input (`image_name`).
- Added model/weights download scripts (`download_models_and_weights.py/.sh`).
- Added GPU toggle for YOLO inference (`use_gpu` flag).
- Added debug logging + strict error propagation for mouse/screen/keyboard routes and services.
- Aligned `/keyboard/press` to use `interval_seconds`.
- Added debug logging + strict error propagation for vision routes and services.
- Added simple debug logs across health/config/database/event logging.

## Next

1. Stabilize dependency installation (revisit `requirements.txt` pins and portability).
2. Split requirements into base vs vision extras (avoid huge default install).
3. Implement MongoDB event logging (replace in-memory logger with Mongo-backed logger).
4. Add health checks for external deps (Mongo, RabbitMQ, Ollama, vision weights).
5. Add `/vision/detect` smoke test flow (document + minimal test case).
6. Remove token placeholder from `download_models_and_weights.sh` and document `HF_TOKEN` usage.

## Last Validation (vns-server container)

- `python3 -m pip install -r requirements.txt`: OK (all requirements already satisfied)
- `uvicorn main:app --reload --host 0.0.0.0 --port 42014`: OK (startup complete)
- `python3 -m unittest discover -s tests -p 'test_*.py'`: OK (4 tests passed)
- `GET /health`: OK (`status=ok`)
- `GET /mouse/position`: OK (returns x/y)
- `GET /screen/size`: OK (returns width/height)
- `GET /screen/screenshot`: OK (returns base64 PNG). Note: `curl: (23) Failure writing output to destination` is expected when piping into `head` (head closes the pipe early).

## Git Log (recent)

- `0a6b80c` fix(vision): disable florence by default to avoid CPU slowdown
- `33dbe59` feat(vision): integrate Florence-2 for natural-language UI element captioning
- `20c02ad` chore: update model weights and dependencies for icon detection
- `f862ca7` docs: update to-do.md with implemented endpoints and known issues
- `d8d5630` feat(vision): add GPU support and improve detection serialization
- `9834c1a` feat(vision): add YOLOv8 and OpenCV UI detection service
- `8ff6ea0` chore: ignore .DS_Store files in git
- `6267290` chore: add output directories for json and screenshots
- `52cbe66` fix(keyboard): set default typing interval to 0.05 seconds
- `5a2b371` docs: update to-do.md with recent changes and future tasks
- `b4859bf` feat: add double-click support and screenshot persistence

## Issues / Notes

- If `logger.debug(...)` from routes/services does not show, set `APP_LOG_LEVEL=DEBUG` (or `LOG_LEVEL=DEBUG`) before starting uvicorn.
- `requirements.txt` pins `pip/setuptools/wheel`; may be unnecessary and can cause conflicts.
- `requirements.txt` includes both `opencv-python` and `opencv-python-headless`; pick one for the container.
- `download_models_and_weights.sh` contains an `HF_TOKEN` placeholder; do not commit real tokens.

## Commands to Run (in vns-server container)

### Install

```bash
cd ai_instance_manager
python3 -m pip install -r requirements.txt
```

### Validate PyAutoGUI import

```bash
cd ai_instance_manager
python3 -c "import pyautogui; print('pyautogui', pyautogui.__version__)"
```

### Quick endpoint smoke test (manual)

```bash
curl -sS http://localhost:42014/health
curl -sS http://localhost:42014/mouse/position
curl -sS http://localhost:42014/screen/size
curl -sS http://localhost:42014/screen/screenshot | head -c 200 && echo
```

### Keyboard smoke test (manual)

```bash
curl -sS http://localhost:42014/keyboard/type \
  -H 'Content-Type: application/json' \
  -d '{"text":"hello","interval_seconds":0.05}'
```

```bash
curl -sS http://localhost:42014/keyboard/press \
  -H 'Content-Type: application/json' \
  -d '{"key":"enter","interval_seconds":0.05}'
```

### Screenshot response size (avoid pipe errors)

```bash
curl -sS http://localhost:42014/screen/screenshot -o /tmp/screenshot.json
python3 -c "import json; d=json.load(open('/tmp/screenshot.json')); print('encoding=', d.get('encoding')); print('base64_len=', len(d.get('data','')))"
```

### Vision detect (use latest screenshot filename)

```bash
ls -1t output/screenshots | head -n 1
```

```bash
curl -sS http://localhost:42014/vision/detect \
  -H 'Content-Type: application/json' \
  -d '{"image_name":"output/screenshots/REPLACE_WITH_FILENAME.png","use_yolo":true,"use_cv2_heuristic":true,"confidence_threshold":0.25,"annotate":true,"use_gpu":false}' \
  | head -c 400 && echo
```

### Download weights (OmniParser v2)

```bash
cd ai_instance_manager
python3 download_models_and_weights.py --detect-only
```

### Run API

```bash
cd ai_instance_manager
uvicorn main:app --reload --host 0.0.0.0 --port 42014
```

### Run tests

```bash
cd ai_instance_manager
python3 -m unittest discover -s tests -p 'test_*.py'
```
