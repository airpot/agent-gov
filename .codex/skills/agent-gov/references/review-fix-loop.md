# Review-Fix Loop

Use this reference when the initialized project needs a release-quality setup rather than a quick scaffold.

## Review Gate

Review the initialized project before handoff. At minimum, check:

- `.agent/spec.json`, `openspec/`, and `scripts/agent_spec.py` exist and identify agent-gov embedded spec management as the spec source.
- `AGENTS.md` is short, stable, and agent-focused.
- `CLAUDE.md` is thin and does not duplicate long instructions.
- `.agent/workflow.json` records lifecycle gates for risk classification, spec approval, plan quality, implementation discipline, diff traceability, worktree isolation, TDD/debugging, review sequence, human review evidence, completion verification, and finish choices.
- `.agent/workflow-profiles.json` records `tiny`, `bugfix`, `standard`, and `full` process weights, and `.agent/workflow.json` points to it.
- `.agent/task-board.json` and `docs/features/INDEX.md` exist; non-tiny task state can be created with `scripts/agent_task.py`.
- `.agent/risk-zones.json` records low, medium, high, and critical autonomy rules; high and critical risk require human review, and critical work is not autonomous modification work.
- `.agent/review-policy.json` records requested, necessary-support, incidental, and risky diff categories plus human review evidence fields.
- `.agent/worktrees.json` records isolated worktree directory selection, ignore verification, baseline validation, and guarded cleanup.
- `.agent/sessions/` supports start, checkpoint, resume, status, and archive.
- `.agent/subagents.json`, `.agent/role-contracts.json`, `.agent/hooks.json`, `.agent/knowledge.json`, and `.agent/skill-distribution.json` are valid.
- `.agent/role-contracts.json` enforces finder-cannot-fix separation: verifier/reviewer roles report findings and route fixes back.
- `.agent/context.json` exists, context budget commands run, and oversized governance docs have compression or retrieval plans.
- `.agent/capabilities.json` exists, enabled capabilities have owners, risks, permissions, and validation evidence.
- `.agent/runlog.jsonl` exists, parses as JSONL, and records validation/session evidence for substantial work.
- `.agent/tooling.json` exists, bounded tooling commands run, and large/empty output behavior is explicit.
- `.agent/security.json` exists, optional security suites are listed, and sensitive-path scans can run locally.
- `.agent/evals.json` exists, `scripts/agent_score.py score --write` runs, and `.agent/evals/latest.md` records current governance drift.
- `.agent/mechanical-checks.json`, `.agent/baselines.json`, and `scripts/agent_verify.py` exist; hard mechanical checks and before/after baseline comparisons can run.
- `.agent/dev-map.json` and `docs/DEV_MAP.md` exist and describe repository entry points without becoming a full file inventory.
- `.agent/harness-evolution.json` exists and postmortem templates include harness gap classification.
- `.agent/mcp-policy.json` exists and keeps MCP optional, credential-safe, and approval-gated by default.
- `.agent/governance-gc.json` and `scripts/agent_gc.py` exist and can report stale docs, stale tasks, baseline drift, config pointers, and owner gaps.
- `docs/adr/`, `docs/rfcs/`, and `docs/incidents/` exist with templates for durable decisions, proposals, and postmortems.
- Native Codex/Claude adapters exist when enabled and remain thin projections of `.agent/` policy.
- VS Code Remote assumptions are captured in session state.
- Validation commands exist and run.
- Substantial changes have fresh completion evidence; skipped checks have explicit reasons and residual risk.
- Delegated or substantial implementation ran spec compliance review before code quality review, or records an accepted exception.
- Substantial implementation records assumptions, simplicity/abstraction justification, surgical diff scope, and success criteria, or records an accepted exception.
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

`standard` and `full` tasks cannot be marked `done` unless the review gate is `pass`, the latest review path exists, and open blocker/major/minor findings are empty.

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
  -> confirm workflow gate evidence or accepted exceptions
  -> record validation and accepted exceptions in runlog/session files
  -> refresh governance score when release readiness matters
  -> create the next review round
  -> repeat until the latest review is clean
```

Do not convert a finding-bearing review to `pass`. Keep it as `needs-fix`, record the fix log, and use the next review round as proof that the fixes held.

Generated projects enforce this through `scripts/agent_task.py`, `scripts/agent_check.py`, `scripts/agent_verify.py`, and `scripts/agent_score.py`.

For skill development in this repository, use `skill_lifecycle.py review`, `fix-log`, and `review-status`.
