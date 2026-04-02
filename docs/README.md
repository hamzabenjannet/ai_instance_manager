# AI Instance Manager (FastAPI)

## Project Overview

AI Instance Manager is a FastAPI application that provides “remote hands” for an agent by controlling a desktop session (typically the `vnc-server` container in this repository). It exposes:

- Desktop control APIs (mouse and keyboard)
- Screen capture and retrieval APIs (screenshots + annotated images)
- Vision APIs (UI element detection over screenshots)
- SSH APIs (health check + remote command execution into the same container)
- MCP (Model Context Protocol) server endpoints (SSE transport) so tools-aware clients can call these capabilities as MCP tools

This app is designed for environments where an agent needs deterministic interaction with a GUI: take a screenshot, detect elements, and then click/type reliably.

Key design decisions:

- Layered structure: routers validate and shape HTTP behavior; services implement side effects (pyautogui, filesystem, paramiko, ML inference).
- “Local filesystem as artifact store”: screenshots and annotated images are stored under `output/` to enable debugging and offline inspection.
- Optional external dependencies: MongoDB is currently “configurable but not required” (there is no active Mongo client yet).

## Architecture

### Architecture style

Layered / modular:

- **API (routers)**: `routes/` contains FastAPI routers per domain area.
- **Domain/services**: `services/` contains the implementation of side-effecting operations.
- **Configuration**: `app/config.py` loads settings from environment variables.
- **(Planned) persistence/logging**: `app/database.py` is a stub handle for MongoDB configuration; `app/logging_service.py` contains a commented prototype for an in-memory event log.
- **MCP server**: `mcp_server/` defines the MCP tool inventory, tool dispatcher, and transports (SSE + stdio).

### Request flow (example: vision)

1. Client requests a screenshot (`GET /screen/screenshot`)
2. Screenshot is saved to `output/screenshots/` and optionally returned as base64
3. Client requests detection (`POST /vision/detect`)
4. Vision service loads weights (if present) and returns bounding boxes; optionally saves annotated output to `output/annotated/`

### Folder structure

```
apps/ai_instance_manager/
  app/
    config.py              # env-based settings loader
    database.py            # MongoDB config handle (stub, optional)
    logging_service.py     # (planned) event logging prototype (currently commented)
  docs/
    README.md              # this document
  mcp_server/
    __main__.py            # stdio entrypoint
    server.py              # MCP tools + dispatcher + SSE app builder
  models/
    event_log_model.py     # event log model (future logging)
    keyboard_models.py     # request/response schemas
    mouse_models.py        # request/response schemas
  output/
    screenshots/           # saved screenshots
    annotated/             # annotated images (vision)
    json/                  # reserved for JSON outputs
  routes/
    health.py
    keyboard.py
    mouse.py
    screen.py
    ssh.py
    vision.py
  services/
    keyboard_service.py
    mouse_service.py
    screen_service.py
    ssh_service.py
    vision_service.py
  tests/                   # lightweight unittest checks (route registration)
  weights/                 # ML weights (ignored in git)
  main.py                  # FastAPI app entrypoint (mounts routers and MCP SSE)
  run.sh                   # convenience runner for the VNC container env
  requirements.txt
  download_models_and_weights.py
```

## Tech Stack

Core API:

- FastAPI + Starlette (routing, OpenAPI)
- Uvicorn (ASGI server)
- Pydantic v2 (request/response validation)

Desktop automation:

- PyAutoGUI (mouse/keyboard + screenshots)

Vision:

- Ultralytics YOLOv8 (UI element detection)
- OpenCV (heuristic UI region detection)
- Transformers + Torch (optional Florence-2 caption enrichment)
- HuggingFace Hub (weight download utility)

Remote control / integration:

- Paramiko (SSH command execution)
- MCP Python SDK + SSE transport (`mcp`, `sse-starlette`)

## Installation & Setup

### Prerequisites

Minimum requirements:

- Python 3.11
- A desktop session accessible to PyAutoGUI (VNC/X11). Pure headless hosts need Xvfb or a VNC desktop.

Recommended (for vision):

- CPU torch is supported (already pinned in `requirements.txt`). GPU requires additional container/driver setup.
- Network access to HuggingFace to download model weights.

### Environment variables (.env example)

Settings are loaded by `app/config.py` from environment variables.

Example `.env` (app-level) contents:

```env
APP_HOST=0.0.0.0
APP_PORT=42014

MONGODB_URI=
MONGODB_DB=

EVENT_LOG_BUFFER_SIZE=1000

SSH_HOST=127.0.0.1
SSH_PORT=42012
SSH_USER=root
SSH_KEY_PATH=/root/.ssh/id_rsa
SSH_CONNECT_TIMEOUT=10

APP_LOG_LEVEL=DEBUG
```

