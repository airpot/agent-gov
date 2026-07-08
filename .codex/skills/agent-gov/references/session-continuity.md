# Session Continuity

Use this reference when initializing or resuming long-running Codex/Claude work, especially in VS Code Remote environments.

## Mental Model

```text
VS Code UI and Codex extension
  -> Codex native thread or plugin session
  -> remote shell and remote filesystem
  -> repository state in .agent/sessions/
```

The repository state is authoritative. Native Codex threads, plugin state, open editor tabs, selections, and terminal scrollback are temporary.
Long-term memory is a retrieval aid layered on top of durable project files. It never replaces embedded specs, `.agent/task-board.json`, `docs/DEV_MAP.md`, feature docs, ADR/RFC/postmortem records, runlog entries, validation notes, or `.agent/sessions/` as sources of truth.

Long-running work also needs a compact goal contract. The goal contract is the current user-approved objective, outcome, non-goals, constraints, success evidence, stop conditions, decision summary, open decisions, task id, and spec id. It should be updated in task-board state, session handoff, feature docs, or decisions when the objective changes; it should not copy the full proposal or chat history into every session file.

## Required Session Files

```text
.agent/sessions/
  index.json
  events.jsonl
  active.md
  <session-id>/
    session.md
    context.md
    decisions.md
    changes.md
    validation.md
    handoff.md
    resume-prompt.md
    bootstrap.md
    artifacts.json
    grounding.md
    offload.jsonl
    offload-index.md
    task-map.mmd
    refs/
      git-status-short.txt
  bootstrap.md
.agent/memory/
  events.jsonl
  index.sqlite3           # generated optional search index
  latest.md
  summaries/
.agent/context/
  stats.jsonl
  latest.md
.agent/runlog.jsonl
.agent/task-board.json
.agent/workflow-profiles.json
.agent/role-contracts.json
.agent/mechanical-checks.json
.agent/baselines.json
.agent/dev-map.json
.agent/harness-evolution.json
docs/features/
docs/DEV_MAP.md
```

## Lifecycle

1. **start**
   - Create a session directory.
   - Create `grounding.md`, `offload.jsonl`, `offload-index.md`, `task-map.mmd`, `refs/.gitkeep`, and runtime `refs/git-status-short.txt`.
   - Append a `started` event to `.agent/sessions/events.jsonl`.
   - Record goal, remote workspace path, git branch, git commit, embedded spec change, and client surface.
   - For standard/full or long-running work, initialize or link the goal contract from `.agent/task-board.json` and the active session templates.
   - Record current workflow stage, base branch, and worktree path when isolated work is used.

2. **checkpoint**
   - Update handoff, changed files, decisions, and validation results after a meaningful work block.
   - Checkpoint before compaction, large tool runs, branch switches, or leaving the workstation.
   - Record workflow gate evidence: spec/design approval, plan quality, implementation discipline, baseline validation, TDD/debugging evidence, review sequence, and completion verification.
   - Refresh the goal contract when objective, non-goals, success evidence, stop conditions, decision summary, or open decisions change.
   - Record task-board id, workflow profile, current stage, feature-doc path, and before/after baseline snapshot names when they apply.
   - Record knowledge promotion candidates as concise bundles in decisions or feature docs when a session observation, source review, or repeated workflow lesson might become durable project knowledge.
   - If subagents were used, record accepted snapshots, rejected snapshots, integration decisions, and follow-up validation.
   - Capture a concise memory record when the checkpoint changes future behavior or saves rediscovery work; repeated identical session ingests should dedupe by session/reason/content hash.
   - Ensure validation and session lifecycle evidence is present in `.agent/runlog.jsonl`.
   - Append a `checkpoint` event to `.agent/sessions/events.jsonl` with concise summary, changed files, validation, and next-step payload.
   - Keep long `git status --short` output in `refs/git-status-short.txt`; `changes.md` and `bootstrap.md` may show truncated human-readable snapshots that point to this full file. After commands that write session files, refresh the full snapshot last so it matches the current worktree state.
   - Bootstrap and compact output must stay as compact recovery packets with evidence handles. Do not inline long historical `handoff.md`, `changes.md`, `validation.md`, `grounding.md`, memory digest, context digest, archived specs, or old dirty-tree bodies.

