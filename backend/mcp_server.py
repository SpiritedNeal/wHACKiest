"""Local MCP server exposing safe developer environment inspection and restoration tools."""

from __future__ import annotations

import os
import shutil
import subprocess
import webbrowser
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import psutil

try:
    from mcp.server.fastmcp import FastMCP
except ModuleNotFoundError:
    from mcp.server.mcpserver import MCPServer as FastMCP

mcp = FastMCP("switchboard")


@dataclass
class ManagedService:
    """In-memory record for a background command started by SWITCHBOARD."""

    project_id: str
    pid: int
    create_time: float
    cmd: str
    cwd: str
    started_at: str
    process: subprocess.Popen[Any]


_MANAGED_SERVICES: dict[str, ManagedService] = {}


def _is_managed_process_alive(service: ManagedService) -> bool:
    """Verify that the tracked PID is still running and belongs to the same process."""
    try:
        proc = psutil.Process(service.pid)
        if not proc.is_running() or proc.status() == psutil.STATUS_ZOMBIE:
            return False
        # Compare creation times to guard against OS PID reuse.
        return abs(proc.create_time() - service.create_time) < 1.0
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False


@mcp.tool()
def inspect_git_status(repo_path: str) -> dict[str, Any]:
    """Inspect a local git repository without modifying or discarding any changes."""
    path = Path(repo_path).expanduser()
    if not path.exists() or not path.is_dir():
        return {
            "ok": False,
            "repo_path": str(path),
            "error": f"Directory does not exist: {path}",
        }

    inside_check = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=str(path),
        capture_output=True,
        text=True,
        check=False,
    )
    if inside_check.returncode != 0 or inside_check.stdout.strip() != "true":
        return {
            "ok": False,
            "repo_path": str(path),
            "error": f"Not a git repository: {path}",
        }

    branch_proc = subprocess.run(
        ["git", "symbolic-ref", "--short", "HEAD"],
        cwd=str(path),
        capture_output=True,
        text=True,
        check=False,
    )
    if branch_proc.returncode == 0 and branch_proc.stdout.strip():
        branch = branch_proc.stdout.strip()
    else:
        detached_proc = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(path),
            capture_output=True,
            text=True,
            check=False,
        )
        branch = (
            f"detached@{detached_proc.stdout.strip()}"
            if detached_proc.returncode == 0 and detached_proc.stdout.strip()
            else "HEAD (unborn)"
        )

    status_proc = subprocess.run(
        ["git", "status", "--porcelain=v1"],
        cwd=str(path),
        capture_output=True,
        text=True,
        check=False,
    )
    if status_proc.returncode != 0:
        return {
            "ok": False,
            "repo_path": str(path),
            "branch": branch,
            "error": status_proc.stderr.strip() or "Failed to read git status.",
        }

    modified_files: list[str] = []
    untracked_files: list[str] = []
    for line in status_proc.stdout.splitlines():
        if len(line) < 4:
            continue
        xy = line[:2]
        file_entry = line[3:]
        if xy == "??":
            untracked_files.append(file_entry)
        else:
            modified_files.append(f"{xy.strip()} {file_entry}")

    is_clean = len(modified_files) == 0 and len(untracked_files) == 0
    return {
        "ok": True,
        "repo_path": str(path.resolve()),
        "branch": branch,
        "modified_files": modified_files,
        "untracked_files": untracked_files,
        "is_clean": is_clean,
    }


@mcp.tool()
def open_vscode_workspace(target_path: str) -> dict[str, Any]:
    """Launch VS Code at target_path without blocking the Python process."""
    path = Path(target_path).expanduser()
    if not path.exists():
        return {
            "ok": False,
            "target_path": str(path),
            "error": f"Target path does not exist: {path}",
        }

    code_bin = shutil.which("code") or shutil.which("code.cmd")
    popen_kwargs: dict[str, Any] = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }

    if os.name == "nt":
        popen_kwargs["creationflags"] = (
            subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        )

    try:
        if code_bin:
            use_shell = code_bin.lower().endswith((".cmd", ".bat"))
            proc = subprocess.Popen(
                [code_bin, str(path.resolve())],
                shell=use_shell,
                **popen_kwargs,
            )
        else:
            return {
                "ok": False,
                "target_path": str(path.resolve()),
                "error": "VS Code CLI ('code') was not found on PATH.",
            }
    except OSError as exc:
        return {
            "ok": False,
            "target_path": str(path.resolve()),
            "error": f"Failed to launch VS Code: {exc}",
        }

    return {
        "ok": True,
        "target_path": str(path.resolve()),
        "pid": proc.pid,
        "command": code_bin,
    }


