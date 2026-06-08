# Implementation Discipline

Use this reference when agent-governed development needs stronger protection against silent assumptions, over-engineering, broad side effects, and unverifiable completion claims.

## Source Mechanism

The `multica-ai/andrej-karpathy-skills` project packages a compact coding discipline across Claude, Cursor, and skill/plugin surfaces. The useful mechanism for `agent-gov` is not a standalone dependency. It is a governance gate that makes four behaviors explicit:

- Clarify assumptions before implementation when a request has multiple plausible meanings.
- Prefer the smallest readable implementation that satisfies the current request.
- Keep edits traceable to the user's request and avoid unrelated cleanup.
- Convert work into success criteria with checks that can be run or inspected.

Source links:

- `https://github.com/multica-ai/andrej-karpathy-skills`
- `https://github.com/multica-ai/andrej-karpathy-skills/blob/main/CLAUDE.md`
- `https://github.com/multica-ai/andrej-karpathy-skills/blob/main/skills/karpathy-guidelines/SKILL.md`
- `https://github.com/multica-ai/andrej-karpathy-skills/blob/main/.cursor/rules/karpathy-guidelines.mdc`

## Adopted Policy

Add an `implementation_discipline` gate to `.agent/workflow.json` for implementation, refactor, new abstraction, architecture, and multi-file changes.

The gate should require:

- Assumptions and tradeoffs are stated when the request is ambiguous.
- A simpler approach is offered when the current plan adds avoidable machinery.
- New abstractions are justified by repeated concrete complexity, an existing local pattern, or an approved design.
- No speculative features, configuration layers, plugin systems, queues, caches, or broad error-handling paths are added without a recorded need.
- Files, comments, formatting, and adjacent code are changed only when directly needed.
- Pre-existing dead code or unrelated issues are reported as follow-up notes instead of deleted during unrelated work.
- Behavior changes define success criteria and validation before completion is claimed.

## Review Evidence

Reviews should ask:

- Does each changed file and major changed block trace to the request, approved spec, or plan?
- Are incidental diff lines removed or recorded as accepted exceptions under `.agent/review-policy.json`?
- Was task risk classified under `.agent/risk-zones.json`, and did autonomy stay within that class?
- Did the implementation solve the present need with the simplest maintainable shape consistent with local patterns?
- Was any new abstraction, framework, dependency, cache, queue, or config surface justified?
- Were assumptions, unresolved ambiguity, and tradeoffs surfaced before committing to implementation?
- Were success criteria converted into tests, commands, or inspected evidence?

If an exception is accepted, record it in the active session, project review, or runlog. Exceptions should name the reason and remaining risk.

## Non-Goals

- Do not turn trivial one-line work into heavyweight process.
- Do not block a needed abstraction when the project already has a clear local pattern or the approved design requires it.
- Do not preserve bad code solely for minimal diffs when the requested change cannot be implemented safely without a local cleanup.
- Do not replace project-specific architecture, testing, or security rules with generic simplicity advice.
