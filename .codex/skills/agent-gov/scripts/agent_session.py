#!/usr/bin/env python3
"""Manage durable agent sessions for an initialized repository."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


SESSION_ROOT = Path(".agent/sessions")
INDEX_PATH = SESSION_ROOT / "index.json"
SESSION_EVENTS_PATH = SESSION_ROOT / "events.jsonl"
ACTIVE_PATH = SESSION_ROOT / "active.md"
BOOTSTRAP_PATH = SESSION_ROOT / "bootstrap.md"
RUNLOG_PATH = Path(".agent/runlog.jsonl")
CONFIG_PATH = Path(".agent/config.json")
OFFLOAD_SCHEMA = "agent-session-offload-v1"
VALID_OFFLOAD_PRIVACY = {"public", "internal", "private-redacted"}
DEFAULT_OFFLOAD_RECALL = {
    "max_chars_per_entry": 700,
    "max_total_chars": 5000,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return re.sub(r"-+", "-", value).strip("-") or "session"


def run_git(args: list[str], fallback: str = "unknown") -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError:
        return fallback
    if result.returncode != 0:
        return fallback
    return result.stdout.strip() or fallback


def read(path: Path, fallback: str = "") -> str:
    if not path.exists():
        return fallback
    return path.read_text(encoding="utf-8")


def load_project_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def positive_int(value: object, fallback: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return fallback
    return parsed if parsed > 0 else fallback


def offload_recall_policy() -> dict:
    raw = load_project_config().get("session_offload_recall", {})
    return {
        "max_chars_per_entry": positive_int(
            raw.get("max_chars_per_entry"),
            DEFAULT_OFFLOAD_RECALL["max_chars_per_entry"],
        ),
        "max_total_chars": positive_int(
            raw.get("max_total_chars"),
            DEFAULT_OFFLOAD_RECALL["max_total_chars"],
        ),
    }


def compact_one_line(text: str) -> str:
    return " ".join(text.split())


def clip_text(text: str, limit: int) -> tuple[str, bool]:
    if len(text) <= limit:
        return text, False
    if limit <= 20:
        return text[:limit], True
    return text[: limit - 15].rstrip() + " ... [truncated]", True


def governance_profile() -> str:
    profile = load_project_config().get("governance_profile", "standard")
    return profile if profile in {"core", "standard", "full"} else "standard"


def resume_steps(session_id: str, workspace: str, openspec_change: str) -> list[str]:
    profile = governance_profile()
    steps = [
        f"`cd {workspace}`",
        "Read `.agent/sessions/active.md`.",
        f"Read `.agent/sessions/{session_id}/handoff.md`.",
        f"Read `.agent/sessions/{session_id}/context.md`.",
        f"Read `.agent/sessions/{session_id}/changes.md`.",
        f"Read `.agent/sessions/{session_id}/validation.md`.",
        f"Read `.agent/sessions/{session_id}/grounding.md` and confirm current repository truth before editing.",
        f"Read `.agent/sessions/{session_id}/offload-index.md`, then use offload recall only for selected evidence-backed history.",
        f"If linked, read the embedded spec change: `{openspec_change}`.",
    ]
    if Path(".agent/workflow.json").exists() and Path(".agent/worktrees.json").exists():
        steps.append("Read `.agent/workflow.json` and `.agent/worktrees.json` when continuing implementation, validation, or finish work.")
    else:
        steps.append("Read `AGENTS.md`, `.agent/config.json`, and `.agent/harness.json` for the generated governance profile and required paths.")
    if Path(".agent/task-board.json").exists():
        steps.append("Read `.agent/task-board.json` before non-tiny edits and confirm task state.")
    if Path(".agent/subagents.json").exists():
        steps.append("Read accepted or rejected subagent snapshots recorded in handoff, changes, or validation notes.")
    if Path(".agent/tools/agent_context.py").exists():
        steps.append("Run `python3 .agent/tools/agent_context.py scan --limit 10` if context size or stale bootstrap state is unclear.")
    steps.append("Review recent append-only session events with `python3 .agent/tools/agent_session.py events --limit 10` when handoff state is unclear.")
    steps.extend(
        [
            "Run `git status --short`.",
            "Confirm current branch, worktree path, dirty files, validation status, workflow gate status, and the next task before editing."
            if profile != "core"
            else "Confirm current branch, dirty files, validation status, and the next task before editing.",
        ]
    )
    return steps


def numbered_steps(steps: list[str]) -> list[str]:
    return [f"{index}. {step}" for index, step in enumerate(steps, start=1)]


def load_index() -> dict:
    if INDEX_PATH.exists():
        return json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    return {"schema": "agent-session-index-v1", "active_session": None, "sessions": []}


def save_index(data: dict) -> None:
    SESSION_ROOT.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def append(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(text)


def emit_session_event(
    *,
    event_type: str,
    session_id: str | None,
    summary: str,
    artifacts: list[str] | None = None,
    payload: dict | None = None,
) -> dict:
    item = {
        "schema": "agent-session-event-v1",
        "id": f"session-event-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}",
        "created_at": utc_now(),
        "event_type": event_type,
        "session_id": session_id,
        "summary": summary,
        "source": ".agent/tools/agent_session.py",
        "artifacts": artifacts or [],
        "payload": payload or {},
    }
    SESSION_EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SESSION_EVENTS_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(item, ensure_ascii=False) + "\n")
    return item


def read_session_events(session_id: str | None = None, limit: int = 10) -> list[dict]:
    if not SESSION_EVENTS_PATH.exists():
        return []
    rows: list[dict] = []
    for line in SESSION_EVENTS_PATH.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if session_id is None or item.get("session_id") == session_id:
            rows.append(item)
    return rows[-limit:]


def format_recent_events(session_id: str, limit: int = 8) -> list[str]:
    events = read_session_events(session_id, limit)
    if not events:
        return ["- No session events recorded yet."]
    return [
        f"- {item.get('created_at', 'unknown')} `{item.get('event_type', 'unknown')}`: {item.get('summary', '')}"
        for item in events
    ]


def record_runlog(
    *,
    kind: str,
    outcome: str,
    summary: str,
    session_id: str | None = None,
    command: str | None = None,
    artifacts: list[str] | None = None,
) -> None:
    item = {
        "schema": "agent-runlog-event-v1",
        "id": f"run-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}",
        "trace_id": uuid.uuid4().hex[:12],
        "created_at": utc_now(),
        "kind": kind,
        "outcome": outcome,
        "summary": summary,
        "session_id": session_id,
        "command": command,
        "source": ".agent/tools/agent_session.py",
        "tags": [],
        "artifacts": artifacts or [],
    }
    RUNLOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with RUNLOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(item, ensure_ascii=False) + "\n")


def maybe_ingest_memory(session_id: str, reason: str) -> None:
    tool = Path(".agent/tools/agent_memory.py")
    if not tool.exists():
        return
    try:
        subprocess.run(
            [sys.executable, str(tool), "ingest-session", session_id, "--reason", reason],
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError:
        return


def maybe_scan_context() -> None:
    tool = Path(".agent/tools/agent_context.py")
    if not tool.exists():
        return
    try:
        subprocess.run(
            [sys.executable, str(tool), "scan", "--limit", "5"],
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError:
        return


def active_session_id() -> str | None:
    return load_index().get("active_session")


def session_dir(session_id: str) -> Path:
    return SESSION_ROOT / session_id


def offload_path(session_id: str) -> Path:
    return session_dir(session_id) / "offload.jsonl"


def grounding_path(session_id: str) -> Path:
    return session_dir(session_id) / "grounding.md"


def offload_index_path(session_id: str) -> Path:
    return session_dir(session_id) / "offload-index.md"


def task_map_path(session_id: str) -> Path:
    return session_dir(session_id) / "task-map.mmd"


def require_active() -> str:
    session_id = active_session_id()
    if not session_id:
        print("error: no active session. Run `agent_session.py start <name> --goal ...`", file=sys.stderr)
        raise SystemExit(1)
    if not session_dir(session_id).exists():
        print(f"error: active session folder is missing: {session_dir(session_id)}", file=sys.stderr)
        raise SystemExit(1)
    return session_id


def load_jsonl(path: Path) -> tuple[list[dict], list[str]]:
    rows: list[dict] = []
    errors: list[str] = []
    if not path.exists():
        return rows, errors
    for index, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"{path}:{index}: {exc}")
            continue
        rows.append(item)
    return rows, errors


def session_offload_entries(session_id: str) -> tuple[list[dict], list[str]]:
    entries, errors = load_jsonl(offload_path(session_id))
    for item in entries:
        if item.get("schema") != OFFLOAD_SCHEMA:
            errors.append(f"{offload_path(session_id)} entry {item.get('id') or '<missing-id>'} has invalid schema")
        if item.get("authority") != "advisory":
            errors.append(f"{offload_path(session_id)} entry {item.get('id') or '<missing-id>'} is not advisory")
        evidence = item.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"{offload_path(session_id)} entry {item.get('id') or '<missing-id>'} has no evidence handles")
    return entries, errors


def runlog_ids() -> set[str]:
    rows, _ = load_jsonl(RUNLOG_PATH)
    return {str(item.get("id")) for item in rows if item.get("id")}


def session_event_ids() -> set[str]:
    rows, _ = load_jsonl(SESSION_EVENTS_PATH)
    return {str(item.get("id")) for item in rows if item.get("id")}


def strip_line_suffix(handle: str) -> str:
    match = re.match(r"^(.+?):\d+(?::\d+)?$", handle)
    return match.group(1) if match else handle


def evidence_exists(handle: str) -> bool:
    handle = handle.strip()
    if not handle:
        return False
    if handle in runlog_ids() or handle in session_event_ids():
        return True
    candidate = Path(strip_line_suffix(handle))
    return candidate.exists()


def dangling_evidence(entries: list[dict]) -> list[str]:
    errors: list[str] = []
    for item in entries:
        entry_id = item.get("id") or "<missing-id>"
        for handle in item.get("evidence", []):
            if not isinstance(handle, str) or not evidence_exists(handle):
                errors.append(f"{entry_id} evidence is missing: {handle}")
    return errors


def active_task_summary() -> list[str]:
    board_path = Path(".agent/task-board.json")
    if not board_path.exists():
        return ["- Task board: not generated for this profile."]
    try:
        board = json.loads(board_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"- Task board: invalid JSON ({exc})."]
    items = [
        item
        for item in board.get("items", [])
        if item.get("state") not in {"done", "archived", "cancelled"}
    ]
    if not items:
        return ["- Active tasks: none recorded."]
    lines = []
    for item in items[:8]:
        lines.append(
            f"- {item.get('id', 'unknown')}: {item.get('title', '')} "
            f"[state={item.get('state', 'unknown')}, stage={item.get('current_stage', 'unknown')}, profile={item.get('profile', 'unknown')}]"
        )
    return lines


def ensure_session_offload_files(session_id: str) -> None:
    directory = session_dir(session_id)
    write(directory / "refs" / ".gitkeep", "")
    if not offload_path(session_id).exists():
        write(offload_path(session_id), "")
    if not grounding_path(session_id).exists():
        write(grounding_path(session_id), render_grounding(session_id))
    refresh_offload_artifacts(session_id)


def render_grounding(session_id: str, note: str | None = None, checked: list[str] | None = None) -> str:
    artifacts = artifacts_for(session_id)
    git_status = run_git(["status", "--short"], fallback="")
    checked_lines = [f"- {item}" for item in checked or []] or ["- Not recorded yet."]
    note_lines = [f"- {note}"] if note else ["- None."]
    return "\n".join(
        [
            f"# Grounding: {session_id}",
            "",
            "## Repository Truth",
            "",
            f"- Workspace: {artifacts.get('workspace_path', str(Path.cwd()))}",
            f"- Current branch: {run_git(['branch', '--show-current'])}",
            f"- Current commit: {run_git(['rev-parse', '--short', 'HEAD'])}",
            f"- Linked spec change: {artifacts.get('openspec_change', 'none')}",
            f"- Workflow stage: {artifacts.get('workflow_stage', 'unknown')}",
            "",
            "## Git Status",
            "",
            "```text",
            git_status or "clean or unavailable",
            "```",
            "",
            "## Active Task State",
            "",
            *active_task_summary(),
            "",
            "## Current Facts Checked",
            "",
            *checked_lines,
            "",
            "## Stale Assumptions Corrected",
            "",
            *note_lines,
            "",
            "## Rule",
            "",
            "- Current repository files, configs, specs, task-board state, and runlog evidence override memory summaries and prior chat assumptions.",
            "",
        ]
    )


def mermaid_id(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_]", "_", value)
    if not value or value[0].isdigit():
        value = f"n_{value}"
    return value[:80]


def mermaid_label(value: str, limit: int = 72) -> str:
    value = re.sub(r"[\"]", "'", " ".join(value.split()))
    return value[: limit - 3] + "..." if len(value) > limit else value


def render_task_map(session_id: str) -> str:
    entries, _ = session_offload_entries(session_id)
    artifacts = artifacts_for(session_id)
    lines = [
        "flowchart TD",
        f"  {mermaid_id(session_id)}[\"session: {mermaid_label(session_id)}\"]",
    ]
    spec = artifacts.get("openspec_change")
    if spec and spec != "none":
        spec_node = mermaid_id(f"spec_{spec}")
        lines.append(f"  {spec_node}[\"spec: {mermaid_label(str(spec))}\"]")
        lines.append(f"  {mermaid_id(session_id)} --> {spec_node}")
    for item in entries[-30:]:
        entry_id = str(item.get("id") or "offload")
        entry_node = mermaid_id(entry_id)
        lines.append(f"  {entry_node}[\"{mermaid_label(str(item.get('summary', entry_id)))}\"]")
        lines.append(f"  {mermaid_id(session_id)} --> {entry_node}")
        task_id = item.get("related_task_id")
        if task_id:
            task_node = mermaid_id(f"task_{task_id}")
            lines.append(f"  {task_node}[\"task: {mermaid_label(str(task_id))}\"]")
            lines.append(f"  {entry_node} --> {task_node}")
        spec_change = item.get("spec_change")
        if spec_change and spec_change != "none":
            spec_node = mermaid_id(f"spec_{spec_change}")
            lines.append(f"  {spec_node}[\"spec: {mermaid_label(str(spec_change))}\"]")
            lines.append(f"  {entry_node} --> {spec_node}")
    return "\n".join(lines) + "\n"


def render_offload_index(session_id: str) -> str:
    entries, errors = session_offload_entries(session_id)
    lines = [
        f"# Offload Index: {session_id}",
        "",
        "Session offload entries are advisory summaries with evidence handles. Confirm facts against the repository before editing.",
        "",
        "## Entries",
        "",
    ]
    if not entries:
        lines.append("- No offload entries recorded yet.")
    for item in entries[-20:]:
        evidence = ", ".join(str(handle) for handle in item.get("evidence", []))
        lines.append(
            f"- `{item.get('id', 'unknown')}` {item.get('created_at', 'unknown')} "
            f"[{item.get('kind', 'unknown')}]: {item.get('summary', '')}"
        )
        lines.append(f"  - Evidence: {evidence or 'missing'}")
        if item.get("related_task_id"):
            lines.append(f"  - Task: {item.get('related_task_id')}")
        if item.get("spec_change") and item.get("spec_change") != "none":
            lines.append(f"  - Spec: {item.get('spec_change')}")
    if errors:
        lines.extend(["", "## Integrity Warnings", ""])
        lines.extend(f"- {error}" for error in errors)
    lines.extend(
        [
            "",
            "## Recall",
            "",
            "```bash",
            "python3 .agent/tools/agent_session.py offload-recall <query>",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def refresh_offload_artifacts(session_id: str) -> None:
    write(offload_index_path(session_id), render_offload_index(session_id))
    write(task_map_path(session_id), render_task_map(session_id))


def render_resume_prompt(session_id: str, workspace: str, openspec_change: str) -> str:
    steps = "\n".join(numbered_steps(resume_steps(session_id, workspace, openspec_change)))
    return f"""# Resume Prompt: {session_id}

