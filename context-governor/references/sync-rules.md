# Sync Rules

## Settlement Model
Use surface dual sources with one internal settlement point:
- Repository markdown is editable by humans.
- Hidden JSON state is editable by the skill.
- Every plan, rebuild, resume, or track action must converge into a fresh canonical snapshot before status is reported.

## Document-Priority Fields
These fields are structural and should default to the normalized doc plan:
- `title`
- `phase`
- `depends_on`
- `acceptance_criteria`
- `confidence`

## State-Priority Fields
These fields are operational and should default to the hidden state:
- `status`
- `evidence`
- `blocked_reason`
- `review_reason`
- `current`
- `next`
- `last_updated_at`

## Merge-Safe Cases
Safe merges:
- Doc plan updates task wording while state updates task status
- Doc plan adds acceptance criteria while state adds evidence
- State advances `current_task_id` without changing structure

In safe merges:
- Keep structural fields from the doc plan
- Keep operational fields from state
- Preserve task IDs and ordering from the doc plan

## Conflict and Review Rules
Mark a task as `conflict` when:
- State changes `depends_on`
- State changes `title` or `phase`
- State changes acceptance criteria and the new values contradict the doc plan

Mark a task as `needs_review` when:
- Evidence exists but is too weak to prove completion
- The active task changed but direct successor selection is ambiguous
- Rebuild output is mostly inferred and not yet confirmed

Every conflict should append a short human-readable note to `warnings`.
When a known review reason exists, keep it in `review_reason` and append a short note to `warnings`.

## Completion Evidence Rules
Move a task to `done` only when at least one of these is true:
- The user explicitly confirms completion
- Code changes or generated files clearly satisfy the task
- Commands, tests, or docs provide direct evidence

Otherwise:
- Use `in_progress` while work is underway
- Use `blocked` for dependency or environment blockers
- Use `needs_review` when evidence is partial
- If a `done` request only has missing or placeholder evidence, downgrade it to `needs_review` and persist the reason

## Current Task Selection
If state already defines `current_task_id`, keep it unless the task is `done`.

If no current task is present:
1. Skip all `done` tasks
2. Find the first task whose dependencies are all `done`
3. Prefer `in_progress` over `todo` when multiple candidates qualify

If multiple ready tasks qualify at the same preference level, keep the first one in plan order and add a warning.

## Graph Projection Rules
- Build the graph from the settled snapshot, not from one surface alone.
- Each task ID must appear once.
- Each `depends_on` edge becomes one directed edge.
- Graph status classes are projections only and never replace the snapshot.
- Save Mermaid text as the default rendered form for easy diffs and low token cost.

## Event Log And Resume Boundaries
- `sync-history.ndjson` is append-only and should record one line for every `initialized`, `settle_checklist`, `resume`, `sync_progress`, and `closeout` action.
- `resume-manifest.json` is the resume-only observability output and should be refreshed by `resume_context_governor.py`.
- Settle, sync, and closeout helpers should refresh the settled working state without rewriting `resume-manifest.json`.
- `focus-set.json` should refresh whenever the current task or narrow doc refs change, including resume, checklist settlement, progress sync, and closeout.
