# Schemas Reference

## Repository Layer
Recommended human-readable project outputs:

```text
docs/
  prd/
    approved-prd.md
  implementation/
    checklist.md
    current-graph.mmd
    context-governor-playbook.md
    progress.md
```

`docs/implementation/progress.md` is an optional bootstrap and milestone log. Do not treat it as the live resume source or current-task authority after later sync, resume, or closeout runs.

## Checklist Markdown Convention
Use stable task-ID headings so narrow doc refs can target `docs/implementation/checklist.md#t-001` directly. This checklist is also the human-editable settlement source for `settle_checklist_context_governor.py`.

Settlement requires:
- unique task IDs
- dependency targets that resolve to existing task IDs
- no self dependencies
- an acyclic dependency graph

```md
# Implementation Checklist: Project Plan Title

## Metadata
- Plan ID: project-plan-id
- Snapshot: .codex/context/latest-snapshot.json
- Last Settled At: 2026-03-15T00:00:00Z

## Tasks

### T-001
- Title: Create ordered implementation checklist
- Status: in_progress
- Phase: planning
- Depends On: none
- Confidence: confirmed
- Current: yes
- Acceptance Criteria:
  - Checklist written
- Evidence:
  - Draft saved
```

Optional task fields:
- `- Blocked Reason: ...` when `status` is `blocked`
- `- Review Reason: ...` when `status` is `needs_review`

## Hidden Layer
Recommended compact machine-readable files:

```text
.codex/
  context/
    active-context.json
    active-context.md
    budget-report.json
    budget-report.md
    doc-plan.json
    session-delta.json
    session-delta.md
    history-rollup.json
    history-rollup.md
    latest-state.json
    latest-snapshot.json
    latest-task-graph.json
    focus-set.json
    resume-pack.md
    next-session-prompt.md
    resume-manifest.json
    sync-history.ndjson
```

## Canonical Doc Plan
`doc-plan.json` is the normalized structural plan derived from the PRD or rebuilt docs.

```json
{
  "plan_id": "project-plan-id",
  "title": "Project Plan Title",
  "tasks": [
    {
      "id": "T-001",
      "title": "Create ordered implementation checklist",
      "phase": "planning",
      "status": "todo",
      "depends_on": [],
      "acceptance_criteria": [
        "Checklist written",
        "IDs are stable"
      ],
      "confidence": "confirmed"
    }
  ]
}
```

## Hidden State
`latest-state.json` tracks operational progress and current focus. `settle_checklist_context_governor.py` can rebuild it directly from checklist status, evidence, and current-task markers.

Optional operational fields:
- `blocked_reason` for blocked tasks
- `review_reason` for tasks that stay in `needs_review`

```json
{
  "generated_at": "2026-03-15T00:00:00Z",
  "current_task_id": "T-001",
  "tasks": [
    {
      "id": "T-001",
      "status": "needs_review",
      "evidence": [],
      "current": true,
      "next": [
        "T-002"
      ],
      "review_reason": "missing completion evidence",
      "last_updated_at": "2026-03-15T00:00:00Z"
    }
  ]
}
```

## Focus Set
`focus-set.json` keeps the narrow context slice that should be loaded first during resume.

Use `doc_refs` for targeted checklist or PRD anchors only. A plain `docs/prd/approved-prd.md` path without an anchor is not a narrow doc ref and should stay in full-PRD fallback handling instead.

```json
{
  "current_task_id": "T-002",
  "dependency_ids": [
    "T-001"
  ],
  "successor_ids": [
    "T-003"
  ],
  "doc_refs": [
    "docs/implementation/checklist.md#t-002"
  ]
}
```

## Active Context
`active-context.json` is the smallest machine-readable resume slice. `active-context.md` is the human-readable companion that should be read before wider project history.

Optional gate fields:
- `recommended_context_level`
- `recommended_files_to_read`
- `stop_reading_after`
- `next_allowed_reads`
- `escalation_reasons`
- `active_slice_sufficient`
- `gate_flags`
- `fallback_files_to_read`

