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
GOVERNANCE_PROFILES = {"core", "standard", "full"}
PROFILE_ORDER = {"core": 0, "standard": 1, "full": 2}
PROJECT_TARGETS = {"agent", "mcp-server", "hybrid", "library"}
RUNTIME_ADAPTERS = {
    "strands",
    "pydantic-ai",
    "langgraph",
    "openai-agents",
    "mcp-server",
    "mcp-sdk-python",
    "mcp-sdk-typescript",
    "fastmcp",
    "custom",
    "none",
}
MODEL_ACCESS_STRATEGIES = {"openai-compatible-first", "litellm-gateway", "provider-sdk", "local-only", "custom"}
SECRET_REF_PREFIXES = ("env:", "file-ref:", "vault:", "proxy:", "op:", "keychain:")
LAYOUTS = {
    "existing": [],
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
APPEND_ONLY_PATHS = {
    ".agent/runlog.jsonl",
    ".agent/sessions/events.jsonl",
    ".agent/memory/events.jsonl",
    ".agent/context/stats.jsonl",
}
SESSION_OFFLOAD_TEMPLATES = (
    "grounding.md.tmpl",
    "offload.jsonl.tmpl",
    "offload-index.md.tmpl",
    "task-map.mmd.tmpl",
    "refs/.gitkeep",
)
BLANK_PROJECT_IGNORED_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".DS_Store",
    "Thumbs.db",
    ".idea",
    ".vscode",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def existing_created_at(root: Path) -> str | None:
    for relative in (".agent/config.json", ".agent/manifest.json", ".agent/harness.json"):
        path = root / relative
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        created_at = data.get("created_at")
        if isinstance(created_at, str) and created_at.strip():
            return created_at
    return None


def ignored_blank_project_artifact(root: Path, path: Path) -> bool:
    if path.name in BLANK_PROJECT_IGNORED_NAMES:
        return True
    try:
        relative = path.relative_to(root).as_posix()
    except ValueError:
        return False
    return relative == ".codex/skills/agent-gov" or relative.startswith(".codex/skills/agent-gov/")


def has_meaningful_project_content(root: Path, path: Path) -> bool:
    if ignored_blank_project_artifact(root, path):
        return False
    if path.is_dir():
        try:
            return any(has_meaningful_project_content(root, child) for child in path.iterdir())
        except OSError:
            return True
    return True


def is_blank_project_root(root: Path) -> bool:
    if not root.exists():
        return True
    if not root.is_dir():
        return False
    try:
        return not any(has_meaningful_project_content(root, child) for child in root.iterdir())
    except OSError:
        return False


def default_governance_profile(root: Path) -> str:
    return "full" if is_blank_project_root(root) else "standard"


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


def load_architecture_intake(path_value: str) -> dict:
    if not path_value:
        return {}
    path = Path(path_value).expanduser()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"cannot read --architecture-intake {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"--architecture-intake must be valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("--architecture-intake must contain a JSON object")
    return data


def bool_from_intake(intake: dict, key: str, default: bool) -> bool:
    value = intake.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def list_from_intake(intake: dict, key: str, default: list[str] | None = None) -> list[str]:
    value = intake.get(key, default or [])
    if isinstance(value, str):
        return parse_csv([value])
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            text = str(item).strip()
            if text and text not in result:
                result.append(text)
        return result
    return list(default or [])


def normalize_provider_id(value: str) -> str:
    lowered = value.strip().lower().replace("_", "-")
    aliases = {
        "dashscope": "qwen",
        "alibaba": "qwen",
        "aliyun": "qwen",
        "deepseek-api": "deepseek",
        "openai-compatible": "openai",
        "local": "local-openai-compatible",
        "ollama": "local-openai-compatible",
        "vllm": "local-openai-compatible",
        "sglang": "local-openai-compatible",
        "litellm": "litellm-gateway",
        "litellm-gateway": "litellm-gateway",
    }
    return aliases.get(lowered, lowered)


def normalize_project_target(value: str) -> str:
    lowered = value.strip().lower().replace("_", "-")
    aliases = {
        "": "agent",
        "product-agent": "agent",
        "llm-agent": "agent",
        "assistant": "agent",
        "mcp": "mcp-server",
        "mcp-server": "mcp-server",
        "mcp server": "mcp-server",
        "model-context-protocol": "mcp-server",
        "model-context-protocol-server": "mcp-server",
        "agent-mcp": "hybrid",
        "mcp-agent": "hybrid",
        "agent-plus-mcp": "hybrid",
        "agent+mcp": "hybrid",
        "hybrid": "hybrid",
        "lib": "library",
        "package": "library",
        "library": "library",
    }
    return aliases.get(lowered, lowered if lowered in PROJECT_TARGETS else "agent")


def architecture_style_for_target(project_target: str, skill_first: bool) -> str:
    if not skill_first:
        return "project-defined"
    if project_target == "mcp-server":
        return "skill-first-mcp"
    if project_target == "hybrid":
        return "skill-first-hybrid"
    if project_target == "library":
        return "skill-first-library"
    return "skill-first"


def default_adapter_for_target(project_target: str, skill_first: bool) -> str:
    if project_target == "mcp-server":
        return "mcp-server"
    if project_target == "library":
        return "none"
    return "strands" if skill_first else "custom"


def mcp_server_intake_config(intake: dict, project_target: str) -> dict:
    enabled = project_target in {"mcp-server", "hybrid"} or bool_from_intake(intake, "mcp_server_enabled", False)
    capability_types = list_from_intake(intake, "mcp_capability_types", ["tools"] if enabled else [])
    transports = list_from_intake(intake, "mcp_transports", ["stdio"] if enabled else [])
    return {
        "enabled": enabled,
        "capability_types": capability_types,
        "transports": transports,
        "host_client_boundary": str(
            intake.get("mcp_host_client_boundary", "MCP clients own model context; this server exposes governed capabilities only.")
        ).strip()
        or "MCP clients own model context; this server exposes governed capabilities only.",
        "contract_manifest": str(intake.get("mcp_contract_manifest", ".agent/mcp-server.json")).strip() or ".agent/mcp-server.json",
        "policy": {
            "tool_schemas_required": True,
            "resource_schemas_required": True,
            "prompt_contracts_required": True,
            "raw_credentials_forbidden": True,
            "credential_material": "references-only",
            "destructive_tools_require_human_approval": True,
            "resource_catalog_resolution_required": True,
            "runtime_dependencies_are_application_owned": True,
        },
    }


def architecture_intake_config(intake: dict, *, has_intake: bool) -> dict:
    project_target = normalize_project_target(
        str(
            intake.get(
                "project_target",
                intake.get("product_target", intake.get("runtime_target", intake.get("deliverable_type", "agent"))),
            )
        )
    )
    has_model_provider_intake = "expected_model_providers" in intake or "model_providers" in intake
    default_models = [] if project_target in {"mcp-server", "library"} else ["qwen", "deepseek"]
    model_key = "expected_model_providers" if "expected_model_providers" in intake else "model_providers"
    expected_models = [normalize_provider_id(item) for item in list_from_intake(intake, model_key, default_models)]
    if not expected_models and project_target in {"agent", "hybrid"}:
        expected_models = ["qwen", "deepseek"]
    language_preference = list_from_intake(intake, "language_preference", [])
    workflow_complexity = str(intake.get("workflow_complexity", "moderate")).strip().lower() or "moderate"
    skill_first = bool_from_intake(intake, "skills_are_first_class", True)
    structured_output = bool_from_intake(intake, "structured_output_required", True)
    long_running_workflows = bool_from_intake(intake, "long_running_workflows", workflow_complexity in {"high", "complex", "graph"})
    models_required = bool_from_intake(
        intake,
        "model_profiles_required",
        project_target in {"agent", "hybrid"},
    )
    model_strategy = str(intake.get("model_access_strategy", "")).strip() or (
        "openai-compatible-first" if any(provider in {"qwen", "deepseek", "openai", "local-openai-compatible"} for provider in expected_models) else "custom"
    )
    if model_strategy not in MODEL_ACCESS_STRATEGIES:
        model_strategy = "custom"
    default_adapter = str(intake.get("default_runtime_adapter", "")).strip() or default_adapter_for_target(project_target, skill_first)
    if default_adapter not in RUNTIME_ADAPTERS:
        default_adapter = "custom"
    optional_adapters = list_from_intake(intake, "optional_runtime_adapters", [])
    if structured_output and project_target in {"agent", "hybrid"} and "pydantic-ai" not in optional_adapters:
        optional_adapters.append("pydantic-ai")
    if long_running_workflows and "langgraph" not in optional_adapters:
        optional_adapters.append("langgraph")
    if project_target in {"mcp-server", "hybrid"} and "mcp-server" not in optional_adapters and default_adapter != "mcp-server":
        optional_adapters.append("mcp-server")
    optional_adapters = [adapter if adapter in RUNTIME_ADAPTERS else "custom" for adapter in optional_adapters]
    selected_model_profiles = []
    for provider in expected_models:
        if provider in {"qwen", "deepseek", "openai", "local-openai-compatible"} and provider not in selected_model_profiles:
            selected_model_profiles.append(provider)
    if "litellm-gateway" in expected_models and "litellm-gateway" not in selected_model_profiles:
        selected_model_profiles.append("litellm-gateway")
    if models_required and not selected_model_profiles and not has_model_provider_intake:
        selected_model_profiles = ["qwen", "deepseek"]
    explicit_confirmed = bool_from_intake(intake, "architecture_confirmed", False)
    if str(intake.get("selection_status", "")).strip() == "confirmed":
        explicit_confirmed = True
    selection_status = str(intake.get("selection_status", "")).strip()
    if selection_status not in {"confirmed", "needs-confirmation"}:
        selection_status = "confirmed" if explicit_confirmed else "needs-confirmation"
    return {
        "schema": "agent-architecture-intake-v1",
        "source": "structured-intake" if has_intake else "default-conservative",
        "project_target": project_target,
        "project_purpose": str(intake.get("project_purpose", "agent application")).strip() or "agent application",
        "skills_are_first_class": skill_first,
        "architecture_style": architecture_style_for_target(project_target, skill_first),
        "expected_model_providers": expected_models,
        "language_preference": language_preference,
        "workflow_complexity": workflow_complexity,
        "structured_output_required": structured_output,
        "tool_calling_required": bool_from_intake(intake, "tool_calling_required", True),
        "long_running_workflows": long_running_workflows,
        "deployment_surface": str(intake.get("deployment_surface", "unspecified")).strip() or "unspecified",
        "data_sensitivity": str(intake.get("data_sensitivity", "project-defined")).strip() or "project-defined",
        "selection_status": selection_status if has_intake else "needs-confirmation",
        "default_runtime_adapter": default_adapter,
        "optional_runtime_adapters": optional_adapters,
        "model_access_strategy": model_strategy,
        "model_profiles_required": models_required,
        "selected_model_profiles": selected_model_profiles,
        "mcp_server": mcp_server_intake_config(intake, project_target),
    }


def clean_layout_dir(value: str) -> str:
    raw = value.strip().replace("\\", "/").strip("/")
    if not raw:
        return ""
    if len(raw) >= 2 and raw[1] == ":":
        raise ValueError(f"--dir must be a repository-relative path, not a drive path: {value}")
    parts: list[str] = []
    for part in raw.split("/"):
        if not part:
            continue
        if part in {".", ".."}:
            raise ValueError(f"--dir must not contain . or .. path segments: {value}")
        parts.append(part)
    return "/".join(parts)


def layout_dirs(layout: str, extra_dirs: list[str]) -> list[str]:
    dirs = list(LAYOUTS.get(layout, LAYOUTS["minimal"]))
    for path in extra_dirs:
        clean = clean_layout_dir(path)
        if clean and clean not in dirs:
            dirs.append(clean)
    return dirs


def profile_at_least(profile: str, level: str) -> bool:
    return PROFILE_ORDER[profile] >= PROFILE_ORDER[level]


def config_path_pointers(governance_profile: str, openspec_enabled: bool, claude_enabled: bool) -> dict[str, str]:
    paths = {
        "session_root": ".agent/sessions",
        "governance_manifest": ".agent/manifest.json",
        "harness_config": ".agent/harness.json",
        "project_layout": ".agent/project-layout.json",
        "evals_config": ".agent/evals.json",
        "governance_score": ".agent/evals/latest.md",
        "runlog": ".agent/runlog.jsonl",
    }
    if openspec_enabled:
        paths["spec_config"] = ".agent/spec.json"
        paths["spec_root"] = "openspec"
    if profile_at_least(governance_profile, "standard"):
        paths.update(
            {
                "workflow_config": ".agent/workflow.json",
                "workflow_profiles": ".agent/workflow-profiles.json",
                "loop_engineering": ".agent/loop-engineering.json",
                "risk_zones": ".agent/risk-zones.json",
                "review_policy": ".agent/review-policy.json",
                "worktree_policy": ".agent/worktrees.json",
                "role_contracts": ".agent/role-contracts.json",
                "task_board": ".agent/task-board.json",
                "knowledge_manifest": ".agent/knowledge.json",
                "dev_map": ".agent/dev-map.json",
                "skill_hygiene": ".agent/skill-hygiene.json",
                "project_skills": ".agent/project-skills.json",
                "skill_runtime": ".agent/skill-runtime.json",
                "runtime_policy": ".agent/runtime-policy.json",
                "model_profiles": ".agent/model-profiles.json",
                "agent_runtime": ".agent/agent-runtime.json",
                "memory_config": ".agent/memory.json",
                "context_config": ".agent/context.json",
                "security_config": ".agent/security.json",
                "capabilities_config": ".agent/capabilities.json",
                "resources_config": ".agent/resources.json",
                "mechanical_checks": ".agent/mechanical-checks.json",
                "baselines": ".agent/baselines.json",
                "harness_evolution": ".agent/harness-evolution.json",
                "mcp_policy": ".agent/mcp-policy.json",
                "governance_gc": ".agent/governance-gc.json",
            }
        )
    if profile_at_least(governance_profile, "full"):
        paths.update(
            {
                "subagent_config": ".agent/subagents.json",
                "hooks_config": ".agent/hooks.json",
                "tooling_config": ".agent/tooling.json",
                "mcp_policy": ".agent/mcp-policy.json",
                "skill_distribution": ".agent/skill-distribution.json",
                "codex_config": ".codex/config.toml",
                "codex_hooks": ".codex/hooks.json",
            }
        )
        if claude_enabled:
            paths["claude_settings"] = ".claude/settings.json"
    return paths


def config_paths_json(governance_profile: str, openspec_enabled: bool, claude_enabled: bool) -> str:
    return json.dumps(config_path_pointers(governance_profile, openspec_enabled, claude_enabled), indent=2)


def harness_config(
    project_name: str,
    created_at: str,
    tech_stack: list[str],
    dirs: list[str],
    openspec_enabled: bool,
    claude_enabled: bool,
    governance_profile: str,
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
        ".agent/manifest.json",
        ".agent/harness.json",
        ".agent/project-layout.json",
        ".agent/evals.json",
        ".agent/evals/latest.md",
        ".agent/runlog.jsonl",
        ".agent/sessions/index.json",
        ".agent/sessions/events.jsonl",
        ".agent/sessions/active.md",
        ".agent/sessions/bootstrap.md",
        ".agent/tools/agent_session.py",
        "scripts/agent_check.py",
        "scripts/agent_spec.py",
        "scripts/agent_validate.py",
        "scripts/agent_runlog.py",
        "scripts/agent_score.py",
        "scripts/agent_migrate.py",
        "docs/index.md",
        "docs/QUALITY.md",
        *dirs,
    ]
    required_paths.extend(
        [
            ".agent/templates/session.md.tmpl",
            ".agent/templates/handoff.md.tmpl",
            ".agent/templates/context.md.tmpl",
            ".agent/templates/decisions.md.tmpl",
            ".agent/templates/changes.md.tmpl",
            ".agent/templates/validation.md.tmpl",
            ".agent/templates/resume-prompt.md.tmpl",
            ".agent/templates/artifacts.json.tmpl",
            ".agent/templates/grounding.md.tmpl",
            ".agent/templates/offload.jsonl.tmpl",
            ".agent/templates/offload-index.md.tmpl",
            ".agent/templates/task-map.mmd.tmpl",
            ".agent/templates/refs/.gitkeep",
        ]
    )
    if profile_at_least(governance_profile, "standard"):
        if "python3 scripts/agent_resources.py doctor" not in validation["test"]:
            validation["test"].append("python3 scripts/agent_resources.py doctor")
        if "python3 scripts/agent_runtime.py doctor" not in validation["test"]:
            validation["test"].append("python3 scripts/agent_runtime.py doctor")
        if "python3 scripts/agent_resources.py list --json" not in validation["smoke"]:
            validation["smoke"].append("python3 scripts/agent_resources.py list --json")
        required_paths.extend(
            [
                ".agent/workflow.json",
                ".agent/workflow-profiles.json",
                ".agent/loop-engineering.json",
                ".agent/risk-zones.json",
                ".agent/review-policy.json",
                ".agent/worktrees.json",
                ".agent/role-contracts.json",
                ".agent/task-board.json",
                ".agent/knowledge.json",
                ".agent/dev-map.json",
                ".agent/skill-hygiene.json",
                ".agent/project-skills.json",
                ".agent/skill-runtime.json",
                ".agent/runtime-policy.json",
                ".agent/model-profiles.json",
                ".agent/agent-runtime.json",
                ".agent/memory.json",
                ".agent/context.json",
                ".agent/security.json",
                ".agent/resources.json",
                ".agent/capabilities.json",
                ".agent/mechanical-checks.json",
                ".agent/baselines.json",
                ".agent/harness-evolution.json",
                ".agent/mcp-policy.json",
                ".agent/governance-gc.json",
                ".agent/baselines/.gitkeep",
                ".agent/memory/events.jsonl",
                ".agent/memory/latest.md",
                ".agent/memory/summaries/.gitkeep",
                ".agent/context/stats.jsonl",
                ".agent/context/latest.md",
                ".agent/intake/.gitkeep",
                ".agent/templates/project-review.md.tmpl",
                ".agent/templates/project-fix-log.md.tmpl",
                ".agent/templates/intake-packet.md.tmpl",
                ".agent/templates/resource-secrets.local.env.tmpl",
                ".agent/templates/implementation-plan.md.tmpl",
                ".agent/templates/debugging-record.md.tmpl",
                ".agent/templates/features/01_REQUIREMENT_ANALYSIS.md.tmpl",
                ".agent/templates/features/02_SOLUTION_DESIGN.md.tmpl",
                ".agent/templates/features/03_GATE_REVIEW.md.tmpl",
                ".agent/templates/features/04_DEVELOPMENT.md.tmpl",
                ".agent/templates/features/05_CODE_REVIEW.md.tmpl",
                ".agent/templates/features/06_TEST_REPORT.md.tmpl",
                ".agent/templates/features/07_DELIVERY_SUMMARY.md.tmpl",
                ".agent/templates/memory-summary.md.tmpl",
                ".agent/templates/memory-latest.md.tmpl",
                ".agent/templates/context-summary.md.tmpl",
                ".agent/templates/adr.md.tmpl",
                ".agent/templates/rfc.md.tmpl",
                ".agent/templates/postmortem.md.tmpl",
                ".agent/templates/quality-score.md.tmpl",
                ".agent/tools/agent_memory.py",
                ".agent/tools/agent_context.py",
                "scripts/agent_knowledge.py",
                "scripts/agent_invariants.py",
                "scripts/agent_capabilities.py",
                "scripts/agent_skill_hygiene.py",
                "scripts/agent_project_skills.py",
                "scripts/agent_runtime.py",
                "scripts/agent_task.py",
                "scripts/agent_verify.py",
                "scripts/agent_gc.py",
                "scripts/agent_security.py",
                "scripts/agent_resources.py",
                "docs/ARCHITECTURE.md",
                "docs/RELIABILITY.md",
                "docs/QUALITY_SCORE.md",
                "docs/AI_CODING_GLOSSARY.md",
                "docs/DOMAIN_GLOSSARY.md",
                "docs/DEV_MAP.md",
                "docs/LOOP_ENGINEERING.md",
                "docs/RESOURCES.md",
                "docs/AGENT_RUNTIME_ARCHITECTURE.md",
                "docs/SKILL_RUNTIME.md",
                "docs/features/INDEX.md",
                "docs/features/.gitkeep",
                "docs/tech-debt.md",
                "docs/adr/README.md",
                "docs/rfcs/README.md",
                "docs/incidents/README.md",
            ]
        )
    if profile_at_least(governance_profile, "full"):
        required_paths.extend(
            [
                ".agent/subagents.json",
                ".agent/hooks.json",
                ".agent/tooling.json",
                ".agent/skill-distribution.json",
                ".agent/templates/subagent-task.md.tmpl",
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
                "scripts/agent_tooling.py",
                "scripts/agent_sync_skills.py",
                "docs/TOOLING.md",
                "docs/SECURITY.md",
            ]
        )
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
    if claude_enabled and profile_at_least(governance_profile, "full"):
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

    observability = {
        "logs": [],
        "health_checks": [],
        "runlog": ".agent/runlog.jsonl",
        "governance_score": ".agent/evals/latest.md",
    }
    if profile_at_least(governance_profile, "standard"):
        observability["capability_registry"] = ".agent/capabilities.json"
        observability["resource_catalog"] = ".agent/resources.json"
        observability["runtime_architecture"] = ".agent/agent-runtime.json"
        observability["skill_runtime"] = ".agent/skill-runtime.json"
        observability["loop_engineering"] = ".agent/loop-engineering.json"

    required_docs = ["docs/QUALITY.md"]
    if profile_at_least(governance_profile, "standard"):
        required_docs.extend(
            [
                "docs/ARCHITECTURE.md",
                "docs/RELIABILITY.md",
                "docs/QUALITY_SCORE.md",
                "docs/AI_CODING_GLOSSARY.md",
                "docs/DOMAIN_GLOSSARY.md",
                "docs/DEV_MAP.md",
                "docs/LOOP_ENGINEERING.md",
                "docs/RESOURCES.md",
                "docs/AGENT_RUNTIME_ARCHITECTURE.md",
                "docs/SKILL_RUNTIME.md",
                "docs/features/INDEX.md",
                "docs/tech-debt.md",
                "docs/adr/README.md",
                "docs/rfcs/README.md",
                "docs/incidents/README.md",
            ]
        )
    if profile_at_least(governance_profile, "full"):
        required_docs.extend(["docs/SECURITY.md", "docs/TOOLING.md"])
    knowledge = {
        "index": "docs/index.md",
        "required_docs": required_docs,
    }
    if profile_at_least(governance_profile, "standard"):
        knowledge["manifest"] = ".agent/knowledge.json"

    return {
        "schema": "agent-harness-v1",
        "project_name": project_name,
        "created_at": created_at,
        "governance_profile": governance_profile,
        "tech_stack": tech_stack,
        "validation": validation,
        "security": {
            "policy_as_code": [],
            "secret_scan": [],
            "dependency_audit": [],
            "sbom": [],
            "license_scan": [],
        },
        "observability": observability,
        "knowledge": knowledge,
        "invariants": {
            "max_doc_age_days": None,
            "forbidden_paths": [],
            "required_paths": required_paths,
            "architecture_boundaries": [],
        },
    }


def project_layout_config(project_name: str, layout: str, tech_stack: list[str], dirs: list[str]) -> dict:
    payload = {
        "schema": "agent-project-layout-v1",
        "project_name": project_name,
        "layout": layout,
        "tech_stack": tech_stack,
        "directories": dirs,
    }
    payload["policy"] = {
        "architecture_boundaries_required": True,
        "empty_directories_require_architecture_boundary_exception": True,
    }
    if not dirs:
        payload["policy"]["architecture_boundary_exception"] = (
            "No application directories were declared at initialization; fill project-layout, ARCHITECTURE, and DEV_MAP before non-tiny application work."
        )
    return payload


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
            "completed_active_changes_fail_validation": True,
            "archive_before_completion_claim": True,
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


FEATURE_STAGE_TEMPLATES = [
    "01_REQUIREMENT_ANALYSIS.md.tmpl",
    "02_SOLUTION_DESIGN.md.tmpl",
    "03_GATE_REVIEW.md.tmpl",
    "04_DEVELOPMENT.md.tmpl",
    "05_CODE_REVIEW.md.tmpl",
    "06_TEST_REPORT.md.tmpl",
    "07_DELIVERY_SUMMARY.md.tmpl",
]


def workflow_profiles_config(project_name: str, created_at: str) -> dict:
    return {
        "schema": "agent-workflow-profiles-v1",
        "project_name": project_name,
        "created_at": created_at,
        "default_profile": "standard",
        "policy": {
            "choose_lightest_profile_that_covers_risk": True,
            "record_profile_in_task_board": True,
            "escalate_when_risk_increases": True,
            "do_not_force_full_flow_for_tiny_changes": True,
        },
        "profiles": {
            "tiny": {
                "description": "Small, low-risk documentation, template, or local cleanup work.",
                "max_risk": "low",
                "task_board_record": "optional",
                "review_gate_required": True,
                "feature_doc_templates": [],
                "stages": ["intake", "goal_refinement", "risk_classification", "task_decomposition", "implementation", "verification", "handoff"],
                "required_evidence": ["risk note", "minimal checklist", "lightweight review", "fresh validation or explicit skip reason"],
            },
            "bugfix": {
                "description": "A reproducible bug or failed check with a bounded fix.",
                "max_risk": "medium",
                "task_board_record": "required",
                "review_gate_required": True,
                "feature_doc_templates": [
                    "01_REQUIREMENT_ANALYSIS.md",
                    "04_DEVELOPMENT.md",
                    "06_TEST_REPORT.md",
                    "07_DELIVERY_SUMMARY.md",
                ],
                "stages": [
                    "intake",
                    "goal_refinement",
                    "requirement_interview",
                    "risk_classification",
                    "task_decomposition",
                    "debugging",
                    "implementation",
                    "verification",
                    "handoff",
                ],
                "required_evidence": ["requirements interview", "reproduction", "root cause", "task decomposition", "bugfix review", "fix validation", "regression check"],
            },
            "standard": {
                "description": "Normal multi-file project work with clear scope and review needs.",
                "max_risk": "high",
                "task_board_record": "required",
                "review_gate_required": True,
                "feature_doc_templates": [
                    "01_REQUIREMENT_ANALYSIS.md",
                    "02_SOLUTION_DESIGN.md",
                    "04_DEVELOPMENT.md",
                    "05_CODE_REVIEW.md",
                    "06_TEST_REPORT.md",
                    "07_DELIVERY_SUMMARY.md",
                ],
                "stages": [
                    "intake",
                    "goal_refinement",
                    "requirement_interview",
                    "risk_classification",
                    "task_decomposition",
                    "spec",
                    "plan",
                    "implementation",
                    "spec_review",
                    "quality_review",
                    "verification",
                    "handoff",
                ],
                "required_evidence": ["requirements interview", "refined goal", "approved scope", "task decomposition", "implementation plan", "review result", "fresh validation"],
            },
            "full": {
                "description": "Cross-module, architectural, release, migration, or high coordination work.",
                "max_risk": "critical",
                "task_board_record": "required",
                "review_gate_required": True,
                "feature_doc_templates": [name.replace(".tmpl", "") for name in FEATURE_STAGE_TEMPLATES],
                "stages": [
                    "intake",
                    "goal_refinement",
                    "requirement_interview",
                    "risk_classification",
                    "task_decomposition",
                    "spec",
                    "plan",
                    "gate_review",
                    "isolation",
                    "implementation",
                    "spec_review",
                    "quality_review",
                    "human_review",
                    "verification",
                    "handoff",
                    "finish",
                ],
                "required_evidence": [
                    "requirement analysis",
                    "requirements interview",
                    "solution design",
                    "gate review",
                    "implementation record",
                    "code review",
                    "test report",
                    "delivery summary",
                ],
            },
        },
        "selection_rules": [
            {
                "when": ["docs_only", "low_risk", "single_file_or_template"],
                "profile": "tiny",
            },
            {
                "when": ["bug_or_failed_check", "reproduction_available", "bounded_fix"],
                "profile": "bugfix",
            },
            {
                "when": ["multi_file_change", "new_behavior", "delegated_work"],
                "profile": "standard",
            },
            {
                "when": ["architecture_change", "migration", "release_claim", "critical_risk", "cross_team_handoff"],
                "profile": "full",
            },
        ],
    }


def task_board_config(project_name: str, created_at: str) -> dict:
    return {
        "schema": "agent-task-board-v1",
        "project_name": project_name,
        "created_at": created_at,
        "paths": {
            "features_dir": "docs/features",
            "feature_index": "docs/features/INDEX.md",
            "feature_template_dir": ".agent/templates/features",
            "intake_dir": ".agent/intake",
            "intake_template": ".agent/templates/intake-packet.md.tmpl",
        },
        "states": ["proposed", "active", "blocked", "review", "done", "archived"],
        "required_fields": [
            "id",
            "title",
            "state",
            "risk",
            "profile",
            "current_stage",
            "docs_path",
            "requirements",
            "task_decomposition",
            "created_at",
            "updated_at",
            "delivery_conclusion",
            "review_gate",
            "stage_reviews",
            "related_tasks",
        ],
        "policy": {
            "non_tiny_work_requires_task": True,
            "new_session_reads_board_before_edits": True,
            "stage_changes_update_current_stage": True,
            "goal_contract_required_for_profiles": ["bugfix", "standard", "full"],
            "goal_contract_required_states": ["active", "review", "done"],
            "goal_contract_required_before_stages": [
                "debugging",
                "spec",
                "plan",
                "gate_review",
                "isolation",
                "implementation",
                "spec_review",
                "quality_review",
                "human_review",
                "verification",
                "handoff",
                "finish",
            ],
            "goal_contract_required_fields": [
                "raw_user_goal",
                "refined_goal",
                "refinement_rationale",
                "user_confirmation_status",
                "objective",
                "user_approved_outcome",
                "non_goals",
                "constraints",
                "success_evidence",
                "stop_conditions",
                "current_decision_summary",
                "open_decisions",
                "linked_task_id",
                "linked_spec_change_id",
            ],
            "goal_confirmation_statuses": ["confirmed", "agent_assumed", "pending", "blocked"],
            "proactive_intake_required_for_non_question_work": True,
            "technology_stack_intake_required_before_initialization": True,
            "technology_stack_intake_required_for_non_tiny_design": True,
            "task_decomposition_required_for_profiles": ["tiny", "bugfix", "standard", "full"],
            "task_decomposition_complete_before_done": True,
            "task_decomposition_required_before_stages": ["plan", "implementation", "verification", "handoff"],
            "tiny_without_task_board_review_evidence": ["active_session", "runlog", ".agent/intake"],
            "review_fix_loop_required_at_stage_exit": True,
            "stage_review_loop_required_for_profiles": ["standard", "full"],
            "done_requires_delivery_conclusion": True,
            "done_requires_review_gate_pass_for_profiles": ["tiny", "bugfix", "standard", "full"],
            "review_gate_pass_status": "pass",
            "review_gate_open_findings_must_be_empty": True,
            "review_gate_latest_review_must_exist": True,
            "stage_review_required_before_stage_exit": [
                "spec",
                "plan",
                "implementation",
                "spec_review",
                "quality_review",
                "verification",
                "handoff",
            ],
            "docs_path_required_when_profile_requires_docs": True,
            "requirements_complete_before_protected_stages": True,
            "requirements_complete_before_done": True,
        },
        "items": [],
    }


def workflow_stage_definitions() -> dict:
    return {
        "intake": {
            "owner_role": "coordinator",
            "required_inputs": ["user request", "repository state"],
            "required_outputs": ["intake packet", "task profile", "risk classification", "task-board id when required"],
            "allowed_next": ["goal_refinement", "requirement_interview", "risk_classification", "spec", "plan", "implementation"],
            "rollback_to": [],
            "forbidden_actions": ["modify files before dirty-state inspection"],
        },
        "goal_refinement": {
            "owner_role": "coordinator",
            "required_inputs": ["raw user goal", "repository state", ".agent/task-board.json when present"],
            "required_outputs": ["refined goal", "non-goals", "success evidence", "confirmation or assumption status"],
            "allowed_next": ["requirement_interview", "risk_classification", "spec", "plan"],
            "rollback_to": ["intake"],
            "forbidden_actions": ["set a durable goal without preserving raw_user_goal"],
        },
        "requirement_interview": {
            "owner_role": "coordinator",
            "required_inputs": ["user request", "repository state", "docs/DOMAIN_GLOSSARY.md"],
            "required_outputs": ["shared understanding", "open questions resolved or recorded", "domain glossary updates", "code/docs cross-check result"],
            "allowed_next": ["risk_classification", "spec", "plan", "debugging"],
            "rollback_to": ["intake"],
            "forbidden_actions": ["ask multiple unrelated questions at once", "accept a user claim that conflicts with current code or docs without resolving it"],
        },
        "risk_classification": {
            "owner_role": "coordinator",
            "required_inputs": [".agent/risk-zones.json", ".agent/workflow-profiles.json", "requirements status"],
            "required_outputs": ["risk level", "autonomy decision", "selected workflow profile"],
            "allowed_next": ["task_decomposition", "spec", "plan", "debugging", "implementation", "gate_review"],
            "rollback_to": ["requirement_interview", "intake"],
            "forbidden_actions": ["continue silently after risk increases"],
        },
        "task_decomposition": {
            "owner_role": "coordinator",
            "required_inputs": ["refined goal", "requirements status", "risk classification", "workflow profile"],
            "required_outputs": ["next task", "subtasks or checklist", "dependencies", "validation evidence path"],
            "allowed_next": ["debugging", "plan", "implementation", "verification"],
            "rollback_to": ["goal_refinement", "requirement_interview", "risk_classification"],
            "forbidden_actions": ["start non-trivial implementation without a next task"],
        },
        "spec": {
            "owner_role": "coordinator",
            "required_inputs": ["embedded spec change or documented project approval"],
            "required_outputs": ["approved scope", "acceptance criteria"],
            "allowed_next": ["plan", "gate_review"],
            "rollback_to": ["intake", "risk_classification"],
            "forbidden_actions": ["implement unapproved non-trivial behavior"],
        },
        "plan": {
            "owner_role": "coordinator",
            "required_inputs": ["approved scope", "risk classification"],
            "required_outputs": ["exact files", "commands", "expected results", "stop conditions"],
            "allowed_next": ["gate_review", "isolation", "implementation"],
            "rollback_to": ["spec", "risk_classification"],
            "forbidden_actions": ["use placeholder tasks", "omit validation plan"],
        },
        "gate_review": {
            "owner_role": "reviewer",
            "required_inputs": ["requirement analysis", "solution design", "risk classification"],
            "required_outputs": ["go/no-go decision", "required changes", "approval evidence"],
            "allowed_next": ["isolation", "implementation"],
            "rollback_to": ["spec", "plan"],
            "forbidden_actions": ["reviewer implements the fix they request"],
        },
        "debugging": {
            "owner_role": "worker",
            "required_inputs": ["reproduction", "observed failure"],
            "required_outputs": ["root cause", "fix hypothesis", "minimal validation"],
            "allowed_next": ["implementation", "verification"],
            "rollback_to": ["intake"],
            "forbidden_actions": ["patch without reproduction or stated exception"],
        },
        "isolation": {
            "owner_role": "worker",
            "required_inputs": [".agent/worktrees.json", "baseline validation"],
            "required_outputs": ["branch or worktree decision", "baseline result"],
            "allowed_next": ["implementation"],
            "rollback_to": ["plan"],
            "forbidden_actions": ["destructive cleanup without explicit confirmation"],
        },
        "implementation": {
            "owner_role": "worker",
            "required_inputs": ["plan", "write boundary", "success criteria"],
            "required_outputs": ["changed files", "implementation notes", "local validation"],
            "allowed_next": ["spec_review", "quality_review", "verification"],
            "rollback_to": ["plan", "debugging"],
            "forbidden_actions": ["unrelated cleanup", "speculative abstraction", "edit outside write boundary"],
        },
        "spec_review": {
            "owner_role": "spec_reviewer",
            "required_inputs": ["requested behavior", "diff", "acceptance criteria"],
            "required_outputs": ["missing behavior findings", "extra behavior findings", "pass or fail"],
            "allowed_next": ["quality_review", "implementation"],
            "rollback_to": ["implementation"],
            "forbidden_actions": ["modify implementation while reviewing"],
        },
        "quality_review": {
            "owner_role": "quality_reviewer",
            "required_inputs": ["spec review pass", "diff", "validation evidence"],
            "required_outputs": ["maintainability findings", "test findings", "safety findings", "pass or fail"],
            "allowed_next": ["human_review", "verification", "implementation"],
            "rollback_to": ["implementation", "spec_review"],
            "forbidden_actions": ["modify implementation while reviewing"],
        },
        "human_review": {
            "owner_role": "reviewer",
            "required_inputs": ["risk level", "diff or file review evidence"],
            "required_outputs": ["reviewer", "files reviewed", "high-risk paths checked", "conclusion"],
            "allowed_next": ["verification", "implementation"],
            "rollback_to": ["implementation", "quality_review"],
            "forbidden_actions": ["treat agent summary as human review"],
        },
        "verification": {
            "owner_role": "verifier",
            "required_inputs": ["validation commands", "baseline snapshot when available"],
            "required_outputs": ["fresh validation result", "baseline delta", "runlog evidence"],
            "allowed_next": ["handoff", "implementation"],
            "rollback_to": ["implementation"],
            "forbidden_actions": ["claim checks passed without command evidence", "fix findings directly"],
        },
        "handoff": {
            "owner_role": "coordinator",
            "required_inputs": ["task-board state", "session state", "validation evidence"],
            "required_outputs": ["checkpoint", "resume prompt", "delivery or remaining-risk summary"],
            "allowed_next": ["finish", "implementation"],
            "rollback_to": ["verification"],
            "forbidden_actions": ["depend on chat history as durable state"],
        },
        "finish": {
            "owner_role": "coordinator",
            "required_inputs": ["user finish choice", "fresh validation", "handoff summary"],
            "required_outputs": ["merge/PR/keep/discard decision", "final runlog evidence"],
            "allowed_next": [],
            "rollback_to": ["handoff", "verification"],
            "forbidden_actions": ["destructive branch or worktree cleanup without confirmation"],
        },
    }


def workflow_config(project_name: str, created_at: str, openspec_enabled: bool) -> dict:
    return {
        "schema": "agent-workflow-v1",
        "project_name": project_name,
        "created_at": created_at,
        "mode": "policy-gated",
        "spec_source": "agent-gov-spec" if openspec_enabled else "project-docs",
        "profile_source": ".agent/workflow-profiles.json",
        "task_board": ".agent/task-board.json",
        "role_contracts": ".agent/role-contracts.json",
        "feature_docs": "docs/features",
        "stages": [
            "intake",
            "goal_refinement",
            "requirement_interview",
            "risk_classification",
            "task_decomposition",
            "debugging",
            "spec",
            "plan",
            "gate_review",
            "isolation",
            "implementation",
            "spec_review",
            "quality_review",
            "human_review",
            "verification",
            "handoff",
            "finish",
        ],
        "stage_definitions": workflow_stage_definitions(),
        "gates": {
            "goal_refinement": {
                "required_for_profiles": ["bugfix", "standard", "full"],
                "advisory_for_profiles": ["tiny"],
                "preserve_raw_user_goal": True,
                "write_refined_goal_before_durable_goal": True,
                "confirmation_statuses": ["confirmed", "agent_assumed", "pending", "blocked"],
                "confirmation_required_when_ambiguity_affects": ["architecture", "data", "security", "release", "cost", "destructive_action"],
                "record_non_goals_constraints_success_evidence": True,
                "intake_packet_template": ".agent/templates/intake-packet.md.tmpl",
            },
            "technology_stack_intake": {
                "required_for": ["initialization", "non_tiny_design", "architecture_change", "runtime_selection"],
                "ask_one_question_at_a_time": True,
                "provide_recommended_answer_and_reason": True,
                "structured_intake_output": "--architecture-intake JSON",
                "do_not_rely_on_transient_chat": True,
            },
            "task_decomposition": {
                "required_for_profiles": ["tiny", "bugfix", "standard", "full"],
                "tiny_evidence": ["active session", ".agent/runlog.jsonl", ".agent/intake/"],
                "bugfix_chain": ["reproduction", "current_expected_preserved_behavior", "root_cause", "fix_tasks", "regression_check"],
                "standard_full_fields": ["subtask_id", "dependency", "parallelizable", "file_scope", "validation", "owner_role", "reviewer_role", "completion_evidence"],
                "complete_before": ["implementation", "verification", "handoff", "done"],
            },
            "requirements_interview": {
                "required_for_profiles": ["bugfix", "standard", "full"],
                "feature_doc": "docs/features/<task-id>/01_REQUIREMENT_ANALYSIS.md",
                "domain_glossary": "docs/DOMAIN_GLOSSARY.md",
                "ask_one_question_at_a_time": True,
                "provide_recommended_answer_and_reason": True,
                "stop_when_shared_understanding_missing": True,
                "cross_check_user_claims_against_code_and_docs": True,
                "record_unresolved_questions": True,
                "update_domain_glossary_for_new_or_ambiguous_terms": True,
            },
            "risk_classification": {
                "required_for": ["implementation", "refactor", "migration", "security_change", "public_api_change"],
                "policy": ".agent/risk-zones.json",
                "record_in_plan": True,
                "stop_when_risk_increases": True,
            },
            "design_approval": {
                "required_for": ["non_trivial_change", "architecture_change", "cross_module_behavior_change"],
                "evidence": ["embedded spec proposal/design approval or recorded project-doc approval"],
            },
            "plan_quality": {
                "required_for": ["multi_step_change", "delegated_work"],
                "requires_exact_files": True,
                "requires_commands_with_expected_results": True,
                "forbidden_placeholders": ["TBD", "TODO", "implement later", "fill in details"],
                "external_sources_record_status": True,
                "minimal_solution_path_considered": True,
            },
            "loop_engineering": {
                "required_for_profiles": ["standard", "full"],
                "policy": ".agent/loop-engineering.json",
                "loop_contract_required": True,
                "iteration_budget_required": True,
                "observation_signal_required": True,
                "stop_conditions_required": True,
                "evidence_per_iteration_required": True,
                "same_failure_requires_strategy_change": True,
                "repeat_failures_promote_to_harness_evolution": True,
                "human_interrupt_for_high_risk_or_destructive": True,
                "self_approval_forbidden": True,
            },
            "goal_contract": {
                "required_for_profiles": ["bugfix", "standard", "full"],
                "required_for": ["long_running_session", "high_context_task", "active_bugfix_standard_or_full_task"],
                "task_board_field": ".agent/task-board.json#/items/*/goal_contract",
                "session_files": [
                    ".agent/sessions/<session-id>/session.md",
                    ".agent/sessions/<session-id>/handoff.md",
                    ".agent/sessions/<session-id>/decisions.md",
                ],
                "feature_docs": [
                    "docs/features/<task-id>/01_REQUIREMENT_ANALYSIS.md",
                    "docs/features/<task-id>/02_SOLUTION_DESIGN.md",
                    "docs/features/<task-id>/04_DEVELOPMENT.md",
                ],
                "required_fields": [
                    "raw_user_goal",
                    "refined_goal",
                    "refinement_rationale",
                    "user_confirmation_status",
                    "objective",
                    "user_approved_outcome",
                    "non_goals",
                    "constraints",
                    "success_evidence",
                    "stop_conditions",
                    "current_decision_summary",
                    "open_decisions",
                    "linked_task_id",
                    "linked_spec_change_id",
                ],
                "repository_truth_overrides_memory": True,
                "update_when_user_changes_objective_or_scope": True,
                "do_not_duplicate_full_spec_body": True,
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
                "minimal_sufficient_ladder": [
                    "skip_unneeded_work",
                    "reuse_local_pattern",
                    "prefer_standard_library",
                    "prefer_native_platform",
                    "prefer_existing_dependency",
                    "small_direct_edit",
                    "minimum_new_code",
                ],
                "safety_carveouts": [
                    "trust_boundary_validation",
                    "data_loss_prevention",
                    "security",
                    "privacy",
                    "accessibility",
                    "explicit_requirements",
                    "required_checks",
                ],
                "avoid_speculative_features": True,
                "abstractions_require_repeated_complexity_or_existing_pattern": True,
                "root_cause_before_symptom_patch": True,
                "simplification_ceiling_requires_upgrade_trigger": True,
                "touch_only_requested_scope": True,
                "every_changed_line_traces_to_request": True,
                "success_criteria_required": True,
                "exceptions_require_session_note": True,
            },
            "diff_traceability": {
                "required_for": ["implementation", "refactor", "bugfix", "generated_file_update"],
                "policy": ".agent/review-policy.json",
                "every_changed_line_traces_to_request": True,
                "incidental_changes_require_removal_or_exception": True,
                "record_in_review": True,
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
                "finder_cannot_fix": True,
                "complexity_audit_is_separate_from_correctness_review": True,
            },
            "stage_review_loop": {
                "required_for_profiles": ["standard", "full"],
                "required_before_stage_exit": [
                    "spec",
                    "plan",
                    "implementation",
                    "spec_review",
                    "quality_review",
                    "verification",
                    "handoff",
                ],
                "loop": ["review", "fix", "re_review"],
                "latest_stage_review_must_be_clean": True,
                "finding_bearing_stage_review_must_remain_needs_fix": True,
                "fix_requires_revalidation": True,
                "fix_requires_next_review_round": True,
                "accepted_exceptions_require_owner_date_and_residual_risk": True,
            },
            "review_fix_gate": {
                "required_for": ["tiny_task_done", "bugfix_task_done", "standard_task_done", "full_task_done", "handoff", "merge", "pull_request", "archive", "release_claim"],
                "source": ".agent/task-board.json#/items/*/review_gate",
                "applies_to_stage_review_loop": True,
                "tiny_without_task_board_evidence": ["active session", ".agent/runlog.jsonl", ".agent/intake/"],
                "latest_review_status_must_be": "pass",
                "open_findings_must_be_empty": True,
                "latest_review_path_must_exist": True,
                "finding_bearing_review_must_remain_needs_fix": True,
                "fix_requires_next_review_round": True,
            },
            "human_review_evidence": {
                "required_for": ["high_risk_change", "critical_risk_change", "release_claim", "delegated_substantial_change"],
                "policy": ".agent/review-policy.json",
                "agent_summary_is_not_review": True,
                "requires_diff_or_file_review": True,
            },
            "completion_verification": {
                "required_for": ["handoff", "merge", "pull_request", "archive", "spec_archive"],
                "fresh_validation_required": True,
                "review_fix_gate_required_for_profiles": ["tiny", "bugfix", "standard", "full"],
                "record_results_in_runlog": True,
                "no_completion_claim_without_command_evidence": True,
                "completed_spec_changes_must_be_archived": True,
                "optimization_claims_require_isolated_baseline": True,
                "reduction_metrics_must_keep_safety_checks": True,
            },
        },
        "commands": {
            "list_validation": "python3 scripts/agent_validate.py --list",
            "archive_completed_spec": "python3 scripts/agent_spec.py archive <name>",
            "record_runlog": "python3 scripts/agent_runlog.py record --kind validation --outcome <pass|fail|skipped> --summary <summary>",
            "session_checkpoint": "python3 .agent/tools/agent_session.py checkpoint --summary <summary>",
            "session_compact": "python3 .agent/tools/agent_session.py compact --summary <summary> --next <next>",
        },
    }


def loop_engineering_config(project_name: str, created_at: str) -> dict:
    return {
        "schema": "agent-loop-engineering-v1",
        "project_name": project_name,
        "created_at": created_at,
        "purpose": "Bound agent work loops so iterative model work has goals, observations, budgets, evidence, and escalation paths.",
        "sources": [
            {
                "name": "Anthropic Building Effective Agents",
                "url": "https://www.anthropic.com/engineering/building-effective-agents",
                "adopted_practice": "Prefer simple workflows first, then use evaluator-optimizer loops when feedback is objective.",
            },
            {
                "name": "LangGraph",
                "url": "https://github.com/langchain-ai/langgraph",
                "adopted_practice": "Use explicit state transitions, durable progress, and human interrupt points for long-running loops.",
            },
            {
                "name": "SWE-agent",
                "url": "https://github.com/SWE-agent/SWE-agent",
                "adopted_practice": "Treat tool interaction as an observe-act loop with bounded environment feedback.",
            },
            {
                "name": "DSPy",
                "url": "https://github.com/stanfordnlp/dspy",
                "adopted_practice": "Optimize prompts or programs against eval signals instead of subjective self-approval.",
            },
            {
                "name": "Promptfoo",
                "url": "https://github.com/promptfoo/promptfoo",
                "adopted_practice": "Keep regression evals in repeatable local or CI commands.",
            },
        ],
        "policy": {
            "loop_contract_required_for_non_tiny_work": True,
            "bounded_iterations_required": True,
            "observation_signal_required": True,
            "stop_conditions_required": True,
            "evidence_per_iteration_required": True,
            "same_failure_requires_strategy_change": True,
            "repeat_failure_threshold": 2,
            "budget_exhaustion_blocks_completion_claim": True,
            "human_interrupt_for_high_risk_or_destructive": True,
            "self_approval_is_not_release_evidence": True,
            "finder_cannot_fix_applies_to_review_loops": True,
            "prevalidate_inputs_before_expensive_work": True,
            "failed_runs_exit_nonzero": True,
            "failed_runs_record_evidence_paths": True,
            "failed_optimization_cannot_be_improvement": True,
        },
        "loop_types": {
            "work_loop": {
                "sequence": ["plan", "act", "observe", "adjust"],
                "default_iteration_budget": 3,
                "observation_signals": ["validation output", "diff review", "task-board stage state"],
                "stop_conditions": ["acceptance_criteria_met", "risk_increased", "blocked", "budget_exhausted"],
                "evidence": ["docs/features/<task-id>/04_DEVELOPMENT.md", ".agent/runlog.jsonl", ".agent/sessions/<session-id>/validation.md"],
            },
            "review_fix_loop": {
                "sequence": ["review", "fix", "revalidate", "re_review"],
                "default_iteration_budget": 4,
                "observation_signals": ["open blocker findings", "open major findings", "open minor findings", "latest review status"],
                "stop_conditions": ["latest_review_passes", "accepted_exception_recorded", "budget_exhausted"],
                "evidence": ["docs/features/<task-id>/05_CODE_REVIEW.md", ".agent/task-board.json#/items/*/review_gate"],
            },
            "debugging_loop": {
                "sequence": ["reproduce", "hypothesize", "test", "fix", "verify"],
                "default_iteration_budget": 3,
                "observation_signals": ["reproduction command", "failing output", "passing output"],
                "stop_conditions": ["root_cause_confirmed_and_fixed", "hypothesis_disproved", "budget_exhausted"],
                "evidence": [".agent/templates/debugging-record.md.tmpl", "docs/features/<task-id>/06_TEST_REPORT.md"],
            },
            "eval_optimization_loop": {
                "sequence": ["prevalidate", "baseline", "change", "benchmark", "accept_or_revert"],
                "default_iteration_budget": 3,
                "observation_signals": ["score delta", "regression count", "quality review"],
                "stop_conditions": ["objective_improvement", "regression_detected", "failed_run", "budget_exhausted"],
                "evidence": [".agent/evals/latest.md", ".agent/baselines/*.json", ".agent/runlog.jsonl"],
            },
            "session_recovery_loop": {
                "sequence": ["bootstrap", "ground", "retrieve", "verify", "continue"],
                "default_iteration_budget": 2,
                "observation_signals": ["bootstrap output", "git status", "task-board state", "spec status"],
                "stop_conditions": ["current_truth_confirmed", "conflict_requires_user", "budget_exhausted"],
                "evidence": [".agent/sessions/bootstrap.md", ".agent/sessions/<session-id>/grounding.md"],
            },
        },
        "escalation": {
            "on_same_failure_repeated": "change strategy before retrying the same loop",
            "after_repeat_failure_threshold": "classify a harness gap and promote the fix",
            "classification_command": "python3 scripts/agent_gc.py classify --category <category> --summary <summary>",
            "preferred_categories": ["workflow_gap", "loop_gap", "script_gap", "role_contract_gap", "knowledge_gap", "context_gap"],
            "postmortem_when_user_visible_or_high_risk": "docs/incidents/",
        },
        "integration": {
            "workflow_gate": ".agent/workflow.json#/gates/loop_engineering",
            "stage_reviews": ".agent/task-board.json#/items/*/stage_reviews",
            "review_gate": ".agent/task-board.json#/items/*/review_gate",
            "runlog": ".agent/runlog.jsonl",
            "harness_evolution": ".agent/harness-evolution.json",
            "quality_doc": "docs/LOOP_ENGINEERING.md",
        },
    }


def risk_zones_config(project_name: str, created_at: str) -> dict:
    return {
        "schema": "agent-risk-zones-v1",
        "project_name": project_name,
        "created_at": created_at,
        "autonomy_levels": {
            "low": {
                "agent_may_implement_after_plan": True,
                "human_review_required": False,
                "examples": ["docs-only clarification", "local template update", "narrow test-only change"],
            },
            "medium": {
                "agent_may_implement_after_plan": True,
                "human_review_required": "recommended",
                "examples": ["single-module behavior change", "non-public refactor", "new local script"],
            },
            "high": {
                "agent_may_implement_after_approval": True,
                "human_review_required": True,
                "examples": ["auth or permission change", "data migration", "public API behavior", "release automation"],
            },
            "critical": {
                "agent_may_not_autonomously_modify": True,
                "human_review_required": True,
                "examples": ["secrets handling", "payment flow", "destructive production operation", "legal or compliance policy"],
            },
        },
        "high_risk_patterns": [
            "auth",
            "authorization",
            "permission",
            "payment",
            "billing",
            "migration",
            "security",
            "privacy",
            "public-api",
            "release",
            "destructive-operation",
            "secret",
        ],
        "policy": {
            "classify_before_implementation": True,
            "record_risk_in_plan_and_review": True,
            "stop_when_risk_increases": True,
            "high_requires_user_or_project_approval": True,
            "critical_requires_human_owner_plan": True,
        },
    }


def review_policy_config(project_name: str, created_at: str) -> dict:
    return {
        "schema": "agent-review-policy-v1",
        "project_name": project_name,
        "created_at": created_at,
        "diff_traceability": {
            "categories": ["requested", "necessary-support", "incidental", "risky"],
            "every_changed_line_traces_to_request": True,
            "incidental_requires_removal_or_exception": True,
            "risky_requires_risk_review": True,
            "record_category_per_file": True,
        },
        "human_review": {
            "agent_summary_is_not_review": True,
            "requires_diff_or_file_review": True,
            "required_for_risk": ["high", "critical"],
            "evidence_fields": [
                "reviewer",
                "review_type",
                "diff_range",
                "files_reviewed",
                "high_risk_paths_checked",
                "conclusion",
            ],
        },
        "automated_review": {
            "allowed_as_precheck": True,
            "not_a_substitute_for_automated_checks": True,
            "not_a_substitute_for_required_human_review": True,
            "record_model_or_tool_when_used": True,
        },
        "policy": {
            "spec_review_before_quality_review": True,
            "re_review_after_fixes": True,
            "fresh_validation_after_review_fixes": True,
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
            "finder_cannot_fix": True,
            "reviewer_roles_are_read_only": True,
            "external_research_requires_source_status": True,
            "complexity_audit_separate_from_correctness_review": True,
        },
        "role_contracts": ".agent/role-contracts.json",
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
                "source_status",
                "validation",
            ],
            "status_values": ["DONE", "DONE_WITH_CONCERNS", "NEEDS_CONTEXT", "BLOCKED"],
            "risk_values": ["low", "medium", "high", "critical"],
            "max_supporting_notes_tokens": 700,
            "prefer_path_line_first_findings": True,
        },
        "dispatch_template": ".agent/templates/subagent-task.md.tmpl",
    }


