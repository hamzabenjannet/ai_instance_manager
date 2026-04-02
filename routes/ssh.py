"""
SSH routes — exposes every ssh_service capability as discrete REST endpoints.

Each endpoint does exactly one thing, logs independently, and raises
HTTPException on failure so callers (including the MCP server) can react.
"""
from __future__ import annotations

import base64
from typing import Any

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field

# from app.logging_service import event_logger
from services import ssh_service
import logging


logger = logging.getLogger(__name__)



router = APIRouter(prefix="/ssh", tags=["ssh"])


# ── Request / Response models ──────────────────────────────────────────────

class RunCommandRequest(BaseModel):
    command: str = Field(..., min_length=1, description="Shell command to execute")
    timeout: int = Field(default=60, ge=1, le=600, description="Timeout in seconds")


class UvicornStartRequest(BaseModel):
    app_module: str = Field(default="main:app")
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=42014, ge=1, le=65535)
    conda_env: str = Field(default="ai_instance_manager")
    project_dir: str = Field(default="/config/workspace/projects/apps/ai_instance_manager")
    log_file: str = Field(default="/tmp/uvicorn.log")


class UvicornStopRequest(BaseModel):
    port: int = Field(default=42014, ge=1, le=65535)


class ReadLogsRequest(BaseModel):
    log_file: str = Field(default="/tmp/uvicorn.log")
    tail_lines: int = Field(default=100, ge=1, le=5000)


class UploadFileRequest(BaseModel):
    remote_path: str = Field(..., min_length=1, description="Absolute path on the container")
    content_base64: str = Field(..., min_length=1, description="Base64-encoded file content")


class DownloadFileRequest(BaseModel):
    remote_path: str = Field(..., min_length=1, description="Absolute path on the container")


class ListDirectoryRequest(BaseModel):
    path: str = Field(default="/config/workspace", description="Directory path to list")


# ── Helpers ────────────────────────────────────────────────────────────────

def _raise_on_error(result: ssh_service.CommandResult) -> None:
    if not result.success:
        raise HTTPException(
            status_code=500,
            detail={
                "command": result.command,
                "exit_code": result.exit_code,
                "stderr": result.stderr,
            },
        )


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.get("/health")
def ssh_health() -> dict[str, Any]:
    """Ping the SSH connection — safe health-check probe."""
    logger.debug("ssh.health checking connection")
    result = ssh_service.check_ssh_connection()
    logger.debug("ssh.health ok %s", result)
    return result


@router.post("/run")
def run_command(request: RunCommandRequest) -> dict[str, Any]:
    """
    Execute an arbitrary shell command on the VNC container.
    Returns stdout, stderr, exit_code. Always logs result.
    """
    try:
        logger.debug("ssh.run", "debug", {"command": request.command})
        result = ssh_service.run_command(request.command, timeout=request.timeout)
        _raise_on_error(result)
        # logger.debug("ssh.run", "debug", result.to_dict())
        logger.debug("ssh.run", "debug", {"exit_code": result.exit_code, "stdout": result.stdout[:100], "stderr": result.stderr[:100]})
        return result.to_dict()
    except RuntimeError as exc:
        logger.error("ssh.run", "error", {"error": str(exc), "command": request.command})
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# @router.post("/uvicorn/start")
# def start_uvicorn(request: UvicornStartRequest) -> dict[str, Any]:
#     """Start the FastAPI/uvicorn process inside the VNC container."""
#     try:
#         result = ssh_service.start_uvicorn(
#             app_module=request.app_module,
#             host=request.host,
#             port=request.port,
#             conda_env=request.conda_env,
#             project_dir=request.project_dir,
#             log_file=request.log_file,
#         )
#     except RuntimeError as exc:
#         raise HTTPException(status_code=500, detail=str(exc)) from exc
#     return result.to_dict()


# @router.post("/uvicorn/stop")
# def stop_uvicorn(request: UvicornStopRequest) -> dict[str, Any]:
#     """Kill uvicorn process(es) on the given port."""
#     try:
#         result = ssh_service.stop_uvicorn(port=request.port)
#     except RuntimeError as exc:
#         raise HTTPException(status_code=500, detail=str(exc)) from exc
#     return result.to_dict()


# @router.get("/uvicorn/status")
# def uvicorn_status(port: int = 42014) -> dict[str, Any]:
#     """Check whether uvicorn is running on the given port."""
#     try:
#         result = ssh_service.uvicorn_status(port=port)
#     except RuntimeError as exc:
#         raise HTTPException(status_code=500, detail=str(exc)) from exc
#     return result.to_dict()


# @router.post("/logs")
# def read_logs(request: ReadLogsRequest) -> dict[str, Any]:
#     """Tail a log file from the container."""
#     try:
#         result = ssh_service.read_logs(
#             log_file=request.log_file,
#             tail_lines=request.tail_lines,
#         )
#     except RuntimeError as exc:
#         raise HTTPException(status_code=500, detail=str(exc)) from exc
#     return result.to_dict()


# @router.post("/files/upload")
# def upload_file(request: UploadFileRequest) -> dict[str, Any]:
#     """
#     Upload a file to the VNC container via SFTP.
#     Send file content as base64 in the JSON body.
#     """
#     try:
#         raw = base64.b64decode(request.content_base64)
#     except Exception as exc:
#         raise HTTPException(status_code=422, detail=f"Invalid base64: {exc}") from exc

#     try:
#         return ssh_service.upload_file(raw, request.remote_path)
#     except RuntimeError as exc:
#         raise HTTPException(status_code=500, detail=str(exc)) from exc


# @router.post("/files/upload-multipart")
# async def upload_file_multipart(
#     remote_path: str,
#     file: UploadFile = File(...),
# ) -> dict[str, Any]:
#     """
#     Upload a file to the VNC container via SFTP using multipart form upload.
#     More convenient than base64 for large files.
#     """
#     try:
#         content = await file.read()
#         return ssh_service.upload_file(content, remote_path)
#     except RuntimeError as exc:
#         raise HTTPException(status_code=500, detail=str(exc)) from exc


# @router.post("/files/download")
# def download_file(request: DownloadFileRequest) -> dict[str, Any]:
#     """
#     Download a file from the VNC container via SFTP.
#     Returns base64-encoded content.
#     """
#     try:
#         return ssh_service.download_file(request.remote_path)
#     except RuntimeError as exc:
#         raise HTTPException(status_code=500, detail=str(exc)) from exc


# @router.post("/ls")
# def list_directory(request: ListDirectoryRequest) -> dict[str, Any]:
#     """List directory contents on the VNC container."""
#     try:
#         result = ssh_service.list_directory(request.path)
#     except RuntimeError as exc:
#         raise HTTPException(status_code=500, detail=str(exc)) from exc
#     return result.to_dict()


# @router.get("/system")
# def system_info() -> dict[str, Any]:
#     """Return container system snapshot: uptime, memory, disk, top processes."""
#     try:
#         result = ssh_service.get_system_info()
#     except RuntimeError as exc:
#         raise HTTPException(status_code=500, detail=str(exc)) from exc
#     return result.to_dict()
