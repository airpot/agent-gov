---
name: agent-gov
description: Initialize, retrofit, audit, and maintain Codex/Claude-ready repositories with repo-local governance. Use when making a project agent-ready or managing embedded specs, harness checks, sessions, memory, context budgets, workflow/task boards, worktrees, loop engineering, review-fix gates, knowledge promotion bundles, goal contracts, evidence boundaries, capability/resource/runtime policy, project skills, release evidence, archival, or long-running session recovery.
---

# Agent Gov

## Overview

Govern a repository so long-running Codex/Claude work can be specified, planned, isolated, executed, checkpointed, resumed, reviewed, validated, archived, and maintained without depending on a fragile chat transcript.

## Workflow

1. **Inspect the repository**
   - Check `pwd`, `git status --short`, existing `AGENTS.md`, `CLAUDE.md`, `openspec/`, `.agent/spec.json`, `.agent/`, `Makefile`, and `scripts/`.
   - If the user is in VS Code Remote or another remote workspace, treat the remote repository path as the authoritative workspace.

2. **Choose initialization scope**
   - Ask for or infer the technology stack before initialization. Include version constraints for languages/runtimes, package managers, frameworks/libraries, datastores/services, deployment targets, and agent runtime/MCP SDKs when they affect design; if unknown, ask whether to continue with `unspecified` and record open version decisions.
   - Ask for the fixed project directory layout. Use a built-in layout (`minimal`, `python-app`, `node-app`, `web-app`, `service`, `library`) or explicit extra directories.
   - Choose the initialization profile that matches the repository maturity: `core` for minimal spec/harness/session continuity, `standard` for durable workflow/task/memory/context governance plus disabled-by-default MCP policy, or `full` for native Codex/Claude adapters, subagent orchestration, security/tooling, and skill distribution. When no profile is specified, blank projects default to `full` and existing projects default to `standard`; use an explicit `--governance-profile` when the user wants a smaller or larger governance footprint.
   - Use `references/spec-management.md` for embedded OpenSpec-style project specification setup, status checks, and mandatory archival of completed changes.
   - Use `references/workflow-governance.md` for workflow profiles, lifecycle gates, task-board continuity, feature-stage documents, loop engineering, task risk/autonomy, plan quality, TDD/debugging evidence, diff traceability, worktree isolation, review order, human review evidence, goal contracts, knowledge promotion review, and completion proof.
   - Use `references/project-blueprint-governance.md` for requirements-interview-to-blueprint flow, global project architecture contracts, runtime/framework decisions, and OpenSpec blueprint-impact sync before implementation.
   - Use `references/implementation-discipline.md` for assumption clarification, simplicity-first implementation, surgical diffs, verifiable goals, and evidence-bounded source adoption.
   - Use `references/harness-management.md` for command, validation, capability governance, project resource catalog governance, Skill-first runtime architecture governance, Skill Runtime Governance, model profile governance, runlog evidence, knowledge promotion bundle checks, evidence-store boundaries, ACI tooling, security/supply-chain suites, governance scoring/evals, dev map, harness evolution, MCP policy, governance-gc, ADR/RFC/postmortem records, native adapters, context budget, project skill governance, skill distribution, and repo-harness setup.
   - Use `references/skill-runtime-governance.md` when governing portable Skill/plugin products, canonical Skill cores, thin host adapters, runtime modes, command lanes, impact benchmarks, shortcut/debt ledgers, or adapter parity.
   - Use `references/skill-self-optimization.md` when governing skill self-optimization, optimization triggers, candidate staging, release-preflight evidence, auto-promote limits, or rollback for agent-system and production skill releases.
   - Use `references/session-continuity.md` for `.agent/sessions/`, `.agent/memory/`, rollover, checkpoint, memory retrieval, resume behavior, compact goal contracts, and current decision summaries.
   - Use `references/context-budget.md` for compression-safe governance docs, token budget scans, subagent output limits, and keeping goal contracts and knowledge bundles compact.
   - Use `references/subagent-orchestration.md` when the project needs delegated agent roles, snapshot contracts, or multi-agent handoff rules.
   - Use `references/review-fix-loop.md` when release readiness, loop engineering, or review gates are part of the request.

