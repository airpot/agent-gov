---
name: openspec-propose
description: Propose a new embedded spec change with all artifacts generated in one step. Use when the user wants to quickly describe what they want to build and get a complete proposal, design, specs, and tasks ready for implementation.
license: MIT
metadata:
  author: agent-gov
  version: "1.0"
  generatedBy: "agent-gov"
---

Propose a new embedded spec change - create the change and generate all artifacts in one step.

I'll create a change with artifacts:
- proposal.md (what & why)
- design.md (how)
- tasks.md (implementation steps)

When ready to implement, use `openspec-apply-change` or ask to implement the change.

---

**Input**: The user's request should include a change name (kebab-case) OR a description of what they want to build.

**Steps**

1. **If no clear input provided, ask what they want to build**

   Ask the user:
   > "What change do you want to work on? Describe what you want to build or fix."

   From their description, derive a kebab-case name (e.g., "add user authentication" → `add-user-auth`).

   **IMPORTANT**: Do NOT proceed without understanding what the user wants to build.

2. **Create the change directory**
   ```bash
   python3 scripts/agent_spec.py new-change "<name>" --summary "<short summary>"
   ```
   This creates a scaffolded change at `openspec/changes/<name>/` with `.agent-spec.json`, `proposal.md`, `design.md`, and `tasks.md`.

3. **Get the artifact status**
   ```bash
   python3 scripts/agent_spec.py status --change "<name>" --json
   ```
   Parse the JSON to get:
   - `applyRequires`: artifact IDs needed before implementation, normally `["proposal", "design", "tasks"]`
   - `artifacts`: artifact IDs, paths, status, and issues
   - `state`: `blocked`, `ready`, or `all_done`

4. **Complete artifacts in sequence until apply-ready**

   Track progress in the active checklist or session notes when the work is non-trivial.

   Complete artifacts in this fixed order: `proposal`, `design`, then `tasks`.

   a. **For each artifact with `status: "missing"` or `status: "draft"`**:
      - Read `.agent/spec.json`, `.agent/workflow.json`, and previously completed artifact files for context.
      - Fill the artifact file using the scaffolded structure.
      - Apply project constraints from `openspec/config.yaml`, but do not copy those rules verbatim into the artifact.
      - Show brief progress: "Created <artifact-id>"

   b. **Continue until all `applyRequires` artifacts are complete**
      - After creating each artifact, re-run `python3 scripts/agent_spec.py status --change "<name>" --json`
      - Check if every artifact ID in `applyRequires` has `status: "done"` in the artifacts array
      - Stop when `state` is `ready` or `all_done`

   c. **If an artifact requires user input** (unclear context):
      - Ask the user to clarify
      - Then continue with creation

5. **Show final status**
   ```bash
   python3 scripts/agent_spec.py status --change "<name>"
   ```

**Output**

After completing all artifacts, summarize:
- Change name and location
- List of artifacts created with brief descriptions
- What's ready: "All artifacts created! Ready for implementation."
- Prompt: "Use `openspec-apply-change` or ask me to implement to start working on the tasks."

**Artifact Creation Guidelines**

- Follow `.agent/spec.json`, `openspec/config.yaml`, and `.agent/workflow.json`
- The embedded schema defines what each artifact should contain - follow it
- Read previously completed artifacts for context before creating the next one
- Use `template` as the structure for your output file - fill in its sections
- **IMPORTANT**: `context` and `rules` are constraints for YOU, not content for the file
  - Do NOT copy `<context>`, `<rules>`, `<project_context>` blocks into the artifact
  - These guide what you write, but should never appear in the output

**Guardrails**
- Create ALL artifacts needed for implementation (as defined by schema's `apply.requires`)
- Always read previously completed artifacts before creating a new one
- If context is critically unclear, ask the user - but prefer making reasonable decisions to keep momentum
- If a change with that name already exists, ask if user wants to continue it or create a new one
- Verify each artifact file exists after writing before proceeding to next
