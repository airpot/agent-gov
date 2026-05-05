---
name: agent-gov
description: Govern Codex/Claude-ready repositories with embedded OpenSpec-style specification management, harness engineering, technology stack and directory layout contracts, durable docs and knowledge metadata, repo-local long-term memory, context budget management, workflow and worktree governance, implementation discipline, capability and integration governance, runlog evidence tracing, ACI-friendly bounded tooling, optional policy-as-code and supply-chain checks, ADR/RFC/postmortem records, governance health scoring/evals, VS Code Remote-friendly session continuity, native hook adapters, subagent orchestration, skill distribution, handoff/resume automation, validation commands, and review-fix gates. Use when the user asks to initialize, retrofit, audit, or maintain an agent-governed project; make a repo agent-ready; add or repair embedded spec/harness/session/memory/context/workflow/worktree/implementation-discipline/capabilities/runlog/tooling/security/evals/ADR/RFC/subagent/hooks/skills management; or recover long-running Codex work across sessions.
---

# Agent Gov

## Overview

Govern a repository so long-running Codex/Claude work can be specified, planned, isolated, executed, checkpointed, resumed, reviewed, validated, and maintained without depending on a fragile chat transcript.

## Workflow

1. **Inspect the repository**
   - Check `pwd`, `git status --short`, existing `AGENTS.md`, `CLAUDE.md`, `openspec/`, `.agent/spec.json`, `.agent/`, `Makefile`, and `scripts/`.
   - If the user is in VS Code Remote or another remote workspace, treat the remote repository path as the authoritative workspace.

2. **Choose initialization scope**
   - Ask for or infer the technology stack before initialization. If unknown, ask whether to continue with `unspecified`.
   - Ask for the fixed project directory layout. Use a built-in layout (`minimal`, `python-app`, `node-app`, `web-app`, `service`, `library`) or explicit extra directories.
   - Choose the initialization profile that matches the repository maturity: `core` for minimal spec/harness/session continuity, `standard` for durable workflow/task/memory/context governance plus disabled-by-default MCP policy, or `full` for native Codex/Claude adapters, subagent orchestration, security/tooling, and skill distribution. Default to `standard`; use `full` only when the user asks for the complete framework.
   - Use `references/spec-management.md` for embedded OpenSpec-style project specification setup.
   - Use `references/workflow-governance.md` for workflow profiles, lifecycle gates, task-board continuity, feature-stage documents, task risk/autonomy, plan quality, TDD/debugging evidence, diff traceability, worktree isolation, review order, human review evidence, and completion proof.
   - Use `references/implementation-discipline.md` for assumption clarification, simplicity-first implementation, surgical diffs, and verifiable goals.
   - Use `references/harness-management.md` for command, validation, capability governance, runlog evidence, ACI tooling, security/supply-chain suites, governance scoring/evals, dev map, harness evolution, MCP policy, governance-gc, ADR/RFC/postmortem records, native adapters, context budget, skill distribution, and repo-harness setup.
   - Use `references/session-continuity.md` for `.agent/sessions/`, `.agent/memory/`, rollover, checkpoint, memory retrieval, and resume behavior.
   - Use `references/context-budget.md` for compression-safe governance docs, token budget scans, and subagent output limits.
   - Use `references/subagent-orchestration.md` when the project needs delegated agent roles, snapshot contracts, or multi-agent handoff rules.
   - Use `references/review-fix-loop.md` when release readiness or review gates are part of the request.

3. **Run deterministic initialization**
   - Prefer `scripts/init_agent_project.py <repo-root>`.
   - Pass `--tech-stack <stack>` and `--layout <layout>` when known.
   - Pass `--governance-profile core|standard|full` when the user wants a smaller or larger governance footprint.
   - Use `--dir <path>` for additional required directories.
   - Add `--remote-kind ssh|devcontainer|wsl|local|unknown` when known.
   - The initializer uses agent-gov's embedded spec layer; it does not install or call a global OpenSpec CLI.
   - Add `--no-claude` only when the user does not want Claude support.
   - Do not overwrite existing files unless the user explicitly asks for `--force`.

