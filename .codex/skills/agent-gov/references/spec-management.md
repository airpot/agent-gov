# Specification Management

Use this reference when initializing or retrofitting a project with agent-gov's embedded OpenSpec-style specification management.

## Role Of Embedded Specs

Use the embedded spec layer as the canonical source for non-trivial change intent, design decisions, task lists, and spec deltas. Do not depend on a global `openspec` binary, npm package, or separately installed base skill.

Recommended layout:

```text
.agent/
  spec.json
openspec/
  config.yaml
  project.md
  changes/
    <change-name>/
      .agent-spec.json
      proposal.md
      design.md
      tasks.md
      specs/
    archive/
  specs/
scripts/
  agent_spec.py
```

`agent-gov` should create these files when missing and preserve existing project files by default. If an existing `openspec/` directory is present, treat it as project data and add only missing embedded governance files unless `--force` is explicitly used.

## Initialization Rules

- Do not install the official OpenSpec CLI.
- Do not run `openspec init`, `openspec update`, or `openspec list`.
- Generate `.agent/spec.json`, `openspec/config.yaml`, `openspec/project.md`, `openspec/changes/`, `openspec/changes/archive/`, `openspec/specs/`, and `scripts/agent_spec.py`.
- Use `python3 scripts/agent_spec.py doctor` as the spec health check.
- Use `python3 scripts/agent_spec.py list --json` for active change discovery.
- Use `python3 scripts/agent_spec.py new-change <name>` for new changes.
- Use `python3 scripts/agent_spec.py status --change <name> --json` for change status.
- Use `python3 scripts/agent_spec.py archive <name>` for completed changes.
- Treat artifact status as `missing`, `draft`, or `done`; scaffolded templates are drafts until their required sections and change-specific tasks are filled.
- Treat change state as `blocked` until all required artifacts are `done`; `ready` means artifacts are complete but implementation tasks remain; `all_done` means all checkbox tasks are complete.
- Add project context that tells agents this repository uses embedded spec-driven development.
- Keep spec context short and stable.
- Use embedded spec changes for non-trivial project changes, not for ordinary checkpoint notes.
- Link active session records to a spec change when work is change-driven.
- Treat non-trivial implementation as a gated flow: approved proposal/design, then implementation plan, then execution.
- For multi-step work, require plan artifacts to list exact files, commands, expected results, and review/validation checkpoints.
- Do not start implementation from an ambiguous or unapproved spec unless the user explicitly asks for exploratory work and the session records that exception.

## Boundary With AGENTS.md

- `AGENTS.md` should explain that embedded spec management is the spec source.
- `openspec/` should contain change-specific details.
- `.agent/spec.json` should contain embedded spec policy and paths.
- `.agent/sessions/` should contain volatile progress, handoff, and resume state.
- `.agent/workflow.json` should contain the cross-project policy for when spec approval, plan quality, implementation discipline, TDD/debugging, and review gates apply.

## Release Gate

Before considering a project initialized:

- `.agent/spec.json` exists and has schema `agent-spec-v1`.
- `scripts/agent_spec.py doctor` passes.
- `openspec/config.yaml`, `openspec/project.md`, `openspec/changes/`, and `openspec/specs/` exist.
- Agents know when to create or continue embedded spec changes.
- Session records can reference `openspec/changes/<name>/` without duplicating its content.
- The generated workflow policy points agents from spec approval to plan execution and fresh validation evidence.
