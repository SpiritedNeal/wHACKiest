"""FastAPI application exposing SWITCHBOARD project, session, and chat orchestration endpoints."""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import agent  # noqa: E402
import db  # noqa: E402


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Ensure SQLite tables and demo workspaces are seeded on server startup."""
    db.ensure_seeded()
    yield


app = FastAPI(
    title="SWITCHBOARD API",
    description="AI-powered developer context switcher and environment restorer.",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    """Request body for natural-language context switching and recall."""

    message: str = Field(..., min_length=1)
    confirmed: bool = False
    open_browser: bool = True
    dry_run: bool = False


class ChatResponse(BaseModel):
    """Structured response returned by POST /api/chat."""

    reply: str
    action_taken: str
    mcp_logs: list[str]
    requires_confirmation: bool
    confirmation_prompt: str | None = None
    active_project: dict[str, Any] | None = None


class TodoUpdateRequest(BaseModel):
    """Request body for adding, toggling, or deleting a project TODO item."""

    action: str | None = None
    index: int | None = None
    text: str | None = None


@app.get("/api/health")
def health_check() -> dict[str, str]:
    """Liveness check endpoint."""
    return {"status": "ok", "service": "switchboard"}


@app.get("/api/projects")
def get_projects() -> dict[str, Any]:
    """Return all projects enriched with live Git status and recent sessions."""
    db.ensure_seeded()
    projects = db.list_projects()
    enriched = [agent.enrich_project(p) for p in projects]
    recent_sessions = db.list_sessions(limit=15)
    return {
        "projects": enriched,
        "recent_sessions": recent_sessions,
    }


@app.post("/api/chat", response_model=ChatResponse)
def post_chat(payload: ChatRequest) -> ChatResponse:
    """Route a natural-language developer command through the SWITCHBOARD orchestrator."""
    result = agent.orchestrate_chat(
        message=payload.message,
        confirmed=payload.confirmed,
        open_browser=payload.open_browser,
        dry_run=payload.dry_run,
    )
    return ChatResponse(**result)


@app.post("/api/projects/{project_id}/todos")
def update_todos(project_id: str, payload: TodoUpdateRequest) -> dict[str, Any]:
    """Toggle, add, or remove a TODO item for a project."""
    db.ensure_seeded()
    project = db.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")

    todos = list(project.get("todos", []))
    action = (payload.action or ("add" if payload.text and payload.index is None else "toggle")).lower()

    if action == "add":
        text = (payload.text or "").strip()
        if not text:
            raise HTTPException(status_code=400, detail="TODO text cannot be empty.")
        todos.append(text)
    elif action == "toggle":
        target_idx = payload.index
        if target_idx is None and payload.text:
            target_text = payload.text.strip().lower()
            for idx, item in enumerate(todos):
                if db.todo_text(item).lower() == target_text:
                    target_idx = idx
                    break
        if target_idx is None or target_idx < 0 or target_idx >= len(todos):
            raise HTTPException(status_code=400, detail="Valid TODO index or matching text is required.")

        item = todos[target_idx]
        if isinstance(item, dict):
            todos[target_idx] = {"text": db.todo_text(item), "done": not bool(item.get("done", False))}
        else:
            todos[target_idx] = {"text": db.todo_text(item), "done": not db.todo_is_done(item)}
    elif action == "delete":
        if payload.index is None or payload.index < 0 or payload.index >= len(todos):
            raise HTTPException(status_code=400, detail="Valid TODO index is required for deletion.")
        todos.pop(payload.index)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported action '{action}'.")

    updated = db.update_project_todos(project_id, todos)
    assert updated is not None
    enriched = agent.enrich_project(updated)
    return {
        "ok": True,
        "project": enriched,
        "todos": enriched["todos"],
    }


@app.get("/api/sessions")
def get_sessions(project_id: str | None = None, limit: int = 30) -> dict[str, Any]:
    """Return session handoff timeline history across projects."""
    db.ensure_seeded()
    sessions = db.list_sessions(project_id=project_id, limit=limit)
    return {"sessions": sessions}
