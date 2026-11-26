"""SQLite persistence and demo workspace seeder for SWITCHBOARD."""

from __future__ import annotations

import json
import sqlite3
import subprocess
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "switchboard.db"
DEMO_WORKSPACES_DIR = PROJECT_ROOT / "demo_workspaces"


def _resolve_db_path(db_path: Path | str | None) -> str:
    """Resolve explicit db_path or fall back to module DB_PATH at call time."""
    return str(DB_PATH if db_path is None else db_path)


@contextmanager
def get_connection(db_path: Path | str | None = None) -> Iterator[sqlite3.Connection]:
    """Yield an SQLite connection and always close it when exiting the context."""
    conn = sqlite3.connect(_resolve_db_path(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
    finally:
        conn.close()


def init_db(db_path: Path | str | None = None) -> None:
    """Create the projects and sessions tables if they do not exist."""
    with get_connection(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                repo_path TEXT NOT NULL,
                workspace_path TEXT NOT NULL,
                startup_cmd TEXT NOT NULL DEFAULT '',
                reference_urls TEXT NOT NULL DEFAULT '[]',
                todos TEXT NOT NULL DEFAULT '[]',
                last_handoff_note TEXT NOT NULL DEFAULT '',
                is_active INTEGER NOT NULL DEFAULT 0
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                git_branch TEXT NOT NULL DEFAULT '',
                git_summary TEXT NOT NULL DEFAULT '',
                handoff_note TEXT NOT NULL DEFAULT '',
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            );
            """
        )
        conn.commit()


def _run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run a git command inside a repository directory."""
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=True,
    )


def _ensure_git_repo(repo_dir: Path, filename: str, content: str, commit_msg: str) -> str:
    """Create a sample file and initialize a real git repo with an initial commit."""
    repo_dir.mkdir(parents=True, exist_ok=True)
    sample_file = repo_dir / filename
    if not sample_file.exists():
        sample_file.write_text(content, encoding="utf-8")

    if not (repo_dir / ".git").exists():
        try:
            _run_git(["init", "-b", "main"], cwd=repo_dir)
        except subprocess.CalledProcessError:
            _run_git(["init"], cwd=repo_dir)

        _run_git(["config", "user.name", "Switchboard Demo"], cwd=repo_dir)
        _run_git(["config", "user.email", "demo@switchboard.local"], cwd=repo_dir)
        _run_git(["add", filename], cwd=repo_dir)
        _run_git(["commit", "-m", commit_msg], cwd=repo_dir)

    branch_res = subprocess.run(
        ["git", "symbolic-ref", "--short", "HEAD"],
        cwd=str(repo_dir),
        capture_output=True,
        text=True,
        check=False,
    )
    return branch_res.stdout.strip() or "main"


def _demo_specs() -> list[dict[str, Any]]:
    """Return definitions for the 3 demo workspaces and seeded projects."""
    notebook_json = json.dumps(
        {
            "cells": [
                {
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": [
                        "# CS402 Lab 4: Time-Series Forecasting\n",
                        "Compare ARIMA, XGBoost, and LSTM baselines on campus energy data.",
                    ],
                },
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": [
                        "import pandas as pd\n",
                        "print('Baseline loader ready')\n",
                    ],
                },
            ],
            "metadata": {
                "kernelspec": {
                    "display_name": "Python 3",
                    "language": "python",
                    "name": "python3",
                },
                "language_info": {"name": "python", "version": "3.12"},
            },
            "nbformat": 4,
            "nbformat_minor": 5,
        },
        indent=2,
    )

    sih_app_py = '''"""SIH Hackathon — Smart Transit Tracker dev server stub."""

from http.server import BaseHTTPRequestHandler, HTTPServer
import json


class TransitHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        payload = {"service": "sih-transit-tracker", "status": "ok"}
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", 8765), TransitHandler)
    print("Smart Transit Tracker running on http://127.0.0.1:8765")
    server.serve_forever()
'''

    ieee_paper_tex = r"""\documentclass[conference]{IEEEtran}
\title{Context-Aware Edge-Cloud Offloading for Low-Latency Developer Agents}
\begin{document}
\maketitle
\begin{abstract}
We present an adaptive offloading scheduler for multi-step developer agent workloads.
\end{abstract}
\section{Introduction}
% TODO: Add latency breakdown figure reference and updated Table II metrics.
Modern IDE assistants switch frequently between local tooling and remote inference.
\end{document}
"""

    return [
        {
            "id": "sih_hackathon",
            "name": "SIH Hackathon — Smart Transit Tracker",
            "description": "Real-time bus ETA prediction backend and alert service for Smart India Hackathon.",
            "folder": "sih_hackathon",
            "filename": "app.py",
            "content": sih_app_py,
            "commit_msg": "Initial commit: add transit tracker app.py",
            "startup_cmd": "python app.py",
            "reference_urls": [
                "https://fastapi.tiangolo.com/",
                "https://gtfs.org/documentation/overview/",
            ],
            "todos": [
                "Implement GTFS-RT delay ingestion endpoint in app.py",
                "Cache route ETA predictions per stop ID",
                "Verify alert webhook JSON schema with frontend team",
            ],
            "last_handoff_note": (
                "Stub HTTP health endpoint is working on port 8765. "
                "Next: wire the GTFS-RT feed parser into app.py and test stop-level ETA caching."
            ),
            "is_active": 1,
        },
        {
            "id": "ieee_paper",
            "name": "IEEE Paper — Edge AI Offloading",
            "description": "IEEE conference LaTeX manuscript, ablation tables, and experimental benchmarks.",
            "folder": "ieee_paper",
            "filename": "paper.tex",
            "content": ieee_paper_tex,
            "commit_msg": "Initial commit: add IEEE paper.tex draft",
            "startup_cmd": "",
            "reference_urls": [
                "https://ieeexplore.ieee.org/",
                "https://www.overleaf.com/learn/latex/Main_Page",
            ],
            "todos": [
                "Update Table II p95 latency numbers from latest ablation run",
                "Add 4 recent citations in Related Work section",
                "Check 6-page IEEE two-column margin compliance",
            ],
            "last_handoff_note": (
                "Finished Abstract and Section I draft in paper.tex. "
                "Next: plug the new p95 benchmark numbers into Table II before advisor review."
            ),
            "is_active": 0,
        },
        {
            "id": "college_assignment",
            "name": "CS402 Assignment — Time-Series Forecasting",
            "description": "Machine learning lab notebook comparing ARIMA, XGBoost, and LSTM baselines.",
            "folder": "college_assignment",
            "filename": "assignment.ipynb",
            "content": notebook_json,
            "commit_msg": "Initial commit: add assignment.ipynb starter notebook",
            "startup_cmd": "",
            "reference_urls": [
                "https://scikit-learn.org/stable/user_guide.html",
                "https://pandas.pydata.org/docs/",
            ],
            "todos": [
                "Compute 7-day vs 30-day RMSE comparison across all three models",
                "Add residual ACF/PACF diagnostic plots",
                "Export clean notebook PDF before Friday 11:59 PM deadline",
            ],
            "last_handoff_note": (
                "Data cleaning cell and train/test split are finalized in assignment.ipynb. "
                "Next: run XGBoost hyperparameter grid and compare against ARIMA baseline."
            ),
            "is_active": 0,
        },
    ]


