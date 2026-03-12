```tree
ai_instance_manager/
│
├── main.py                                 # FastAPI app entry point + MCP SSE mount
├── requirements.txt                        # All dependencies
├── .env                                    # Environment variables (SSH, MongoDB, etc.)
├── .gitignore
├── README.md
├── run.sh                                  # Run uvicorn
├── roadmap.md
├── folder_structure.md                     # This file
├── claude_desktop_config_snippet.json      # Claude Desktop stdio config snippet
│
├── app/
│   ├── config.py                           # App + SSH settings from env
│   ├── logging_service.py                  # In-memory event log (shared by all layers)
│   └── database.py                         # MongoDB connection handle
│
├── mcp/                                    # MCP server (stdio + SSE)
│   ├── __main__.py                         # python -m mcp.server  →  stdio transport
│   └── server.py                           # Tool registry + dispatcher + SSE factory
│
├── routes/
│   ├── mouse.py                            # Mouse position, move, click
│   ├── keyboard.py                         # Type text, press key
│   ├── screen.py                           # Screenshot, screen size
│   ├── vision.py                           # YOLO + CV2 UI detection
│   ├── ssh.py                              # SSH / shell operations  ← NEW
│   └── health.py                           # Health check (includes SSH + MCP status)
│
├── services/
│   ├── mouse_service.py                    # PyAutoGUI mouse logic
│   ├── keyboard_service.py                 # PyAutoGUI keyboard logic
│   ├── screen_service.py                   # Screenshot logic
│   ├── vision_service.py                   # YOLO + Florence-2 + CV2 detection
│   └── ssh_service.py                      # Paramiko SSH/SFTP client  ← NEW
│
├── models/
│   ├── mouse_models.py
│   ├── keyboard_models.py
│   └── event_log_model.py
│
├── utils/
│   └── helpers.py
│
├── tests/
│   ├── test_mouse.py
│   ├── test_keyboard.py
│   ├── test_screen.py
│   ├── test_vision.py
│   └── test_ssh.py                         # SSH route + MCP mount tests  ← NEW
│
├── output/
│   ├── screenshots/                        # Raw screenshots (timestamped PNG)
│   ├── annotated/                          # YOLO-annotated images
│   └── json/                               # Reserved for future JSON outputs
│
└── weights/
    ├── icon_detect/                        # OmniParser YOLOv8 weights
    │   ├── model.pt
    │   ├── model.yaml
    │   └── train_args.yaml
    └── icon_caption_florence/              # Florence-2 captioning weights
        ├── config.json
        ├── generation_config.json
        └── model.safetensors
```

## MCP Transport endpoints

| Transport | How to connect                                       | Use case                        |
|-----------|------------------------------------------------------|---------------------------------|
| SSE       | `http://localhost:42014/mcp/sse`                     | n8n, web clients, remote agents |
| stdio     | `python -m mcp.server` (inside the container)        | Claude Desktop, CLI             |

## SSH tool inventory (all available as MCP tools + REST endpoints)

| MCP Tool              | REST endpoint              | Description                              |
|-----------------------|----------------------------|------------------------------------------|
| `ssh_health`          | `GET  /ssh/health`         | Ping SSH connection                      |
| `ssh_run_command`     | `POST /ssh/run`            | Run arbitrary shell command              |
| `ssh_uvicorn_start`   | `POST /ssh/uvicorn/start`  | Start FastAPI process in container       |
| `ssh_uvicorn_stop`    | `POST /ssh/uvicorn/stop`   | Kill uvicorn on given port               |
| `ssh_uvicorn_status`  | `GET  /ssh/uvicorn/status` | Check if uvicorn is running              |
| `ssh_read_logs`       | `POST /ssh/logs`           | Tail log file from container             |
| `ssh_upload_file`     | `POST /ssh/files/upload`   | Upload file via SFTP (base64 body)       |
| `ssh_download_file`   | `POST /ssh/files/download` | Download file via SFTP (base64 response) |
| `ssh_list_directory`  | `POST /ssh/ls`             | `ls -lah` on container path             |
| `ssh_system_info`     | `GET  /ssh/system`         | uptime + memory + disk + top procs       |
