#!/usr/bin/env python3
"""Package-level regression checks for agent-gov."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[2]
INIT_SCRIPT = PACKAGE_ROOT / ".codex" / "skills" / "agent-gov" / "scripts" / "init_agent_project.py"


def run(cmd: list[str], cwd: Path, expect_ok: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)
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
        "agent_memory.py": [target / ".agent" / "tools" / "agent_memory.py"],
        "agent_context.py": [target / ".agent" / "tools" / "agent_context.py"],
        "agent_capabilities.py": [target / "scripts" / "agent_capabilities.py"],
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


def assert_workflow_stage_closure(target: Path) -> None:
    workflow_path = target / ".agent" / "workflow.json"
    profiles_path = target / ".agent" / "workflow-profiles.json"
    if not workflow_path.exists() or not profiles_path.exists():
        return
    workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
    profiles = json.loads(profiles_path.read_text(encoding="utf-8"))
    workflow_stages = set(workflow.get("stages", []))
    for name, profile in profiles.get("profiles", {}).items():
        for stage in profile.get("stages", []):
            if stage not in workflow_stages:
                print(f"workflow profile {name} references unknown stage: {stage}", file=sys.stderr)
                raise SystemExit(1)


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


def assert_task_board_guards(init_script: Path, temp_root: Path, python: str) -> None:
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
    done_without_conclusion = run([python, "scripts/agent_task.py", "update", "guard-task", "--state", "done"], cwd=guarded, expect_ok=False)
    if "conclusion" not in (done_without_conclusion.stdout + done_without_conclusion.stderr):
        print("agent_task.py did not reject done without delivery_conclusion", file=sys.stderr)
        print(done_without_conclusion.stdout + done_without_conclusion.stderr, file=sys.stderr)
        raise SystemExit(1)

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


def main() -> int:
    python = sys.executable
    temp_root = Path(tempfile.mkdtemp(prefix="agent-gov-regression-"))
    try:
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
        manifest = json.loads((target / ".agent" / "manifest.json").read_text(encoding="utf-8"))
        harness = json.loads((target / ".agent" / "harness.json").read_text(encoding="utf-8"))
        if sorted(manifest.get("required_paths", [])) != sorted(harness.get("invariants", {}).get("required_paths", [])):
            print(".agent/manifest.json required_paths does not match .agent/harness.json", file=sys.stderr)
            return 1
        if not (target / "docs" / "AI_CODING_GLOSSARY.md").exists():
            print("docs/AI_CODING_GLOSSARY.md was not created", file=sys.stderr)
            return 1
        if not (target / "docs" / "features" / "INDEX.md").exists():
            print("docs/features/INDEX.md was not created", file=sys.stderr)
            return 1
        if not (target / "docs" / "DEV_MAP.md").exists():
            print("docs/DEV_MAP.md was not created", file=sys.stderr)
            return 1

        assert_no_missing_doc_refs(target)
        assert_workflow_stage_closure(target)
        run([python, "scripts/agent_check.py"], cwd=target)
        run([python, "scripts/agent_migrate.py", "doctor"], cwd=target)
        run([python, "scripts/agent_gc.py", "doctor", "--fail-on-warning"], cwd=target)
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
        run([python, "scripts/agent_score.py", "doctor"], cwd=target)
        score_report = json.loads(run([python, "scripts/agent_score.py", "score", "--json"], cwd=target).stdout)
        for dimension in ("dev_map", "harness_evolution", "mcp_policy", "governance_gc"):
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
                run([python, "scripts/agent_verify.py", "doctor"], cwd=profiled)
                run([python, "scripts/agent_gc.py", "doctor", "--fail-on-warning"], cwd=profiled)
                if (profiled / ".agent" / "mcp-policy.json").exists():
                    print("standard profile unexpectedly generated .agent/mcp-policy.json", file=sys.stderr)
                    return 1
        assert_task_board_guards(INIT_SCRIPT, temp_root, python)
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
