---
name: autonomous-prd-delivery
description: Use when a repository has PRD, spec, or durable project docs such as Prompt.md, Plan.md, Implement.md, or Documentation.md plus flowcharts, or the user asks for autonomous end-to-end delivery without milestone check-ins and Codex should keep shipping from repo state plus .codex/context/ until true blockers.
---

# Autonomous PRD Delivery

## Overview

Turn repo-local PRDs, durable project docs, and flowcharts into a continuous delivery loop. Keep implementing, verifying, syncing repo-visible status plus `.codex/context/`, and moving to the next ready task until all required work is complete or a real blocker forces a stop.

**Core principle:** A milestone, summary, or finished phase is not a stop signal. Only a real blocker is.

**Memory model:** Treat repo project docs plus `.codex/context/` as dual-track memory. Repo docs explain intent and shared status. `.codex/context/` preserves machine-friendly resume state.

**Announce at start:** "I'm using the autonomous-prd-delivery skill to keep shipping from the repo's PRD, project docs, and flowcharts until the required work is done."

## Entry Rule

Enter this skill when either of these is true:

- The repo has both written requirements and flow artifacts.
- The repo has durable project docs such as `Prompt.md`, `Plan.md`, `Implement.md`, or `Documentation.md` that define scope, execution order, or current status.
- The user explicitly asks for autonomous execution, no checkpoint pauses, or asks in Chinese to continue until done or not interrupt, and the missing artifact can be recovered from repo context.

If `.codex/context/active-context.md` exists, treat it as the default resume surface instead of starting from scratch.

If repo protocol docs exist, load them before broad rediscovery.

## Required Sub-Skills

- **REQUIRED:** Use `context-governor` to bootstrap or refresh `.codex/context/` before broad execution and after meaningful progress.
- **REQUIRED:** Use `test-driven-development` for each feature or bugfix task you implement.
- **REQUIRED:** Use `verification-before-completion` before claiming a task, milestone, or project is done.
- Use `writing-plans` when the repo has requirements but no usable ordered checklist yet.
- Use `systematic-debugging` when repeated failures indicate a real bug, broken assumption, or environmental issue.

## Repo Protocol Layer

When these docs exist, use them as durable repo-visible control files:

- `Prompt.md` freezes goal, non-goals, constraints, deliverables, and done-when criteria.
- `Plan.md` defines milestones, dependencies, acceptance checks, verification commands, stop-and-fix rules, and major decisions.
- `Implement.md` is the execution handbook: how to work, when to verify, how to bound diffs, and how to keep docs synced.
- `Documentation.md` records current status, decisions, run or demo commands, known issues, and next ready work.

These docs may live at repo root or nearby docs folders. Prefer the closest authoritative copy instead of merging multiple competing variants.

## Priority And Conflict Rule

Resolve authority in this order:

1. explicit user instructions
2. `Prompt.md` or approved PRD/spec for scope and acceptance
3. `Implement.md` for execution discipline
4. `Plan.md` and `Documentation.md` for ordered work and current status
5. `.codex/context/active-context.md`
6. `.codex/context/latest-snapshot.json`
7. flowchart slices and other progress docs

If sources conflict:

- preserve user direction over everything
- preserve product scope from `Prompt.md` or the approved PRD over stale status docs
- preserve fresh verification evidence and current code reality over stale documentation
- update stale docs immediately instead of following them blindly

## Loading Order

Load the smallest safe context in this order:

1. explicit user request and latest branch or worktree state
2. `.codex/context/active-context.md`
3. `.codex/context/latest-snapshot.json`
4. `Documentation.md`
5. `Plan.md`
6. `Prompt.md` or approved PRD/spec
7. `Implement.md`
8. only the flowchart and spec slices required for the current task
9. broader repo context only if still needed

Favor narrow reload over whole-repo rereads.

## Execution Loop

