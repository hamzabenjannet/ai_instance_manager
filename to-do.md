## Status

- Current repo contains FastAPI skeleton + routes/services/models scaffolding.
- MongoDB + RabbitMQ + YOLO are not implemented yet (only placeholders/stubs).
- Mouse/keyboard/screenshot services use `pyautogui` and persist screenshots to `output/screenshots/`.
- Requirements are now pinned heavily (including `pip`, `setuptools`, `wheel`).

## Done

- Created missing folders and files described in `folder_structure.md`.
- Registered routers in `main.py`.
- Removed `__init__.py` files (per request).
- Added `PyAutoGUI` to `requirements.txt`.
- Added screenshot persistence to `output/screenshots/`.
- Added mouse double-click support (`doubleLeft`).
- Added `output/` directories with `.gitkeep`/`.gitignore`.

## Next

1. Stabilize dependency installation (revisit `requirements.txt` pins and portability).
2. Fix error handling for mouse/screen services (no `print`, no `return str(e)`).
3. Implement MongoDB event logging (replace in-memory logger with Mongo-backed logger).
4. Add request/response models per endpoint (expand typing/validation).
5. Add real screen/mouse/keyboard implementations (permissions + runtime checks).
6. Define vision pipeline contracts (YOLO model loading, input/output formats, storage).
7. Add health checks for external deps (Mongo, RabbitMQ, Ollama).

## Last Validation (vns-server container)

- `python3 -m pip install -r requirements.txt`: OK (all requirements already satisfied)
- `uvicorn main:app --reload --host 0.0.0.0 --port 42014`: OK (startup complete)
- `python3 -m unittest discover -s tests -p 'test_*.py'`: OK (4 tests passed)
- PyAutoGUI-driven endpoints not yet validated end-to-end.

## Git Log (recent)

- `b4859bf` feat: add double-click support and screenshot persistence
- `88c0f86` chore: add empty .gitkeep files for output directories
- `30f4c41` chore: add tree.log to document project structure
- `e4a378d` docs: update installation instructions and requirements
- `d528f95` feat: add core services, routes, models, and tests for AI instance manager
- `180d9e2` refactor: move routes to top-level directory for better organization
- `9c5996c` feat: initialize FastAPI project for AI instance manager

## Issues / Notes

- `screen_service.take_screenshot_base64()` returns `str(e)` on failure; API will treat it as base64 data.
- `mouse_service.click()` prints errors instead of raising/logging; failures can look like success.
- `requirements.txt` pins `pip/setuptools/wheel`; may be unnecessary and can cause conflicts.

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
