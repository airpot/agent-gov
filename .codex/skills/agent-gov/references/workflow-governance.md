# Workflow Governance

Use this reference when a governed project should make agent development stages explicit instead of relying on a chat transcript or informal habits.

## Adopted Mechanisms

Borrow these practices from mature agent workflow projects:

- Check applicable workflow instructions before acting.
- Route every non-Q&A request through proactive intake: classify request kind, risk, required gates, and whether spec/task records are needed.
- Preserve the raw user goal before rewriting it. Set durable task/session goals only after recording a refined goal, rationale, non-goals, constraints, success evidence, confirmation or assumption status, and open questions.
- Get design or specification approval before implementation for non-trivial changes.
- Convert approved specs into executable plans with exact files, commands, expected results, and no placeholders.
- Convert accepted goals into task decomposition before implementation: tiny checklist, bugfix fix chain, or standard/full task graph.
- Convert iterative work into explicit loop contracts with goals, observation signals, budgets, stop conditions, evidence paths, and escalation rules.
- Classify non-tiny iterative loops by readiness level before continuation: `manual`, `report_only`, `assisted`, or `unattended`.
- Require unattended loops to have attempt ledger evidence, stable failure signatures, quota/circuit-breaker controls, explicit interrupt points, state persistence, and safe stop behavior before automatic continuation.
- Record a compact goal contract for standard/full or otherwise long-running work: objective, user-approved outcome, non-goals, constraints, success evidence, stop conditions, current decision summary, open decisions, task id, and spec id.
- Surface assumptions, ambiguity, and tradeoffs before implementation when a request has multiple plausible meanings.
- Run a requirements interview for non-tiny work: one unresolved question at a time, recommended answer plus rationale, shared-understanding confirmation, domain glossary updates, and code/docs cross-checks before design or implementation.
- Convert requirements interview output into a global project blueprint before non-trivial architecture or implementation work. Use `.agent/blueprint.json` and `docs/PROJECT_BLUEPRINT.md` for product purpose, system boundary, runtime/framework choice, layout, data/state ownership, resource/MCP/security boundaries, validation strategy, milestones, open decisions, and linked specs/ADRs.
- Prefer simple direct code, and justify new abstractions or speculative flexibility before adding them.
- For research-driven updates, record each external source as verified, partial, or blocked before using it as governance evidence.
- Use a minimal-sufficient ladder before adding implementation or process: skip unneeded work, reuse local patterns, prefer standard library/native platform features, use existing dependencies before new ones, and only then add the smallest new code.
- Keep simplicity bounded by safety: validation, data-loss handling, security, accessibility, explicit requirements, and required checks are not simplification targets.
- Keep diffs surgical: every changed line should trace to the request, approved spec, or local cleanup caused by the change.
- Classify task risk and autonomy before implementation; stop and re-plan when the risk level increases.
- Separate requested, necessary-support, incidental, and risky diff lines before handoff.
- Treat automated review as a precheck; high and critical risk changes need recorded human diff or file review evidence.
- Prefer isolated git worktrees for feature work, plan execution, and risky refactors.
- Establish a clean baseline before editing so new failures can be attributed.
- For behavior changes, capture failing-test evidence before production code and passing evidence after the fix.
- For bugs and build/test failures, record reproduction, root cause, hypothesis, fix, and validation.
- For delegated or substantial work, run spec compliance review before code quality review.
- When over-engineering is a material risk, run a complexity-only audit as a separate precheck that identifies deletions, local reuse, stdlib/native replacements, and avoidable dependencies; do not let it replace correctness or security review.
- For portable Skill/plugin work, check `.agent/skill-runtime.json`: keep one canonical Skill core, keep host adapters thin, map native commands to command lanes, verify runtime mode deactivation/persistence, and require adapter parity evidence before release claims.
- For skill-impact claims, require benchmark evidence with baseline and skill-enabled arms, isolated workspaces or plugin dirs, contamination self-test, correctness/safety gates, preserved artifacts, and limitation notes.
- For every task profile, run review-fix-review before completion. Tiny tasks use lightweight evidence in the active session, runlog, or `.agent/intake/` when no task-board record exists; bugfix tasks review reproduction/root-cause/regression; standard/full tasks use protected stage exits.
- For non-tiny work loops, use `.agent/loop-engineering.json` and `docs/LOOP_ENGINEERING.md` to bound plan-act-observe-adjust, review-fix-review, debugging, eval optimization, and session recovery loops.
- Use safe fallback lanes only when they preserve the unresolved human gate and stay within read-only analysis, test preparation, docs review, planning, or artifact inventory.
- Archive embedded spec changes as soon as they reach `all_done`; do not leave completed work in `openspec/changes/<name>/`.
- Require fresh validation evidence before claiming completion, merge readiness, or PR readiness.
- Treat knowledge promotion as a reviewed handoff: session observations, external research, or repeated workflow lessons should become durable only through an evidence-backed promotion bundle with source status, target surface, authority level, freshness, and review reference.
- Present branch finish choices explicitly; destructive cleanup needs explicit confirmation.

