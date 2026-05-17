# Harness Management

Use this reference when setting up the engineering harness around an agent-ready project.

## Target Layout

```text
AGENTS.md
CLAUDE.md                  # optional, thin pointer to AGENTS.md
openspec/config.yaml
.codex/
  config.toml
  hooks.json
  agents/
    governance-*.toml
.claude/                  # optional when Claude support is enabled
  settings.json
  agents/
    governance-*.md
.agent/
  config.json
  manifest.json
  harness.json
  project-layout.json
  spec.json
  workflow.json
  workflow-profiles.json
  task-board.json
  risk-zones.json
  review-policy.json
  worktrees.json
  subagents.json
  role-contracts.json
  hooks.json
  knowledge.json
  dev-map.json
  skill-hygiene.json
  memory.json
  context.json
  capabilities.json
  tooling.json
  security.json
  evals.json
  mechanical-checks.json
  baselines.json
  harness-evolution.json
  mcp-policy.json
  governance-gc.json
  skill-distribution.json
  runlog.jsonl
  baselines/
  context/
    stats.jsonl
    latest.md
  evals/
    latest.md
  memory/
    events.jsonl
    index.sqlite3
    latest.md
    summaries/
  sessions/
    index.json
    events.jsonl
    active.md
    bootstrap.md
  templates/
    session.md.tmpl
    handoff.md.tmpl
    context.md.tmpl
    decisions.md.tmpl
    changes.md.tmpl
    validation.md.tmpl
    resume-prompt.md.tmpl
    artifacts.json.tmpl
    project-review.md.tmpl
    project-fix-log.md.tmpl
    implementation-plan.md.tmpl
    debugging-record.md.tmpl
    subagent-task.md.tmpl
    features/
      01_REQUIREMENT_ANALYSIS.md.tmpl
      02_SOLUTION_DESIGN.md.tmpl
      03_GATE_REVIEW.md.tmpl
      04_DEVELOPMENT.md.tmpl
      05_CODE_REVIEW.md.tmpl
      06_TEST_REPORT.md.tmpl
      07_DELIVERY_SUMMARY.md.tmpl
    memory-summary.md.tmpl
    memory-latest.md.tmpl
    context-summary.md.tmpl
    adr.md.tmpl
    rfc.md.tmpl
    postmortem.md.tmpl
    quality-score.md.tmpl
  tools/
    agent_session.py
    agent_memory.py
    agent_context.py
    governance_hook.py
scripts/
  agent_check.py
  agent_spec.py
  agent_validate.py
  agent_knowledge.py
  agent_invariants.py
  agent_capabilities.py
  agent_skill_hygiene.py
  agent_runlog.py
  agent_tooling.py
  agent_security.py
  agent_score.py
  agent_sync_skills.py
  agent_task.py
  agent_verify.py
  agent_gc.py
docs/
  index.md
  ARCHITECTURE.md
  QUALITY.md
  RELIABILITY.md
  SECURITY.md
  TOOLING.md
  QUALITY_SCORE.md
  AI_CODING_GLOSSARY.md
  DOMAIN_GLOSSARY.md
  DEV_MAP.md
  features/
    INDEX.md
  tech-debt.md
  adr/
    README.md
  rfcs/
    README.md
  incidents/
    README.md
Makefile                   # optional if missing
```

## Harness Principles