def seed_demo_data(
    db_path: Path | str | None = None,
    workspaces_dir: Path | str | None = None,
) -> list[dict[str, Any]]:
    """Initialize SQLite schema, create 3 git-backed demo workspaces, and seed records."""
    init_db(db_path)
    base_ws = Path(DEMO_WORKSPACES_DIR if workspaces_dir is None else workspaces_dir)
    base_ws.mkdir(parents=True, exist_ok=True)

    now_iso = datetime.now(timezone.utc).isoformat()
    specs = _demo_specs()

    with get_connection(db_path) as conn:
        for spec in specs:
            repo_dir = (base_ws / spec["folder"]).resolve()
            branch = _ensure_git_repo(
                repo_dir=repo_dir,
                filename=spec["filename"],
                content=spec["content"],
                commit_msg=spec["commit_msg"],
            )

            conn.execute(
                """
                INSERT INTO projects (
                    id, name, description, repo_path, workspace_path,
                    startup_cmd, reference_urls, todos, last_handoff_note, is_active
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO NOTHING;
                """,
                (
                    spec["id"],
                    spec["name"],
                    spec["description"],
                    str(repo_dir),
                    str(repo_dir),
                    spec["startup_cmd"],
                    json.dumps(spec["reference_urls"]),
                    json.dumps(spec["todos"]),
                    spec["last_handoff_note"],
                    spec["is_active"],
                ),
            )

            existing_session = conn.execute(
                "SELECT id FROM sessions WHERE project_id = ? LIMIT 1;",
                (spec["id"],),
            ).fetchone()
            if existing_session is None:
                conn.execute(
                    """
                    INSERT INTO sessions (
                        project_id, timestamp, git_branch, git_summary, handoff_note
                    )
                    VALUES (?, ?, ?, ?, ?);
                    """,
                    (
                        spec["id"],
                        now_iso,
                        branch,
                        f"Clean initial commit ({spec['filename']})",
                        spec["last_handoff_note"],
                    ),
                )

        conn.commit()

    return list_projects(db_path)


def todo_text(item: Any) -> str:
    """Extract display text from either a string TODO or a {text, done} dict."""
    if isinstance(item, dict):
        return str(item.get("text", "")).strip()
    return str(item).strip()


def todo_is_done(item: Any) -> bool:
    """Return whether a TODO item is marked completed."""
    if isinstance(item, dict):
        return bool(item.get("done", False))
    text = str(item).strip()
    return text.startswith("[x] ") or text.startswith("[X] ")