def role_contracts_config(project_name: str, created_at: str, governance_profile: str) -> dict:
    read_common = [
        "AGENTS.md",
        ".agent/workflow.json",
        ".agent/workflow-profiles.json",
        ".agent/loop-engineering.json",
        ".agent/task-board.json",
        ".agent/risk-zones.json",
        ".agent/review-policy.json",
        "docs/DOMAIN_GLOSSARY.md",
    ]
    if profile_at_least(governance_profile, "full"):
        read_common.append(".agent/subagents.json")
    return {
        "schema": "agent-role-contracts-v1",
        "project_name": project_name,
        "created_at": created_at,
        "policy": {
            "contracts_are_machine_checkable": True,
            "downstream_roles_must_not_rewrite_upstream_outputs": True,
            "finder_cannot_fix": True,
            "reviewer_roles_are_read_only": True,
            "route_findings_back_to_coordinator_or_worker": True,
        },
        "separation_of_duties": {
            "finder_roles": ["verifier", "spec_reviewer", "quality_reviewer", "reviewer"],
            "fixer_roles": ["worker"],
            "router_roles": ["coordinator"],
            "finder_cannot_modify_files": True,
            "reviewer_cannot_mark_own_work_passed": True,
        },
        "contracts": {
            "coordinator": {
                "owner_for_stages": ["intake", "requirement_interview", "risk_classification", "spec", "plan", "handoff", "finish"],
                "must_read": read_common,
                "may_write": [".agent/task-board.json", ".agent/sessions/**", "docs/features/**", "docs/DOMAIN_GLOSSARY.md"],
                "must_write": ["task-board state when required", "requirements status", "handoff/resume state"],
                "forbidden_actions": ["perform implementation inside reviewer-only stages"],
                "blocking_conditions": ["missing risk classification", "missing task-board record for non-tiny work"],
            },
            "searcher": {
                "owner_for_stages": [],
                "must_read": read_common,
                "may_write": [],
                "must_write": ["external-source summary", "source status: verified | partial | blocked"],
                "forbidden_actions": ["modify repository files", "present inference as sourced fact"],
                "blocking_conditions": ["missing source attribution for current external facts", "unverified source content used as fact"],
            },
            "explorer": {
                "owner_for_stages": ["intake"],
                "must_read": read_common,
                "may_write": [],
                "must_write": ["path-first repository findings"],
                "forbidden_actions": ["modify repository files", "infer ownership without file evidence"],
                "blocking_conditions": ["assigned read boundary is unclear"],
            },
            "worker": {
                "owner_for_stages": ["debugging", "isolation", "implementation"],
                "must_read": read_common + [".agent/worktrees.json"],
                "may_write": ["declared write boundary only"],
                "must_write": ["changed files summary", "validation attempted", "concerns or blockers"],
                "forbidden_actions": ["edit outside write boundary", "review own work as passed", "do unrelated cleanup"],
                "blocking_conditions": ["risk exceeds approval", "write boundary overlaps another worker"],
            },
            "verifier": {
                "owner_for_stages": ["verification"],
                "must_read": read_common + [".agent/mechanical-checks.json", ".agent/baselines.json"],
                "may_write": [".agent/baselines/**", ".agent/runlog.jsonl"],
                "must_write": ["validation result", "baseline delta when available"],
                "forbidden_actions": ["fix failures directly", "change implementation files"],
                "blocking_conditions": ["validation command is missing or unsafe"],
            },
            "spec_reviewer": {
                "owner_for_stages": ["spec_review"],
                "must_read": read_common + ["embedded spec or feature docs", "diff"],
                "may_write": [],
                "must_write": ["spec compliance finding list", "pass or fail conclusion"],
                "forbidden_actions": ["fix missing behavior directly", "run quality review before spec review pass"],
                "blocking_conditions": ["requested behavior or acceptance criteria are missing"],
            },
            "quality_reviewer": {
                "owner_for_stages": ["quality_review"],
                "must_read": read_common + ["spec review result", "diff", "validation evidence"],
                "may_write": [],
                "must_write": ["quality finding list", "complexity findings when in scope", "pass or fail conclusion"],
                "forbidden_actions": ["fix quality findings directly", "review before spec review passes"],
                "blocking_conditions": ["spec review has unresolved findings"],
            },
            "reviewer": {
                "owner_for_stages": ["gate_review", "human_review"],
                "must_read": read_common + [".agent/role-contracts.json"],
                "may_write": [],
                "must_write": ["approval or rejection evidence", "high-risk paths checked when applicable"],
                "forbidden_actions": ["replace human review evidence with agent summary", "fix findings directly"],
                "blocking_conditions": ["high-risk paths are unspecified for high or critical work"],
            },
            "coordinator_delegate": {
                "owner_for_stages": ["handoff"],
                "must_read": read_common,
                "may_write": [".agent/sessions/**"],
                "must_write": ["accepted snapshots", "remaining risks"],
                "forbidden_actions": ["hide blocked subagent status"],
                "blocking_conditions": ["subagent snapshot status is BLOCKED or NEEDS_CONTEXT"],
            },
        },
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


def knowledge_config(project_name: str, created_at: str, governance_profile: str) -> dict:
    docs = [
        "docs/index.md",
        "docs/ARCHITECTURE.md",
        "docs/QUALITY.md",
        "docs/RELIABILITY.md",
        "docs/QUALITY_SCORE.md",
        "docs/AI_CODING_GLOSSARY.md",
        "docs/DOMAIN_GLOSSARY.md",
        "docs/DEV_MAP.md",
        "docs/LOOP_ENGINEERING.md",
        "docs/RESOURCES.md",
        "docs/AGENT_RUNTIME_ARCHITECTURE.md",
        "docs/SKILL_RUNTIME.md",
        "docs/features/INDEX.md",
        "docs/tech-debt.md",
        "docs/adr/README.md",
        "docs/rfcs/README.md",
        "docs/incidents/README.md",
    ]
    if profile_at_least(governance_profile, "full"):
        docs.extend(["docs/SECURITY.md", "docs/TOOLING.md"])
    return {
        "schema": "agent-knowledge-v1",
        "project_name": project_name,
        "created_at": created_at,
        "promotion_policy": {
            "record_locations": [
                ".agent/knowledge.json#/promotion_bundles",
                ".agent/sessions/<session-id>/decisions.md",
                "docs/features/<task-id>/04_DEVELOPMENT.md",
                "docs/adr/",
                "docs/rfcs/",
                "docs/incidents/",
            ],
            "candidate_types": [
                "episodic",
                "semantic",
                "procedural",
                "architecture",
                "validation",
                "workflow",
                "domain-term",
            ],
            "target_surfaces": [
                "docs/",
                ".agent/knowledge.json",
                ".agent/memory/",
                "docs/DEV_MAP.md",
                "docs/DOMAIN_GLOSSARY.md",
                "docs/features/",
                "docs/adr/",
                "docs/rfcs/",
                "docs/incidents/",
                ".agent/workflow.json",
                ".agent/loop-engineering.json",
                ".agent/review-policy.json",
                ".codex/skills/",
                ".agent/templates/",
            ],
            "authority_levels": [
                "advisory-memory",
                "durable-project-fact",
                "reviewed-procedural-rule",
                "generated-policy",
            ],
            "source_statuses": ["verified", "partial", "blocked"],
            "review_statuses": ["pending", "reviewed", "rejected", "deferred"],
            "required_fields": [
                "id",
                "candidate_type",
                "source_evidence",
                "source_status",
                "target_surface",
                "authority_level",
                "owner",
                "review_status",
                "freshness",
                "validation",
                "decision",
            ],
            "procedural_requires_review_ref": True,
            "blocked_sources_cannot_be_promoted": True,
            "rejected_or_deferred_requires_reason": True,
            "do_not_promote_from_single_unverified_session": True,
        },
        "evidence_boundary_policy": {
            "diagnostic_artifacts": "Raw or long command output belongs in ignored local artifacts or declared artifact paths; tracked files store compact summaries and pointers.",
            "runlog": "Compact parseable evidence for validations, high-risk capability use, session lifecycle actions, and accepted exceptions.",
            "sessions": "Current work state, decisions, changed files, validation summaries, offload entries, and handoff notes.",
            "memory": "Advisory searchable summaries with source path, review status, and recall limits; never source of truth.",
            "knowledge_docs": "Reviewed durable project knowledge with owner, source links, freshness metadata, and stale-section markers.",
            "specs_and_feature_docs": "Authoritative planned scope, acceptance criteria, review evidence, and delivery conclusion for non-tiny work.",
            "forbidden_in_tracked_ledgers": [
                "raw transcripts",
                "terminal scrollback",
                "secrets",
                "private host data",
                "long diagnostic logs",
            ],
        },
        "promotion_bundles": [],
        "documents": [
            {
                "path": path,
                "owner": "governance-owner",
                "last_reviewed": created_at[:10],
                "source_links": [],
                "known_stale_sections": [],
            }
            for path in docs
        ],
    }


def dev_map_config(project_name: str, created_at: str, dirs: list[str]) -> dict:
    application_area = {
        "id": "application",
        "name": "Application code",
        "entry_points": dirs[:3],
        "read_before_edit": ["docs/ARCHITECTURE.md", "docs/QUALITY.md", "docs/DOMAIN_GLOSSARY.md", "docs/SKILL_RUNTIME.md"],
        "owned_paths": dirs,
        "common_patterns": ["Update this area when application entry points, module ownership, or implementation patterns change."],
    }
    if not dirs:
        application_area["architecture_boundary_exception"] = (
            "No application directories were declared at initialization; fill this area before non-tiny application work."
        )
    areas = [
        {
            "id": "governance",
            "name": "Agent governance",
            "entry_points": ["AGENTS.md", ".agent/config.json", ".agent/harness.json", ".agent/skill-runtime.json"],
            "read_before_edit": ["docs/index.md", "docs/QUALITY.md", "docs/DEV_MAP.md", "docs/LOOP_ENGINEERING.md", "docs/RESOURCES.md", "docs/SKILL_RUNTIME.md"],
            "owned_paths": [".agent/", "docs/", "scripts/agent_*.py"],
            "common_patterns": [
                "Keep durable truth in repository files, not chat history.",
                "Resource assets live in `.agent/resources.json`; raw secret material stays in ignored local files or external vault/proxy references.",
                "Loop contracts live in `.agent/loop-engineering.json`; long-running agent work must have budgets, evidence, stop conditions, and escalation paths.",
            ],
        },
        application_area,
    ]
    return {
        "schema": "agent-dev-map-v1",
        "project_name": project_name,
        "created_at": created_at,
        "doc": "docs/DEV_MAP.md",
        "policy": {
            "map_is_index_not_inventory": True,
            "update_when_entry_points_change": True,
            "update_when_module_ownership_changes": True,
            "new_sessions_read_before_broad_edits": True,
        },
        "areas": areas,
    }


def harness_evolution_config(project_name: str, created_at: str) -> dict:
    categories = {
        "rule_gap": "A repeated mistake or red line should become an agent-readable rule.",
        "skill_gap": "A repeated operation should become a documented skill workflow.",
        "script_gap": "A soft rule should become a deterministic check or command.",
        "workflow_gap": "A stage, transition, rollback, or approval condition was missing.",
        "loop_gap": "An iterative agent work loop lacked a goal, observation signal, budget, stop condition, evidence, or escalation path.",
        "role_contract_gap": "A role boundary, forbidden action, or handoff contract failed.",
        "tool_or_mcp_gap": "A local tool, project resource catalog, MCP, or external integration boundary was missing.",
        "knowledge_gap": "A stable project fact was missing from docs or dev map.",
        "session_gap": "Context, memory, handoff, or resume state was insufficient.",
        "context_gap": "Agent-facing context was too large, stale, or poorly indexed.",
    }
    return {
        "schema": "agent-harness-evolution-v1",
        "project_name": project_name,
        "created_at": created_at,
        "incident_categories": categories,
        "policy": {
            "classify_governance_failures": True,
            "turn_repeat_failures_into_harness_changes": True,
            "prefer_script_for_mechanical_rules": True,
            "prefer_docs_for_stable_knowledge": True,
            "record_promotions_in_postmortems": True,
        },
        "promotion_targets": {
            "rule_gap": ["AGENTS.md", ".agent/workflow.json", ".agent/review-policy.json"],
            "skill_gap": [".codex/skills", ".agent/skill-distribution.json"],
            "script_gap": ["scripts/agent_check.py", "scripts/agent_verify.py"],
            "workflow_gap": [".agent/workflow.json", ".agent/workflow-profiles.json"],
            "loop_gap": [".agent/loop-engineering.json", ".agent/workflow.json", ".agent/harness-evolution.json"],
            "role_contract_gap": [".agent/role-contracts.json", ".agent/subagents.json"],
            "tool_or_mcp_gap": [".agent/capabilities.json", ".agent/resources.json", ".agent/mcp-policy.json"],
            "knowledge_gap": ["docs/index.md", "docs/DEV_MAP.md", "docs/DOMAIN_GLOSSARY.md", ".agent/knowledge.json"],
            "session_gap": [".agent/sessions", ".agent/memory.json"],
            "context_gap": [".agent/context.json", ".agent/context/latest.md"],
        },
        "commands": {
            "gc_report": "python3 scripts/agent_gc.py report",
            "classify": "python3 scripts/agent_gc.py classify --category <category> --summary <summary>",
            "postmortem_template": ".agent/templates/postmortem.md.tmpl",
        },
        "incidents": [],
    }


def mcp_policy_config(project_name: str, created_at: str) -> dict:
    return {
        "schema": "agent-mcp-policy-v1",
        "project_name": project_name,
        "created_at": created_at,
        "mode": "optional-disabled-by-default",
        "policy": {
            "mcp_is_not_required_for_local_governance": True,
            "deny_external_network_by_default": True,
            "credentials_must_not_be_stored_in_repo": True,
            "credentials_must_use_vault_or_proxy": True,
            "sandbox_must_not_receive_raw_credentials": True,
            "credential_rotation_and_audit_required": True,
            "destructive_or_release_operations_need_human_approval": True,
            "record_high_risk_mcp_use_in_runlog": True,
            "prefer_read_only_integrations_until_delivery_loop_is_stable": True,
        },
        "trust_boundaries": {
            "repo_local": {"default": "allow", "notes": "Local filesystem governance files."},
            "resource_catalog": {
                "default": "metadata-and-references-only",
                "notes": "Project resources live in .agent/resources.json; raw credentials and private secret material stay outside the repository.",
            },
            "external_read": {"default": "approval-or-project-policy", "notes": "Docs, issue trackers, CI status, artifact metadata."},
            "external_write": {"default": "human-approval", "notes": "Issue updates, CI triggers, release status writes."},
            "credential_vault": {"default": "outside-repo", "notes": "Secrets live outside the repository, harness, sandbox, and generated governance files."},
            "credential_proxy": {"default": "approval-or-project-policy", "notes": "External calls use a broker/proxy that injects credentials without exposing raw values to the sandbox."},
            "release_or_signing": {"default": "human-driven", "notes": "Publishing, signing, production deploy, irreversible operations."},
        },
        "servers": [],
        "allowed_operations": [],
        "forbidden_operations": ["store credentials in repository", "silent destructive writes", "silent release or signing"],
    }


def resource_catalog_config(project_name: str, created_at: str, workspace_path: str) -> dict:
    verified_date = created_at[:10]
    return {
        "schema": "agent-resource-catalog-v1",
        "project_name": project_name,
        "created_at": created_at,
        "policy": {
            "repo_local_catalog": True,
            "raw_secret_values_forbidden": True,
            "private_addresses_may_use_refs": True,
            "local_secret_material_path": ".agent/local/resource-secrets.local.env",
            "local_secret_material_template": ".agent/templates/resource-secrets.local.env.tmpl",
            "local_secret_material_is_git_ignored": True,
            "match_requires_resolve_before_use": True,
            "high_risk_use_requires_approval": True,
            "production_write_requires_approval": True,
            "destructive_actions_forbidden_by_default": True,
            "record_high_risk_use_in_runlog": True,
            "healthcheck_default_max_risk": "low",
            "stale_after_days": 90,
        },
        "secret_ref_prefixes": ["env:", "file-ref:", "vault:", "proxy:", "op:", "keychain:"],
        "risk_values": ["low", "medium", "high", "critical"],
        "lifecycle_values": ["active", "planned", "disabled", "retired"],
        "action_policies": ["allowed", "approval-required", "forbidden"],
        "resource_types": {
            "repository": "Source code, release, mirror, or artifact repository.",
            "server": "Remote host, VM, bastion, service node, or deployment target.",
            "database": "Database service or connection target.",
            "compute": "Remote compute machine, GPU host, runner, or batch execution target.",
            "service": "HTTP, RPC, queue, cache, object store, or other network service.",
            "deployment": "Deploy environment, cluster, release target, or production operation boundary.",
            "credential-store": "External vault, proxy, or local ignored secret-material location.",
        },
        "resources": [
            {
                "id": "local-repository",
                "type": "repository",
                "environment": "local",
                "enabled": True,
                "aliases": ["workspace", f"{project_name} repo"],
                "intent_tags": ["code-edit", "validation", "governance-source"],
                "owner": "governance-owner",
                "risk": "medium",
                "lifecycle": "active",
                "description": "Authoritative local workspace for agent-governed project work.",
                "when_to_use": ["Edit or validate repository files.", "Inspect project-level agent-gov state."],
                "do_not_use_for": ["Storing secrets or private credentials."],
                "endpoint": {"path": workspace_path, "visibility": "workspace", "address_sensitivity": "internal"},
                "access": {"methods": ["filesystem", "git"], "credential_refs": [], "secret_material": "not-required"},
                "allowed_actions": {"read": "allowed", "write": "allowed", "destructive": "approval-required"},
                "health_checks": [{"id": "git-status", "command": "git status --short", "risk": "low"}],
                "last_verified": verified_date,
            },
            {
                "id": "staging-server-template",
                "type": "server",
                "environment": "staging",
                "enabled": False,
                "aliases": ["staging host"],
                "intent_tags": ["deploy-staging", "ssh-staging", "debug-service"],
                "owner": "project-owner",
                "risk": "medium",
                "lifecycle": "planned",
                "description": "Template entry for a staging server. Fill endpoint refs and credentials outside tracked files before enabling.",
                "when_to_use": ["Deploy or inspect staging services after the project owner fills local references."],
                "do_not_use_for": ["Production operations.", "Destructive host changes."],
                "endpoint": {
                    "host_ref": "env:STAGING_SERVER_HOST",
                    "port_ref": "env:STAGING_SERVER_SSH_PORT",
                    "visibility": "internal",
                    "address_sensitivity": "confidential",
                },
                "access": {
                    "methods": ["ssh"],
                    "credential_refs": ["env:STAGING_SERVER_USER", "file-ref:STAGING_SERVER_SSH_KEY"],
                    "secret_material": "local-template",
                },
                "allowed_actions": {"read": "allowed", "write": "approval-required", "destructive": "forbidden"},
                "health_checks": [],
                "last_verified": "",
            },
            {
                "id": "staging-database-template",
                "type": "database",
                "environment": "staging",
                "enabled": False,
                "aliases": ["staging db"],
                "intent_tags": ["debug-db", "migration-check", "staging-backend"],
                "owner": "project-owner",
                "risk": "medium",
                "lifecycle": "planned",
                "description": "Template entry for a staging database. Store only references in the catalog and real connection material outside tracked files.",
                "when_to_use": ["Validate staging migrations.", "Read staging data for debugging after approval policy is satisfied."],
                "do_not_use_for": ["Production repair.", "Destructive data operations."],
                "endpoint": {
                    "host_ref": "env:STAGING_DB_HOST",
                    "port_ref": "env:STAGING_DB_PORT",
                    "visibility": "internal",
                    "address_sensitivity": "confidential",
                },
                "access": {
                    "methods": ["psql"],
                    "credential_refs": ["env:STAGING_DATABASE_URL"],
                    "secret_material": "local-template",
                },
                "allowed_actions": {"read": "allowed", "write": "approval-required", "destructive": "forbidden"},
                "health_checks": [],
                "last_verified": "",
            },
            {
                "id": "remote-compute-template",
                "type": "compute",
                "environment": "shared",
                "enabled": False,
                "aliases": ["gpu machine", "remote runner"],
                "intent_tags": ["remote-compute", "gpu", "long-job"],
                "owner": "project-owner",
                "risk": "high",
                "lifecycle": "planned",
                "description": "Template entry for remote compute capacity. Enable only after cost, credential, and allowed-action boundaries are documented.",
                "when_to_use": ["Run approved remote compute jobs that cannot run locally."],
                "do_not_use_for": ["Unbounded cost jobs.", "Jobs that require undeclared credentials."],
                "endpoint": {
                    "host_ref": "env:REMOTE_COMPUTE_HOST",
                    "port_ref": "env:REMOTE_COMPUTE_SSH_PORT",
                    "visibility": "internal",
                    "address_sensitivity": "confidential",
                },
                "access": {
                    "methods": ["ssh"],
                    "credential_refs": ["env:REMOTE_COMPUTE_USER", "file-ref:REMOTE_COMPUTE_SSH_KEY"],
                    "secret_material": "local-template",
                },
                "allowed_actions": {"read": "allowed", "write": "approval-required", "destructive": "forbidden"},
                "health_checks": [],
                "last_verified": "",
            },
        ],
        "commands": {
            "doctor": "python3 scripts/agent_resources.py doctor",
            "list": "python3 scripts/agent_resources.py list",
            "match": "python3 scripts/agent_resources.py match --intent <intent> --json",
            "resolve": "python3 scripts/agent_resources.py resolve <resource-id> --json",
            "template": "python3 scripts/agent_resources.py template --print",
            "healthcheck": "python3 scripts/agent_resources.py healthcheck <resource-id>",
        },
    }


def governance_gc_config(project_name: str, created_at: str) -> dict:
    return {
        "schema": "agent-governance-gc-v1",
        "project_name": project_name,
        "created_at": created_at,
        "policy": {
            "periodic_review_cadence": "weekly",
            "doctor_is_non_destructive": True,
            "report_warnings_without_failing_by_default": True,
            "stale_docs_warn_after_days": 180,
            "active_tasks_warn_after_days": 30,
            "baseline_warn_after_days": 30,
        },
        "checks": {
            "knowledge_owners": True,
            "stale_docs": True,
            "task_board_stale_active_items": True,
            "baseline_age": True,
            "config_pointer_consistency": True,
            "dev_map_presence": True,
            "resource_catalog_schema": True,
            "mcp_policy_disabled_or_audited": True,
        },
        "commands": {
            "doctor": "python3 scripts/agent_gc.py doctor",
            "report": "python3 scripts/agent_gc.py report",
            "json": "python3 scripts/agent_gc.py report --json",
        },
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
            "procedural_memory_review_ref_can_point_to_promotion_bundle": True,
            "confirm_selected_memory_facts_against_truth_sources": True,
            "raw_diagnostic_material_stays_out_of_memory": True,
            "truth_sources_in_order": [
                ".agent/spec.json and openspec/",
                ".agent/task-board.json",
                "docs/DEV_MAP.md and .agent/dev-map.json",
                "docs/DOMAIN_GLOSSARY.md for shared project-domain terms",
                "docs/features/<task-id>/",
                "docs/adr/, docs/rfcs/, docs/incidents/",
                ".agent/runlog.jsonl and validation.md",
                ".agent/sessions/ for active handoff state",
                ".agent/memory/ summaries",
            ],
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
            "procedural_review_ref_may_be_knowledge_promotion_bundle": True,
            "do_not_promote_from_single_unverified_session": True,
        },
        "recall": {
            "max_chars_per_memory": 600,
            "max_total_chars": 4000,
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


def context_budget_config(project_name: str, created_at: str, governance_profile: str) -> dict:
    total_budget = 50000 if profile_at_least(governance_profile, "standard") else 40000
    agent_instruction_budget = 2200
    if profile_at_least(governance_profile, "full"):
        # Full profile tracks native adapters, subagents, security/tooling, and
        # skill distribution. Keep it bounded, but avoid shipping a scaffold
        # that immediately warns before the project has added any content.
        total_budget = 50000
        agent_instruction_budget = 2400
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
            ".agent/resources.json",
            ".agent/runtime-policy.json",
            ".agent/model-profiles.json",
            ".agent/agent-runtime.json",
            ".agent/skill-runtime.json",
            ".agent/manifest.json",
            ".agent/workflow.json",
            ".agent/workflow-profiles.json",
            ".agent/role-contracts.json",
            ".agent/risk-zones.json",
            ".agent/review-policy.json",
            ".agent/worktrees.json",
            ".agent/tooling.json",
            ".agent/security.json",
            ".agent/evals.json",
            ".agent/mechanical-checks.json",
            ".agent/baselines.json",
            ".agent/dev-map.json",
            ".agent/skill-hygiene.json",
            ".agent/harness-evolution.json",
            ".agent/mcp-policy.json",
            ".agent/governance-gc.json",
            ".agent/evals/latest.md",
            "docs/TOOLING.md",
            "docs/QUALITY_SCORE.md",
            "docs/DOMAIN_GLOSSARY.md",
            "docs/DEV_MAP.md",
            "docs/LOOP_ENGINEERING.md",
            "docs/RESOURCES.md",
            "docs/AGENT_RUNTIME_ARCHITECTURE.md",
            "docs/SKILL_RUNTIME.md",
            "docs/features/INDEX.md",
            "docs/adr/README.md",
            "docs/rfcs/README.md",
            "docs/incidents/README.md",
            ".agent/templates/subagent-task.md.tmpl",
            ".agent/templates/implementation-plan.md.tmpl",
            ".agent/templates/debugging-record.md.tmpl",
            ".agent/templates/project-review.md.tmpl",
            ".agent/templates/features/01_REQUIREMENT_ANALYSIS.md.tmpl",
            ".agent/templates/features/07_DELIVERY_SUMMARY.md.tmpl",
            "openspec/project.md",
        ],
        "tracked_globs": [
            "openspec/changes/*/proposal.md",
            "openspec/changes/*/design.md",
            "openspec/changes/*/tasks.md",
        ],
        "budgets": {
            "max_total_tracked_tokens": total_budget,
            "max_single_doc_tokens": 6000,
            "max_agent_instruction_tokens": agent_instruction_budget,
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
            "doctor_fails_on_budget_excess": True,
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
        "default_install_scope": "project",
        "project_codex_skill_dir": ".codex/skills",
        "global_codex_skill_dir": "~/.codex/skills",
        "preferred_codex_skill_dir": ".codex/skills",
        "legacy_codex_skill_dir": ".codex/skills",
        "claude_skill_dir": ".claude/skills",
        "sync_script": "scripts/agent_sync_skills.py",
        "policy": {
            "prefer_project_codex_skills": True,
            "global_install_requires_explicit_request": True,
            "all_installed_skills_are_governed": True,
            "prefer_agents_skills_for_codex": False,
            "preserve_legacy_codex_skills": True,
            "do_not_overwrite_without_force": True,
        },
    }


def skill_hygiene_config(project_name: str, created_at: str) -> dict:
    return {
        "schema": "agent-skill-hygiene-v1",
        "project_name": project_name,
        "created_at": created_at,
        "scan_roots": [
            ".agents/skills",
            ".codex/skills",
            ".claude/skills",
            ".cursor/skills",
            "~/.agents/skills",
            "~/.codex/skills",
            "~/.claude/skills",
            "~/.cursor/skills",
        ],
        "policy": {
            "doctor_is_read_only": True,
            "scripts_collect_facts_ai_interprets": True,
            "human_confirms_cleanup": True,
            "no_auto_delete": True,
            "do_not_treat_zero_canary_as_unused": True,
            "stale_after_days": 180,
            "report_symlinks_as_topology_not_duplicates": True,
        },
        "risk_signals": {
            "missing_frontmatter": "warning",
            "missing_name": "warning",
            "missing_description": "warning",
            "stale_mtime": "warning",
            "duplicate_or_drifted_skill_name": "warning",
            "broken_symlink": "error",
            "curl_pipe_shell": "error",
        },
        "canary": {
            "enabled": False,
            "meaning": "Canary evidence only proves the canary command ran; it does not prove skill discovery, full loading, compliance, or output quality.",
            "requires_explicit_user_confirmation": True,
        },
        "commands": {
            "doctor": "python3 scripts/agent_skill_hygiene.py doctor",
            "report": "python3 scripts/agent_skill_hygiene.py report",
            "json": "python3 scripts/agent_skill_hygiene.py report --json",
        },
    }


def project_skills_config(project_name: str, created_at: str) -> dict:
    return {
        "schema": "agent-project-skills-v1",
        "project_name": project_name,
        "created_at": created_at,
        "updated_at": created_at,
        "registry_inputs": {
            "skill_hygiene": ".agent/skill-hygiene.json",
            "production_manifest": "skills.manifest.json",
            "workspace_tools_manifest": "workspace-tools.manifest.json",
            "capabilities": ".agent/capabilities.json",
        },
        "policy": {
            "repo_local": True,
            "dependency_free": True,
            "no_auto_delete": True,
            "no_auto_install": True,
            "default_install_scope": "project",
            "global_install_requires_explicit_request": True,
            "scripts_collect_facts_ai_interprets": True,
            "requires_review_fix_review_for_lifecycle_changes": True,
            "archive_completed_skill_changes": True,
            "fail_on_unmanaged_project_skills": True,
            "fail_on_orphaned_project_skills": True,
            "fail_on_unmanaged_global_skills": True,
            "review_artifact_required": True,
            "destructive_delete_requires_explicit_user_approval": True,
            "do_not_merge_workspace_helpers_into_production_manifest": True,
        },
        "status_values": [
            "managed",
            "unmanaged",
            "orphaned",
            "missing",
            "drifted",
            "pinned",
            "unpinned",
            "unknown_source",
            "manifest_mismatch",
            "review_pending",
            "unsafe_path",
            "capability_mismatch",
            "global_unmanaged",
            "global_path_mismatch",
        ],
        "commands": {
            "doctor": "python3 scripts/agent_project_skills.py doctor",
            "report": "python3 scripts/agent_project_skills.py report",
            "json": "python3 scripts/agent_project_skills.py report --json",
            "snapshot": "python3 scripts/agent_project_skills.py snapshot",
            "snapshot_write": "python3 scripts/agent_project_skills.py snapshot --write",
            "check": "python3 scripts/agent_project_skills.py check <skill>",
        },
        "skills": {},
    }


def runtime_policy_config(project_name: str, created_at: str, intake: dict) -> dict:
    return {
        "schema": "agent-runtime-policy-v1",
        "project_name": project_name,
        "created_at": created_at,
        "architecture_contract": {
            "name": "Skill-first Runtime Architecture",
            "principles": [
                "Skill is the first-class ability boundary.",
                "Project target is selected before framework choice: agent, MCP server, hybrid, or library.",
                "Agent targets compose Skills and route work to runtime tools.",
                "MCP server targets expose governed tools, resources, or prompts to MCP clients.",
                "Runtime adapter or protocol SDK is replaceable and application-owned.",
                "Model profile is a replaceable access boundary, not application logic.",
                "Application state, user sessions, memory, traces, and product databases belong to the application layer, not agent-gov session state.",
                "agent-gov is the governance control plane and must remain dependency-free.",
            ],
        },
        "project_targets": {
            "selected": intake["project_target"],
            "allowed": sorted(PROJECT_TARGETS),
            "mcp_server_is_not_agent_subtype": True,
            "hybrid_requires_agent_and_mcp_boundaries": True,
        },
        "interview": {
            "source": intake["source"],
            "selection_status": intake["selection_status"],
            "questions": [
                {
                    "id": "project_target",
                    "question": "Is the deliverable an agent, an MCP server, a hybrid agent-plus-MCP system, or a library?",
                    "recommended_answer": "Classify MCP servers as `mcp-server` instead of forcing them into an agent runtime shape.",
                    "reason": "MCP server work is centered on governed tool/resource/prompt exposure to clients; agent work is centered on model-driven orchestration.",
                },
                {
                    "id": "skill_boundary",
                    "question": "Should every durable capability be packaged as a Skill?",
                    "recommended_answer": "Yes, use Skills as ability boundaries.",
                    "reason": "This keeps capabilities governable, reusable, reviewable, and testable across agents and MCP servers.",
                },
                {
                    "id": "model_providers",
                    "question": "Which model providers must the project support?",
                    "recommended_answer": "Declare Qwen and DeepSeek through OpenAI-compatible profiles, with optional LiteLLM routing.",
                    "reason": "Provider API shape alone does not prove tool calling, JSON, streaming, or reasoning behavior; profiles make those flags explicit.",
                },
                {
                    "id": "workflow_complexity",
                    "question": "Does the product agent need long-lived graph workflows or resumable state machines?",
                    "recommended_answer": "Use LangGraph only when this is explicitly needed.",
                    "reason": "Most Skill-first agents can start with a lighter runtime adapter and add graph orchestration later.",
                },
                {
                    "id": "typing_and_outputs",
                    "question": "Do tools require strong typing or strict structured outputs?",
                    "recommended_answer": "Use Pydantic AI as a typed tooling adapter when schemas become central.",
                    "reason": "Typed boundaries are useful for production tools, but should not become a hard dependency of agent-gov.",
                },
            ],
            "script_boundary": "The initializer consumes structured intake from --architecture-intake; it does not read chat history directly.",
        },
        "decision_rules": [
            {
                "when": ["skills_are_first_class"],
                "select": {"architecture_style": intake["architecture_style"], "default_runtime_adapter": intake["default_runtime_adapter"]},
            },
            {
                "when": ["project_target is mcp-server"],
                "select": {"models_required": False, "mcp_server_boundaries": "required"},
            },
            {
                "when": ["project_target is hybrid"],
                "select": {"models_required": True, "mcp_server_boundaries": "required"},
            },
            {
                "when": ["expected_model_providers includes qwen or deepseek"],
                "select": {"model_access_strategy": "openai-compatible-first", "model_gateway": "optional-litellm"},
            },
            {
                "when": ["structured_output_required"],
                "select": {"optional_runtime_adapter": "pydantic-ai"},
            },
            {
                "when": ["long_running_workflows"],
                "select": {"workflow_adapter": "langgraph-when-needed"},
            },
        ],
        "runtime_adapters": {
            "strands": {
                "role": "default-skill-runtime-adapter",
                "status": "recommended",
                "reason": "Closest fit for Agent Skills / SKILL.md oriented runtime activation while remaining an adapter, not the architecture standard.",
                "install_policy": "application-owned-dependency",
            },
            "pydantic-ai": {
                "role": "typed-tooling-and-structured-output-adapter",
                "status": "optional",
                "reason": "Useful for Python type-safe tools and structured outputs when product code needs strict contracts.",
                "install_policy": "application-owned-dependency",
            },
            "langgraph": {
                "role": "stateful-workflow-adapter",
                "status": "conditional",
                "reason": "Use for explicit graph workflows, resumable state machines, or complex multi-step orchestration.",
                "install_policy": "application-owned-dependency",
            },
            "mcp-server": {
                "role": "mcp-server-protocol-target",
                "status": "conditional",
                "reason": "Use when the product deliverable exposes tools, resources, or prompts to MCP clients rather than orchestrating an agent.",
                "install_policy": "application-owned-dependency",
            },
            "mcp-sdk-python": {
                "role": "python-mcp-sdk-adapter",
                "status": "optional",
                "reason": "Allowed for Python MCP server implementations when the application owns the dependency.",
                "install_policy": "application-owned-dependency",
            },
            "mcp-sdk-typescript": {
                "role": "typescript-mcp-sdk-adapter",
                "status": "optional",
                "reason": "Allowed for TypeScript MCP server implementations when the application owns the dependency.",
                "install_policy": "application-owned-dependency",
            },
            "fastmcp": {
                "role": "fastmcp-style-server-adapter",
                "status": "optional",
                "reason": "Allowed for lightweight MCP servers when the application owns the dependency and schema boundary.",
                "install_policy": "application-owned-dependency",
            },
            "custom": {
                "role": "project-defined-adapter",
                "status": "allowed",
                "reason": "Allowed when project constraints do not fit a recommended adapter.",
                "install_policy": "application-owned-dependency",
            },
        },
        "boundaries": {
            "agent_gov_must_not_import_runtime_frameworks": True,
            "runtime_dependencies_belong_to_application": True,
            "development_session_state_is_not_product_runtime_state": True,
            "raw_model_credentials_forbidden_in_repo": True,
            "model_capabilities_must_be_explicit": True,
            "mcp_server_credentials_forbidden_in_repo": True,
            "mcp_destructive_tools_require_human_approval": True,
        },
        "commands": {
            "doctor": "python3 scripts/agent_runtime.py doctor",
            "report": "python3 scripts/agent_runtime.py report",
            "interview": "python3 scripts/agent_runtime.py interview",
        },
    }


def model_profile(
    profile_id: str,
    provider: str,
    *,
    enabled: bool,
    base_url_ref: str,
    api_key_ref: str,
    model_ref: str,
    notes: str,
) -> dict:
    return {
        "id": profile_id,
        "provider": provider,
        "enabled": enabled,
        "access": {
            "api_style": "openai-compatible" if profile_id != "litellm-gateway" else "litellm",
            "base_url_ref": base_url_ref,
            "api_key_ref": api_key_ref,
            "model_ref": model_ref,
        },
        "capabilities": {
            "chat": True,
            "tool_calling": "verify-before-production",
            "structured_output": "verify-before-production",
            "streaming": "verify-before-production",
            "reasoning": "provider-model-specific",
            "embeddings": False,
            "multimodal": "provider-model-specific",
        },
        "policy": {
            "raw_credentials_forbidden": True,
            "do_not_infer_capabilities_from_api_shape": True,
            "record_model_changes_in_runtime_config": True,
        },
        "notes": notes,
    }


def model_profiles_config(project_name: str, created_at: str, intake: dict) -> dict:
    selected = set(intake["selected_model_profiles"])
    profiles = [
        model_profile(
            "qwen",
            "qwen",
            enabled="qwen" in selected,
            base_url_ref="env:QWEN_OPENAI_BASE_URL",
            api_key_ref="env:QWEN_API_KEY",
            model_ref="env:QWEN_MODEL",
            notes="Use Alibaba/Qwen OpenAI-compatible API or an approved project proxy. Verify tool calling and structured output per selected model.",
        ),
        model_profile(
            "deepseek",
            "deepseek",
            enabled="deepseek" in selected,
            base_url_ref="env:DEEPSEEK_OPENAI_BASE_URL",
            api_key_ref="env:DEEPSEEK_API_KEY",
            model_ref="env:DEEPSEEK_MODEL",
            notes="Use DeepSeek OpenAI-compatible API or an approved project proxy. Verify model aliases and reasoning/tool behavior before production.",
        ),
        model_profile(
            "openai",
            "openai",
            enabled="openai" in selected,
            base_url_ref="env:OPENAI_BASE_URL",
            api_key_ref="env:OPENAI_API_KEY",
            model_ref="env:OPENAI_MODEL",
            notes="Optional OpenAI profile for projects that use OpenAI directly or as a compatibility baseline.",
        ),
        model_profile(
            "local-openai-compatible",
            "local",
            enabled="local-openai-compatible" in selected,
            base_url_ref="env:LOCAL_OPENAI_BASE_URL",
            api_key_ref="env:LOCAL_OPENAI_API_KEY",
            model_ref="env:LOCAL_OPENAI_MODEL",
            notes="Use for Ollama, vLLM, SGLang, or an internal OpenAI-compatible endpoint. Capability flags must be verified per deployment.",
        ),
        model_profile(
            "litellm-gateway",
            "litellm",
            enabled="litellm-gateway" in selected or intake["model_access_strategy"] == "litellm-gateway",
            base_url_ref="env:LITELLM_BASE_URL",
            api_key_ref="env:LITELLM_API_KEY",
            model_ref="env:LITELLM_MODEL",
            notes="Optional routing gateway profile. Keep provider credentials behind LiteLLM or a project proxy, not in repository files.",
        ),
    ]
    return {
        "schema": "agent-model-profiles-v1",
        "project_name": project_name,
        "created_at": created_at,
        "secret_ref_prefixes": list(SECRET_REF_PREFIXES),
        "policy": {
            "raw_credentials_forbidden": True,
            "base_urls_may_be_public_or_ref": True,
            "private_base_urls_should_use_refs": True,
            "capabilities_require_verification": True,
            "openai_compatible_does_not_imply_tool_parity": True,
        },
        "profiles": profiles,
    }


def agent_runtime_config(project_name: str, created_at: str, intake: dict) -> dict:
    selected_model_profiles = intake["selected_model_profiles"]
    return {
        "schema": "agent-runtime-selection-v1",
        "project_name": project_name,
        "created_at": created_at,
        "selection_status": intake["selection_status"],
        "project_target": intake["project_target"],
        "architecture_style": intake["architecture_style"],
        "project_purpose": intake["project_purpose"],
        "skill_registry": {
            "project_skills": ".agent/project-skills.json",
            "codex_skills_dir": ".codex/skills",
            "production_manifest": "skills.manifest.json",
            "skill_runtime_manifest_name": "skill-runtime.json",
            "policy": {
                "skill_is_ability_boundary": True,
                "skill_md_is_instruction_not_callable_tool": True,
                "callable_tools_require_explicit_schema": True,
            },
        },
        "runtime": {
            "default_adapter": intake["default_runtime_adapter"],
            "optional_adapters": intake["optional_runtime_adapters"],
            "allowed_adapters": sorted(RUNTIME_ADAPTERS),
            "adapter_policy": {
                "strands_is_default_adapter_not_architecture_standard": True,
                "runtime_dependencies_are_application_owned": True,
                "agent_gov_doctor_does_not_import_runtime_frameworks": True,
            },
        },
        "models": {
            "required": intake["model_profiles_required"],
            "access_strategy": intake["model_access_strategy"],
            "selected_profiles": selected_model_profiles,
            "profiles_file": ".agent/model-profiles.json",
            "gateway": "optional-litellm"
            if intake["model_access_strategy"] in {"openai-compatible-first", "litellm-gateway"}
            else "project-defined",
        },
        "mcp_server": intake["mcp_server"],
        "application_state": {
            "owner": "application",
            "do_not_store_product_runtime_state_in_agent_gov_sessions": True,
            "development_session_state": ".agent/sessions",
            "recommended_product_state": ["database", "queue", "object store", "trace store", "application logs"],
        },
        "initialization_intake": intake,
        "docs": {
            "architecture": "docs/AGENT_RUNTIME_ARCHITECTURE.md",
            "resources": "docs/RESOURCES.md",
            "skills": ".agent/project-skills.json",
        },
        "commands": {
            "doctor": "python3 scripts/agent_runtime.py doctor",
            "report": "python3 scripts/agent_runtime.py report --json",
        },
    }


def skill_runtime_config(project_name: str, created_at: str) -> dict:
    return {
        "schema": "agent-skill-runtime-v1",
        "project_name": project_name,
        "created_at": created_at,
        "source_evidence": [
            {
                "source": "DietrichGebert/ponytail",
                "status": "verified",
                "evidence": [
                    "skills/*/SKILL.md",
                    "commands/*.toml",
                    "hooks/ponytail-*.js",
                    "docs/agent-portability.md",
                    "docs/platform-native.md",
                    "scripts/check-rule-copies.js",
                    "benchmarks/agentic/README.md",
                ],
                "adopted_as": "Portable skill/runtime governance patterns, not product persona or source-specific command names.",
            },
            {
                "source": "WeChat article URLs supplied by user on 2026-07-01",
                "status": "blocked",
                "evidence": ["extraction returned generic WeChat shell pages without article title/body"],
                "adopted_as": "No governance rules derived until accessible content is supplied.",
            },
        ],
        "canonical_core": {
            "principle": "Durable behavior lives in one canonical skill core; host adapters are projections and must not fork policy.",
            "path_patterns": ["SKILL.md", "AGENTS.md", "references/", "scripts/", "assets/"],
            "core_files_are_authoritative": True,
            "adapters_must_be_thin": True,
            "do_not_duplicate_behavior_in_host_adapters": True,
            "manual_adapter_edits_require_merge_note": True,
        },
        "host_adapters": {
            "adapter_targets": [
                {
                    "host": "codex",
                    "path_patterns": [".codex/skills/*/SKILL.md", ".codex/config.toml", ".codex/hooks.json", ".codex/agents/*.toml"],
                    "capability_tier": "native-skill-or-project-adapter",
                    "projection_type": "skill-core-plus-native-config",
                    "parity_check": "manifest/hash/invariant check or manual merge note required before release claims",
                },
                {
                    "host": "claude",
                    "path_patterns": ["CLAUDE.md", ".claude/settings.json", ".claude/agents/*.md"],
                    "capability_tier": "native-instruction-or-subagent-adapter",
                    "projection_type": "thin instruction projection",
                    "parity_check": "canonical rule invariants must remain aligned with AGENTS.md and project skills",
                },
                {
                    "host": "generic-agent",
                    "path_patterns": ["AGENTS.md", "skills/*/SKILL.md"],
                    "capability_tier": "instruction-tier",
                    "projection_type": "always-on instructions or direct skill loading",
                    "parity_check": "AGENTS.md stays compact and links to durable docs instead of copying volatile policy",
                },
                {
                    "host": "mcp-client",
                    "path_patterns": [".agent/agent-runtime.json", ".agent/mcp-policy.json", "skills.manifest.json"],
                    "capability_tier": "protocol-contract-tier",
                    "projection_type": "explicit tool/resource/prompt contract",
                    "parity_check": "do not expose raw SKILL.md as a callable tool without schema and resource boundaries",
                },
            ],
            "parity_policy": {
                "canonical_source_required": True,
                "adapter_drift_must_be_detected": True,
                "allowed_parity_methods": ["content_hash", "invariant_phrases", "generated_projection", "manual_merge_note"],
                "release_claim_requires_parity_evidence": True,
                "hook_projection_boundary_required": True,
                "orphaned_hook_files_are_findings": True,
                "empty_hooks_object_may_suppress_autodiscovery": True,
            },
        },
        "runtime_modes": {
            "allowed_modes": ["off", "advisory", "standard", "strict", "audit-only"],
            "default_mode": "standard",
            "deactivation_mode": "off",
            "persistence": {
                "mode_state_location_policy": "host-owned state or ignored local files only",
                "repo_committed_state_forbidden": True,
                "raw_secret_state_forbidden": True,
            },
            "switch_command_pattern": "/<skill> <mode> or a host-native command that maps to a declared command lane",
            "activation_events": ["session-start", "turn-start", "explicit-command"],
            "fallback_behavior": "If hooks or host commands fail, keep the canonical Skill usable as normal instructions and report degraded native activation.",
            "hook_boundaries": {
                "read_only_by_default": True,
                "may_write_only_mode_state": True,
                "stdin_must_not_deadlock": True,
                "stdin_errors_degrade_safely": True,
                "strip_utf8_bom_before_json_parse": True,
                "valid_json_required_when_host_requires_json": True,
                "preserve_empty_additional_context": True,
                "invalid_mandatory_output_exits_nonzero": True,
                "allowed_outputs": ["additional context", "system message", "status line", "hookSpecificOutput JSON", "no-op JSON"],
                "failure_degrades_safely": True,
                "hook_must_not_store_secrets": True,
            },
        },
        "command_lanes": {
            "mode_switch": {
                "description": "Switch or disable runtime intensity/mode.",
                "lane_type": "persistent-state-changing",
                "read_only": False,
                "persistent": True,
                "requires_deactivation_behavior": True,
            },
            "complexity_review": {
                "description": "Review current changes for unnecessary complexity only.",
                "lane_type": "review-only",
                "read_only": True,
                "persistent": False,
                "finding_tags": ["delete", "reuse", "stdlib", "native", "existing-dependency", "yagni", "shrink", "defer"],
            },
            "repository_audit": {
                "description": "Audit the whole repository for overbuild, duplication, or avoidable dependencies.",
                "lane_type": "review-only",
                "read_only": True,
                "persistent": False,
                "scope": "whole-repository",
            },
            "debt_harvest": {
                "description": "Harvest deliberate simplification markers into a ledger.",
                "lane_type": "read-only-by-default",
                "read_only": True,
                "persistent": "only-when-user-requests-ledger-write",
                "ledger_targets": ["docs/tech-debt.md", "docs/features/<task-id>/", "project-declared debt file"],
            },
            "impact_scoreboard": {
                "description": "Report measured skill impact from benchmark artifacts without inventing live-repo savings.",
                "lane_type": "report-only",
                "read_only": True,
                "persistent": False,
            },
            "help_status": {
                "description": "Show active modes, commands, boundaries, and local validation entry points.",
                "lane_type": "report-only",
                "read_only": True,
                "persistent": False,
            },
        },
        "review_lanes": {
            "spec_compliance": {
                "scope": "requested behavior, spec deltas, missing behavior, extra behavior",
                "may_fix": False,
            },
            "quality_security": {
                "scope": "maintainability, tests, security, privacy, data-loss handling, accessibility, performance",
                "may_fix": False,
            },
            "complexity_only": {
                "scope": "delete, reuse, stdlib/native replacement, existing dependency replacement, shrink, defer",
                "may_fix": False,
                "forbidden_findings": ["correctness", "security", "privacy", "data-loss", "accessibility"],
                "route_forbidden_findings_to": "quality_security",
            },
            "debt_ledger": {
                "scope": "deliberate simplification markers, ceilings, upgrade triggers, owner/location",
                "may_fix": False,
            },
            "impact_benchmark": {
                "scope": "baseline arm, skill-enabled arm, contamination checks, correctness/safety gates, artifacts, limitations",
                "may_fix": False,
            },
        },
        "impact_benchmarks": {
            "policy": {
                "baseline_arm_required": True,
                "skill_enabled_arm_required": True,
                "isolated_workspaces_or_plugin_dirs_required": True,
                "pinned_tasks_or_repos_required": True,
                "contamination_selftest_required": True,
                "correctness_or_safety_gate_required": True,
                "preserve_outputs": True,
                "record_limitations": True,
                "reduction_claims_must_not_drop_safety_or_requirements": True,
            },
            "metrics": ["correctness", "safety", "completeness", "source_loc", "source_files", "cost", "duration", "turns", "review_findings"],
            "honesty_boundary": "Do not claim per-repo savings without a real baseline; report benchmark scope and limitations with every impact claim.",
            "artifact_paths": ["evals/", ".agent/evals/latest.md", "skillflows/<skill>/reviews/", "docs/features/<task-id>/"],
        },
        "shortcut_debt": {
            "marker": "agent-gov-debt:",
            "allowed_comment_prefixes": ["#", "//", "/*", "<!--"],
            "required_fields": ["ceiling", "upgrade_trigger"],
            "optional_fields": ["owner", "created_at", "evidence"],
            "read_only_harvest_by_default": True,
            "missing_upgrade_trigger_is_finding": True,
            "ledger_targets": ["docs/tech-debt.md", "docs/features/<task-id>/", "project-declared debt file"],
        },
        "dependency_policy": {
            "local_doctors_dependency_free": True,
            "python_standard_library_only_for_generated_checks": True,
            "no_network_required_for_doctor": True,
            "no_global_plugin_state_required_for_doctor": True,
            "external_benchmarks_are_optional_and_must_be_declared": True,
        },
    }


def init_runlog_event(project_name: str, created_at: str) -> dict:
    event_suffix = created_at.replace("-", "").replace(":", "").replace("T", "-").replace("Z", "")
    return {
        "schema": "agent-runlog-event-v1",
        "id": f"run-init-{event_suffix}",
        "trace_id": "agent-gov-init",
        "created_at": created_at,
        "kind": "governance-init",
        "outcome": "pass",
        "summary": f"Initialized agent-gov governance scaffold for {project_name}.",
        "session_id": None,
        "command": "init_agent_project.py",
        "source": "agent-gov",
        "tags": ["init", "governance"],
        "artifacts": ["AGENTS.md", ".agent/config.json", ".agent/harness.json"],
    }


def capabilities_config(
    project_name: str,
    created_at: str,
    openspec_enabled: bool,
    claude_enabled: bool,
    governance_profile: str,
) -> dict:
    capabilities = [
        {
            "id": "repo-filesystem",
            "kind": "resource",
            "provider": "local",
            "enabled": True,
            "risk": "medium",
            "owner": "governance-owner",
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
            "owner": "governance-owner",
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
            "owner": "governance-owner",
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
            "owner": "governance-owner",
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
            "owner": "governance-owner",
            "description": "Lifecycle gates for spec, plan, implementation, isolation, tests, reviews, and completion evidence.",
            "permissions": {"read": True, "write": False, "network": False, "secrets": False},
            "validation": ["python3 scripts/agent_check.py"],
        },
        {
            "id": "workflow-profiles",
            "kind": "policy",
            "provider": "local",
            "enabled": True,
            "risk": "medium",
            "owner": "governance-owner",
            "description": "Task-size-aware workflow profiles for light tiny work and evidence-rich full work.",
            "permissions": {"read": True, "write": "bounded", "network": False, "secrets": False},
            "validation": ["python3 scripts/agent_check.py", "python3 scripts/agent_score.py doctor"],
        },
        {
            "id": "loop-engineering",
            "kind": "policy",
            "provider": "local",
            "enabled": True,
            "risk": "medium",
            "owner": "governance-owner",
            "description": "Bounded agent work-loop policy for goals, observation signals, iteration budgets, stop conditions, evidence, and escalation.",
            "permissions": {"read": True, "write": False, "network": False, "secrets": False},
            "validation": ["python3 scripts/agent_check.py", "python3 scripts/agent_score.py doctor"],
        },
        {
            "id": "task-board",
            "kind": "tool",
            "provider": "agent-gov",
            "enabled": True,
            "risk": "medium",
            "owner": "governance-owner",
            "description": "Repo-local cross-session task index with feature document scaffolding.",
            "permissions": {"read": True, "write": "bounded", "network": False, "secrets": False},
            "validation": ["python3 scripts/agent_task.py doctor"],
        },
        {
            "id": "role-contracts",
            "kind": "policy",
            "provider": "local",
            "enabled": True,
            "risk": "medium",
            "owner": "governance-owner",
            "description": "Machine-checkable role contracts and finder-cannot-fix separation.",
            "permissions": {"read": True, "write": False, "network": False, "secrets": False},
            "validation": ["python3 scripts/agent_check.py"],
        },
        {
            "id": "implementation-discipline",
            "kind": "policy",
            "provider": "local",
            "enabled": True,
            "risk": "medium",
            "owner": "governance-owner",
            "description": "Simplicity-first rules for assumptions, abstractions, diff scope, and success criteria.",
            "permissions": {"read": True, "write": False, "network": False, "secrets": False},
            "validation": ["python3 scripts/agent_check.py", "python3 scripts/agent_score.py doctor"],
        },
        {
            "id": "requirements-interview",
            "kind": "policy",
            "provider": "local",
            "enabled": True,
            "risk": "medium",
            "owner": "governance-owner",
            "description": "One-question-at-a-time intake with recommended answers and code/docs cross-checks.",
            "permissions": {"read": True, "write": "bounded", "network": False, "secrets": False},
            "validation": ["python3 scripts/agent_task.py doctor", "python3 scripts/agent_check.py"],
        },
        {
            "id": "worktree-isolation",
            "kind": "policy",
            "provider": "git",
            "enabled": True,
            "risk": "medium",
            "owner": "governance-owner",
            "description": "Preferred isolated worktree policy with baseline validation and guarded cleanup.",
            "permissions": {"read": True, "write": "bounded", "network": False, "secrets": False},
            "validation": ["git worktree list", "git status --short"],
        },
        {
            "id": "aci-tooling",
            "kind": "tool",
            "provider": "local",
            "enabled": True,
            "risk": "low",
            "owner": "governance-owner",
            "description": "Bounded file listing, reading, and search with explicit output limits.",
            "permissions": {"read": True, "write": False, "network": False, "secrets": False},
            "validation": ["python3 scripts/agent_tooling.py doctor"],
        },
        {
            "id": "security-baseline",
            "kind": "tool",
            "provider": "local",
            "enabled": True,
            "risk": "medium",
            "owner": "governance-owner",
            "description": "Optional policy, secret, dependency, SBOM, and license scan command slots.",
            "permissions": {"read": True, "write": False, "network": "project-defined", "secrets": False},
            "validation": ["python3 scripts/agent_security.py doctor"],
        },
        {
            "id": "governance-score",
            "kind": "tool",
            "provider": "local",
            "enabled": True,
            "risk": "low",
            "owner": "governance-owner",
            "description": "Deterministic governance score over local project state.",
            "permissions": {"read": True, "write": "bounded", "network": False, "secrets": False},
            "validation": ["python3 scripts/agent_score.py doctor"],
        },
        {
            "id": "mechanical-verification",
            "kind": "tool",
            "provider": "agent-gov",
            "enabled": True,
            "risk": "medium",
            "owner": "governance-owner",
            "description": "Hard checks and before/after baselines for JSON, paths, roles, tasks, and links.",
            "permissions": {"read": True, "write": "bounded", "network": False, "secrets": False},
            "validation": ["python3 scripts/agent_verify.py doctor"],
        },
        {
            "id": "skill-hygiene",
            "kind": "tool",
            "provider": "agent-gov",
            "enabled": True,
            "risk": "medium",
            "owner": "governance-owner",
            "description": "Read-only local skill topology, hash, frontmatter, stale, and risk scan.",
            "permissions": {"read": True, "write": False, "network": False, "secrets": False},
            "validation": ["python3 scripts/agent_skill_hygiene.py doctor"],
        },
        {
            "id": "project-skill-governance",
            "kind": "tool",
            "provider": "agent-gov",
            "enabled": True,
            "risk": "medium",
            "owner": "governance-owner",
            "description": "Repo-local skill registry, provenance, drift, manifest, and lifecycle reporting.",
            "permissions": {"read": True, "write": "bounded", "network": False, "secrets": False},
            "validation": ["python3 scripts/agent_project_skills.py doctor"],
        },
        {
            "id": "resource-catalog",
            "kind": "resource",
            "provider": "agent-gov",
            "enabled": True,
            "risk": "high",
            "owner": "governance-owner",
            "description": "Repo-local resource catalog for servers, databases, remotes, compute, deployments, secret refs, match, resolve, and healthchecks.",
            "permissions": {"read": True, "write": "bounded", "network": "declared-resource-only", "secrets": False},
            "validation": [
                "python3 scripts/agent_resources.py doctor",
                "python3 scripts/agent_resources.py match --intent \"deploy staging backend\" --include-disabled --json",
            ],
        },
        {
            "id": "agent-runtime-architecture",
            "kind": "policy",
            "provider": "agent-gov",
            "enabled": True,
            "risk": "medium",
            "owner": "governance-owner",
            "description": "Skill-first runtime architecture, project target selection, MCP server boundaries, model profiles, adapter selection, and initialization intake.",
            "permissions": {"read": True, "write": "bounded", "network": False, "secrets": False},
            "validation": ["python3 scripts/agent_runtime.py doctor"],
        },
        {
            "id": "skill-runtime-governance",
            "kind": "policy",
            "provider": "agent-gov",
            "enabled": True,
            "risk": "medium",
            "owner": "governance-owner",
            "description": "Portable Skill/plugin runtime governance for canonical cores, thin adapters, modes, command lanes, review lanes, benchmarks, and debt ledgers.",
            "permissions": {"read": True, "write": "bounded", "network": False, "secrets": False},
            "validation": ["python3 scripts/agent_verify.py doctor", "python3 scripts/agent_score.py doctor"],
        },
        {
            "id": "dev-map",
            "kind": "knowledge",
            "provider": "local",
            "enabled": True,
            "risk": "low",
            "owner": "governance-owner",
            "description": "Repository navigation map for entry points, ownership, and common patterns.",
            "permissions": {"read": True, "write": "bounded", "network": False, "secrets": False},
            "validation": ["test -f docs/DEV_MAP.md", "python3 scripts/agent_gc.py doctor"],
        },
        {
            "id": "harness-evolution",
            "kind": "policy",
            "provider": "agent-gov",
            "enabled": True,
            "risk": "medium",
            "owner": "governance-owner",
            "description": "Incident taxonomy for promoting repeated failures into rules, skills, scripts, gates, tools, or docs.",
            "permissions": {"read": True, "write": "bounded", "network": False, "secrets": False},
            "validation": ["python3 scripts/agent_gc.py doctor"],
        },
        {
            "id": "mcp-policy",
            "kind": "mcp",
            "provider": "project-defined",
            "enabled": False,
            "risk": "medium",
            "owner": "governance-owner",
            "description": "Optional MCP trust-boundary policy for systems, credentials, audit, and approvals.",
            "permissions": {"read": "project-defined", "write": "approval-required", "network": "project-defined", "secrets": False},
            "validation": ["python3 scripts/agent_gc.py doctor"],
        },
        {
            "id": "governance-gc",
            "kind": "tool",
            "provider": "agent-gov",
            "enabled": True,
            "risk": "low",
            "owner": "governance-owner",
            "description": "Periodic governance gardening for stale docs, tasks, baselines, drift, and owner gaps.",
            "permissions": {"read": True, "write": False, "network": False, "secrets": False},
            "validation": ["python3 scripts/agent_gc.py doctor"],
        },
        {
            "id": "decision-records",
            "kind": "resource",
            "provider": "local",
            "enabled": True,
            "risk": "low",
            "owner": "governance-owner",
            "description": "ADR, RFC, and incident templates for durable decisions and reliability learning.",
            "permissions": {"read": True, "write": "bounded", "network": False, "secrets": False},
            "validation": ["test -d docs/adr && test -d docs/rfcs && test -d docs/incidents"],
        },
        {
            "id": "session-memory",
            "kind": "resource",
            "provider": "local",
            "enabled": True,
            "risk": "medium",
            "owner": "governance-owner",
            "description": "Repo-local session continuity and memory summaries.",
            "permissions": {"read": True, "write": "bounded", "network": False, "secrets": False},
            "validation": ["python3 .agent/tools/agent_memory.py doctor"],
        },
        {
            "id": "context-budget",
            "kind": "tool",
            "provider": "local",
            "enabled": True,
            "risk": "low",
            "owner": "governance-owner",
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
            "owner": "governance-owner",
            "description": "Permission-gated delegated roles, boundaries, and snapshot contract.",
            "permissions": {"read": True, "write": False, "network": False, "secrets": False},
            "validation": ["python3 scripts/agent_check.py"],
        },
        {
            "id": "native-hooks",
            "kind": "adapter",
            "provider": "codex-claude",
            "enabled": True,
            "risk": "medium",
            "owner": "governance-owner",
            "description": "Advisory native hooks for bootstrap and checkpoint reminders.",
            "permissions": {"read": True, "write": "bounded", "network": False, "secrets": False},
            "validation": ["python3 .agent/tools/governance_hook.py --event session-start"],
        },
        {
            "id": "claude-native-adapters",
            "kind": "adapter",
            "provider": "claude",
            "enabled": claude_enabled,
            "risk": "medium",
            "owner": "governance-owner",
            "description": "Claude settings and subagent projections when enabled.",
            "permissions": {"read": True, "write": "bounded", "network": False, "secrets": False},
            "validation": ["python3 scripts/agent_check.py"],
        },
        {
            "id": "skill-distribution",
            "kind": "skill",
            "provider": "agent-gov",
            "enabled": True,
            "risk": "medium",
            "owner": "governance-owner",
            "description": "Repo-local skill mirroring and distribution policy.",
            "permissions": {"read": True, "write": "bounded", "network": False, "secrets": False},
            "validation": ["python3 scripts/agent_sync_skills.py --dry-run"],
        },
        {
            "id": "ai-coding-glossary",
            "kind": "knowledge",
            "provider": "local",
            "enabled": True,
            "risk": "low",
            "owner": "governance-owner",
            "description": "Shared AI coding terminology for agents, reviewers, and maintainers.",
            "permissions": {"read": True, "write": "bounded", "network": False, "secrets": False},
            "validation": ["test -f docs/AI_CODING_GLOSSARY.md"],
        },
        {
            "id": "domain-glossary",
            "kind": "knowledge",
            "provider": "local",
            "enabled": True,
            "risk": "low",
            "owner": "governance-owner",
            "description": "Project-domain terms, canonical names, forbidden synonyms, and source evidence.",
            "permissions": {"read": True, "write": "bounded", "network": False, "secrets": False},
            "validation": ["test -f docs/DOMAIN_GLOSSARY.md"],
        },
    ]
    capability_classes = {
        "instruction": {
            "description": "Agent-readable rules, skills, docs, policies, templates, specs, and glossaries.",
            "examples": ["AGENTS.md", "SKILL.md", ".agent/workflow.json", "docs/AI_CODING_GLOSSARY.md"],
        },
        "executable": {
            "description": "Commands, scripts, local CLIs, validation harnesses, and checks.",
            "examples": ["scripts/agent_check.py", "scripts/agent_validate.py", "git status --short"],
        },
        "integration": {
            "description": "Repository resources, external MCP servers, project-owned MCP server surfaces, APIs, databases, browsers, and networked systems.",
            "examples": ["repo filesystem", "external mcp server", "project-owned mcp server", "external issue tracker"],
        },
        "native_adapter": {
            "description": "Client-specific projections of neutral .agent governance policy.",
            "examples": [".codex/hooks.json", ".codex/agents/*.toml", ".claude/agents/*.md"],
        },
    }
    class_by_id = {
        "repo-filesystem": "integration",
        "git-worktree": "executable",
        "agent-spec": "executable",
        "harness-validation": "executable",
        "workflow-governance": "instruction",
        "workflow-profiles": "instruction",
        "task-board": "executable",
        "role-contracts": "instruction",
        "implementation-discipline": "instruction",
        "requirements-interview": "instruction",
        "worktree-isolation": "instruction",
        "aci-tooling": "executable",
        "security-baseline": "executable",
        "governance-score": "executable",
        "mechanical-verification": "executable",
        "skill-hygiene": "executable",
        "project-skill-governance": "executable",
        "resource-catalog": "integration",
        "agent-runtime-architecture": "instruction",
        "skill-runtime-governance": "instruction",
        "dev-map": "instruction",
        "harness-evolution": "instruction",
        "mcp-policy": "integration",
        "governance-gc": "executable",
        "decision-records": "instruction",
        "session-memory": "executable",
        "context-budget": "executable",
        "subagent-orchestration": "instruction",
        "native-hooks": "native_adapter",
        "claude-native-adapters": "native_adapter",
        "skill-distribution": "instruction",
        "ai-coding-glossary": "instruction",
        "domain-glossary": "instruction",
    }
    standard_capabilities = {
        "repo-filesystem",
        "git-worktree",
        "agent-spec",
        "harness-validation",
        "workflow-governance",
        "workflow-profiles",
        "task-board",
        "role-contracts",
        "implementation-discipline",
        "requirements-interview",
        "worktree-isolation",
        "governance-score",
        "mechanical-verification",
        "skill-hygiene",
        "project-skill-governance",
        "resource-catalog",
        "agent-runtime-architecture",
        "skill-runtime-governance",
        "dev-map",
        "harness-evolution",
        "mcp-policy",
        "governance-gc",
        "decision-records",
        "session-memory",
        "context-budget",
        "ai-coding-glossary",
        "domain-glossary",
    }
    full_capabilities = set(class_by_id)
    allowed = full_capabilities if profile_at_least(governance_profile, "full") else standard_capabilities
    capabilities = [item for item in capabilities if item["id"] in allowed]
    for item in capabilities:
        item["capability_class"] = class_by_id.get(item["id"], "instruction")
    return {
        "schema": "agent-capabilities-v1",
        "project_name": project_name,
        "created_at": created_at,
        "capability_classes": capability_classes,
        "policy": {
            "registry_is_advisory": True,
            "confirm_current_state_before_use": True,
            "default_external_network": "deny-unless-user-or-project-allows",
            "record_high_risk_tool_use_in_runlog": True,
            "do_not_store_secrets": True,
            "classify_skill_tool_mcp_before_enabling": True,
        },
        "taxonomy": {
            "skill": "Instruction package loaded by the agent as guidance.",
            "tool": "Executable command or callable function with permissions, risk, owner, and validation.",
            "mcp": "Protocol-backed MCP surface. External MCP integrations require trust and data boundaries; project-owned MCP servers require explicit tool/resource/prompt contracts.",
            "adapter": "Client-native projection of neutral governance policy.",
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
            "raw_credentials_stay_outside_repo_harness_and_sandbox": True,
            "external_secret_use_requires_vault_or_proxy_boundary": True,
            "resource_catalog_must_not_store_raw_secret_values": True,
            "do_not_read_secret_contents": True,
            "sensitive_path_scan_in_doctor": True,
            "sensitive_path_scan_limit": 100,
            "doctor_fails_on_sensitive_paths": True,
            "review_high_risk_findings_before_handoff": True,
        },
        "suites": {
            "policy_as_code": ["python3 scripts/agent_security.py scan-paths --fail-on-findings", "python3 scripts/agent_resources.py doctor"],
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
            "scan_paths": "python3 scripts/agent_security.py scan-paths --fail-on-findings",
            "run": "python3 scripts/agent_security.py run <suite>",
        },
    }


def evals_config(project_name: str, created_at: str, governance_profile: str) -> dict:
    dimensions = {
        "project_integrity": {"weight": 12},
        "required_paths": {"weight": 16},
        "validation": {"weight": 10},
        "session_continuity": {"weight": 8},
        "session_offload": {"weight": 8},
        "runlog": {"weight": 6},
    }
    if profile_at_least(governance_profile, "standard"):
        dimensions.update(
            {
                "workflow_profiles": {"weight": 8},
                "loop_engineering": {"weight": 6},
                "task_board": {"weight": 8},
                "role_contracts": {"weight": 8},
                "mechanical_verification": {"weight": 10},
                "dev_map": {"weight": 6},
                "skill_hygiene": {"weight": 6},
                "project_skills": {"weight": 6},
                "resource_catalog": {"weight": 8},
                "agent_runtime_architecture": {"weight": 8},
                "skill_runtime": {"weight": 8},
                "harness_evolution": {"weight": 6},
                "mcp_policy": {"weight": 4},
                "governance_gc": {"weight": 6},
                "implementation_discipline": {"weight": 8},
                "risk_governance": {"weight": 8},
                "review_policy": {"weight": 8},
                "context_budget": {"weight": 8},
                "memory": {"weight": 8},
                "capabilities": {"weight": 8},
                "security": {"weight": 8},
                "knowledge": {"weight": 6},
            }
        )
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
            "invalid_project_json_is_hard_fail": True,
            "record_score_runs_in_runlog": True,
            "periodic_review_cadence": "weekly",
            "validation_freshness_required": True,
            "validation_freshness_days": 7,
            "do_not_read_secret_contents": True,
        },
        "thresholds": {
            "pass": 85,
            "warn": 70,
        },
        "dimensions": dimensions,
        "commands": {
            "doctor": "python3 scripts/agent_score.py doctor",
            "score": "python3 scripts/agent_score.py score",
            "write": "python3 scripts/agent_score.py score --write",
            "json": "python3 scripts/agent_score.py score --json",
        },
    }


