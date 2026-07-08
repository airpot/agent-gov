# Skill Self-Optimization Governance

Use this reference when a project skill, production skill, or agent-system release needs optimization, release preflight, or self-improvement governance.

## Control Plane

Generated standard and full projects include:

```text
.agent/skill-optimization.json
docs/SKILL_OPTIMIZATION.md
scripts/agent_skill_opt.py
skillflows/<skill>/optimization/
```

`.agent/skill-optimization.json` is the structured policy. `docs/SKILL_OPTIMIZATION.md` is the operator guide. `scripts/agent_skill_opt.py` is the dependency-free local command surface. `skillflows/<skill>/optimization/` stores durable signal, candidate, rejection, preflight, and rollback evidence.

## Required Policy

The policy must define:

- enabled skills or a default skill policy;
- risk class and allowed optimization mode;
- triggers: `manual`, `failure-threshold`, `release-gate`, and `scheduled-sleep`;
- thresholds for repeated failures, corrections, review findings, regression failures, context-budget failures, and release-gate failures;
- gate requirements for selection, held-out regression, review-fix, release preflight, and rollback;
- target, optimizer, and reviewer role boundaries;
- resource, model, credential, and cost boundaries;
- release preflight artifacts and fail-closed behavior.

`scheduled-sleep` is a `scheduled_routine`, not a goal-only loop. It must record cadence or event source, disable or expiry policy, owner, run location, permission mode, resource and credential boundary, cost boundary, dry-run default, human interrupt points, evidence path, and fail-closed behavior.

## Modes

- `manual-only`: report suggestions only.
- `auto-candidate`: stage candidate artifacts and gates, but never write production skill files.
- `auto-apply-staged`: apply candidate to a staging branch, worktree, or candidate artifact after gates.
- `auto-promote`: apply passing candidate edits to local production skill files only when policy explicitly permits it and rollback evidence exists.

`auto-promote` never publishes packages, pushes remotes, signs releases, or bypasses release-check.

## Release Preflight

Before any agent-system or production skill release, run:

```bash
python3 scripts/agent_skill_opt.py preflight --skill <skill>
```

Release preflight must produce:

```text
skillflows/<skill>/optimization/release-preflight/<release-id>/
  signal-scan.md
  candidate-summary.md
  gate-report.md
  rejected-edits.jsonl
  release-decision.md
  rollback-plan.md
```

The release id is derived from skill name, version or date, and current skill source tree identity unless explicitly overridden with `--release-id`.

Release-check validates existing preflight evidence only. It must fail without mutating production files when preflight evidence is missing, stale, or failing, and it must print the exact `agent_skill_opt.py preflight` repair command.

## Blocking Conditions

Block release when:

- repeated optimization signals are untriaged;
- candidate edits lack gate evidence;
- gate failures lack rejection reasons;
- `auto-promote` lacks rollback evidence;
- preflight artifacts are missing or stale;
- release-decision does not record `status: pass`.

An empty `rejected-edits.jsonl` is valid only when no edits were rejected.