3. **Run deterministic initialization**
   - Prefer `scripts/init_agent_project.py <repo-root>`.
   - Pass `--tech-stack <stack>` and `--layout <layout>` when known.
   - Pass `--governance-profile core|standard|full` when the user wants a smaller or larger governance footprint.
   - Use `--dir <path>` for additional required directories.
   - Add `--remote-kind ssh|devcontainer|wsl|local|unknown` when known.
   - The initializer uses agent-gov's embedded spec layer; it does not install or call a global OpenSpec CLI.
   - Add `--no-claude` only when the user does not want Claude support.
   - Do not overwrite existing files unless the user explicitly asks for `--force`.
   - For existing projects, run `--dry-run` first and inspect `would create`, `unchanged`, `preserved append-only`, and `conflicts` before writing.

4. **Create or verify session continuity**
   - Ensure `.agent/config.json`, `.agent/sessions/index.json`, `.agent/sessions/events.jsonl`, `.agent/sessions/active.md`, `.agent/tools/agent_session.py`, and session/offload templates exist.
   - For active long-running work, use the generated `.agent/tools/agent_session.py start/checkpoint/bootstrap/compact/grounding/offload-add/offload-recall/offload-map/rollover/doctor/resume/status/events` commands.
   - Require new sessions to run `python3 .agent/tools/agent_session.py bootstrap` before editing when an active session exists.
   - Keep bootstrap and compact output as compact recovery packets with evidence handles. Do not inline long historical handoff, changes, validation, grounding, memory, context, archived spec, or dirty-status bodies; keep complete dirty state in `refs/git-status-short.txt`.
   - Use `grounding` before implementation after rollover: current repository files, configs, specs, task-board state, runlog evidence, and validation notes override memory summaries and prior chat assumptions.
   - Use `offload-add` for compact cross-session context only when every summary has evidence handles; use `offload-recall` progressively and verify recalled facts against durable truth sources before editing.

5. **Create or verify long-term memory**
   - This is generated by the `standard` and `full` profiles.
   - Ensure `.agent/memory.json`, `.agent/memory/events.jsonl`, `.agent/memory/summaries/`, and `.agent/tools/agent_memory.py` exist.
   - Treat memory as advisory retrieval, not the source of truth; durable truth belongs in embedded specs, task-board records, dev map entries, feature docs, ADR/RFC/postmortem records, runlog evidence, validation notes, and active session handoff files.
   - Use progressive disclosure: `timeline`, then `search`, then `detail` only for selected memory ids.
   - Store concise summaries, decisions, validation, and retrieval handles; do not store raw transcripts or secrets.

6. **Create or verify context budget management**
   - This is generated by the `standard` and `full` profiles.
   - Ensure `.agent/context.json`, `.agent/context/stats.jsonl`, `.agent/context/latest.md`, and `.agent/tools/agent_context.py` exist.
   - Track agent-facing docs, bootstrap packets, memory digests, embedded spec change docs, and subagent output budgets.
   - Use `scan`, `suggest`, and `validate-pair` to keep governance docs compact while preserving headings, code blocks, inline code, URLs, paths, commands, versions, and technical names.
   - Never send sensitive-looking files or private environment files to external compression services.