4. **Create or verify session continuity**
   - Ensure `.agent/config.json`, `.agent/sessions/index.json`, `.agent/sessions/active.md`, `.agent/tools/agent_session.py`, and session templates exist.
   - For active long-running work, use the generated `.agent/tools/agent_session.py start/checkpoint/bootstrap/compact/doctor/resume/status` commands.
   - Require new sessions to run `python3 .agent/tools/agent_session.py bootstrap` before editing when an active session exists.

5. **Create or verify long-term memory**
   - Ensure `.agent/memory.json`, `.agent/memory/events.jsonl`, `.agent/memory/summaries/`, and `.agent/tools/agent_memory.py` exist.
   - Treat memory as advisory retrieval, not the source of truth; durable truth belongs in embedded specs, task-board records, dev map entries, feature docs, ADR/RFC/postmortem records, runlog evidence, validation notes, and active session handoff files.
   - Use progressive disclosure: `timeline`, then `search`, then `detail` only for selected memory ids.
   - Store concise summaries, decisions, validation, and retrieval handles; do not store raw transcripts or secrets.

6. **Create or verify context budget management**
   - Ensure `.agent/context.json`, `.agent/context/stats.jsonl`, `.agent/context/latest.md`, and `.agent/tools/agent_context.py` exist.
   - Track agent-facing docs, bootstrap packets, memory digests, embedded spec change docs, and subagent output budgets.
   - Use `scan`, `suggest`, and `validate-pair` to keep governance docs compact while preserving headings, code blocks, inline code, URLs, paths, commands, versions, and technical names.
   - Never send sensitive-looking files or private environment files to external compression services.

7. **Create or verify workflow and worktree governance**
   - Ensure `.agent/workflow.json`, `.agent/workflow-profiles.json`, `.agent/task-board.json`, `.agent/risk-zones.json`, `.agent/review-policy.json`, `.agent/worktrees.json`, `.agent/templates/implementation-plan.md.tmpl`, `.agent/templates/debugging-record.md.tmpl`, and `.agent/templates/features/*.md.tmpl` exist.
   - Choose the lightest workflow profile that covers the task risk: `tiny`, `bugfix`, `standard`, or `full`.
   - Use `scripts/agent_task.py` to keep non-tiny task state in `.agent/task-board.json` and feature-stage documents under `docs/features/<task-id>/`.
   - For `standard` and `full` tasks, require `review_gate.status=pass`, an existing latest review document, and no open blocker/major/minor findings before task state can become `done`.
   - Use workflow gates for task risk/autonomy, design/spec approval, plan quality, implementation discipline, diff traceability, isolated execution, TDD evidence, systematic debugging, spec review, quality review, human review evidence, completion verification, handoff, and finish choices.
   - Require high and critical risk work to record approval/review evidence; critical work is not autonomous modification work.
   - Prefer ignored git worktrees for feature work, implementation-plan execution, and risky refactors; record baseline validation before edits.
   - Require fresh validation evidence before completion, merge, PR, archive, or handoff claims.
   - Treat destructive branch/worktree cleanup as explicit-user-confirmation work.

8. **Create or verify capability governance and runlog evidence**
   - Ensure core scoring and evidence files exist in every profile: `.agent/manifest.json`, `.agent/runlog.jsonl`, `.agent/evals.json`, `.agent/evals/latest.md`, `scripts/agent_runlog.py`, `scripts/agent_score.py`, and `scripts/agent_migrate.py`.
   - For `standard` and `full`, ensure `.agent/capabilities.json`, `.agent/dev-map.json`, `.agent/harness-evolution.json`, `.agent/mcp-policy.json`, `.agent/governance-gc.json`, `scripts/agent_capabilities.py`, `scripts/agent_verify.py`, and `scripts/agent_gc.py` exist.
   - For `full`, ensure `.agent/tooling.json`, `.agent/security.json`, `scripts/agent_tooling.py`, and `scripts/agent_security.py` exist.
   - Treat `.agent/manifest.json` as the generated governance manifest for required paths, JSON schemas, JSONL stores, and score dimensions; update it when the governance surface changes.
   - Use `.agent/capabilities.json` to record enabled skills, tools, MCP/integration entries, resources, native adapters, owner, risk, capability class, permission shape, and validation commands.
   - Use `.agent/runlog.jsonl` for compact evidence of validation runs, session lifecycle events, accepted review exceptions, and high-risk capability use.
   - Use `.agent/tooling.json` and `scripts/agent_tooling.py` for bounded, path-first, line-numbered repository inspection.
   - Use `.agent/security.json` and `scripts/agent_security.py` for optional policy-as-code, secret scan, dependency audit, SBOM, and license scan command slots.
   - Use `.agent/evals.json` and `scripts/agent_score.py` for local governance health scoring and `.agent/evals/latest.md` dashboard refresh.
   - Ensure `docs/AI_CODING_GLOSSARY.md`, `docs/adr/`, `docs/rfcs/`, `docs/incidents/`, and their templates exist for shared terminology, durable decisions, proposals, and postmortems.
   - Ensure `docs/DEV_MAP.md` exists as a concise repository navigation map, not a full file inventory.
   - Use `.agent/harness-evolution.json` and `python3 scripts/agent_gc.py classify ...` to classify repeated failures and promote fixes into rules, skills, scripts, workflow gates, role contracts, tool/MCP policy, or docs.
   - Treat `.agent/mcp-policy.json` as optional and disabled by default until the project explicitly enables external integrations; it defines trust boundaries even when no MCP server is active.
   - Keep runlog entries structured and concise; do not store raw transcripts, terminal scrollback, secrets, or private host data.

