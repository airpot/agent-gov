#!/usr/bin/env python3
"""Initialize or retrofit a repository for agent-driven development."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


REMOTE_KINDS = {"ssh", "devcontainer", "wsl", "local", "unknown"}
SPEC_MODES = {"embedded"}
LAYOUTS = {
    "minimal": ["src", "tests", "docs", "scripts"],
    "python-app": ["src", "tests", "docs", "scripts", "configs"],
    "node-app": ["src", "tests", "docs", "scripts", "public"],
    "web-app": ["src", "tests", "docs", "scripts", "public"],
    "service": ["src", "tests", "docs", "scripts", "configs", "deploy"],
    "library": ["src", "tests", "docs", "scripts", "examples"],
}
STACK_COMMANDS = {
    "python": {
        "test": ["python -m pytest"],
        "lint": ["python -m ruff check ."],
        "typecheck": ["python -m mypy src"],
    },
    "node": {
        "build": ["npm run build"],
        "test": ["npm test"],
        "lint": ["npm run lint"],
        "typecheck": ["npm run typecheck"],
    },
    "typescript": {
        "build": ["npm run build"],
        "test": ["npm test"],
        "lint": ["npm run lint"],
        "typecheck": ["npm run typecheck"],
    },
    "go": {
        "build": ["go build ./..."],
        "test": ["go test ./..."],
        "lint": ["go vet ./..."],
    },
    "rust": {
        "build": ["cargo build"],
        "test": ["cargo test"],
        "lint": ["cargo clippy --all-targets --all-features"],
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def skill_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def template(name: str) -> str:
    return (skill_dir() / "assets" / "templates" / name).read_text(encoding="utf-8")


def render(text: str, values: dict[str, str]) -> str:
    result = text
    for key, value in values.items():
        result = result.replace("{{" + key + "}}", value)
    return result


def parse_csv(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        for item in value.split(","):
            item = item.strip()
            if item and item not in result:
                result.append(item)
    return result


def layout_dirs(layout: str, extra_dirs: list[str]) -> list[str]:
    dirs = list(LAYOUTS.get(layout, LAYOUTS["minimal"]))
    for path in extra_dirs:
        clean = path.strip().strip("/")
        if clean and clean not in dirs:
            dirs.append(clean)
    return dirs


def harness_config(
    project_name: str,
    created_at: str,
    tech_stack: list[str],
    dirs: list[str],
    openspec_enabled: bool,
    claude_enabled: bool,
) -> dict:
    validation = {
        "build": [],
        "test": [],
        "lint": [],
        "typecheck": [],
        "smoke": [],
    }
    for stack in tech_stack:
        for suite, commands in STACK_COMMANDS.get(stack.lower(), {}).items():
            for command in commands:
                if command not in validation[suite]:
                    validation[suite].append(command)

    required_paths = [
        "AGENTS.md",
        ".agent/config.json",
        ".agent/harness.json",
        ".agent/project-layout.json",
        ".agent/workflow.json",
        ".agent/worktrees.json",
        ".agent/subagents.json",
        ".agent/hooks.json",
        ".agent/knowledge.json",
        ".agent/memory.json",
        ".agent/context.json",
        ".agent/capabilities.json",
        ".agent/tooling.json",
        ".agent/security.json",
        ".agent/evals.json",
        ".agent/evals/latest.md",
        ".agent/runlog.jsonl",
        ".agent/memory/events.jsonl",
        ".agent/memory/latest.md",
        ".agent/memory/summaries/.gitkeep",
        ".agent/context/stats.jsonl",
        ".agent/context/latest.md",
        ".agent/skill-distribution.json",
        ".agent/sessions/index.json",
        ".agent/sessions/active.md",
        ".agent/sessions/bootstrap.md",
        ".agent/templates/project-review.md.tmpl",
        ".agent/templates/project-fix-log.md.tmpl",
        ".agent/templates/implementation-plan.md.tmpl",
        ".agent/templates/debugging-record.md.tmpl",
        ".agent/templates/subagent-task.md.tmpl",
        ".agent/templates/memory-summary.md.tmpl",
        ".agent/templates/memory-latest.md.tmpl",
        ".agent/templates/context-summary.md.tmpl",
        ".agent/templates/adr.md.tmpl",
        ".agent/templates/rfc.md.tmpl",
        ".agent/templates/postmortem.md.tmpl",
        ".agent/templates/quality-score.md.tmpl",
        ".agent/tools/agent_session.py",
        ".agent/tools/agent_memory.py",
        ".agent/tools/agent_context.py",
        ".agent/tools/governance_hook.py",
        ".codex/config.toml",
        ".codex/hooks.json",
        ".codex/agents/governance-searcher.toml",
        ".codex/agents/governance-explorer.toml",
        ".codex/agents/governance-worker.toml",
        ".codex/agents/governance-verifier.toml",
        ".codex/agents/governance-spec_reviewer.toml",
        ".codex/agents/governance-quality_reviewer.toml",
        ".codex/agents/governance-reviewer.toml",
        ".codex/agents/governance-coordinator.toml",
        "scripts/agent_check.py",
        "scripts/agent_spec.py",
        "scripts/agent_validate.py",
        "scripts/agent_knowledge.py",
        "scripts/agent_invariants.py",
        "scripts/agent_capabilities.py",
        "scripts/agent_runlog.py",
        "scripts/agent_tooling.py",
        "scripts/agent_security.py",
        "scripts/agent_score.py",
        "scripts/agent_sync_skills.py",
        "docs/TOOLING.md",
        "docs/QUALITY_SCORE.md",
        "docs/adr/README.md",
        "docs/rfcs/README.md",
        "docs/incidents/README.md",
        *dirs,
    ]
    if openspec_enabled:
        required_paths.extend(
            [
                "openspec/config.yaml",
                "openspec/project.md",
                ".agent/spec.json",
                "openspec/changes/.gitkeep",
                "openspec/changes/archive/.gitkeep",
                "openspec/specs/.gitkeep",
            ]
        )
    if claude_enabled:
        required_paths.extend(
            [
                "CLAUDE.md",
                ".claude/settings.json",
                ".claude/agents/governance-searcher.md",
                ".claude/agents/governance-explorer.md",
                ".claude/agents/governance-worker.md",
                ".claude/agents/governance-verifier.md",
                ".claude/agents/governance-spec_reviewer.md",
                ".claude/agents/governance-quality_reviewer.md",
                ".claude/agents/governance-reviewer.md",
                ".claude/agents/governance-coordinator.md",
            ]
        )

    return {
        "schema": "agent-harness-v1",
        "project_name": project_name,
        "created_at": created_at,
        "tech_stack": tech_stack,
        "validation": validation,
        "security": {
            "policy_as_code": [],
            "secret_scan": [],
            "dependency_audit": [],
            "sbom": [],
            "license_scan": [],
        },
        "observability": {
            "logs": [],
            "health_checks": [],
            "runlog": ".agent/runlog.jsonl",
            "capability_registry": ".agent/capabilities.json",
            "governance_score": ".agent/evals/latest.md",
        },
        "knowledge": {
            "index": "docs/index.md",
            "manifest": ".agent/knowledge.json",
            "required_docs": [
                "docs/ARCHITECTURE.md",
                "docs/QUALITY.md",
                "docs/RELIABILITY.md",
                "docs/SECURITY.md",
                "docs/TOOLING.md",
                "docs/QUALITY_SCORE.md",
                "docs/tech-debt.md",
                "docs/adr/README.md",
                "docs/rfcs/README.md",
                "docs/incidents/README.md",
            ],
        },
        "invariants": {
            "max_doc_age_days": None,
            "forbidden_paths": [],
            "required_paths": required_paths,
            "architecture_boundaries": [],
        },
    }


def project_layout_config(project_name: str, layout: str, tech_stack: list[str], dirs: list[str]) -> dict:
    return {
        "schema": "agent-project-layout-v1",
        "project_name": project_name,
        "layout": layout,
        "tech_stack": tech_stack,
        "directories": dirs,
    }


def spec_config(project_name: str, created_at: str) -> dict:
    return {
        "schema": "agent-spec-v1",
        "project_name": project_name,
        "created_at": created_at,
        "mode": "embedded",
        "source": "agent-gov",
        "paths": {
            "root": "openspec",
            "changes": "openspec/changes",
            "archive": "openspec/changes/archive",
            "specs": "openspec/specs",
            "project": "openspec/project.md",
        },
        "artifacts": {
            "proposal": "proposal.md",
            "design": "design.md",
            "tasks": "tasks.md",
        },
        "required_before_apply": ["proposal", "design", "tasks"],
        "policy": {
            "non_trivial_changes_require_change": True,
            "tasks_are_markdown_checkboxes": True,
            "archive_requires_completed_tasks_or_force": True,
            "record_session_links": True,
        },
        "commands": {
            "init": "python3 scripts/agent_spec.py init",
            "list": "python3 scripts/agent_spec.py list --json",
            "new_change": "python3 scripts/agent_spec.py new-change <name>",
            "status": "python3 scripts/agent_spec.py status --change <name> --json",
            "validate": "python3 scripts/agent_spec.py validate",
            "archive": "python3 scripts/agent_spec.py archive <name>",
            "doctor": "python3 scripts/agent_spec.py doctor",
        },
    }


def workflow_config(project_name: str, created_at: str, openspec_enabled: bool) -> dict:
    return {
        "schema": "agent-workflow-v1",
        "project_name": project_name,
        "created_at": created_at,
        "mode": "policy-gated",
        "spec_source": "agent-gov-spec" if openspec_enabled else "project-docs",
        "stages": [
            "intake",
            "spec",
            "plan",
            "isolation",
            "implementation",
            "spec_review",
            "quality_review",
            "verification",
            "handoff",
            "finish",
        ],
        "gates": {
            "design_approval": {
                "required_for": ["non_trivial_change", "architecture_change", "cross_module_behavior_change"],
                "evidence": ["embedded spec proposal/design approval or recorded project-doc approval"],
            },
            "plan_quality": {
                "required_for": ["multi_step_change", "delegated_work"],
                "requires_exact_files": True,
                "requires_commands_with_expected_results": True,
                "forbidden_placeholders": ["TBD", "TODO", "implement later", "fill in details"],
            },
            "implementation_discipline": {
                "required_for": [
                    "implementation",
                    "refactor",
                    "new_abstraction",
                    "architecture_change",
                    "multi_file_change",
                ],
                "state_assumptions_when_ambiguous": True,
                "prefer_simple_direct_code": True,
                "avoid_speculative_features": True,
                "abstractions_require_repeated_complexity_or_existing_pattern": True,
                "touch_only_requested_scope": True,
                "every_changed_line_traces_to_request": True,
                "success_criteria_required": True,
                "exceptions_require_session_note": True,
            },
            "worktree_isolation": {
                "preferred_for": ["feature_work", "implementation_plan_execution", "risky_refactor"],
                "policy": ".agent/worktrees.json",
                "baseline_validation_before_edits": True,
                "never_start_on_main_without_explicit_user_consent": True,
            },
            "tdd": {
                "required_for": ["behavior_change", "bugfix", "refactor"],
                "exceptions_require_session_note": True,
                "evidence": ["failing test command", "passing test command"],
            },
            "systematic_debugging": {
                "required_for": ["bug", "test_failure", "build_failure", "unexpected_behavior"],
                "template": ".agent/templates/debugging-record.md.tmpl",
                "evidence": ["reproduction", "root_cause", "hypothesis", "minimal_fix_validation"],
            },
            "review_sequence": {
                "required_for": ["delegated_work", "substantial_change"],
                "order": ["spec_review", "quality_review"],
                "spec_review_must_pass_before_quality_review": True,
                "re_review_after_fixes": True,
            },
            "completion_verification": {
                "required_for": ["handoff", "merge", "pull_request", "archive"],
                "fresh_validation_required": True,
                "record_results_in_runlog": True,
                "no_completion_claim_without_command_evidence": True,
            },
        },
        "commands": {
            "list_validation": "python3 scripts/agent_validate.py --list",
            "record_runlog": "python3 scripts/agent_runlog.py record --kind validation --outcome <pass|fail|skipped> --summary <summary>",
            "session_checkpoint": "python3 .agent/tools/agent_session.py checkpoint --summary <summary>",
            "session_compact": "python3 .agent/tools/agent_session.py compact --summary <summary> --next <next>",
        },
    }


def worktree_config(project_name: str, created_at: str) -> dict:
    return {
        "schema": "agent-worktree-policy-v1",
        "project_name": project_name,
        "created_at": created_at,
        "mode": "preferred-not-forced",
        "directories": {
            "preferred_project_local": ".worktrees",
            "alternate_project_local": "worktrees",
            "global_fallback": f"~/.config/agent-gov/worktrees/{project_name}",
        },
        "policy": {
            "use_existing_project_local_dir_first": True,
            "verify_project_local_dir_is_git_ignored": True,
            "add_ignore_rule_only_with_explicit_change_record": True,
            "run_project_setup_when_detected": True,
            "run_baseline_validation_before_feature_edits": True,
            "do_not_continue_from_failing_baseline_without_user_or_session_decision": True,
            "cleanup_requires_finish_decision": True,
            "discard_requires_typed_confirmation": True,
            "force_delete_requires_explicit_user_request": True,
        },
        "branching": {
            "feature_branch_prefix": "agent/",
            "avoid_main_or_master_for_implementation": True,
            "record_base_branch": True,
            "record_worktree_path_in_session": True,
        },
        "finish_options": [
            "merge_locally",
            "push_pull_request",
            "keep_branch",
            "discard_after_confirmation",
        ],
    }


def subagent_config(project_name: str, created_at: str, claude_enabled: bool) -> dict:
    roles = {
        "searcher": {
            "purpose": "External documentation, standards, API behavior, and current ecosystem checks.",
            "default_write_access": False,
        },
        "explorer": {
            "purpose": "Repository discovery, file ownership, call graph, and risk mapping.",
            "default_write_access": False,
        },
        "worker": {
            "purpose": "Bounded implementation or mechanical edits within a declared write set.",
            "default_write_access": True,
        },
        "verifier": {
            "purpose": "Tests, builds, lint, typecheck, smoke checks, and log inspection.",
            "default_write_access": False,
        },
        "spec_reviewer": {
            "purpose": "Independent review that checks implementation against the requested spec before quality review.",
            "default_write_access": False,
        },
        "quality_reviewer": {
            "purpose": "Independent review that checks maintainability, tests, safety, and project conventions after spec review passes.",
            "default_write_access": False,
        },
        "reviewer": {
            "purpose": "Independent risk review, conflict arbitration, and side-effect assessment.",
            "default_write_access": False,
        },
        "coordinator": {
            "purpose": "Optional submodule coordination for large tasks with independent subsystem boundaries.",
            "default_write_access": False,
        },
    }
    return {
        "schema": "agent-subagent-orchestration-v1",
        "project_name": project_name,
        "created_at": created_at,
        "mode": "permission-gated",
        "policy": {
            "use_only_when_allowed_by_active_instructions": True,
            "do_not_force_delegation": True,
            "do_not_pin_model_by_default": True,
            "prefer_minimal_context": True,
            "prefer_compressed_structured_outputs": True,
            "prefer_fresh_subagent_per_plan_task": True,
            "require_disjoint_worker_write_boundaries": True,
            "record_accepted_snapshots_in_session": True,
            "spec_review_before_quality_review": True,
            "re_review_after_fix": True,
        },
        "review_workflow": {
            "implementation_status_values": ["DONE", "DONE_WITH_CONCERNS", "NEEDS_CONTEXT", "BLOCKED"],
            "review_sequence": ["spec_reviewer", "quality_reviewer"],
            "handle_done_with_concerns_before_review": True,
            "handle_needs_context_by_re_dispatching_with_more_context": True,
            "handle_blocked_by_replanning_or_escalating": True,
        },
        "native_adapters": {
            "codex": {
                "enabled": True,
                "config": ".codex/config.toml",
                "hooks": ".codex/hooks.json",
                "agents_dir": ".codex/agents",
            },
            "claude": {
                "enabled": claude_enabled,
                "settings": ".claude/settings.json",
                "agents_dir": ".claude/agents",
            },
        },
        "roles": roles,
        "snapshot_contract": {
            "marker": "===SNAPSHOT===",
            "required_fields": [
                "status",
                "role",
                "files_touched",
                "exports_added_or_modified",
                "critical_finding",
                "next_dependency",
                "estimated_risk_level",
                "validation",
            ],
            "status_values": ["DONE", "DONE_WITH_CONCERNS", "NEEDS_CONTEXT", "BLOCKED"],
            "risk_values": ["low", "medium", "high"],
            "max_supporting_notes_tokens": 700,
            "prefer_path_line_first_findings": True,
        },
        "dispatch_template": ".agent/templates/subagent-task.md.tmpl",
    }


def hooks_config(project_name: str, created_at: str) -> dict:
    return {
        "schema": "agent-hooks-v1",
        "project_name": project_name,
        "created_at": created_at,
        "mode": "advisory",
        "policy": {
            "do_not_block_by_default": True,
            "session_start_is_read_only": True,
            "session_start_runs_status": True,
            "session_start_shows_memory_timeline": True,
            "session_start_shows_context_budget": True,
            "session_start_shows_capability_summary": True,
            "stop_reminds_checkpoint": True,
            "stop_ingests_active_session_memory": True,
            "stop_records_context_budget": True,
            "stop_records_runlog_evidence": True,
            "hooks_must_not_store_secrets": True,
        },
        "commands": {
            "session_start": "python3 .agent/tools/governance_hook.py --event session-start",
            "stop": "python3 .agent/tools/governance_hook.py --event stop",
            "memory_timeline": "python3 .agent/tools/agent_memory.py timeline --limit 5",
            "memory_ingest": "python3 .agent/tools/agent_memory.py ingest-session --reason hook-stop",
            "context_preview": "python3 .agent/tools/agent_context.py scan --limit 5 --no-write",
            "context_scan": "python3 .agent/tools/agent_context.py scan --limit 5",
            "capability_summary": "python3 scripts/agent_capabilities.py list --enabled",
            "runlog_tail": "python3 scripts/agent_runlog.py tail --limit 5",
        },
        "native_adapters": {
            "codex": ".codex/hooks.json",
            "claude": ".claude/settings.json",
        },
    }


def knowledge_config(project_name: str, created_at: str) -> dict:
    docs = [
        "docs/index.md",
        "docs/ARCHITECTURE.md",
        "docs/QUALITY.md",
        "docs/RELIABILITY.md",
        "docs/SECURITY.md",
        "docs/TOOLING.md",
        "docs/QUALITY_SCORE.md",
        "docs/tech-debt.md",
        "docs/adr/README.md",
        "docs/rfcs/README.md",
        "docs/incidents/README.md",
    ]
    return {
        "schema": "agent-knowledge-v1",
        "project_name": project_name,
        "created_at": created_at,
        "documents": [
            {
                "path": path,
                "owner": "unassigned",
                "last_reviewed": created_at[:10],
                "source_links": [],
                "known_stale_sections": [],
            }
            for path in docs
        ],
    }


def memory_config(project_name: str, created_at: str) -> dict:
    return {
        "schema": "agent-memory-v1",
        "project_name": project_name,
        "created_at": created_at,
        "mode": "repo-local",
        "authoritative_session_store": ".agent/sessions",
        "stores": {
            "events_jsonl": ".agent/memory/events.jsonl",
            "sqlite_index": ".agent/memory/index.sqlite3",
            "summary_dir": ".agent/memory/summaries",
            "latest_digest": ".agent/memory/latest.md",
        },
        "policy": {
            "store_summaries_not_raw_transcripts": True,
            "progressive_disclosure": ["timeline", "search", "detail"],
            "ingest_on_checkpoint": True,
            "ingest_on_compact": True,
            "ingest_on_stop_hook": True,
            "memory_is_advisory_not_authoritative": True,
            "procedural_memory_requires_review": True,
        },
        "taxonomy": {
            "episodic": {
                "description": "What happened in a session or work block.",
                "kinds": ["session-summary", "handoff", "validation", "subagent-snapshot", "incident"],
            },
            "semantic": {
                "description": "Stable project facts that should still be confirmed against the repository.",
                "kinds": ["project-fact", "architecture-fact", "dependency-fact", "api-behavior"],
            },
            "procedural": {
                "description": "Reusable workflow rules or constraints promoted only after review.",
                "kinds": ["workflow-rule", "validation-rule", "coding-rule", "review-rule"],
            },
        },
        "promotion_policy": {
            "semantic_requires_source_path": True,
            "procedural_requires_review_ref": True,
            "procedural_requires_reviewed_true": True,
            "do_not_promote_from_single_unverified_session": True,
        },
        "privacy": {
            "private_start": "<private>",
            "private_end": "</private>",
            "redaction_text": "[redacted-private]",
            "forbidden_content": ["secrets", "tokens", "ssh keys", "private credentials"],
        },
        "commands": {
            "init": "python3 .agent/tools/agent_memory.py init",
            "doctor": "python3 .agent/tools/agent_memory.py doctor",
            "timeline": "python3 .agent/tools/agent_memory.py timeline --limit 10",
            "search": "python3 .agent/tools/agent_memory.py search <query>",
            "detail": "python3 .agent/tools/agent_memory.py detail <id>",
            "ingest_session": "python3 .agent/tools/agent_memory.py ingest-session",
            "promote": "python3 .agent/tools/agent_memory.py promote <id> --to semantic|procedural --review-ref <ref>",
        },
    }


def context_budget_config(project_name: str, created_at: str) -> dict:
    return {
        "schema": "agent-context-budget-v1",
        "project_name": project_name,
        "created_at": created_at,
        "stores": {
            "stats_jsonl": ".agent/context/stats.jsonl",
            "latest_digest": ".agent/context/latest.md",
        },
        "tracked_files": [
            "AGENTS.md",
            "CLAUDE.md",
            "docs/index.md",
            "docs/ARCHITECTURE.md",
            "docs/QUALITY.md",
            "docs/RELIABILITY.md",
            "docs/SECURITY.md",
            "docs/tech-debt.md",
            ".agent/sessions/bootstrap.md",
            ".agent/memory/latest.md",
            ".agent/spec.json",
            ".agent/capabilities.json",
            ".agent/workflow.json",
            ".agent/worktrees.json",
            ".agent/tooling.json",
            ".agent/security.json",
            ".agent/evals.json",
            ".agent/evals/latest.md",
            "docs/TOOLING.md",
            "docs/QUALITY_SCORE.md",
            "docs/adr/README.md",
            "docs/rfcs/README.md",
            "docs/incidents/README.md",
            ".agent/templates/subagent-task.md.tmpl",
            ".agent/templates/implementation-plan.md.tmpl",
            ".agent/templates/debugging-record.md.tmpl",
            "openspec/project.md",
        ],
        "tracked_globs": [
            "openspec/changes/*/proposal.md",
            "openspec/changes/*/design.md",
            "openspec/changes/*/tasks.md",
        ],
        "budgets": {
            "max_total_tracked_tokens": 20000,
            "max_single_doc_tokens": 3000,
            "max_agent_instruction_tokens": 1600,
            "max_claude_instruction_tokens": 2500,
            "max_bootstrap_tokens": 5000,
            "max_memory_digest_tokens": 1200,
            "max_subagent_result_tokens": 700,
            "max_review_finding_tokens": 120,
        },
        "policy": {
            "estimate_method": "chars_div_4",
            "prefer_progressive_disclosure": True,
            "compress_only_natural_language": True,
            "preserve_code_urls_paths_headings": True,
            "do_not_send_sensitive_files_to_external_models": True,
            "doctor_fails_on_budget_excess": False,
        },
        "commands": {
            "doctor": "python3 .agent/tools/agent_context.py doctor",
            "scan": "python3 .agent/tools/agent_context.py scan --limit 10",
            "suggest": "python3 .agent/tools/agent_context.py suggest",
            "validate_pair": "python3 .agent/tools/agent_context.py validate-pair <original> <compressed>",
        },
    }


def skill_distribution_config(project_name: str, created_at: str) -> dict:
    return {
        "schema": "agent-skill-distribution-v1",
        "project_name": project_name,
        "created_at": created_at,
        "preferred_codex_skill_dir": ".agents/skills",
        "legacy_codex_skill_dir": ".codex/skills",
        "claude_skill_dir": ".claude/skills",
        "sync_script": "scripts/agent_sync_skills.py",
        "policy": {
            "prefer_agents_skills_for_codex": True,
            "preserve_legacy_codex_skills": True,
            "do_not_overwrite_without_force": True,
        },
    }


def capabilities_config(project_name: str, created_at: str, openspec_enabled: bool, claude_enabled: bool) -> dict:
    capabilities = [
        {
            "id": "repo-filesystem",
            "kind": "resource",
            "provider": "local",
            "enabled": True,
            "risk": "medium",
            "owner": "unassigned",
            "description": "Remote repository filesystem is the authoritative state store.",
            "permissions": {"read": True, "write": "bounded", "network": False, "secrets": False},
            "validation": ["python3 scripts/agent_check.py"],
        },
        {
            "id": "git-worktree",
            "kind": "tool",
            "provider": "git",
            "enabled": True,
            "risk": "medium",
            "owner": "unassigned",
            "description": "Inspect branch, commit, and dirty worktree before edits and handoff.",
            "permissions": {"read": True, "write": "bounded", "network": False, "secrets": False},
            "validation": ["git status --short"],
        },
        {
            "id": "agent-spec",
            "kind": "tool",
            "provider": "agent-gov",
            "enabled": openspec_enabled,
            "risk": "low",
            "owner": "unassigned",
            "description": "Embedded specification-driven change planning and task tracking.",
            "permissions": {"read": True, "write": "bounded", "network": False, "secrets": False},
            "validation": ["python3 scripts/agent_spec.py doctor", "python3 scripts/agent_spec.py list --json"],
        },
        {
            "id": "harness-validation",
            "kind": "tool",
            "provider": "local",
            "enabled": True,
            "risk": "medium",
            "owner": "unassigned",
            "description": "Configured build, test, lint, typecheck, and smoke command registry.",
            "permissions": {"read": True, "write": False, "network": "project-defined", "secrets": False},
            "validation": ["python3 scripts/agent_validate.py --list"],
        },
        {
            "id": "workflow-governance",
            "kind": "policy",
            "provider": "local",
            "enabled": True,
            "risk": "medium",
            "owner": "unassigned",
            "description": "Lifecycle gates for spec approval, plan quality, implementation discipline, worktree isolation, TDD, debugging, reviews, and completion evidence.",
            "permissions": {"read": True, "write": False, "network": False, "secrets": False},
            "validation": ["python3 scripts/agent_check.py"],
        },
        {
            "id": "implementation-discipline",
            "kind": "policy",
            "provider": "local",
            "enabled": True,
            "risk": "medium",
            "owner": "unassigned",
            "description": "Simplicity-first and surgical-change rules for assumptions, abstractions, diff scope, and verifiable success criteria.",
            "permissions": {"read": True, "write": False, "network": False, "secrets": False},
            "validation": ["python3 scripts/agent_check.py", "python3 scripts/agent_score.py doctor"],
        },
        {
            "id": "worktree-isolation",
            "kind": "policy",
            "provider": "git",
            "enabled": True,
            "risk": "medium",
            "owner": "unassigned",
            "description": "Preferred isolated git worktree policy with baseline validation and guarded cleanup.",
            "permissions": {"read": True, "write": "bounded", "network": False, "secrets": False},
            "validation": ["git worktree list", "git status --short"],
        },
        {
            "id": "aci-tooling",
            "kind": "tool",
            "provider": "local",
            "enabled": True,
            "risk": "low",
            "owner": "unassigned",
            "description": "Agent-facing bounded file listing, reading, and searching with explicit output limits.",
            "permissions": {"read": True, "write": False, "network": False, "secrets": False},
            "validation": ["python3 scripts/agent_tooling.py doctor"],
        },
        {
            "id": "security-baseline",
            "kind": "tool",
            "provider": "local",
            "enabled": True,
            "risk": "medium",
            "owner": "unassigned",
            "description": "Optional policy-as-code, secret scan, dependency audit, SBOM, and license scan command slots.",
            "permissions": {"read": True, "write": False, "network": "project-defined", "secrets": False},
            "validation": ["python3 scripts/agent_security.py doctor"],
        },
        {
            "id": "governance-score",
            "kind": "tool",
            "provider": "local",
            "enabled": True,
            "risk": "low",
            "owner": "unassigned",
            "description": "Deterministic governance health score and eval dashboard over local project state.",
            "permissions": {"read": True, "write": "bounded", "network": False, "secrets": False},
            "validation": ["python3 scripts/agent_score.py doctor"],
        },
        {
            "id": "decision-records",
            "kind": "resource",
            "provider": "local",
            "enabled": True,
            "risk": "low",
            "owner": "unassigned",
            "description": "ADR, RFC, and incident/postmortem templates for durable decisions and reliability learning.",
            "permissions": {"read": True, "write": "bounded", "network": False, "secrets": False},
            "validation": ["test -d docs/adr && test -d docs/rfcs && test -d docs/incidents"],
        },
        {
            "id": "session-memory",
            "kind": "resource",
            "provider": "local",
            "enabled": True,
            "risk": "medium",
            "owner": "unassigned",
            "description": "Repo-local session continuity and long-term memory summaries.",
            "permissions": {"read": True, "write": "bounded", "network": False, "secrets": False},
            "validation": ["python3 .agent/tools/agent_memory.py doctor"],
        },
        {
            "id": "context-budget",
            "kind": "tool",
            "provider": "local",
            "enabled": True,
            "risk": "low",
            "owner": "unassigned",
            "description": "Local context budget scans and compression safety checks.",
            "permissions": {"read": True, "write": "bounded", "network": False, "secrets": False},
            "validation": ["python3 .agent/tools/agent_context.py doctor"],
        },
        {
            "id": "subagent-orchestration",
            "kind": "policy",
            "provider": "local",
            "enabled": True,
            "risk": "medium",
            "owner": "unassigned",
            "description": "Permission-gated delegated agent roles, boundaries, and snapshot contract.",
            "permissions": {"read": True, "write": False, "network": False, "secrets": False},
            "validation": ["python3 scripts/agent_check.py"],
        },
        {
            "id": "native-hooks",
            "kind": "adapter",
            "provider": "codex-claude",
            "enabled": True,
            "risk": "medium",
            "owner": "unassigned",
            "description": "Advisory native hook projections for bootstrap and checkpoint reminders.",
            "permissions": {"read": True, "write": "bounded", "network": False, "secrets": False},
            "validation": ["python3 .agent/tools/governance_hook.py --event session-start"],
        },
        {
            "id": "claude-native-adapters",
            "kind": "adapter",
            "provider": "claude",
            "enabled": claude_enabled,
            "risk": "medium",
            "owner": "unassigned",
            "description": "Claude settings and subagent projections when Claude support is enabled.",
            "permissions": {"read": True, "write": "bounded", "network": False, "secrets": False},
            "validation": ["python3 scripts/agent_check.py"],
        },
    ]
    return {
        "schema": "agent-capabilities-v1",
        "project_name": project_name,
        "created_at": created_at,
        "policy": {
            "registry_is_advisory": True,
            "confirm_current_state_before_use": True,
            "default_external_network": "deny-unless-user-or-project-allows",
            "record_high_risk_tool_use_in_runlog": True,
            "do_not_store_secrets": True,
        },
        "risk_values": ["low", "medium", "high"],
        "capabilities": capabilities,
        "mcp_servers": [],
        "external_integrations": [],
    }


def tooling_config(project_name: str, created_at: str) -> dict:
    return {
        "schema": "agent-tooling-v1",
        "project_name": project_name,
        "created_at": created_at,
        "policy": {
            "bounded_output": True,
            "explicit_no_result_output": True,
            "path_first_output": True,
            "line_number_output": True,
            "skip_sensitive_paths_by_default": True,
            "do_not_read_binary_files": True,
        },
        "limits": {
            "max_read_lines": 160,
            "max_read_bytes": 200000,
            "max_search_matches": 80,
            "max_search_files": 5000,
            "max_line_chars": 240,
            "max_file_list": 200,
        },
        "ignore_dirs": [".git", ".agent/memory", ".agent/context", "node_modules", "dist", "build", "target", "__pycache__"],
        "commands": {
            "doctor": "python3 scripts/agent_tooling.py doctor",
            "files": "python3 scripts/agent_tooling.py files --glob '<pattern>'",
            "read": "python3 scripts/agent_tooling.py read <path> --start 1 --limit 120",
            "search": "python3 scripts/agent_tooling.py search '<query>' --glob '<pattern>'",
        },
    }


def security_config(project_name: str, created_at: str) -> dict:
    return {
        "schema": "agent-security-v1",
        "project_name": project_name,
        "created_at": created_at,
        "policy": {
            "commands_are_optional": True,
            "prefer_local_scans": True,
            "record_security_runs_in_runlog": True,
            "do_not_store_secrets": True,
            "review_high_risk_findings_before_handoff": True,
        },
        "suites": {
            "policy_as_code": [],
            "secret_scan": [],
            "dependency_audit": [],
            "sbom": [],
            "license_scan": [],
        },
        "local_scans": {
            "sensitive_path_scan": True,
            "sensitive_content_scan": False,
        },
        "commands": {
            "doctor": "python3 scripts/agent_security.py doctor",
            "list": "python3 scripts/agent_security.py list",
            "scan_paths": "python3 scripts/agent_security.py scan-paths",
            "run": "python3 scripts/agent_security.py run <suite>",
        },
    }


def evals_config(project_name: str, created_at: str) -> dict:
    return {
        "schema": "agent-evals-v1",
        "project_name": project_name,
        "created_at": created_at,
        "stores": {
            "latest_score": ".agent/evals/latest.md",
            "runlog": ".agent/runlog.jsonl",
        },
        "policy": {
            "local_deterministic": True,
            "score_is_advisory": True,
            "record_score_runs_in_runlog": True,
            "periodic_review_cadence": "weekly",
            "do_not_read_secret_contents": True,
        },
        "thresholds": {
            "pass": 85,
            "warn": 70,
        },
        "dimensions": {
            "required_paths": {"weight": 18},
            "validation": {"weight": 10},
            "implementation_discipline": {"weight": 8},
            "context_budget": {"weight": 10},
            "session_continuity": {"weight": 10},
            "memory": {"weight": 10},
            "capabilities": {"weight": 10},
            "security": {"weight": 10},
            "knowledge": {"weight": 8},
            "runlog": {"weight": 6},
        },
        "commands": {
            "doctor": "python3 scripts/agent_score.py doctor",
            "score": "python3 scripts/agent_score.py score",
            "write": "python3 scripts/agent_score.py score --write",
            "json": "python3 scripts/agent_score.py score --json",
        },
    }


def escape_toml_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def role_instruction(role: str, purpose: str) -> str:
    return f"""Role: {role}
