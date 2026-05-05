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
ACTIVE_PATH = SESSION_ROOT / "active.md"
BOOTSTRAP_PATH = SESSION_ROOT / "bootstrap.md"
RUNLOG_PATH = Path(".agent/runlog.jsonl")
CONFIG_PATH = Path(".agent/config.json")


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


def require_active() -> str:
    session_id = active_session_id()
    if not session_id:
        print("error: no active session. Run `agent_session.py start <name> --goal ...`", file=sys.stderr)
        raise SystemExit(1)
    if not session_dir(session_id).exists():
        print(f"error: active session folder is missing: {session_dir(session_id)}", file=sys.stderr)
        raise SystemExit(1)
    return session_id


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


def artifacts_for(session_id: str) -> dict:
    path = session_dir(session_id) / "artifacts.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def write_bootstrap(session_id: str) -> Path:
    directory = session_dir(session_id)
    artifacts = artifacts_for(session_id)
    workspace = artifacts.get("workspace_path", str(Path.cwd()))
    openspec_change = artifacts.get("openspec_change", "none")
    goal = artifacts.get("goal", "unknown")
    git_status = run_git(["status", "--short"], fallback="")
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
        git_status or "clean or unavailable",
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
    append(
        directory / "changes.md",
        f"\n## Git Status Snapshot {timestamp}\n\n```text\n{git_status or 'clean or unavailable'}\n```\n",
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
    write_bootstrap(session_id)
    maybe_scan_context()
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
    compact_session(session_id, ingest_reason="checkpoint")
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
    path = write_bootstrap(session_id)
    print(path.read_text(encoding="utf-8"))
    return 0


def cmd_compact(args: argparse.Namespace) -> int:
    session_id = args.session_id or require_active()
    path = compact_session(session_id, args.summary, args.next)
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

    if not session_id:
        warnings.append("no active session")
        if not BOOTSTRAP_PATH.exists():
            write(
                BOOTSTRAP_PATH,
                "# Session Bootstrap\n\nNo active session yet.\n\nStart one with `python3 .agent/tools/agent_session.py start <name> --goal \"<goal>\"`.\n",
            )
    else:
        directory = session_dir(session_id)
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
        ):
            if not (directory / name).exists():
                errors.append(f"missing {directory / name}")

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
        print(f"marked {session_id} archived")
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