def pending_todo_texts(todos: list[Any]) -> list[str]:
    """Return clean text strings for all incomplete TODO items."""
    return [todo_text(item) for item in todos if not todo_is_done(item) and todo_text(item)]


def _decode_project_row(row: sqlite3.Row) -> dict[str, Any]:
    """Convert an SQLite project row into a plain dictionary with decoded JSON fields."""
    data = dict(row)
    data["reference_urls"] = json.loads(data.get("reference_urls") or "[]")
    data["todos"] = json.loads(data.get("todos") or "[]")
    data["is_active"] = bool(data.get("is_active", 0))
    return data


def ensure_seeded(
    db_path: Path | str | None = None,
    workspaces_dir: Path | str | None = None,
) -> None:
    """Ensure SQLite tables exist and seed demo data if no projects are registered."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM projects;").fetchone()[0]
    if count == 0:
        seed_demo_data(db_path=db_path, workspaces_dir=workspaces_dir)


def list_projects(db_path: Path | str | None = None) -> list[dict[str, Any]]:
    """Fetch all registered projects ordered with the active project first."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM projects ORDER BY is_active DESC, name ASC;"
        ).fetchall()
    return [_decode_project_row(row) for row in rows]


def get_project(project_id: str, db_path: Path | str | None = None) -> dict[str, Any] | None:
    """Fetch a single project by ID, or None if not found."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM projects WHERE id = ?;",
            (project_id,),
        ).fetchone()
    return _decode_project_row(row) if row is not None else None


def get_active_project(db_path: Path | str | None = None) -> dict[str, Any] | None:
    """Return the currently active project, or None if none is marked active."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM projects WHERE is_active = 1 LIMIT 1;"
        ).fetchone()
    return _decode_project_row(row) if row is not None else None


def set_active_project(project_id: str, db_path: Path | str | None = None) -> dict[str, Any] | None:
    """Mark project_id as active and deactivate all other projects."""
    with get_connection(db_path) as conn:
        exists = conn.execute(
            "SELECT id FROM projects WHERE id = ?;",
            (project_id,),
        ).fetchone()
        if exists is None:
            return None
        conn.execute("UPDATE projects SET is_active = 0;")
        conn.execute("UPDATE projects SET is_active = 1 WHERE id = ?;", (project_id,))
        conn.commit()
    return get_project(project_id, db_path=db_path)


def save_session(
    project_id: str,
    git_branch: str,
    git_summary: str,
    handoff_note: str,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    """Insert a session snapshot and update the project's last_handoff_note."""
    timestamp = datetime.now(timezone.utc).isoformat()
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO sessions (project_id, timestamp, git_branch, git_summary, handoff_note)
            VALUES (?, ?, ?, ?, ?);
            """,
            (project_id, timestamp, git_branch, git_summary, handoff_note),
        )
        conn.execute(
            "UPDATE projects SET last_handoff_note = ? WHERE id = ?;",
            (handoff_note, project_id),
        )
        conn.commit()
        session_id = cursor.lastrowid
        row = conn.execute(
            """
            SELECT s.*, p.name AS project_name
            FROM sessions s
            LEFT JOIN projects p ON p.id = s.project_id
            WHERE s.id = ?;
            """,
            (session_id,),
        ).fetchone()
    return dict(row) if row is not None else {
        "id": session_id,
        "project_id": project_id,
        "timestamp": timestamp,
        "git_branch": git_branch,
        "git_summary": git_summary,
        "handoff_note": handoff_note,
    }


def list_sessions(
    project_id: str | None = None,
    limit: int = 30,
    db_path: Path | str | None = None,
) -> list[dict[str, Any]]:
    """Return session history ordered from newest to oldest."""
    with get_connection(db_path) as conn:
        if project_id:
            rows = conn.execute(
                """
                SELECT s.*, p.name AS project_name
                FROM sessions s
                LEFT JOIN projects p ON p.id = s.project_id
                WHERE s.project_id = ?
                ORDER BY s.id DESC
                LIMIT ?;
                """,
                (project_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT s.*, p.name AS project_name
                FROM sessions s
                LEFT JOIN projects p ON p.id = s.project_id
                ORDER BY s.id DESC
                LIMIT ?;
                """,
                (limit,),
            ).fetchall()
    return [dict(row) for row in rows]


def update_project_todos(
    project_id: str,
    todos: list[Any],
    db_path: Path | str | None = None,
) -> dict[str, Any] | None:
    """Persist an updated TODO list for the given project."""
    with get_connection(db_path) as conn:
        exists = conn.execute(
            "SELECT id FROM projects WHERE id = ?;",
            (project_id,),
        ).fetchone()
        if exists is None:
            return None
        conn.execute(
            "UPDATE projects SET todos = ? WHERE id = ?;",
            (json.dumps(todos), project_id),
        )
        conn.commit()
    return get_project(project_id, db_path=db_path)


if __name__ == "__main__":
    seeded = seed_demo_data()
    print(f"Seeded {len(seeded)} demo projects into {DB_PATH}")