Purpose: {purpose}

Follow repository governance:
- Read AGENTS.md first when available.
- Respect .agent/subagents.json, .agent/workflow.json, .agent/worktrees.json, .agent/harness.json, and .agent/project-layout.json.
- Keep work inside the assigned read/write boundary.
- Prefer the simplest direct implementation and justify new abstractions or speculative flexibility.
- Keep diffs surgical; do not do unrelated cleanup unless it is part of the assigned task.
- For implementation reviews, confirm spec compliance before code quality.
- Keep final output structured and concise; respect .agent/context.json output budgets.
- Do not claim validation you did not run.
- Start the final report with ===SNAPSHOT=== followed by JSON matching the repository snapshot contract.
"""


def codex_agent_toml(role: str, purpose: str) -> str:
    name = f"governance_{role}"
    description = f"Project governance {role}: {purpose}"
    instructions = role_instruction(role, purpose)
    sandbox = (
        'sandbox_mode = "read-only"\n'
        if role in {"searcher", "explorer", "verifier", "reviewer", "spec_reviewer", "quality_reviewer"}
        else ""
    )
    return (
        f'name = "{name}"\n'
        f'description = "{escape_toml_string(description)}"\n'
        f"{sandbox}"
        'developer_instructions = """\n'
        f"{instructions}"
        '"""\n'
    )