- Make the remote repository filesystem the source of truth.
- Use scripts for deterministic checks and session state operations.
- Use `.agent/harness.json` as the project-specific command registry for build, test, lint, typecheck, smoke, logs, and health checks.
- Use `.agent/manifest.json` as the generated governance manifest for required paths, JSON schemas, JSONL stores, and score dimensions; generated checks should prefer it over duplicated static lists.
- Use `.agent/project-layout.json` as the fixed directory contract for top-level project structure.
- Use `.agent/spec.json` and `scripts/agent_spec.py` as the embedded specification policy and command surface.
- Use `.agent/workflow.json` as the lifecycle gate policy for risk classification, design/spec approval, plan quality, implementation discipline, diff traceability, isolated work, TDD, debugging, review order, human review evidence, completion proof, and finish choices.
- Use `.agent/risk-zones.json` as the task risk and autonomy policy.
- Use `.agent/review-policy.json` as the diff traceability, automated review boundary, and human review evidence policy.
- Use `.agent/worktrees.json` as the git worktree isolation and guarded cleanup policy.
- Use `.agent/workflow-profiles.json` to choose a task-size-aware process: `tiny`, `bugfix`, `standard`, or `full`.
- Use `.agent/task-board.json`, `scripts/agent_task.py`, and `docs/features/` as the cross-session task index and feature-stage document store.
- For existing projects, initialize with `--dry-run` first. Treat `conflicts` as a manual merge queue and `preserved append-only` as history that must not be overwritten.
- Use the requirements interview gate for non-tiny work: ask one unresolved question at a time, provide a recommended answer and rationale, cross-check user claims against current code/docs, and update `docs/DOMAIN_GLOSSARY.md` when stable project-domain terms are established.
- Use `.agent/subagents.json` as the delegated agent role, boundary, and snapshot contract when subagents are allowed.
- Use `.agent/role-contracts.json` to enforce role inputs, outputs, forbidden actions, and finder-cannot-fix separation.
- Use `.agent/hooks.json` as the platform-neutral hook policy, with native Codex and Claude hook adapters treated as generated projections.
- Use `.agent/knowledge.json` as the durable knowledge manifest for ownership, review dates, source links, and known stale sections.
- Use `.agent/dev-map.json` and `docs/DEV_MAP.md` as a concise repository navigation map for entry points, ownership, read-before-edit docs, and common patterns.
- Use `.agent/skill-hygiene.json` and `scripts/agent_skill_hygiene.py` for read-only skill topology, source/hash, symlink, frontmatter, stale, and risk-signal scans.
- Use `.agent/memory.json` as the cross-session memory policy for summaries, indexes, privacy redaction, and progressive retrieval.
- Use `.agent/context.json` as the context budget policy for agent-facing docs, bootstrap packets, memory digests, embedded spec change docs, and subagent output size.
- Use `.agent/capabilities.json` as the capability, skill/tool/MCP taxonomy, integration, permission, and risk registry for agent-visible skills, tools, resources, adapters, and integrations.
- Use `.agent/runlog.jsonl` as the append-only evidence ledger for validation runs, review-fix gates, and high-risk capability use; use `.agent/sessions/events.jsonl` as the append-only session lifecycle stream.
- Use `.agent/tooling.json` as the agent-computer-interface policy for bounded, path-first, line-numbered repository inspection.
- Use `.agent/security.json` as the optional policy-as-code and supply-chain command registry.
- Use `.agent/evals.json` and `.agent/evals/latest.md` as the local governance health score configuration and dashboard.
- Use `.agent/mechanical-checks.json`, `.agent/baselines.json`, and `scripts/agent_verify.py` for hard mechanical checks, template rendering checks, test-count baselines, and before/after regression comparison.
- Use `.agent/harness-evolution.json` as the incident taxonomy and promotion policy for repeated failures; record classifications with `python3 scripts/agent_gc.py classify --category <category> --summary <summary>`.
- Use `.agent/mcp-policy.json` as the optional MCP trust-boundary and approval policy; it is generated disabled by default before any MCP server is enabled, and raw credentials must remain behind vault/proxy boundaries outside the repo, harness, and sandbox.
- Use `.agent/governance-gc.json` and `scripts/agent_gc.py` for periodic governance gardening.
- Use `.agent/skill-distribution.json` as the skill distribution policy for `.codex/skills`, `.agents/skills`, and `.claude/skills`.
- Prefer `npx @airpot/agent-gov@latest` as the public one-command installer; it should copy bundled project skills before running the initializer.
- Use `docs/AI_CODING_GLOSSARY.md` for shared AI coding terminology, `docs/DOMAIN_GLOSSARY.md` for project-domain terminology, and `docs/adr/`, `docs/rfcs/`, and `docs/incidents/` for durable decisions, proposals, and postmortems that should outlive a session.
- Capture the technology stack during initialization and prefill harness commands when there is a known safe default.
- Prefer ignored git worktrees for feature work, implementation-plan execution, and risky refactors; record baseline validation before editing.
- Require fresh validation evidence before reporting completion, merge readiness, PR readiness, archive readiness, or handoff readiness.
- Keep durable project knowledge in `docs/`; keep `AGENTS.md` as a short routing document.
- Add mechanical invariants when architecture or taste constraints can be checked by scripts.
- Keep commands idempotent and non-destructive by default.
- Report skipped existing files instead of overwriting them.
- Keep generated files ASCII and easy to diff.

