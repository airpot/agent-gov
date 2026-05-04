# Workflow Governance

Use this reference when a governed project should make agent development stages explicit instead of relying on a chat transcript or informal habits.

## Adopted Mechanisms

Borrow these practices from mature agent workflow projects:

- Check applicable workflow instructions before acting.
- Get design or specification approval before implementation for non-trivial changes.
- Convert approved specs into executable plans with exact files, commands, expected results, and no placeholders.
- Surface assumptions, ambiguity, and tradeoffs before implementation when a request has multiple plausible meanings.
- Prefer simple direct code, and justify new abstractions or speculative flexibility before adding them.
- Keep diffs surgical: every changed line should trace to the request, approved spec, or local cleanup caused by the change.
- Prefer isolated git worktrees for feature work, plan execution, and risky refactors.
- Establish a clean baseline before editing so new failures can be attributed.
- For behavior changes, capture failing-test evidence before production code and passing evidence after the fix.
- For bugs and build/test failures, record reproduction, root cause, hypothesis, fix, and validation.
- For delegated or substantial work, run spec compliance review before code quality review.
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
  worktrees.json
  runlog.jsonl
  templates/
    implementation-plan.md.tmpl
    debugging-record.md.tmpl
  sessions/
    <session-id>/
      validation.md
      handoff.md
```

`.agent/workflow.json` is the lifecycle policy. `.agent/worktrees.json` is the isolation and finish policy. Session files and runlog entries store evidence.

## Lifecycle Stages

Use these stages for substantial work:

1. `intake`: understand request, repository state, active session, and constraints.
2. `spec`: create or continue the embedded spec change, RFC, or documented approval.
3. `plan`: write an implementation plan with exact files, commands, and expected results.
4. `isolation`: choose branch/worktree, verify ignore rules when project-local, and capture baseline validation.
5. `implementation`: execute task by task with simple direct code, surgical diffs, and preferably TDD for behavior changes.
6. `spec_review`: verify the implementation matches the requested spec and does not add unrequested behavior.
7. `quality_review`: verify maintainability, tests, security, performance, and project conventions.
8. `verification`: run fresh validation commands and record output summaries.
9. `handoff`: checkpoint session state, runlog ids, accepted subagent snapshots, and remaining risks.
10. `finish`: merge, create PR, keep branch, or discard only after the user chooses.

## Plan Quality

Plans should be executable by an agent that has no prior session context:

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
- Treat `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, and `BLOCKED` as workflow states that need handling before review.
- Run `spec_reviewer` first and resolve missing or extra behavior.
- Run `quality_reviewer` only after spec review passes.
- Re-review after fixes; do not carry open important findings into the next task without an explicit exception.
- Record accepted snapshots and review decisions in the active session before compaction.

## Completion Claims

Before saying work is complete:

- Identify the command or checklist that proves the claim.
- Run the command fresh or inspect fresh recorded evidence.
- Read the output and exit status.
- Record the command, result, and runlog id or session validation note.
- State skipped checks plainly with reasons and residual risk.
