# Context Budget

Use this reference when agent-facing project governance files are becoming large enough to harm session startup, rollover, subagent delegation, or review quality.

## Borrowed Ideas

The useful ideas from `caveman` are context economy, measurable token budgets, safe compression validation, lifecycle hooks, and concise subagent outputs. Do not borrow the comedic style. Governance output should stay professional, precise, and easy to audit.

## Target Files

```text
.agent/
  context.json
  context/
    stats.jsonl
    latest.md
  capabilities.json
  workflow.json
  worktrees.json
  tooling.json
  security.json
  evals.json
  evals/
    latest.md
  templates/
    context-summary.md.tmpl
  tools/
    agent_context.py
```

`.agent/context.json` is the policy. `.agent/context/latest.md` is the digest loaded during session bootstrap. `.agent/context/stats.jsonl` records scans over time.

## Budget Model

Use approximate tokens, not provider-specific tokenizer APIs. The generated tool uses `ceil(chars / 4)`, which is stable, local, and good enough for budget drift detection.

Default budgets:

- Total tracked governance context: 20000 estimated tokens.
- `AGENTS.md`: 1600 estimated tokens.
- `CLAUDE.md`: 2500 estimated tokens.
- Single durable doc: 3000 estimated tokens.
- Session bootstrap: 5000 estimated tokens.
- Memory digest: 1200 estimated tokens.
- Capability registry: 3000 estimated tokens through the single durable doc budget.
- Tooling and security registries: 3000 estimated tokens each through the single durable doc budget.
- Workflow and worktree policy: 3000 estimated tokens each through the single durable doc budget.
- Governance score config and latest dashboard: 3000 estimated tokens each through the single durable doc budget.
- Subagent supporting notes after the snapshot JSON: 700 estimated tokens.
- Single review finding: 120 estimated tokens.

Budgets are warnings by default. Projects can set `doctor_fails_on_budget_excess` when they want a hard gate.

## Safe Compression Rules

Compress only natural-language governance text. Preserve exactly:

- Markdown headings.
- Fenced code blocks.
- Inline code.
- URLs and Markdown links.
- File paths.
- Shell commands.
- API names, symbols, package names, versions, dates, and numeric values.
- Embedded spec change ids and task ids.

Remove or shorten:

- Pleasantries, throat-clearing, hedging, and repeated disclaimers.
- Duplicate examples that prove the same rule.
- Long prose that can become a pointer to a detailed doc or command.
- Repeated platform instructions that already live in `AGENTS.md`.

Do not compress:

- Source code files.
- JSON/YAML/TOML config files.
- `.env`, credentials, keys, token files, private host config, or anything under private environment directories.
- Raw transcripts, secrets, or terminal scrollback.

## Validation

Before replacing a governance doc with a compressed version, keep an original copy and validate:

```bash
python3 .agent/tools/agent_context.py validate-pair <original> <compressed>
```

The validator treats changed headings, code blocks, URLs, and inline code as errors. Path and bullet count drift are warnings because legitimate compression can merge prose, but warnings must still be reviewed before handoff.

## Commands

```bash
python3 .agent/tools/agent_context.py doctor
python3 .agent/tools/agent_context.py scan --limit 10
python3 .agent/tools/agent_context.py suggest
python3 .agent/tools/agent_context.py validate-pair <original> <compressed>
```

`doctor` is read-only by default. Run `scan` before compaction or when `AGENTS.md`, `CLAUDE.md`, docs, embedded spec change docs, workflow policy, worktree policy, or session bootstraps grow substantially. Use `doctor --write` only when you want a health check to refresh the latest context digest.

## Lifecycle Integration

- Session start hook is read-only: it runs a no-write context preview and prints a short budget view.
- Session compact refreshes `.agent/context/latest.md`.
- Bootstrap includes the latest context digest.
- Review-fix gates check whether governance files exceed budgets or duplicate instructions.
- Subagent dispatch packets include an output budget so tool results do not flood the parent context.