### Local setup (standalone)

From the repo root (or the `apps/ai_instance_manager` folder):

```bash
cd apps/ai_instance_manager
conda create -n ai_instance_manager python=3.11 -c conda-forge -y
conda activate ai_instance_manager
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 42014 --log-level debug
```

Open:

- Swagger UI: `http://localhost:42014/docs`
- Health: `http://localhost:42014/health`

### Docker setup (recommended for this repository)

This repository’s `docker-compose.yaml` includes a VNC desktop container (`container-service-vnc-server`) and maps relevant ports:

- noVNC UI: `42010`
- VNC port: `42011`
- SSH: `42012`
- FastAPI: `42014`

From `infrastructure/`:

```bash
docker compose --profile minimal up -d container-service-vnc-server
```

Then open the VNC desktop via noVNC:

- `http://localhost:42010`

Inside the VNC container, run:

```bash
cd /config/workspace/projects/apps/ai_instance_manager
bash ./run.sh
```

### Download vision weights

YOLO icon detection weights are required when `use_yolo=true` in `POST /vision/detect`.

```bash
cd apps/ai_instance_manager
conda activate ai_instance_manager
python3 download_models_and_weights.py --detect-only
```

To also download Florence-2 weights (optional enrichment):

```bash
python3 download_models_and_weights.py
```

If you need a HuggingFace token for rate limits/private access, set it at runtime and do not commit it:

```bash
export HF_TOKEN="..."
```

## Configuration

### Current configuration model

All runtime config is environment-variable driven.

Supported keys and defaults (from `app/config.py`):

| Variable                |             Default | Description                                |
| ----------------------- | ------------------: | ------------------------------------------ |
| `APP_HOST`              |           `0.0.0.0` | Host for uvicorn/FastAPI                   |
| `APP_PORT`              |             `42014` | Port for uvicorn/FastAPI                   |
| `MONGODB_URI`           |               empty | MongoDB connection string (optional)       |
| `MONGODB_DB`            |               empty | MongoDB database name (optional)           |
| `EVENT_LOG_BUFFER_SIZE` |              `1000` | Planned event log buffer sizing            |
| `SSH_HOST`              |         `127.0.0.1` | SSH host                                   |
| `SSH_PORT`              |             `42012` | SSH port (VNC container sshd in this repo) |
| `SSH_USER`              |              `root` | SSH username                               |
| `SSH_KEY_PATH`          | `/root/.ssh/id_rsa` | Private key path used by paramiko          |
| `SSH_CONNECT_TIMEOUT`   |                `10` | SSH connect timeout (seconds)              |
| `APP_LOG_LEVEL`         |             `DEBUG` | App log level (also respects `LOG_LEVEL`)  |

### Environments (dev/staging/prod)

The code does not currently include explicit environment profiles; the recommended approach is:

- Use separate `.env` files per environment (dev/staging/prod)
- Inject secrets via your platform secret store (not in files)
- Run uvicorn without `--reload` in non-dev environments

## API Documentation

### OpenAPI / Swagger

- Swagger UI: `GET /docs`
- OpenAPI schema: `GET /openapi.json`

### Main endpoints

Base URL examples below assume: `http://localhost:42014`.

#### Health

`GET /health`

Example response:

```json
{
  "status": "ok",
  "started_at": "2026-04-02T10:20:30.123456+00:00",
  "mongodb_configured": false,
  "ssh": { "ssh_connected": true, "host": "127.0.0.1", "port": 42012 },
  "mcp_sse_endpoint": "/mcp/sse",
  "mcp_messages_endpoint": "/mcp/messages"
}
```

#### Mouse

- `GET /mouse/position` → `{ "x": int, "y": int }`
- `POST /mouse/move` with `{ "x": int, "y": int }` → `{ "status": "ok" }`
- `POST /mouse/click` with `{ "button": "left" | "right" | "middle" | "doubleLeft" }` → `{ "status": "ok" }`

```bash
curl -s http://localhost:42014/mouse/position
curl -s -X POST http://localhost:42014/mouse/move -H 'content-type: application/json' -d '{"x":100,"y":120}'
curl -s -X POST http://localhost:42014/mouse/click -H 'content-type: application/json' -d '{"button":"left"}'
```

#### Keyboard

- `POST /keyboard/type` with `{ "text": string, "interval_seconds": number }` → `{ "status": "ok" }`
- `POST /keyboard/press` with `{ "key": string, "interval_seconds": number }` → `{ "status": "ok" }`

```bash
curl -s -X POST http://localhost:42014/keyboard/type -H 'content-type: application/json' -d '{"text":"hello","interval_seconds":0.02}'
curl -s -X POST http://localhost:42014/keyboard/press -H 'content-type: application/json' -d '{"key":"enter","interval_seconds":0.02}'
```