def claude_agent_markdown(role: str, purpose: str) -> str:
    name = f"governance-{role}"
    description = f"Project governance {role}: {purpose}"
    return f"""---
name: {name}
description: {description}
---

{role_instruction(role, purpose)}
"""


def codex_config_toml() -> str:
    return """[features]
codex_hooks = true

[agents]
max_threads = 6
max_depth = 1
job_max_runtime_seconds = 1800
"""


def codex_hooks_json() -> str:
    hook_command = (
        "sh -lc 'root=\"$(git rev-parse --show-toplevel 2>/dev/null || pwd)\"; "
        "while [ ! -f \"$root/.agent/tools/governance_hook.py\" ] && [ \"$root\" != \"/\" ]; "
        "do root=\"$(dirname \"$root\")\"; done; "
        "if [ -f \"$root/.agent/tools/governance_hook.py\" ]; then "
        "python3 \"$root/.agent/tools/governance_hook.py\" --event {event}; "
        "else echo \"governance hook: .agent/tools/governance_hook.py not found\"; fi'"
    )
    data = {
        "hooks": {
            "SessionStart": [
                {
                    "matcher": "startup|resume",
                    "hooks": [
                        {
                            "type": "command",
                            "command": hook_command.format(event="session-start"),
                            "statusMessage": "Loading governance bootstrap",
                            "timeout": 30,
                        }
                    ],
                }
            ],
            "Stop": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": hook_command.format(event="stop"),
                            "statusMessage": "Checking governance handoff",
                            "timeout": 30,
                        }
                    ]
                }
            ],
        }
    }
    return json.dumps(data, indent=2) + "\n"