Continue the agent development session for this repository.

{steps}

Do not rely on prior chat history, VS Code tabs, selected text, or terminal scrollback.
"""


def first_nonempty_lines(path: Path, limit: int = 40) -> list[str]:
    if not path.exists():
        return []
    lines = [line.rstrip() for line in path.read_text(encoding="utf-8").splitlines()]
    return [line for line in lines if line.strip()][:limit]


def limited_text_block(text: str, limit: int) -> list[str]:
    lines = (text or "clean or unavailable").splitlines()
    if len(lines) <= limit:
        return lines
    hidden = len(lines) - limit
    return lines[:limit] + [f"... {hidden} more line(s); run `git status --short` for the full current state."]


def artifacts_for(session_id: str) -> dict:
    path = session_dir(session_id) / "artifacts.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def write_bootstrap(session_id: str) -> Path:
    directory = session_dir(session_id)
    ensure_session_offload_files(session_id)
    artifacts = artifacts_for(session_id)
    workspace = artifacts.get("workspace_path", str(Path.cwd()))
    openspec_change = artifacts.get("openspec_change", "none")
    goal = artifacts.get("goal", "unknown")
    git_status = run_git(["status", "--short"], fallback="")
    git_status_lines = limited_text_block(git_status, 40)
    start_steps = [
        f"`cd {workspace}`",
        "Read this file fully.",
        "Run `git status --short` and compare with the snapshot below.",
    ]
    if Path(".agent/workflow.json").exists() and Path(".agent/worktrees.json").exists():
        start_steps.append("Read `.agent/workflow.json` and `.agent/worktrees.json` when continuing implementation, validation, or finish work.")
    else:
        start_steps.append("Read `AGENTS.md`, `.agent/config.json`, and `.agent/harness.json` for the generated governance profile and required paths.")
    if openspec_change != "none":
        start_steps.append("Read linked embedded spec artifacts before editing.")
    if Path(".agent/task-board.json").exists():
        start_steps.append("Read `.agent/task-board.json` and confirm task state before editing.")
    start_steps.append("Continue only after confirming the next task and workflow gate status." if governance_profile() != "core" else "Continue only after confirming the next task and current repository state.")

    sections = [
        f"# Session Bootstrap: {session_id}",
        "",
        "## Start Here",
        "",
        *numbered_steps(start_steps),
        "",
        "## Session",
        "",
        f"- Goal: {goal}",
        f"- Spec change: {openspec_change}",
        f"- Workspace: {workspace}",
        f"- Git branch: {artifacts.get('git_branch', 'unknown')}",
        f"- Git commit at start: {artifacts.get('git_commit', 'unknown')}",
        "",
        "## Current Git Status Snapshot",
        "",
        "```text",
        *git_status_lines,
        "```",
        "",
        "## Handoff Summary",
        "",
        *first_nonempty_lines(directory / "handoff.md", 80),
        "",
        "## Changed Files",
        "",
        *first_nonempty_lines(directory / "changes.md", 80),
        "",
        "## Validation",
        "",
        *first_nonempty_lines(directory / "validation.md", 80),
        "",
        "## Truth-First Grounding",
        "",
        *first_nonempty_lines(grounding_path(session_id), 80),
        "",
        "## Offload Index",
        "",
        *first_nonempty_lines(offload_index_path(session_id), 80),
        "",
        "## Recent Session Events",
        "",
        *format_recent_events(session_id, 8),
        "",
        "## Memory Digest",
        "",
        *first_nonempty_lines(Path(".agent/memory/latest.md"), 40),
        "",
        "## Context Budget",
        "",
        *first_nonempty_lines(Path(".agent/context/latest.md"), 40),
        "",
        "## Resume Prompt",
        "",
        f"See `.agent/sessions/{session_id}/resume-prompt.md`.",
        "",
        "Do not rely on prior chat history, VS Code tabs, selected text, or terminal scrollback.",
        "",
    ]
    bootstrap = "\n".join(sections)
    session_bootstrap = directory / "bootstrap.md"
    write(session_bootstrap, bootstrap)
    write(BOOTSTRAP_PATH, bootstrap)
    return session_bootstrap


def refresh_resume_prompt(session_id: str) -> None:
    artifacts = artifacts_for(session_id)
    workspace = artifacts.get("workspace_path", str(Path.cwd()))
    openspec_change = artifacts.get("openspec_change", "none")
    write(session_dir(session_id) / "resume-prompt.md", render_resume_prompt(session_id, workspace, openspec_change))


def compact_session(
    session_id: str,
    summary: str | None = None,
    next_step: str | None = None,
    ingest_reason: str | None = "compact",
) -> Path:
    directory = session_dir(session_id)
    timestamp = utc_now()
    if summary:
        append(directory / "handoff.md", f"\n## Compaction {timestamp}\n\n{summary}\n")
    if next_step:
        append(directory / "handoff.md", f"\n## Next Step {timestamp}\n\n{next_step}\n")
    git_status = run_git(["status", "--short"], fallback="")
    git_status_text = "\n".join(limited_text_block(git_status, 80))
    append(
        directory / "changes.md",
        f"\n## Git Status Snapshot {timestamp}\n\n```text\n{git_status_text}\n```\n",
    )
    if ingest_reason:
        maybe_ingest_memory(session_id, ingest_reason)
    maybe_scan_context()
    refresh_resume_prompt(session_id)
    return write_bootstrap(session_id)


def create_session_files(
    session_id: str,
    goal: str,
    client_surface: str,
    remote_kind: str,
    openspec_change: str,
) -> dict:
    created_at = utc_now()
    workspace = str(Path.cwd())
    git_branch = run_git(["branch", "--show-current"])
    git_commit = run_git(["rev-parse", "--short", "HEAD"])
    directory = session_dir(session_id)

    artifacts = {
        "schema": "agent-session-artifacts-v1",
        "session_id": session_id,
        "goal": goal,
        "client_surface": client_surface,
        "remote_kind": remote_kind,
        "workspace_path": workspace,
        "git_branch": git_branch,
        "git_commit": git_commit,
        "openspec_change": openspec_change,
        "workflow_stage": "intake",
        "worktree_path": workspace,
        "created_at": created_at,
        "status": "active",
        "files": [],
        "commands": [],
    }

    write(
        directory / "session.md",
        f"""# Session {session_id}

