from __future__ import annotations

import asyncio
import base64
import json
import logging
import uuid
from typing import Any
from urllib.parse import parse_qs, urlencode

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolResult,
    TextContent,
    Tool,
)
from starlette.applications import Starlette
from starlette.routing import Mount

from app.logging_service import event_logger
from services import (
    keyboard_service,
    mouse_service,
    screen_service,
    ssh_service,
    vision_service,
)

logger = logging.getLogger(__name__)

_MCP_SESSIONS: list[dict[str, str]] = []
_MCP_SESSION_BY_FINGERPRINT: dict[str, str] = {}

mcp_server = Server("ai-instance-manager")

def _safe_value_summary(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return {"type": "str", "length": len(value)}
    if isinstance(value, bytes):
        return {"type": "bytes", "length": len(value)}
    if isinstance(value, (list, tuple, set)):
        return {"type": type(value).__name__, "length": len(value)}
    if isinstance(value, dict):
        keys = [str(k) for k in value.keys()]
        return {"type": "dict", "keys": keys[:50], "key_count": len(keys)}
    return {"type": type(value).__name__}


def _safe_args_summary(arguments: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {"keys": sorted(arguments.keys())}
    for key, value in arguments.items():
        if key in {"content_base64", "data", "image", "password", "token", "secret", "private_key"}:
            summary[key] = "redacted"
        else:
            summary[key] = _safe_value_summary(value)
    return summary


@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    logger.debug("mcp.list_tools called")
    return [
        Tool(
            name="mouse_get_position",
            description="Get the current mouse cursor X/Y coordinates on the VNC desktop.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="mouse_move",
            description="Move the mouse cursor to the given X/Y coordinates.",
            inputSchema={
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "minimum": 0, "description": "Target X coordinate"},
                    "y": {"type": "integer", "minimum": 0, "description": "Target Y coordinate"},
                },
                "required": ["x", "y"],
            },
        ),
        Tool(
            name="mouse_click",
            description="Click the mouse at the current cursor position.",
            inputSchema={
                "type": "object",
                "properties": {
                    "button": {
                        "type": "string",
                        "enum": ["left", "right", "middle", "doubleLeft"],
                        "default": "left",
                        "description": "Mouse button to click",
                    }
                },
                "required": [],
            },
        ),
        Tool(
            name="keyboard_type",
            description="Type a string of text character by character on the VNC desktop.",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "minLength": 1, "description": "Text to type"},
                    "interval_seconds": {
                        "type": "number",
                        "minimum": 0,
                        "default": 0.05,
                        "description": "Delay between keystrokes in seconds",
                    },
                },
                "required": ["text"],
            },
        ),
        Tool(
            name="keyboard_press",
            description=(
                "Press a single named key (e.g. 'enter', 'tab', 'escape', 'ctrl', 'f5', "
                "'backspace', 'delete', 'up', 'down', 'left', 'right', 'space')."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {"type": "string", "minLength": 1, "description": "Key name to press"},
                },
                "required": ["key"],
            },
        ),
        Tool(
            name="screen_get_size",
            description="Return the width and height of the VNC desktop in pixels.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="screen_take_screenshot",
            description=(
                "Take a screenshot of the VNC desktop. "
                "Returns the filename saved to output/screenshots/ and base64 PNG data."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="vision_detect",
            description=(
                "Run UI element detection (YOLOv8 and/or OpenCV heuristics) on a screenshot. "
                "Returns bounding boxes with coordinates, labels, and center points."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "image_name": {"type": "string", "description": "Filename of the screenshot"},
                    "use_yolo": {"type": "boolean", "default": True},
                    "use_cv2_heuristic": {"type": "boolean", "default": True},
                    "use_florence": {"type": "boolean", "default": False},
                    "confidence_threshold": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.25},
                    "annotate": {"type": "boolean", "default": True},
                    "use_gpu": {"type": "boolean", "default": False},
                },
                "required": ["image_name"],
            },
        ),
        Tool(
            name="ssh_health",
            description="Check whether the SSH connection to the VNC container is alive.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="ssh_run_command",
            description="Execute an arbitrary shell command on the VNC container via SSH.",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "minLength": 1},
                    "timeout": {"type": "integer", "minimum": 1, "maximum": 600, "default": 60},
                },
                "required": ["command"],
            },
        ),
        Tool(
            name="ssh_uvicorn_start",
            description="Start the FastAPI/uvicorn process inside the VNC container.",
            inputSchema={
                "type": "object",
                "properties": {
                    "app_module": {"type": "string", "default": "main:app"},
                    "host": {"type": "string", "default": "0.0.0.0"},
                    "port": {"type": "integer", "default": 42014},
                    "conda_env": {"type": "string", "default": "ai_instance_manager"},
                    "project_dir": {"type": "string", "default": "/config/workspace/projects/apps/ai_instance_manager"},
                    "log_file": {"type": "string", "default": "/tmp/uvicorn.log"},
                },
                "required": [],
            },
        ),
        Tool(
            name="ssh_uvicorn_stop",
            description="Stop the uvicorn process on the given port.",
            inputSchema={
                "type": "object",
                "properties": {"port": {"type": "integer", "default": 42014}},
                "required": [],
            },
        ),
        Tool(
            name="ssh_uvicorn_status",
            description="Check whether uvicorn is running on the given port.",
            inputSchema={
                "type": "object",
                "properties": {"port": {"type": "integer", "default": 42014}},
                "required": [],
            },
        ),
        Tool(
            name="ssh_read_logs",
            description="Tail a log file from the VNC container.",
            inputSchema={
                "type": "object",
                "properties": {
                    "log_file": {"type": "string", "default": "/tmp/uvicorn.log"},
                    "tail_lines": {"type": "integer", "minimum": 1, "maximum": 5000, "default": 100},
                },
                "required": [],
            },
        ),
        Tool(
            name="ssh_upload_file",
            description="Upload a file to the VNC container via SFTP (base64-encoded content).",
            inputSchema={
                "type": "object",
                "properties": {
                    "remote_path": {"type": "string"},
                    "content_base64": {"type": "string"},
                },
                "required": ["remote_path", "content_base64"],
            },
        ),
        Tool(
            name="ssh_download_file",
            description="Download a file from the VNC container via SFTP (returns base64).",
            inputSchema={
                "type": "object",
                "properties": {"remote_path": {"type": "string"}},
                "required": ["remote_path"],
            },
        ),
        Tool(
            name="ssh_list_directory",
            description="List directory contents on the VNC container (ls -lah).",
            inputSchema={
                "type": "object",
                "properties": {"path": {"type": "string", "default": "/config/workspace"}},
                "required": [],
            },
        ),
        Tool(
            name="ssh_system_info",
            description="Return uptime, memory, disk usage, and top processes from the container.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
    ]


