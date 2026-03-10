## Status

- Current repo contains FastAPI skeleton + routes/services/models scaffolding.
- MongoDB + RabbitMQ + YOLO are not implemented yet (only placeholders/stubs).
- Mouse/keyboard/screenshot services currently expect `pyautogui` to be installed at runtime.

## Done

- Created missing folders and files described in `folder_structure.md`.
- Registered routers in `main.py`.
- Removed `__init__.py` files (per request).

## Next

1. Stabilize dependency installation (ensure `requirements.txt` installs cleanly in container).
2. Implement MongoDB event logging (replace in-memory logger with Mongo-backed logger).
3. Add request/response models per endpoint (expand typing/validation).
4. Add real screen/mouse/keyboard implementations (permissions + runtime checks).
5. Define vision pipeline contracts (YOLO model loading, input/output formats, storage).
6. Add health checks for external deps (Mongo, RabbitMQ, Ollama).

## Last Validation (vns-server container)

- `python3 -m pip install -r requirements.txt`: OK (all requirements already satisfied)
- `uvicorn main:app --reload --host 0.0.0.0 --port 42014`: OK (startup complete)
- `python3 -m unittest discover -s tests -p 'test_*.py'`: OK (4 tests passed)

## Commands to Run (in vns-server container)

### Install

```bash
cd ai_instance_manager
python3 -m pip install -r requirements.txt
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
