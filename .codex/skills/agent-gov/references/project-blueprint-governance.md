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
3. Confirm technology version constraints for languages/runtimes, package managers, frameworks/libraries, datastores/services, deployment targets, and agent runtime/MCP SDKs; record exact versions, supported ranges, LTS lines, managed-service versions, or accepted defer-to-lockfile policies.
4. Confirm external resources, MCP boundary, security/risk boundary, and validation strategy.
5. Confirm agent runtime/framework strategy in `.agent/blueprint.json#/runtime_framework_decision`.
6. Run `python3 scripts/agent_blueprint.py doctor`; before implementation, run `python3 scripts/agent_blueprint.py readiness`.
7. Create or continue the feature-level OpenSpec change and fill `.agent-spec.json#/blueprint_impact`.

Record unresolved choices in the blueprint `open_decisions` list instead of implementing around them silently.
Record unresolved version choices in `.agent/blueprint.json#/technology_version_decisions.open_version_decisions`; these are valid draft evidence but do not satisfy implementation readiness until a concrete version/range or accepted lockfile policy is recorded.

## Technology Version Rules

- Technology stack names without version constraints are incomplete intake for non-tiny design.
- Acceptable constraints include exact versions, semantic ranges, LTS lines, distro package versions, managed-service versions, and explicit defer-to-application-lockfile policies.
- Existing projects should use evidence from lockfiles, manifests, `.tool-versions`, Dockerfiles, CI config, package-manager metadata, and deployment config before asking the user to restate known versions.
- Agent runtime package plans must record package version constraints or an accepted application lockfile policy before readiness.
- Do not auto-install, silently pin, or auto-upgrade dependencies from agent-gov. Dependency execution remains application-owned and review-before-execution.

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
- `scripts/agent_blueprint.py readiness` passes before non-trivial implementation.
- `docs/PROJECT_BLUEPRINT.md` has all required sections.
- `.agent/blueprint.json` has unique stable IDs.
- `.agent/blueprint.json` and required blueprint records are marked `reviewed`.
- `.agent/blueprint.json#/technology_version_decisions` records concrete version constraints or accepted lockfile policy; open version decisions alone block implementation readiness.
- Runtime decision agrees with `.agent/agent-runtime.json`.
- Active OpenSpec changes have valid `blueprint_impact`.
- Archive blocking reasons are either resolved or explicitly accepted with owner, date, and residual risk.
