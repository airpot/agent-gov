# Specification Management

Use this reference when initializing or retrofitting a project with OpenSpec-backed specification management.

## Role Of OpenSpec

Use OpenSpec as the canonical source for change intent, design decisions, task lists, and spec deltas. Do not replace it with ad hoc project notes.

Recommended layout:

```text
openspec/
  config.yaml
  changes/
  specs/
```

`agent-gov` should create `openspec/config.yaml` only when missing. If an existing OpenSpec setup is present, leave it in place and report it.

## Initialization Rules

- Install the official latest OpenSpec CLI by default using `npm install -g @fission-ai/openspec@latest`.
- Require Node.js 20.19.0 or higher before installation.
- Run `openspec init <repo> --tools codex,claude` for new repositories, or `openspec update <repo>` when `openspec/` already exists.
- Use `--install-openspec never` only for offline, restricted, or already-managed environments.
- Use `--no-openspec` only when the target project intentionally does not use OpenSpec; in that case generated checks must not require `openspec/config.yaml`.
- Add project context that tells agents this repository uses OpenSpec for specification-driven development.
- Keep OpenSpec context short and stable.
- Use OpenSpec changes for non-trivial project changes, not for ordinary checkpoint notes.
- Link active session records to an OpenSpec change when work is change-driven.

## Boundary With AGENTS.md

- `AGENTS.md` should explain that OpenSpec is the spec source.
- OpenSpec should contain change-specific details.
- `.agent/sessions/` should contain volatile progress, handoff, and resume state.

## Release Gate

Before considering an OpenSpec-enabled project initialized:

- `openspec/config.yaml` exists or an existing equivalent is documented.
- Agents know when to create or continue OpenSpec changes.
- Session records can reference `openspec/changes/<name>/` without duplicating its content.

When OpenSpec is disabled, `.agent/config.json` should set `spec_source` to `none` and `openspec_enabled` to `false`.
