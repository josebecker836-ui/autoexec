# Workflow Reference

## Table of Contents
- Modes
- Context loading order
- Output expectations
- Recovery rules

## Modes

### `plan-from-prd`
Required inputs:
- Approved PRD or spec
- Optional constraints, milestones, or non-goals

Default reads:
- PRD title, scope, milestones, acceptance criteria
- Existing implementation docs only if they already exist

Expected outputs:
- Ordered `docs/implementation/checklist.md` with stable task IDs
- Rebuilt `doc-plan.json` from the checklist
- Initial `latest-task-graph.json`
- Initial `latest-state.json`
- Settled `latest-snapshot.json`
- Refreshed `active-context.*`
- Refreshed `session-delta.*`
- Refreshed `history-rollup.*`
- Refreshed `budget-report.*`
- Refreshed `focus-set.json`
- Refreshed `resume-pack.md`
- Refreshed `next-session-prompt.md`
- Appended `sync-history.ndjson`

Trigger sync when:
- The task list is approved
- IDs are renumbered or dependencies change

Avoid re-reading the whole PRD when:
- The current planning step only needs one section or milestone

Operational note:
- Codex should reason from the PRD and rewrite `docs/implementation/checklist.md`, then run `settle_checklist_context_governor.py` to settle the hidden state.
- If the checklist has duplicate IDs, unresolved dependencies, self dependencies, or dependency cycles, settlement must fail before any hidden state or snapshot refresh.

### `rebuild-from-docs`
Required inputs:
- Existing docs, notes, READMEs, partial plans, and progress logs
- Optional targeted code inspection if docs are incomplete

Default reads:
- Latest checklist or progress doc
- Existing graph or state files if present
- Only the code or README slices needed to confirm inferred tasks

Expected outputs:
- Rebuilt `docs/implementation/checklist.md` with `confirmed`, `inferred`, or `uncertain` confidence
- Rebuilt `doc-plan.json`
- Rebuilt `latest-task-graph.json`
- Rebuilt `latest-state.json`
- Refreshed `latest-snapshot.json`
- Refreshed `active-context.*`
- Refreshed `session-delta.*`
- Refreshed `history-rollup.*`
- Refreshed `budget-report.*`
- Refreshed `focus-set.json`
- Refreshed `resume-pack.md`
- Refreshed `next-session-prompt.md`
- Appended `sync-history.ndjson`

Trigger sync when:
- New evidence confirms an inferred task
- The rebuilt task order changes

Avoid re-reading the whole PRD when:
- Existing checklist and snapshot already cover the active branch of work

Operational note:
- Treat the checklist as the human settlement layer. After reconstructing or editing it, run `settle_checklist_context_governor.py`.
- Fix structural checklist errors before retrying settlement; do not let malformed task graphs flow into resume state.

### `resume-from-state`
Required inputs:
- `latest-snapshot.json`
- Optional `active-context.md`, `session-delta.md`, `history-rollup.md`, `budget-report.md`, or the auxiliary single-task `resume-pack.md`

Default reads:
- `active-context.md` first
- `session-delta.md` only when the gate says the active slice should widen to the smallest recent-change handoff
- Direct dependencies and direct successors for the active task
- Focused checklist or PRD slices only if referenced by that active slice
- Treat a plain `docs/prd/approved-prd.md` path without an anchor as a full-document fallback, not as a targeted requirement slice
- `history-rollup.md` only if recent milestones, blockers, review state, or recent events beyond the delta matter
- `latest-snapshot.json` only if the active slice is insufficient or ambiguous
- In the `prd_required` path, read `latest-snapshot.json` before escalating to the full PRD
- `resume-pack.md` only as an auxiliary single-task recap outside the default widening ladder

Expected outputs:
- Current task recommendation
- Refreshed `focus-set.json`
- Refreshed `active-context.json` and `active-context.md`
- Refreshed `session-delta.json` and `session-delta.md`
- Refreshed `history-rollup.json` and `history-rollup.md`
- Refreshed `budget-report.json` and `budget-report.md`
- Minimal resume pack
- Refreshed `next-session-prompt.md`
- Explicit list of the smallest required context files
- Recommended context level, stop point, escalation reasons, and next allowed reads
- `resume-manifest.json` with loading statistics and PRD fallback status
- Appended `sync-history.ndjson`