7. **Create or verify workflow and worktree governance**
   - Ensure `.agent/workflow.json`, `.agent/workflow-profiles.json`, `.agent/task-board.json`, `.agent/risk-zones.json`, `.agent/review-policy.json`, `.agent/worktrees.json`, `.agent/templates/implementation-plan.md.tmpl`, `.agent/templates/debugging-record.md.tmpl`, and `.agent/templates/features/*.md.tmpl` exist.
   - Choose the lightest workflow profile that covers the task risk: `tiny`, `bugfix`, `standard`, or `full`.
   - For every non-Q&A request, proactively classify request kind, risk, required gates, and whether task/spec records are needed before editing.
   - Preserve the raw user goal and write a refined goal before setting a durable task or session goal. Record rationale, non-goals, constraints, success evidence, confirmation status, and open questions.
   - Use `scripts/agent_task.py` to keep non-tiny task state in `.agent/task-board.json` and feature-stage documents under `docs/features/<task-id>/`.
   - For non-tiny tasks, complete the requirements interview gate before design or implementation: ask one unresolved question at a time, give a recommended answer with rationale, cross-check user claims against current code/docs, and update `docs/DOMAIN_GLOSSARY.md` for stable terms.
   - Complete technology-stack and runtime intake before initialization and before non-tiny design when stack, runtime, layout, or version choices affect the solution; ask one version question at a time when needed, record exact versions, supported ranges, LTS lines, managed-service versions, or defer-to-lockfile policies, and convert the interview into structured `--architecture-intake` input when possible.
   - Decompose work before implementation: tiny work gets a minimal checklist, bugfix work gets a reproduction/root-cause/fix/regression chain, and standard/full work gets subtasks or a task graph with dependencies, file scope, validation, and next task.
   - Run review -> fix -> re-review for every task profile. Tiny work uses lightweight review evidence in the active session, runlog, or `.agent/intake/` when no task-board record exists; bugfix work reviews reproduction/root-cause/regression; standard/full work uses protected stage reviews.
   - For non-tiny iterative work, choose a loop primitive before repeating: `turn_based`, `goal_based`, `time_based`, `scheduled_routine`, or `scripted_workflow`. Use `goal_based` only for verifiable internal convergence, route external polling to `time_based` or `scheduled_routine`, and require pilot/cross-check/cost evidence for scripted workflows.
   - For non-tiny iterative work, require a loop contract from `.agent/loop-engineering.json`: primitive, loop type, readiness level, goal, observation signal, iteration budget, stop conditions, evidence path, owner role, evaluator boundary, stop reason, and escalation rule.
   - Require unattended loops to have attempt ledger evidence, stable failure signatures, quota/circuit-breaker controls, human interrupt points, explicit state transitions, resume safety, and safe stop behavior before automatic continuation.
   - Require durable recurring work to record routine id, trigger/cadence, run location, permission mode, resource and credential boundary, per-run stop condition, disable/expiry policy, owner, and evidence path before it is treated as a scheduled routine.
   - When a primary lane is blocked by a human decision, allow only bounded safe fallback work that preserves the unresolved gate and stays within read-only analysis, test preparation, docs review, planning, or artifact inventory.
   - Stop repeating when the same failure recurs; change strategy, classify a harness gap, or ask for human input instead of retrying the same action without new evidence.
   - For every task-board-backed task, require `review_gate.status=pass`, an existing latest review document, no open blocker/major/minor findings, and completed task decomposition before task state can become `done`.
   - Use workflow gates for task risk/autonomy, design/spec approval, plan quality, implementation discipline, diff traceability, isolated execution, TDD evidence, systematic debugging, spec review, quality review, human review evidence, completion verification, handoff, and finish choices.
   - Require high and critical risk work to record approval/review evidence; critical work is not autonomous modification work.
   - Prefer ignored git worktrees for feature work, implementation-plan execution, and risky refactors; record baseline validation before edits.
   - Require fresh validation evidence before completion, merge, PR, archive, or handoff claims.
   - When an embedded spec change reaches `all_done`, archive it with `python3 scripts/agent_spec.py archive <name>` before claiming completion, handoff, release, or archive readiness.
   - Treat destructive branch/worktree cleanup as explicit-user-confirmation work.

