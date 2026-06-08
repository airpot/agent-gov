# Workflow Governance

Use this reference when a governed project should make agent development stages explicit instead of relying on a chat transcript or informal habits.

## Adopted Mechanisms

Borrow these practices from mature agent workflow projects:

- Check applicable workflow instructions before acting.
- Get design or specification approval before implementation for non-trivial changes.
- Convert approved specs into executable plans with exact files, commands, expected results, and no placeholders.
- Surface assumptions, ambiguity, and tradeoffs before implementation when a request has multiple plausible meanings.
- Run a requirements interview for non-tiny work: one unresolved question at a time, recommended answer plus rationale, shared-understanding confirmation, domain glossary updates, and code/docs cross-checks before design or implementation.
- Prefer simple direct code, and justify new abstractions or speculative flexibility before adding them.
- Keep diffs surgical: every changed line should trace to the request, approved spec, or local cleanup caused by the change.
- Classify task risk and autonomy before implementation; stop and re-plan when the risk level increases.
- Separate requested, necessary-support, incidental, and risky diff lines before handoff.
- Treat automated review as a precheck; high and critical risk changes need recorded human diff or file review evidence.
- Prefer isolated git worktrees for feature work, plan execution, and risky refactors.
- Establish a clean baseline before editing so new failures can be attributed.
- For behavior changes, capture failing-test evidence before production code and passing evidence after the fix.
- For bugs and build/test failures, record reproduction, root cause, hypothesis, fix, and validation.
- For delegated or substantial work, run spec compliance review before code quality review.
- For `standard` and `full` tasks, run review-fix-review at protected stage exits and keep it running until the task-board `review_gate.status` is `pass`, `open_findings` is empty, and the latest review document exists.
- Archive embedded spec changes as soon as they reach `all_done`; do not leave completed work in `openspec/changes/<name>/`.
- Require fresh validation evidence before claiming completion, merge readiness, or PR readiness.
- Present branch finish choices explicitly; destructive cleanup needs explicit confirmation.

Do not adopt these as absolute project rules:

- Do not override higher-priority system, developer, user, platform, or repository instructions.
- Do not force subagents when the active environment disallows them.
- Do not require a worktree for tiny documentation or configuration edits when it would add more risk than value.
- Do not turn trivial one-line fixes into heavyweight process.
- Do not delete branches, worktrees, or commits without explicit user confirmation.
- Do not store raw transcripts, secrets, tokens, or terminal scrollback as workflow evidence.

## Target Files

```text
.agent/
  workflow.json
  workflow-profiles.json
  task-board.json
  risk-zones.json
  review-policy.json
  worktrees.json
  role-contracts.json
  mechanical-checks.json
  baselines.json
  runlog.jsonl
  templates/
    implementation-plan.md.tmpl
    debugging-record.md.tmpl
    features/
      01_REQUIREMENT_ANALYSIS.md.tmpl
      02_SOLUTION_DESIGN.md.tmpl
      03_GATE_REVIEW.md.tmpl
      04_DEVELOPMENT.md.tmpl
      05_CODE_REVIEW.md.tmpl
      06_TEST_REPORT.md.tmpl
      07_DELIVERY_SUMMARY.md.tmpl
  sessions/
    <session-id>/
      validation.md
      handoff.md
      grounding.md
      offload-index.md
      offload.jsonl
docs/
  DOMAIN_GLOSSARY.md
  features/
    INDEX.md
```

`.agent/workflow.json` is the lifecycle policy. `.agent/workflow-profiles.json` maps task size and risk to process weight. `.agent/task-board.json` is the cross-session task index. `.agent/role-contracts.json` makes role inputs, outputs, forbidden actions, and finder-cannot-fix separation machine-checkable. `.agent/risk-zones.json` is the risk and autonomy policy. `.agent/review-policy.json` is the diff traceability and human review policy. `.agent/worktrees.json` is the isolation and finish policy. Session files and runlog entries store evidence.

## Workflow Profiles

Use the lightest profile that covers the risk:

