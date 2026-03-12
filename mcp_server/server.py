from __future__ import annotations

import asyncio
import base64
import json
from typing import Any

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolResult,
    TextContent,
    Tool,
)
from starlette.applications import Starlette
from starlette.routing import Mount, Route

from app.logging_service import event_logger
from services import (
    keyboard_service,
    mouse_service,
    screen_service,
    ssh_service,
    vision_service,
)


mcp_server = Server("ai-instance-manager")


@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
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
                "Returns bounding boxes with coordinates, labels, and center points. "
                "Optionally saves an annotated image."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "image_name": {
                        "type": "string",
                        "description": (
                            "Filename or path of the screenshot to analyse. "
                            "Example: 'screenshot_2026-03-10_14-44-52.png'"
                        ),
                    },
                    "use_yolo": {"type": "boolean", "default": True},
                    "use_cv2_heuristic": {"type": "boolean", "default": True},
                    "use_florence": {
                        "type": "boolean",
                        "default": False,
                        "description": "Enable Florence-2 captioning (slow on CPU)",
                    },
                    "confidence_threshold": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "default": 0.25,
                    },
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
            description=(
                "Execute an arbitrary shell command on the VNC container via SSH. "
                "Returns stdout, stderr, exit_code. All exceptions are logged."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "minLength": 1,
                        "description": "Shell command to run",
                    },
                    "timeout": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 600,
                        "default": 60,
                        "description": "Timeout in seconds",
                    },
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
                    "project_dir": {
                        "type": "string",
                        "default": "/config/workspace/projects/apps/ai_instance_manager",
                    },
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
                "properties": {
                    "port": {"type": "integer", "default": 42014},
                },
                "required": [],
            },
        ),
        Tool(
            name="ssh_uvicorn_status",
            description="Check whether uvicorn is running on the given port.",
            inputSchema={
                "type": "object",
                "properties": {
                    "port": {"type": "integer", "default": 42014},
                },
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
                    "tail_lines": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 5000,
                        "default": 100,
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="ssh_upload_file",
            description=(
                "Upload a file to the VNC container via SFTP. "
                "Provide content as base64-encoded string."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "remote_path": {
                        "type": "string",
                        "description": "Absolute path on the container",
                    },
                    "content_base64": {
                        "type": "string",
                        "description": "Base64-encoded file content",
                    },
                },
                "required": ["remote_path", "content_base64"],
            },
        ),
        Tool(
            name="ssh_download_file",
            description=(
                "Download a file from the VNC container via SFTP. "
                "Returns base64-encoded content."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "remote_path": {
                        "type": "string",
                        "description": "Absolute path on the container",
                    },
                },
                "required": ["remote_path"],
            },
        ),
        Tool(
            name="ssh_list_directory",
            description="List directory contents on the VNC container (ls -lah).",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "default": "/config/workspace"},
                },
                "required": [],
            },
        ),
        Tool(
            name="ssh_system_info",
            description=(
                "Return a system snapshot from the VNC container: "
                "uptime, memory, disk usage, and top processes."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
    ]


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

    try:
        if name == "mouse_get_position":
            x, y = mouse_service.get_position()
            return _ok({"x": x, "y": y})

        if name == "mouse_move":
            mouse_service.move_to(int(arguments["x"]), int(arguments["y"]))
            return _ok({"status": "ok", "x": arguments["x"], "y": arguments["y"]})

        if name == "mouse_click":
            button = arguments.get("button", "left")
            mouse_service.click(button=button)
            return _ok({"status": "ok", "button": button})

        if name == "keyboard_type":
            keyboard_service.type_text(
                arguments["text"],
                interval_seconds=float(arguments.get("interval_seconds", 0.05)),
            )
            return _ok({"status": "ok", "length": len(arguments["text"])})

        if name == "keyboard_press":
            keyboard_service.press_key(arguments["key"])
            return _ok({"status": "ok", "key": arguments["key"]})

        if name == "screen_get_size":
            size = screen_service.get_screen_size()
            return _ok({"width": size.width, "height": size.height})

        if name == "screen_take_screenshot":
            data = screen_service.take_screenshot_base64()
            return _ok({"encoding": "base64_png", "data": data})

        if name == "vision_detect":
            result = vision_service.detect_ui_elements(
                image_name=arguments["image_name"],
                use_yolo=arguments.get("use_yolo", True),
                use_cv2_heuristic=arguments.get("use_cv2_heuristic", True),
                use_florence=arguments.get("use_florence", False),
                confidence_threshold=float(arguments.get("confidence_threshold", 0.25)),
                annotate=arguments.get("annotate", True),
                use_gpu=arguments.get("use_gpu", False),
            )
            return _ok(result)

        if name == "ssh_health":
            return _ok(ssh_service.check_ssh_connection())

        if name == "ssh_run_command":
            result = ssh_service.run_command(
                arguments["command"],
                timeout=int(arguments.get("timeout", 60)),
            )
            return _ok(result.to_dict())

        if name == "ssh_uvicorn_start":
            result = ssh_service.start_uvicorn(
                app_module=arguments.get("app_module", "main:app"),
                host=arguments.get("host", "0.0.0.0"),
                port=int(arguments.get("port", 42014)),
                conda_env=arguments.get("conda_env", "ai_instance_manager"),
                project_dir=arguments.get(
                    "project_dir",
                    "/config/workspace/projects/apps/ai_instance_manager",
                ),
                log_file=arguments.get("log_file", "/tmp/uvicorn.log"),
            )
            return _ok(result.to_dict())

        if name == "ssh_uvicorn_stop":
            result = ssh_service.stop_uvicorn(port=int(arguments.get("port", 42014)))
            return _ok(result.to_dict())

        if name == "ssh_uvicorn_status":
            result = ssh_service.uvicorn_status(port=int(arguments.get("port", 42014)))
            return _ok(result.to_dict())

        if name == "ssh_read_logs":
            result = ssh_service.read_logs(
                log_file=arguments.get("log_file", "/tmp/uvicorn.log"),
                tail_lines=int(arguments.get("tail_lines", 100)),
            )
            return _ok(result.to_dict())

        if name == "ssh_upload_file":
            raw = base64.b64decode(arguments["content_base64"])
            result = ssh_service.upload_file(raw, arguments["remote_path"])
            return _ok(result)

        if name == "ssh_download_file":
            result = ssh_service.download_file(arguments["remote_path"])
            return _ok(result)

        if name == "ssh_list_directory":
            result = ssh_service.list_directory(arguments.get("path", "/config/workspace"))
            return _ok(result.to_dict())

        if name == "ssh_system_info":
            result = ssh_service.get_system_info()
            return _ok(result.to_dict())

        return _err(f"Unknown tool: {name}")

    except FileNotFoundError as exc:
        event_logger.log("mcp.tool_call", "error", {"tool": name, "error": str(exc)})
        return _err(str(exc))
    except RuntimeError as exc:
        event_logger.log("mcp.tool_call", "error", {"tool": name, "error": str(exc)})
        return _err(str(exc))
    except Exception as exc:
        event_logger.log("mcp.tool_call", "error", {"tool": name, "error": repr(exc)})
        return _err(f"Unexpected error: {exc}")


def create_sse_app() -> Starlette:
    sse_transport = SseServerTransport("/mcp/sse")

    async def _handle_sse(scope, receive, send):
        if scope.get("method") != "GET":
            body = b"Use GET /mcp/sse for SSE. Use POST /mcp/sse for messages.\n"
            await send(
                {
                    "type": "http.response.start",
                    "status": 405,
                    "headers": [
                        (b"content-type", b"text/plain; charset=utf-8"),
                        (b"content-length", str(len(body)).encode("ascii")),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": body})
            return
        async with sse_transport.connect_sse(scope, receive, send) as (read, write):
            await mcp_server.run(read, write, mcp_server.create_initialization_options())

    async def _handle_post(scope, receive, send):
        await sse_transport.handle_post_message(scope, receive, send)

    return Starlette(
        routes=[
            Route("/sse", endpoint=_handle_sse, methods=["GET", "POST"]),
            Route("/messages", endpoint=_handle_post, methods=["POST"]),
            Route("/messages/", endpoint=_handle_post, methods=["POST"]),
        ]
    )


async def _run_stdio() -> None:
    async with stdio_server() as (read, write):
        await mcp_server.run(read, write, mcp_server.create_initialization_options())


def run_stdio() -> None:
    asyncio.run(_run_stdio())


if __name__ == "__main__":
    run_stdio()