8. **Create or verify capability governance and runlog evidence**
   - Ensure core scoring and evidence files exist in every profile: `.agent/manifest.json`, `.agent/runlog.jsonl`, `.agent/evals.json`, `.agent/evals/latest.md`, `scripts/agent_runlog.py`, `scripts/agent_score.py`, and `scripts/agent_migrate.py`.
   - For `standard` and `full`, ensure `.agent/capabilities.json`, `.agent/dev-map.json`, `.agent/skill-hygiene.json`, `.agent/loop-engineering.json`, `.agent/harness-evolution.json`, `.agent/mcp-policy.json`, `.agent/governance-gc.json`, `scripts/agent_capabilities.py`, `scripts/agent_skill_hygiene.py`, `scripts/agent_verify.py`, and `scripts/agent_gc.py` exist.
   - For `full`, ensure `.agent/tooling.json`, `.agent/security.json`, `scripts/agent_tooling.py`, and `scripts/agent_security.py` exist.
   - Treat `.agent/manifest.json` as the generated governance manifest for required paths, JSON schemas, JSONL stores, and score dimensions; update it when the governance surface changes.
   - Use `.agent/capabilities.json` to record enabled skills, tools, MCP/integration entries, resource-catalog capability, native adapters, owner, risk, capability class, permission shape, provider status (`present`, `missing`, `unknown`, or `degraded`), required/optional classification, fallback behavior, and validation commands.
   - Use `.agent/manifest.json#/governance_presets` for selected presets, extensions, and catalog entries with source status, version or revision, owner, permission scope, generated paths, validation, conflict behavior, dry-run support, and no automatic dependency installation.
   - Use `.agent/resources.json`, `scripts/agent_resources.py`, `.agent/templates/resource-secrets.local.env.tmpl`, and `docs/RESOURCES.md` to govern project resource assets such as servers, databases, repositories, deployment targets, compute machines, endpoint references, credential references, usage rules, allowed actions, and health checks.
   - Before using a remote server, database, repository, deployment target, or compute machine, run `python3 scripts/agent_resources.py match --intent "<intent>" --json`, then `python3 scripts/agent_resources.py resolve <resource-id> --json`; do not rely on chat memory, shell history, or trial-and-error discovery.
   - Keep raw account passwords, tokens, SSH private keys, database URLs with embedded credentials, and private secret material out of `.agent/resources.json`; store only refs such as `env:`, `file-ref:`, `vault:`, `proxy:`, `op:`, or `keychain:`.
   - Use `.agent/runtime-policy.json`, `.agent/model-profiles.json`, `.agent/agent-runtime.json`, `scripts/agent_runtime.py`, and `docs/AGENT_RUNTIME_ARCHITECTURE.md` to govern product-level Skill-first runtime architecture, project target selection (`agent`, `mcp-server`, `hybrid`, or `library`), initialization architecture interview output, runtime adapter choice, MCP server exposure boundaries, model provider profiles, and application-state boundaries.
   - Use `.agent/blueprint.json`, `docs/PROJECT_BLUEPRINT.md`, `.agent/templates/project-blueprint.md.tmpl`, and `scripts/agent_blueprint.py` as the global product and architecture blueprint. For `standard` and `full` projects, update or verify the blueprint after requirements interview and before feature-level OpenSpec implementation when product purpose, architecture, runtime/framework, technology version constraints, layout, data/state, resource, security, MCP, validation, or harness decisions change.
   - Use `.agent/skill-runtime.json` and `docs/SKILL_RUNTIME.md` to govern portable Skill/plugin product architecture: canonical skill core, thin host adapters, runtime modes, command lanes, separated review lanes, benchmark evidence, and deliberate shortcut/debt ledgers.
   - Use `.agent/skill-optimization.json`, `docs/SKILL_OPTIMIZATION.md`, `scripts/agent_skill_opt.py`, and `skillflows/<skill>/optimization/` to govern skill self-optimization, candidate staging, release-preflight evidence, rejected edits, promotion limits, and rollback. Before every agent-system or production skill release, run or verify a current self-optimization preflight; release checks validate existing evidence and fail closed with a repair command when it is missing, stale, or failing.
   - During initialization, convert the user's architecture conversation into structured `--architecture-intake <json-file>` input when possible; the initializer does not read transient chat history directly.
   - Treat Strands as the default Skill-first agent runtime adapter, not as the architecture standard; keep Pydantic AI, LangGraph, MCP SDKs, and FastMCP-style servers as optional application-owned adapters and keep runtime dependencies in application code, not agent-gov.
   - For `agent` and `hybrid` projects, treat runtime adoption as framework-first by default: run `python3 scripts/agent_runtime.py doctor`, `python3 scripts/agent_runtime.py readiness`, and `python3 scripts/agent_runtime.py report --json`, follow `.agent/agent-runtime.json` `runtime_adoption.package_plan` when adding application dependencies, and do not hand-write direct LLM orchestration unless `.agent/agent-runtime.json` records an accepted `manual_llm_exception` with rationale, owner, review evidence, validation evidence, and residual risk.
   - For MCP server projects, do not force model profiles or agent orchestration; require explicit MCP tool/resource/prompt, transport, host/client, credential, and destructive-operation boundaries.
   - Use `.agent/runlog.jsonl` for compact evidence of validation runs, session lifecycle events, accepted review exceptions, and high-risk capability use.
   - Use `.agent/tooling.json` and `scripts/agent_tooling.py` for bounded, path-first, line-numbered repository inspection.
   - Use `.agent/security.json` and `scripts/agent_security.py` for optional policy-as-code, secret scan, dependency audit, SBOM, and license scan command slots.
   - Use `.agent/evals.json` and `scripts/agent_score.py` for local governance health scoring and `.agent/evals/latest.md` dashboard refresh.
   - Ensure `docs/AI_CODING_GLOSSARY.md`, `docs/DOMAIN_GLOSSARY.md`, `docs/adr/`, `docs/rfcs/`, `docs/incidents/`, and their templates exist for shared terminology, durable decisions, proposals, and postmortems.
   - Ensure `docs/DEV_MAP.md` exists as a concise repository navigation map, not a full file inventory.
   - Use `.agent/loop-engineering.json` and `docs/LOOP_ENGINEERING.md` to govern loop primitive selection, bounded work loops, review-fix loops, debugging loops, eval optimization loops, session recovery loops, goal proof contracts, scheduled routines, scripted workflows, usage evidence, readiness levels, attempt ledgers, quota/circuit-breaker controls, safe fallback lanes, and explicit loop state transitions.
   - Use `.agent/harness-evolution.json` and `python3 scripts/agent_gc.py classify ...` to classify repeated failures and promote fixes into rules, skills, scripts, workflow gates, loop contracts, role contracts, tool/MCP policy, or docs.
   - Use `.agent/mechanical-checks.json#/checks/strict_agent_contracts`, `.agent/baselines.json#/regression_criteria`, and `.agent/governance-gc.json#/component_expiry` for contract fixtures, protected-action evidence, provider fallback checks, bootstrap compactness, regression criteria, and stale load-bearing component review.
   - Use `.agent/skill-hygiene.json` and `scripts/agent_skill_hygiene.py` as a read-only skill topology/source/hash/frontmatter/symlink/risk-signal scan; cleanup and canary injection require explicit human confirmation.
   - For `standard` and `full`, ensure `.agent/project-skills.json` and `scripts/agent_project_skills.py` exist.
   - Use `.agent/project-skills.json` as the canonical repo-local registry for intentionally governed project skills; keep `skills.manifest.json` as the production/release boundary and `workspace-tools.manifest.json` as workspace-only helper awareness when present.
   - When installing a skill while operating in a project, default to project-local `.codex/skills/<skill>`; install to global/user skill directories only when the user explicitly requests a global install.
   - Treat both project-local and global installed skills as governed inventory: `scripts/agent_project_skills.py report --json` must surface both, and unmanaged global installs require registration or an explicit policy exception.
   - Use `scripts/agent_project_skills.py report --json` before adopting, updating, deprecating, removing, pinning, or reclassifying project skills; use `snapshot --write` only after the lifecycle change has been reviewed and validated.
   - Treat project skill lifecycle changes as non-trivial governance work: open or use an embedded spec, run review -> fix -> review through the controlling skill lifecycle, run validation, and archive the completed embedded spec before claiming completion.
   - Treat `.agent/mcp-policy.json` as optional and disabled by default until the project explicitly enables external integrations; it defines trust boundaries even when no MCP server is active, and raw credentials must stay behind vault/proxy boundaries outside the repo, harness, and sandbox.
   - Treat high-risk, production write, destructive, release, billing, privileged, or cost-bearing resource use as approval-gated work and record high-risk use in runlog when available.
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
   - Keep native hooks EOF-safe, UTF-8-BOM tolerant, valid-JSON when the host requires JSON, empty-context preserving, and explicit about whether hook files/manifests are preserved, stripped, suppressed, or skipped during packaging.