def mechanical_checks_config(project_name: str, created_at: str, governance_profile: str) -> dict:
    json_paths = [
        ".agent/config.json",
        ".agent/manifest.json",
        ".agent/spec.json",
        ".agent/harness.json",
        ".agent/project-layout.json",
        ".agent/workflow.json",
        ".agent/workflow-profiles.json",
        ".agent/loop-engineering.json",
        ".agent/task-board.json",
        ".agent/risk-zones.json",
        ".agent/review-policy.json",
        ".agent/worktrees.json",
        ".agent/role-contracts.json",
        ".agent/knowledge.json",
        ".agent/dev-map.json",
        ".agent/skill-hygiene.json",
        ".agent/project-skills.json",
        ".agent/memory.json",
        ".agent/context.json",
        ".agent/capabilities.json",
        ".agent/resources.json",
        ".agent/evals.json",
        ".agent/skill-runtime.json",
        ".agent/mechanical-checks.json",
        ".agent/baselines.json",
        ".agent/harness-evolution.json",
        ".agent/mcp-policy.json",
        ".agent/governance-gc.json",
        ".agent/sessions/index.json",
    ]
    if profile_at_least(governance_profile, "full"):
        json_paths.extend(
            [
                ".agent/subagents.json",
                ".agent/hooks.json",
                ".agent/tooling.json",
                ".agent/security.json",
                ".agent/skill-distribution.json",
            ]
        )
    checks = {
        "json_integrity": {
            "enabled": True,
            "fail_on_invalid": True,
            "paths": json_paths,
        },
        "jsonl_integrity": {
            "enabled": True,
            "fail_on_invalid": True,
            "paths": [".agent/runlog.jsonl", ".agent/sessions/events.jsonl", ".agent/memory/events.jsonl", ".agent/context/stats.jsonl"],
            "session_offload_glob": ".agent/sessions/*/offload.jsonl",
        },
        "required_paths": {
            "enabled": True,
            "source": ".agent/harness.json",
            "fail_on_missing": True,
        },
        "feature_templates": {
            "enabled": True,
            "template_dir": ".agent/templates/features",
            "required_templates": FEATURE_STAGE_TEMPLATES,
        },
        "task_board": {
            "enabled": True,
            "path": ".agent/task-board.json",
            "require_unique_ids": True,
        },
        "role_contracts": {
            "enabled": True,
            "path": ".agent/role-contracts.json",
            "enforce_finder_cannot_fix": True,
        },
        "loop_engineering": {
            "enabled": True,
            "path": ".agent/loop-engineering.json",
            "workflow_gate": ".agent/workflow.json#/gates/loop_engineering",
            "require_loop_contracts": True,
            "require_iteration_budgets": True,
            "require_stop_conditions": True,
            "require_evidence": True,
            "require_escalation": True,
        },
        "session_offload": {
            "enabled": True,
            "session_root": ".agent/sessions",
            "schema": "agent-session-offload-v1",
            "require_grounding_for_active_session": True,
            "require_git_status_snapshot": True,
            "git_status_snapshot": "refs/git-status-short.txt",
            "require_evidence_handles": True,
            "evidence_must_exist": True,
            "memory_is_advisory": True,
            "bootstrap_must_include_grounding_and_offload": True,
        },
        "manifest": {
            "enabled": True,
            "path": ".agent/manifest.json",
            "must_match_harness_required_paths": True,
        },
        "knowledge_governance": {
            "enabled": True,
            "path": ".agent/knowledge.json",
            "script": "scripts/agent_knowledge.py",
            "require_promotion_bundle_schema": True,
            "procedural_promotion_requires_review_ref": True,
            "blocked_sources_cannot_be_promoted": True,
            "scan_evidence_boundaries": True,
            "forbidden_raw_material": [
                "raw transcripts",
                "terminal scrollback",
                "secrets",
                "private host data",
                "long diagnostic logs",
            ],
        },
        "dev_map": {
            "enabled": True,
            "path": ".agent/dev-map.json",
            "doc": "docs/DEV_MAP.md",
        },
        "skill_hygiene": {
            "enabled": True,
            "path": ".agent/skill-hygiene.json",
            "script": "scripts/agent_skill_hygiene.py",
            "doctor_is_read_only": True,
        },
        "project_skills": {
            "enabled": True,
            "path": ".agent/project-skills.json",
            "script": "scripts/agent_project_skills.py",
            "doctor_is_non_destructive": True,
            "requires_review_fix_review_for_lifecycle_changes": True,
        },
        "agent_runtime_architecture": {
            "enabled": True,
            "policy": ".agent/runtime-policy.json",
            "models": ".agent/model-profiles.json",
            "selection": ".agent/agent-runtime.json",
            "script": "scripts/agent_runtime.py",
            "doctor": "python3 scripts/agent_runtime.py doctor",
            "dependency_free": True,
        },
        "skill_runtime": {
            "enabled": True,
            "path": ".agent/skill-runtime.json",
            "doc": "docs/SKILL_RUNTIME.md",
            "schema": "agent-skill-runtime-v1",
            "require_canonical_core": True,
            "require_adapter_parity_policy": True,
            "require_runtime_modes": True,
            "require_command_lanes": True,
            "require_review_lanes": True,
            "require_impact_benchmark_policy": True,
            "require_shortcut_debt_policy": True,
            "dependency_free": True,
        },
        "resource_catalog": {
            "enabled": True,
            "path": ".agent/resources.json",
            "script": "scripts/agent_resources.py",
            "doctor": "python3 scripts/agent_resources.py doctor",
            "template": ".agent/templates/resource-secrets.local.env.tmpl",
            "fail_on_raw_secret_values": True,
        },
        "harness_evolution": {
            "enabled": True,
            "path": ".agent/harness-evolution.json",
            "require_incident_categories": True,
        },
        "mcp_policy": {
            "enabled": True,
            "path": ".agent/mcp-policy.json",
            "must_be_disabled_or_audited": True,
        },
        "governance_gc": {
            "enabled": True,
            "path": ".agent/governance-gc.json",
            "script": "scripts/agent_gc.py",
        },
        "template_rendering": {
            "enabled": True,
            "json_templates": [".agent/templates/artifacts.json.tmpl"],
            "placeholder_value": "agent-gov-placeholder",
            "fail_on_invalid_render": True,
        },
        "test_baseline": {
            "enabled": True,
            "globs": [
                "tests/*.py",
                "tests/**/*.py",
                "test/*.py",
                "test/**/*.py",
                "**/*_test.py",
                "**/*.test.ts",
                "**/*.spec.ts",
                "**/*.test.js",
                "**/*.spec.js",
                "**/*_test.go",
                "**/*Test.java",
            ],
            "ignore_dirs": [".git", ".agent", "node_modules", "dist", "build", "target", "__pycache__"],
            "fail_on_count_decrease": True,
        },
        "markdown_links": {
            "enabled": True,
            "roots": ["AGENTS.md", "docs", ".agent/templates"],
            "fail_on_missing_local_file": False,
        },
    }
    return {
        "schema": "agent-mechanical-checks-v1",
        "project_name": project_name,
        "created_at": created_at,
        "checks": checks,
        "baseline_policy": {
            "snapshot_dir": ".agent/baselines",
            "fail_on_new_invalid_json": True,
            "fail_on_new_missing_required_path": True,
            "fail_on_new_broken_local_link": False,
            "record_before_after_for_standard_and_full": True,
        },
        "commands": {
            "doctor": "python3 scripts/agent_verify.py doctor",
            "snapshot": "python3 scripts/agent_verify.py snapshot --name before-change",
            "compare": "python3 scripts/agent_verify.py compare --before .agent/baselines/before-change.json --after .agent/baselines/after-change.json",
        },
    }