def claude_settings_json() -> str:
    hook_command = (
        "sh -lc 'root=\"${{CLAUDE_PROJECT_DIR:-$(pwd)}}\"; "
        "while [ ! -f \"$root/.agent/tools/governance_hook.py\" ] && [ \"$root\" != \"/\" ]; "
        "do root=\"$(dirname \"$root\")\"; done; "
        "if [ -f \"$root/.agent/tools/governance_hook.py\" ]; then "
        "python3 \"$root/.agent/tools/governance_hook.py\" --event {event}; "
        "else echo \"governance hook: .agent/tools/governance_hook.py not found\"; fi'"
    )
    data = {
        "hooks": {
            "SessionStart": [
                {
                    "matcher": "startup|resume",
                    "hooks": [
                        {
                            "type": "command",
                            "command": hook_command.format(event="session-start"),
                        }
                    ],
                }
            ],
            "Stop": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": hook_command.format(event="stop"),
                        }
                    ]
                }
            ],
        }
    }
    return json.dumps(data, indent=2) + "\n"


def git_value(root: Path, args: list[str], fallback: str = "unknown") -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError:
        return fallback
    if result.returncode != 0:
        return fallback
    return result.stdout.strip() or fallback


class Writer:
    def __init__(self, root: Path, force: bool, dry_run: bool) -> None:
        self.root = root
        self.force = force
        self.dry_run = dry_run
        self.created: list[str] = []
        self.updated: list[str] = []
        self.skipped: list[str] = []

    def write(self, relative: str, content: str, executable: bool = False) -> None:
        path = self.root / relative
        exists = path.exists()
        if exists and not self.force:
            self.skipped.append(relative)
            return
        if not self.dry_run:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            if executable:
                path.chmod(path.stat().st_mode | 0o111)
        (self.updated if exists else self.created).append(relative)

    def copy(self, source: Path, relative: str, executable: bool = False) -> None:
        path = self.root / relative
        exists = path.exists()
        if exists and not self.force:
            self.skipped.append(relative)
            return
        if not self.dry_run:
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, path)
            if executable:
                path.chmod(path.stat().st_mode | 0o111)
        (self.updated if exists else self.created).append(relative)