#### Screen

- `GET /screen/size` → `{ "width": int, "height": int }`
- `GET /screen/screenshot?encoded_base64=true`
  - Returns `image_name` saved to `output/screenshots/`
  - Returns base64 PNG if `encoded_base64=true`
- `GET /screen/image?image_name=<filename>` → base64 PNG from `output/screenshots/`
- `GET /screen/annotated-image?image_name=<filename>` → base64 PNG from `output/annotated/`

```bash
curl -s "http://localhost:42014/screen/screenshot?encoded_base64=false"
```

#### Vision

`POST /vision/detect`

Request body (key fields):

```json
{
  "image_name": "screenshot_2026-03-10_14-44-52.png",
  "use_yolo": true,
  "use_cv2_heuristic": true,
  "use_florence": false,
  "confidence_threshold": 0.25,
  "annotate": true,
  "use_gpu": false
}
```

Typical flow:

1. `GET /screen/screenshot` to generate an image
2. `POST /vision/detect` with the returned `image_name`

#### SSH

- `GET /ssh/health`
  - Health check for SSH connectivity; includes a banner probe to help diagnose “open port but not SSH”.
- `POST /ssh/run` with `{ "command": string, "timeout": int }`
  - Executes arbitrary shell command on the container and returns stdout/stderr/exit code

```bash
curl -s http://localhost:42014/ssh/health
curl -s -X POST http://localhost:42014/ssh/run -H 'content-type: application/json' -d '{"command":"uname -a","timeout":30}'
```

Authentication:

- No authentication/authorization is implemented yet. See the Security section and roadmap below.

## Data Layer

Current state:

- MongoDB config is supported via `MONGODB_URI` and `MONGODB_DB`, but the code currently only reports whether MongoDB is configured (`app/database.py`) and does not create a client or perform reads/writes.
- There is no migration framework configured (no ODM/ORM in use).

Recommended evolution path:

- Choose one:
  - MongoDB with an ODM (e.g., Beanie) and `motor` client for async I/O
  - SQL database (Postgres) with SQLAlchemy + Alembic migrations
- Define clear persistence boundaries:
  - repositories for DB access
  - services for business logic
  - routers for HTTP behavior only

## Testing

Current state:

- `tests/` uses `unittest` and primarily checks that routes are registered.

Run tests:

```bash
cd apps/ai_instance_manager
python3 -m unittest
```

Recommended strategy (roadmap):

- Unit tests for services (mouse/keyboard/screen/vision/ssh) with dependency seams/mocks
- Integration tests for HTTP routes using FastAPI `TestClient`
- End-to-end tests inside the VNC container (because desktop automation is environment-dependent)
- Coverage target: enforce a minimum threshold once test suite grows

## Code Quality & Standards

Current state:

- No repo-wide lint/format/typecheck tooling is configured for this app.

Recommended baseline (roadmap):

- Formatting: `black`
- Linting: `ruff`
- Typing: `mypy` (or `pyright`)
- Security scanning: `pip-audit` (CI) + Dependabot/Renovate for dependency updates
- Commit conventions: Conventional Commits (`feat:`, `fix:`, `chore:`)

## Deployment

### Production run command

For production-like environments:

- Disable `--reload`
- Run multiple workers if appropriate for the workload (note: GUI automation is often not safe to parallelize without careful isolation)

Example:

```bash
uvicorn main:app --host 0.0.0.0 --port 42014 --log-level info
```

### Container considerations

- This service is typically coupled to the desktop session; deploy it in the same container/VM as the GUI to avoid display/input issues.
- Restrict network exposure (private network only) because it can control a desktop and run commands.

## Logging (Roadmap)

Target: introduce production-grade logging suitable for troubleshooting, auditability, and monitoring.

1. Structured logs (JSON)
   - Switch from printf-style logs to JSON logs (e.g., `structlog` or standard logging JSON formatter)
   - Define a stable schema: `timestamp`, `level`, `service`, `route`, `request_id`, `trace_id`, `event_type`, `duration_ms`
2. Correlation IDs
   - Add middleware to generate/propagate `X-Request-Id`
   - Include request id in every log line
3. Centralized logging
   - Send logs to an aggregator (ELK/OpenSearch, Loki, or Cloud provider logging)
   - Add retention and redaction policies
4. Request/response tracing
   - Trace slow endpoints (vision, ssh) and include timings and error categories
5. Performance monitoring
   - Emit metrics (latency histograms, error rates, model inference time)
   - Alerting on failure conditions (SSH down, vision weight missing)

## Dynamic Configuration (Roadmap)

Target: store selected configuration in the database and hot-reload without service restart.

1. Configuration stored in database
   - Create a `config` collection/table (key/value + type + version + scope)
   - Add validation schema and audit trail (who/when changed)