Contract notes:
- `doc_refs` should stay limited to targeted anchors such as `docs/implementation/checklist.md#t-002` or `docs/prd/approved-prd.md#milestone-2`.
- A plain `docs/prd/approved-prd.md` entry means resume could not stay narrow and must treat the PRD as a full fallback document instead of a targeted requirement slice.
- When the gate escalates to `prd_required`, the read order is `active-context.md` -> `latest-snapshot.json` -> `docs/prd/approved-prd.md`.
- Missing targeted doc refs plus missing acceptance criteria is a valid reason to escalate to `prd_required`.

```json
{
  "plan_id": "project-plan-id",
  "generated_at": "2026-03-15T00:00:00Z",
  "current_task_id": "T-002",
  "current_task_title": "Write the ordered implementation checklist",
  "current_task_status": "in_progress",
  "acceptance_criteria": [
    "Checklist saved to docs/implementation/checklist.md"
  ],
  "evidence": [
    "checklist-written"
  ],
  "review_reason": "missing completion evidence",
  "dependency_ids": ["T-001"],
  "successor_ids": ["T-003"],
  "doc_refs": [
    "docs/implementation/checklist.md#t-002"
  ],
  "files_to_read": [
    ".codex/context/active-context.md",
    "docs/implementation/checklist.md#t-002"
  ],
  "recommended_context_level": "active_only",
  "recommended_files_to_read": [
    ".codex/context/active-context.md",
    "docs/implementation/checklist.md#t-002"
  ],
  "stop_reading_after": "active-context path",
  "next_allowed_reads": [
    ".codex/context/session-delta.md"
  ],
  "escalation_reasons": [
    "Current task, dependencies, successors, and doc anchors are resolved in the active slice."
  ],
  "active_slice_sufficient": true,
  "gate_flags": {
    "missing_doc_anchor": false,
    "has_conflicts": false,
    "has_structural_warnings": false,
    "has_review_or_blocker_state": false,
    "needs_full_prd": false
  },
  "fallback_files_to_read": [
    ".codex/context/session-delta.md",
    ".codex/context/history-rollup.md",
    ".codex/context/latest-snapshot.json",
    "docs/prd/approved-prd.md"
  ],
  "warnings": []
}
```

## Session Delta
`session-delta.json` is the optional ultra-compact recent-change handoff between `active-context.*` and `history-rollup.*`. It should stay focused on the latest meaningful transition, touched tasks, and the next wider read. It is not canonical state and should always be derivable from the settled snapshot plus sync history.

```json
{
  "plan_id": "project-plan-id",
  "generated_at": "2026-03-15T00:00:00Z",
  "current_task_id": "T-002",
  "current_task_title": "Write the ordered implementation checklist",
  "current_task_status": "in_progress",
  "latest_event": {
    "timestamp": "2026-03-15T00:00:00Z",
    "event": "sync_progress",
    "current_task_id": "T-002",
    "current_task_status": "in_progress",
    "updated_task_id": "T-001",
    "updated_task_status": "done",
    "warnings_count": 0
  },
  "previous_current_task_id": "T-001",
  "focus_transition": {
    "from_task_id": "T-001",
    "to_task_id": "T-002"
  },
  "touched_task_ids": ["T-001", "T-002"],
  "touched_tasks": [
    {
      "id": "T-001",
      "title": "Create ordered implementation checklist",
      "status": "done",
      "last_updated_at": "2026-03-15T00:00:00Z"
    },
    {
      "id": "T-002",
      "title": "Write the ordered implementation checklist",
      "status": "in_progress",
      "last_updated_at": "2026-03-15T00:00:00Z"
    }
  ],
  "warning_count": 0,
  "warnings": [],
  "next_read": ".codex/context/history-rollup.md"
}
```

## Canonical Snapshot
`latest-snapshot.json` is the single canonical settled view that resume consumes and sync/closeout regenerate. Even when `active-context.*`, `session-delta.*`, and `history-rollup.*` all exist, only `latest-snapshot.json` is canonical.

Required top-level fields:
- `plan_id`
- `generated_at`
- `current_task_id`
- `tasks`
- `warnings`

## Task Node Shape
Every settled task node should support at least these fields:

```json
{
  "id": "T-001",
  "title": "Create ordered implementation checklist",
  "phase": "planning",
  "status": "todo",
  "depends_on": [],
  "acceptance_criteria": [
    "Checklist written",
    "IDs are stable"
  ],
  "confidence": "confirmed",
  "evidence": [],
  "review_reason": "missing completion evidence",
  "current": false,
  "next": [],
  "last_updated_at": "2026-03-15T00:00:00Z"
}
```

Minimal example:

```json
{
  "id": "T-001",
  "title": "Create ordered implementation checklist",
  "status": "todo",
  "depends_on": [],
  "acceptance_criteria": ["Checklist written", "IDs are stable"],
  "evidence": [],
  "last_updated_at": "2026-03-15T00:00:00Z"
}
```

## Status Enum
Allowed operational statuses:
- `todo`
- `in_progress`
- `done`
- `blocked`
- `needs_review`
- `conflict`

Optional rebuild confidence labels:
- `confirmed`
- `inferred`
- `uncertain`

## Task Graph Shape
`latest-task-graph.json` can stay compact:

```json
{
  "plan_id": "project-plan-id",
  "tasks": [
    {
      "id": "T-001",
      "title": "Create ordered implementation checklist",
      "status": "todo",
      "depends_on": []
    }
  ]
}
```

## Resume Pack Fields
`resume-pack.md` is an auxiliary current-task recap, not part of the primary widening ladder in `fallback_files_to_read`.

It should stay focused on:
- Plan ID
- Snapshot timestamp
- Current task ID and title
- Current task status
- Current task acceptance criteria
- Direct dependencies
- Direct successors
- Direct evidence or blockers

## History Rollup
`history-rollup.json` compacts recent milestones, open review/blocker state, and the last few lifecycle events after `session-delta.*` is no longer enough. It should stay broader than `session-delta.*` but still much smaller than replaying `sync-history.ndjson` on every session.

```json
{
  "plan_id": "project-plan-id",
  "generated_at": "2026-03-15T00:00:00Z",
  "current_task_id": "T-002",
  "status_counts": {
    "done": 1,
    "in_progress": 1,
    "todo": 1
  },
  "recent_completed_task_ids": ["T-001"],
  "blocked_task_ids": [],
  "needs_review_task_ids": [],
  "warning_count": 0,
  "warnings": [],
  "recent_events": [
    {
      "timestamp": "2026-03-15T00:00:00Z",
      "event": "resume",
      "plan_id": "project-plan-id",
      "current_task_id": "T-002"
    }
  ]
}
```

## Budget Report
`budget-report.json` quantifies the default active-context resume cost against the heavier fallback path so you can see how much context expansion would cost before loading it. `budget-report.md` is the human-readable companion.

```json
{
  "plan_id": "project-plan-id",
  "generated_at": "2026-03-15T00:00:00Z",
  "current_task_id": "T-002",
  "current_task_title": "Write the ordered implementation checklist",
  "active_context_path": {
    "file_count": 2,
    "bytes_total": 480,
    "approx_tokens_total": 120,
    "refs": [
      {
        "path": ".codex/context/active-context.md",
        "source_path": ".codex/context/active-context.md",
        "scope": "file",
        "bytes": 320,
        "approx_tokens": 80,
        "anchor_found": true
      },
      {
        "path": "docs/implementation/checklist.md#t-002",
        "source_path": "docs/implementation/checklist.md",
        "scope": "anchor",
        "anchor": "t-002",
        "bytes": 160,
        "approx_tokens": 40,
        "anchor_found": true
      }
    ]
  },
  "current_recommendation": {
    "recommended_context_level": "active_only",
    "active_slice_sufficient": true,
    "recommended_files_to_read": [
      ".codex/context/active-context.md",
      "docs/implementation/checklist.md#t-002"
    ],
    "stop_reading_after": "active-context path",
    "next_allowed_reads": [
      ".codex/context/session-delta.md"
    ],
    "escalation_reasons": [
      "Current task, dependencies, successors, and doc anchors are resolved in the active slice."
    ],
    "recommended_path": {
      "file_count": 2,
      "bytes_total": 480,
      "approx_tokens_total": 120,
      "refs": []
    }
  },
  "snapshot_heavy_fallback_path": {
    "file_count": 6,
    "bytes_total": 2348,
    "approx_tokens_total": 587,
    "refs": []
  },
  "comparison": {
    "extra_files_if_fallback_needed": 4,
    "extra_bytes_if_fallback_needed": 1868,
    "approx_tokens_saved_when_active_slice_is_enough": 467,
    "reduction_percent_vs_snapshot_heavy_path": 79.56
  },
  "notes": [
    "Approx tokens are estimated as ceil(bytes / 4)."
  ]
}
```