1. Detect `Prompt.md`, `Plan.md`, `Implement.md`, `Documentation.md`, qualifying PRD/spec files, and flowchart artifacts.
2. Load the smallest safe context using the loading order above.
3. Ensure there is a usable ordered task graph. If `Plan.md` is missing or not actionable, build or repair it with `writing-plans` and settle it with `context-governor`.
4. Select the smallest ready task that advances the required work and stays inside the current milestone boundary.
5. Implement that task with TDD.
6. Run fresh task verification plus any milestone verification required by `Plan.md` or repo scripts.
7. Sync repo docs and `.codex/context/` with completed work, verification evidence, assumptions, blockers, and next ready work.
8. Select the next ready task immediately.
9. Repeat until every required task is done, explicitly deferred, or truly blocked.

Never stop after verification or doc sync just to ask permission for the next obvious step.

## Anti-Interruption Rule

Do not pause because:

- a phase finished
- a summary would be helpful
- the next task looks obvious
- the user has not typed "continue"
- a low-risk detail is unspecified
- docs were just synced
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
- The next task is already clear from the PRD, flowchart, repo protocol docs, or saved state.
- A low-risk detail is missing but a reasonable assumption keeps the work moving.
- You want to summarize progress.
- You are waiting for the user to authorize the obvious next task.
- A docs sync, progress log update, or closeout check is the normal next step.

## Low-Risk Assumptions

Make reasonable assumptions for low-risk details and keep moving. Record them in repo docs plus `.codex/context/` so future sessions can see what was assumed.

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
3. `Documentation.md`
4. `Plan.md`
5. the current task's direct dependencies and successors
6. `Prompt.md`, the approved PRD/spec, and relevant flow slices only if the saved state is insufficient

If repo docs and `.codex/context/` disagree, verify against code and tests, then repair whichever record is stale.

## Milestone Verification Rule

Before calling a milestone complete:

- run milestone-specific commands from `Plan.md` if present
- otherwise run the strongest local verification chain available, such as tests, lint, typecheck, build, and smoke checks
- fix failures before advancing
- record the exact command set and result in repo docs plus `.codex/context/`

A milestone is not complete because the code "looks done."

## Diff Boundary Rule

Keep each pass inside the current milestone boundary:

- touch only files required by the active task, verification, or necessary local cleanup
- do not opportunistically refactor unrelated modules just because you're nearby
- if you discover useful follow-up work outside the current slice, record it in `Plan.md` or `Documentation.md` instead of silently expanding scope
- widen the diff only when required to satisfy the approved requirement or unblock failing verification

## Documentation Sync Rule

After each meaningful task, sync both tracks of memory:

- repo-visible docs such as `Documentation.md`, `Plan.md`, or the nearest progress doc
- `.codex/context/active-context.md` and snapshot state

At minimum record:

- current milestone and task
- completed and next ready work
- verification evidence
- assumptions or decisions
- blockers or known issues

Do not leave repo docs claiming "in progress" after code and tests already moved on.

## State Update Rule

After each meaningful task, refresh project state so the next session can continue without rediscovering context. At minimum, keep `.codex/context/` aligned with:

- current milestone
- current task
- completed tasks
- blocked tasks
- next ready tasks
- low-risk assumptions
- verification evidence
- latest blocker summary
- last completed closeout step

## Done-When Rule

Use the repo's explicit "done when" criteria when available. Otherwise require all of the following:

- all required PRD or `Prompt.md` deliverables implemented or explicitly deferred by the user
- acceptance criteria from `Plan.md` satisfied
- the latest verification chain passes
- repo docs and `.codex/context/` synced to the final state
- requested git closeout completed or its blocker stated explicitly

## Closeout Rule

When the final required task is implemented, do not stop at "the code is done." Finish the closeout loop:

1. run final smoke or regression verification
2. sync `.codex/context/` and repo progress docs
3. ensure `Documentation.md` or the equivalent progress doc explains final status, run or demo commands, and known follow-ups
4. if the user requested version-control delivery, complete commit and push steps too
5. only then report completion or the remaining blocker

## Completion Rule

Do not claim the project is done because a milestone looks complete. Completion requires:

- all required tasks completed or explicitly deferred by the user
- fresh verification evidence for the implemented work
- final repo-visible docs and saved state updated to reflect the final status
- requested closeout actions such as doc sync, commit, or push completed, or their blocker stated explicitly

If the environment prevents a required verification or git action, state that limitation explicitly instead of pretending completion.

## References

- `references/trigger-and-blocking-rules.md`
- `references/repo-protocol-layer.md`
