---
name: context-governor
description: Use when a long-running project has an approved PRD, stale checklist, or saved session state and Codex needs to rebuild ordered work, resume from the current task, sync progress with evidence, or avoid repeatedly loading broad project context.
---

# Context Governor

## Overview
Turn approved PRDs or fragmented project docs into an ordered implementation checklist, a dependency graph, and a compact resumable state. Keep repository docs human-readable, keep `.codex/context/` machine-readable, surface a very small active context for the next session, add an ultra-compact recent-change handoff layer, and settle everything into one canonical snapshot before resuming or syncing work.

## When to Use
- An approved PRD needs to become sequenced implementation work with stable task IDs and dependencies.
- Existing notes or checklists drifted and one settled source of truth is missing.
- The project is resuming after a pause and the next session should load the narrowest safe context.
- Progress needs to be synced back into docs and saved state without re-reading the whole project.
- Prompt input is dominated by repeated project context across multiple sessions.

Do not use this for tiny one-session tasks where maintaining plan state costs more than a simple local todo list.

## Core Workflow
1. Write or rewrite `docs/implementation/checklist.md` as the human-readable ordered task list.
2. Settle that checklist into `doc-plan.json` and hidden state.
3. Build or refresh stable task IDs, ordering, dependency edges, and current-task focus.
4. Settle surface edits and hidden state into `latest-snapshot.json`.
5. Render a checklist with stable task-ID anchors, a text graph, an auxiliary focused `resume-pack.md`, and a copy-ready `next-session-prompt.md`.
6. Report the active task, its direct dependencies, the next candidate tasks, and the smallest safe resume prompt.

## Mode Selection
### `plan-from-prd`
Use when an approved PRD or spec should become the first full implementation checklist. Have Codex reason through the PRD, rewrite `docs/implementation/checklist.md` with stable task IDs and dependencies, then settle it into the first hidden state files.

### `rebuild-from-docs`
Use when the project already has notes, README files, partial checklists, or implementation docs but the plan is stale. Reconstruct tasks into `docs/implementation/checklist.md`, label each task as `confirmed`, `inferred`, or `uncertain`, then settle the rebuilt plan into the canonical snapshot.

### `resume-from-state`
Use when returning to a project after a pause. Start from `.codex/context/active-context.md`, obey the context gate, and widen through the current task, its direct dependencies, direct successors, and broader settled context only when needed.

### `track-progress`
Use after a coding or planning session. Update only the tasks supported by explicit user confirmation or concrete evidence, then refresh the hidden state, checklist, graph, snapshot, and resume pack.

## Settlement Rule
Treat repository markdown and hidden JSON state as dual editable surfaces. Use `docs/implementation/checklist.md` as the human-editable settlement source for structural changes, then settle every plan, rebuild, resume, or sync action into one canonical snapshot before reporting status or next steps. Checklist settlement must hard-fail on duplicate task IDs, missing dependency targets, self dependencies, or dependency cycles so malformed structure never pollutes the canonical snapshot.

## Context Discipline
- Default to `.codex/context/active-context.md` before reopening broad project docs.
- Obey the active context gate: stop at the recommended layer, and only widen to the next allowed reads when the stated escalation reasons apply.
- Read `.codex/context/session-delta.md` before broader history when you only need the smallest recent-change handoff from the previous session.
- Read `.codex/context/history-rollup.md` only when recent milestones, blockers, or review state matter.
- Check `.codex/context/budget-report.md` when you want a quick byte or token estimate before widening the resume read set.
- Fall back to `latest-snapshot.json` when the compact active slice is insufficient or structurally ambiguous.
- Pull only referenced PRD or checklist slices unless the narrow context is still insufficient.
- Treat a plain `docs/prd/approved-prd.md` path without an anchor as a full-document fallback, not as a narrow `doc_refs` slice.
- Re-read the full PRD only as a final fallback when the current node cannot be resolved safely.
- In the `prd_required` path, read `latest-snapshot.json` before escalating to the full PRD.

## Completion Guardrails
Move a task to `done` only with explicit user confirmation or verifiable evidence such as code changes, passing checks, or written deliverables. Otherwise prefer `in_progress`, `blocked`, `needs_review`, or `conflict`.

## Outputs
- Repository layer: checklist markdown, progress notes, graph `.mmd`, project-local playbook
- Hidden layer: `doc-plan.json`, `active-context.json`, `active-context.md`, `session-delta.json`, `session-delta.md`, `history-rollup.json`, `history-rollup.md`, `budget-report.json`, `budget-report.md`, `latest-state.json`, `latest-snapshot.json`, `latest-task-graph.json`, `focus-set.json`, `resume-pack.md`, `next-session-prompt.md`, `resume-manifest.json`, `sync-history.ndjson`
- Resume outputs should expose the recommended context level, stop point, escalation reasons, and the next allowed reads so the next session does not widen context by habit.
- `resume-manifest.json` stays resume-only observability written by the resume helper, while `resume-pack.md` stays an auxiliary single-task recap outside the primary widening ladder.
- `sync-history.ndjson` stays append-only so resume, sync, settlement, and closeout leave a durable lifecycle trail.

