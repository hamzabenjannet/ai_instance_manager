"""
SSH service — wraps paramiko to talk to the VNC container's own sshd.

All operations are logged via the shared event_logger so they appear
in GET /health and the in-memory event log alongside every other API action.
"""
from __future__ import annotations

import base64
import os
import stat
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Any

import paramiko
import logging



logger = logging.getLogger(__name__)



# from app.logging_service import event_logger
from app.config import get_settings


# ---------------------------------------------------------------------------
# SSH config — read once from settings / env
# ---------------------------------------------------------------------------
def _cfg() -> "SSHConfig":
    s = get_settings()
    return SSHConfig(
        host=s.ssh_host,
        port=s.ssh_port,
        user=s.ssh_user,
        key_path=s.ssh_key_path,
        connect_timeout=s.ssh_connect_timeout,
    )


@dataclass(frozen=True)
class SSHConfig:
    host: str
    port: int
    user: str
    key_path: str
    connect_timeout: int = 10


@dataclass
class CommandResult:
    command: str
    stdout: str
    stderr: str
    exit_code: int
    success: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "success": self.success,
        }


# ---------------------------------------------------------------------------
# Internal: build a fresh paramiko client for every call.
# We don't keep a persistent connection — avoids stale-socket headaches.
# ---------------------------------------------------------------------------
def _client(cfg: SSHConfig) -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    key_path = Path(cfg.key_path).expanduser()
    if not key_path.exists():
        raise FileNotFoundError(f"SSH private key not found: {key_path}")

    pkey = paramiko.RSAKey.from_private_key_file(str(key_path))
    client.connect(
        hostname=cfg.host,
        port=cfg.port,
        username=cfg.user,
        pkey=pkey,
        timeout=cfg.connect_timeout,
        allow_agent=False,
        look_for_keys=False,
    )
    return client


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_command(command: str, timeout: int = 60) -> CommandResult:
    """Execute an arbitrary shell command on the VNC container."""
    cfg = _cfg()
    event_type = "ssh.run_command"
    try:
        with _client(cfg) as client:
            stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
            out = stdout.read().decode("utf-8", errors="replace")
            err = stderr.read().decode("utf-8", errors="replace")
            code = stdout.channel.recv_exit_status()
            result = CommandResult(
                command=command,
                stdout=out,
                stderr=err,
                exit_code=code,
                success=code == 0,
            )
            logger.debug(event_type, "success" if result.success else "error", {
                "command": command,
                "exit_code": code,
                "stderr_snippet": err[:200],
            })
            return result
    except Exception as exc:
        logger.debug(event_type, "error", {"command": command, "error": str(exc)})
        raise RuntimeError(f"SSH command failed: {exc}") from exc


def start_uvicorn(
    app_module: str = "main:app",
    host: str = "0.0.0.0",
    port: int = 42014,
    conda_env: str = "ai_instance_manager",
    project_dir: str = "/config/workspace/projects/apps/ai_instance_manager",
    log_file: str = "/tmp/uvicorn.log",
) -> CommandResult:
    """Start the FastAPI/uvicorn process inside the container (via nohup)."""
    cmd = (
        f"source /root/conda/etc/profile.d/conda.sh && "
        f"conda activate {conda_env} && "
        f"cd {project_dir} && "
        f"nohup uvicorn {app_module} --host {host} --port {port} "
        f">> {log_file} 2>&1 & echo $!"
    )
    full_cmd = f'bash -lc "{cmd}"'
    return run_command(full_cmd, timeout=15)


def stop_uvicorn(port: int = 42014) -> CommandResult:
    """Kill all uvicorn processes listening on the given port."""
    cmd = f"fuser -k {port}/tcp 2>/dev/null; pkill -f 'uvicorn.*{port}' 2>/dev/null; echo done"
    return run_command(cmd, timeout=15)


def uvicorn_status(port: int = 42014) -> CommandResult:
    """Check whether uvicorn is running on the given port."""
    cmd = f"fuser {port}/tcp 2>/dev/null && echo RUNNING || echo STOPPED"
    return run_command(cmd, timeout=10)


