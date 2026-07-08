# Review-Fix Loop

Use this reference whenever initialized project work needs completion evidence. Review-fix-review is required for every task profile, with process weight scaled by risk.

## Review Gate

Review the initialized project before handoff. At minimum, check:

- `.agent/spec.json`, `openspec/`, and `scripts/agent_spec.py` exist and identify agent-gov embedded spec management as the spec source.
- `python3 scripts/agent_spec.py doctor` passes, and no active change under `openspec/changes/<name>/` is already `all_done`; completed changes are archived under `openspec/changes/archive/`.
- `AGENTS.md` is short, stable, and agent-focused.
- `CLAUDE.md` is thin and does not duplicate long instructions.
- `.agent/workflow.json` records lifecycle gates for risk classification, spec approval, plan quality, implementation discipline, diff traceability, worktree isolation, TDD/debugging, review sequence, human review evidence, completion verification, and finish choices.
- `.agent/blueprint.json`, `docs/PROJECT_BLUEPRINT.md`, `.agent/templates/project-blueprint.md.tmpl`, and `scripts/agent_blueprint.py` exist for standard/full projects; blueprint doctor passes; active OpenSpec changes declare valid `blueprint_impact`.
- `.agent/workflow-profiles.json` records `tiny`, `bugfix`, `standard`, and `full` process weights, and `.agent/workflow.json` points to it.
- `.agent/loop-engineering.json` exists, `.agent/workflow.json` has a `loop_engineering` gate, and non-tiny iterative work has loop contracts for primitive, readiness level, budget, observation signal, stop conditions, evidence, owner role, evaluator boundary, stop reason, and escalation.
- `.agent/loop-engineering.json` defines `manual`, `report_only`, `assisted`, and `unattended` readiness levels, and unattended readiness requires attempt ledger evidence, failure signatures, quota/circuit-breaker controls, human interrupt points, state persistence, and safe stop behavior.
- `.agent/loop-engineering.json` defines the primitive selection matrix for `turn_based`, `goal_based`, `time_based`, `scheduled_routine`, and `scripted_workflow`, including trigger source, stop condition, task shape, required evidence, and misuse signals.
- `.agent/loop-engineering.json` routes CI/deploy/queue/issue/PR review/monitoring/third-party polling to `time_based` or `scheduled_routine`, not goal-only convergence.
- `.agent/loop-engineering.json` requires goal-based loops to record measurable done state, proof method, protected constraints, turn/time cap, evidence path, evaluator boundary, and stop reason; cap exhaustion is not success.
- `.agent/loop-engineering.json` requires scheduled routines to record routine id/name, trigger/cadence/event source, run location, permission mode, resource and credential boundary, per-run stop condition, disable/expiry policy, owner, evidence path, and fail-closed behavior for missing protected-action approval.
- `.agent/loop-engineering.json` requires scripted workflows to record script artifact/source, phase plan, worker role boundaries, concurrency cap, pilot scope, cross-check/adversarial review strategy, state/resume boundary, save/reuse policy, intermediate result storage, and cost/usage evidence before broad execution.
- `.agent/loop-engineering.json` defines attempt ledger fields, quota policy, circuit breakers for destructive/production/release/billing/credential/privileged/external mutation actions, safe fallback lanes, explicit loop state transitions, usage evidence, and a dependency-free source-only boundary for external loop research.
- `.agent/task-board.json`, `.agent/intake/`, and `docs/features/INDEX.md` exist; non-tiny task state can be created with `scripts/agent_task.py`, bugfix/standard/full active, review, or done tasks have a complete refined goal contract, and tiny no-task-board work has session/runlog/intake review evidence.
- `docs/DOMAIN_GLOSSARY.md` exists; non-tiny work has requirements interview evidence before implementation or done state.
- `.agent/risk-zones.json` records low, medium, high, and critical autonomy rules; high and critical risk require human review, and critical work is not autonomous modification work.
- `.agent/review-policy.json` records requested, necessary-support, incidental, and risky diff categories plus human review evidence fields.
- `.agent/worktrees.json` records isolated worktree directory selection, ignore verification, baseline validation, and guarded cleanup.
- `.agent/sessions/` supports start, checkpoint, resume, status, and archive.
- `.agent/subagents.json`, `.agent/role-contracts.json`, `.agent/hooks.json`, `.agent/knowledge.json`, and `.agent/skill-distribution.json` are valid.
- `.agent/knowledge.json` records promotion policy and evidence-boundary policy; any durable procedural knowledge or generated policy promotion has source evidence, source status, target surface, authority level, review reference, and validation or rejection status.
- `.agent/role-contracts.json` enforces finder-cannot-fix separation: verifier/reviewer roles report findings and route fixes back.
- `.agent/context.json` exists, context budget commands run, and oversized governance docs have compression or retrieval plans.
- `.agent/capabilities.json` exists, enabled capabilities have owners, risks, permissions, and validation evidence.
- `.agent/capabilities.json` records provider status, required/optional classification, validation, and fallback. Missing required providers, invalid status values, or optional providers without fallback are findings.
- `.agent/manifest.json#/governance_presets` records selected presets/extensions/catalog entries with source status, version, permissions, generated paths, validation, conflict behavior, dry-run support, and no automatic dependency installation.
- `.agent/runlog.jsonl` exists, parses as JSONL, and records validation/session evidence for substantial work.
- `.agent/tooling.json` exists, bounded tooling commands run, and large/empty output behavior is explicit.
- `.agent/security.json` exists, optional security suites are listed, and sensitive-path scans can run locally.
- `.agent/evals.json` exists, `scripts/agent_score.py score --write` runs, and `.agent/evals/latest.md` records current governance drift.
- `.agent/mechanical-checks.json`, `.agent/baselines.json`, and `scripts/agent_verify.py` exist; hard mechanical checks and before/after baseline comparisons can run.
- `.agent/mechanical-checks.json` includes strict agent contract checks and negative fixtures for reviewer self-fix, verifier writes, worker out-of-bound writes, missing protected-action approval, provider fallback gaps, adapter parity gaps, and bootstrap history inlining.
- `.agent/baselines.json#/regression_criteria` records baseline behavior, expected behavior, validation commands, protected invariants, and rejected regressions for governance changes.
- `scripts/agent_knowledge.py` runs and evidence-boundary lint reports no raw transcripts, terminal scrollback, secrets, private host data, or long diagnostic blocks in tracked governance stores.
- `.agent/dev-map.json` and `docs/DEV_MAP.md` exist and describe repository entry points without becoming a full file inventory.
- `.agent/skill-hygiene.json` and `scripts/agent_skill_hygiene.py` exist; skill topology and risk signals can be scanned read-only, and cleanup/canary actions are explicit human-confirmation work.
- `.agent/project-skills.json` and `scripts/agent_project_skills.py` exist; project skills are registered as managed, workspace-only helpers are not merged into `skills.manifest.json`, and lifecycle changes have embedded spec, review-fix-review, validation, and archive evidence.
- `.agent/skill-runtime.json` and `docs/SKILL_RUNTIME.md` exist; portable Skill/plugin work records canonical core boundaries, thin host adapters, runtime modes, command lanes, separated review lanes, benchmark evidence gates, and shortcut/debt marker policy.
- `.agent/harness-evolution.json` exists and postmortem templates include harness gap classification.
- `.agent/mcp-policy.json` exists and keeps MCP optional, credential-safe, vault/proxy-bounded, and approval-gated by default.
- `.agent/governance-gc.json` and `scripts/agent_gc.py` exist and can report stale docs, stale tasks, baseline drift, config pointers, and owner gaps.
- `.agent/governance-gc.json#/component_expiry` records owner, purpose, load-bearing status, last review, review cadence or expiry, validation, renewal path, and removal path; stale or unowned load-bearing components are findings.
- `docs/adr/`, `docs/rfcs/`, and `docs/incidents/` exist with templates for durable decisions, proposals, and postmortems.
- Native Codex/Claude adapters exist when enabled and remain thin projections of `.agent/` policy.
- VS Code Remote assumptions are captured in session state.
- Validation commands exist and run.
- Substantial changes have fresh completion evidence; skipped checks have explicit reasons and residual risk.
- Tiny, bugfix, standard, and full task completions have profile-specific review-fix-review evidence. Standard/full protected stage exits also have review-fix-review evidence before progressing past spec, plan, implementation, spec review, quality review, verification, and handoff.
- Delegated or substantial implementation ran spec compliance review before code quality review, or records an accepted exception.
- Substantial implementation records assumptions, simplicity/abstraction justification, surgical diff scope, and success criteria, or records an accepted exception.
- Research-driven changes record which external sources were verified, partial, or blocked before source-derived rules were adopted.
- Knowledge promotion bundles are reviewed before source-derived or session-derived observations become durable docs, procedural memory, generated policy, skill references, or templates.
- Substantial implementation considered local reuse, standard library, native platform features, existing dependencies, and the minimum direct edit before adding new abstractions, dependencies, generated files, or governance surface.
- Any deliberate simplification with a known ceiling records the ceiling and upgrade trigger in development or review evidence.
- Complexity-only audit findings, when used, stay separate from correctness/security findings and do not replace spec or quality review.
- Native Codex/Claude/project instruction adapters remain thin projections of canonical `.agent/` or skill policy; copied rule text has sync, hash, or invariant evidence when release readiness depends on parity.
- Native hook changes have evidence for valid host output shape, stdin EOF/error handling, UTF-8 BOM stripping before JSON parsing, empty `additionalContext` preservation, safe degradation, and non-zero exit for invalid mandatory output.
- Skill/package release checks state whether hook manifests/files are preserved, stripped, suppressed by an explicit empty hooks object, or skipped for manual merge; orphaned hook files or manifest entries are resolved or recorded as accepted exceptions.
- Skill or governance optimization claims have isolated baseline/current evidence and check for global hook, plugin, cache, or session contamination.
- Skill-impact claims do not count line, cost, speed, or token reductions as improvements when requirements, correctness, safety, privacy, data-loss handling, accessibility, or required validation were dropped.
- Failed profile, benchmark, optimization, migration, or pipeline runs are marked failed with evidence paths where available and do not exit zero.
- Reviewers flag loop primitive mismatch as a finding: goal loops used for external polling, timer loops used for finite proof-based convergence, routines without disable/expiry policy, scripted workflows without pilot/cross-check/cost evidence, or inaccessible sources promoted into procedural rules.
- Repeated loop attempts record stable failure signatures and strategy-change evidence before retry; budget exhaustion stops into replan, blocked, human gate, failed, or accepted exception rather than silent continuation.
- Safe fallback work preserves unresolved human gates and stays within read-only analysis, test preparation, docs review, planning, or artifact inventory.
- High-risk and critical changes have reviewer, diff range, reviewed files, high-risk paths checked, and conclusion recorded.
- Incidental diff lines are removed or recorded as accepted exceptions.
- No secrets or private host credentials are written.
- Compression does not alter headings, code blocks, inline code, URLs, paths, commands, versions, or technical identifiers.
- Existing project files were not overwritten without explicit instruction.

