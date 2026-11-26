"""SWITCHBOARD AI Orchestrator connecting natural-language intents, SQLite, and MCP tools."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import db  # noqa: E402
import mcp_server  # noqa: E402

load_dotenv(db.PROJECT_ROOT / ".env")

_STOPWORDS = {
    "the", "and", "for", "with", "from", "into", "that", "this",
    "your", "my", "project", "workspace", "session", "progress",
}

_SWITCH_PHRASES = (
    "take me back to",
    "take me to",
    "switch back to",
    "switch over to",
    "switch to",
    "move to",
    "go back to",
    "go to",
    "jump to",
    "restore",
    "resume",
    "open",
    "load",
    "switch",
)

_CAPTURE_PHRASES = (
    "save",
    "capture",
    "checkpoint",
    "snapshot",
    "handoff",
    "hand off",
    "bookmark",
    "record",
)


def _match_project(text: str, projects: list[dict[str, Any]]) -> str | None:
    """Resolve the best matching project ID from free-form text, or None if ambiguous."""
    lowered = text.lower()
    tokens = set(re.findall(r"[a-z0-9]+", lowered))
    if not tokens:
        return None

    best_id: str | None = None
    best_score = 0

    for proj in projects:
        pid = proj["id"].lower()
        score = 0

        if pid in lowered or pid.replace("_", " ") in lowered:
            score += 12

        id_parts = [p for p in pid.split("_") if len(p) >= 3]
        for part in id_parts:
            if part in tokens or part in lowered:
                score += 5

        name_tokens = [
            t for t in re.findall(r"[a-z0-9]+", proj.get("name", "").lower())
            if len(t) >= 3 and t not in _STOPWORDS
        ]
        for tok in name_tokens:
            if tok in tokens:
                score += 4

        desc_tokens = [
            t for t in re.findall(r"[a-z0-9]+", proj.get("description", "").lower())
            if len(t) >= 4 and t not in _STOPWORDS
        ]
        for tok in desc_tokens:
            if tok in tokens:
                score += 1

        if score > best_score:
            best_score = score
            best_id = proj["id"]

    return best_id if best_score >= 4 else None


def _parse_intent_rule_based(
    message: str,
    projects: list[dict[str, Any]],
) -> dict[str, Any]:
    """Deterministic fallback intent parser that works completely offline."""
    lowered = message.strip().lower()

    matched_phrase: str | None = None
    phrase_idx = -1
    for phrase in _SWITCH_PHRASES:
        idx = lowered.find(phrase)
        if idx != -1:
            matched_phrase = phrase
            phrase_idx = idx
            break

    if matched_phrase is not None:
        before_clause = lowered[:phrase_idx].strip()
        after_clause = lowered[phrase_idx + len(matched_phrase) :].strip()
        target_id = _match_project(after_clause, projects) or _match_project(lowered, projects)
        source_id = _match_project(before_clause, projects) if before_clause else None
        return {
            "intent": "switch",
            "source_project_id": source_id,
            "target_project_id": target_id,
            "handoff_note": None,
            "parser": "rule_based",
        }

    if any(kw in lowered for kw in _CAPTURE_PHRASES):
        target_id = _match_project(lowered, projects)
        return {
            "intent": "capture",
            "source_project_id": target_id,
            "target_project_id": target_id,
            "handoff_note": None,
            "parser": "rule_based",
        }

    target_id = _match_project(lowered, projects)
    return {
        "intent": "status",
        "source_project_id": target_id,
        "target_project_id": target_id,
        "handoff_note": None,
        "parser": "rule_based",
    }


def _call_llm_json(prompt: str) -> dict[str, Any] | None:
    """Try Gemini or OpenAI for structured JSON output; return None on any failure."""
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    if gemini_key:
        try:
            from google import genai  # type: ignore

            client = genai.Client(api_key=gemini_key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={"response_mime_type": "application/json"},
            )
            if response and response.text:
                return json.loads(response.text)
        except Exception:
            pass

    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    if openai_key:
        try:
            resp = httpx.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {openai_key}"},
                json={
                    "model": "gpt-4o-mini",
                    "response_format": {"type": "json_object"},
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                },
                timeout=8.0,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            return json.loads(content)
        except Exception:
            pass

    return None


def parse_intent(message: str, projects: list[dict[str, Any]]) -> dict[str, Any]:
    """Parse user intent using LLM when available, with deterministic fallback."""
    valid_ids = {p["id"] for p in projects}
    catalog = [
        {"id": p["id"], "name": p["name"], "description": p["description"], "is_active": p["is_active"]}
        for p in projects
    ]
    llm_prompt = (
        "You are SWITCHBOARD's intent router. Classify the developer message into one intent:\n"
        '- "capture": save/capture current session progress without switching.\n'
        '- "switch": switch workspace/project (even if they also ask to save current progress first).\n'
        '- "status": ask what they were doing, unfinished TODOs, or git/session status.\n\n'
        f"Available projects: {json.dumps(catalog)}\n"
        f"User message: {json.dumps(message)}\n\n"
        "Return strict JSON with keys: "
        '{"intent": "capture"|"switch"|"status", "source_project_id": string|null, "target_project_id": string|null}.'
    )

    parsed = _call_llm_json(llm_prompt)
    if isinstance(parsed, dict) and parsed.get("intent") in {"capture", "switch", "status"}:
        src = parsed.get("source_project_id")
        tgt = parsed.get("target_project_id")
        if (src is None or src in valid_ids) and (tgt is None or tgt in valid_ids):
            # Guard against missing target when message clearly names one in rule parser.
            fallback = _parse_intent_rule_based(message, projects)
            if parsed["intent"] == "switch" and tgt is None:
                tgt = fallback.get("target_project_id")
            return {
                "intent": parsed["intent"],
                "source_project_id": src,
                "target_project_id": tgt,
                "handoff_note": None,
                "parser": "llm",
            }

    return _parse_intent_rule_based(message, projects)


def _summarize_git(git_status: dict[str, Any]) -> str:
    """Build a short human-readable summary string from inspect_git_status output."""
    if not git_status.get("ok"):
        return git_status.get("error", "Git repository status unavailable.")
    branch = git_status.get("branch", "unknown")
    modified = git_status.get("modified_files", [])
    untracked = git_status.get("untracked_files", [])
    if git_status.get("is_clean", False):
        return f"Branch '{branch}', clean working tree."
    parts: list[str] = [f"Branch '{branch}'"]
    if modified:
        parts.append(f"{len(modified)} modified ({', '.join(modified[:3])})")
    if untracked:
        parts.append(f"{len(untracked)} untracked ({', '.join(untracked[:3])})")
    return ", ".join(parts) + "."


def _generate_handoff_note(
    project: dict[str, Any],
    git_status: dict[str, Any],
    user_message: str = "",
) -> str:
    """Create a concise developer handoff note using LLM if available, else deterministically."""
    pending = db.pending_todo_texts(project.get("todos", []))
    git_summary = _summarize_git(git_status)

    if os.getenv("GEMINI_API_KEY", "").strip() or os.getenv("OPENAI_API_KEY", "").strip():
        prompt = (
            "Write a concise 1-2 sentence developer handoff note summarizing where work left off.\n"
            f"Project: {project['name']}\n"
            f"Git status: {git_summary}\n"
            f"Pending TODOs: {json.dumps(pending[:3])}\n"
            f"Previous note: {project.get('last_handoff_note', '')}\n"
            f"User request: {user_message}\n"
            'Return strict JSON: {"handoff_note": "..."}'
        )
        llm_res = _call_llm_json(prompt)
        if isinstance(llm_res, dict) and isinstance(llm_res.get("handoff_note"), str):
            note = llm_res["handoff_note"].strip()
            if note:
                return note

    if pending:
        top_todos = "; ".join(pending[:2])
        return f"Captured on {git_summary} Next up: {top_todos}."
    return f"Captured on {git_summary} All tracked TODOs are complete."


def _run_mcp_inspect_git(repo_path: str, mcp_logs: list[str]) -> dict[str, Any]:
    """Invoke inspect_git_status and record an MCP audit log entry."""
    res = mcp_server.inspect_git_status(repo_path)
    if res.get("ok"):
        mcp_logs.append(
            f"MCP[inspect_git_status] {Path(repo_path).name} -> "
            f"branch={res.get('branch')}, clean={res.get('is_clean')}, "
            f"modified={len(res.get('modified_files', []))}, untracked={len(res.get('untracked_files', []))}"
        )
    else:
        mcp_logs.append(f"MCP[inspect_git_status] {repo_path} -> error={res.get('error')}")
    return res


def _run_mcp_service(
    project: dict[str, Any],
    action: str,
    mcp_logs: list[str],
) -> dict[str, Any]:
    """Invoke check_or_start_service and record an MCP audit log entry."""
    res = mcp_server.check_or_start_service(
        project_id=project["id"],
        cmd=project.get("startup_cmd", ""),
        cwd=project.get("workspace_path", ""),
        action=action,
    )
    mcp_logs.append(
        f"MCP[check_or_start_service] {project['id']} ({action}) -> "
        f"running={res.get('running')}, pid={res.get('pid')}"
    )
    return res


def _run_mcp_vscode(workspace_path: str, dry_run: bool, mcp_logs: list[str]) -> dict[str, Any]:
    """Invoke open_vscode_workspace (or log dry-run during automated tests)."""
    if dry_run:
        res = {"ok": True, "target_path": workspace_path, "dry_run": True}
        mcp_logs.append(f"MCP[open_vscode_workspace] {workspace_path} -> dry_run=True")
        return res
    res = mcp_server.open_vscode_workspace(workspace_path)
    mcp_logs.append(
        f"MCP[open_vscode_workspace] {workspace_path} -> ok={res.get('ok')}"
        + (f", pid={res.get('pid')}" if res.get("pid") else f", error={res.get('error')}")
    )
    return res


def _run_mcp_references(
    urls: list[str],
    open_browser: bool,
    dry_run: bool,
    mcp_logs: list[str],
) -> dict[str, Any]:
    """Invoke open_project_references when enabled (or log dry-run/skipped)."""
    if not urls or not open_browser:
        reason = "disabled" if not open_browser else "no_urls"
        mcp_logs.append(f"MCP[open_project_references] skipped ({reason})")
        return {"ok": True, "opened": [], "skipped": []}
    if dry_run:
        mcp_logs.append(f"MCP[open_project_references] {len(urls)} URL(s) -> dry_run=True")
        return {"ok": True, "opened": urls, "skipped": [], "dry_run": True}
    res = mcp_server.open_project_references(urls)
    mcp_logs.append(
        f"MCP[open_project_references] {len(urls)} URL(s) -> opened={len(res.get('opened', []))}"
    )
    return res


def enrich_project(
    project: dict[str, Any],
    mcp_logs: list[str] | None = None,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    """Attach live Git status, managed service status, and recent sessions to a project."""
    logs = mcp_logs if mcp_logs is not None else []
    git_status = _run_mcp_inspect_git(project["repo_path"], logs)
    service_status = _run_mcp_service(project, "check", logs)
    recent_sessions = db.list_sessions(project_id=project["id"], limit=5, db_path=db_path)
    return {
        **project,
        "git_status": git_status,
        "branch": git_status.get("branch", ""),
        "is_clean": git_status.get("is_clean", False),
        "modified_files": git_status.get("modified_files", []),
        "untracked_files": git_status.get("untracked_files", []),
        "service_status": service_status,
        "recent_sessions": recent_sessions,
    }


def _capture_project_context(
    project: dict[str, Any],
    user_message: str,
    mcp_logs: list[str],
    db_path: Path | str | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Inspect git, generate handoff note, and persist session snapshot for a project."""
    git_status = _run_mcp_inspect_git(project["repo_path"], mcp_logs)
    git_branch = git_status.get("branch", "main")
    git_summary = _summarize_git(git_status)
    handoff_note = _generate_handoff_note(project, git_status, user_message=user_message)
    session = db.save_session(
        project_id=project["id"],
        git_branch=git_branch,
        git_summary=git_summary,
        handoff_note=handoff_note,
        db_path=db_path,
    )
    updated_project = db.get_project(project["id"], db_path=db_path) or project
    return updated_project, session, git_status