3. **pre-compact**
   - Summarize task state into files before the session becomes too large.
   - Update `.agent/task-board.json` and relevant `docs/features/<task-id>/` stage documents before compaction.
   - Add evidence-backed offload entries with `python3 .agent/tools/agent_session.py offload-add --summary "..." --evidence <path-or-runlog-id>` for context that would otherwise be lost.
   - Do not wait for OOM or context failure.
   - Run `python3 .agent/tools/agent_session.py compact`.
   - Run `python3 .agent/tools/agent_memory.py ingest-session --reason compact` to refresh searchable long-term memory; identical compact summaries should not create duplicate memory records.
   - Run `python3 .agent/tools/agent_context.py scan --limit 10` to refresh the context budget digest.
   - Treat native hook reminders as advisory; still checkpoint explicitly after meaningful work.

4. **rollover**
   - Start a new Codex session with `bootstrap.md` or `resume-prompt.md`.
   - Run `python3 .agent/tools/agent_session.py rollover` before leaving a long session when possible.
   - Read `grounding.md` and `offload-index.md` after `active.md`; treat offload recall as advisory until verified against current files.
   - Read recent append-only session events with `python3 .agent/tools/agent_session.py events --limit 10` when handoff state is unclear.
   - Use progressive memory retrieval: `timeline` first, `search` second, `detail` only for selected records.
   - Use runlog retrieval: `tail` first, then `summary` when validation or session evidence is unclear.
   - Confirm `git status`, embedded spec state, and validation status before editing.

5. **archive**
   - Mark completed sessions archived after the related change is complete.
   - Keep goal contract, decisions, validation summaries, and evidence handles; do not keep raw logs unless explicitly required in an allowed artifact path.
   - Preserve branch/worktree finish decision and any destructive cleanup confirmation.

## VS Code Remote Rules

- Save relevant buffers before checkpointing.
- Convert `@file`, selected text, and open-tab assumptions into stable paths and line references.
- Record remote workspace path, not local UI path.
- Record command results in `validation.md`, not only in terminal scrollback.
- If cloud-delegated work returns to the IDE, checkpoint the diff, branch, and validation state before continuing.
- If subagent work returns to the parent session, checkpoint the snapshot summary before compacting or starting a new Codex thread.

## Resume Prompt Requirements

`resume-prompt.md` must instruct the next agent to:

1. `cd` into the remote workspace.
2. Read `.agent/sessions/active.md`.
3. Read current session `handoff.md`, `context.md`, `changes.md`, and `validation.md`.
4. Read linked embedded spec artifacts.
5. Run `git status --short` and compare it with current session `refs/git-status-short.txt`; treat the `bootstrap.md` status block as a human-readable excerpt when it is truncated.
6. Continue only after confirming current branch, dirty files, and remaining task.
7. Read `.agent/workflow.json`, `.agent/workflow-profiles.json`, `.agent/task-board.json`, `.agent/role-contracts.json`, `docs/DEV_MAP.md`, and `.agent/worktrees.json` when the remaining task involves implementation, validation, review, delegation, or branch/worktree finish.
8. Read any accepted subagent snapshots recorded in `handoff.md`, `changes.md`, or `validation.md`.
9. Run `python3 .agent/tools/agent_memory.py timeline --limit 10`, then search/detail only if needed.
10. Run `python3 .agent/tools/agent_context.py scan --limit 10` when bootstrap, docs, or memory digest look large.
11. Run `python3 scripts/agent_runlog.py tail --limit 10` when validation or handoff evidence is unclear.
12. Use `python3 .agent/tools/agent_session.py offload-recall <query>` only after reading `offload-index.md`; verify recalled facts against repository truth sources.

## Automation Commands

Use these commands instead of manually stitching session files together:

```bash
python3 .agent/tools/agent_session.py bootstrap
python3 .agent/tools/agent_session.py grounding --checked "git status --short"
python3 .agent/tools/agent_session.py offload-add --summary "..." --evidence <path-or-runlog-id>
python3 .agent/tools/agent_session.py offload-recall "<query>"
python3 .agent/tools/agent_session.py offload-map
python3 .agent/tools/agent_session.py rollover --summary "..." --next "..."
python3 .agent/tools/agent_session.py compact --summary "..." --next "..."
python3 .agent/tools/agent_session.py doctor
python3 .agent/tools/agent_session.py events --limit 10
python3 .agent/tools/agent_memory.py doctor
python3 .agent/tools/agent_context.py doctor
python3 .agent/tools/agent_memory.py search "<query>"
python3 scripts/agent_task.py list
python3 scripts/agent_verify.py doctor
python3 scripts/agent_gc.py report
python3 scripts/agent_runlog.py tail --limit 10
python3 .agent/tools/governance_hook.py --event session-start
```

- `bootstrap` prints and refreshes the active session startup packet. It must stay compact and evidence-handle based; full details live behind `refs/git-status-short.txt`, `offload-index.md`, runlog ids, memory detail ids, and embedded spec paths.
- `grounding` refreshes the truth-first repository snapshot; current files, configs, specs, task-board state, runlog evidence, and validation notes override memory and prior chat.
- `offload-add` records compact session context with evidence handles. Entries are advisory and must not contain raw transcripts, terminal scrollback, secrets, or unsupported claims.
- `offload-recall` searches advisory offload entries with bounded human-readable output; use it after `offload-index.md`, then verify selected facts from evidence handles.
- `offload-map` refreshes a small Mermaid task canvas from structured offload entries.
- `rollover` refreshes handoff, grounding, offload index, task map, bootstrap, and resume prompt for a new native session.
- `compact` refreshes `handoff.md`, `resume-prompt.md`, and `bootstrap.md`.
- `events` reads the append-only session event stream. It is the session lifecycle event source; markdown files remain the human-readable handoff layer.
- `doctor` checks the active session files, validation notes, and dirty worktree continuity through `refs/git-status-short.txt` so long dirty trees do not create false warnings from truncated markdown snapshots.
- `agent_memory.py` provides cross-session timeline/search/detail over concise summaries, decisions, validations, and handoffs. Search output is bounded by `.agent/memory.json` recall limits; use `detail <id>` for selected full records. Its `doctor` command is read-only by default; use `init`, `ingest-session`, or `doctor --write` when refreshing stores is intended.
- `agent_context.py` keeps governance docs, bootstraps, memory digests, embedded spec change docs, and subagent outputs within measured budgets. Its `doctor` command is read-only by default; use `scan` or `doctor --write` when refreshing the latest digest is intended.
- `agent_runlog.py` records and retrieves compact evidence for validations, session lifecycle actions, and high-risk capability use.
- `governance_hook.py` is an advisory native-hook bridge; session-start is read-only, and hooks should never be the only place session state is updated.

## Memory Privacy

- Store summaries, not raw model transcripts.
- Redact `<private>...</private>` blocks before memory capture.
- Do not write secrets, tokens, SSH keys, or private credentials to `.agent/memory/`.
- Treat memory search results as historical context; confirm current facts from the repository before editing.
- Keep memory class explicit: use `episodic` for session history, `semantic` for sourced project facts, and `procedural` only for reviewed workflow rules.
- Promote procedural memory only through reviewed evidence such as a knowledge promotion bundle or review artifact; memory remains advisory even after promotion evidence exists.

## Context Budget Rules

- Keep `AGENTS.md`, `CLAUDE.md`, session bootstraps, memory digests, and embedded spec change docs concise enough to load progressively.
- Use `scan` for drift detection and `suggest` before manually compressing a large governance doc.
- Validate compressed rewrites with `validate-pair` before replacing the original.
- Prefer summaries plus retrieval commands over embedding long histories in bootstrap files.