The initializer places target-project templates at:

```text
.agent/templates/project-review.md.tmpl
.agent/templates/project-fix-log.md.tmpl
```

For task-managed work, the pass gate is also recorded in `.agent/task-board.json`:

```json
"review_gate": {
  "required": true,
  "status": "pass",
  "latest_review": "docs/features/<task-id>/05_CODE_REVIEW.md",
  "latest_fix": "docs/features/<task-id>/04_DEVELOPMENT.md",
  "open_findings": [],
  "accepted_exception": ""
}
```

Task-board-backed `tiny`, `bugfix`, `standard`, and `full` tasks cannot be marked `done` unless the review gate is `pass`, the latest review path exists, open blocker/major/minor findings are empty, and task decomposition is complete. Tiny work without a task-board record must keep lightweight review evidence in the active session, runlog, or `.agent/intake/`.

## Findings

Use four severities:

- `blocker`: setup cannot be used, cannot be resumed, or can lose state.
- `major`: setup is materially incomplete or inaccurate.
- `minor`: wording, naming, or organization can improve.
- `note`: future improvement.

Resolve blocker, major, and minor findings before release, or document an explicit exception accepted by the user or project owner. Notes are future work and do not block release.

## Fix Loop

```text
review
  -> fix blocker/major/minor findings
  -> re-run agent_check.py and relevant commands
  -> stop or change strategy if the same failure repeats or loop budget is exhausted
  -> confirm workflow gate evidence or accepted exceptions
  -> record validation and accepted exceptions in runlog/session files
  -> refresh governance score when release readiness matters
  -> create the next review round
  -> repeat until the latest review is clean
```

