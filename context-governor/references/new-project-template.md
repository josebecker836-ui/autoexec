# New Project Template

Use this file when you want to attach `context-governor` to a brand-new project without inventing the setup flow each time. Replace the placeholders once, then copy the commands and prompts directly.

## Replace These Placeholders First

- `my-project` -> stable plan slug
- `My Project Plan` -> human-readable plan title
- `T-001` -> current task ID when syncing progress

## 1. Initialize The Project

Run this from the target project root:

```cmd
python %USERPROFILE%\.codex\skills\context-governor\scripts\init_context_governor.py --root . --plan-id my-project --plan-title "My Project Plan"
```

This bootstraps:

- `docs/prd/approved-prd.md`
- `docs/implementation/checklist.md`
- `docs/implementation/current-graph.mmd`
- `docs/implementation/context-governor-playbook.md`
- `.codex/context/*`

## 2. Drop In The Approved PRD

Put the approved PRD here:

```text
docs/prd/approved-prd.md
```

If the PRD already lives elsewhere, copy or settle it into this path before the first planning pass.

## 3. First Planning Prompt

Use this in Codex right after the PRD is in place:

```text
Use $context-governor to break docs/prd/approved-prd.md into an ordered checklist, dependency graph, and initial snapshot. Rewrite docs/implementation/checklist.md as a sequenced implementation plan with stable task IDs, clear dependencies, and the best current task to start from.
```

## 4. Settle The Checklist

After `docs/implementation/checklist.md` is created or revised, run:

```cmd
python %USERPROFILE%\.codex\skills\context-governor\scripts\settle_checklist_context_governor.py --root .
```

If this fails, fix the checklist structure first. Do not bypass duplicate task IDs, missing dependency targets, self dependencies, or dependency cycles.

## 5. Resume A Later Session With Minimum Context

Before reopening broad project docs in the next session:

```cmd
python %USERPROFILE%\.codex\skills\context-governor\scripts\resume_context_governor.py --root .
```

Then use this prompt:

```text
Use $context-governor to resume this project from .codex/context/active-context.md, widen to .codex/context/session-delta.md before broader history, fall back to .codex/context/latest-snapshot.json only if needed, and tell me the next task with the smallest necessary context.
```

## 6. Sync A Task Change Immediately

When one task changes status, sync it right away:

```cmd
python %USERPROFILE%\.codex\skills\context-governor\scripts\sync_progress_context_governor.py --root . --task T-001 --status done --evidence shipped-checklist
```

Blocked example:

```cmd
python %USERPROFILE%\.codex\skills\context-governor\scripts\sync_progress_context_governor.py --root . --task T-001 --status blocked --blocked-reason waiting-on-api --evidence found-blocker
```

Sync prompt:

```text
Use $context-governor to sync progress after today's work and only mark tasks done where evidence exists.
```

## 7. Close Out The Day

After today's status and evidence have already been synced:

```cmd
python %USERPROFILE%\.codex\skills\context-governor\scripts\closeout_context_governor.py --root .
```

Closeout prompt:

```text
Use $context-governor to close out today's session. If today's task status or evidence has not been synced yet, sync it first. If you changed task structure in docs/implementation/checklist.md, settle the checklist first. Then refresh the latest snapshot, graph, and resume pack for the next session.
```

## 8. Minimal Daily Loop

Use this order every time:

1. `init` once per project
2. place the approved PRD
3. run the first planning prompt
4. settle the checklist
5. resume before each later session
6. sync after each meaningful task change
7. close out the session

## 9. One-Command Validation

When you change the skill package or want to confirm the helpers still agree with the docs:

```cmd
cd %USERPROFILE%\.codex\skills\context-governor
python scripts\quick_validate.py
```

Expected final line:

```text
READY
```