11. **Validate**
   - Run the generated project check when available: `python3 scripts/agent_check.py`.
   - Before agent/hybrid/MCP runtime implementation in `standard` or `full` projects, run strict readiness: `python3 scripts/agent_check.py --strict` or `python3 scripts/agent_validate.py readiness --require-configured`.
   - Check migration and version drift when available: `python3 scripts/agent_migrate.py doctor`.
   - Run `python3 scripts/agent_spec.py doctor` and `python3 scripts/agent_spec.py list --json`; `doctor` must fail while a completed `all_done` change remains active instead of archived.
   - Inspect executable feedback commands: `python3 scripts/agent_validate.py --list`.
   - Check the knowledge store and invariants: `python3 scripts/agent_knowledge.py` and `python3 scripts/agent_invariants.py`.
   - Check capability governance and runlog health: `python3 scripts/agent_capabilities.py doctor` and `python3 scripts/agent_runlog.py doctor`.
   - Check ACI tooling and security baseline health: `python3 scripts/agent_tooling.py doctor` and `python3 scripts/agent_security.py doctor`.
   - Check task-board, skill hygiene, project skill governance, and mechanical verification health: `python3 scripts/agent_task.py doctor`, `python3 scripts/agent_skill_hygiene.py doctor`, `python3 scripts/agent_project_skills.py doctor`, and `python3 scripts/agent_verify.py doctor`.
   - Check skill optimization governance before agent-system or production skill releases: `python3 scripts/agent_skill_opt.py doctor`, `python3 scripts/agent_skill_opt.py preflight --skill <skill>`, and release-check validation of the generated preflight evidence.
   - Check governance-gc health: `python3 scripts/agent_gc.py doctor`.
   - Check governance score health: `python3 scripts/agent_score.py doctor`; refresh score with `python3 scripts/agent_score.py score --write` before release handoff.
   - Check session offload health through `python3 .agent/tools/agent_session.py doctor`, `python3 scripts/agent_verify.py doctor`, and `python3 scripts/agent_score.py score --json`.
   - Check memory health: `python3 .agent/tools/agent_memory.py doctor`.
   - Check context budget health: `python3 .agent/tools/agent_context.py doctor`.
   - Confirm workflow and worktree policy are covered by `python3 scripts/agent_check.py`.
   - Check skill sync readiness: `python3 scripts/agent_sync_skills.py --dry-run`.
   - Skip commands whose scripts were intentionally not generated by the selected governance profile.
   - Report skipped files, existing files, and any manual merge required.
   - Treat `conflicts` in initializer dry-run output as a manual merge queue; append-only stores are preserved to avoid losing history.