## Goal

{goal}

## Environment

- Client surface: {client_surface}
- Remote kind: {remote_kind}
- Workspace: {workspace}
- Git branch: {git_branch}
- Git commit: {git_commit}
- Spec change: {openspec_change}
- Workflow stage: intake
- Worktree path: current workspace
- Started at: {created_at}

## Status

active
""",
    )
    write(
        directory / "handoff.md",
        f"""# Handoff: {session_id}

## Current State

- Goal: {goal}
- Status: active
- Workflow stage:
- Worktree or branch state:
- Latest validation evidence:
- Open review findings:

## Next Step

- Continue by reading `resume-prompt.md`, then confirm workflow gate status and `git status --short`.

## Notes

- Add concise checkpoints here after major work blocks.
""",
    )
    write(
        directory / "context.md",
        f"""# Context: {session_id}

## Stable Facts

-

## Relevant Files

-

## Linked Spec Artifacts

- {openspec_change}
""",
    )
    write(directory / "decisions.md", f"# Decisions: {session_id}\n\n")
    write(
        directory / "changes.md",
        f"""# Changes: {session_id}

## Changed Files

-

## Unfinished Work

-

## Worktree Notes

- Capture dirty files before rollover or handoff.
""",
    )
    write(
        directory / "validation.md",
        f"""# Validation: {session_id}