Do not adopt these as absolute project rules:

- Do not override higher-priority system, developer, user, platform, or repository instructions.
- Do not force subagents when the active environment disallows them.
- Do not require a worktree for tiny documentation or configuration edits when it would add more risk than value.
- Do not turn trivial one-line fixes into heavyweight process.
- Do not delete branches, worktrees, or commits without explicit user confirmation.
- Do not store raw transcripts, secrets, tokens, or terminal scrollback as workflow evidence.
- Do not promote procedural knowledge from a single unverified source when the bundle requires reviewed or durable authority.

## Target Files

```text
.agent/
  blueprint.json
  workflow.json
  workflow-profiles.json
  loop-engineering.json
  task-board.json
  risk-zones.json
  review-policy.json
  worktrees.json
  role-contracts.json
  mechanical-checks.json
  baselines.json
  runlog.jsonl
  templates/
    project-blueprint.md.tmpl
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
  PROJECT_BLUEPRINT.md
  DOMAIN_GLOSSARY.md
  features/
    INDEX.md
```

`.agent/workflow.json` is the lifecycle policy. `.agent/workflow-profiles.json` maps task size and risk to process weight. `.agent/loop-engineering.json` defines bounded loop contracts, budgets, stop conditions, evidence, and escalation. `.agent/task-board.json` is the cross-session task index. `.agent/role-contracts.json` makes role inputs, outputs, forbidden actions, and finder-cannot-fix separation machine-checkable. `.agent/risk-zones.json` is the risk and autonomy policy. `.agent/review-policy.json` is the diff traceability and human review policy. `.agent/worktrees.json` is the isolation and finish policy. Session files and runlog entries store evidence.
`.agent/blueprint.json` and `docs/PROJECT_BLUEPRINT.md` are the global product and architecture authority. OpenSpec changes are the change-level authority and declare `.agent-spec.json#/blueprint_impact`.
`.agent/intake/` is the optional pre-task holding area for raw/refined goals, stack intake, tiny no-task-board review evidence, and next-gate decisions before a task id exists.

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

For task-board-backed `tiny`, `bugfix`, `standard`, and `full` tasks, `state=done` requires a passing review gate:

- `review_gate.status` is `pass`
- `review_gate.latest_review` points to an existing review document
- `review_gate.open_findings` is empty
- the delivery conclusion is recorded

For `standard` and `full` tasks, protected stage exits also require the same loop discipline. For `tiny` and `bugfix`, completion requires the profile-specific review-fix evidence defined in `.agent/workflow-profiles.json` and `.agent/task-board.json`.

- create a review record for the stage result
- keep any finding-bearing review as `needs-fix`
- route fixes back to the coordinator or worker, not the reviewer
- re-run relevant validation after fixes
- create a fresh re-review round and only proceed when blocker, major, and minor findings are empty

The task board is not a casual TODO list. It is the project-local source for current and historical agent work when a new session starts.

## Lifecycle Stages

Use these stages for substantial work:

1. `intake`: understand request, repository state, active session, and constraints.
2. `goal_refinement`: preserve raw goal, write refined goal, and record confirmation or assumption status.
3. `requirement_interview`: resolve key ambiguities one question at a time, record shared understanding, update domain glossary terms, and cross-check important claims against current code/docs.
4. `task_decomposition`: turn the refined goal into a tiny checklist, bugfix chain, or standard/full task graph with a next task.
5. `spec`: create or continue the embedded spec change, RFC, or documented approval.
6. `plan`: write an implementation plan with exact files, commands, and expected results.
7. `isolation`: choose branch/worktree, verify ignore rules when project-local, and capture baseline validation.
8. `implementation`: execute task by task with simple direct code, surgical diffs, and preferably TDD for behavior changes.
9. `spec_review`: verify the implementation matches the requested spec and does not add unrequested behavior.
10. `quality_review`: verify maintainability, tests, security, performance, and project conventions.
11. `verification`: run fresh validation commands and record output summaries.
12. `handoff`: checkpoint session state, runlog ids, accepted subagent snapshots, and remaining risks.
13. `finish`: merge, create PR, keep branch, or discard only after the user chooses.

At minimum, standard/full work must pass review-fix-review before exiting `spec`, `plan`, `implementation`, `spec_review`, `quality_review`, `verification`, and `handoff`. If a review finds blocker, major, or minor issues, fix them, revalidate, and create the next review round rather than changing the original review to `pass`.

## Loop Engineering

