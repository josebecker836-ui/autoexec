# Context Governor Balanced Enhancements Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tighten the remaining hard runtime/document contracts for `context-governor` and add validator coverage for resume-manifest boundaries, PRD escalation, and closeout lifecycle behavior.

**Architecture:** Keep the current dual-surface model intact: human-edited `docs/implementation/*`, machine-managed `.codex/context/*`, and `.codex/context/latest-snapshot.json` as the internal settlement point. Implement only precision patches: document confirmed contracts, add failing validator scenarios, then make the smallest runtime fixes needed to restore green.

**Tech Stack:** Python 3, markdown references, JSON state files, `quick_validate.py`

---

## Chunk 1: Document The Approved Balanced Scope

### Task 1: Persist the approved design and scope

**Files:**
- Create: `C:\Users\WeiZhaoyuan\.codex\skills\context-governor\docs\superpowers\specs\2026-03-16-context-governor-balanced-enhancements-design.md`
- Create: `C:\Users\WeiZhaoyuan\.codex\skills\context-governor\docs\superpowers\plans\2026-03-16-context-governor-balanced-enhancements.md`

- [ ] **Step 1: Write the balanced design doc**

Document the chosen scope, constraints, round-by-round intent, and non-goals.

- [ ] **Step 2: Verify the design doc matches approved constraints**

Check:
- `.codex/context/latest-snapshot.json` remains the settlement point
- `resume-pack.md` stays auxiliary
- `resume-manifest.json` stays resume-only
- `focus_transition` stays object-shaped in JSON

- [ ] **Step 3: Write the implementation plan**

Record exact files, validator-first sequencing, and verification commands.

- [ ] **Step 4: Review both docs for scope creep**

Reject anything outside:
- contract mismatches
- validator gaps
- realistic scenario gaps

## Chunk 2: Round 1 And Round 2 TDD

### Task 2: Add a failing validator for resume-manifest boundaries

**Files:**
- Modify: `C:\Users\WeiZhaoyuan\.codex\skills\context-governor\scripts\quick_validate.py`
- Possibly modify: `C:\Users\WeiZhaoyuan\.codex\skills\context-governor\references\schemas.md`
- Possibly modify: `C:\Users\WeiZhaoyuan\.codex\skills\context-governor\references\sync-rules.md`
- Possibly modify: `C:\Users\WeiZhaoyuan\.codex\skills\context-governor\references\workflow.md`

- [ ] **Step 1: Write the failing validator scenario**

Extend `quick_validate.py` so it:
- runs `resume_context_governor.py`
- captures `resume-manifest.json`
- runs `sync_progress_context_governor.py` and `closeout_context_governor.py`
- proves the manifest was not rewritten

- [ ] **Step 2: Run validation and confirm RED**

Run:

```bash
python C:\Users\WeiZhaoyuan\.codex\skills\context-governor\scripts\quick_validate.py
```

Expected: FAIL with a manifest-boundary assertion if the runtime or validator still permits drift.

- [ ] **Step 3: Apply the minimal fix**

If runtime is already correct, keep the code unchanged and update only contract docs. If runtime is wrong, patch only the writer boundary causing the manifest rewrite.

- [ ] **Step 4: Run validation and confirm GREEN**

Run the same full validator command and confirm the new boundary passes.

### Task 3: Add a failing validator for PRD escalation consistency

**Files:**
- Modify: `C:\Users\WeiZhaoyuan\.codex\skills\context-governor\scripts\quick_validate.py`
- Possibly modify: `C:\Users\WeiZhaoyuan\.codex\skills\context-governor\scripts\closeout_context_governor.py`
- Possibly modify: `C:\Users\WeiZhaoyuan\.codex\skills\context-governor\references\schemas.md`
- Possibly modify: `C:\Users\WeiZhaoyuan\.codex\skills\context-governor\references\workflow.md`

- [ ] **Step 1: Write the failing validator scenario**

Add a scenario where the active task resolves without targeted doc refs and without acceptance criteria while `docs/prd/approved-prd.md` exists.

- [ ] **Step 2: Run validation and confirm RED**

Run:

```bash
python C:\Users\WeiZhaoyuan\.codex\skills\context-governor\scripts\quick_validate.py
```

Expected: FAIL if `recommended_context_level`, `recommended_files_to_read`, `next_allowed_reads`, or prompt policy text drift from the intended `prd_required` path.

- [ ] **Step 3: Apply the minimal fix**

Patch only the gate or prompt logic needed to restore consistency.

- [ ] **Step 4: Run validation and confirm GREEN**

Run the same validator and confirm the PRD escalation scenario passes.

## Chunk 3: Round 3 Scenario Coverage

### Task 4: Add a failing validator for closeout lifecycle semantics

**Files:**
- Modify: `C:\Users\WeiZhaoyuan\.codex\skills\context-governor\scripts\quick_validate.py`
- Possibly modify: `C:\Users\WeiZhaoyuan\.codex\skills\context-governor\scripts\closeout_context_governor.py`
- Possibly modify: `C:\Users\WeiZhaoyuan\.codex\skills\context-governor\references\schemas.md`

- [ ] **Step 1: Write the failing validator scenario**

Add a scenario that verifies:
- `sync-history.ndjson` grows append-only
- latest event becomes `closeout` after closeout
- `session-delta.json` and `history-rollup.json` reflect the expected closeout lifecycle outcome

- [ ] **Step 2: Run validation and confirm RED**

Run:

```bash
python C:\Users\WeiZhaoyuan\.codex\skills\context-governor\scripts\quick_validate.py
```

Expected: FAIL if closeout semantics are still only indirectly covered.

- [ ] **Step 3: Apply the minimal fix**

Patch only the event-construction or derived-output logic required by the failing scenario.

- [ ] **Step 4: Run validation and confirm GREEN**

Run the same validator and confirm the closeout scenario passes.

### Task 5: Refresh contract docs to match verified runtime

**Files:**
- Modify: `C:\Users\WeiZhaoyuan\.codex\skills\context-governor\SKILL.md`
- Modify: `C:\Users\WeiZhaoyuan\.codex\skills\context-governor\references\workflow.md`
- Modify: `C:\Users\WeiZhaoyuan\.codex\skills\context-governor\references\sync-rules.md`
- Modify: `C:\Users\WeiZhaoyuan\.codex\skills\context-governor\references\schemas.md`

- [ ] **Step 1: Update only contract text proven by validation**

Do not add aspirational wording.

- [ ] **Step 2: Re-read the touched sections**

Confirm:
- resume-only manifest rule is explicit
- PRD escalation wording matches runtime
- closeout event semantics do not contradict validator behavior

## Chunk 4: Final Verification

### Task 6: Run the full fresh verification pass

**Files:**
- Modify: none required

- [ ] **Step 1: Run full validation**

```bash
python C:\Users\WeiZhaoyuan\.codex\skills\context-governor\scripts\quick_validate.py
```

Expected: each pass section succeeds and the output ends with `READY`.

- [ ] **Step 2: Inspect for unintended file growth or architectural drift**

Check that no new authority file or widening step was introduced.

- [ ] **Step 3: Report results without claiming more than the evidence proves**

Include:
- what changed
- which validator scenarios were added
- whether fresh verification ended in `READY`
- any residual gaps not covered in this balanced pass