## Workflow Evidence

- Design/spec approval:
- Plan quality check:
- Worktree or branch baseline:
- TDD red command:
- TDD green command:
- Debugging record:
- Spec review:
- Quality review:
- Completion verification:
- Runlog ids:
""",
    )
    write(directory / "resume-prompt.md", render_resume_prompt(session_id, workspace, openspec_change))
    write(directory / "artifacts.json", json.dumps(artifacts, indent=2) + "\n")
    ensure_session_offload_files(session_id)
    write_bootstrap(session_id)
    maybe_scan_context()
    emit_session_event(
        event_type="started",
        session_id=session_id,
        summary=f"Started session for goal: {goal}",
        artifacts=[str(directory / "session.md"), str(directory / "resume-prompt.md")],
        payload={"client_surface": client_surface, "remote_kind": remote_kind, "openspec_change": openspec_change},
    )
    refresh_offload_artifacts(session_id)
    write_bootstrap(session_id)
    return artifacts


def cmd_start(args: argparse.Namespace) -> int:
    session_id = (
        f"{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-"
        f"{slugify(args.name)}-{uuid.uuid4().hex[:8]}"
    )
    artifacts = create_session_files(
        session_id,
        args.goal,
        args.client_surface,
        args.remote_kind,
        args.openspec_change,
    )

    data = load_index()
    data["active_session"] = session_id
    data.setdefault("sessions", []).append(
        {
            "id": session_id,
            "goal": args.goal,
            "status": "active",
            "created_at": artifacts["created_at"],
            "workspace_path": artifacts["workspace_path"],
            "git_branch": artifacts["git_branch"],
            "openspec_change": args.openspec_change,
        }
    )
    save_index(data)
    write(
        ACTIVE_PATH,
        f"""# Active Agent Session