def baselines_config(project_name: str, created_at: str) -> dict:
    return {
        "schema": "agent-baselines-v1",
        "project_name": project_name,
        "created_at": created_at,
        "snapshot_dir": ".agent/baselines",
        "latest_snapshot": None,
        "snapshots": [],
        "policy": {
            "before_after_required_for_profiles": ["standard", "full"],
            "bugfix_should_capture_reproduction_baseline": True,
            "tiny_may_skip_with_session_note": True,
        },
    }


def manifest_config(project_name: str, created_at: str, harness: dict, evals: dict) -> dict:
    required_paths = harness.get("invariants", {}).get("required_paths", [])
    required_set = set(required_paths)
    all_json_schemas = {
        ".agent/config.json": "agent-project-config-v1",
        ".agent/manifest.json": "agent-governance-manifest-v1",
        ".agent/spec.json": "agent-spec-v1",
        ".agent/harness.json": "agent-harness-v1",
        ".agent/project-layout.json": "agent-project-layout-v1",
        ".agent/workflow.json": "agent-workflow-v1",
        ".agent/workflow-profiles.json": "agent-workflow-profiles-v1",
        ".agent/loop-engineering.json": "agent-loop-engineering-v1",
        ".agent/risk-zones.json": "agent-risk-zones-v1",
        ".agent/review-policy.json": "agent-review-policy-v1",
        ".agent/worktrees.json": "agent-worktree-policy-v1",
        ".agent/subagents.json": "agent-subagent-orchestration-v1",
        ".agent/role-contracts.json": "agent-role-contracts-v1",
        ".agent/task-board.json": "agent-task-board-v1",
        ".agent/hooks.json": "agent-hooks-v1",
        ".agent/knowledge.json": "agent-knowledge-v1",
        ".agent/dev-map.json": "agent-dev-map-v1",
        ".agent/skill-hygiene.json": "agent-skill-hygiene-v1",
        ".agent/project-skills.json": "agent-project-skills-v1",
        ".agent/memory.json": "agent-memory-v1",
        ".agent/context.json": "agent-context-budget-v1",
        ".agent/capabilities.json": "agent-capabilities-v1",
        ".agent/resources.json": "agent-resource-catalog-v1",
        ".agent/runtime-policy.json": "agent-runtime-policy-v1",
        ".agent/model-profiles.json": "agent-model-profiles-v1",
        ".agent/agent-runtime.json": "agent-runtime-selection-v1",
        ".agent/skill-runtime.json": "agent-skill-runtime-v1",
        ".agent/tooling.json": "agent-tooling-v1",
        ".agent/security.json": "agent-security-v1",
        ".agent/evals.json": "agent-evals-v1",
        ".agent/mechanical-checks.json": "agent-mechanical-checks-v1",
        ".agent/baselines.json": "agent-baselines-v1",
        ".agent/harness-evolution.json": "agent-harness-evolution-v1",
        ".agent/mcp-policy.json": "agent-mcp-policy-v1",
        ".agent/governance-gc.json": "agent-governance-gc-v1",
        ".agent/skill-distribution.json": "agent-skill-distribution-v1",
        ".agent/sessions/index.json": "agent-session-index-v1",
    }
    json_schemas = {path: schema for path, schema in all_json_schemas.items() if path in required_set}
    critical_json = sorted(json_schemas)
    json_without_schema = [
        path for path in [".codex/hooks.json", ".claude/settings.json"] if path in required_set
    ]
    jsonl_files = [
        path
        for path in [".agent/runlog.jsonl", ".agent/sessions/events.jsonl", ".agent/memory/events.jsonl", ".agent/context/stats.jsonl"]
        if path in required_set
    ]
    return {
        "schema": "agent-governance-manifest-v1",
        "project_name": project_name,
        "created_at": created_at,
        "manifest_version": 1,
        "sources": {
            "required_paths": ".agent/harness.json#/invariants/required_paths",
            "score_dimensions": ".agent/evals.json#/dimensions",
            "mechanical_checks": ".agent/mechanical-checks.json#/checks",
        },
        "required_paths": required_paths,
        "json_schemas": json_schemas,
        "critical_json": critical_json,
        "json_without_schema": json_without_schema,
        "jsonl_files": jsonl_files,
        "session_offload": {
            "schema": "agent-session-offload-v1",
            "glob": ".agent/sessions/*/offload.jsonl",
            "grounding": ".agent/sessions/*/grounding.md",
            "index": ".agent/sessions/*/offload-index.md",
            "task_map": ".agent/sessions/*/task-map.mmd",
            "git_status_snapshot": ".agent/sessions/*/refs/git-status-short.txt",
            "authority": "advisory",
        },
        "score_dimensions": sorted(evals.get("dimensions", {})),
        "policy": {
            "generated_scripts_should_prefer_manifest": True,
            "fallback_to_legacy_lists_when_missing": True,
            "update_manifest_when_governance_surface_changes": True,
        },
    }