@mcp.tool()
def open_project_references(urls: list[str]) -> dict[str, Any]:
    """Open saved HTTP(S) reference URLs in the system default web browser."""
    opened: list[str] = []
    skipped: list[dict[str, str]] = []

    for raw_url in urls:
        url = raw_url.strip()
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            skipped.append({"url": raw_url, "reason": "Only valid http/https URLs are allowed."})
            continue

        try:
            launched = webbrowser.open_new_tab(url)
            if launched:
                opened.append(url)
            else:
                skipped.append({"url": url, "reason": "Browser handler returned False."})
        except Exception as exc:  # pragma: no cover - OS browser handler error
            skipped.append({"url": url, "reason": str(exc)})

    return {
        "ok": len(skipped) == 0,
        "opened": opened,
        "skipped": skipped,
    }


@mcp.tool()
def check_or_start_service(
    project_id: str,
    cmd: str,
    cwd: str,
    action: str = "check",
) -> dict[str, Any]:
    """Safely check or start a SWITCHBOARD-managed background service by project_id."""
    normalized_action = action.strip().lower()
    if normalized_action not in {"check", "start", "stop"}:
        return {
            "ok": False,
            "project_id": project_id,
            "error": f"Unsupported action '{action}'. Use 'check', 'start', or 'stop'.",
        }

    existing = _MANAGED_SERVICES.get(project_id)
    if existing is not None and not _is_managed_process_alive(existing):
        _MANAGED_SERVICES.pop(project_id, None)
        existing = None

    if normalized_action == "check":
        if existing is None:
            return {
                "ok": True,
                "project_id": project_id,
                "running": False,
                "pid": None,
                "cmd": cmd,
            }
        return {
            "ok": True,
            "project_id": project_id,
            "running": True,
            "pid": existing.pid,
            "cmd": existing.cmd,
            "cwd": existing.cwd,
            "started_at": existing.started_at,
        }

    if normalized_action == "stop":
        if existing is None:
            return {
                "ok": True,
                "project_id": project_id,
                "running": False,
                "message": "No SWITCHBOARD-managed service is running for this project.",
            }
        try:
            proc = psutil.Process(existing.pid)
            for child in proc.children(recursive=True):
                child.terminate()
            proc.terminate()
            proc.wait(timeout=3)
        except psutil.TimeoutExpired:
            proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied) as exc:
            return {
                "ok": False,
                "project_id": project_id,
                "pid": existing.pid,
                "error": f"Unable to stop managed service: {exc}",
            }
        finally:
            _MANAGED_SERVICES.pop(project_id, None)

        return {
            "ok": True,
            "project_id": project_id,
            "running": False,
            "stopped_pid": existing.pid,
        }

    # action == "start"
    if existing is not None:
        return {
            "ok": True,
            "project_id": project_id,
            "running": True,
            "already_running": True,
            "pid": existing.pid,
            "cmd": existing.cmd,
            "cwd": existing.cwd,
            "started_at": existing.started_at,
        }

    if not cmd.strip():
        return {
            "ok": False,
            "project_id": project_id,
            "running": False,
            "error": "No startup command configured for this project.",
        }

    cwd_path = Path(cwd).expanduser()
    if not cwd_path.exists() or not cwd_path.is_dir():
        return {
            "ok": False,
            "project_id": project_id,
            "running": False,
            "error": f"Working directory does not exist: {cwd_path}",
        }

    popen_kwargs: dict[str, Any] = {
        "cwd": str(cwd_path.resolve()),
        "shell": True,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if os.name == "nt":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

    try:
        proc = subprocess.Popen(cmd, **popen_kwargs)
        ps_proc = psutil.Process(proc.pid)
        managed = ManagedService(
            project_id=project_id,
            pid=proc.pid,
            create_time=ps_proc.create_time(),
            cmd=cmd,
            cwd=str(cwd_path.resolve()),
            started_at=datetime.now(timezone.utc).isoformat(),
            process=proc,
        )
        _MANAGED_SERVICES[project_id] = managed
    except (OSError, psutil.Error) as exc:
        return {
            "ok": False,
            "project_id": project_id,
            "running": False,
            "error": f"Failed to start service: {exc}",
        }

    return {
        "ok": True,
        "project_id": project_id,
        "running": True,
        "already_running": False,
        "pid": managed.pid,
        "cmd": managed.cmd,
        "cwd": managed.cwd,
        "started_at": managed.started_at,
    }


if __name__ == "__main__":
    mcp.run()