- Session: {session_id}
- Goal: {args.goal}
- Workspace: {artifacts["workspace_path"]}
- Spec change: {args.openspec_change}
- Workflow stage: {artifacts["workflow_stage"]}
- Worktree path: {artifacts["worktree_path"]}

Resume prompt:

```bash
sed -n '1,220p' .agent/sessions/{session_id}/resume-prompt.md
```

Bootstrap:

```bash
python3 .agent/tools/agent_session.py bootstrap
```
""",
    )
    record_runlog(
        kind="session",
        outcome="started",
        summary=f"started active session {session_id}",
        session_id=session_id,
        command="agent_session.py start",
        artifacts=[str(session_dir(session_id) / "resume-prompt.md")],
    )
    print(f"started {session_id}")
    print(f"resume: .agent/sessions/{session_id}/resume-prompt.md")
    return 0


def cmd_checkpoint(args: argparse.Namespace) -> int:
    session_id = require_active()
    directory = session_dir(session_id)
    timestamp = utc_now()

    append(directory / "handoff.md", f"\n## Checkpoint {timestamp}\n\n{args.summary}\n")
    if args.decision:
        append(directory / "decisions.md", f"\n## {timestamp}\n\n{args.decision}\n")
    if args.changed_file:
        append(directory / "changes.md", "\n## Checkpoint Files\n\n")
        for path in args.changed_file:
            append(directory / "changes.md", f"- {path}\n")
    if args.validation:
        append(directory / "validation.md", f"\n## {timestamp}\n\n{args.validation}\n")
    if args.next:
        append(directory / "handoff.md", f"\n## Next Step\n\n{args.next}\n")
    emit_session_event(
        event_type="checkpoint",
        session_id=session_id,
        summary=args.summary,
        artifacts=[str(directory / "handoff.md"), str(directory / "changes.md"), str(directory / "validation.md")],
        payload={
            "decision": args.decision or "",
            "changed_files": args.changed_file,
            "validation": args.validation or "",
            "next": args.next or "",
        },
    )
    compact_session(session_id, ingest_reason="checkpoint")
    refresh_offload_artifacts(session_id)
    record_runlog(
        kind="session",
        outcome="completed",
        summary="checkpointed active session",
        session_id=session_id,
        command="agent_session.py checkpoint",
        artifacts=[str(directory / "handoff.md"), str(directory / "validation.md")],
    )

    print(f"checkpointed {session_id}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    data = load_index()
    session_id = data.get("active_session")
    print(f"active_session: {session_id or 'none'}")
    print(f"sessions: {len(data.get('sessions', []))}")
    if session_id:
        directory = session_dir(session_id)
        print(f"path: {directory}")
        print(f"resume_prompt: {directory / 'resume-prompt.md'}")
        print(f"offload_index: {offload_index_path(session_id)}")
    return 0


def cmd_resume(args: argparse.Namespace) -> int:
    session_id = args.session_id or require_active()
    refresh_resume_prompt(session_id)
    prompt = session_dir(session_id) / "resume-prompt.md"
    if not prompt.exists():
        print(f"error: missing resume prompt: {prompt}", file=sys.stderr)
        return 1
    print(prompt.read_text(encoding="utf-8"))
    return 0


def cmd_bootstrap(args: argparse.Namespace) -> int:
    session_id = args.session_id or require_active()
    emit_session_event(
        event_type="bootstrap",
        session_id=session_id,
        summary="Refreshed and printed session bootstrap",
        artifacts=[str(session_dir(session_id) / "bootstrap.md")],
    )
    path = write_bootstrap(session_id)
    print(path.read_text(encoding="utf-8"))
    return 0


def cmd_compact(args: argparse.Namespace) -> int:
    session_id = args.session_id or require_active()
    emit_session_event(
        event_type="compact",
        session_id=session_id,
        summary=args.summary or "Compacted session bootstrap and resume artifacts",
        artifacts=[str(session_dir(session_id) / "bootstrap.md"), str(session_dir(session_id) / "resume-prompt.md")],
        payload={"next": args.next or ""},
    )
    path = compact_session(session_id, args.summary, args.next)
    refresh_offload_artifacts(session_id)
    record_runlog(
        kind="session",
        outcome="completed",
        summary="compacted session bootstrap and resume artifacts",
        session_id=session_id,
        command="agent_session.py compact",
        artifacts=[str(path), str(session_dir(session_id) / "resume-prompt.md")],
    )
    print(f"compacted {session_id}")
    print(f"bootstrap: {path}")
    print(f"resume: {session_dir(session_id) / 'resume-prompt.md'}")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    errors: list[str] = []
    warnings: list[str] = []

    if not INDEX_PATH.exists():
        errors.append(f"missing {INDEX_PATH}")
        session_id = None
    else:
        try:
            session_id = active_session_id()
        except json.JSONDecodeError as exc:
            errors.append(f"{INDEX_PATH} is invalid JSON: {exc}")
            session_id = None

    if SESSION_EVENTS_PATH.exists():
        for index, line in enumerate(SESSION_EVENTS_PATH.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"{SESSION_EVENTS_PATH} line {index} is invalid JSON: {exc}")
                continue
            if item.get("schema") != "agent-session-event-v1":
                errors.append(f"{SESSION_EVENTS_PATH} line {index} has invalid schema")
    else:
        warnings.append(f"missing optional event stream {SESSION_EVENTS_PATH}; it will be created on the next session event")

    if not session_id:
        warnings.append("no active session")
        if not BOOTSTRAP_PATH.exists():
            write(
                BOOTSTRAP_PATH,
                "# Session Bootstrap\n\nNo active session yet.\n\nStart one with `python3 .agent/tools/agent_session.py start <name> --goal \"<goal>\"`.\n",
            )
    else:
        directory = session_dir(session_id)
        ensure_session_offload_files(session_id)
        for name in (
            "session.md",
            "context.md",
            "decisions.md",
            "changes.md",
            "validation.md",
            "handoff.md",
            "resume-prompt.md",
            "bootstrap.md",
            "artifacts.json",
            "grounding.md",
            "offload.jsonl",
            "offload-index.md",
            "task-map.mmd",
            "refs/.gitkeep",
        ):
            if not (directory / name).exists():
                errors.append(f"missing {directory / name}")
        entries, offload_errors = session_offload_entries(session_id)
        errors.extend(offload_errors)
        errors.extend(dangling_evidence(entries))
        if not read(grounding_path(session_id)).strip():
            errors.append(f"empty {grounding_path(session_id)}")

        validation = read(directory / "validation.md")
        validation_entries = [
            line
            for line in validation.splitlines()
            if line.startswith("- ") and ":" in line and line.split(":", 1)[1].strip()
        ]
        if validation.strip() in {f"# Validation: {session_id}", f"# Validation: {session_id}\n"} or not validation_entries:
            warnings.append("validation.md has no recorded validation")

        git_status = run_git(["status", "--short"], fallback="")
        if git_status and git_status not in read(directory / "changes.md"):
            warnings.append("worktree has changes not reflected verbatim in changes.md")

        refresh_resume_prompt(session_id)
        if not grounding_path(session_id).exists():
            write(grounding_path(session_id), render_grounding(session_id))
        refresh_offload_artifacts(session_id)
        write_bootstrap(session_id)

    for warning in warnings:
        print(f"warning: {warning}")
    for error in errors:
        print(f"error: {error}")
    if errors:
        return 1
    print("agent session doctor passed")
    return 0


def cmd_archive(args: argparse.Namespace) -> int:
    session_id = args.session_id or require_active()
    data = load_index()
    for item in data.get("sessions", []):
        if item.get("id") == session_id:
            item["status"] = "archived"
            item["archived_at"] = utc_now()
    if data.get("active_session") == session_id:
        data["active_session"] = None
        write(ACTIVE_PATH, "# Active Agent Session\n\nNo active session yet.\n")
    save_index(data)

    archive_root = Path(".agent/archive")
    source = session_dir(session_id)
    if source.exists() and args.move:
        target = archive_root / session_id
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            print(f"error: archive target exists: {target}", file=sys.stderr)
            return 1
        shutil.move(str(source), str(target))
        record_runlog(
            kind="session",
            outcome="completed",
            summary=f"archived session {session_id} to {target}",
            session_id=session_id,
            command="agent_session.py archive --move",
            artifacts=[str(target)],
        )
        emit_session_event(
            event_type="archived",
            session_id=session_id,
            summary=f"Archived session to {target}",
            artifacts=[str(target)],
            payload={"moved": True},
        )
        print(f"archived {session_id} to {target}")
    else:
        record_runlog(
            kind="session",
            outcome="completed",
            summary=f"marked session {session_id} archived",
            session_id=session_id,
            command="agent_session.py archive",
            artifacts=[str(session_dir(session_id))],
        )
        emit_session_event(
            event_type="archived",
            session_id=session_id,
            summary="Marked session archived",
            artifacts=[str(session_dir(session_id))],
            payload={"moved": False},
        )
        print(f"marked {session_id} archived")
    return 0


def cmd_events(args: argparse.Namespace) -> int:
    events = read_session_events(args.session_id, args.limit)
    if args.json:
        print(json.dumps({"schema": "agent-session-events-v1", "events": events}, indent=2))
        return 0
    if not events:
        print("no session events")
        return 0
    for item in events:
        session_id = item.get("session_id") or "none"
        print(f"{item.get('created_at')} | {session_id} | {item.get('event_type')} | {item.get('summary')}")
    return 0


def cmd_grounding(args: argparse.Namespace) -> int:
    session_id = args.session_id or require_active()
    text = render_grounding(session_id, args.note, args.checked)
    write(grounding_path(session_id), text)
    emit_session_event(
        event_type="grounding",
        session_id=session_id,
        summary="Refreshed truth-first grounding snapshot",
        artifacts=[str(grounding_path(session_id))],
        payload={"checked": args.checked, "note": args.note or ""},
    )
    record_runlog(
        kind="session",
        outcome="completed",
        summary="refreshed truth-first grounding snapshot",
        session_id=session_id,
        command="agent_session.py grounding",
        artifacts=[str(grounding_path(session_id))],
    )
    refresh_offload_artifacts(session_id)
    write_bootstrap(session_id)
    print(text)
    return 0


def cmd_offload_add(args: argparse.Namespace) -> int:
    session_id = args.session_id or require_active()
    if args.privacy not in VALID_OFFLOAD_PRIVACY:
        print(f"error: privacy must be one of {', '.join(sorted(VALID_OFFLOAD_PRIVACY))}", file=sys.stderr)
        return 1
    evidence = [item.strip() for item in args.evidence if item.strip()]
    if not evidence:
        print("error: at least one --evidence handle is required", file=sys.stderr)
        return 1
    missing = [handle for handle in evidence if not evidence_exists(handle)]
    if missing and not args.allow_missing_evidence:
        for handle in missing:
            print(f"error: evidence handle is missing: {handle}", file=sys.stderr)
        return 1
    artifacts = artifacts_for(session_id)
    entry = {
        "schema": OFFLOAD_SCHEMA,
        "id": f"offload-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}",
        "session_id": session_id,
        "created_at": utc_now(),
        "kind": args.kind,
        "summary": args.summary,
        "evidence": evidence,
        "related_task_id": args.task_id or "",
        "spec_change": args.spec_change or artifacts.get("openspec_change", "none"),
        "confidence": args.confidence,
        "privacy": args.privacy,
        "authority": "advisory",
    }
    append(offload_path(session_id), json.dumps(entry, ensure_ascii=False) + "\n")
    refresh_offload_artifacts(session_id)
    emit_session_event(
        event_type="offload",
        session_id=session_id,
        summary=args.summary,
        artifacts=[str(offload_path(session_id)), str(offload_index_path(session_id)), str(task_map_path(session_id))],
        payload={"offload_id": entry["id"], "evidence": evidence},
    )
    record_runlog(
        kind="session",
        outcome="completed",
        summary=f"recorded session offload {entry['id']}",
        session_id=session_id,
        command="agent_session.py offload-add",
        artifacts=[str(offload_path(session_id)), str(offload_index_path(session_id))],
    )
    write_bootstrap(session_id)
    print(json.dumps(entry, indent=2))
    return 0


def cmd_offload_recall(args: argparse.Namespace) -> int:
    session_id = args.session_id or require_active()
    query = args.query.lower()
    entries, errors = session_offload_entries(session_id)
    policy = offload_recall_policy()
    max_chars_per_entry = positive_int(args.max_chars_per_entry, policy["max_chars_per_entry"])
    max_total_chars = positive_int(args.max_total_chars, policy["max_total_chars"])
    matches = []
    for item in entries:
        haystack = " ".join(
            [
                str(item.get("summary", "")),
                str(item.get("kind", "")),
                str(item.get("related_task_id", "")),
                str(item.get("spec_change", "")),
                " ".join(str(handle) for handle in item.get("evidence", [])),
            ]
        ).lower()
        if query in haystack:
            matches.append(item)
    result = {
        "schema": "agent-session-offload-recall-v1",
        "session_id": session_id,
        "query": args.query,
        "matches": matches[-args.limit :],
        "errors": errors,
        "rule": "Offload recall is advisory; verify current facts against repository truth sources before editing.",
    }
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if errors:
            for error in errors:
                print(f"warning: {error}")
        if not result["matches"]:
            print("no matching offload entries")
            return 0
        emitted_chars = 0
        for item in result["matches"]:
            summary = compact_one_line(str(item.get("summary", "")))
            summary, summary_truncated = clip_text(summary, max_chars_per_entry)
            evidence = ", ".join(str(handle) for handle in item.get("evidence", []))
            block = f"{item.get('created_at')} | {item.get('id')} | {item.get('kind')} | {summary}\n  evidence: {evidence}"
            if emitted_chars + len(block) > max_total_chars:
                remaining = max_total_chars - emitted_chars
                if remaining > 80:
                    clipped, _ = clip_text(block, remaining)
                    print(clipped)
                print("offload recall output budget reached; use evidence handles or `offload-index.md` for selected detail.")
                break
            print(block)
            if summary_truncated:
                print("  note: summary truncated; verify selected facts against evidence handles.")
            emitted_chars += len(block)
    return 0


def cmd_offload_map(args: argparse.Namespace) -> int:
    session_id = args.session_id or require_active()
    refresh_offload_artifacts(session_id)
    text = task_map_path(session_id).read_text(encoding="utf-8")
    print(text)
    return 0


def cmd_rollover(args: argparse.Namespace) -> int:
    session_id = args.session_id or require_active()
    if args.summary or args.next:
        compact_session(session_id, args.summary, args.next, ingest_reason="rollover")
    if not grounding_path(session_id).exists() or args.refresh_grounding:
        write(grounding_path(session_id), render_grounding(session_id, args.note, args.checked))
    refresh_resume_prompt(session_id)
    refresh_offload_artifacts(session_id)
    bootstrap = write_bootstrap(session_id)
    emit_session_event(
        event_type="rollover",
        session_id=session_id,
        summary=args.summary or "Prepared session rollover packet",
        artifacts=[
            str(bootstrap),
            str(session_dir(session_id) / "resume-prompt.md"),
            str(grounding_path(session_id)),
            str(offload_index_path(session_id)),
        ],
        payload={"next": args.next or ""},
    )
    record_runlog(
        kind="session",
        outcome="completed",
        summary="prepared session rollover packet",
        session_id=session_id,
        command="agent_session.py rollover",
        artifacts=[str(bootstrap), str(session_dir(session_id) / "resume-prompt.md")],
    )
    print(bootstrap.read_text(encoding="utf-8"))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    start = subparsers.add_parser("start", help="Start a durable agent session")
    start.add_argument("name")
    start.add_argument("--goal", required=True)
    start.add_argument("--client-surface", default="vscode-codex-extension")
    start.add_argument("--remote-kind", default="unknown")
    start.add_argument("--spec-change", "--openspec-change", dest="openspec_change", default="none")
    start.set_defaults(func=cmd_start)

    checkpoint = subparsers.add_parser("checkpoint", help="Append a checkpoint to the active session")
    checkpoint.add_argument("--summary", required=True)
    checkpoint.add_argument("--decision")
    checkpoint.add_argument("--changed-file", action="append", default=[])
    checkpoint.add_argument("--validation")
    checkpoint.add_argument("--next")
    checkpoint.set_defaults(func=cmd_checkpoint)

    status = subparsers.add_parser("status", help="Show active session status")
    status.set_defaults(func=cmd_status)

    resume = subparsers.add_parser("resume", help="Print a resume prompt")
    resume.add_argument("session_id", nargs="?")
    resume.set_defaults(func=cmd_resume)

    bootstrap = subparsers.add_parser("bootstrap", help="Print the active session bootstrap packet")
    bootstrap.add_argument("session_id", nargs="?")
    bootstrap.set_defaults(func=cmd_bootstrap)

    compact = subparsers.add_parser("compact", help="Refresh handoff, bootstrap, and resume artifacts")
    compact.add_argument("session_id", nargs="?")
    compact.add_argument("--summary")
    compact.add_argument("--next")
    compact.set_defaults(func=cmd_compact)

    events = subparsers.add_parser("events", help="Read append-only session events")
    events.add_argument("--session-id")
    events.add_argument("--limit", type=int, default=10)
    events.add_argument("--json", action="store_true")
    events.set_defaults(func=cmd_events)

    grounding = subparsers.add_parser("grounding", help="Refresh truth-first grounding for the active session")
    grounding.add_argument("session_id", nargs="?")
    grounding.add_argument("--checked", action="append", default=[], help="Current file, config, command, or evidence checked")
    grounding.add_argument("--note", help="Stale assumption corrected or grounding note")
    grounding.set_defaults(func=cmd_grounding)

    offload_add = subparsers.add_parser("offload-add", help="Record an evidence-backed compact session offload entry")
    offload_add.add_argument("--summary", required=True)
    offload_add.add_argument("--evidence", action="append", default=[], help="Path, path:line, runlog id, or session event id")
    offload_add.add_argument("--kind", default="session-summary")
    offload_add.add_argument("--task-id")
    offload_add.add_argument("--spec-change")
    offload_add.add_argument("--confidence", default="medium", choices=["low", "medium", "high"])
    offload_add.add_argument("--privacy", default="internal", choices=sorted(VALID_OFFLOAD_PRIVACY))
    offload_add.add_argument("--allow-missing-evidence", action="store_true")
    offload_add.add_argument("session_id", nargs="?")
    offload_add.set_defaults(func=cmd_offload_add)

    offload_recall = subparsers.add_parser("offload-recall", help="Search advisory offload entries for the active session")
    offload_recall.add_argument("query")
    offload_recall.add_argument("--session-id")
    offload_recall.add_argument("--limit", type=int, default=10)
    offload_recall.add_argument("--max-chars-per-entry", type=int, help="Override session_offload_recall.max_chars_per_entry")
    offload_recall.add_argument("--max-total-chars", type=int, help="Override session_offload_recall.max_total_chars")
    offload_recall.add_argument("--json", action="store_true")
    offload_recall.set_defaults(func=cmd_offload_recall)

    offload_map = subparsers.add_parser("offload-map", help="Refresh and print the active session Mermaid task map")
    offload_map.add_argument("session_id", nargs="?")
    offload_map.set_defaults(func=cmd_offload_map)

    rollover = subparsers.add_parser("rollover", help="Prepare bootstrap, grounding, offload index, and resume packet for a new session")
    rollover.add_argument("session_id", nargs="?")
    rollover.add_argument("--summary")
    rollover.add_argument("--next")
    rollover.add_argument("--checked", action="append", default=[])
    rollover.add_argument("--note")
    rollover.add_argument("--refresh-grounding", action="store_true")
    rollover.set_defaults(func=cmd_rollover)

    doctor = subparsers.add_parser("doctor", help="Check active session continuity health")
    doctor.set_defaults(func=cmd_doctor)

    archive = subparsers.add_parser("archive", help="Archive a session")
    archive.add_argument("session_id", nargs="?")
    archive.add_argument("--move", action="store_true")
    archive.set_defaults(func=cmd_archive)

    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
