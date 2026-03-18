# Context Governor

Reusable Codex skill for long-running projects that need disciplined context loading, PRD-to-checklist planning, dependency tracking, progress sync, and low-token resume flows.

Chinese overview:
- [README-zh.md](./README-zh.md)

## What It Solves

- Turn an approved PRD into an ordered implementation checklist with stable task IDs.
- Build a dependency graph or Mermaid task graph from the settled plan.
- Keep human-readable project docs and machine-readable hidden state in sync.
- Resume from the smallest safe context instead of reloading the full project every session.
- Mark progress with evidence so future sessions know exactly where to continue.

## Why It Helps With Token Control

The skill enforces a narrow loading ladder instead of re-reading broad project context by habit:

1. `.codex/context/active-context.md`
2. `.codex/context/session-delta.md`
3. `.codex/context/history-rollup.md`
4. `.codex/context/latest-snapshot.json`
5. PRD slices or full PRD only as the final fallback

That keeps repeated input much smaller across long project lifecycles.

## Repository Layout

- [SKILL.md](./SKILL.md): main skill contract
- [README-zh.md](./README-zh.md): Chinese-first reuse and onboarding overview
- [scripts](./scripts): deterministic helpers for init, settle, resume, sync, closeout, render, and validation
- [references](./references): workflow, schema, sync rules, and quickstart docs
- [assets](./assets): templates and expected outputs for validation

## Install For Reuse

Install it into the global Codex skills directory so every project can call it.

### New machine

```cmd
git clone https://github.com/josebecker836-ui/Product_context_management..git %USERPROFILE%\.codex\skills\context-governor
```

### This machine

This skill is already globally available because it already lives at:

```text
C:\Users\WeiZhaoyuan\.codex\skills\context-governor
```

After installing on any machine, restart Codex so the skill list refreshes.

## Verify Installation

Run:

```cmd
cd %USERPROFILE%\.codex\skills\context-governor
python scripts\quick_validate.py
```

Expected final line:

```text
READY
```

## Use In Any Project

Inside the target project root:

```cmd
python %USERPROFILE%\.codex\skills\context-governor\scripts\init_context_governor.py --root . --plan-id my-project --plan-title "My Project Plan"
```

Then invoke the skill in Codex with prompts like:

- `Use $context-governor to break this approved PRD into an ordered checklist, dependency graph, and initial snapshot.`
- `Use $context-governor to resume this project from .codex/context/active-context.md with the smallest necessary context.`
- `Use $context-governor to sync progress from today's work and only mark tasks done where evidence exists.`

For a copy-ready first-run template, start here:
- [references/new-project-template.md](./references/new-project-template.md)

## Recommended Project Workflow

1. Initialize the project-local context scaffolding.
2. Build `docs/implementation/checklist.md` from the approved PRD.
3. Settle the checklist into hidden state and snapshot files.
4. Resume future sessions from `active-context.md` instead of broad repo docs.
5. Sync progress only when evidence exists.
6. Close out the session to refresh resume artifacts for the next day.

## Core Commands

```cmd
python scripts\init_context_governor.py --root . --plan-id my-project --plan-title "My Project Plan"
python scripts\settle_checklist_context_governor.py --root .
python scripts\resume_context_governor.py --root .
python scripts\sync_progress_context_governor.py --root . --task T-014 --status done --evidence shipped-checklist
python scripts\closeout_context_governor.py --root .
python scripts\quick_validate.py
```

## Docs

- [README-zh.md](./README-zh.md)
- [new-project-template.md](./references/new-project-template.md)
- [quickstart.md](./references/quickstart.md)
- [quickstart-zh.md](./references/quickstart-zh.md)
- [cheatsheet-zh.md](./references/cheatsheet-zh.md)
- [workflow.md](./references/workflow.md)
- [schemas.md](./references/schemas.md)
- [sync-rules.md](./references/sync-rules.md)