- `tiny`: low-risk small changes; no feature document required by default.
- `bugfix`: reproducible bug or failed check; record requirement, development, test report, and delivery summary.
- `standard`: normal multi-file or behavior work; record requirement, design, development, code review, test report, and delivery summary.
- `full`: architecture, migration, release, critical risk, or cross-team handoff; record all seven stage documents.

Escalate the profile when task risk increases. Do not force a full flow for tiny changes.

## Task Board And Feature Docs

Use `.agent/task-board.json` for durable task state across sessions. It records task id, title, state, risk, profile, current stage, docs path, requirements status, delivery conclusion, review gate status, and related tasks. Use `scripts/agent_task.py new` to create a task and scaffold `docs/features/<task-id>/` from the profile-specific stage templates.

For `bugfix`, `standard`, and `full` tasks, the requirements interview gate must be complete before protected stages such as `plan`, `implementation`, review, verification, handoff, or done state. Completion means:

- `requirements.status=complete`
- shared understanding is recorded
- code/docs cross-check was performed
- `docs/DOMAIN_GLOSSARY.md` was updated or explicitly confirmed current
- `docs/features/<task-id>/01_REQUIREMENT_ANALYSIS.md` exists

For `standard` and `full` tasks, `state=done` requires a passing review gate:

- `review_gate.status` is `pass`
- `review_gate.latest_review` points to an existing review document
- `review_gate.open_findings` is empty
- the delivery conclusion is recorded

For `standard` and `full` tasks, protected stage exits also require the same loop discipline:

- create a review record for the stage result
- keep any finding-bearing review as `needs-fix`
- route fixes back to the coordinator or worker, not the reviewer
- re-run relevant validation after fixes
- create a fresh re-review round and only proceed when blocker, major, and minor findings are empty

The task board is not a casual TODO list. It is the project-local source for current and historical agent work when a new session starts.

## Lifecycle Stages

Use these stages for substantial work:

1. `intake`: understand request, repository state, active session, and constraints.
2. `requirement_interview`: resolve key ambiguities one question at a time, record shared understanding, update domain glossary terms, and cross-check important claims against current code/docs.
3. `spec`: create or continue the embedded spec change, RFC, or documented approval.
4. `plan`: write an implementation plan with exact files, commands, and expected results.
5. `isolation`: choose branch/worktree, verify ignore rules when project-local, and capture baseline validation.
6. `implementation`: execute task by task with simple direct code, surgical diffs, and preferably TDD for behavior changes.
7. `spec_review`: verify the implementation matches the requested spec and does not add unrequested behavior.
8. `quality_review`: verify maintainability, tests, security, performance, and project conventions.
9. `verification`: run fresh validation commands and record output summaries.
10. `handoff`: checkpoint session state, runlog ids, accepted subagent snapshots, and remaining risks.
11. `finish`: merge, create PR, keep branch, or discard only after the user chooses.

At minimum, standard/full work must pass review-fix-review before exiting `spec`, `plan`, `implementation`, `spec_review`, `quality_review`, `verification`, and `handoff`. If a review finds blocker, major, or minor issues, fix them, revalidate, and create the next review round rather than changing the original review to `pass`.

## Plan Quality

Plans should be executable by an agent that has no prior session context:

- Include task risk, autonomy allowed, approval/review requirements, and stop conditions.
- List exact files to create, modify, test, and document.
- Split work into small, independently verifiable tasks.
- Include commands and expected results for red, green, and broader validation.
- Avoid placeholder wording such as future fill-ins or vague "handle edge cases" instructions.
- Repeat needed context inside each delegated task instead of asking a subagent to infer it from the full plan.
- Link to embedded spec changes, ADRs, RFCs, or docs for broader context.

## Implementation Discipline

Before editing, use the `implementation_discipline` gate for non-trivial implementation, refactors, new abstractions, architecture changes, and multi-file changes:

- State assumptions and tradeoffs when the request is ambiguous.
- Offer the simpler approach when the proposed implementation adds avoidable machinery.
- Build the smallest readable version that satisfies the current request and local conventions.
- Add abstractions only when repeated concrete complexity, an existing project pattern, or an approved design justifies them.
- Avoid unrequested flexibility, configuration layers, plugin systems, caches, queues, background jobs, or broad error-handling paths.
- Touch only files, comments, formatting, and adjacent code needed for the request.
- Remove only dead code or unused imports created by the current change unless the user approved broader cleanup.
- Define success criteria as tests, commands, or inspectable evidence before claiming completion.

Reviewers should flag unnecessary abstraction, broad rewrites, speculative extensibility, and unrelated cleanup as findings unless an accepted exception is recorded.

## Risk And Review Evidence

Use `.agent/risk-zones.json` for task risk:

- `low`: agent may implement after a plan; human review is optional.
- `medium`: agent may implement after a plan; human review is recommended.
- `high`: agent may implement only after approval; human review is required.
- `critical`: agent should not autonomously modify; a human owner must drive the plan.

Use `.agent/review-policy.json` for traceability:

- Requested lines are directly asked for by the user, spec, or approved plan.
- Necessary-support lines are required to make the requested change correct.
- Incidental lines should be removed or recorded as an exception.
- Risky lines require risk review and, for high or critical risk, human review evidence.

Human review evidence must name reviewer, review type, diff range, files reviewed, high-risk paths checked, and conclusion. Agent summaries and automated reviews can inform this process but do not replace required tests or human review.

## TDD And Debugging Evidence

For behavior changes, record:

- The test or executable check written before implementation.
- The failing command and expected failure.
- The smallest implementation change.
- The passing command and any broader regression command.

For failures, record:

- Reproduction steps and whether the failure is consistent.
- Recent changes checked.
- Evidence at component boundaries when multiple layers are involved.
- A single hypothesis, a minimal test of that hypothesis, and the confirmed root cause.
- The validation command proving the fix.

Use `.agent/templates/debugging-record.md.tmpl` when the root cause is not immediately obvious.

## Worktree Policy

Use `.agent/worktrees.json` to keep isolation predictable:

- Prefer an existing `.worktrees/` directory, then `worktrees/`, then a documented global fallback.
- Verify project-local worktree directories are ignored before creating worktrees.
- Record base branch, feature branch, worktree path, and baseline validation in the active session.
- Do not proceed from a failing baseline without a user decision or explicit session note.
- Offer finish choices instead of assuming merge, PR, keep, or discard.
- Require typed confirmation before discard and explicit user instruction for force deletion.

## Review Sequence

For delegated or substantial work:

- Use a `worker` for bounded implementation only when delegation is allowed.
- Enforce `.agent/role-contracts.json`: verifier and reviewer roles report findings and route fixes back; they do not fix their own findings directly.
- Treat `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, and `BLOCKED` as workflow states that need handling before review.
- Run `spec_reviewer` first and resolve missing or extra behavior.
- Run `quality_reviewer` only after spec review passes.
- Re-review after fixes; do not carry open important findings into the next task without an explicit exception.
- Record accepted snapshots and review decisions in the active session before compaction.

## Completion Claims

Before saying work is complete:

- Identify the command or checklist that proves the claim.
- Run the command fresh or inspect fresh recorded evidence.
- For standard and full work, compare before/after mechanical snapshots when available.
- Treat new invalid JSON, missing required paths, newly broken local links, template-render failures, and test-count decreases as baseline regressions unless an explicit exception is recorded.
- For standard and full work, confirm task-board `review_gate.status=pass` with no open blocker, major, or minor findings.
- For embedded spec work, run `python3 scripts/agent_spec.py status --change <name> --json`; if the state is `all_done`, run `python3 scripts/agent_spec.py archive <name>` before the completion claim.
- Read the output and exit status.
- Record the command, result, and runlog id or session validation note.
- Before rollover or compaction for long-running work, refresh `grounding.md` and add only evidence-backed offload entries for context that would otherwise be lost.
- State skipped checks plainly with reasons and residual risk.
