---
name: openspec-archive-change
description: Archive a completed embedded spec change. Use when the user wants to finalize and archive a change after implementation is complete.
license: MIT
metadata:
  author: agent-gov
  version: "1.0"
  generatedBy: "agent-gov"
---

Archive a completed embedded spec change.

**Input**: Optionally specify a change name. If omitted, check if it can be inferred from conversation context. If vague or ambiguous you MUST prompt for available changes.

**Steps**

1. **If no change name provided, prompt for selection**

   Run `python3 scripts/agent_spec.py list --json` to get available changes. Ask the user to select when ambiguous.

   Show only active changes (not already archived).
   Include the schema used for each change if available.

   **IMPORTANT**: Do NOT guess or auto-select a change. Always let the user choose.

2. **Check artifact completion status**

   Run `python3 scripts/agent_spec.py status --change "<name>" --json` to check artifact completion.

   Parse the JSON to understand:
   - `schemaName`: The workflow being used
   - `artifacts`: List of artifacts with their status (`missing`, `draft`, or `done`)
   - `state`: `blocked`, `ready`, or `all_done`

   **If any artifacts are not `done`:**
   - Display warning listing incomplete artifacts
   - Ask the user to confirm whether to proceed
   - Proceed if user confirms

3. **Check task completion status**

   Read the tasks file (typically `tasks.md`) to check for incomplete tasks.

   Count tasks marked with `- [ ]` (incomplete) vs `- [x]` (complete).

   **If incomplete tasks found:**
   - Display warning showing count of incomplete tasks
   - Ask the user to confirm whether to proceed
   - Proceed if user confirms

   **If no checkbox tasks exist:** Treat the change as incomplete, ask the user to confirm whether to proceed, and use `--force` only after explicit confirmation.

4. **Assess delta spec sync state**

   Check for delta specs at `openspec/changes/<name>/specs/`. If none exist, proceed without sync prompt.

   **If delta specs exist:**
   - Compare each delta spec with its corresponding main spec at `openspec/specs/<capability>/spec.md`
   - Determine what changes would be applied (adds, modifications, removals, renames)
   - Show a combined summary before prompting

   **Prompt options:**
   - If changes needed: "Sync now (recommended)", "Archive without syncing"
   - If already synced: "Archive now", "Sync anyway", "Cancel"

   If user chooses sync, update the corresponding files under `openspec/specs/` directly and record the decision in the active session. Proceed to archive after the sync decision.

5. **Perform the archive**

   Use the embedded spec tool:
   ```bash
   python3 scripts/agent_spec.py archive "<name>"
   ```
   Add `--force` only when the user explicitly accepts incomplete tasks or artifact warnings.

6. **Display summary**

   Show archive completion summary including:
   - Change name
   - Schema that was used
   - Archive location
   - Whether specs were synced (if applicable)
   - Note about any warnings (incomplete artifacts/tasks)

**Output On Success**

```
## Archive Complete

**Change:** <change-name>
**Schema:** <schema-name>
**Archived to:** openspec/changes/archive/YYYY-MM-DD-<name>/
**Specs:** synced to main specs (or "No delta specs" or "Sync skipped")

All artifacts complete. All tasks complete.
```

**Guardrails**
- Always prompt for change selection if not provided
- Use `agent_spec.py status --json` for completion checking
- Don't block archive on warnings - just inform and confirm
- Preserve `.agent-spec.json` when moving to archive (it moves with the directory)
- Show clear summary of what happened
- If sync is requested, perform a bounded direct update to `openspec/specs/` and record evidence
- If delta specs exist, always run the sync assessment and show the combined summary before prompting
