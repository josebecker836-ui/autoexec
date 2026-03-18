# Quickstart

## When to Use
Use this flow when a project does not yet have `.codex/context/` state, when the docs folders are inconsistent, or when you want a clean first-run layout for `context-governor`.

Chinese quick reference:
- `references/quickstart-zh.md` for a copy-ready operating guide focused on minimal prompt input across repeated sessions
- `references/new-project-template.md` for a first-time project bootstrap template with copy-ready commands and prompts

## One-Minute Bootstrap
1. Run the initializer from any project root:

```cmd
python C:\Users\WeiZhaoyuan\.codex\skills\context-governor\scripts\init_context_governor.py --root .
```

2. Put the approved PRD in `docs/prd/approved-prd.md`.
3. Ask Codex to turn the PRD into `docs/implementation/checklist.md`:

```text
Use $context-governor to break docs/prd/approved-prd.md into an ordered checklist, dependency graph, and initial snapshot.
```

4. After the checklist is written or revised, settle it:

```cmd
python C:\Users\WeiZhaoyuan\.codex\skills\context-governor\scripts\settle_checklist_context_governor.py --root .
```

If settlement fails, fix the checklist structure first. Duplicate task IDs, missing dependency targets, self dependencies, and dependency cycles are blocked before hidden state is refreshed.

## Generated Starter Files
Repository layer:
- `docs/prd/approved-prd.md`
- `docs/implementation/checklist.md`
- `docs/implementation/current-graph.mmd`
- `docs/implementation/context-governor-playbook.md`
- `docs/implementation/progress.md` (optional bootstrap and milestone log; not a live resume source)

Hidden layer:
- `.codex/context/active-context.json`
- `.codex/context/active-context.md`
- `.codex/context/budget-report.json`
- `.codex/context/budget-report.md`
- `.codex/context/doc-plan.json`
- `.codex/context/session-delta.json`
- `.codex/context/session-delta.md`
- `.codex/context/history-rollup.json`
- `.codex/context/history-rollup.md`
- `.codex/context/latest-state.json`
- `.codex/context/latest-snapshot.json`
- `.codex/context/latest-task-graph.json`
- `.codex/context/focus-set.json`
- `.codex/context/resume-pack.md`
- `.codex/context/next-session-prompt.md`
- `.codex/context/sync-history.ndjson`

## Useful Options
- `--plan-id project-plan-id` to force a stable plan ID
- `--plan-title "Project Plan"` to seed human-readable docs
- `--overwrite` to replace generated starter files

## One-Command Validation
When you want to verify the helper scripts still work together, run:

```cmd
python C:\Users\WeiZhaoyuan\.codex\skills\context-governor\scripts\quick_validate.py
```

This checks:
- Python compilation for every script in `scripts/`
- reference-contract consistency for key docs
- initializer output generation
- checklist settlement back into hidden state
- structural lint failures for duplicate IDs, missing dependency targets, self dependencies, and dependency cycles
- resume manifest refresh
- next-session prompt policy alignment so files in the current read-now set are never simultaneously forbidden
- successor advancement during progress sync
- weak-evidence downgrade to `needs_review` with a persisted review reason
- ambiguity warnings when multiple ready tasks qualify
- final closeout refresh

## Session Startup
Before reading broad docs in a later session, run:

```cmd
python C:\Users\WeiZhaoyuan\.codex\skills\context-governor\scripts\resume_context_governor.py --root .
```

This refreshes:
- `.codex/context/focus-set.json`
- `.codex/context/active-context.json`
- `.codex/context/active-context.md`
- `.codex/context/session-delta.json`
- `.codex/context/session-delta.md`
- `.codex/context/history-rollup.json`
- `.codex/context/history-rollup.md`
- `.codex/context/budget-report.json`
- `.codex/context/budget-report.md`
- `.codex/context/resume-pack.md`
- `.codex/context/next-session-prompt.md`
- `.codex/context/resume-manifest.json`

This also appends:
- `.codex/context/sync-history.ndjson`

Use `resume-manifest.json` to see:
- which task to resume
- which direct dependencies and successors were loaded
- which files should be read first
- which context level is currently recommended
- where the current session should stop reading by default
- which file is the next allowed escalation step, usually `session-delta.md` before broader history
- which fallback files expand context if the active slice is insufficient
- whether full PRD fallback was triggered because the checklist slice was unavailable

Use `budget-report.md` to see:
- the default active-context-first read-set cost
- whether the active slice is currently sufficient
- the recommended read-now path for this session
- the heavier fallback path cost if you widen context
- the approximate bytes and tokens saved when the active slice is enough

## Progress Sync
When one task changes status and you want the checklist and graph marked immediately, run:

```cmd
python C:\Users\WeiZhaoyuan\.codex\skills\context-governor\scripts\sync_progress_context_governor.py --root . --task T-001 --status done --evidence shipped-checklist
```

