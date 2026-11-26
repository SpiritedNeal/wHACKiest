"""Stage 1 verification script for SWITCHBOARD database, seeder, and MCP tools."""

from __future__ import annotations

import asyncio
import inspect
import json
import sys
from pathlib import Path

# Allow running directly as `python backend/test_stage1.py` or `python test_stage1.py`
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from db import DB_PATH, get_connection, seed_demo_data  # noqa: E402
from mcp_server import check_or_start_service, inspect_git_status, mcp  # noqa: E402


def main() -> None:
    print("=== 1. Seeding demo workspaces and SQLite database ===")
    projects = seed_demo_data()
    print(f"Database path: {DB_PATH}")
    print(f"Seeded {len(projects)} projects.\n")

    print("=== 2. Querying SQLite projects table ===")
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM projects ORDER BY is_active DESC, name ASC;").fetchall()
        session_count = conn.execute("SELECT COUNT(*) FROM sessions;").fetchone()[0]

    assert len(rows) == 3, f"Expected 3 seeded projects, found {len(rows)}"
    assert session_count >= 3, f"Expected at least 3 seeded sessions, found {session_count}"

    sih_repo_path = ""
    for row in rows:
        record = dict(row)
        record["reference_urls"] = json.loads(record["reference_urls"])
        record["todos"] = json.loads(record["todos"])
        print(f"- [{record['id']}] {record['name']} (active={bool(record['is_active'])})")
        print(f"  repo_path: {record['repo_path']}")
        print(f"  todos ({len(record['todos'])}): {record['todos']}")
        print(f"  handoff: {record['last_handoff_note']}\n")
        if record["id"] == "sih_hackathon":
            sih_repo_path = record["repo_path"]

    print(f"Total seeded sessions: {session_count}\n")

    print("=== 3. Verifying registered MCP tools & inspect_git_status ===")
    tools_result = mcp.list_tools()
    registered_tools = asyncio.run(tools_result) if inspect.isawaitable(tools_result) else tools_result
    tool_names = [tool.name for tool in registered_tools]
    print(f"Registered MCP tools: {tool_names}")
    for expected in (
        "inspect_git_status",
        "open_vscode_workspace",
        "open_project_references",
        "check_or_start_service",
    ):
        assert expected in tool_names, f"Missing expected MCP tool: {expected}"

    git_status = inspect_git_status(sih_repo_path)
    print("inspect_git_status('sih_hackathon') result:")
    print(json.dumps(git_status, indent=2))
    assert git_status.get("ok") is True, f"Git inspection failed: {git_status}"
    assert git_status.get("is_clean") is True, f"Expected clean initial repo: {git_status}"

    service_status = check_or_start_service(
        project_id="sih_hackathon",
        cmd="python app.py",
        cwd=sih_repo_path,
        action="check",
    )
    print("check_or_start_service('sih_hackathon', action='check') result:")
    print(json.dumps(service_status, indent=2))
    assert service_status.get("ok") is True and service_status.get("running") is False
    print("\nStage 1 verification PASSED.")


if __name__ == "__main__":
    main()