## Resume Manifest Shape
`resume-manifest.json` records the narrow startup slice and a few observability counters. It is refreshed by `resume_context_governor.py` and intentionally not rewritten by sync or closeout helpers.

Boundary rules:
- `resume-manifest.json` remains resume-only observability and must not become a hidden-state settlement source.
- `full_prd_fallback` should flip to `true` only when resume actually had to read the full `docs/prd/approved-prd.md` document after `latest-snapshot.json`.
- A plain `docs/prd/approved-prd.md` path without an anchor indicates full-document fallback, not a targeted `doc_refs` entry.

```json
{
  "plan_id": "project-plan-id",
  "snapshot_generated_at": "2026-03-15T00:00:00Z",
  "current_task_id": "T-002",
  "current_task_title": "Write the ordered implementation checklist",
  "loaded_task_ids": ["T-002", "T-001", "T-003"],
  "dependency_ids": ["T-001"],
  "successor_ids": ["T-003"],
  "doc_refs": [
    "docs/implementation/checklist.md#t-002"
  ],
  "files_to_read": [
    ".codex/context/active-context.md",
    "docs/implementation/checklist.md#t-002"
  ],
  "recommended_context_level": "active_only",
  "recommended_files_to_read": [
    ".codex/context/active-context.md",
    "docs/implementation/checklist.md#t-002"
  ],
  "stop_reading_after": "active-context path",
  "next_allowed_reads": [
    ".codex/context/session-delta.md"
  ],
  "escalation_reasons": [
    "Current task, dependencies, successors, and doc anchors are resolved in the active slice."
  ],
  "fallback_files_to_read": [
    ".codex/context/session-delta.md",
    ".codex/context/history-rollup.md",
    ".codex/context/latest-snapshot.json",
    "docs/prd/approved-prd.md"
  ],
  "full_prd_fallback": false,
  "tasks_loaded_count": 3,
  "doc_refs_count": 1,
  "active_context_bytes": 412,
  "session_delta_bytes": 228,
  "history_rollup_bytes": 620,
  "resume_pack_bytes": 512,
  "warnings_count": 0
}
```

## Next Session Prompt
`next-session-prompt.md` is a copy-ready prompt that should stay aligned with the current task, direct dependencies, and narrow doc refs.

Keep it focused on:
- the current task ID and title
- the current operational status
- direct dependency and successor IDs
- the smallest list of files to read first, led by `active-context.md`
- the first widening step to `session-delta.md`
- the fallback reads that expand from `session-delta.md` to `history-rollup.md` and `latest-snapshot.json`
- `resume-pack.md` only as an auxiliary current-task recap outside the primary widening ladder
- a clear fallback to the full PRD only when the narrow slice is insufficient
- policy lines that stay aligned with the read-now set; if `latest-snapshot.json` or `approved-prd.md` is already required now, the prompt should explain that instead of saying `Do not read`

## Sync History Event Shape
`sync-history.ndjson` appends one line per `initialized`, `settle_checklist`, `resume`, `sync_progress`, or `closeout` action.

```json
{
  "timestamp": "2026-03-15T00:00:00Z",
  "event": "sync_progress",
  "plan_id": "project-plan-id",
  "current_task_id": "T-002",
  "current_task_status": "todo",
  "updated_task_id": "T-001",
  "updated_task_status": "done",
  "evidence_added_count": 1,
  "blocked_reason_present": false,
  "review_reason_present": false,
  "current_task_selection": "single-ready-successor",
  "warnings_count": 0
}
```