def read_logs(
    log_file: str = "/tmp/uvicorn.log",
    tail_lines: int = 100,
) -> CommandResult:
    """Tail the uvicorn (or any) log file from the container."""
    cmd = f"tail -n {tail_lines} {log_file} 2>&1 || echo 'Log file not found'"
    return run_command(cmd, timeout=15)


def list_directory(path: str = "/config/workspace") -> CommandResult:
    """List directory contents with detail."""
    cmd = f"ls -lah {path} 2>&1"
    return run_command(cmd, timeout=10)


def upload_file(local_content: bytes, remote_path: str) -> dict[str, Any]:
    """
    Upload bytes as a file to the VNC container via SFTP.
    `local_content` is the raw bytes of the file to write.
    """
    cfg = _cfg()
    event_type = "ssh.upload_file"
    try:
        with _client(cfg) as client:
            sftp = client.open_sftp()
            buf = BytesIO(local_content)

            # Ensure parent directory exists
            remote_dir = str(Path(remote_path).parent)
            try:
                sftp.stat(remote_dir)
            except FileNotFoundError:
                # mkdir -p equivalent
                parts = Path(remote_dir).parts
                built = ""
                for part in parts:
                    built = str(Path(built) / part) if built else part
                    try:
                        sftp.stat(built)
                    except FileNotFoundError:
                        sftp.mkdir(built)

            sftp.putfo(buf, remote_path)
            sftp.close()

        result = {
            "remote_path": remote_path,
            "size_bytes": len(local_content),
            "success": True,
        }
        logger.debug(event_type, "success", result)
        return result
    except Exception as exc:
        payload = {"remote_path": remote_path, "error": str(exc), "success": False}
        logger.debug(event_type, "error", payload)
        raise RuntimeError(f"SFTP upload failed: {exc}") from exc


def download_file(remote_path: str) -> dict[str, Any]:
    """
    Download a file from the VNC container via SFTP.
    Returns base64-encoded content so it is JSON-serialisable.
    """
    cfg = _cfg()
    event_type = "ssh.download_file"
    try:
        with _client(cfg) as client:
            sftp = client.open_sftp()
            buf = BytesIO()
            sftp.getfo(remote_path, buf)
            sftp.close()
            raw = buf.getvalue()

        result = {
            "remote_path": remote_path,
            "size_bytes": len(raw),
            "encoding": "base64",
            "data": base64.b64encode(raw).decode("ascii"),
            "success": True,
        }
        logger.debug(event_type, "success", {
            "remote_path": remote_path,
            "size_bytes": len(raw),
        })
        return result
    except Exception as exc:
        payload = {"remote_path": remote_path, "error": str(exc), "success": False}
        logger.debug(event_type, "error", payload)
        raise RuntimeError(f"SFTP download failed: {exc}") from exc


def get_system_info() -> CommandResult:
    """Return a snapshot of container system info (uptime, memory, disk, processes)."""
    cmd = (
        "echo '=== UPTIME ===' && uptime && "
        "echo '=== MEMORY ===' && free -h && "
        "echo '=== DISK ===' && df -h / && "
        "echo '=== TOP PROCS ===' && ps aux --sort=-%cpu | head -15"
    )
    return run_command(cmd, timeout=15)


def check_ssh_connection() -> dict[str, Any]:
    """Ping the SSH connection and return success/failure — used by health checks."""
    cfg = _cfg()
    try:
        with _client(cfg) as client:
            _, stdout, _ = client.exec_command("echo ok", timeout=5)
            out = stdout.read().decode().strip()
            ok = out == "ok"
        logger.debug("ssh.health", "success", {"host": cfg.host, "port": cfg.port})
        return {"ssh_connected": ok, "host": cfg.host, "port": cfg.port}
    except Exception as exc:
        logger.debug("ssh.health", "error", {"host": cfg.host, "error": str(exc)})
        return {"ssh_connected": False, "host": cfg.host, "port": cfg.port, "error": str(exc)}
