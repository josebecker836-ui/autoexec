# Session Delta Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an ultra-compact `session-delta` handoff layer that captures only the latest meaningful project changes without increasing the default resume read set.

**Architecture:** Reuse the existing `refresh_outputs` settlement path as the single writer for the new artifact. Generate `.codex/context/session-delta.{json,md}` from the canonical snapshot plus recent history events, then wire it into the resume escalation ladder as an optional shortcut between `active-context` and `history-rollup`.

**Tech Stack:** Python 3, markdown render helpers, JSON state snapshots, deterministic validation in `quick_validate.py`

**Implementation Status:** Completed and validated with `python C:\Users\WeiZhaoyuan\.codex\skills\context-governor\scripts\quick_validate.py` -> `READY`

---

## Chunk 1: Red Tests

### Task 1: Define the expected session-delta contract

**Files:**
- Modify: `C:\Users\WeiZhaoyuan\.codex\skills\context-governor\scripts\quick_validate.py`
- Test: `C:\Users\WeiZhaoyuan\.codex\skills\context-governor\scripts\quick_validate.py`

- [x] **Step 1: Write the failing test**
  Add smoke assertions that require:
  - `.codex/context/session-delta.json`
  - `.codex/context/session-delta.md`
  - `next_allowed_reads` to point to `.codex/context/session-delta.md` before `history-rollup.md`
  - `active_plus_history` recommendations to include both `session-delta.md` and `history-rollup.md`
  - `session-delta.json` to stay smaller than `history-rollup.json`

- [x] **Step 2: Run test to verify it fails**
  Run: `python C:\Users\WeiZhaoyuan\.codex\skills\context-governor\scripts\quick_validate.py`
  Expected: FAIL because `session-delta` outputs and new escalation ordering do not exist yet.

## Chunk 2: Generate Session Delta

### Task 2: Add minimal builders and writers

**Files:**
- Modify: `C:\Users\WeiZhaoyuan\.codex\skills\context-governor\scripts\closeout_context_governor.py`
- Test: `C:\Users\WeiZhaoyuan\.codex\skills\context-governor\scripts\quick_validate.py`

- [x] **Step 1: Write the minimal implementation**
  Add helper functions to:
  - summarize the latest event
  - compute recently touched task IDs
  - render a tiny `.json` and `.md` artifact
  - write both files during `refresh_outputs`

- [x] **Step 2: Run targeted verification**
  Run: `python C:\Users\WeiZhaoyuan\.codex\skills\context-governor\scripts\quick_validate.py`
  Expected: the new file-existence assertions pass, with any remaining failures isolated to resume wiring.

## Chunk 3: Wire Resume Escalation

### Task 3: Insert session-delta into the read ladder

**Files:**
- Modify: `C:\Users\WeiZhaoyuan\.codex\skills\context-governor\scripts\closeout_context_governor.py`
- Modify: `C:\Users\WeiZhaoyuan\.codex\skills\context-governor\scripts\resume_context_governor.py`
- Test: `C:\Users\WeiZhaoyuan\.codex\skills\context-governor\scripts\quick_validate.py`

- [x] **Step 1: Update gate behavior**
  Keep `active_only` as the default recommendation, but change the next escalation step to `session-delta.md`.

- [x] **Step 2: Update widened recommendations**
  For `active_plus_history`, include `session-delta.md` before `history-rollup.md`.

- [x] **Step 3: Refresh prompt and manifest outputs**
  Make `next-session-prompt.md` and `resume-manifest.json` advertise the new order without adding `session-delta.md` to the default minimal read set.

- [x] **Step 4: Run the full validator**
  Run: `python C:\Users\WeiZhaoyuan\.codex\skills\context-governor\scripts\quick_validate.py`
  Expected: PASS for smoke, ambiguity, and structure lint with the new layer included.

## Chunk 4: Update Skill Docs

### Task 4: Document the new handoff layer

**Files:**
- Modify: `C:\Users\WeiZhaoyuan\.codex\skills\context-governor\SKILL.md`
- Modify: `C:\Users\WeiZhaoyuan\.codex\skills\context-governor\references\workflow.md`
- Modify: `C:\Users\WeiZhaoyuan\.codex\skills\context-governor\references\schemas.md`
- Modify: `C:\Users\WeiZhaoyuan\.codex\skills\context-governor\references\quickstart.md`
- Modify: `C:\Users\WeiZhaoyuan\.codex\skills\context-governor\references\quickstart-zh.md`
- Modify: `C:\Users\WeiZhaoyuan\.codex\skills\context-governor\references\cheatsheet-zh.md`

- [x] **Step 1: Describe the new layer**
  Explain that `session-delta` is an optional recent-change handoff layer, not a new canonical source.

- [x] **Step 2: Update load order and file lists**
  Keep `active-context` first, then `session-delta`, then `history-rollup`, then snapshot and PRD fallback.

- [x] **Step 3: Re-run verification**
  Run: `python C:\Users\WeiZhaoyuan\.codex\skills\context-governor\scripts\quick_validate.py`
  Expected: READY