def ensure_json(path: Path, default: dict, writer: Writer, relative: str) -> None:
    if path.exists() and not writer.force:
        writer.skipped.append(relative)
        return
    writer.write(relative, json.dumps(default, indent=2) + "\n")


def spec_enabled(args: argparse.Namespace) -> bool:
    return args.spec_mode == "embedded"


def build_values(root: Path, args: argparse.Namespace) -> dict[str, str]:
    project_name = args.project_name or root.name
    tech_stack = parse_csv(args.tech_stack)
    dirs = layout_dirs(args.layout, parse_csv(args.dir))
    enabled = spec_enabled(args)
    return {
        "project_name": project_name,
        "tech_stack": ", ".join(tech_stack) if tech_stack else "unspecified",
        "layout_name": args.layout,
        "layout_dirs": "\n".join(f"- `{path}/`" for path in dirs),
        "client_surface": args.client_surface,
        "remote_kind": args.remote_kind,
        "workspace_path": str(root.resolve()),
        "created_at": utc_now(),
        "openspec_enabled_json": "true" if enabled else "false",
        "claude_enabled_json": "false" if args.no_claude else "true",
        "spec_source": "none" if not enabled else "agent-gov-spec",
        "spec_management_rule": (
            "Use project docs and `.agent/sessions/` for planning context because the embedded spec layer is disabled."
            if not enabled
            else "Use agent-gov's embedded spec layer for non-trivial change planning and task tracking."
        ),
        "spec_workflow_step": (
            "Check documented planning context before substantial changes."
            if not enabled
            else "Check embedded spec context with `python3 scripts/agent_spec.py list --json` before substantial changes."
        ),
        "git_branch": git_value(root, ["branch", "--show-current"]),
        "git_commit": git_value(root, ["rev-parse", "--short", "HEAD"]),
        "openspec_change": "none",
        "session_id": "template",
        "goal": "Start a durable agent development session.",
    }