def orchestrate_chat(
    message: str,
    confirmed: bool = False,
    open_browser: bool = True,
    dry_run: bool = False,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    """Process a natural-language developer command via SQLite + MCP tools."""
    db.ensure_seeded(db_path=db_path)
    projects = db.list_projects(db_path=db_path)
    active_project = db.get_active_project(db_path=db_path) or (projects[0] if projects else None)
    mcp_logs: list[str] = []

    if not projects or active_project is None:
        return {
            "reply": "No projects are registered in SWITCHBOARD yet.",
            "action_taken": "none",
            "mcp_logs": mcp_logs,
            "requires_confirmation": False,
            "confirmation_prompt": None,
            "active_project": None,
        }

    parsed = parse_intent(message, projects)
    intent = parsed["intent"]

    # 1. Capture / Save Context
    if intent == "capture":
        target_id = parsed.get("target_project_id") or active_project["id"]
        target = db.get_project(target_id, db_path=db_path) or active_project
        updated_proj, session, git_status = _capture_project_context(
            target, message, mcp_logs, db_path=db_path
        )
        enriched = enrich_project(updated_proj, db_path=db_path)
        pending = db.pending_todo_texts(updated_proj.get("todos", []))
        reply = (
            f"Saved session #{session['id']} for **{updated_proj['name']}**.\n"
            f"- **Git:** {session['git_summary']}\n"
            f"- **Handoff note:** {session['handoff_note']}\n"
            f"- **Pending TODOs ({len(pending)}):** {', '.join(pending) if pending else 'None'}"
        )
        return {
            "reply": reply,
            "action_taken": "capture_context",
            "mcp_logs": mcp_logs,
            "requires_confirmation": False,
            "confirmation_prompt": None,
            "active_project": enriched,
        }

    # 2. Switch Project
    if intent == "switch":
        target_id = parsed.get("target_project_id")
        if not target_id:
            names = ", ".join(f"`{p['id']}` ({p['name']})" for p in projects)
            return {
                "reply": f"Which project would you like to switch to? Available projects: {names}.",
                "action_taken": "clarify_project",
                "mcp_logs": mcp_logs,
                "requires_confirmation": False,
                "confirmation_prompt": None,
                "active_project": enrich_project(active_project, db_path=db_path),
            }

        target = db.get_project(target_id, db_path=db_path)
        assert target is not None

        # Safety check: if current active project has a running managed service, ask before stopping.
        if active_project["id"] != target["id"]:
            svc_status = _run_mcp_service(active_project, "check", mcp_logs)
            if svc_status.get("running") and not confirmed:
                enriched_active = enrich_project(active_project, db_path=db_path)
                prompt = (
                    f"{active_project['name']} has a managed background service running "
                    f"(PID {svc_status.get('pid')}: `{active_project.get('startup_cmd')}`). "
                    f"Stop it and switch to {target['name']}?"
                )
                return {
                    "reply": prompt,
                    "action_taken": "confirmation_required",
                    "mcp_logs": mcp_logs,
                    "requires_confirmation": True,
                    "confirmation_prompt": prompt,
                    "active_project": enriched_active,
                }

            if svc_status.get("running") and confirmed:
                _run_mcp_service(active_project, "stop", mcp_logs)

            # Capture outgoing project state before switching away.
            _, saved_session, _ = _capture_project_context(
                active_project, message, mcp_logs, db_path=db_path
            )
        else:
            saved_session = None

        # Activate target project and restore workspace via MCP tools.
        activated = db.set_active_project(target["id"], db_path=db_path) or target
        _run_mcp_vscode(activated["workspace_path"], dry_run=dry_run, mcp_logs=mcp_logs)
        _run_mcp_references(
            activated.get("reference_urls", []),
            open_browser=open_browser,
            dry_run=dry_run,
            mcp_logs=mcp_logs,
        )
        enriched_target = enrich_project(activated, mcp_logs=mcp_logs, db_path=db_path)
        pending = db.pending_todo_texts(activated.get("todos", []))

        saved_line = (
            f"Captured outgoing context for **{active_project['name']}** "
            f"(session #{saved_session['id']}).\n"
            if saved_session is not None
            else ""
        )
        dirty_count = len(enriched_target["modified_files"]) + len(enriched_target["untracked_files"])
        git_line = (
            f"Branch `{enriched_target['branch']}` (clean)"
            if enriched_target["is_clean"]
            else f"Branch `{enriched_target['branch']}` ({dirty_count} uncommitted item(s))"
        )
        todo_lines = "\n".join(f"  - {t}" for t in pending) if pending else "  - None"

        reply = (
            f"{saved_line}"
            f"Switched active workspace to **{activated['name']}**.\n"
            f"- **Git Status:** {git_line}\n"
            f"- **Restored Handoff Note:** {activated['last_handoff_note']}\n"
            f"- **Pending TODOs ({len(pending)}):**\n{todo_lines}"
        )
        return {
            "reply": reply,
            "action_taken": "switch_project",
            "mcp_logs": mcp_logs,
            "requires_confirmation": False,
            "confirmation_prompt": None,
            "active_project": enriched_target,
        }

    # 3. Status / Recall Query (does not switch workspaces)
    query_project_id = parsed.get("target_project_id") or active_project["id"]
    queried = db.get_project(query_project_id, db_path=db_path) or active_project
    enriched = enrich_project(queried, mcp_logs=mcp_logs, db_path=db_path)
    recent = enriched.get("recent_sessions", [])
    last_session = recent[0] if recent else None
    pending = db.pending_todo_texts(enriched.get("todos", []))
    dirty_files = enriched["modified_files"] + enriched["untracked_files"]

    session_info = (
        f"Session #{last_session['id']} ({last_session['timestamp']}): {last_session['git_summary']}"
        if last_session
        else "No recorded sessions yet."
    )
    dirty_info = ", ".join(dirty_files) if dirty_files else "Working tree is clean."
    todo_info = "\n".join(f"  - {t}" for t in pending) if pending else "  - None"

    reply = (
        f"Context recall for **{enriched['name']}** (no workspace switch performed):\n"
        f"- **Last Session:** {session_info}\n"
        f"- **Handoff Note:** {enriched['last_handoff_note']}\n"
        f"- **Git (`{enriched['branch']}`):** {dirty_info}\n"
        f"- **Pending TODOs ({len(pending)}):**\n{todo_info}"
    )
    return {
        "reply": reply,
        "action_taken": "status_recall",
        "mcp_logs": mcp_logs,
        "requires_confirmation": False,
        "confirmation_prompt": None,
        "active_project": enrich_project(active_project, db_path=db_path),
    }