## Validation Commands

Preferred validation after initialization:

```bash
python3 scripts/agent_check.py
python3 scripts/agent_spec.py doctor
python3 scripts/agent_knowledge.py
python3 scripts/agent_invariants.py
python3 scripts/agent_capabilities.py doctor
python3 scripts/agent_skill_hygiene.py doctor
python3 scripts/agent_runlog.py doctor
python3 scripts/agent_tooling.py doctor
python3 scripts/agent_security.py doctor
python3 scripts/agent_task.py doctor
python3 scripts/agent_verify.py doctor
python3 scripts/agent_gc.py doctor
python3 scripts/agent_score.py doctor
python3 scripts/agent_validate.py --list
python3 scripts/agent_sync_skills.py --dry-run
python3 .agent/tools/agent_memory.py doctor
python3 .agent/tools/agent_context.py doctor
python3 scripts/agent_spec.py list --json
python3 .agent/tools/agent_session.py status
```

If `Makefile` is created by the initializer, also run:

```bash
make agent-check
make agent-validate
```

## Harness Feedback Surface

`agent_validate.py` reads `.agent/harness.json`. New projects start with empty command lists so initialization succeeds before the application stack is known. Once the stack is known, fill in commands such as:

```json
{
  "validation": {
    "build": ["npm run build"],
    "test": ["npm test"],
    "lint": ["npm run lint"],
    "typecheck": ["npm run typecheck"],
    "smoke": ["npm run smoke"]
  }
}
```

Agents should run `python3 scripts/agent_validate.py --list` before choosing validation, then run the narrowest configured suite that proves the change.

`agent_validate.py` appends pass/fail evidence to `.agent/runlog.jsonl`. When validation is skipped, record the reason in the active session `validation.md`; optionally add a runlog entry with `python3 scripts/agent_runlog.py record --kind validation --outcome skipped --summary "..."`.

## Workflow And Worktree Surface

`.agent/workflow.json` records the project lifecycle gates:

- Design/spec approval for non-trivial changes.
- Risk classification and autonomy boundary before implementation.
- Plan quality for multi-step or delegated work.
- Implementation discipline for assumption surfacing, simplicity-first implementation, surgical diffs, abstraction justification, and success criteria.
- Diff traceability for requested, necessary-support, incidental, and risky changes.
- Worktree isolation and clean baseline evidence for feature work.
- TDD evidence for behavior changes and systematic debugging evidence for failures.
- Spec compliance review before code quality review.
- Human review evidence for high and critical risk changes.
- Fresh validation evidence before completion claims.
- Explicit finish choices for merge, PR, keep, or discard.

`.agent/worktrees.json` records where isolated worktrees should live, how to verify project-local directories are ignored, what baseline validation is expected, and which cleanup operations need confirmation. Do not treat it as permission to run destructive git commands; it is a policy surface that constrains such commands.

## Capability Governance Surface

`.agent/capabilities.json` records agent-visible capabilities, not just command names:

