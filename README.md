# Agent Gov

Project-level skills and a one-command initializer for governing long-running agent-driven software work. The main published skill is `.codex/skills/agent-gov`.

Recommended GitHub repository name: `agent-gov`.

Recommended npm package name: `@airpot/agent-gov`.

## Quick Start

Initialize the current repository:

```bash
npx @airpot/agent-gov@latest
```

Initialize with an explicit stack and layout:

```bash
npx @airpot/agent-gov@latest --tech-stack python,typescript --layout service
```

The npm command copies bundled project skills into `.codex/skills/` and then runs the `agent-gov` initializer for the target repository. Existing files are preserved unless `--force` or `--force-skill` is supplied.

Useful variants:

```bash
npx @airpot/agent-gov@latest init /path/to/repo --remote-kind ssh
npx @airpot/agent-gov@latest install-skill /path/to/repo
npx @airpot/agent-gov@latest doctor /path/to/repo
```

After installing project-level skills, restart or reload Codex so the new skills are discovered.

## Skill Development

```bash
python3 .codex/skills/skill-dev-framework/scripts/skill_lifecycle.py start my-skill \
  --description "Describe what the skill does. Use when Codex should apply this workflow." \
  --resources scripts,references \
  --positive-prompt "Create a project-level skill for a concrete workflow." \
  --negative-prompt "Fix an unrelated application bug." \
  --realistic-prompt "Build a skill with references, validation, and eval cases."

python3 .codex/skills/skill-dev-framework/scripts/skill_lifecycle.py check my-skill
python3 .codex/skills/skill-dev-framework/scripts/skill_lifecycle.py review my-skill
python3 .codex/skills/skill-dev-framework/scripts/skill_lifecycle.py fix-log my-skill
make validate
```

For current Codex/Claude skill distribution, keep editable sources in `.codex/skills` and mirror with the generated target-project `scripts/agent_sync_skills.py` when needed.

## Layout

- `.codex/skills/`: Project-level skills discovered by Codex.
- `.codex/skills/skill-dev-framework/`: Meta skill for skill design, scaffolding, validation, and evaluation.
- `skillflows/`: Lifecycle briefs for non-trivial skills.
- `evals/`: Positive, negative, and realistic skill eval cases.
- `openspec/`: Planning context for larger changes.
- `Makefile`: Common validation commands.

## Main Commands

```bash
make validate
make lifecycle-check SKILL=skill-dev-framework
make review-status SKILL=skill-dev-framework
```

## Agent Gov

Use `$agent-gov`, the npm entrypoint, or the initializer directly:

```bash
npx @airpot/agent-gov@latest --remote-kind ssh --tech-stack python,typescript --layout service

python3 .codex/skills/agent-gov/scripts/init_agent_project.py /path/to/repo \
  --remote-kind ssh \
  --tech-stack python,typescript \
  --layout service
```

The generated target project includes OpenSpec config, `AGENTS.md`, optional `CLAUDE.md`, `.agent/sessions/`, `.agent/memory.json`, `.agent/memory/`, `.agent/context.json`, `.agent/context/`, `.agent/harness.json`, `.agent/project-layout.json`, `.agent/subagents.json`, `.agent/hooks.json`, `.agent/knowledge.json`, `.agent/skill-distribution.json`, native Codex/Claude subagent and hook adapters, fixed project directories, `docs/`, `scripts/agent_check.py`, `scripts/agent_validate.py`, `scripts/agent_sync_skills.py`, and durable `.agent/tools/agent_session.py` / `.agent/tools/agent_memory.py` / `.agent/tools/agent_context.py` workflows.

`agent-gov` installs the official latest OpenSpec CLI by default and runs `openspec init` or `openspec update` for the target repository. Use `--install-openspec never` only when installation is managed externally.

## Install From npm

After publishing to npm, the shortest install path is:

```bash
npx @airpot/agent-gov@latest
```

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

## Publish

```bash
cd /work/project_skill
git init
git config user.name "airpot"
git config user.email "airpot@foxmail.com"
git add .
git commit -m "Publish agent governance skills"
git branch -M main
git remote add origin git@github.com:airpot/agent-gov.git
git push -u origin main
```

Validate before pushing or publishing:

```bash
PYTHONDONTWRITEBYTECODE=1 make validate
PYTHONDONTWRITEBYTECODE=1 python3 .codex/skills/skill-dev-framework/scripts/skill_lifecycle.py check agent-gov
npm pack --dry-run
```

Publish the npm package:

```bash
npm login
npm publish --access public
```