# ── Tool dispatcher ────────────────────────────────────────────────────────

def _ok(data: Any) -> CallToolResult:
    text = json.dumps(data, indent=2) if not isinstance(data, str) else data
    return CallToolResult(content=[TextContent(type="text", text=text)])


def _err(message: str) -> CallToolResult:
    return CallToolResult(
        isError=True,
        content=[TextContent(type="text", text=f"ERROR: {message}")],
    )


@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
    event_logger.log("mcp.tool_call", "received", {"tool": name, "args": arguments})
    logger.debug("mcp.call_tool received name=%s args=%s", name, _safe_args_summary(arguments))
    try:
        if name == "mouse_get_position":
            logger.debug("mcp.call_tool executing mouse_get_position")
            x, y = mouse_service.get_position()
            logger.debug("mcp.call_tool executed mouse_get_position x=%s y=%s", x, y)
            return _ok({"x": x, "y": y})
        if name == "mouse_move":
            logger.debug("mcp.call_tool executing mouse_move x=%s y=%s", arguments.get("x"), arguments.get("y"))
            mouse_service.move_to(int(arguments["x"]), int(arguments["y"]))
            logger.debug("mcp.call_tool executed mouse_move")
            return _ok({"status": "ok", "x": arguments["x"], "y": arguments["y"]})
        if name == "mouse_click":
            button = arguments.get("button", "left")
            logger.debug("mcp.call_tool executing mouse_click button=%s", button)
            mouse_service.click(button=button)
            logger.debug("mcp.call_tool executed mouse_click")
            return _ok({"status": "ok", "button": button})
        if name == "keyboard_type":
            interval_seconds = float(arguments.get("interval_seconds", 0.05))
            text_len = len(arguments.get("text") or "")
            logger.debug("mcp.call_tool executing keyboard_type length=%s interval_seconds=%s", text_len, interval_seconds)
            keyboard_service.type_text(arguments["text"], interval_seconds=interval_seconds)
            logger.debug("mcp.call_tool executed keyboard_type")
            return _ok({"status": "ok", "length": len(arguments["text"])})
        if name == "keyboard_press":
            logger.debug("mcp.call_tool executing keyboard_press key=%s", arguments.get("key"))
            keyboard_service.press_key(arguments["key"])
            logger.debug("mcp.call_tool executed keyboard_press")
            return _ok({"status": "ok", "key": arguments["key"]})
        if name == "screen_get_size":
            logger.debug("mcp.call_tool executing screen_get_size")
            size = screen_service.get_screen_size()
            logger.debug("mcp.call_tool executed screen_get_size width=%s height=%s", size.width, size.height)
            return _ok({"width": size.width, "height": size.height})
        if name == "screen_take_screenshot":
            logger.debug("mcp.call_tool executing screen_take_screenshot")
            data = screen_service.take_screenshot_base64()
            logger.debug("mcp.call_tool executed screen_take_screenshot base64_length=%s", len(data) if isinstance(data, str) else None)
            return _ok({"encoding": "base64_png", "data": data})
        if name == "vision_detect":
            logger.debug(
                "mcp.call_tool executing vision_detect image_name=%s use_yolo=%s use_cv2_heuristic=%s use_florence=%s confidence_threshold=%s annotate=%s use_gpu=%s",
                arguments.get("image_name"),
                arguments.get("use_yolo", True),
                arguments.get("use_cv2_heuristic", True),
                arguments.get("use_florence", False),
                arguments.get("confidence_threshold", 0.25),
                arguments.get("annotate", True),
                arguments.get("use_gpu", False),
            )
            result = vision_service.detect_ui_elements(
                image_name=arguments["image_name"],
                use_yolo=arguments.get("use_yolo", True),
                use_cv2_heuristic=arguments.get("use_cv2_heuristic", True),
                use_florence=arguments.get("use_florence", False),
                confidence_threshold=float(arguments.get("confidence_threshold", 0.25)),
                annotate=arguments.get("annotate", True),
                use_gpu=arguments.get("use_gpu", False),
            )
            logger.debug("mcp.call_tool executed vision_detect result_type=%s", type(result).__name__)
            return _ok(result)
        if name == "ssh_health":
            logger.debug("mcp.call_tool executing ssh_health")
            return _ok(ssh_service.check_ssh_connection())
        if name == "ssh_run_command":
            timeout = int(arguments.get("timeout", 60))
            command = arguments.get("command") or ""
            logger.debug("mcp.call_tool executing ssh_run_command timeout=%s command_length=%s", timeout, len(command))
            result = ssh_service.run_command(command, timeout=timeout)
            logger.debug("mcp.call_tool executed ssh_run_command")
            return _ok(result.to_dict())
        if name == "ssh_uvicorn_start":
            logger.debug(
                "mcp.call_tool executing ssh_uvicorn_start app_module=%s host=%s port=%s conda_env=%s project_dir=%s log_file=%s",
                arguments.get("app_module", "main:app"),
                arguments.get("host", "0.0.0.0"),
                arguments.get("port", 42014),
                arguments.get("conda_env", "ai_instance_manager"),
                arguments.get("project_dir", "/config/workspace/projects/apps/ai_instance_manager"),
                arguments.get("log_file", "/tmp/uvicorn.log"),
            )
            result = ssh_service.start_uvicorn(
                app_module=arguments.get("app_module", "main:app"),
                host=arguments.get("host", "0.0.0.0"),
                port=int(arguments.get("port", 42014)),
                conda_env=arguments.get("conda_env", "ai_instance_manager"),
                project_dir=arguments.get("project_dir", "/config/workspace/projects/apps/ai_instance_manager"),
                log_file=arguments.get("log_file", "/tmp/uvicorn.log"),
            )
            logger.debug("mcp.call_tool executed ssh_uvicorn_start")
            return _ok(result.to_dict())
        if name == "ssh_uvicorn_stop":
            logger.debug("mcp.call_tool executing ssh_uvicorn_stop port=%s", arguments.get("port", 42014))
            result = ssh_service.stop_uvicorn(port=int(arguments.get("port", 42014)))
            logger.debug("mcp.call_tool executed ssh_uvicorn_stop")
            return _ok(result.to_dict())
        if name == "ssh_uvicorn_status":
            logger.debug("mcp.call_tool executing ssh_uvicorn_status port=%s", arguments.get("port", 42014))
            result = ssh_service.uvicorn_status(port=int(arguments.get("port", 42014)))
            logger.debug("mcp.call_tool executed ssh_uvicorn_status")
            return _ok(result.to_dict())
        if name == "ssh_read_logs":
            log_file = arguments.get("log_file", "/tmp/uvicorn.log")
            tail_lines = int(arguments.get("tail_lines", 100))
            logger.debug("mcp.call_tool executing ssh_read_logs log_file=%s tail_lines=%s", log_file, tail_lines)
            result = ssh_service.read_logs(log_file=log_file, tail_lines=tail_lines)
            logger.debug("mcp.call_tool executed ssh_read_logs")
            return _ok(result.to_dict())
        if name == "ssh_upload_file":
            logger.debug("mcp.call_tool executing ssh_upload_file remote_path=%s content_base64_length=%s", arguments.get("remote_path"), len(arguments.get("content_base64") or ""))
            raw = base64.b64decode(arguments["content_base64"])
            result = ssh_service.upload_file(raw, arguments["remote_path"])
            logger.debug("mcp.call_tool executed ssh_upload_file bytes=%s", len(raw))
            return _ok(result)
        if name == "ssh_download_file":
            logger.debug("mcp.call_tool executing ssh_download_file remote_path=%s", arguments.get("remote_path"))
            result = ssh_service.download_file(arguments["remote_path"])
            logger.debug("mcp.call_tool executed ssh_download_file")
            return _ok(result)
        if name == "ssh_list_directory":
            path = arguments.get("path", "/config/workspace")
            logger.debug("mcp.call_tool executing ssh_list_directory path=%s", path)
            result = ssh_service.list_directory(path)
            logger.debug("mcp.call_tool executed ssh_list_directory")
            return _ok(result.to_dict())
        if name == "ssh_system_info":
            logger.debug("mcp.call_tool executing ssh_system_info")
            result = ssh_service.get_system_info()
            logger.debug("mcp.call_tool executed ssh_system_info")
            return _ok(result.to_dict())
        logger.debug("mcp.call_tool unknown tool name=%s", name)
        return _err(f"Unknown tool: {name}")
    except FileNotFoundError as exc:
        event_logger.log("mcp.tool_call", "error", {"tool": name, "error": str(exc)})
        logger.debug("mcp.call_tool FileNotFoundError name=%s error=%s", name, str(exc))
        return _err(str(exc))
    except RuntimeError as exc:
        event_logger.log("mcp.tool_call", "error", {"tool": name, "error": str(exc)})
        logger.debug("mcp.call_tool RuntimeError name=%s error=%s", name, str(exc))
        return _err(str(exc))
    except Exception as exc:
        event_logger.log("mcp.tool_call", "error", {"tool": name, "error": repr(exc)})
        logger.debug("mcp.call_tool Exception name=%s error=%s", name, repr(exc))
        return _err(f"Unexpected error: {exc}")