9. **Create or verify subagent orchestration**
   - This is generated by the `full` profile.
   - Ensure `.agent/subagents.json`, `.agent/role-contracts.json`, and `.agent/templates/subagent-task.md.tmpl` exist.
   - Treat subagent delegation as optional and permission-gated: use it only when the current platform and higher-priority instructions allow it.
   - Require bounded roles, disjoint write ownership, minimal input facts, context-budgeted supporting notes, workflow status values, and `===SNAPSHOT===` JSON summaries for delegated work.
   - Enforce the role-contract rule that finder/reviewer roles report findings and route fixes back; they do not fix their own findings directly.
   - For delegated implementation, handle `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, and `BLOCKED` before review; run spec review before quality review and re-review after fixes.
   - Record accepted subagent snapshots in `.agent/sessions/` handoff, changes, or validation files before compaction.

10. **Create or verify native adapters**
   - This is generated by the `full` profile.
   - Ensure `.agent/hooks.json`, `.agent/knowledge.json`, `.agent/skill-distribution.json`, and `.agent/tools/governance_hook.py` exist.
   - Ensure Codex adapters exist: `.codex/config.toml`, `.codex/hooks.json`, and `.codex/agents/governance-*.toml`.
   - Ensure Claude adapters exist when Claude support is enabled: `.claude/settings.json` and `.claude/agents/governance-*.md`.
   - Preserve existing native config files by default; report skipped files for manual merge.

11. **Validate**
   - Run the generated project check when available: `python3 scripts/agent_check.py`.
   - Check migration and version drift when available: `python3 scripts/agent_migrate.py doctor`.
   - Run `python3 scripts/agent_spec.py doctor` and `python3 scripts/agent_spec.py list --json`.
   - Inspect executable feedback commands: `python3 scripts/agent_validate.py --list`.
   - Check the knowledge store and invariants: `python3 scripts/agent_knowledge.py` and `python3 scripts/agent_invariants.py`.
   - Check capability governance and runlog health: `python3 scripts/agent_capabilities.py doctor` and `python3 scripts/agent_runlog.py doctor`.
   - Check ACI tooling and security baseline health: `python3 scripts/agent_tooling.py doctor` and `python3 scripts/agent_security.py doctor`.
   - Check task-board and mechanical verification health: `python3 scripts/agent_task.py doctor` and `python3 scripts/agent_verify.py doctor`.
   - Check governance-gc health: `python3 scripts/agent_gc.py doctor`.
   - Check governance score health: `python3 scripts/agent_score.py doctor`; refresh score with `python3 scripts/agent_score.py score --write` before release handoff.
   - Check memory health: `python3 .agent/tools/agent_memory.py doctor`.
   - Check context budget health: `python3 .agent/tools/agent_context.py doctor`.
   - Confirm workflow and worktree policy are covered by `python3 scripts/agent_check.py`.
   - Check skill sync readiness: `python3 scripts/agent_sync_skills.py --dry-run`.
   - Skip commands whose scripts were intentionally not generated by the selected governance profile.
   - Report skipped files, existing files, and any manual merge required.

12. **Review before handoff**
   - For substantial initialization work, create or update a review-fix record in the controlling skill lifecycle.
   - If the user asks to review or audit an agent-governed project, use `references/review-fix-loop.md` and repeat review, fix, revalidation, and review until the latest review has no blocker, major, or minor findings.
   - Do not claim completion, handoff, merge readiness, archive readiness, or release readiness for `standard` or `full` tasks until the generated task-board review gate is `pass`.
   - Confirm that resume instructions do not depend on unsaved editor buffers, terminal scrollback, or Codex native thread history.

## Resource Map

- `scripts/init_agent_project.py`: Initialize or retrofit a target repository.
- `scripts/agent_session.py`: Source for the generated target-project `.agent/tools/agent_session.py`.
- `assets/templates/agent-memory.py.tmpl`: Source for generated target-project `.agent/tools/agent_memory.py`.
- `assets/templates/agent-context.py.tmpl`: Source for generated target-project `.agent/tools/agent_context.py`.
- `assets/templates/agent-capabilities.py.tmpl`: Source for generated target-project `scripts/agent_capabilities.py`.
- `assets/templates/agent-runlog.py.tmpl`: Source for generated target-project `scripts/agent_runlog.py`.
- `assets/templates/agent-tooling.py.tmpl`: Source for generated target-project `scripts/agent_tooling.py`.
- `assets/templates/agent-security.py.tmpl`: Source for generated target-project `scripts/agent_security.py`.
- `assets/templates/agent-score.py.tmpl`: Source for generated target-project `scripts/agent_score.py`.
- `assets/templates/agent-migrate.py.tmpl`: Source for generated target-project `scripts/agent_migrate.py`.
- `assets/templates/agent-task.py.tmpl`: Source for generated target-project `scripts/agent_task.py`.
- `assets/templates/agent-verify.py.tmpl`: Source for generated target-project `scripts/agent_verify.py`.
- `assets/templates/agent-gc.py.tmpl`: Source for generated target-project `scripts/agent_gc.py`.
- `assets/templates/agent-spec.py.tmpl`: Source for generated target-project `scripts/agent_spec.py`.
- `references/workflow-governance.md`: Workflow gates, worktree isolation, TDD/debugging evidence, review sequencing, and completion proof.
- `references/implementation-discipline.md`: Assumption clarification, simplicity-first implementation, surgical change boundaries, and goal-driven verification.
- `references/spec-management.md`: Embedded OpenSpec-style specification rules.
- `references/harness-management.md`: Harness files, native adapters, commands, validation, and safety rules.
- `references/session-continuity.md`: Codex/Claude session continuity and long-term memory protocol for VS Code Remote work.
- `references/context-budget.md`: Context budget, safe compression, and token-scan protocol.
- `references/subagent-orchestration.md`: Permission-gated subagent roles, dispatch templates, and snapshot contracts.
- `references/review-fix-loop.md`: Review-fix gate for initialized projects.
- `assets/templates/`: Target-project templates rendered by `init_agent_project.py`.

## Guardrails

- Do not treat Codex thread history, VS Code tabs, terminal scrollback, or unsaved buffers as durable state.
- Do not store secrets, SSH keys, tokens, host credentials, or private environment values in `.agent/`.
- Do not store raw transcripts, terminal scrollback, secrets, or private host data in `.agent/runlog.jsonl`.
- Preserve existing project files by default; create missing files and report conflicts instead of silently rewriting.
- Prefer simple, direct implementations and justify new abstractions, speculative flexibility, or broad cleanup with recorded evidence.
- Keep `AGENTS.md` short and stable; move volatile state to `.agent/sessions/` and embedded spec changes.
- Keep `CLAUDE.md` thin; prefer importing or pointing to `AGENTS.md` rather than duplicating rules.
- Keep context compression semantic, not stylistic: compress redundancy and filler, preserve technical facts and retrieval handles.
- Do not force subagent use, model pinning, or delegation-only execution when the active Codex/Claude environment does not permit it.
- Do not claim completion, merge readiness, PR readiness, or successful handoff without fresh validation evidence recorded in session or runlog state.
- Do not create, discard, or force-delete worktrees or branches without following the project worktree policy and explicit user confirmation for destructive actions.
