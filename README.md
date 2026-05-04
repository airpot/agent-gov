# Agent Gov

One-command project governance initializer for long-running Codex and Claude agent workflows.

`@airpot/agent-gov` installs repo-local skills and initializes a durable project governance harness with embedded spec management, session continuity, long-term memory, context budgets, validation/runlog evidence, review gates, and optional Codex/Claude native adapters.

## Quick Start

Initialize the current repository:

```bash
npx @airpot/agent-gov@latest
```

Initialize with an explicit stack and fixed layout:

```bash
npx @airpot/agent-gov@latest --tech-stack python,typescript --layout service
```

Useful variants:

```bash
npx @airpot/agent-gov@latest init /path/to/repo --remote-kind ssh
npx @airpot/agent-gov@latest install-skill /path/to/repo
npx @airpot/agent-gov@latest doctor /path/to/repo
```

The npm command copies bundled project skills into `<repo>/.codex/skills/` and then runs the `agent-gov` initializer. Existing files are preserved unless `--force` or `--force-skill` is supplied.

After installing project-level skills, restart or reload Codex so the new skills are discovered.

## What It Generates

The initialized target project includes:

- `AGENTS.md` and optional `CLAUDE.md`
- embedded spec config in `.agent/spec.json` and `openspec/`
- session continuity under `.agent/sessions/`
- repo-local memory and context budget stores under `.agent/memory/` and `.agent/context/`
- `.agent/harness.json`, `.agent/workflow.json`, `.agent/worktrees.json`, `.agent/subagents.json`, `.agent/hooks.json`, `.agent/knowledge.json`, `.agent/capabilities.json`, `.agent/runlog.jsonl`, `.agent/tooling.json`, `.agent/security.json`, and `.agent/evals.json`
- native Codex and Claude subagent/hook adapter files when enabled
- `docs/` governance docs and local scripts such as `scripts/agent_check.py`, `scripts/agent_spec.py`, `scripts/agent_validate.py`, and `scripts/agent_score.py`

The workflow layer captures spec approval, plan quality, implementation discipline, isolated worktree execution, TDD/debugging evidence, spec-review before quality-review, and fresh validation before completion claims.

The implementation-discipline gate integrates the useful ideas from `andrej-karpathy-skills`: surface assumptions, prefer simple direct changes, justify new abstractions, keep diffs tied to the request, and define verifiable success criteria.

`agent-gov` does not install or call a global OpenSpec CLI. Spec lifecycle commands are provided by generated `scripts/agent_spec.py`.

## Common Commands

Run these inside an initialized target repository:

```bash
python3 scripts/agent_check.py
python3 scripts/agent_spec.py doctor
python3 scripts/agent_validate.py --list
python3 scripts/agent_capabilities.py doctor
python3 scripts/agent_runlog.py doctor
python3 scripts/agent_tooling.py doctor
python3 scripts/agent_security.py doctor
python3 scripts/agent_score.py score --write
python3 .agent/tools/agent_session.py bootstrap
python3 .agent/tools/agent_memory.py timeline --limit 10
python3 .agent/tools/agent_context.py scan --limit 10
```

## Install From npm

Global installation is optional:

```bash
npm install -g @airpot/agent-gov
agent-gov
```

The npm package exposes `agent-gov` as the command name while keeping package ownership under the `@airpot` scope.

## Install From GitHub

GitHub installation remains available when npm is not desired:

```text
Install skill from https://github.com/airpot/agent-gov/tree/main/.codex/skills/agent-gov
```

Restart Codex after installation so the new skills are discovered.

## Maintainer Checks

Validate before pushing or publishing:

```bash
npm run validate
```

Publish the npm package:

```bash
npm login
npm publish --access public
```