Use `.agent/loop-engineering.json` for non-tiny work that can repeat. The loop contract should name:

- loop type: `work_loop`, `review_fix_loop`, `debugging_loop`, `eval_optimization_loop`, or `session_recovery_loop`
- readiness level: `manual`, `report_only`, `assisted`, or `unattended`
- goal and owner role
- observation signal that tells the agent whether the iteration improved, failed, or changed risk
- iteration budget and stop conditions
- evidence path for each iteration
- escalation rule when the same failure repeats or the budget is exhausted

Do not retry the same patch, prompt, test command, tool sequence, or review round after the same failure repeats without a new hypothesis or strategy change. Record attempts with loop id, iteration id, readiness level, owner role, action summary, evidence paths, result status, failure signature, strategy-change flag, budget usage, and next transition. When the failure reveals a missing rule, script, workflow gate, role boundary, knowledge source, or context budget, classify it in `.agent/harness-evolution.json`; use `loop_gap` when the missing control is the loop contract itself.

Loop state transitions should be explicit enough to resume safely: pending, running, waiting_human, waiting_tool, paused, retrying, replan, blocked, completed, failed, and cancelled. Budget exhaustion may only lead to replan, blocked, a human gate, failed, or an accepted exception. Before replaying external mutation after resume, require the last committed step, side-effect boundary, and idempotency or approval evidence.

## Plan Quality

Plans should be executable by an agent that has no prior session context:

- Include task risk, autonomy allowed, approval/review requirements, and stop conditions.
- List exact files to create, modify, test, and document.
- Split work into small, independently verifiable tasks.
- Include commands and expected results for red, green, and broader validation.
- Name any external sources that influence the plan and whether each source was verified, partial, or blocked.
- For Skill/plugin architecture plans, state which source mechanisms are being adopted as project-neutral governance and which source-specific behavior is intentionally not imported.
- Identify the reuse/native/stdlib path considered before proposing new dependencies, new abstractions, or new governance surface.
- Avoid placeholder wording such as future fill-ins or vague "handle edge cases" instructions.
- Repeat needed context inside each delegated task instead of asking a subagent to infer it from the full plan.
- Link to embedded spec changes, ADRs, RFCs, or docs for broader context.

## Implementation Discipline

Before editing, use the `implementation_discipline` gate for non-trivial implementation, refactors, new abstractions, architecture changes, and multi-file changes:

- State assumptions and tradeoffs when the request is ambiguous.
- Offer the simpler approach when the proposed implementation adds avoidable machinery.
- Build the smallest readable version that satisfies the current request and local conventions.
- Apply the minimal-sufficient ladder: skip unneeded work, reuse local code, prefer standard library/native platform capabilities, use existing dependencies, then add only the minimum new implementation.
- Add abstractions only when repeated concrete complexity, an existing project pattern, or an approved design justifies them.
- Avoid unrequested flexibility, configuration layers, plugin systems, caches, queues, background jobs, or broad error-handling paths.
- Touch only files, comments, formatting, and adjacent code needed for the request.
- Remove only dead code or unused imports created by the current change unless the user approved broader cleanup.
- Define success criteria as tests, commands, or inspectable evidence before claiming completion.
- For bug fixes, inspect shared callers or entry points before patching a symptom-specific branch.
- For deliberate simplifications with a known ceiling, record the ceiling and upgrade trigger in development or review evidence rather than adding speculative machinery.

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
- Run a complexity/austerity audit as an additional review pass when scope, dependency, or abstraction growth is a risk; keep its findings scoped to what can be deleted, reused, replaced, or deferred.
- Re-review after fixes; do not carry open important findings into the next task without an explicit exception.
- Record accepted snapshots and review decisions in the active session before compaction.

## Completion Claims

Before saying work is complete:

- Identify the command or checklist that proves the claim.
- Run the command fresh or inspect fresh recorded evidence.
- For standard and full work, compare before/after mechanical snapshots when available.
- Treat new invalid JSON, missing required paths, newly broken local links, template-render failures, and test-count decreases as baseline regressions unless an explicit exception is recorded.
- For task-board-backed work, confirm task-board `review_gate.status=pass` with no open blocker, major, or minor findings.
- For tiny work without a task-board record, confirm active session, runlog, or `.agent/intake/` contains lightweight review-fix evidence.
- For embedded spec work, run `python3 scripts/agent_spec.py status --change <name> --json`; if the state is `all_done`, run `python3 scripts/agent_spec.py archive <name>` before the completion claim.
- Read the output and exit status.
- Record the command, result, and runlog id or session validation note.
- Before rollover or compaction for long-running work, refresh `grounding.md` and add only evidence-backed offload entries for context that would otherwise be lost.
- State skipped checks plainly with reasons and residual risk.