# ── SSE transport ──────────────────────────────────────────────────────────
#
# ROOT CAUSE OF THE BUG:
#   Starlette Route wraps the endpoint as a request handler — it calls
#   endpoint(Request) with ONE argument. But SseServerTransport needs raw
#   ASGI callables: (scope, receive, send).
#
# FIX:
#   Use Starlette's Mount with a hand-written ASGI callable instead of Route.
#   The ASGI callable receives (scope, receive, send) directly — no wrapping.

def create_sse_app() -> Starlette:
    """
    Returns a Starlette sub-application serving the MCP SSE transport.
    Mount at /mcp in the FastAPI app:

        app.mount("/mcp", create_sse_app())

    SSE stream  →  GET  http://localhost:42014/mcp/sse
    Message POST →  POST http://localhost:42014/mcp/messages/
    """
    sse_transport = SseServerTransport("/messages/")

    # ── Raw ASGI callables — NOT Starlette endpoint functions ──────────────

    def _session_id_hex(value: str) -> str:
        value = value.strip()
        if len(value) == 36 and value.count("-") == 4:
            return value.replace("-", "")
        return value

    def _session_id_uuid(value: str) -> str:
        value = value.strip()
        if len(value) == 32:
            return f"{value[0:8]}-{value[8:12]}-{value[12:16]}-{value[16:20]}-{value[20:32]}"
        return value

    def _client_fingerprint(scope: dict[str, Any]) -> str:
        client = scope.get("client") or ("unknown", 0)
        raw_headers = scope.get("headers") or []
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in raw_headers}
        user_agent = headers.get("user-agent", "unknown")
        return f"{client[0]}|{user_agent}"

    def _record_connected_session(*, fingerprint: str, session_id: str) -> None:
        session_hex = _session_id_hex(session_id)
        _MCP_SESSION_BY_FINGERPRINT[fingerprint] = session_hex
        _MCP_SESSIONS.append({"session_id": session_hex, "fingerprint": fingerprint, "state": "connected"})

    def _clear_session(*, fingerprint: str, session_id: str) -> None:
        normalized = _session_id_hex(session_id)
        current = _MCP_SESSION_BY_FINGERPRINT.get(fingerprint)
        if current == normalized:
            del _MCP_SESSION_BY_FINGERPRINT[fingerprint]
        _MCP_SESSIONS[:] = [
            item
            for item in _MCP_SESSIONS
            if item.get("session_id") != normalized and item.get("fingerprint") != fingerprint
        ]

    async def _read_request_body(receive) -> bytes:
        body = b""
        more_body = True
        while more_body:
            message = await receive()
            if message["type"] != "http.request":
                continue
            body += message.get("body", b"")
            more_body = bool(message.get("more_body", False))
        logger.debug("mcp.http.read_body bytes=%s", len(body))
        return body

    def _to_jsonable(value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        if isinstance(value, list):
            return [_to_jsonable(v) for v in value]
        if isinstance(value, tuple):
            return [_to_jsonable(v) for v in value]
        if isinstance(value, dict):
            return {str(k): _to_jsonable(v) for k, v in value.items()}
        model_dump = getattr(value, "model_dump", None)
        if callable(model_dump):
            return model_dump(by_alias=True, exclude_none=True)
        to_dict = getattr(value, "to_dict", None)
        if callable(to_dict):
            return to_dict()
        as_dict = getattr(value, "dict", None)
        if callable(as_dict):
            return as_dict()
        return str(value)

    async def _send_bytes(send, *, status: int, headers: list[tuple[bytes, bytes]], body: bytes) -> None:
        await send({"type": "http.response.start", "status": status, "headers": headers})
        await send({"type": "http.response.body", "body": body})

    async def _handle_stateless_rpc(scope, receive, send, *, forced_session_id: str | None = None) -> None:
        raw_headers = scope.get("headers") or []
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in raw_headers}
        fingerprint = _client_fingerprint(scope)
        logger.debug(
            "mcp.http.stateless.enter method=%s path=%s fingerprint=%s forced_session_id=%s content_type=%s",
            scope.get("method"),
            scope.get("path"),
            fingerprint,
            "present" if forced_session_id else "missing",
            headers.get("content-type"),
        )

        body_bytes = await _read_request_body(receive)
        if not body_bytes:
            logger.debug("mcp.http.stateless.empty_body")
            await _send_bytes(
                send,
                status=400,
                headers=[(b"content-type", b"text/plain; charset=utf-8"), (b"content-length", b"0")],
                body=b"",
            )
            return

        try:
            payload = json.loads(body_bytes.decode("utf-8"))
        except Exception as exc:
            logger.debug("mcp.http.stateless.json_parse_error error=%s", str(exc))
            response = {"jsonrpc": "2.0", "id": 0, "error": {"code": -32700, "message": "Parse error", "data": str(exc)}}
            body = json.dumps(response).encode("utf-8")
            await _send_bytes(
                send,
                status=400,
                headers=[(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode("ascii"))],
                body=body,
            )
            return

        request = payload[0] if isinstance(payload, list) and payload else payload
        request_id = request.get("id")
        method = request.get("method")
        params = request.get("params") or {}
        logger.debug(
            "mcp.http.stateless.request id=%s method=%s params=%s",
            request_id,
            method,
            _safe_value_summary(params) if isinstance(params, dict) else {"type": type(params).__name__},
        )

        if request.get("jsonrpc") != "2.0" or not isinstance(method, str):
            logger.debug("mcp.http.stateless.invalid_request jsonrpc=%s method_type=%s", request.get("jsonrpc"), type(method).__name__)
            response = {"jsonrpc": "2.0", "id": request_id or 0, "error": {"code": -32600, "message": "Invalid Request"}}
            body = json.dumps(response).encode("utf-8")
            await _send_bytes(
                send,
                status=400,
                headers=[(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode("ascii"))],
                body=body,
            )
            return

        if request_id is None:
            logger.debug("mcp.http.stateless.notification method=%s", method)
            await _send_bytes(
                send,
                status=204,
                headers=[(b"content-length", b"0")],
                body=b"",
            )
            return

        session_id = forced_session_id or _MCP_SESSION_BY_FINGERPRINT.get(fingerprint)
        if not session_id:
            session_id = uuid.uuid4().hex
        session_id = _session_id_hex(session_id)
        _MCP_SESSION_BY_FINGERPRINT[fingerprint] = session_id
        logger.debug("mcp.http.stateless.session session_id=%s fingerprint=%s", session_id, fingerprint)
        if not any(item.get("session_id") == session_id for item in _MCP_SESSIONS):
            _MCP_SESSIONS.append({"session_id": session_id, "fingerprint": fingerprint, "state": "http_stateless"})
            if len(_MCP_SESSIONS) > 200:
                _MCP_SESSIONS[:] = _MCP_SESSIONS[-200:]

        if method == "initialize":
            client_protocol = None
            if isinstance(params, dict):
                client_protocol = params.get("protocolVersion")
            protocol_version = client_protocol or "2025-03-26"
            logger.debug("mcp.http.stateless.initialize protocol_version=%s", protocol_version)
            result = {
                "protocolVersion": protocol_version,
                "capabilities": {"tools": {"listChanged": True}},
                "serverInfo": {"name": "ai-instance-manager", "version": "0.1.0"},
            }
            response = {"jsonrpc": "2.0", "id": request_id, "result": result}
        elif method == "notifications/initialized":
            logger.debug("mcp.http.stateless.initialized_notification")
            response = {"jsonrpc": "2.0", "id": request_id, "result": {}}
        elif method == "tools/list":
            logger.debug("mcp.http.stateless.tools_list")
            tools = await list_tools()
            response = {"jsonrpc": "2.0", "id": request_id, "result": {"tools": _to_jsonable(tools)}}
        elif method == "tools/call":
            if not isinstance(params, dict):
                logger.debug("mcp.http.stateless.tools_call.invalid_params params_type=%s", type(params).__name__)
                response = {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32602, "message": "Invalid params"}}
            else:
                tool_name = params.get("name")
                tool_args = params.get("arguments") or {}
                logger.debug("mcp.http.stateless.tools_call name=%s args=%s", tool_name, _safe_value_summary(tool_args))
                try:
                    result = await call_tool(str(tool_name), dict(tool_args))
                    logger.debug("mcp.http.stateless.tools_call.ok name=%s", tool_name)
                    response = {"jsonrpc": "2.0", "id": request_id, "result": _to_jsonable(result)}
                except Exception as exc:
                    logger.debug("mcp.http.stateless.tools_call.error name=%s error=%s", tool_name, str(exc))
                    response = {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32000, "message": "Server error", "data": str(exc)}}
        else:
            logger.debug("mcp.http.stateless.method_not_found method=%s", method)
            response = {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}

        response_body = json.dumps(response).encode("utf-8")
        logger.debug("mcp.http.stateless.respond id=%s method=%s bytes=%s", request_id, method, len(response_body))
        await _send_bytes(
            send,
            status=200,
            headers=[
                (b"content-type", b"application/json"),
                (b"content-length", str(len(response_body)).encode("ascii")),
                (b"mcp-session-id", session_id.encode("ascii")),
            ],
            body=response_body,
        )

    async def handle_sse(scope, receive, send):
        """
        Raw ASGI app for GET /mcp/sse.
        Starlette Route would wrap this and pass a Request object — wrong.
        We use Mount so Starlette passes (scope, receive, send) directly.
        """
        assert scope["type"] == "http"
        fingerprint = _client_fingerprint(scope)
        logger.debug("mcp.sse.connect.enter method=%s path=%s fingerprint=%s", scope.get("method"), scope.get("path"), fingerprint)
        session_id: str | None = None
        try:
            async with sse_transport.connect_sse(scope, receive, send) as (read, write):
                session_id = (
                    getattr(write, "session_id", None)
                    or getattr(read, "session_id", None)
                    or getattr(sse_transport, "session_id", None)
                    or getattr(sse_transport, "_session_id", None)
                    or (scope.get("state") or {}).get("session_id")
                )
                if session_id:
                    _record_connected_session(fingerprint=fingerprint, session_id=str(session_id))
                    logger.debug("mcp.sse.connect session_id=present fingerprint=%s", fingerprint)
                else:
                    _MCP_SESSIONS.append({"session_id": "", "fingerprint": fingerprint, "state": "connected_no_id"})
                    logger.debug("mcp.sse.connect session_id=missing fingerprint=%s", fingerprint)
                await mcp_server.run(read, write, mcp_server.create_initialization_options())
        finally:
            if session_id:
                _clear_session(fingerprint=fingerprint, session_id=str(session_id))
                logger.debug("mcp.sse.disconnect session_id=cleared fingerprint=%s", fingerprint)

    async def handle_messages(scope, receive, send):
        """Raw ASGI app for POST /mcp/messages/"""
        assert scope["type"] == "http"

        raw_headers = scope.get("headers") or []
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in raw_headers}
        logger.debug(
            "mcp.messages.enter method=%s path=%s content_type=%s accept=%s",
            scope.get("method"),
            scope.get("path"),
            headers.get("content-type"),
            headers.get("accept"),
        )
        query_string: bytes = scope.get("query_string", b"")
        query = parse_qs(query_string.decode("latin-1"), keep_blank_values=True)
        session_id = (query.get("session_id") or [None])[0] or (query.get("sessionId") or [None])[0]

        if not session_id:
            for candidate in ("mcp-session-id", "x-mcp-session-id", "x-mcp-sessionid", "session-id"):
                if headers.get(candidate):
                    session_id = headers[candidate]
                    break

        if not session_id:
            fingerprint = _client_fingerprint(scope)
            session_id = _MCP_SESSION_BY_FINGERPRINT.get(fingerprint)
            if not session_id and len(_MCP_SESSION_BY_FINGERPRINT) == 1:
                session_id = next(iter(_MCP_SESSION_BY_FINGERPRINT.values()))

        if session_id:
            session_id = _session_id_hex(str(session_id))

        if session_id and "session_id" not in query:
            query["session_id"] = [session_id]
            scope["query_string"] = urlencode(query, doseq=True).encode("latin-1")

        logger.debug(
            "mcp.sse.post method=%s path=%s session_id=%s content_type=%s",
            scope.get("method"),
            scope.get("path"),
            "present" if session_id else "missing",
            headers.get("content-type"),
        )

        if not session_id:
            logger.debug("mcp.messages.stateless_fallback reason=missing_session_id")
            await _handle_stateless_rpc(scope, receive, send)
            return

        sessions = getattr(sse_transport, "_sessions", None) or getattr(sse_transport, "sessions", None)
        uuid_id = _session_id_uuid(session_id)
        active_session = False
        if isinstance(sessions, dict):
            if session_id in sessions or uuid_id in sessions:
                active_session = True
            else:
                try:
                    active_session = uuid.UUID(uuid_id) in sessions
                except Exception:
                    active_session = False

        if not active_session:
            fingerprint = _client_fingerprint(scope)
            _MCP_SESSION_BY_FINGERPRINT[fingerprint] = session_id
            _MCP_SESSIONS.append({"session_id": session_id, "fingerprint": fingerprint, "state": "http_stateless_bound"})
            logger.debug("mcp.messages.stateless_fallback reason=unknown_session_id session_id=%s", session_id)
            await _handle_stateless_rpc(scope, receive, send, forced_session_id=session_id)
            return

        logger.debug("mcp.messages.sse_transport session_id=%s", session_id)
        await sse_transport.handle_post_message(scope, receive, send)

    # ── Simple path-based ASGI router ─────────────────────────────────────

    async def router(scope, receive, send):
        if scope["type"] == "lifespan":
            logger.debug("mcp.router.lifespan.enter")
            while True:
                event = await receive()
                if event["type"] == "lifespan.startup":
                    logger.debug("mcp.router.lifespan.startup")
                    await send({"type": "lifespan.startup.complete"})
                    break
                if event["type"] == "lifespan.shutdown":
                    logger.debug("mcp.router.lifespan.shutdown")
                    await send({"type": "lifespan.shutdown.complete"})
                    return
            while True:
                event = await receive()
                if event["type"] == "lifespan.shutdown":
                    logger.debug("mcp.router.lifespan.shutdown")
                    await send({"type": "lifespan.shutdown.complete"})
                    return

        assert scope["type"] == "http"
        root_path: str = scope.get("root_path", "") or ""
        raw_path: str = scope.get("path", "") or ""
        path: str = raw_path
        if root_path and path.startswith(root_path):
            path = path[len(root_path):] or "/"
        if path.startswith("/mcp/"):
            path = path[len("/mcp"):] or "/"
        elif path == "/mcp":
            path = "/"
        method: str = scope.get("method", "GET")
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in (scope.get("headers") or [])}
        accept = headers.get("accept", "")
        wants_sse = "text/event-stream" in accept
        logger.debug(
            "mcp.router.http method=%s raw_path=%s root_path=%s normalized_path=%s accept=%s",
            method,
            raw_path,
            root_path,
            path,
            accept,
        )

        if method == "GET" and (path == "/sse" or (wants_sse and path in ("/messages", "/messages/"))):
            logger.debug("mcp.router.dispatch target=handle_sse")
            await handle_sse(scope, receive, send)
        elif method == "POST" and path in ("/", "/messages", "/messages/"):
            logger.debug("mcp.router.dispatch target=handle_messages")
            await handle_messages(scope, receive, send)
        else:
            status = 404
            if path in ("/sse", "/messages", "/messages/"):
                status = 405
            body = b"MCP SSE: use GET /mcp/sse (SSE) or POST /mcp/messages/ (messages)\n"
            logger.debug("mcp.router.unhandled status=%s path=%s method=%s", status, path, method)
            await send({
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"text/plain; charset=utf-8"),
                    (b"content-length", str(len(body)).encode()),
                ],
            })
            await send({"type": "http.response.body", "body": body})

    # Wrap in Starlette only so FastAPI's app.mount() is happy
    return Starlette(routes=[Mount("/", app=router)])


# ── stdio transport ────────────────────────────────────────────────────────

async def _run_stdio() -> None:
    async with stdio_server() as (read, write):
        await mcp_server.run(read, write, mcp_server.create_initialization_options())


def run_stdio() -> None:
    asyncio.run(_run_stdio())


if __name__ == "__main__":
    run_stdio()
