# Repo Protocol Layer

Repo-visible project docs complement `.codex/context/`. They let later sessions resume from durable files instead of reconstructing intent from chat history alone.

## Durable Project Files

### `Prompt.md`

Use as the stable contract for:

- goals and non-goals
- hard constraints
- concrete deliverables
- explicit "done when" criteria

If there is no `Prompt.md`, use the approved PRD or spec that plays the same role.

### `Plan.md`

Use as the ordered execution map for:

- milestones and dependencies
- acceptance criteria per milestone
- verification commands
- stop-and-fix rules
- architectural and sequencing decisions

If `Plan.md` is missing or too vague to drive execution, repair or create it before broad implementation continues.

### `Implement.md`

Use as the execution handbook for:

- what counts as the source of truth during implementation
- when verification must run
- how tightly to bound diffs
- how and when to sync docs

If `Implement.md` is missing, follow the skill's own execution rules and repo conventions.

### `Documentation.md`

Use as the shared status log for:

- current milestone and next ready task
- recent decisions and why they were made
- run or demo commands
- known issues, follow-ups, and blockers

If `Documentation.md` is missing, create or refresh the nearest equivalent progress doc once work reaches a stable checkpoint.

## Loading Order

When these files exist, reload them in this order:

1. `.codex/context/active-context.md`
2. `.codex/context/latest-snapshot.json`
3. `Documentation.md`
4. `Plan.md`
5. `Prompt.md` or approved PRD/spec
6. `Implement.md`
7. only the flow or spec slices needed for the current task

This order keeps resumes narrow while still restoring scope, order, and process discipline.

## Missing-File Fallbacks

- No `Prompt.md`: use the approved PRD, spec, or design doc that defines scope and done-when.
- No `Plan.md`: create or repair a milestone plan before continuing broad execution.
- No `Implement.md`: use the skill's loop plus repo conventions as the working handbook.
- No `Documentation.md`: create or refresh a progress doc after the current verified slice.
- No durable docs at all: fall back to PRD, flowcharts, and `.codex/context/`, then sync stable repo docs as soon as practical.

## Conflict Handling

Use this resolution order:

1. explicit user instruction
2. scope and acceptance from `Prompt.md` or approved PRD
3. process rules from `Implement.md`
4. ordering and current status from `Plan.md` and `Documentation.md`
5. machine-readable resume state from `.codex/context/`
6. current code and fresh verification evidence as the tie-breaker for stale records

If docs disagree with verified code, update the stale docs instead of letting multiple truths persist.

## Completion Discipline

Treat project completion as a protocol outcome, not a feeling. Before calling work done:

- satisfy the deliverables and done-when rules from `Prompt.md` or the PRD
- satisfy milestone acceptance and verification from `Plan.md`
- follow closeout behavior from `Implement.md` if present
- update `Documentation.md` and `.codex/context/` to the final status

The repo protocol layer exists to make long-running delivery durable, reviewable, and resumable.
