# Implementation Discipline

Use this reference when agent-governed development needs stronger protection against silent assumptions, over-engineering, broad side effects, and unverifiable completion claims.

## Source Mechanism

The `multica-ai/andrej-karpathy-skills` project packages a compact coding discipline across Claude, Cursor, and skill/plugin surfaces. The useful mechanism for `agent-gov` is not a standalone dependency. It is a governance gate that makes four behaviors explicit:

- Clarify assumptions before implementation when a request has multiple plausible meanings.
- Preserve the raw user goal, then write a refined goal with rationale, non-goals, constraints, evidence, and confirmation or assumption status before implementation.
- Prefer the smallest readable implementation that satisfies the current request.
- Keep edits traceable to the user's request and avoid unrelated cleanup.
- Convert work into success criteria with checks that can be run or inspected.

`DietrichGebert/ponytail` adds a useful complementary mechanism: make "simple enough" executable instead of rhetorical. Its transferable value is a ladder for choosing the smallest maintainable change, explicit safety carve-outs, a separate complexity-review pass, cross-host rule parity checks, and benchmark isolation. Do not borrow its persona, command names, or terse output style.

Source links:

- `https://github.com/multica-ai/andrej-karpathy-skills`
- `https://github.com/multica-ai/andrej-karpathy-skills/blob/main/CLAUDE.md`
- `https://github.com/multica-ai/andrej-karpathy-skills/blob/main/skills/karpathy-guidelines/SKILL.md`
- `https://github.com/multica-ai/andrej-karpathy-skills/blob/main/.cursor/rules/karpathy-guidelines.mdc`
- `https://github.com/DietrichGebert/ponytail`
- `https://github.com/DietrichGebert/ponytail/blob/main/AGENTS.md`
- `https://github.com/DietrichGebert/ponytail/blob/main/skills/ponytail/SKILL.md`
- `https://github.com/DietrichGebert/ponytail/blob/main/skills/ponytail-review/SKILL.md`
- `https://github.com/DietrichGebert/ponytail/blob/main/docs/agent-portability.md`
- `https://github.com/DietrichGebert/ponytail/blob/main/benchmarks/results/2026-06-18-agentic.md`

When external articles, repos, or social posts are used to update governance, record source status before adopting any idea:

- `verified`: content was fetched, cloned, or otherwise read from a stable source.
- `partial`: only metadata or snippets were available; use only the verified portion.
- `blocked`: content was inaccessible, captcha-gated, deleted, or extraction failed; document it as excluded evidence.

Never convert inaccessible source titles, remembered summaries, or search-result guesses into procedural project rules.

When a discovered practice should become durable project behavior, create or update a knowledge promotion bundle before changing procedural rules. The bundle must name source evidence, source status, candidate type, target surface, authority level, review status, validation command or review reference, and promotion/rejection/defer decision. Keep raw article bodies, chat transcripts, terminal scrollback, secrets, and long diagnostics out of tracked ledgers; use compact summaries and evidence handles.

## Adopted Policy

Add an `implementation_discipline` gate to `.agent/workflow.json` for implementation, refactor, new abstraction, architecture, and multi-file changes.

The gate should require:

- Assumptions and tradeoffs are stated when the request is ambiguous.
- The refined goal is recorded before editing, with raw goal, non-goals, success evidence, and confirmation or assumption status.
- The refined goal is decomposed into a tiny checklist, bugfix chain, or standard/full task graph before implementation.
- A simpler approach is offered when the current plan adds avoidable machinery.
- New abstractions are justified by repeated concrete complexity, an existing local pattern, or an approved design.
- No speculative features, configuration layers, plugin systems, queues, caches, or broad error-handling paths are added without a recorded need.
- Files, comments, formatting, and adjacent code are changed only when directly needed.
- Pre-existing dead code or unrelated issues are reported as follow-up notes instead of deleted during unrelated work.
- Behavior changes define success criteria and validation before completion is claimed.

Use this minimal-sufficient ladder before adding code or process:

1. Does the requested behavior need to exist now, or can the current project goal be met without it?
2. Does the codebase already have a helper, workflow, template, schema, command, or pattern that should be reused?
3. Does the language standard library or shell/toolchain already solve it well enough?
4. Does the native platform, database, browser, framework, or existing runtime feature cover it?
5. Does an already-installed dependency solve it without broadening the release or security surface?
6. Can the change be a small direct edit instead of a new abstraction or new file?
7. Only then add the minimum new implementation that satisfies the accepted requirements.

The ladder runs after understanding the request and touched flow, not before reading. For bug fixes, inspect likely callers and shared entry points before placing the fix; the smallest safe patch is often one guard in the common path, not several symptom-specific guards.

Never simplify away:

- input validation at trust boundaries;
- error handling that prevents data loss or unrecoverable state;
- security and privacy controls;
- accessibility requirements;
- calibration or operational knobs required by real runtime conditions;
- explicit user requirements or approved spec criteria;
- one runnable check for non-trivial logic.

When a deliberate simplification has a known ceiling, record the ceiling and upgrade trigger in the development note, review note, or a short code comment near the simplification. Do not add a speculative extension point just to prove the shortcut is understood.

## Review Evidence

Reviews should ask:

- Does each changed file and major changed block trace to the request, approved spec, or plan?
- Are incidental diff lines removed or recorded as accepted exceptions under `.agent/review-policy.json`?
- Was task risk classified under `.agent/risk-zones.json`, and did autonomy stay within that class?
- Did the implementation solve the present need with the simplest maintainable shape consistent with local patterns?
- Did the implementation climb the minimal-sufficient ladder before adding new code, files, dependencies, or governance surface?
- Was any new abstraction, framework, dependency, cache, queue, or config surface justified?
- Did any simplification remove validation, data-loss handling, security, accessibility, explicit requirements, or required checks?
- For bug fixes, was the root cause or shared entry point considered instead of patching only the reported symptom?
- Were external research claims marked verified, partial, or blocked before they influenced rules or design?
- Did any durable knowledge or procedural rule added by the change have a promotion bundle, review reference, or equivalent feature-doc evidence?
- Were raw transcripts, terminal scrollback, secrets, private host data, and long diagnostic logs kept out of tracked memory, runlog, session, and knowledge stores?
- Were assumptions, unresolved ambiguity, and tradeoffs surfaced before committing to implementation?
- Was the raw user goal preserved and converted into a refined goal before the durable task/session goal was set?
- Was the refined goal decomposed into an explicit next task or task graph before editing?
- Were success criteria converted into tests, commands, or inspected evidence?

Complexity-only review is allowed as a separate pass, but it must not replace spec, correctness, security, or release review. Complexity findings should name what can be deleted, reused, replaced with stdlib/native behavior, or deferred, and should route any correctness/security observation to the normal review path.

If an exception is accepted, record it in the active session, project review, or runlog. Exceptions should name the reason and remaining risk.

## Non-Goals

- Do not turn trivial one-line work into heavyweight process.
- Do not block a needed abstraction when the project already has a clear local pattern or the approved design requires it.
- Do not preserve bad code solely for minimal diffs when the requested change cannot be implemented safely without a local cleanup.
- Do not replace project-specific architecture, testing, or security rules with generic simplicity advice.
- Do not treat "shortest" as "least safe"; safety and explicit requirements outrank line-count reduction.
- Do not promote inaccessible external sources into durable governance rules.