## References
- `references/workflow.md` for the four operating modes and loading order
- `references/new-project-template.md` for copy-ready new-project bootstrap commands and prompts
- `references/quickstart.md` for the one-minute bootstrap flow in a new or messy project
- `references/quickstart-zh.md` for a Chinese minimal operating guide with copy-ready commands and prompts
- `references/cheatsheet-zh.md` for a one-screen Chinese cheat sheet optimized for repeat project resume flows
- `references/schemas.md` for repository and hidden-state file shapes
- `references/sync-rules.md` for settlement, evidence, and conflict rules

## Deterministic Helpers
- `scripts/init_context_governor.py` bootstraps the recommended docs and `.codex/context/` layout
- `scripts/settle_checklist_context_governor.py` parses `docs/implementation/checklist.md`, rejects malformed dependency structure, rebuilds `doc-plan.json` and `latest-state.json`, and refreshes the settled outputs
- `scripts/resume_context_governor.py` rebuilds the smallest safe startup context, refreshes `active-context`, `session-delta`, `history-rollup`, and `budget-report`, refreshes `focus-set.json` and `next-session-prompt.md`, and emits resume loading stats in `resume-manifest.json`
- `scripts/sync_progress_context_governor.py` records one task status change with evidence, advances the next task when possible, and refreshes settled outputs
- `scripts/closeout_context_governor.py` settles end-of-session outputs into `active-context`, `session-delta`, `history-rollup`, `budget-report`, snapshot, checklist, graph, focus set, and the auxiliary resume pack without rewriting `resume-manifest.json`
- `scripts/quick_validate.py` compiles every helper and runs an end-to-end smoke test across init, checklist settlement, structural linting, resume, progress sync, and closeout
- `docs/implementation/context-governor-playbook.md` is the project-local operator guide generated by the initializer
- `.codex/context/next-session-prompt.md` is the copy-ready prompt that should be refreshed before the next coding session
- `scripts/render_checklist.py` renders checklist markdown with stable `#t-001` style anchors from the settled snapshot
- `scripts/settle_snapshot.py` merges doc-plan JSON and hidden state into `latest-snapshot.json`
- `scripts/render_task_graph.py` renders Mermaid from canonical graph JSON
- `scripts/build_resume_pack.py` creates an auxiliary minimal resume pack for one task

## Reusable Assets
- `assets/checklist-template.md`
- `assets/task-graph-template.json`
- `assets/plan-state-template.json`
- `assets/focus-set-template.json`
- `assets/sample-doc-plan.json`
- `assets/sample-state.json`
- `assets/sample-task-graph.json`

## Entry Prompts
- `Use $context-governor to break this approved PRD into an ordered checklist, dependency graph, and initial snapshot.` -> `plan-from-prd`
- `Use $context-governor to rebuild this project from scattered docs and mark which tasks are confirmed versus inferred.` -> `rebuild-from-docs`
- `Use $context-governor to resume this project from .codex/context/active-context.md with the smallest necessary context.` -> `resume-from-state`
- `Use $context-governor to sync progress from today's work and only mark tasks done where evidence exists.` -> `track-progress`
- Requests that mention PRDs, implementation checklists, dependency graphs, snapshots, sync, or resume flows should route to this skill even when phrased differently.

## Example Commands
```cmd
python scripts\init_context_governor.py --root . --plan-id my-project --plan-title "My Project Plan"
python scripts\quick_validate.py
python scripts\settle_checklist_context_governor.py --root .
python scripts\resume_context_governor.py --root .
python scripts\sync_progress_context_governor.py --root . --task T-014 --status done --evidence shipped-checklist
python scripts\closeout_context_governor.py --root .
python scripts\settle_snapshot.py --doc-plan .codex\context\doc-plan.json --state .codex\context\latest-state.json --output .codex\context\latest-snapshot.json
python scripts\render_checklist.py --doc-plan .codex\context\doc-plan.json --snapshot .codex\context\latest-snapshot.json --output docs\implementation\checklist.md
python scripts\render_task_graph.py --input .codex\context\latest-task-graph.json --output docs\implementation\current-graph.mmd
python scripts\build_resume_pack.py --snapshot .codex\context\latest-snapshot.json --task T-014 --output .codex\context\resume-pack.md
```
