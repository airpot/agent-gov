# Skill Runtime Governance

Use this reference when a project builds, publishes, adapts, or reviews portable Skills, plugin-style runtimes, native host commands, hooks, or skill-impact benchmark claims.

## Adopted Mechanisms

Borrow these project-neutral mechanisms from verified portable skill/plugin architectures:

- Keep one canonical skill core. Put durable behavior in `SKILL.md`, `AGENTS.md`, `references/`, `scripts/`, and `assets/`.
- Keep host adapters thin. Codex, Claude, Cursor, Copilot, MCP, or other host files should load, project, or activate the canonical core rather than fork policy.
- Record adapter targets and parity evidence. Use generated projections, content hashes, invariant phrase checks, or manual merge notes when the same rule appears in multiple host files.
- Make native hook packaging explicit. Preserve hooks, strip hooks, suppress host autodiscovery with an empty hooks object, or record a manual merge skip intentionally; orphaned hook files and manifest entries are findings.
- Model runtime modes explicitly. Record allowed modes, default mode, deactivation mode, persistence location, switch command pattern, activation event, hook output shape, and safe fallback behavior.
- Model commands as lanes. Separate mode switches, complexity review, repo audit, debt harvest, impact scoreboard, and help/status instead of making every command an opaque prompt.
- Keep review lanes separate. Complexity-only review must not replace spec compliance, quality/security, debt ledger, or impact benchmark review.
- Treat measured impact as a benchmark claim. Require a real baseline arm, skill-enabled arm, isolated workspaces or plugin dirs, contamination self-test, correctness/safety gate, preserved artifacts, and limitation notes.
- Treat failed profile, benchmark, optimization, migration, and pipeline runs as failures. Validate inputs before expensive work, preserve evidence paths when available, mark the run failed, and exit non-zero.
- Track deliberate shortcuts with a neutral marker that names a ceiling and upgrade trigger. Harvest markers read-only by default.

Do not adopt these as absolute project rules:

- Do not import a source project's persona, command names, or product-specific behavior.
- Do not claim blocked or inaccessible articles as evidence.
- Do not force every project to publish multiple host adapters.
- Do not require network access, package installation, global plugin state, or external MCP servers for local governance doctors.

## Target Files

```text
.agent/
  skill-runtime.json
  manifest.json
  mechanical-checks.json
  evals.json
docs/
  SKILL_RUNTIME.md
  tech-debt.md
scripts/
  agent_check.py
  agent_verify.py
  agent_score.py
```

`.agent/skill-runtime.json` is the structured authority. `docs/SKILL_RUNTIME.md` is the human operating guide. Mechanical checks and score dimensions make the surface visible to normal governance validation.

## Required Sections

`.agent/skill-runtime.json` must include:

- `source_evidence`: each source labelled `verified`, `partial`, or `blocked`; blocked sources cannot drive rules.
- `canonical_core`: canonical core path patterns and the rule that adapters remain thin.
- `host_adapters`: adapter targets and parity policy.
- `runtime_modes`: modes, deactivation, persistence, switch pattern, activation events, and hook boundaries.
- `command_lanes`: mode switch, complexity review, repository audit, debt harvest, impact scoreboard, help/status.
- `review_lanes`: spec compliance, quality/security, complexity-only, debt ledger, impact benchmark.
- `impact_benchmarks`: isolation, contamination, correctness/safety, artifacts, and limitation policy.
- `shortcut_debt`: marker convention, required ceiling, required upgrade trigger, and ledger targets.
- `dependency_policy`: local doctors remain dependency-free and offline.

## Review Policy

For portable Skill/plugin work:

- Run spec compliance review before quality/security review.
- Run complexity-only review only as an additional lane. It may report delete/reuse/stdlib/native/existing-dependency/shrink/defer findings.
- Route correctness, security, privacy, data-loss, and accessibility concerns to quality/security review.
- For command changes, verify every command maps to a declared command lane.
- For mode/hook changes, verify persistence and deactivation behavior.
- For native hook changes, verify stdin EOF/error handling, UTF-8 BOM stripping before JSON parsing, valid host JSON output when required, preservation of empty `additionalContext`, and non-zero failure on invalid mandatory output.
- For host adapter changes, verify parity evidence before release claims.
- For impact claims, verify benchmark isolation and correctness/safety gates before using reductions as design evidence.
- For failed benchmark/profile/pipeline runs, verify the failure was not counted as an improvement or pass.

## Shortcut Debt

Use a project-neutral marker for deliberate simplifications with known ceilings:

```text
agent-gov-debt: <what was simplified>; ceiling: <limit>; upgrade_trigger: <when to revisit>
```

Markers without an upgrade trigger are findings. Harvesting is read-only by default. Persist ledgers only when requested, usually in `docs/tech-debt.md` or the active feature document.

## Validation

Run:

```bash
python3 scripts/agent_check.py
python3 scripts/agent_verify.py doctor
python3 scripts/agent_score.py doctor
python3 scripts/agent_score.py score --write
```

Generated checks must use Python standard-library JSON inspection. They must not depend on external plugin installation, network calls, global host state, or paid benchmark APIs.