12. **Review before handoff**
   - For substantial initialization work, create or update a review-fix record in the controlling skill lifecycle.
   - If the user asks to review or audit an agent-governed project, use `references/review-fix-loop.md` and repeat review, fix, revalidation, and review until the latest review has no blocker, major, or minor findings.
   - For active embedded spec changes, run `python3 scripts/agent_spec.py status --change <name> --json`; if the state is `all_done`, archive it before final response or handoff.
   - Do not claim completion, handoff, merge readiness, archive readiness, or release readiness for `standard` or `full` tasks until the generated task-board review gate is `pass`.
   - Confirm that resume instructions do not depend on unsaved editor buffers, terminal scrollback, or Codex native thread history.

## Resource Map

- `scripts/init_agent_project.py`: Initialize or retrofit a target repository.
- `scripts/agent_session.py`: Source for the generated target-project `.agent/tools/agent_session.py`.
- `assets/templates/agent-memory.py.tmpl`: Source for generated target-project `.agent/tools/agent_memory.py`.
- `assets/templates/agent-context.py.tmpl`: Source for generated target-project `.agent/tools/agent_context.py`.
- `assets/templates/agent-capabilities.py.tmpl`: Source for generated target-project `scripts/agent_capabilities.py`.
- `assets/templates/agent-resources.py.tmpl`: Source for generated target-project `scripts/agent_resources.py`.
- `assets/templates/agent-blueprint.py.tmpl`: Source for generated target-project `scripts/agent_blueprint.py`.
- `assets/templates/agent-runtime.py.tmpl`: Source for generated target-project `scripts/agent_runtime.py`.
- `assets/templates/agent-skill-hygiene.py.tmpl`: Source for generated target-project `scripts/agent_skill_hygiene.py`.
- `assets/templates/agent-project-skills.py.tmpl`: Source for generated target-project `scripts/agent_project_skills.py`.
- `assets/templates/agent-skill-opt.py.tmpl`: Source for generated target-project `scripts/agent_skill_opt.py`.
- `assets/templates/agent-runlog.py.tmpl`: Source for generated target-project `scripts/agent_runlog.py`.
- `assets/templates/agent-tooling.py.tmpl`: Source for generated target-project `scripts/agent_tooling.py`.
- `assets/templates/agent-security.py.tmpl`: Source for generated target-project `scripts/agent_security.py`.
- `assets/templates/agent-score.py.tmpl`: Source for generated target-project `scripts/agent_score.py`.
- `assets/templates/agent-migrate.py.tmpl`: Source for generated target-project `scripts/agent_migrate.py`.
- `assets/templates/agent-task.py.tmpl`: Source for generated target-project `scripts/agent_task.py`.
- `assets/templates/agent-verify.py.tmpl`: Source for generated target-project `scripts/agent_verify.py`.
- `assets/templates/agent-gc.py.tmpl`: Source for generated target-project `scripts/agent_gc.py`.
- `assets/templates/agent-spec.py.tmpl`: Source for generated target-project `scripts/agent_spec.py`.
- `references/workflow-governance.md`: Workflow gates, loop engineering, worktree isolation, TDD/debugging evidence, review sequencing, and completion proof.
- `references/project-blueprint-governance.md`: Global project blueprint, runtime/framework decision, and OpenSpec blueprint-impact governance.
- `references/implementation-discipline.md`: Assumption clarification, simplicity-first implementation, surgical change boundaries, and goal-driven verification.
- `references/spec-management.md`: Embedded OpenSpec-style specification rules.
- `references/harness-management.md`: Harness files, native adapters, commands, validation, and safety rules.
- `references/skill-self-optimization.md`: Governed skill self-optimization, release preflight, auto-promote limits, and rollback evidence.
- `references/session-continuity.md`: Codex/Claude session continuity and long-term memory protocol for VS Code Remote work.
- `references/context-budget.md`: Context budget, safe compression, and token-scan protocol.
- `references/subagent-orchestration.md`: Permission-gated subagent roles, dispatch templates, and snapshot contracts.
- `references/review-fix-loop.md`: Review-fix gate for initialized projects.
- `assets/templates/`: Target-project templates rendered by `init_agent_project.py`.

