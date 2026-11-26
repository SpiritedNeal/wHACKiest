"""Stage 2 verification script using FastAPI TestClient without opening external GUIs."""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import db  # noqa: E402
import main  # noqa: E402
import mcp_server  # noqa: E402


def main_test() -> None:
    # Isolate database writes in a temporary copy so Stage 1's switchboard.db stays clean,
    # while still exercising the real git repositories inside demo_workspaces/.
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_db = Path(tmp_dir) / "test_switchboard.db"
        shutil.copyfile(db.DB_PATH, tmp_db)

        with (
            patch.object(db, "DB_PATH", tmp_db),
            patch.object(mcp_server, "open_vscode_workspace", return_value={"ok": True, "dry_run": True}) as mock_vscode,
            patch.object(mcp_server, "open_project_references", return_value={"ok": True, "opened": [], "skipped": []}),
        ):
            with TestClient(main.app) as client:
                print("=== 1. GET /api/projects ===")
                resp = client.get("/api/projects")
                assert resp.status_code == 200, resp.text
                data = resp.json()
                projects = data["projects"]
                assert len(projects) == 3, f"Expected 3 projects, got {len(projects)}"
                for proj in projects:
                    assert "git_status" in proj
                    assert proj["git_status"]["ok"] is True
                    print(
                        f"- {proj['id']}: branch={proj['branch']}, "
                        f"clean={proj['is_clean']}, active={proj['is_active']}"
                    )

                print("\n=== 2. POST /api/chat ('Save my SIH progress and switch to IEEE paper') ===")
                chat_resp = client.post(
                    "/api/chat",
                    json={
                        "message": "Save my SIH progress and switch to IEEE paper",
                        "confirmed": False,
                        "open_browser": True,
                    },
                )
                assert chat_resp.status_code == 200, chat_resp.text
                chat_data = chat_resp.json()
                print(f"action_taken: {chat_data['action_taken']}")
                print(f"requires_confirmation: {chat_data['requires_confirmation']}")
                print(f"mcp_logs: {chat_data['mcp_logs']}")
                print(f"reply:\n{chat_data['reply']}\n")

                assert chat_data["action_taken"] == "switch_project"
                assert chat_data["requires_confirmation"] is False
                assert chat_data["active_project"]["id"] == "ieee_paper"
                assert len(chat_data["mcp_logs"]) >= 3
                assert mock_vscode.called, "Expected open_vscode_workspace to be called during switch"

                print("=== 3. Verify SQLite updates & GET /api/sessions ===")
                sih_after = db.get_project("sih_hackathon", db_path=tmp_db)
                ieee_after = db.get_project("ieee_paper", db_path=tmp_db)
                assert sih_after is not None and sih_after["is_active"] is False
                assert ieee_after is not None and ieee_after["is_active"] is True
                assert "Captured on Branch" in sih_after["last_handoff_note"] or sih_after["last_handoff_note"]

                sess_resp = client.get("/api/sessions")
                assert sess_resp.status_code == 200, sess_resp.text
                sessions = sess_resp.json()["sessions"]
                assert len(sessions) >= 4, f"Expected >= 4 sessions after capture, got {len(sessions)}"
                print(f"Total sessions in timeline: {len(sessions)}")
                print(f"Latest session: {sessions[0]['project_id']} -> {sessions[0]['handoff_note']}")

                print("\n=== 4. Status Recall & Live TODO Update ===")
                recall_resp = client.post(
                    "/api/chat",
                    json={"message": "What is unfinished in college assignment?"},
                )
                assert recall_resp.status_code == 200, recall_resp.text
                assert recall_resp.json()["action_taken"] == "status_recall"
                assert recall_resp.json()["active_project"]["id"] == "ieee_paper"

                todo_resp = client.post(
                    "/api/projects/ieee_paper/todos",
                    json={"action": "toggle", "index": 0},
                )
                assert todo_resp.status_code == 200, todo_resp.text
                assert todo_resp.json()["todos"][0]["done"] is True

                print("\n=== 5. Managed Service Safety Confirmation Check ===")
                def fake_service_check(project_id: str, cmd: str, cwd: str, action: str = "check") -> dict:
                    if action == "check" and project_id == "ieee_paper":
                        return {"ok": True, "project_id": project_id, "running": True, "pid": 99999, "cmd": "latexmk -pvc"}
                    if action == "stop" and project_id == "ieee_paper":
                        return {"ok": True, "project_id": project_id, "running": False, "stopped_pid": 99999}
                    return {"ok": True, "project_id": project_id, "running": False, "pid": None, "cmd": cmd}

                with patch.object(mcp_server, "check_or_start_service", side_effect=fake_service_check):
                    blocked_resp = client.post(
                        "/api/chat",
                        json={"message": "Switch to SIH hackathon", "confirmed": False},
                    )
                    assert blocked_resp.status_code == 200, blocked_resp.text
                    blocked_data = blocked_resp.json()
                    assert blocked_data["requires_confirmation"] is True
                    assert blocked_data["action_taken"] == "confirmation_required"
                    assert "99999" in (blocked_data["confirmation_prompt"] or "")

                    confirmed_resp = client.post(
                        "/api/chat",
                        json={"message": "Switch to SIH hackathon", "confirmed": True},
                    )
                    assert confirmed_resp.status_code == 200, confirmed_resp.text
                    confirmed_data = confirmed_resp.json()
                    assert confirmed_data["requires_confirmation"] is False
                    assert confirmed_data["action_taken"] == "switch_project"
                    assert confirmed_data["active_project"]["id"] == "sih_hackathon"

                print("Stage 2 verification PASSED.")


if __name__ == "__main__":
    main_test()