def init_project(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    if not root.exists():
        if args.create_root and not args.dry_run:
            root.mkdir(parents=True, exist_ok=True)
        elif not args.create_root:
            print(f"error: repository root does not exist: {root}", file=sys.stderr)
            return 2

    if args.remote_kind not in REMOTE_KINDS:
        print(f"error: --remote-kind must be one of {', '.join(sorted(REMOTE_KINDS))}", file=sys.stderr)
        return 2
    if args.layout not in LAYOUTS:
        print(f"error: --layout must be one of {', '.join(sorted(LAYOUTS))}", file=sys.stderr)
        return 2
    if args.spec_mode not in SPEC_MODES:
        print(f"error: --spec-mode must be one of {', '.join(sorted(SPEC_MODES))}", file=sys.stderr)
        return 2
    if args.install_openspec != "ignored" or args.openspec_package_manager or args.openspec_tools:
        print("note: external OpenSpec CLI options are ignored; agent-gov uses its embedded spec layer")
    if args.no_openspec:
        print("note: --no-openspec is ignored; embedded spec management is part of agent-gov")

    writer = Writer(root, args.force, args.dry_run)
    values = build_values(root, args)
    tech_stack = parse_csv(args.tech_stack)
    dirs = layout_dirs(args.layout, parse_csv(args.dir))
    project_name = args.project_name or root.name
    openspec_enabled = spec_enabled(args)
    claude_enabled = not args.no_claude

    if openspec_enabled:
        writer.write("openspec/config.yaml", render(template("openspec-config.yaml.tmpl"), values))
        writer.write("openspec/project.md", render(template("openspec-project.md.tmpl"), values))
        writer.write("openspec/changes/.gitkeep", "")
        writer.write("openspec/changes/archive/.gitkeep", "")
        writer.write("openspec/specs/.gitkeep", "")

    writer.write("AGENTS.md", render(template("AGENTS.md.tmpl"), values))
    if claude_enabled:
        writer.write("CLAUDE.md", render(template("CLAUDE.md.tmpl"), values))

    writer.write(".agent/config.json", render(template("agent-config.json.tmpl"), values))
    if openspec_enabled:
        writer.write(".agent/spec.json", json.dumps(spec_config(project_name, values["created_at"]), indent=2) + "\n")
    writer.write(
        ".agent/harness.json",
        json.dumps(
            harness_config(project_name, values["created_at"], tech_stack, dirs, openspec_enabled, claude_enabled),
            indent=2,
        )
        + "\n",
    )
    writer.write(
        ".agent/project-layout.json",
        json.dumps(project_layout_config(project_name, args.layout, tech_stack, dirs), indent=2) + "\n",
    )
    writer.write(
        ".agent/workflow.json",
        json.dumps(workflow_config(project_name, values["created_at"], openspec_enabled), indent=2) + "\n",
    )
    writer.write(
        ".agent/worktrees.json",
        json.dumps(worktree_config(project_name, values["created_at"]), indent=2) + "\n",
    )
    writer.write(
        ".agent/subagents.json",
        json.dumps(subagent_config(project_name, values["created_at"], claude_enabled), indent=2) + "\n",
    )
    writer.write(".agent/hooks.json", json.dumps(hooks_config(project_name, values["created_at"]), indent=2) + "\n")
    writer.write(
        ".agent/knowledge.json",
        json.dumps(knowledge_config(project_name, values["created_at"]), indent=2) + "\n",
    )
    writer.write(
        ".agent/memory.json",
        json.dumps(memory_config(project_name, values["created_at"]), indent=2) + "\n",
    )
    writer.write(
        ".agent/context.json",
        json.dumps(context_budget_config(project_name, values["created_at"]), indent=2) + "\n",
    )
    writer.write(
        ".agent/capabilities.json",
        json.dumps(
            capabilities_config(project_name, values["created_at"], openspec_enabled, claude_enabled),
            indent=2,
        )
        + "\n",
    )
    writer.write(
        ".agent/tooling.json",
        json.dumps(tooling_config(project_name, values["created_at"]), indent=2) + "\n",
    )
    writer.write(
        ".agent/security.json",
        json.dumps(security_config(project_name, values["created_at"]), indent=2) + "\n",
    )
    writer.write(
        ".agent/evals.json",
        json.dumps(evals_config(project_name, values["created_at"]), indent=2) + "\n",
    )
    writer.write(
        ".agent/skill-distribution.json",
        json.dumps(skill_distribution_config(project_name, values["created_at"]), indent=2) + "\n",
    )
    writer.write(".agent/evals/latest.md", template("quality-score.md.tmpl"))
    writer.write(".agent/runlog.jsonl", "")
    writer.write(".agent/memory/events.jsonl", "")
    writer.write(".agent/memory/latest.md", template("memory-latest.md.tmpl"))
    writer.write(".agent/memory/summaries/.gitkeep", "")
    writer.write(".agent/context/stats.jsonl", "")
    writer.write(".agent/context/latest.md", template("context-summary.md.tmpl"))
    writer.write(".agent/sessions/index.json", template("session-index.json.tmpl"))
    writer.write(".agent/sessions/active.md", template("active.md.tmpl"))
    writer.write(".agent/sessions/bootstrap.md", template("bootstrap.md.tmpl"))

    for name in (
        "session.md.tmpl",
        "handoff.md.tmpl",
        "context.md.tmpl",
        "decisions.md.tmpl",
        "changes.md.tmpl",
        "validation.md.tmpl",
        "resume-prompt.md.tmpl",
        "artifacts.json.tmpl",
        "project-review.md.tmpl",
        "project-fix-log.md.tmpl",
        "implementation-plan.md.tmpl",
        "debugging-record.md.tmpl",
        "subagent-task.md.tmpl",
        "memory-summary.md.tmpl",
        "memory-latest.md.tmpl",
        "context-summary.md.tmpl",
        "adr.md.tmpl",
        "rfc.md.tmpl",
        "postmortem.md.tmpl",
        "quality-score.md.tmpl",
    ):
        writer.write(f".agent/templates/{name}", template(name))

    writer.copy(skill_dir() / "scripts" / "agent_session.py", ".agent/tools/agent_session.py", executable=True)
    writer.write(".agent/tools/agent_memory.py", template("agent-memory.py.tmpl"), executable=True)
    writer.write(".agent/tools/agent_context.py", template("agent-context.py.tmpl"), executable=True)
    writer.write(".agent/tools/governance_hook.py", template("governance-hook.py.tmpl"), executable=True)
    writer.write(".codex/config.toml", codex_config_toml())
    writer.write(".codex/hooks.json", codex_hooks_json())
    for role, spec in subagent_config(project_name, values["created_at"], claude_enabled)["roles"].items():
        writer.write(f".codex/agents/governance-{role}.toml", codex_agent_toml(role, spec["purpose"]))
        if claude_enabled:
            writer.write(f".claude/agents/governance-{role}.md", claude_agent_markdown(role, spec["purpose"]))
    if claude_enabled:
        writer.write(".claude/settings.json", claude_settings_json())
    writer.write("scripts/agent_check.py", template("agent-check.py.tmpl"), executable=True)
    writer.write("scripts/agent_spec.py", template("agent-spec.py.tmpl"), executable=True)
    writer.write("scripts/agent_validate.py", template("agent-validate.py.tmpl"), executable=True)
    writer.write("scripts/agent_knowledge.py", template("agent-knowledge.py.tmpl"), executable=True)
    writer.write("scripts/agent_invariants.py", template("agent-invariants.py.tmpl"), executable=True)
    writer.write("scripts/agent_capabilities.py", template("agent-capabilities.py.tmpl"), executable=True)
    writer.write("scripts/agent_runlog.py", template("agent-runlog.py.tmpl"), executable=True)
    writer.write("scripts/agent_tooling.py", template("agent-tooling.py.tmpl"), executable=True)
    writer.write("scripts/agent_security.py", template("agent-security.py.tmpl"), executable=True)
    writer.write("scripts/agent_score.py", template("agent-score.py.tmpl"), executable=True)
    writer.write("scripts/agent_sync_skills.py", template("agent-sync-skills.py.tmpl"), executable=True)

    writer.write("docs/index.md", render(template("docs-index.md.tmpl"), values))
    writer.write("docs/ARCHITECTURE.md", render(template("docs-architecture.md.tmpl"), values))
    writer.write("docs/QUALITY.md", render(template("docs-quality.md.tmpl"), values))
    writer.write("docs/RELIABILITY.md", render(template("docs-reliability.md.tmpl"), values))
    writer.write("docs/SECURITY.md", render(template("docs-security.md.tmpl"), values))
    writer.write("docs/TOOLING.md", render(template("docs-tooling.md.tmpl"), values))
    writer.write("docs/QUALITY_SCORE.md", render(template("docs-quality-score.md.tmpl"), values))
    writer.write("docs/tech-debt.md", render(template("docs-tech-debt.md.tmpl"), values))
    writer.write("docs/adr/README.md", render(template("docs-adr-index.md.tmpl"), values))
    writer.write("docs/rfcs/README.md", render(template("docs-rfc-index.md.tmpl"), values))
    writer.write("docs/incidents/README.md", render(template("docs-incidents-index.md.tmpl"), values))

    if not args.no_create_layout:
        for directory in dirs:
            writer.write(f"{directory.rstrip('/')}/.gitkeep", "")

    if not args.no_makefile:
        writer.write("Makefile", template("Makefile.tmpl"))

    print(f"project root: {root}")
    for label, items in (("created", writer.created), ("updated", writer.updated), ("skipped", writer.skipped)):
        if items:
            print(f"{label}:")
            for item in items:
                print(f"  {item}")

    if writer.skipped:
        print("note: skipped existing files; rerun with --force only if overwriting is intended")

    if not args.dry_run:
        check = root / "scripts" / "agent_check.py"
        if check.exists():
            print("next: python3 scripts/agent_check.py")
            if openspec_enabled:
                print("next: python3 scripts/agent_spec.py doctor")
            print("next: python3 scripts/agent_validate.py --list")
            print("next: python3 scripts/agent_capabilities.py doctor")
            print("next: python3 scripts/agent_tooling.py doctor")
            print("next: python3 scripts/agent_security.py doctor")
            print("next: python3 scripts/agent_score.py score --write")
        session_tool = root / ".agent/tools/agent_session.py"
        if session_tool.exists():
            print("next: python3 .agent/tools/agent_session.py start <name> --goal \"<goal>\"")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".", help="Repository root to initialize")
    parser.add_argument("--project-name")
    parser.add_argument("--tech-stack", action="append", default=[], help="Technology stack, repeatable or comma-separated (for example: python,typescript)")
    parser.add_argument("--layout", default="minimal", choices=sorted(LAYOUTS), help="Fixed project directory layout")
    parser.add_argument("--dir", action="append", default=[], help="Extra required directory, repeatable or comma-separated")
    parser.add_argument("--client-surface", default="vscode-codex-extension")
    parser.add_argument("--remote-kind", default="unknown")
    parser.add_argument(
        "--spec-mode",
        choices=sorted(SPEC_MODES),
        default="embedded",
        help="Specification layer mode. Only embedded agent-gov spec management is supported.",
    )
    parser.add_argument(
        "--install-openspec",
        choices=["auto", "always", "never", "ignored"],
        default="ignored",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--openspec-package-manager",
        default="",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--openspec-tools",
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--create-root", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-claude", action="store_true")
    parser.add_argument("--no-openspec", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--no-makefile", action="store_true")
    parser.add_argument("--no-create-layout", action="store_true")
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    return init_project(args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