- Capability id, kind, capability class, provider, owner, enabled state, and risk level.
- Taxonomy for skill, tool, MCP/integration, and native adapter entries.
- Permission shape for read, write, network, and secret exposure.
- Validation commands proving the capability is available or intentionally disabled.
- Empty extension points for MCP servers and external integrations.

Use `python3 scripts/agent_capabilities.py list --enabled` before using optional tools or native integrations. High-risk enabled capabilities must have an owner and should leave evidence in `.agent/runlog.jsonl`.

## Runlog Surface

`.agent/runlog.jsonl` stores compact events with `id`, `trace_id`, timestamp, kind, outcome, summary, command, session id, tags, and artifacts. It is not a raw transcript. Use it to answer:

- Which validations ran and what passed or failed.
- Which session lifecycle actions happened before rollover.
- Which high-risk tool or integration was used.
- Which review-fix or subagent result was accepted.

## ACI Tooling Surface

`scripts/agent_tooling.py` provides bounded repository inspection commands:

- `files`: list files with a maximum result count.
- `read`: print a line-numbered range and refuse sensitive-looking or binary paths.
- `search`: search text with bounded matches and explicit `no matches` output.
- `doctor`: validate `.agent/tooling.json`.

Use this wrapper when normal shell output would be too large, silent on empty results, or likely to include irrelevant files. It complements shell tools; it does not replace direct repo inspection when the active environment expects it.

## Security And Supply Chain Surface

`.agent/security.json` records optional command slots:

- `policy_as_code`
- `secret_scan`
- `dependency_audit`
- `sbom`
- `license_scan`

`scripts/agent_security.py scan-paths` performs a local sensitive-path scan without reading secret contents. Project-specific security tools can be added later without making initialization fail in empty projects.

## Decision And Incident Surface

Use `.agent/templates/adr.md.tmpl`, `.agent/templates/rfc.md.tmpl`, and `.agent/templates/postmortem.md.tmpl` to create durable records:

- ADRs under `docs/adr/` for accepted architecture decisions.
- RFCs under `docs/rfcs/` for broad proposals before they become embedded spec changes.
- Postmortems under `docs/incidents/` for reliability, security, session, memory, context, or validation failures.

## Governance Score Surface

`scripts/agent_score.py` computes an advisory 0-100 local score over:

- Required paths from `.agent/harness.json`.
- Configured validation commands.
- Workflow profile, task-board, role-contract, and mechanical baseline health.
- Risk autonomy policy.
- Diff traceability and human review policy.
- Context budget drift.
- Session continuity files.
- Memory taxonomy and procedural review evidence.
- Capability registry health.
- Security suite configuration and sensitive-path scan.
- Knowledge document freshness and ownership.
- Runlog parseability and evidence presence.

Use `python3 scripts/agent_score.py score --write` before release handoff or on a periodic cadence. The score is a drift signal, not a substitute for review or tests.

## Subagent Feedback Surface

`subagents.json` is a policy surface, not a command runner. It records:

- Whether subagents are permission-gated.
- Which roles are available.
- Whether workers may write by default.
- Whether implementation uses `DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED` states.
- Whether spec review must pass before code quality review.
- The required `===SNAPSHOT===` JSON fields.
- The dispatch template path.

Use it to keep multi-agent work bounded and reviewable. Do not use it to override active platform instructions, force model choices, or require delegation for simple work.

## Native Adapter Surface

The project-neutral sources are `.agent/subagents.json`, `.agent/hooks.json`, and `.agent/skill-distribution.json`. Generated native adapters should remain thin:

- Codex subagents: `.codex/agents/governance-*.toml`
- Codex hooks: `.codex/hooks.json`, enabled by `.codex/config.toml`
- Claude subagents: `.claude/agents/governance-*.md`
- Claude hooks: `.claude/settings.json`
- Skill sync: `scripts/agent_sync_skills.py`

When an existing native config is skipped, preserve it and report the skipped file. Merge manually instead of overwriting project-specific settings.

