# Context Governor Balanced Enhancements Design

**Date:** 2026-03-16
**Skill:** `context-governor`
**Mode:** Balanced enhancement
**Status:** Approved in-session, documented before implementation
**Git:** Do not commit yet

## Goal
Close the remaining hard contract gaps between runtime outputs, reference docs, and validator coverage without changing the underlying storage model or widening strategy.

## Confirmed Constraints
- Keep the current architecture:
  - human-editable surface: `docs/implementation/*`
  - machine-managed hidden layer: `.codex/context/*`
  - internal settlement point: `.codex/context/latest-snapshot.json`
- Keep the primary widening ladder:
  1. `active-context.*`
  2. `session-delta.*`
  3. `history-rollup.*`
  4. `latest-snapshot.json`
  5. `docs/prd/approved-prd.md`
- Keep `resume-pack.md` auxiliary only.
- Keep `resume-manifest.json` as resume-only observability output, not freshness authority.
- Keep `session-delta.json.focus_transition` in structured object form:

```json
{
  "from_task_id": "T-001",
  "to_task_id": "T-002"
}
```

## Problem Statement
The skill is already operational, but a few important guarantees are still too implicit:
- some runtime/document contracts are correct in one place and only partially asserted elsewhere
- some machine-readable fields are present but not guarded by dedicated validator checks
- some realistic lifecycle scenarios are only covered indirectly by the current smoke flow

This leaves room for silent drift in future edits, especially around resume-only outputs, PRD escalation behavior, and closeout event semantics.

## Chosen Approach
Use a three-round balanced enhancement path:

### Round 1: Contract Audit Tightening
Audit and align the remaining hard runtime contracts across:
- `SKILL.md`
- `references/workflow.md`
- `references/sync-rules.md`
- `references/schemas.md`
- any quickstart or cheatsheet text that describes machine behavior

This round is documentation-first and only touches runtime code if a real documented contract is missing or ambiguous.

### Round 2: Validator Coverage Expansion
Add narrow validator assertions for machine-readable fields that are important but still weakly protected. Priorities:
- `resume-manifest.json` must remain resume-only and must not be rewritten by settle/sync/closeout flows
- context-gate and prompt fields must stay consistent when PRD escalation is or is not required
- closeout/sync event chains should preserve the latest-event semantics expected by `session-delta.json` and `history-rollup.json`

### Round 3: Scenario Validation
Add realistic scenario tests that reproduce the lifecycle boundaries most likely to regress:
- resume writes `resume-manifest.json`, later sync/closeout refreshes do not
- full PRD fallback path is triggered only when targeted doc refs and acceptance criteria are both insufficient
- closeout after prior sync preserves append-only history semantics and expected latest-event behavior

## Non-Goals
- No storage model redesign
- No new output files
- No broader refactor of `refresh_outputs`
- No speculative optimization or cosmetic cleanup
- No change to the public widening ladder

## Runtime Contract Decisions

### Resume Manifest Boundary
`resume-manifest.json` is written only by `resume_context_governor.py`.

`sync_progress_context_governor.py` and `closeout_context_governor.py` may refresh the settled working outputs, but they must not rewrite the manifest because the manifest describes the current resume entrypoint, not every internal settlement action.

### PRD Escalation Rule
`prd_required` is the strongest escalation level and should occur only when:
- the active slice lacks targeted `doc_refs`
- the active slice lacks acceptance criteria
- `docs/prd/approved-prd.md` exists

This remains stricter than `snapshot_required`. Missing anchors, conflicts, and structural warnings escalate to snapshot first, not directly to full PRD.

### Closeout Event Semantics
Closeout should continue to append an event and refresh derived outputs from the settled state. The validator should explicitly guard:
- append-only history growth
- latest event identity after closeout
- stable current-task semantics when closeout does not intentionally retarget focus

## Testing Strategy
Implementation will follow strict TDD:
1. add the failing validator or scenario first
2. run `quick_validate.py` and confirm the failure is real and correctly targeted
3. make the smallest code or doc fix
4. rerun validation to green

## Risks And Mitigations
- Risk: over-testing internal implementation details
  - Mitigation: assert durable contracts and observable outputs, not incidental formatting
- Risk: doc updates drifting past actual runtime behavior
  - Mitigation: keep validator-led changes first, then document only confirmed behavior
- Risk: accidental architecture creep
  - Mitigation: reject any change that adds new storage authority or changes widening order

## Acceptance Criteria
- Remaining hard contract mismatches in the balanced scope are resolved
- `quick_validate.py` gains dedicated coverage for resume-manifest, PRD escalation, and closeout-lifecycle semantics
- All existing validations still pass
- Final verification ends with `READY`