## Guardrails

- Do not treat Codex thread history, VS Code tabs, terminal scrollback, or unsaved buffers as durable state.
- Do not store secrets, SSH keys, tokens, host credentials, or private environment values in `.agent/`.
- Do not store raw resource credentials or private secret material in `.agent/resources.json`; use generated local templates or external vault/proxy/keychain references.
- Do not store model API keys, provider tokens, private base URLs with credentials, or other raw model secrets in `.agent/model-profiles.json`; use `env:`, `file-ref:`, `vault:`, `proxy:`, `op:`, or `keychain:` references.
- Do not confuse agent-gov development session state with product runtime state; user conversations, product memory, MCP calls, traces, queues, and databases belong to the application layer.
- Do not store raw transcripts, terminal scrollback, secrets, or private host data in `.agent/runlog.jsonl`.
- Preserve existing project files by default; create missing files and report conflicts instead of silently rewriting.
- Prefer simple, direct implementations and justify new abstractions, speculative flexibility, or broad cleanup with recorded evidence.
- Keep `AGENTS.md` short and stable; move volatile state to `.agent/sessions/` and embedded spec changes.
- Keep `CLAUDE.md` thin; prefer importing or pointing to `AGENTS.md` rather than duplicating rules.
- Keep context compression semantic, not stylistic: compress redundancy and filler, preserve technical facts and retrieval handles.
- Do not force subagent use, model pinning, or delegation-only execution when the active Codex/Claude environment does not permit it.
- Do not claim completion, merge readiness, PR readiness, or successful handoff without fresh validation evidence recorded in session or runlog state.
- Do not leave a completed embedded spec change active; archive `all_done` changes before completion, handoff, release, or archive-readiness claims.
- Do not create, discard, or force-delete worktrees or branches without following the project worktree policy and explicit user confirmation for destructive actions.