2. Hot-reload
   - Add an in-memory cache with TTL
   - Add a watcher mechanism (MongoDB change streams or a polling strategy)
   - Apply safe reload boundaries (do not reload secrets into logs; validate before apply)
3. Feature flags
   - Add feature flag evaluation (per env/tenant/workspace)
   - Gate risky capabilities (`/ssh/run`, Florence captioning, GPU)
4. Admin interface
   - Add protected admin endpoints for config management
   - Prefer a separate admin UI service or integrate with an internal tool (only behind auth)

## Security

This service is powerful by design (desktop control + arbitrary SSH commands). A secure deployment is mandatory.

### Current baseline (what exists now)

- Input validation via Pydantic models on most POST routes.
- Some filesystem hardening in image retrieval: `screen_service.get_image()` and `get_annotated_image()` restrict `image_name` to a basename to reduce path traversal risk.
- No authn/authz, no rate limiting, no CORS policy, and no secrets management integration.

### Immediate hardening checklist (recommended)

1. Authentication (JWT or OAuth2)
   - Add `fastapi.security` (OAuth2 Password Flow) or integrate with your IdP (OIDC)
2. Authorization (roles/permissions)
   - Introduce roles such as `viewer`, `operator`, `admin`
   - Restrict dangerous endpoints: `/ssh/run`, mouse/keyboard control, MCP tool calls
3. Rate limiting
   - Add rate limiting middleware (e.g., Redis-backed) to prevent abuse
4. CORS configuration
   - Restrict origins, methods, and headers; avoid wildcard in production
5. Secrets management
   - Store secrets in environment or secret store (Vault/KMS), never in git
6. HTTPS enforcement
   - Terminate TLS at a reverse proxy (nginx/traefik) or platform load balancer
7. Dependency vulnerability scanning
   - Add `pip-audit` and/or SCA tooling in CI

### Protection against common attacks

- SQL injection: not applicable today (no SQL), but still validate inputs and keep DB drivers updated.
- XSS/CSRF: if you add a browser-based admin UI, apply CSRF protections and secure cookies; avoid reflecting user input in HTML.
- Command injection: `/ssh/run` is intentionally a remote shell. Treat it as admin-only and isolate it behind strong auth and network controls.

## Observability (Recommended)

- Health checks:
  - `GET /health` already provides SSH status and MCP endpoints.
- Metrics:
  - Add Prometheus endpoint (`/metrics`) and track request duration + error counts.
- Tracing:
  - Add OpenTelemetry instrumentation for FastAPI + paramiko/vision spans.

## Contribution Guidelines

Recommended workflow for a professional environment:

- Branching: `main` protected, feature branches `feat/<topic>`, bugfix branches `fix/<topic>`
- PR requirements:
  - small, reviewable diffs
  - tests added/updated
  - security review for any change affecting `/ssh/run`, MCP, or desktop control
- Review process:
  - at least one approving review
  - no direct pushes to `main`

## FAQ / Troubleshooting

### `/ssh/health` returns `unpack requires a buffer of 4 bytes`

This indicates paramiko received an incomplete/invalid SSH handshake. Common causes:

- SSH daemon not running on the configured port
- Wrong `SSH_PORT` (port is open but not SSH)
- Wrong key type/path (e.g., only `id_ed25519` exists while config points to `id_rsa`)

`/ssh/health` includes a probe result so you can confirm whether the port actually speaks SSH (banner starts with `SSH-`).

### `pyautogui is not installed or not available on this host`

- Ensure dependencies are installed (`pip install -r requirements.txt`).
- Ensure you run inside a real desktop session (VNC/X11). Pure headless environments need Xvfb or a VNC desktop.

### Vision weights missing

If you see errors about missing weights under `weights/`, run:

```bash
cd apps/ai_instance_manager
python3 download_models_and_weights.py --detect-only
```

### Annotated image not found

`/screen/annotated-image` reads from `output/annotated/`. You only get annotated images when you run `POST /vision/detect` with `annotate=true`.

## MCP Server

The MCP server is implemented in `mcp_server/server.py`.

### SSE transport

The FastAPI app mounts the MCP SSE application under `/mcp`:

- SSE stream: `GET /mcp/sse`
- Client messages: `POST /mcp/messages/`

### Stdio transport (local tools clients)

Run the stdio server (from `apps/ai_instance_manager`):

```bash
python3 -m mcp_server
```

### Tools

Tool inventory is defined in `mcp_server/server.py` under `@mcp_server.list_tools()`. Current tools include:

- `mouse_get_position`, `mouse_move`, `mouse_click`
- `keyboard_type`, `keyboard_press`
- `screen_get_size`, `screen_take_screenshot`
- `vision_detect`
- `ssh_health`, `ssh_run_command`
