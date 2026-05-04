# Review-Fix Loop

Use this reference when the initialized project needs a release-quality setup rather than a quick scaffold.

## Review Gate

Review the initialized project before handoff. At minimum, check:

- `.agent/spec.json`, `openspec/`, and `scripts/agent_spec.py` exist and identify agent-gov embedded spec management as the spec source.
- `AGENTS.md` is short, stable, and agent-focused.
- `CLAUDE.md` is thin and does not duplicate long instructions.
- `.agent/workflow.json` records lifecycle gates for spec approval, plan quality, implementation discipline, worktree isolation, TDD/debugging, review sequence, completion verification, and finish choices.
- `.agent/worktrees.json` records isolated worktree directory selection, ignore verification, baseline validation, and guarded cleanup.
- `.agent/sessions/` supports start, checkpoint, resume, status, and archive.
- `.agent/subagents.json`, `.agent/hooks.json`, `.agent/knowledge.json`, and `.agent/skill-distribution.json` are valid.
- `.agent/context.json` exists, context budget commands run, and oversized governance docs have compression or retrieval plans.
- `.agent/capabilities.json` exists, enabled capabilities have owners, risks, permissions, and validation evidence.
- `.agent/runlog.jsonl` exists, parses as JSONL, and records validation/session evidence for substantial work.
- `.agent/tooling.json` exists, bounded tooling commands run, and large/empty output behavior is explicit.
- `.agent/security.json` exists, optional security suites are listed, and sensitive-path scans can run locally.
- `.agent/evals.json` exists, `scripts/agent_score.py score --write` runs, and `.agent/evals/latest.md` records current governance drift.
- `docs/adr/`, `docs/rfcs/`, and `docs/incidents/` exist with templates for durable decisions, proposals, and postmortems.
- Native Codex/Claude adapters exist when enabled and remain thin projections of `.agent/` policy.
- VS Code Remote assumptions are captured in session state.
- Validation commands exist and run.
- Substantial changes have fresh completion evidence; skipped checks have explicit reasons and residual risk.
- Delegated or substantial implementation ran spec compliance review before code quality review, or records an accepted exception.
- Substantial implementation records assumptions, simplicity/abstraction justification, surgical diff scope, and success criteria, or records an accepted exception.
- No secrets or private host credentials are written.
- Compression does not alter headings, code blocks, inline code, URLs, paths, commands, versions, or technical identifiers.
- Existing project files were not overwritten without explicit instruction.

The initializer places target-project templates at:

```text
.agent/templates/project-review.md.tmpl
.agent/templates/project-fix-log.md.tmpl
```

## Findings

Use four severities:

- `blocker`: setup cannot be used, cannot be resumed, or can lose state.
- `major`: setup is materially incomplete or inaccurate.
- `minor`: wording, naming, or organization can improve.
- `note`: future improvement.

Resolve blocker and major findings before release, or document an explicit exception.

## Fix Loop

```text
review
  -> fix blocker/major findings
  -> re-run agent_check.py and relevant commands
  -> confirm workflow gate evidence or accepted exceptions
  -> record validation and accepted exceptions in runlog/session files
  -> refresh governance score when release readiness matters
  -> update review status
```

For skill development in this repository, use `skill_lifecycle.py review`, `fix-log`, and `review-status`.