This updates:
- `.codex/context/active-context.json`
- `.codex/context/active-context.md`
- `.codex/context/session-delta.json`
- `.codex/context/session-delta.md`
- `.codex/context/history-rollup.json`
- `.codex/context/history-rollup.md`
- `.codex/context/budget-report.json`
- `.codex/context/budget-report.md`
- `.codex/context/latest-state.json`
- `.codex/context/latest-snapshot.json`
- `.codex/context/latest-task-graph.json`
- `.codex/context/focus-set.json`
- `.codex/context/resume-pack.md`
- `.codex/context/next-session-prompt.md`
- `docs/implementation/checklist.md`
- `docs/implementation/current-graph.mmd`

This also appends:
- `.codex/context/sync-history.ndjson`

If the completed task has exactly one ready direct successor, that successor becomes current automatically. Otherwise the canonical selection rules choose the next task.
If `--status done` only has missing or placeholder evidence, the task is downgraded to `needs_review`, `Review Reason` is written into the settled outputs, and the task stays available for the next session.

## Structural Rebuild
When you manually rewrite `docs/implementation/checklist.md` from a PRD or scattered docs, settle the structural edits back into hidden state with:

```cmd
python C:\Users\WeiZhaoyuan\.codex\skills\context-governor\scripts\settle_checklist_context_governor.py --root .
```

This rebuilds:
- `.codex/context/active-context.json`
- `.codex/context/active-context.md`
- `.codex/context/doc-plan.json`
- `.codex/context/session-delta.json`
- `.codex/context/session-delta.md`
- `.codex/context/history-rollup.json`
- `.codex/context/history-rollup.md`
- `.codex/context/budget-report.json`
- `.codex/context/budget-report.md`
- `.codex/context/latest-state.json`
- `.codex/context/latest-snapshot.json`
- `.codex/context/latest-task-graph.json`
- `.codex/context/focus-set.json`
- `.codex/context/resume-pack.md`
- `.codex/context/next-session-prompt.md`
- `docs/implementation/checklist.md`
- `docs/implementation/current-graph.mmd`

This also appends:
- `.codex/context/sync-history.ndjson`

If `settle_checklist_context_governor.py` stops with a structure error, fix the checklist instead of bypassing the failure. The snapshot should only be regenerated from a structurally valid plan.

## Session Closeout
After today's task status and evidence have already been synced into `.codex/context/latest-state.json` (normally via `sync_progress_context_governor.py`), run:

```cmd
python C:\Users\WeiZhaoyuan\.codex\skills\context-governor\scripts\closeout_context_governor.py --root .
```

This refreshes:
- `.codex/context/active-context.json`
- `.codex/context/active-context.md`
- `.codex/context/session-delta.json`
- `.codex/context/session-delta.md`
- `.codex/context/history-rollup.json`
- `.codex/context/history-rollup.md`
- `.codex/context/budget-report.json`
- `.codex/context/budget-report.md`
- `.codex/context/latest-snapshot.json`
- `.codex/context/latest-task-graph.json`
- `.codex/context/focus-set.json`
- `.codex/context/resume-pack.md`
- `.codex/context/next-session-prompt.md`
- `docs/implementation/checklist.md`
- `docs/implementation/current-graph.mmd`

This also appends:
- `.codex/context/sync-history.ndjson`

## Project-Local Operator Notes
- Read `docs/implementation/context-governor-playbook.md` when you want the project-specific command loop without reopening the full skill docs.
- Start with `.codex/context/active-context.md` after running `resume_context_governor.py`.
- In `.codex/context/active-context.md`, obey the `Context Gate` section: read `Read Now`, stop at `Stop Reading After`, and widen only to `Next Allowed Reads`.
- Treat `.codex/context/session-delta.md` as the first widening step when you only need the smallest recent-change handoff from the last session.
- Read `.codex/context/history-rollup.md` only after `session-delta.md` when recent blockers, review state, or a broader lifecycle summary matter.
- Check `.codex/context/budget-report.md` before widening to snapshot-heavy reads.
- Copy `.codex/context/next-session-prompt.md` into the next Codex session after running `resume_context_governor.py`.

## Next-Session Prompts
Resume with the smallest possible context:

```text
Use $context-governor to resume this project from .codex/context/active-context.md, widen to .codex/context/session-delta.md before broader history, fall back to .codex/context/latest-snapshot.json only if needed, and tell me the next task with the smallest necessary context.
```

Sync only what changed:

```text
Use $context-governor to sync progress after today's work and only mark tasks done where evidence exists.
```

Close out today's session after state edits:

```text
Use $context-governor to close out today's session. If today's task status or evidence has not been synced yet, sync it first. If you changed task structure in `docs/implementation/checklist.md`, settle the checklist first. Then refresh the latest snapshot, graph, and resume pack for the next session.
```

## Minimal Load Order
On the next session, read in this order:
1. run `resume_context_governor.py`
2. `.codex/context/active-context.md`
3. obey the `Context Gate` and stop at the recommended layer before widening
4. `.codex/context/budget-report.md` if you want to compare the active path against the heavier fallback path
5. only the files listed in `.codex/context/resume-manifest.json` under `recommended_files_to_read`
6. `.codex/context/session-delta.md` only if it is the next allowed read
7. `.codex/context/history-rollup.md` only after `session-delta.md` when broader recent history is still needed
8. `.codex/context/latest-snapshot.json` only if the gate says the active slice is insufficient
