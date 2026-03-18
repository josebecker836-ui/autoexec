---
name: autonomous-prd-delivery
description: Use when a repository has PRD or spec documents plus flowcharts, or the user asks for autonomous end-to-end delivery, asks in English or Chinese to continue until all required work is done or not to interrupt, and Codex should keep shipping from .codex/context/ instead of stopping at milestone check-ins.
---

# Autonomous PRD Delivery

## Overview

Turn repo-local PRDs, specs, and flowcharts into a continuous delivery loop. Keep implementing, verifying, syncing state, and moving to the next ready task until all required work is complete or a real blocker forces a stop.

**Core principle:** A milestone, summary, or finished phase is not a stop signal. Only a real blocker is.

**Announce at start:** "I'm using the autonomous-prd-delivery skill to keep shipping from the repo's PRD and flowcharts until the required work is done."

## Entry Rule

Enter this skill when either of these is true:

- The repo has both written product requirements and flow artifacts.
- The user explicitly asks for autonomous execution, no checkpoint pauses, or asks in Chinese to continue until done or not interrupt, and the missing artifact can be found from repo context.

If `.codex/context/active-context.md` exists, treat it as the default resume surface instead of starting from scratch.

## Required Sub-Skills

- **REQUIRED:** Use `context-governor` to bootstrap or refresh `.codex/context/` before broad execution and after meaningful progress.
- **REQUIRED:** Use `test-driven-development` for each feature or bugfix task you implement.
- **REQUIRED:** Use `verification-before-completion` before claiming a task, milestone, or project is done.
- Use `writing-plans` when the repo has requirements but no usable ordered checklist yet.
- Use `systematic-debugging` when repeated failures indicate a real bug, broken assumption, or environmental issue.

## Execution Loop

1. Detect qualifying PRD/spec files and flowchart artifacts.
2. Read the smallest safe context first:
   - `.codex/context/active-context.md`
   - then `.codex/context/latest-snapshot.json` if needed
   - then only the PRD/spec and flow slices required for the current task
3. Ensure there is a usable ordered task graph. If not, build one with `writing-plans` and settle it with `context-governor`.
4. Select the smallest ready task that advances the required work.
5. Implement that task with TDD.
6. Run fresh verification for that task.
7. Sync `.codex/context/` with completed work, verification evidence, assumptions, and blockers.
8. Select the next ready task immediately.
9. Repeat until every required task is done, explicitly deferred, or truly blocked.

Never stop after step 6 or step 7 just to give a checkpoint update.

## Anti-Interruption Rule

Do not pause because:

- a phase finished
- a summary would be helpful
- the next task looks obvious
- the user has not typed "continue"
- a low-risk detail is unspecified
- you want permission for the default next implementation step

Progress updates are allowed only if they are non-blocking and immediately followed by more work in the same session.

## Forbidden Pause Patterns

Do not emit messages like:

- "Phase 1 is complete. Do you want me to continue?"
- "I finished this part. Should I proceed?"
- "I wrote the plan. Want me to implement it now?"
- "Checkpoint: review this before I touch the next task."

Replace them with:

- "Task T-014 is verified; I'm syncing state and moving to T-015 next."
- "The current slice is complete. I'm starting the next ready task now."

## Communication Rule

Short progress updates are allowed, but they must never become permission checkpoints.

Good progress update:

- "Implementing task T-014 now; after verification I'll move directly to the next ready task."

Bad progress update:

- "Phase 1 is complete. Do you want me to continue?"
- "I finished this part. Should I proceed to the next step?"

If you send a progress update, continue working in the same session unless the stop conditions below are met.

## Continue By Default

Do continue when:

- A task or phase just finished.
- The next task is already clear from the PRD, flowchart, or saved state.
- A low-risk detail is missing but a reasonable assumption keeps the work moving.
- You want to summarize progress.
- You are waiting for the user to authorize the obvious next task.
- A docs sync, progress log update, or closeout check is the normal next step.

## Low-Risk Assumptions

Make reasonable assumptions for low-risk details and keep moving. Record them in `.codex/context/` so future sessions can see what was assumed.

Typical low-risk assumptions:

- naming details
- minor copy or labels
- local component boundaries
- non-critical default values
- task ordering within the same dependency level
- straightforward test data

## Stop Only For Real Blockers

Pause and ask the user only when one of these is true:

- Core requirements are missing or contradictory.
- A high-risk decision is unresolved and cannot be safely inferred.
- Required credentials, permissions, infrastructure, or external services are unavailable.
- Verification keeps failing after appropriate debugging, and continuing would likely amplify the wrong solution.

When you stop, report:

- the exact blocker
- the current task or file
- what you already tried
- the smallest decision or input needed to continue

## High-Risk Decision Rule

Do not silently assume high-risk items such as:

- primary data models and irreversible migrations
- authentication or authorization boundaries
- payment, billing, or compliance behavior
- destructive data handling
- public API contracts that affect other systems
- production security posture

If the unresolved question changes architecture, access control, data integrity, billing, or external contracts, stop and escalate.

## Resume Rule

On a later session, do not restart from the top unless the state is missing or corrupted. Resume in this order:

1. `.codex/context/active-context.md`
2. `.codex/context/latest-snapshot.json`
3. the current task's direct dependencies and successors
4. the underlying PRD and flowchart slices only if the saved state is insufficient

Favor narrow reloading over re-reading the whole repo.

## State Update Rule

After each meaningful task, refresh the project state so the next session can continue without rediscovering context. At minimum, keep `.codex/context/` aligned with:

- current task
- completed tasks
- blocked tasks
- next ready tasks
- low-risk assumptions
- verification evidence
- latest blocker summary
- last completed closeout step

## Closeout Rule

When the final required task is implemented, do not stop at "the code is done." Finish the closeout loop:

1. run final smoke or regression verification
2. sync `.codex/context/` and repo progress docs
3. if the user requested version-control delivery, complete commit and push steps too
4. only then report completion or the remaining blocker

## Completion Rule

Do not claim the project is done because a milestone looks complete. Completion requires:

- all required PRD tasks completed or explicitly deferred by the user
- fresh verification evidence for the implemented work
- saved state updated to reflect the final status
- requested closeout actions such as doc sync, commit, or push completed, or their blocker stated explicitly

If the environment prevents a required verification or git action, state that limitation explicitly instead of pretending completion.
