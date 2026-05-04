# Subagent Orchestration

Use this reference when a governed project should support delegated agent work. This distills the local `reference/agents.md` idea into a repository-safe policy that remains subordinate to the active platform, system, developer, and user instructions.

## Adoption Boundary

Borrow these practices:

- Role-based delegation for search, exploration, implementation, verification, review, and coordination work.
- Small input packets with explicit read/write boundaries.
- Disjoint write ownership for parallel workers.
- Structured `===SNAPSHOT===` JSON summaries before natural-language detail.
- Compressed, path-first supporting notes so delegated tool results do not consume the parent context budget.
- Fast cleanup of completed delegated work.
- Session handoff records that preserve accepted subagent results.

Do not adopt these as absolute project rules:

- A parent agent may not be forbidden from reading, editing, or validating when the active environment expects it to do so.
- A project rule may not force specific model names, reasoning levels, or tool calls.
- A project rule may not require subagents for every task.
- A project rule may not override higher-priority instructions about when delegation is allowed.

## Target Files

```text
.agent/
  subagents.json
  templates/
    subagent-task.md.tmpl
  sessions/
    <session-id>/
      handoff.md
      changes.md
      validation.md
  runlog.jsonl
```

`.agent/subagents.json` is the durable policy. `.agent/templates/subagent-task.md.tmpl` is the dispatch shape. Session files record accepted snapshots and integration decisions.

Native adapters are generated projections:

```text
.codex/agents/governance-*.toml
.claude/agents/governance-*.md
```

Keep `.agent/subagents.json` authoritative. If a native adapter exists and is project-specific, preserve it and merge manually.

## Role Taxonomy

- `searcher`: external documentation, standards, API behavior, and current ecosystem checks.
- `explorer`: repository discovery, file ownership, call graph, and risk mapping.
- `worker`: bounded implementation or mechanical edits within a declared write set.
- `verifier`: tests, builds, lint, typecheck, smoke checks, and log inspection.
- `reviewer`: independent risk review, conflict arbitration, and high-risk side-effect assessment.
- `coordinator`: optional submodule coordinator for large tasks with independent subsystem boundaries.

Roles are descriptive, not a license to bypass platform limits. Use the role names to clarify responsibility and expected evidence.

## Delegation Rules

1. Delegate only when the user request, active environment, and higher-priority instructions permit subagents.
2. Keep immediate blocking work local unless parallel delegation can proceed without stalling the critical path.
3. Give every subagent a narrow task goal, read boundary, write boundary, allowed operations, and expected validation.
4. Assign disjoint write boundaries to parallel workers.
5. Prefer `fork_context=false` or the nearest platform equivalent unless the subagent needs exact conversation context.
6. Do not pin a model unless the user or platform explicitly requires it.
7. Close or release completed subagents when the platform exposes lifecycle controls.
8. Record accepted snapshots in the active session before compaction or handoff.
9. Keep supporting notes within `.agent/context.json` budget, default 700 estimated tokens after the required JSON snapshot.
10. Record accepted worker, verifier, or reviewer snapshots in `.agent/runlog.jsonl` when they materially affect validation, risk, or handoff.

## Snapshot Contract

Require delegated agents to start their final report with:

```text
===SNAPSHOT===
```

Follow it with JSON:

```json
{
  "status": "success | partial | blocked",
  "role": "searcher | explorer | worker | verifier | reviewer | coordinator",
  "files_touched": [],
  "exports_added_or_modified": [],
  "critical_finding": "short finding",
  "next_dependency": "recommended next task or none",
  "estimated_risk_level": "low | medium | high",
  "validation": []
}
```

After the JSON, the subagent may add concise notes. It must separate confirmed facts from inference when reporting risks.

Use path-first notes when possible:

```text
path/to/file.py:42 - `symbol` - short confirmed fact.
```

For reviews, one line per finding is preferred unless security or architecture risk needs fuller rationale.

## Integration Checklist

- Read `.agent/subagents.json` before delegating.
- Use `.agent/templates/subagent-task.md.tmpl` for dispatch wording.
- Use native Codex/Claude governance agents only when the active client supports them.
- Inspect snapshot `status`, `files_touched`, `estimated_risk_level`, and `validation` before integrating.
- Reject or summarize snapshots that ignore the output budget before storing them in session handoff files.
- Reconcile conflicts through a reviewer role or local review.
- Run relevant harness commands after integrating worker changes.
- Add a checkpoint that records the accepted snapshots, rejected snapshots, validation, and remaining risks.
- Add runlog evidence for accepted high-risk snapshots and any skipped post-integration validation.