def escape_toml_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def role_instruction(role: str, purpose: str) -> str:
    return f"""Role: {role}
Purpose: {purpose}

Follow repository governance:
- Read AGENTS.md first when available.
- Respect .agent/subagents.json, .agent/role-contracts.json, .agent/workflow.json, .agent/workflow-profiles.json, .agent/task-board.json, .agent/risk-zones.json, .agent/review-policy.json, .agent/worktrees.json, .agent/harness.json, and .agent/project-layout.json.
- Keep work inside the assigned read/write boundary.
- If you find a defect while acting as verifier or reviewer, report it and route it back; do not fix it directly.
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
        "python3 \"$root/.agent/tools/governance_hook.py\" --event {event} --json-output; "
        "else printf \"%s\\n\" \"{{\\\"hookSpecificOutput\\\":{{\\\"hookEventName\\\":\\\"{event}\\\",\\\"additionalContext\\\":\\\"governance hook: .agent/tools/governance_hook.py not found\\\"}},\\\"additionalContext\\\":\\\"governance hook: .agent/tools/governance_hook.py not found\\\",\\\"status\\\":\\\"error\\\"}}\"; fi'"
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
        "python3 \"$root/.agent/tools/governance_hook.py\" --event {event} --json-output; "
        "else printf \"%s\\n\" \"{{\\\"hookSpecificOutput\\\":{{\\\"hookEventName\\\":\\\"{event}\\\",\\\"additionalContext\\\":\\\"governance hook: .agent/tools/governance_hook.py not found\\\"}},\\\"additionalContext\\\":\\\"governance hook: .agent/tools/governance_hook.py not found\\\",\\\"status\\\":\\\"error\\\"}}\"; fi'"
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
        self.unchanged: list[str] = []
        self.preserved: list[str] = []
        self.conflicts: list[str] = []

    def target(self, relative: str) -> Path:
        relative_path = Path(relative)
        if relative_path.is_absolute():
            raise ValueError(f"refusing to write absolute generated path: {relative}")
        root = self.root.resolve()
        path = (self.root / relative_path).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"refusing to write outside project root: {relative}") from exc
        return path

    def write(self, relative: str, content: str, executable: bool = False) -> None:
        path = self.target(relative)
        exists = path.exists()
        if exists and not self.force:
            if relative in APPEND_ONLY_PATHS:
                self.preserved.append(relative)
            elif self.same_text(path, content):
                self.unchanged.append(relative)
            else:
                self.skipped.append(relative)
                self.conflicts.append(relative)
            return
        if not self.dry_run:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            if executable:
                path.chmod(path.stat().st_mode | 0o111)
        (self.updated if exists else self.created).append(relative)

    def ensure_line(self, relative: str, line: str) -> None:
        path = self.target(relative)
        exists = path.exists()
        current = path.read_text(encoding="utf-8") if exists else ""
        lines = current.splitlines()
        if line in lines:
            self.unchanged.append(relative)
            return
        if not self.dry_run:
            path.parent.mkdir(parents=True, exist_ok=True)
            prefix = current
            if prefix and not prefix.endswith("\n"):
                prefix += "\n"
            path.write_text(prefix + line + "\n", encoding="utf-8")
        (self.updated if exists else self.created).append(relative)

    def copy(self, source: Path, relative: str, executable: bool = False) -> None:
        path = self.target(relative)
        exists = path.exists()
        if exists and not self.force:
            if relative in APPEND_ONLY_PATHS:
                self.preserved.append(relative)
            elif self.same_bytes(path, source):
                self.unchanged.append(relative)
            else:
                self.skipped.append(relative)
                self.conflicts.append(relative)
            return
        if not self.dry_run:
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, path)
            if executable:
                path.chmod(path.stat().st_mode | 0o111)
        (self.updated if exists else self.created).append(relative)

    @staticmethod
    def same_text(path: Path, content: str) -> bool:
        if not path.is_file():
            return False
        try:
            return path.read_text(encoding="utf-8") == content
        except OSError:
            return False

    @staticmethod
    def same_bytes(path: Path, source: Path) -> bool:
        if not path.is_file() or not source.is_file():
            return False
        try:
            return path.read_bytes() == source.read_bytes()
        except OSError:
            return False


def spec_enabled(args: argparse.Namespace) -> bool:
    return args.spec_mode == "embedded"


def lines(items: list[str]) -> str:
    return "\n".join(items)


def agent_ground_rules(governance_profile: str) -> tuple[str, str]:
    standard = []
    full = []
    if profile_at_least(governance_profile, "standard"):
        standard = [
            "- Use `.agent/workflow*.json`, `.agent/task-board.json`, `docs/features/`, `.agent/risk-zones.json`, `.agent/review-policy.json`, `.agent/worktrees.json`, and `.agent/role-contracts.json` for task flow, autonomy, isolation, review evidence, and finder-cannot-fix separation.",
            "- Use `.agent/loop-engineering.json` and `docs/LOOP_ENGINEERING.md` for bounded work/review/debug/eval/recovery loops.",
            "- Use `.agent/knowledge.json`, `.agent/memory.json`, `.agent/context.json`, `.agent/dev-map.json`, `docs/DEV_MAP.md`, `docs/AI_CODING_GLOSSARY.md`, and `docs/DOMAIN_GLOSSARY.md` for durable knowledge, memory retrieval, context budgets, navigation, and terminology.",
            "- Use `.agent/resources.json`, `docs/RESOURCES.md`, and `scripts/agent_resources.py` for managed project resources and safe-use boundaries.",
            "- Use `.agent/runtime-policy.json`, `.agent/model-profiles.json`, `.agent/agent-runtime.json`, `docs/AGENT_RUNTIME_ARCHITECTURE.md`, and `scripts/agent_runtime.py` for Skill-first runtime target, MCP boundary, model profile, adapter, and interview decisions.",
            "- Use `.agent/skill-runtime.json` and `docs/SKILL_RUNTIME.md` for portable Skill/plugin architecture: canonical core, thin host adapters, runtime modes, command lanes, review lanes, impact benchmarks, and shortcut/debt ledgers.",
            "- Use `.agent/capabilities.json`, `.agent/mechanical-checks.json`, `.agent/baselines.json`, `.agent/harness-evolution.json`, `.agent/mcp-policy.json`, `.agent/governance-gc.json`, and `scripts/agent_*` doctors for capability risk, hard checks, incident promotion, integration boundaries, and governance gardening.",
        ]
    if profile_at_least(governance_profile, "full"):
        full = [
            "- Use `.agent/subagents.json`, `.agent/hooks.json`, `.agent/tooling.json`, `.agent/security.json`, and `.agent/skill-distribution.json` only when delegated work, native adapters, bounded inspection, security suites, or skill mirroring are actually in scope.",
        ]
    return lines(standard), lines(full)


def agent_workflow(governance_profile: str, spec_workflow_step: str) -> tuple[str, str, str]:
    core = [
        "- If `.agent/sessions/active.md` exists, run `python3 .agent/tools/agent_session.py bootstrap` and read the output before editing.",
        "- Run `python3 .agent/tools/agent_session.py doctor`; resolve errors before continuing and note warnings in the active session.",
        "- Run `python3 scripts/agent_check.py`, `python3 scripts/agent_migrate.py doctor`, `python3 scripts/agent_runlog.py doctor`, and `python3 scripts/agent_score.py doctor` before substantial governance edits.",
        "- Inspect `git status --short` before editing.",
        "- Read `.agent/project-layout.json` before adding top-level directories or moving files.",
        f"- {spec_workflow_step}",
        "- Read `docs/index.md` and the relevant linked doc before making broad changes.",
        "- Inspect configured harness commands with `python3 scripts/agent_validate.py --list`.",
        "- For behavior changes, record failing-test evidence before implementation unless an exception is documented.",
        "- Before broad implementation, state assumptions and success criteria; ask for clarification when multiple interpretations would change the solution.",
        "- For long-running work, start or continue an agent session with `python3 .agent/tools/agent_session.py status`.",
        "- Checkpoint after major decisions, file changes, and validation runs.",
        "- Before handing off or compacting context, run `python3 .agent/tools/agent_session.py compact`.",
        "- Run `python3 scripts/agent_check.py` after project governance changes.",
    ]
    standard = []
    full = []
    if profile_at_least(governance_profile, "standard"):
        standard = [
            "- Run `python3 .agent/tools/agent_memory.py doctor` and retrieve durable context with `timeline`, `search`, then `detail` only as needed.",
            "- Run `python3 .agent/tools/agent_context.py doctor` and keep large docs behind summaries and detail commands.",
            "- Run `python3 scripts/agent_capabilities.py doctor`, `python3 scripts/agent_resources.py doctor`, `python3 scripts/agent_task.py doctor`, `python3 scripts/agent_verify.py doctor`, and `python3 scripts/agent_gc.py doctor`.",
            "- Read `.agent/workflow.json`, `.agent/workflow-profiles.json`, `.agent/task-board.json`, `.agent/risk-zones.json`, and `.agent/review-policy.json`; choose the lightest sufficient workflow profile before implementation.",
            "- For non-tiny work, complete the requirements interview gate before design or implementation: ask one question at a time, provide a recommended answer and reason, cross-check claims against current code/docs, and update `docs/DOMAIN_GLOSSARY.md` when terms are ambiguous.",
            "- Read `.agent/worktrees.json`; prefer an ignored isolated worktree for feature work, plan execution, or risky refactors.",
            "- Read `docs/DEV_MAP.md` and `.agent/dev-map.json` before broad codebase navigation or module-boundary edits.",
            "- Before using managed resources, run `agent_resources.py match` then `resolve`; keep raw secrets in ignored local files or an external vault/proxy.",
            "- Before implementing agents, MCP servers, hybrids, or runtime libraries, run `agent_runtime.py doctor` and confirm `.agent/agent-runtime.json`.",
            "- Before publishing or adapting a portable Skill/plugin, confirm `.agent/skill-runtime.json` and `docs/SKILL_RUNTIME.md`; keep behavior in the canonical Skill core and host adapters thin.",
            "- Run `python3 scripts/agent_skill_hygiene.py report --json` when reviewing installed or project-level skills; treat it as read-only fact collection, not cleanup authority.",
            "- For bugs, test failures, build failures, unexpected behavior, or governance failures, classify the harness gap with `.agent/harness-evolution.json`.",
            "- For non-tiny work, create or update a task-board record with `python3 scripts/agent_task.py` and keep `docs/features/<task-id>/` stage documents current.",
            "- For standard or full work, capture before/after snapshots with `python3 scripts/agent_verify.py snapshot --name <name>` and compare regressions before handoff.",
            "- Before enabling MCP or external integrations, update `.agent/mcp-policy.json`, keep credentials outside the repo, and record high-risk use in runlog.",
            "- For reusable context, run `python3 .agent/tools/agent_memory.py ingest-session --reason handoff`.",
            "- For oversized governance docs, run `python3 .agent/tools/agent_context.py suggest` and validate any compressed rewrite with `validate-pair`.",
            "- Use ADRs for durable architecture decisions, RFCs for proposals, and postmortems for incidents.",
            "- Run `python3 scripts/agent_gc.py report` during periodic governance cleanup.",
        ]
    if profile_at_least(governance_profile, "full"):
        full = [
            "- Run `python3 scripts/agent_tooling.py doctor` and `python3 scripts/agent_security.py doctor`.",
            "- For delegated, substantial, high-risk, or critical work, run spec review before quality review, re-review after fixes, and record risk, diff, human review, and automated review boundaries.",
            "- For delegated work, read `.agent/subagents.json` and `.agent/role-contracts.json`, assign disjoint write boundaries, and require concise `===SNAPSHOT===` JSON reports.",
            "- Check `.agent/hooks.json` before modifying native hook adapters.",
            "- Record accepted subagent snapshots before compaction.",
        ]
    return lines(core), lines(standard), lines(full)


def harness_commands(governance_profile: str) -> str:
    commands = [
        "python3 scripts/agent_check.py",
        "python3 scripts/agent_migrate.py doctor",
        "python3 scripts/agent_spec.py doctor",
        "python3 scripts/agent_validate.py --list",
        "python3 scripts/agent_runlog.py doctor",
        "python3 scripts/agent_score.py doctor",
    ]
    if profile_at_least(governance_profile, "standard"):
        commands.extend(
            [
                "python3 scripts/agent_knowledge.py",
                "python3 scripts/agent_invariants.py",
                "python3 scripts/agent_capabilities.py doctor",
                "python3 scripts/agent_resources.py doctor",
                "python3 scripts/agent_runtime.py doctor",
                "python3 scripts/agent_skill_hygiene.py doctor",
                "python3 scripts/agent_project_skills.py doctor",
                "python3 scripts/agent_task.py doctor",
                "python3 scripts/agent_verify.py doctor",
                "python3 scripts/agent_gc.py doctor",
                "python3 .agent/tools/agent_memory.py doctor",
                "python3 .agent/tools/agent_context.py doctor",
            ]
        )
    if profile_at_least(governance_profile, "full"):
        commands.extend(
            [
                "python3 scripts/agent_tooling.py doctor",
                "python3 scripts/agent_security.py doctor",
                "python3 scripts/agent_sync_skills.py --dry-run",
            ]
        )
    return "\n".join(commands)


def quality_blocks(governance_profile: str) -> dict[str, str]:
    standard_commands = ""
    full_commands = ""
    standard_expectations = ""
    full_expectations = ""
    if profile_at_least(governance_profile, "standard"):
        standard_commands = """Workflow and governance checks:

```bash
python3 scripts/agent_task.py doctor
python3 scripts/agent_verify.py doctor
python3 scripts/agent_gc.py doctor
python3 .agent/tools/agent_context.py scan --limit 10
python3 .agent/tools/agent_context.py suggest
python3 scripts/agent_capabilities.py doctor
python3 scripts/agent_skill_hygiene.py doctor
python3 scripts/agent_project_skills.py doctor
python3 scripts/agent_project_skills.py report
python3 scripts/agent_resources.py doctor
python3 scripts/agent_resources.py list --json
python3 scripts/agent_runtime.py doctor
python3 scripts/agent_runtime.py report --json
python3 scripts/agent_security.py doctor
python3 scripts/agent_capabilities.py list --enabled
python3 scripts/agent_task.py list
python3 scripts/agent_verify.py snapshot --name before-change
python3 scripts/agent_verify.py snapshot --name after-change
python3 scripts/agent_verify.py compare --before .agent/baselines/before-change.json --after .agent/baselines/after-change.json
```"""
        standard_expectations = """- Follow `.agent/workflow.json` and `.agent/workflow-profiles.json` for spec approval, plan quality, implementation discipline, worktree isolation, TDD/debugging, review sequence, and completion verification gates.
- Choose the lightest sufficient workflow profile: `tiny`, `bugfix`, `standard`, or `full`.
- For non-tiny work, keep `.agent/task-board.json` and `docs/features/<task-id>/` current.
- Complete the requirements interview gate before design or implementation: ask one question at a time, recommend an answer with rationale, cross-check user claims against current code/docs, and update `docs/DOMAIN_GLOSSARY.md` for stable terms.
- Classify task risk with `.agent/risk-zones.json` before implementation; stop and re-plan when the risk level increases.
- Follow the `implementation_discipline` gate for non-trivial implementation: surface assumptions, choose the simplest maintainable approach, check local reuse/stdlib/native/existing dependency paths before new code, keep diffs tied to the request, and define success criteria.
- For external-source-driven changes, record each source as verified, partial, or blocked before turning it into project rules.
- Follow `.agent/review-policy.json` before handoff: every changed line should map to requested, necessary-support, incidental, or risky; incidental changes need removal or an explicit exception.
- For bugs, build failures, test failures, and unexpected behavior, record reproduction, root cause, hypothesis, and validation with `.agent/templates/debugging-record.md.tmpl`.
- For multi-step work, use `.agent/templates/implementation-plan.md.tmpl` or an embedded spec task file with exact files, commands, expected results, and no placeholders.
- For non-tiny iterative work, use `.agent/loop-engineering.json` and `docs/LOOP_ENGINEERING.md` to set a loop contract, observation signal, iteration budget, stop conditions, evidence path, and escalation path before repeating attempts.
- Prefer an ignored isolated worktree for feature work and substantial plan execution; record baseline validation before edits.
- For standard and full work, capture before/after mechanical snapshots and compare them before handoff.
- Before broad edits, read `docs/DEV_MAP.md` and update it when entry points, ownership, or read-before-edit guidance changes.
- Before using remote servers, databases, repositories, deployment targets, or compute machines, match and resolve them through `.agent/resources.json` and `scripts/agent_resources.py`; keep raw secrets in ignored local files or external vault/proxy references.
- Before implementing product-level LLM agents, MCP servers, hybrid agent-plus-MCP systems, or runtime libraries, confirm the project target, Skill-first runtime contract, MCP server boundary when applicable, model capability flags in `.agent/model-profiles.json`, and adapter rules in `.agent/runtime-policy.json`.
- Run review-fix loops for substantial changes.
- Run spec compliance review before code quality review for delegated or substantial implementation, and re-review after fixes.
- Keep complexity-only audit findings separate from correctness, security, and spec review findings.
- Enforce `.agent/role-contracts.json`: verifier and reviewer roles report findings and route fixes back instead of fixing them directly.
- Before relying on remembered context, retrieve it through `agent_memory.py search` or `detail` and distinguish stored facts from current repository state.
- Promote memory deliberately: `episodic` for session history, `semantic` for sourced facts, and `procedural` only after review.
- Keep `AGENTS.md`, docs, session bootstraps, and generated outputs within `.agent/context.json` budgets.
- Use ADRs for accepted long-term decisions, RFCs for broad proposals, and postmortems for incidents.
- Classify repeated governance or loop failures with `.agent/harness-evolution.json` and promote fixes into rules, skills, scripts, workflow gates, loop contracts, role contracts, tools/MCP policy, or docs.
- Run `python3 scripts/agent_gc.py report` periodically to find stale docs, stale tasks, baseline drift, owner gaps, and config pointer issues."""
    if profile_at_least(governance_profile, "full"):
        full_commands = """Full-profile tooling, security, and skill distribution checks:

```bash
python3 scripts/agent_tooling.py doctor
python3 scripts/agent_security.py doctor
python3 scripts/agent_security.py scan-paths
python3 scripts/agent_sync_skills.py --dry-run
```"""
        full_expectations = """- Agent-generated summaries and automated review comments are prechecks, not human review evidence. High and critical risk changes need reviewer, diff range, files reviewed, high-risk paths checked, and conclusion.
- When subagents are used, validate integrated changes after accepting their snapshots.
- Use `scripts/agent_tooling.py` when normal shell output would be too large or ambiguous.
- Configure optional security suites in `.agent/security.json`; record skipped suites in runlog or validation notes.
- Keep native Codex/Claude adapters consistent with `.agent/subagents.json`, `.agent/hooks.json`, and `.agent/skill-distribution.json`.
- Review `.agent/mcp-policy.json` before enabling MCP or external integrations."""
    return {
        "quality_standard_commands": standard_commands,
        "quality_full_commands": full_commands,
        "quality_standard_expectations": standard_expectations,
        "quality_full_expectations": full_expectations,
    }


def build_values(root: Path, args: argparse.Namespace) -> dict[str, str]:
    project_name = args.project_name or root.name
    tech_stack = parse_csv(args.tech_stack)
    dirs = layout_dirs(args.layout, parse_csv(args.dir))
    enabled = spec_enabled(args)
    claude_enabled = (not args.no_claude) and profile_at_least(args.governance_profile, "full")
    standard_ground_rules, full_ground_rules = agent_ground_rules(args.governance_profile)
    workspace_path = str(root.resolve())
    created_at = utc_now() if args.force else (existing_created_at(root) or utc_now())
    core_workflow, standard_workflow, full_workflow = agent_workflow(
        args.governance_profile,
        "Check documented planning context before substantial changes."
        if not enabled
        else "Check embedded spec context with `python3 scripts/agent_spec.py list --json` before substantial changes.",
    )
    quality = quality_blocks(args.governance_profile)
    return {
        "project_name": project_name,
        "project_name_json": json.dumps(project_name),
        "tech_stack": ", ".join(tech_stack) if tech_stack else "unspecified",
        "tech_stack_json": json.dumps(", ".join(tech_stack) if tech_stack else "unspecified"),
        "layout_name": args.layout,
        "layout_name_json": json.dumps(args.layout),
        "governance_profile": args.governance_profile,
        "governance_profile_json": json.dumps(args.governance_profile),
        "layout_dirs": "\n".join(f"- `{path}/`" for path in dirs)
        or "- No required application directories declared at initialization; `.agent/project-layout.json` records an architecture boundary exception.",
        "layout_dirs_inline": ", ".join(f"`{path}/`" for path in dirs)
        or "none declared; `.agent/project-layout.json` records an architecture boundary exception",
        "client_surface": args.client_surface,
        "client_surface_json": json.dumps(args.client_surface),
        "remote_kind": args.remote_kind,
        "remote_kind_json": json.dumps(args.remote_kind),
        "workspace_path": workspace_path,
        "workspace_path_json": json.dumps(workspace_path),
        "created_at": created_at,
        "created_at_json": json.dumps(created_at),
        "openspec_enabled_json": "true" if enabled else "false",
        "claude_enabled_json": "true" if claude_enabled else "false",
        "config_paths_json": config_paths_json(args.governance_profile, enabled, claude_enabled),
        "agent_standard_ground_rules": standard_ground_rules,
        "agent_full_ground_rules": full_ground_rules,
        "agent_core_workflow": core_workflow,
        "agent_standard_workflow": standard_workflow,
        "agent_full_workflow": full_workflow,
        "agent_harness_commands": harness_commands(args.governance_profile),
        **quality,
        "standard_docs_intro": (
            "Knowledge metadata is tracked in `.agent/knowledge.json`. Update `owner`, `last_reviewed`, `source_links`, and `known_stale_sections` when durable knowledge changes.\n"
            "Development navigation is tracked in `.agent/dev-map.json` and `docs/DEV_MAP.md`.\n"
            "Project-domain terminology is tracked in `docs/DOMAIN_GLOSSARY.md`; use it to resolve naming conflicts before implementation.\n"
            "Skill topology and hygiene policy are tracked in `.agent/skill-hygiene.json`; scans are read-only and cleanup requires human confirmation.\n"
            "Project skill lifecycle governance is tracked in `.agent/project-skills.json`; use `scripts/agent_project_skills.py` to report managed, unmanaged, missing, drifted, pinned, and manifest boundary states.\n"
            "Cross-session working memory is tracked in `.agent/memory.json` and `.agent/memory/`. Store summaries, decisions, validation, and retrieval handles; do not store raw transcripts.\n"
            "Capability governance is tracked in `.agent/capabilities.json`.\n"
            "Project resource assets are tracked in `.agent/resources.json`; use `scripts/agent_resources.py` to match and resolve servers, databases, repositories, deployment targets, compute machines, and credential references without storing raw secrets.\n"
            "Skill runtime governance is tracked in `.agent/skill-runtime.json`; use `docs/SKILL_RUNTIME.md` before publishing or adapting portable Skills, native host adapters, command lanes, runtime modes, benchmarks, or shortcut ledgers.\n"
            "Lightweight security governance is tracked in `.agent/security.json`; standard profile scans sensitive-looking paths without reading secret contents.\n"
            "Workflow gates, including risk classification, implementation discipline, diff traceability, and review evidence, are tracked in `.agent/workflow.json`.\n"
            "Workflow profiles are tracked in `.agent/workflow-profiles.json`. Cross-session task state is tracked in `.agent/task-board.json` and `docs/features/`.\n"
            "Loop engineering policy is tracked in `.agent/loop-engineering.json` and `docs/LOOP_ENGINEERING.md`; use it for bounded work, review-fix, debugging, eval optimization, and session recovery loops.\n"
            "Risk autonomy is tracked in `.agent/risk-zones.json`. Diff and review policy is tracked in `.agent/review-policy.json`.\n"
            "Isolated worktree policy is tracked in `.agent/worktrees.json`.\n"
            "Role contracts are tracked in `.agent/role-contracts.json`. Mechanical checks and before/after baselines are tracked in `.agent/mechanical-checks.json` and `.agent/baselines.json`.\n"
            "Harness evolution is tracked in `.agent/harness-evolution.json`. Periodic governance gardening is tracked in `.agent/governance-gc.json`."
            if profile_at_least(args.governance_profile, "standard")
            else ""
        ),
        "standard_docs_links": (
            "- [Architecture](ARCHITECTURE.md): system boundaries, dependency direction, and major design decisions.\n"
            "- [Reliability](RELIABILITY.md): runtime behavior, observability, rollback, and operational risks.\n"
            "- [Governance Score](QUALITY_SCORE.md): local score dimensions, dashboard, and drift signals.\n"
            "- [AI Coding Glossary](AI_CODING_GLOSSARY.md): shared terms for skills, tools, MCP, harness, sessions, memory, and reviews.\n"
            "- [Domain Glossary](DOMAIN_GLOSSARY.md): project-domain terms, canonical names, forbidden synonyms, and source evidence.\n"
            "- [Development Map](DEV_MAP.md): concise entry points, ownership, read-before-edit docs, and common patterns.\n"
            "- [Loop Engineering](LOOP_ENGINEERING.md): loop contracts, iteration budgets, stop conditions, evidence, and escalation rules.\n"
            "- [Project Resources](RESOURCES.md): resource catalog, local secret-material template, matching, resolve, and safe-use rules.\n"
            "- [Skill Runtime Governance](SKILL_RUNTIME.md): canonical Skill cores, thin host adapters, runtime modes, command lanes, review lanes, skill-impact benchmarks, and shortcut/debt ledgers.\n"
            "- [Feature Work](features/INDEX.md): task-board-backed feature-stage documents.\n"
            "- [Tech Debt](tech-debt.md): known debt, cleanup candidates, and follow-up work.\n"
            "- [ADRs](adr/README.md): durable architecture decisions.\n"
            "- [RFCs](rfcs/README.md): pre-change design proposals.\n"
            "- [Incidents](incidents/README.md): postmortems and reliability learning."
            if profile_at_least(args.governance_profile, "standard")
            else ""
        ),
        "standard_config_updates": (
            "Update `.agent/workflow.json` when lifecycle gates, risk classification, implementation discipline, diff traceability, review order, TDD/debugging rules, or completion evidence rules change.\n"
            "Update `.agent/workflow-profiles.json` when task-size process weights or required stage documents change.\n"
            "Update `.agent/loop-engineering.json` and `docs/LOOP_ENGINEERING.md` when loop types, iteration budgets, observation signals, stop conditions, evidence paths, or escalation rules change.\n"
            "Update `.agent/task-board.json` and `docs/features/` when non-tiny task state, stage, or delivery conclusions change.\n"
            "Update `docs/DOMAIN_GLOSSARY.md` when requirements interviews introduce or resolve project-domain terms.\n"
            "Update `.agent/risk-zones.json` when risk levels, autonomy rules, approval gates, or high-risk path patterns change.\n"
            "Update `.agent/review-policy.json` when diff traceability categories, human review evidence, or automated review boundaries change.\n"
            "Update `.agent/worktrees.json` when isolated worktree locations, baseline validation, or guarded cleanup rules change.\n"
            "Update `.agent/role-contracts.json` when role inputs, outputs, forbidden actions, or finder-cannot-fix policy changes.\n"
            "Update `.agent/memory.json` when memory stores, privacy tags, or retention policy change.\n"
            "Update `.agent/capabilities.json` when agent-visible tools, external integrations, permissions, owners, or risk levels change.\n"
            "Update `.agent/resources.json` when servers, databases, repositories, deployment targets, compute machines, endpoint references, credential references, owners, usage rules, health checks, or resource risk levels change.\n"
            "Update `.agent/skill-runtime.json` and `docs/SKILL_RUNTIME.md` when portable Skill/plugin core rules, host adapters, runtime modes, command lanes, review lanes, impact benchmark policy, or shortcut/debt marker policy changes.\n"
            "Update `.agent/security.json` when credential boundary policy, sensitive-path scans, or local security suites change.\n"
            "Update `.agent/dev-map.json` and `docs/DEV_MAP.md` when entry points, ownership, read-before-edit guidance, or common project patterns change.\n"
            "Update `.agent/skill-hygiene.json` when skill scan roots, stale thresholds, risk signals, or canary policy change.\n"
            "Update `.agent/project-skills.json` when project-level skills are added, adopted, updated, deprecated, removed, pinned, or reclassified between production and workspace-only intent.\n"
            "Update `.agent/mechanical-checks.json` and `.agent/baselines.json` when hard checks or baseline comparison policy changes.\n"
            "Update `.agent/harness-evolution.json` when incident categories or promotion targets change.\n"
            "Update `.agent/governance-gc.json` when periodic governance cleanup checks or thresholds change."
            if profile_at_least(args.governance_profile, "standard")
            else ""
        ),
        "full_docs_links": (
            "- [Security](SECURITY.md): secrets, auth, sensitive data, and dependency risk rules.\n"
            "- [Agent Tooling](TOOLING.md): bounded repository inspection, search, and output rules."
            if profile_at_least(args.governance_profile, "full")
            else ""
        ),
        "full_config_updates": (
            "Update `.agent/subagents.json` when delegated agent roles, boundaries, or snapshot rules change.\n"
            "Update `.agent/hooks.json` when session bootstrap, checkpoint, or native hook adapter behavior changes.\n"
            "Update `.agent/tooling.json` when output limits, ignored directories, or bounded inspection rules change.\n"
            "Update `.agent/security.json` when policy-as-code, secret scan, dependency audit, SBOM, or license scan commands change.\n"
            "Update `.agent/mcp-policy.json` before enabling or changing MCP/external integrations.\n"
            "Update `.agent/skill-distribution.json` when project skill synchronization paths change."
            if profile_at_least(args.governance_profile, "full")
            else ""
        ),
        "spec_source": "none" if not enabled else "agent-gov-spec",
        "spec_source_json": json.dumps("none" if not enabled else "agent-gov-spec"),
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
        "workspace_path": str(root),
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
    claude_enabled = (not args.no_claude) and profile_at_least(args.governance_profile, "full")
    governance_profile = args.governance_profile
    standard_enabled = profile_at_least(governance_profile, "standard")
    full_enabled = profile_at_least(governance_profile, "full")
    harness = harness_config(project_name, values["created_at"], tech_stack, dirs, openspec_enabled, claude_enabled, governance_profile)
    evals = evals_config(project_name, values["created_at"], governance_profile)

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
    writer.write(
        ".agent/manifest.json",
        json.dumps(manifest_config(project_name, values["created_at"], harness, evals), indent=2) + "\n",
    )
    if openspec_enabled:
        writer.write(".agent/spec.json", json.dumps(spec_config(project_name, values["created_at"]), indent=2) + "\n")
    writer.write(
        ".agent/harness.json",
        json.dumps(harness, indent=2) + "\n",
    )
    writer.write(
        ".agent/project-layout.json",
        json.dumps(project_layout_config(project_name, args.layout, tech_stack, dirs), indent=2) + "\n",
    )
    writer.write(
        ".agent/evals.json",
        json.dumps(evals, indent=2) + "\n",
    )
    if standard_enabled:
        writer.ensure_line(".gitignore", ".agent/local/")
        raw_architecture_intake = load_architecture_intake(args.architecture_intake)
        architecture_intake = architecture_intake_config(raw_architecture_intake, has_intake=bool(args.architecture_intake))
        writer.write(
            ".agent/workflow.json",
            json.dumps(workflow_config(project_name, values["created_at"], openspec_enabled), indent=2) + "\n",
        )
        writer.write(
            ".agent/workflow-profiles.json",
            json.dumps(workflow_profiles_config(project_name, values["created_at"]), indent=2) + "\n",
        )
        writer.write(
            ".agent/loop-engineering.json",
            json.dumps(loop_engineering_config(project_name, values["created_at"]), indent=2) + "\n",
        )
        writer.write(
            ".agent/risk-zones.json",
            json.dumps(risk_zones_config(project_name, values["created_at"]), indent=2) + "\n",
        )
        writer.write(
            ".agent/review-policy.json",
            json.dumps(review_policy_config(project_name, values["created_at"]), indent=2) + "\n",
        )
        writer.write(
            ".agent/worktrees.json",
            json.dumps(worktree_config(project_name, values["created_at"]), indent=2) + "\n",
        )
        writer.write(
            ".agent/role-contracts.json",
            json.dumps(role_contracts_config(project_name, values["created_at"], governance_profile), indent=2) + "\n",
        )
        writer.write(
            ".agent/task-board.json",
            json.dumps(task_board_config(project_name, values["created_at"]), indent=2) + "\n",
        )
        writer.write(
            ".agent/knowledge.json",
            json.dumps(knowledge_config(project_name, values["created_at"], governance_profile), indent=2) + "\n",
        )
        writer.write(
            ".agent/dev-map.json",
            json.dumps(dev_map_config(project_name, values["created_at"], dirs), indent=2) + "\n",
        )
        writer.write(
            ".agent/skill-hygiene.json",
            json.dumps(skill_hygiene_config(project_name, values["created_at"]), indent=2) + "\n",
        )
        writer.write(
            ".agent/project-skills.json",
            json.dumps(project_skills_config(project_name, values["created_at"]), indent=2) + "\n",
        )
        writer.write(
            ".agent/runtime-policy.json",
            json.dumps(runtime_policy_config(project_name, values["created_at"], architecture_intake), indent=2) + "\n",
        )
        writer.write(
            ".agent/model-profiles.json",
            json.dumps(model_profiles_config(project_name, values["created_at"], architecture_intake), indent=2) + "\n",
        )
        writer.write(
            ".agent/agent-runtime.json",
            json.dumps(agent_runtime_config(project_name, values["created_at"], architecture_intake), indent=2) + "\n",
        )
        writer.write(
            ".agent/skill-runtime.json",
            json.dumps(skill_runtime_config(project_name, values["created_at"]), indent=2) + "\n",
        )
        writer.write(
            ".agent/memory.json",
            json.dumps(memory_config(project_name, values["created_at"]), indent=2) + "\n",
        )
        writer.write(
            ".agent/context.json",
            json.dumps(context_budget_config(project_name, values["created_at"], governance_profile), indent=2) + "\n",
        )
        writer.write(
            ".agent/security.json",
            json.dumps(security_config(project_name, values["created_at"]), indent=2) + "\n",
        )
        writer.write(
            ".agent/resources.json",
            json.dumps(resource_catalog_config(project_name, values["created_at"], values["workspace_path"]), indent=2) + "\n",
        )
        writer.write(
            ".agent/capabilities.json",
            json.dumps(
                capabilities_config(project_name, values["created_at"], openspec_enabled, claude_enabled, governance_profile),
                indent=2,
            )
            + "\n",
        )
        writer.write(
            ".agent/mechanical-checks.json",
            json.dumps(mechanical_checks_config(project_name, values["created_at"], governance_profile), indent=2) + "\n",
        )
        writer.write(
            ".agent/baselines.json",
            json.dumps(baselines_config(project_name, values["created_at"]), indent=2) + "\n",
        )
        writer.write(
            ".agent/harness-evolution.json",
            json.dumps(harness_evolution_config(project_name, values["created_at"]), indent=2) + "\n",
        )
        writer.write(
            ".agent/mcp-policy.json",
            json.dumps(mcp_policy_config(project_name, values["created_at"]), indent=2) + "\n",
        )
        writer.write(
            ".agent/governance-gc.json",
            json.dumps(governance_gc_config(project_name, values["created_at"]), indent=2) + "\n",
        )
    if full_enabled:
        writer.write(
            ".agent/subagents.json",
            json.dumps(subagent_config(project_name, values["created_at"], claude_enabled), indent=2) + "\n",
        )
        writer.write(".agent/hooks.json", json.dumps(hooks_config(project_name, values["created_at"]), indent=2) + "\n")
        writer.write(
            ".agent/tooling.json",
            json.dumps(tooling_config(project_name, values["created_at"]), indent=2) + "\n",
        )
        writer.write(
            ".agent/skill-distribution.json",
            json.dumps(skill_distribution_config(project_name, values["created_at"]), indent=2) + "\n",
        )
    writer.write(".agent/evals/latest.md", template("quality-score.md.tmpl"))
    writer.write(".agent/runlog.jsonl", json.dumps(init_runlog_event(project_name, values["created_at"])) + "\n")
    if standard_enabled:
        writer.write(".agent/baselines/.gitkeep", "")
        writer.write(".agent/memory/events.jsonl", "")
        writer.write(".agent/memory/latest.md", template("memory-latest.md.tmpl"))
        writer.write(".agent/memory/summaries/.gitkeep", "")
        writer.write(".agent/context/stats.jsonl", "")
        writer.write(".agent/context/latest.md", template("context-summary.md.tmpl"))
    writer.write(".agent/sessions/index.json", template("session-index.json.tmpl"))
    writer.write(".agent/sessions/events.jsonl", "")
    writer.write(".agent/sessions/active.md", template("active.md.tmpl"))
    writer.write(".agent/sessions/bootstrap.md", template("bootstrap.md.tmpl"))

    core_templates = (
        "session.md.tmpl",
        "handoff.md.tmpl",
        "context.md.tmpl",
        "decisions.md.tmpl",
        "changes.md.tmpl",
        "validation.md.tmpl",
        "resume-prompt.md.tmpl",
        "artifacts.json.tmpl",
        *SESSION_OFFLOAD_TEMPLATES,
    )
    standard_templates = (
        "project-review.md.tmpl",
        "project-fix-log.md.tmpl",
        "intake-packet.md.tmpl",
        "resource-secrets.local.env.tmpl",
        "implementation-plan.md.tmpl",
        "debugging-record.md.tmpl",
        "memory-summary.md.tmpl",
        "memory-latest.md.tmpl",
        "context-summary.md.tmpl",
        "adr.md.tmpl",
        "rfc.md.tmpl",
        "postmortem.md.tmpl",
        "quality-score.md.tmpl",
    )
    full_templates = ("subagent-task.md.tmpl",)
    template_names = list(core_templates)
    if standard_enabled:
        template_names.extend(standard_templates)
    if full_enabled:
        template_names.extend(full_templates)
    for name in template_names:
        writer.write(f".agent/templates/{name}", template(name))
    if standard_enabled:
        for name in FEATURE_STAGE_TEMPLATES:
            writer.write(f".agent/templates/features/{name}", template(f"features/{name}"))
        writer.write(".agent/intake/.gitkeep", "")

    writer.copy(skill_dir() / "scripts" / "agent_session.py", ".agent/tools/agent_session.py", executable=True)
    if standard_enabled:
        writer.write(".agent/tools/agent_memory.py", template("agent-memory.py.tmpl"), executable=True)
        writer.write(".agent/tools/agent_context.py", template("agent-context.py.tmpl"), executable=True)
    if full_enabled:
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
    writer.write("scripts/agent_runlog.py", template("agent-runlog.py.tmpl"), executable=True)
    writer.write("scripts/agent_score.py", template("agent-score.py.tmpl"), executable=True)
    writer.write("scripts/agent_migrate.py", template("agent-migrate.py.tmpl"), executable=True)
    if standard_enabled:
        writer.write("scripts/agent_knowledge.py", template("agent-knowledge.py.tmpl"), executable=True)
        writer.write("scripts/agent_invariants.py", template("agent-invariants.py.tmpl"), executable=True)
        writer.write("scripts/agent_capabilities.py", template("agent-capabilities.py.tmpl"), executable=True)
        writer.write("scripts/agent_skill_hygiene.py", template("agent-skill-hygiene.py.tmpl"), executable=True)
        writer.write("scripts/agent_project_skills.py", template("agent-project-skills.py.tmpl"), executable=True)
        writer.write("scripts/agent_runtime.py", template("agent-runtime.py.tmpl"), executable=True)
        writer.write("scripts/agent_task.py", template("agent-task.py.tmpl"), executable=True)
        writer.write("scripts/agent_verify.py", template("agent-verify.py.tmpl"), executable=True)
        writer.write("scripts/agent_gc.py", template("agent-gc.py.tmpl"), executable=True)
        writer.write("scripts/agent_security.py", template("agent-security.py.tmpl"), executable=True)
        writer.write("scripts/agent_resources.py", template("agent-resources.py.tmpl"), executable=True)
    if full_enabled:
        writer.write("scripts/agent_tooling.py", template("agent-tooling.py.tmpl"), executable=True)
        writer.write("scripts/agent_sync_skills.py", template("agent-sync-skills.py.tmpl"), executable=True)

    writer.write("docs/index.md", render(template("docs-index.md.tmpl"), values))
    writer.write("docs/QUALITY.md", render(template("docs-quality.md.tmpl"), values))
    if standard_enabled:
        writer.write("docs/ARCHITECTURE.md", render(template("docs-architecture.md.tmpl"), values))
        writer.write("docs/RELIABILITY.md", render(template("docs-reliability.md.tmpl"), values))
        writer.write("docs/QUALITY_SCORE.md", render(template("docs-quality-score.md.tmpl"), values))
        writer.write("docs/AI_CODING_GLOSSARY.md", render(template("docs-ai-coding-glossary.md.tmpl"), values))
        writer.write("docs/DOMAIN_GLOSSARY.md", render(template("docs-domain-glossary.md.tmpl"), values))
        writer.write("docs/DEV_MAP.md", render(template("docs-dev-map.md.tmpl"), values))
        writer.write("docs/LOOP_ENGINEERING.md", render(template("docs-loop-engineering.md.tmpl"), values))
        writer.write("docs/RESOURCES.md", render(template("docs-resources.md.tmpl"), values))
        writer.write("docs/AGENT_RUNTIME_ARCHITECTURE.md", render(template("docs-agent-runtime-architecture.md.tmpl"), values))
        writer.write("docs/SKILL_RUNTIME.md", render(template("docs-skill-runtime.md.tmpl"), values))
        writer.write("docs/features/INDEX.md", render(template("docs-features-index.md.tmpl"), values))
        writer.write("docs/features/.gitkeep", "")
        writer.write("docs/tech-debt.md", render(template("docs-tech-debt.md.tmpl"), values))
        writer.write("docs/adr/README.md", render(template("docs-adr-index.md.tmpl"), values))
        writer.write("docs/rfcs/README.md", render(template("docs-rfc-index.md.tmpl"), values))
        writer.write("docs/incidents/README.md", render(template("docs-incidents-index.md.tmpl"), values))
    if full_enabled:
        writer.write("docs/SECURITY.md", render(template("docs-security.md.tmpl"), values))
        writer.write("docs/TOOLING.md", render(template("docs-tooling.md.tmpl"), values))

    if not args.no_create_layout:
        for directory in dirs:
            writer.write(f"{directory.rstrip('/')}/.gitkeep", "")

    if not args.no_makefile:
        writer.write("Makefile", template("Makefile.tmpl"))

    print(f"project root: {root}")
    print(f"governance profile: {governance_profile}")
    print(f"layout: {args.layout}")
    print(f"create layout dirs: {'no' if args.no_create_layout else 'yes'}")
    print(f"mode: {'dry-run' if args.dry_run else 'write'}")
    labels = (
        ("would create" if args.dry_run else "created", writer.created),
        ("would update" if args.dry_run else "updated", writer.updated),
        ("unchanged", writer.unchanged),
        ("preserved append-only", writer.preserved),
        ("conflicts", writer.conflicts),
    )
    for label, items in labels:
        if items:
            print(f"{label}:")
            for item in items:
                print(f"  {item}")

    if writer.conflicts:
        print("note: existing different files were preserved; merge manually or rerun with --force only if overwriting is intended")
    if writer.preserved:
        print("note: append-only stores were preserved to avoid losing runlog, session, memory, or context history")

    if not args.dry_run:
        check = root / "scripts" / "agent_check.py"
        if check.exists():
            print("next: python3 scripts/agent_check.py")
            if openspec_enabled:
                print("next: python3 scripts/agent_spec.py doctor")
            print("next: python3 scripts/agent_validate.py --list")
            print("next: python3 scripts/agent_migrate.py doctor")
            if standard_enabled:
                print("next: python3 scripts/agent_capabilities.py doctor")
                print("next: python3 scripts/agent_runtime.py doctor")
                print("next: python3 scripts/agent_task.py doctor")
                print("next: python3 scripts/agent_verify.py doctor")
                print("next: python3 scripts/agent_gc.py doctor")
            if full_enabled:
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
    parser.add_argument("--governance-profile", choices=sorted(GOVERNANCE_PROFILES), help="Governance scaffold size: core, standard, or full. Defaults to full for blank projects and standard for existing projects.")
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
    parser.add_argument("--architecture-intake", default="", help="Path to JSON architecture interview intake for runtime/model selection")
    parser.add_argument("--no-openspec", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--no-makefile", action="store_true")
    parser.add_argument("--no-create-layout", action="store_true")
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    if args.governance_profile is None:
        args.governance_profile = default_governance_profile(Path(args.root).expanduser().resolve())
    try:
        return init_project(args)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