When a finding is about avoidable complexity, route it through the same loop but keep the fix objective concrete: delete unused code, reuse a local helper, replace hand-rolled logic with stdlib/native behavior, remove an unearned dependency, or record an explicit exception. Do not accept vague "simplify later" responses as a pass-gate fix.

When a finding is about portable Skill/plugin architecture, route it through `.agent/skill-runtime.json`: restore canonical-core authority, thin the adapter, add parity evidence, map the command lane, clarify mode persistence/deactivation, add benchmark gates, or add a debt marker ceiling and upgrade trigger.

When a finding is about external research evidence, the fix is either to provide verified source content, downgrade the claim to partial evidence, or remove the source-derived rule. Search snippets and inaccessible article URLs are not enough for a procedural governance rule.

When a finding is about knowledge promotion or evidence storage, the fix is either to add a complete promotion bundle with review evidence, downgrade the content to advisory memory, move raw diagnostic material to an allowed artifact path, or remove the unsupported durable rule.

When a finding is about loop primitive fit, the fix is to change the primitive, add the missing proof/routine/workflow/usage evidence, downgrade host-native features to optional mappings, or record an accepted exception with owner/date/residual risk. Do not treat a cap-exhausted or approval-missing loop as completed work.

Do not convert a finding-bearing review to `pass`. Keep it as `needs-fix`, record the fix log, and use the next review round as proof that the fixes held.

For embedded spec work, include this archive check in the loop:

```text
status --change <name>
  -> if state is all_done, archive <name>
  -> run agent_spec.py doctor
  -> proceed only when doctor passes
```

Generated projects enforce this through `scripts/agent_task.py`, `scripts/agent_skill_hygiene.py`, `scripts/agent_project_skills.py`, `scripts/agent_check.py`, `scripts/agent_verify.py`, and `scripts/agent_score.py`.

For skill development in this repository, use `skill_lifecycle.py review`, `fix-log`, and `review-status`.
