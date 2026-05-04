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
Long-term memory is a retrieval aid layered on top of session files. It never replaces `.agent/sessions/` as the source of truth.

## Required Session Files

```text
.agent/sessions/
  index.json
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
```

## Lifecycle

1. **start**
   - Create a session directory.
   - Record goal, remote workspace path, git branch, git commit, OpenSpec change, and client surface.

2. **checkpoint**
   - Update handoff, changed files, decisions, and validation results after a meaningful work block.
   - Checkpoint before compaction, large tool runs, branch switches, or leaving the workstation.
   - If subagents were used, record accepted snapshots, rejected snapshots, integration decisions, and follow-up validation.
   - Capture a concise memory record when the checkpoint changes future behavior or saves rediscovery work.
   - Ensure validation and session lifecycle evidence is present in `.agent/runlog.jsonl`.

3. **pre-compact**
   - Summarize task state into files before the session becomes too large.
   - Do not wait for OOM or context failure.
   - Run `python3 .agent/tools/agent_session.py compact`.
   - Run `python3 .agent/tools/agent_memory.py ingest-session --reason compact` to refresh searchable long-term memory.
   - Run `python3 .agent/tools/agent_context.py scan --limit 10` to refresh the context budget digest.
   - Treat native hook reminders as advisory; still checkpoint explicitly after meaningful work.

4. **rollover**
   - Start a new Codex session with `bootstrap.md` or `resume-prompt.md`.
   - Use progressive memory retrieval: `timeline` first, `search` second, `detail` only for selected records.
   - Use runlog retrieval: `tail` first, then `summary` when validation or session evidence is unclear.
   - Confirm `git status`, OpenSpec state, and validation status before editing.

5. **archive**
   - Mark completed sessions archived after the related change is complete.
   - Keep decisions and validation summaries; do not keep raw logs unless explicitly required.

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
4. Read linked OpenSpec artifacts.
5. Run `git status --short`.
6. Continue only after confirming current branch, dirty files, and remaining task.
7. Read any accepted subagent snapshots recorded in `handoff.md`, `changes.md`, or `validation.md`.
8. Run `python3 .agent/tools/agent_memory.py timeline --limit 10`, then search/detail only if needed.
9. Run `python3 .agent/tools/agent_context.py scan --limit 10` when bootstrap, docs, or memory digest look large.
10. Run `python3 scripts/agent_runlog.py tail --limit 10` when validation or handoff evidence is unclear.

## Automation Commands

Use these commands instead of manually stitching session files together:

```bash
python3 .agent/tools/agent_session.py bootstrap
python3 .agent/tools/agent_session.py compact --summary "..." --next "..."
python3 .agent/tools/agent_session.py doctor
python3 .agent/tools/agent_memory.py doctor
python3 .agent/tools/agent_context.py doctor
python3 .agent/tools/agent_memory.py search "<query>"
python3 scripts/agent_runlog.py tail --limit 10
python3 .agent/tools/governance_hook.py --event session-start
```

- `bootstrap` prints and refreshes the active session startup packet.
- `compact` refreshes `handoff.md`, `resume-prompt.md`, and `bootstrap.md`.
- `doctor` checks the active session files, validation notes, and dirty worktree continuity.
- `agent_memory.py` provides cross-session timeline/search/detail over concise summaries, decisions, validations, and handoffs. Its `doctor` command is read-only by default; use `init`, `ingest-session`, or `doctor --write` when refreshing stores is intended.
- `agent_context.py` keeps governance docs, bootstraps, memory digests, OpenSpec change docs, and subagent outputs within measured budgets. Its `doctor` command is read-only by default; use `scan` or `doctor --write` when refreshing the latest digest is intended.
- `agent_runlog.py` records and retrieves compact evidence for validations, session lifecycle actions, and high-risk capability use.
- `governance_hook.py` is an advisory native-hook bridge; session-start is read-only, and hooks should never be the only place session state is updated.

## Memory Privacy

- Store summaries, not raw model transcripts.
- Redact `<private>...</private>` blocks before memory capture.
- Do not write secrets, tokens, SSH keys, or private credentials to `.agent/memory/`.
- Treat memory search results as historical context; confirm current facts from the repository before editing.
- Keep memory class explicit: use `episodic` for session history, `semantic` for sourced project facts, and `procedural` only for reviewed workflow rules.

## Context Budget Rules

- Keep `AGENTS.md`, `CLAUDE.md`, session bootstraps, memory digests, and OpenSpec change docs concise enough to load progressively.
- Use `scan` for drift detection and `suggest` before manually compressing a large governance doc.
- Validate compressed rewrites with `validate-pair` before replacing the original.
- Prefer summaries plus retrieval commands over embedding long histories in bootstrap files.