Trigger sync when:
- The active task changes
- A blocker or completion state changes

Do not re-read the entire PRD unless:
- The snapshot is missing
- The current task references a requirement slice that cannot be found after checking `latest-snapshot.json`
- The active slice has neither targeted doc refs nor acceptance criteria, so resume must escalate to `prd_required`
- Structural conflicts force a rebuild

### `track-progress`
Required inputs:
- Recent edits, docs changes, or direct user confirmation
- Settled task structure and hidden state
- Task ID being updated
- New status and optional evidence

Default reads:
- `doc-plan.json`
- `latest-state.json`
- Evidence attached to completed or changed tasks
- Only the checklist and graph sections touched by new evidence

Expected outputs:
- Updated `latest-state.json`
- Updated checklist markdown with stable `### T-001` anchors
- Updated task statuses
- Updated graph node states
- Updated `latest-task-graph.json`
- Updated `docs/implementation/current-graph.mmd`
- Updated `active-context.*`
- Updated `session-delta.*`
- Updated `history-rollup.*`
- Updated `budget-report.*`
- New `latest-snapshot.json`
- Refreshed `focus-set.json`
- Refreshed `resume-pack.md`
- Refreshed `next-session-prompt.md`
- Appended `sync-history.ndjson`

Trigger sync when:
- Evidence changes task status
- The active task or next tasks change

Avoid re-reading the whole PRD when:
- Only operational status changed and no structural requirement changed

## Context Loading Order
Load the smallest useful slice first:
1. `active-context.md`
2. Follow the `Context Gate` section and stop at the recommended layer unless an allowed escalation reason applies
3. Direct dependencies and direct successors
4. Focused PRD or checklist slices referenced by that active slice
5. `session-delta.md` only if it is the next allowed read and you need the most recent handoff before broader history
6. `history-rollup.md` only if the gate or current task state says broader recent history matters
7. `latest-snapshot.json` only if the gate says the active slice is structurally insufficient
8. Full PRD only as a fallback after the snapshot still cannot resolve the requirement

A plain `docs/prd/approved-prd.md` reference without an anchor belongs to step 8, not step 4.

## Output Expectations
- Keep the canonical snapshot machine-readable and deterministic.
- Keep `active-context.*` small enough to drive the next session without replaying the entire snapshot.
- Keep the gate fields actionable: they should say where to stop, why to widen, and which file is the next allowed escalation step.
- Keep `session-delta.*` smaller than `history-rollup.*` and focused on the latest meaningful handoff, not a replay of recent history.
- Keep `history-rollup.*` compact enough to summarize milestones and open review state without replaying full history logs.
- Keep `budget-report.*` explicit about the byte and approximate-token gap between the active path and the snapshot-heavy fallback path.
- Keep `budget-report.*` explicit about whether the active slice is currently sufficient and what the recommended read-now path costs.
- Keep `next-session-prompt.md` self-consistent: a file already listed under the current `Read only these files now` set must not also be described as forbidden by the escalation policy.
- Keep `docs/implementation/checklist.md` human-editable and structurally complete enough to rebuild hidden state.
- Keep the graph diffable in Mermaid or Graphviz text.
- Keep the resume pack short enough to paste into the next coding session without restating the whole project.
- Keep `resume-manifest.json` explicit about what to read next and whether full PRD fallback was needed.
- Keep `sync-history.ndjson` append-only so every initializer, checklist settlement, resume, progress sync, and closeout leaves a durable event trail.
- Report what is confirmed versus inferred when rebuilding from fragmented docs.

## Recovery Rules
- If snapshot and docs disagree on structural fields, rewrite the checklist first, then settle it and mark conflicts instead of guessing.
- If checklist settlement reports duplicate IDs, missing dependency targets, self dependencies, or dependency cycles, fix the checklist before regenerating hidden state.
- If no current task is set, pick the first non-`done` task whose dependencies are all `done`.
- If a completed task has exactly one ready direct successor, prefer that successor as the next current task before falling back to the general selection rule.
- If all tasks are `done`, report completion and preserve the final snapshot rather than rebuilding.
- If evidence is weak or ambiguous, downgrade to `needs_review` instead of `done`.