Session-start hooks must remain read-only. They may print status, existing bootstrap excerpts, memory timelines, no-write context previews, and enabled capability summaries, but they must not create indexes, append scan history, or refresh session files. Native hook commands must locate `.agent/tools/governance_hook.py` without requiring the target project to be a git repository. Stop hooks may ingest active session memory, refresh context scans, and append compact runlog evidence.

## Memory Surface

The memory layer borrows the useful shape of hook-captured, compressed, searchable context without depending on a global service:

- `.agent/memory/events.jsonl` stores concise memory records.
- `.agent/memory/index.sqlite3` is an optional generated SQLite/FTS index.
- `.agent/memory/latest.md` is a small bootstrap digest.
- `.agent/memory/summaries/` stores detail records by memory id.

Use `timeline -> search -> detail` to avoid loading excessive context. Store summaries and retrieval handles, not raw transcripts.

Memory classes are explicit:

- `episodic`: session summaries, handoffs, validations, subagent snapshots, and incidents.
- `semantic`: durable project facts with source paths that still need confirmation against the repository.
- `procedural`: reusable workflow rules promoted only with review evidence.

Do not promote a one-off session observation into procedural memory without a review reference.

## Context Budget Surface

The context budget layer borrows the useful parts of token-saving projects without adopting a terse persona:

- `.agent/context.json` records tracked files, glob patterns, token budgets, and safe-compression policy.
- `.agent/context/stats.jsonl` stores budget scan records over time.
- `.agent/context/latest.md` is a small digest included in session bootstrap.
- `.agent/tools/agent_context.py` provides `doctor`, `scan`, `suggest`, and `validate-pair`.

Use context budget scans to catch bloated `AGENTS.md`, `CLAUDE.md`, docs, session bootstraps, memory digests, embedded spec change docs, and subagent outputs before they cause rollover or OOM problems. `doctor` is read-only by default; use `scan` or `doctor --write` only when refreshing `.agent/context/latest.md` is intended.

Compression must preserve headings, fenced code blocks, inline code, URLs, paths, commands, versions, and technical names. The generated tool validates these invariants locally. Sensitive-looking paths are allowed for local pair validation, but the tool warns that they must not be sent to external compression services.

## Technology Stack And Layout

Initialization should capture the project stack explicitly:

```bash
python3 .codex/skills/agent-gov/scripts/init_agent_project.py /path/to/repo \
  --tech-stack python,typescript \
  --layout service \
  --dir tools
```

Built-in layouts:

- `existing`: no default directories; use `--dir` to record the repository's real fixed directories
- `minimal`: `src`, `tests`, `docs`, `scripts`
- `python-app`: `src`, `tests`, `docs`, `scripts`, `configs`
- `node-app`: `src`, `tests`, `docs`, `scripts`, `public`
- `web-app`: `src`, `tests`, `docs`, `scripts`, `public`
- `service`: `src`, `tests`, `docs`, `scripts`, `configs`, `deploy`
- `library`: `src`, `tests`, `docs`, `scripts`, `examples`

The initializer creates these directories by default and records them in `.agent/project-layout.json`. Use `--no-create-layout` for existing repositories where directories should be checked but not created. For repositories that do not use the built-in `src` / `tests` shape, use `--layout existing --dir cmd,pkg,internal --no-create-layout`.

`--dir` values must be repository-relative directory paths. Absolute paths, drive paths, `.` segments, and `..` segments are rejected so initialization cannot write outside the target project root.

## Safety Rules

- Never write secrets to `.agent/config.json`.
- Do not record terminal scrollback or full model transcripts.
- Store only durable summaries, file paths, command results, and decisions.
- Store only accepted subagent snapshots and integration decisions, not full subagent transcripts.
- Keep subagent final notes within the configured `.agent/context.json` budget after the required `===SNAPSHOT===` JSON.
- In VS Code Remote, require saved files before checkpointing.
