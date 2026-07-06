# Project Blueprint Governance

Use this reference when a project needs a durable product and architecture blueprint before feature-level implementation.

## Role

The project blueprint is the global current contract for product purpose, users/operators, non-goals, workflows, domain model, system boundary, quality attributes, runtime/framework decisions, module layout, data/state ownership, external resources, MCP boundary, security, validation strategy, milestones, open decisions, and linked specs/ADRs.

Embedded OpenSpec changes remain the change-level contract for one proposed change. They must declare whether they affect the global blueprint through `.agent-spec.json#/blueprint_impact`.

## Generated Surface

For `standard` and `full` profiles, agent-gov generates:

```text
.agent/blueprint.json
docs/PROJECT_BLUEPRINT.md
.agent/templates/project-blueprint.md.tmpl
scripts/agent_blueprint.py
```

`core` profile projects do not require blueprint governance by default.

## Workflow Gate

After requirements interview and before non-trivial implementation:

1. Confirm product purpose, users/operators, non-goals, and core workflows.
2. Confirm technical architecture, module/directory boundary, and data/state ownership.
3. Confirm external resources, MCP boundary, security/risk boundary, and validation strategy.
4. Confirm agent runtime/framework strategy in `.agent/blueprint.json#/runtime_framework_decision`.
5. Run `python3 scripts/agent_blueprint.py doctor`.
6. Create or continue the feature-level OpenSpec change and fill `.agent-spec.json#/blueprint_impact`.

Record unresolved choices in the blueprint `open_decisions` list instead of implementing around them silently.

## Runtime Framework Rules

- `agent` and `hybrid` targets default to `framework-first`.
- Skill-first agent projects default to Strands as the primary adapter unless the blueprint selects another accepted adapter.
- Add Pydantic AI when typed tools, schema-first outputs, or strong structured extraction are architectural requirements.
- Add LangGraph when long-running, recoverable, graph/state-machine, or human-in-the-loop workflows are architectural requirements.
- `mcp-server` targets default to `mcp-first`; require tool/resource/prompt, transport, host/client, credential, and destructive-operation boundaries without forcing model profiles.
- `library` targets may use `library-only` with rationale.
- Direct hand-written LLM orchestration requires `manual-llm-exception` with rationale, owner, review evidence, validation evidence, residual risk, and linked ADR or exception record.

agent-gov generates package plans but does not install runtime dependencies. Dependency execution belongs to application code after review.

## OpenSpec Impact

Every generated change in a blueprint-governed project includes:

```yaml
affected_blueprint_ids: []
impact_type: none
runtime_framework_impact: none
blueprint_update_required: false
adr_required: false
no_impact_reason: ""
```

Validation rules:

- `impact_type`: `none`, `add`, `modify`, or `deprecate`.
- `runtime_framework_impact`: `none`, `add`, `change`, or `exception`.
- Non-`none` impact must name known blueprint IDs unless this is the bootstrap change that introduces blueprint governance before `.agent/blueprint.json` exists.
- Architecture/runtime/layout/data/resource/security/MCP/validation/harness-looking no-impact changes need a meaningful `no_impact_reason`.
- Archive is blocked when `blueprint_update_required` is true without update evidence, or when runtime framework change/exception lacks linked ADR or accepted exception evidence.

## Review

Review blueprint work before implementation and during release readiness:

- `scripts/agent_blueprint.py doctor` passes.
- `docs/PROJECT_BLUEPRINT.md` has all required sections.
- `.agent/blueprint.json` has unique stable IDs.
- Runtime decision agrees with `.agent/agent-runtime.json`.
- Active OpenSpec changes have valid `blueprint_impact`.
- Archive blocking reasons are either resolved or explicitly accepted with owner, date, and residual risk.
