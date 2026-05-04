---
name: openspec-apply-change
description: Implement tasks from an embedded spec change. Use when the user wants to start implementing, continue implementation, or work through tasks.
license: MIT
metadata:
  author: agent-gov
  version: "1.0"
  generatedBy: "agent-gov"
---

Implement tasks from an embedded spec change.

**Input**: Optionally specify a change name. If omitted, check if it can be inferred from conversation context. If vague or ambiguous you MUST prompt for available changes.

**Steps**

1. **Select the change**

   If a name is provided, use it. Otherwise:
   - Infer from conversation context if the user mentioned a change
   - Auto-select if only one active change exists
   - If ambiguous, run `python3 scripts/agent_spec.py list --json` to get available changes and ask the user to select

   Always announce: "Using change: <name>" and say that the user can name a different change to override.

2. **Check status to understand the schema**
   ```bash
   python3 scripts/agent_spec.py status --change "<name>" --json
   ```
   Parse the JSON to understand:
   - `schemaName`: The workflow being used, normally `agent-gov-embedded`
   - Which artifact contains the tasks, normally `tasks`
   - Artifact status values: `missing`, `draft`, or `done`

3. **Get apply context**

   Use the status JSON plus `.agent/spec.json` and `.agent/workflow.json`.

   The status JSON returns:
   - `contextFiles`: artifact ID -> array of concrete file paths
   - `tasks`: complete, incomplete, and total counts
   - `state`: `blocked`, `ready`, or `all_done`

   **Handle states:**
   - If `state: "blocked"`: show the missing or draft artifacts and complete them before implementation
   - If `state: "all_done"`: report that implementation tasks are complete and suggest archive
   - If `state: "ready"`: proceed to implementation

4. **Read context files**

   Read every file path listed under `contextFiles` from the status JSON.
   The files depend on the schema being used:
   - Embedded agent-gov spec: proposal, design, tasks, and any files under `specs/`

5. **Show current progress**

   Display:
   - Schema being used
   - Progress: "N/M tasks complete"
   - Remaining tasks overview
   - Workflow gates from `.agent/workflow.json`

6. **Implement tasks (loop until done or blocked)**

   For each pending task:
   - Show which task is being worked on
   - Make the code changes required
   - Keep changes minimal and focused
   - Mark task complete in the tasks file: `- [ ]` → `- [x]`
   - Continue to next task

   **Pause if:**
   - Task is unclear → ask for clarification
   - Implementation reveals a design issue → suggest updating artifacts
   - Error or blocker encountered → report and wait for guidance
   - User interrupts

7. **On completion or pause, show status**

   Display:
   - Tasks completed this session
   - Overall progress: "N/M tasks complete"
   - If all done: suggest archive
   - If paused: explain why and wait for guidance

**Output During Implementation**

```
## Implementing: <change-name> (schema: <schema-name>)

Working on task 3/7: <task description>
[...implementation happening...]
[done] Task complete

Working on task 4/7: <task description>
[...implementation happening...]
[done] Task complete
```

**Output On Completion**

```
## Implementation Complete

**Change:** <change-name>
**Schema:** <schema-name>
**Progress:** 7/7 tasks complete

### Completed This Session
- [x] Task 1
- [x] Task 2
...

All tasks complete! Ready to archive this change.
```

**Output On Pause (Issue Encountered)**

```
## Implementation Paused

**Change:** <change-name>
**Schema:** <schema-name>
**Progress:** 4/7 tasks complete

### Issue Encountered
<description of the issue>

**Options:**
1. <option 1>
2. <option 2>
3. Other approach

What would you like to do?
```

**Guardrails**
- Keep going through tasks until done or blocked
- Always read context files before starting (from the status JSON)
- If task is ambiguous, pause and ask before implementing
- If implementation reveals issues, pause and suggest artifact updates
- Keep code changes minimal and scoped to each task
- Update task checkbox immediately after completing each task
- Pause on errors, blockers, or unclear requirements - don't guess
- Use `contextFiles` from `agent_spec.py status --json`; don't assume specific file names

**Fluid Workflow Integration**

This skill supports the "actions on a change" model:

- **Can be invoked anytime**: Before all artifacts are done (if tasks exist), after partial implementation, interleaved with other actions
- **Allows artifact updates**: If implementation reveals design issues, suggest updating artifacts - not phase-locked, work fluidly
