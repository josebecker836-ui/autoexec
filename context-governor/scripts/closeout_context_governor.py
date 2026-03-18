import argparse
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

from build_resume_pack import render_resume_pack
from render_checklist import render_checklist
from render_task_graph import render_mermaid
from settle_snapshot import settle_snapshot


SCRIPTS_DIR = Path(__file__).resolve().parent


def now_utc() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_index(tasks: list[dict]) -> dict[str, dict]:
    return {task["id"]: task for task in tasks}


def direct_successor_ids(tasks: list[dict], task_id: str) -> list[str]:
    successors = []
    for task in tasks:
        if task_id in task.get("depends_on", []):
            successors.append(task["id"])
    return successors


def ordered_unique(values: list[str]) -> list[str]:
    seen = set()
    ordered = []
    for value in values:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def markdown_anchor_slug(value: str) -> str:
    lowered = value.strip().lower()
    cleaned = re.sub(r"[^\w\s-]", "", lowered)
    collapsed = re.sub(r"[\s]+", "-", cleaned)
    return collapsed.strip("-")


def split_ref(ref: str) -> tuple[str, str | None]:
    if "#" not in ref:
        return ref, None
    path, anchor = ref.split("#", 1)
    return path, anchor or None


def is_full_prd_ref(ref: str) -> bool:
    base_path, anchor = split_ref(ref)
    return Path(base_path).as_posix() == "docs/prd/approved-prd.md" and anchor is None


def load_optional_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def render_json(payload: dict) -> str:
    return json.dumps(payload, indent=2) + "\n"


def extract_markdown_anchor_slice(content: str, anchor: str) -> tuple[str, bool]:
    lines = content.splitlines()
    heading_pattern = re.compile(r"^(#{1,6})\s+(.*)$")
    start_index = None
    start_level = None

    for index, line in enumerate(lines):
        match = heading_pattern.match(line)
        if not match:
            continue
        heading_text = match.group(2).strip()
        if markdown_anchor_slug(heading_text) != anchor:
            continue
        start_index = index
        start_level = len(match.group(1))
        break

    if start_index is None or start_level is None:
        return content, False

    end_index = len(lines)
    for index in range(start_index + 1, len(lines)):
        match = heading_pattern.match(lines[index])
        if not match:
            continue
        if len(match.group(1)) <= start_level:
            end_index = index
            break

    slice_lines = lines[start_index:end_index]
    if not slice_lines:
        return content, False
    return "\n".join(slice_lines) + "\n", True


def resolve_ref_content(root: Path, ref: str, content_map: dict[str, str]) -> tuple[str, str, bool]:
    base_path, anchor = split_ref(ref)
    normalized_path = Path(base_path).as_posix()
    content = content_map.get(normalized_path)
    exists = True
    if content is None:
        content = load_optional_text(root / Path(base_path))
        exists = bool(content)

    if anchor and content:
        sliced, found = extract_markdown_anchor_slice(content, anchor)
        if found:
            return normalized_path, sliced, True
        return normalized_path, content, False

    return normalized_path, content, exists


def approx_tokens(byte_count: int) -> int:
    if byte_count <= 0:
        return 0
    return math.ceil(byte_count / 4)


def build_budget_path(
    root: Path,
    refs: list[str],
    content_map: dict[str, str],
) -> dict:
    entries = []
    for ref in refs:
        normalized_path, content, anchor_found = resolve_ref_content(root, ref, content_map)
        byte_count = len(content.encode("utf-8"))
        base_path, anchor = split_ref(ref)
        entry = {
            "path": ref,
            "source_path": Path(base_path).as_posix(),
            "scope": "anchor" if anchor else "file",
            "bytes": byte_count,
            "approx_tokens": approx_tokens(byte_count),
            "anchor_found": anchor_found if anchor else True,
        }
        if anchor:
            entry["anchor"] = anchor
        if normalized_path != entry["source_path"]:
            entry["normalized_source_path"] = normalized_path
        entries.append(entry)

    total_bytes = sum(item["bytes"] for item in entries)
    total_tokens = sum(item["approx_tokens"] for item in entries)
    return {
        "file_count": len(entries),
        "bytes_total": total_bytes,
        "approx_tokens_total": total_tokens,
        "refs": entries,
    }


def is_structural_warning(warning: str) -> bool:
    lowered = warning.lower()
    return any(
        marker in lowered
        for marker in (
            "multiple ready tasks",
            "conflict",
            "missing anchor",
            "anchor not found",
            "no current task",
            "structural ambiguity",
        )
    )


def build_context_gate(
    root: Path,
    snapshot: dict,
    active_context: dict,
    content_map: dict[str, str],
) -> dict:
    active_path = build_budget_path(root, list(active_context.get("files_to_read", [])), content_map)
    warnings = list(snapshot.get("warnings", []))
    structural_warnings = [item for item in warnings if is_structural_warning(item)]
    operational_warnings = [item for item in warnings if item not in structural_warnings]
    has_conflicts = any(task.get("status") == "conflict" for task in snapshot["tasks"])
    has_review_or_blocker_state = any(
        task.get("status") in {"needs_review", "blocked"} for task in snapshot["tasks"]
    )
    missing_doc_anchor = any(
        item.get("scope") == "anchor" and not item.get("anchor_found", True)
        for item in active_path.get("refs", [])
    )
    lacks_targeted_doc_refs = not any(
        not is_full_prd_ref(ref) for ref in active_context.get("doc_refs", [])
    )
    lacks_acceptance = not active_context.get("acceptance_criteria")
    needs_full_prd = (
        lacks_targeted_doc_refs
        and lacks_acceptance
        and (root / "docs" / "prd" / "approved-prd.md").exists()
    )

    recommended_context_level = "active_only"
    escalation_reasons = []

    if needs_full_prd:
        recommended_context_level = "prd_required"
        escalation_reasons.append(
            "No targeted doc ref or acceptance criteria could resolve the current task safely."
        )
    elif missing_doc_anchor or has_conflicts or structural_warnings:
        recommended_context_level = "snapshot_required"
        if missing_doc_anchor:
            escalation_reasons.append(
                "A targeted checklist or markdown anchor could not be resolved from the active slice."
            )
        if has_conflicts:
            escalation_reasons.append(
                "At least one task is in conflict status, so the active slice is not structurally sufficient."
            )
        if structural_warnings:
            escalation_reasons.extend(structural_warnings[:3])
    elif has_review_or_blocker_state or operational_warnings:
        recommended_context_level = "active_plus_history"
        if has_review_or_blocker_state:
            escalation_reasons.append(
                "Review or blocker state exists, so recent lifecycle context may affect the next move."
            )
        if operational_warnings:
            escalation_reasons.extend(operational_warnings[:3])
    else:
        escalation_reasons.append(
            "Current task, dependencies, successors, and doc anchors are resolved in the active slice."
        )

    base_reads = list(active_context.get("files_to_read", []))
    if recommended_context_level == "active_only":
        recommended_files = list(base_reads)
        stop_reading_after = "active-context path"
        next_allowed_reads = [".codex/context/session-delta.md"]
    elif recommended_context_level == "active_plus_history":
        recommended_files = ordered_unique(
            [
                *base_reads,
                ".codex/context/session-delta.md",
                ".codex/context/history-rollup.md",
            ]
        )
        stop_reading_after = ".codex/context/history-rollup.md"
        next_allowed_reads = [".codex/context/latest-snapshot.json"]
    elif recommended_context_level == "snapshot_required":
        recommended_files = ordered_unique([*base_reads, ".codex/context/latest-snapshot.json"])
        stop_reading_after = ".codex/context/latest-snapshot.json"
        next_allowed_reads = ["docs/prd/approved-prd.md"]
    else:
        recommended_files = [
            ".codex/context/active-context.md",
            ".codex/context/latest-snapshot.json",
            "docs/prd/approved-prd.md",
        ]
        stop_reading_after = "docs/prd/approved-prd.md"
        next_allowed_reads = []

    recommended_path = build_budget_path(root, recommended_files, content_map)
    return {
        "recommended_context_level": recommended_context_level,
        "recommended_files_to_read": recommended_files,
        "stop_reading_after": stop_reading_after,
        "next_allowed_reads": next_allowed_reads,
        "escalation_reasons": escalation_reasons,
        "active_slice_sufficient": recommended_context_level == "active_only",
        "gate_flags": {
            "missing_doc_anchor": missing_doc_anchor,
            "has_conflicts": has_conflicts,
            "has_structural_warnings": bool(structural_warnings),
            "has_review_or_blocker_state": has_review_or_blocker_state,
            "needs_full_prd": needs_full_prd,
        },
        "recommended_path": recommended_path,
    }


def apply_context_gate(active_context: dict, context_gate: dict) -> dict:
    enriched = dict(active_context)
    enriched["recommended_context_level"] = context_gate["recommended_context_level"]
    enriched["recommended_files_to_read"] = list(context_gate["recommended_files_to_read"])
    enriched["stop_reading_after"] = context_gate["stop_reading_after"]
    enriched["next_allowed_reads"] = list(context_gate["next_allowed_reads"])
    enriched["escalation_reasons"] = list(context_gate["escalation_reasons"])
    enriched["active_slice_sufficient"] = context_gate["active_slice_sufficient"]
    enriched["gate_flags"] = dict(context_gate["gate_flags"])
    return enriched


def build_budget_report(
    root: Path,
    snapshot: dict,
    active_context: dict,
    content_map: dict[str, str],
    context_gate: dict | None = None,
) -> dict:
    active_refs = list(active_context.get("files_to_read", []))
    fallback_refs = ordered_unique(
        [*active_refs, *active_context.get("fallback_files_to_read", [])]
    )
    active_path = build_budget_path(root, active_refs, content_map)
    fallback_path = build_budget_path(root, fallback_refs, content_map)
    extra_bytes = max(0, fallback_path["bytes_total"] - active_path["bytes_total"])
    extra_tokens = max(
        0, fallback_path["approx_tokens_total"] - active_path["approx_tokens_total"]
    )
    extra_files = max(0, fallback_path["file_count"] - active_path["file_count"])
    reduction_percent = 0.0
    if fallback_path["bytes_total"] > 0:
        reduction_percent = round(
            (extra_bytes / fallback_path["bytes_total"]) * 100,
            2,
        )

    tasks = build_index(snapshot["tasks"])
    current_task = tasks.get(snapshot.get("current_task_id", ""), {})
    current_recommendation = None
    if context_gate:
        recommended_files = list(context_gate["recommended_files_to_read"])
        current_recommendation = {
            "recommended_context_level": context_gate["recommended_context_level"],
            "active_slice_sufficient": context_gate["active_slice_sufficient"],
            "recommended_files_to_read": recommended_files,
            "stop_reading_after": context_gate["stop_reading_after"],
            "next_allowed_reads": list(context_gate["next_allowed_reads"]),
            "escalation_reasons": list(context_gate["escalation_reasons"]),
            "recommended_path": build_budget_path(root, recommended_files, content_map),
        }
    return {
        "plan_id": snapshot["plan_id"],
        "generated_at": snapshot["generated_at"],
        "current_task_id": snapshot.get("current_task_id"),
        "current_task_title": current_task.get("title"),
        "active_context_path": active_path,
        "snapshot_heavy_fallback_path": fallback_path,
        "current_recommendation": current_recommendation,
        "comparison": {
            "extra_files_if_fallback_needed": extra_files,
            "extra_bytes_if_fallback_needed": extra_bytes,
            "approx_tokens_saved_when_active_slice_is_enough": extra_tokens,
            "reduction_percent_vs_snapshot_heavy_path": reduction_percent,
        },
        "notes": [
            "Approx tokens are estimated as ceil(bytes / 4).",
            "Markdown refs with #anchors count only the targeted section when the anchor is found.",
            "If the active-context path is sufficient, the fallback path does not need to be loaded.",
        ],
    }


def render_budget_report(report: dict) -> str:
    active_path = report["active_context_path"]
    fallback_path = report["snapshot_heavy_fallback_path"]
    comparison = report["comparison"]
    lines = [
        "# Budget Report",
        "",
        f"- Plan: {report.get('plan_id', 'unknown-plan')}",
        f"- Generated: {report.get('generated_at', 'unknown')}",
        f"- Current Task: {report.get('current_task_id', 'unknown')} {report.get('current_task_title', 'Unknown task')}",
        "- Purpose: Estimate the resume-context cost before widening the read set.",
        "",
    ]
    current_recommendation = report.get("current_recommendation")
    if current_recommendation:
        lines.extend(
            [
                "## Current Recommendation",
                f"- Recommended Context Level: {current_recommendation['recommended_context_level']}",
                f"- Active Slice Sufficient: {'yes' if current_recommendation['active_slice_sufficient'] else 'no'}",
                f"- Stop Reading After: {current_recommendation['stop_reading_after']}",
                f"- Recommended Bytes: {current_recommendation['recommended_path']['bytes_total']}",
                f"- Recommended Approx Tokens: {current_recommendation['recommended_path']['approx_tokens_total']}",
            ]
        )
        lines.extend(
            [
                f"- Read Now: {item}"
                for item in current_recommendation.get("recommended_files_to_read", [])
            ]
            or ["- Read Now: none"]
        )
        lines.extend(
            [
                f"- Next Allowed Read: {item}"
                for item in current_recommendation.get("next_allowed_reads", [])
            ]
            or ["- Next Allowed Read: none"]
        )
        lines.extend(
            [
                f"- Reason: {item}"
                for item in current_recommendation.get("escalation_reasons", [])
            ]
            or ["- Reason: none"]
        )
        lines.append("")
    lines.extend(
        [
            "## Active-Context Path",
            f"- File Count: {active_path['file_count']}",
            f"- Bytes: {active_path['bytes_total']}",
            f"- Approx Tokens: {active_path['approx_tokens_total']}",
        ]
    )
    lines.extend(
        [
            f"- {item['path']} ({item['bytes']} bytes, ~{item['approx_tokens']} tokens)"
            for item in active_path["refs"]
        ]
        or ["- none"]
    )

    lines.extend(
        [
            "",
            "## Snapshot-Heavy Fallback Path",
            f"- File Count: {fallback_path['file_count']}",
            f"- Bytes: {fallback_path['bytes_total']}",
            f"- Approx Tokens: {fallback_path['approx_tokens_total']}",
        ]
    )
    lines.extend(
        [
            f"- {item['path']} ({item['bytes']} bytes, ~{item['approx_tokens']} tokens)"
            for item in fallback_path["refs"]
        ]
        or ["- none"]
    )

    lines.extend(
        [
            "",
            "## Savings If Active Slice Is Enough",
            f"- Extra Files Avoided: {comparison['extra_files_if_fallback_needed']}",
            f"- Extra Bytes Avoided: {comparison['extra_bytes_if_fallback_needed']}",
            f"- Approx Tokens Saved: {comparison['approx_tokens_saved_when_active_slice_is_enough']}",
            f"- Reduction vs Snapshot-Heavy Path: {comparison['reduction_percent_vs_snapshot_heavy_path']}%",
            "",
            "## Notes",
        ]
    )
    lines.extend([f"- {item}" for item in report.get("notes", [])] or ["- none"])
    return "\n".join(lines)


def apply_current_task(snapshot: dict, task_id: str) -> dict:
    copied = {
        "plan_id": snapshot["plan_id"],
        "generated_at": snapshot["generated_at"],
        "current_task_id": task_id,
        "tasks": [],
        "warnings": list(snapshot.get("warnings", [])),
    }
    for task in snapshot["tasks"]:
        updated = dict(task)
        updated["current"] = task["id"] == task_id
        copied["tasks"].append(updated)
    return copied


def project_graph(snapshot: dict) -> dict:
    tasks = []
    for task in snapshot["tasks"]:
        tasks.append(
            {
                "id": task["id"],
                "title": task["title"],
                "status": task.get("status", "todo"),
                "depends_on": task.get("depends_on", []),
            }
        )
    return {
        "plan_id": snapshot["plan_id"],
        "tasks": tasks,
    }


def build_focus_set(snapshot: dict, root: Path, current_task_id: str) -> dict:
    tasks = snapshot["tasks"]
    index = build_index(tasks)
    active = index[current_task_id]
    checklist_path = root / "docs" / "implementation" / "checklist.md"
    prd_path = root / "docs" / "prd" / "approved-prd.md"
    if checklist_path.exists():
        doc_refs = [f"docs/implementation/checklist.md#{current_task_id.lower()}"]
    elif prd_path.exists():
        doc_refs = ["docs/prd/approved-prd.md"]
    else:
        doc_refs = []
    return {
        "current_task_id": current_task_id,
        "dependency_ids": list(active.get("depends_on", [])),
        "successor_ids": direct_successor_ids(tasks, current_task_id),
        "doc_refs": doc_refs,
    }


def task_stub(task: dict) -> dict:
    stub = {
        "id": task["id"],
        "title": task["title"],
        "status": task.get("status", "todo"),
        "last_updated_at": task.get("last_updated_at", "unknown"),
    }
    if task.get("review_reason"):
        stub["review_reason"] = task["review_reason"]
    if task.get("blocked_reason"):
        stub["blocked_reason"] = task["blocked_reason"]
    return stub


def session_delta_task_stub(task: dict) -> dict:
    stub = task_stub(task)
    evidence = list(task.get("evidence", []))
    if evidence:
        stub["evidence_count"] = len(evidence)
        stub["evidence_tail"] = evidence[-3:]
    return stub


def summarize_latest_event(event: dict | None) -> dict:
    if not event:
        return {}

    summary = {}
    for key in (
        "timestamp",
        "event",
        "current_task_id",
        "current_task_status",
        "updated_task_id",
        "updated_task_status",
        "requested_task_status",
        "current_task_selection",
        "tasks_loaded_count",
        "doc_refs_count",
        "full_prd_fallback",
        "warnings_count",
        "completion_status_downgraded",
        "downgrade_reason",
    ):
        if key in event and event[key] is not None:
            summary[key] = event[key]
    return summary


def build_session_delta(snapshot: dict, history_events: list[dict], limit: int = 3) -> dict:
    tasks = snapshot["tasks"]
    index = build_index(tasks)
    current_task_id = snapshot.get("current_task_id")
    current_task = index.get(current_task_id, {})
    latest_event = history_events[-1] if history_events else {}

    previous_current_task_id = None
    if len(history_events) >= 2:
        for event in reversed(history_events[:-1]):
            candidate = event.get("current_task_id")
            if candidate:
                previous_current_task_id = candidate
                break

    touched_task_ids = ordered_unique(
        [
            latest_event.get("updated_task_id", ""),
            latest_event.get("current_task_id", ""),
            current_task_id or "",
            *[
                task["id"]
                for task in sorted(
                    tasks,
                    key=lambda item: (item.get("last_updated_at", ""), item["id"]),
                    reverse=True,
                )
            ],
        ]
    )
    touched_task_ids = [task_id for task_id in touched_task_ids if task_id in index][:limit]
    touched_tasks = [session_delta_task_stub(index[task_id]) for task_id in touched_task_ids]

    focus_transition = None
    if previous_current_task_id and previous_current_task_id != current_task_id:
        focus_transition = {
            "from_task_id": previous_current_task_id,
            "to_task_id": current_task_id,
        }

    return {
        "plan_id": snapshot["plan_id"],
        "generated_at": snapshot["generated_at"],
        "current_task_id": current_task_id,
        "current_task_title": current_task.get("title"),
        "current_task_status": current_task.get("status"),
        "latest_event": summarize_latest_event(latest_event),
        "previous_current_task_id": previous_current_task_id,
        "focus_transition": focus_transition,
        "touched_task_ids": touched_task_ids,
        "touched_tasks": touched_tasks,
        "warning_count": len(snapshot.get("warnings", [])),
        "warnings": list(snapshot.get("warnings", []))[:3],
        "next_read": ".codex/context/history-rollup.md",
    }


def render_session_delta(session_delta: dict) -> str:
    latest_event = session_delta.get("latest_event", {})
    lines = [
        "# Session Delta",
        "",
        f"- Plan: {session_delta.get('plan_id', 'unknown-plan')}",
        f"- Generated: {session_delta.get('generated_at', 'unknown')}",
        f"- Current Task: {session_delta.get('current_task_id', 'unknown')} {session_delta.get('current_task_title', 'Unknown task')}",
        f"- Current Status: {session_delta.get('current_task_status', 'unknown')}",
        "- Purpose: Capture only the latest meaningful handoff before wider history is needed.",
        "",
        "## Latest Event",
    ]
    if latest_event:
        lines.extend(
            [
                f"- Timestamp: {latest_event.get('timestamp', 'unknown')}",
                f"- Event: {latest_event.get('event', 'unknown')}",
                f"- Event Current Task: {latest_event.get('current_task_id', 'unknown')}",
            ]
        )
        if latest_event.get("updated_task_id"):
            lines.append(
                f"- Updated Task: {latest_event['updated_task_id']} ({latest_event.get('updated_task_status', 'unknown')})"
            )
        if latest_event.get("current_task_selection"):
            lines.append(
                f"- Current Task Selection: {latest_event['current_task_selection']}"
            )
        if latest_event.get("downgrade_reason"):
            lines.append(f"- Downgrade Reason: {latest_event['downgrade_reason']}")
    else:
        lines.append("- none")

    lines.extend(["", "## Focus Transition"])
    focus_transition = session_delta.get("focus_transition")
    if focus_transition:
        lines.append(
            f"- {focus_transition['from_task_id']} -> {focus_transition['to_task_id']}"
        )
    else:
        lines.append("- unchanged")

    lines.extend(["", "## Recently Touched"])
    touched_tasks = session_delta.get("touched_tasks", [])
    if touched_tasks:
        for task in touched_tasks:
            evidence_tail = ", ".join(task.get("evidence_tail", []))
            suffix = f"; evidence: {evidence_tail}" if evidence_tail else ""
            lines.append(
                f"- {task['id']} {task['title']} ({task['status']}, {task['last_updated_at']}{suffix})"
            )
    else:
        lines.append("- none")

    warnings = session_delta.get("warnings", [])
    if warnings:
        lines.extend(["", "## Warnings"])
        lines.extend([f"- {item}" for item in warnings])

    lines.extend(
        ["", "## Next Read", f"- {session_delta.get('next_read', '.codex/context/history-rollup.md')}"]
    )
    return "\n".join(lines)


def load_history_events(path: Path) -> list[dict]:
    if not path.exists():
        return []

    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        events.append(json.loads(stripped))
    return events


def build_status_counts(tasks: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for task in tasks:
        status = task.get("status", "todo")
        counts[status] = counts.get(status, 0) + 1
    return counts


def build_active_context(snapshot: dict, focus: dict) -> dict:
    current_task_id = focus["current_task_id"]
    index = build_index(snapshot["tasks"])
    if current_task_id not in index:
        raise KeyError(f"Task not found: {current_task_id}")

    active = index[current_task_id]
    doc_refs = list(focus.get("doc_refs", []))
    files_to_read = ordered_unique([".codex/context/active-context.md", *doc_refs])
    fallback_files = ordered_unique(
        [
            ".codex/context/session-delta.md",
            ".codex/context/history-rollup.md",
            ".codex/context/latest-snapshot.json",
            "docs/prd/approved-prd.md",
        ]
    )

    return {
        "plan_id": snapshot["plan_id"],
        "generated_at": snapshot["generated_at"],
        "current_task_id": current_task_id,
        "current_task_title": active["title"],
        "current_task_status": active.get("status", "todo"),
        "acceptance_criteria": list(active.get("acceptance_criteria", [])),
        "evidence": list(active.get("evidence", [])),
        "review_reason": active.get("review_reason"),
        "blocked_reason": active.get("blocked_reason"),
        "dependency_ids": list(focus.get("dependency_ids", [])),
        "successor_ids": list(focus.get("successor_ids", [])),
        "doc_refs": doc_refs,
        "files_to_read": files_to_read,
        "fallback_files_to_read": fallback_files,
        "warnings": list(snapshot.get("warnings", []))[:5],
    }


def render_active_context(active_context: dict) -> str:
    acceptance = active_context.get("acceptance_criteria", [])
    evidence = active_context.get("evidence", [])
    warnings = active_context.get("warnings", [])

    lines = [
        "# Active Context",
        "",
        f"- Plan: {active_context.get('plan_id', 'unknown-plan')}",
        "- Purpose: Start here before loading broader project history.",
        f"- Current Task: {active_context['current_task_id']} {active_context['current_task_title']}",
        f"- Status: {active_context.get('current_task_status', 'todo')}",
    ]
    if active_context.get("review_reason"):
        lines.append(f"- Review Reason: {active_context['review_reason']}")
    if active_context.get("blocked_reason"):
        lines.append(f"- Blocked Reason: {active_context['blocked_reason']}")

    lines.extend(["", "## Acceptance"])
    lines.extend([f"- {item}" for item in acceptance] or ["- none recorded"])

    lines.extend(["", "## Dependencies"])
    lines.extend([f"- {item}" for item in active_context.get("dependency_ids", [])] or ["- none"])

    lines.extend(["", "## Next Candidates"])
    lines.extend([f"- {item}" for item in active_context.get("successor_ids", [])] or ["- none"])

    lines.extend(["", "## Evidence"])
    lines.extend([f"- {item}" for item in evidence] or ["- none recorded"])

    lines.extend(["", "## Read First"])
    lines.extend([f"- {item}" for item in active_context.get("files_to_read", [])] or ["- none"])

    if active_context.get("recommended_context_level"):
        lines.extend(["", "## Context Gate"])
        lines.append(
            f"- Recommended Context Level: {active_context['recommended_context_level']}"
        )
        lines.append(
            f"- Active Slice Sufficient: {'yes' if active_context.get('active_slice_sufficient') else 'no'}"
        )
        lines.append(f"- Stop Reading After: {active_context['stop_reading_after']}")

        lines.extend(["", "## Read Now"])
        lines.extend(
            [f"- {item}" for item in active_context.get("recommended_files_to_read", [])]
            or ["- none"]
        )

        lines.extend(["", "## Next Allowed Reads"])
        lines.extend(
            [f"- {item}" for item in active_context.get("next_allowed_reads", [])]
            or ["- none"]
        )

        lines.extend(["", "## Escalation Reasons"])
        lines.extend(
            [f"- {item}" for item in active_context.get("escalation_reasons", [])]
            or ["- none"]
        )

    lines.extend(["", "## Fallback Reads"])
    lines.extend(
        [f"- {item}" for item in active_context.get("fallback_files_to_read", [])] or ["- none"]
    )

    if warnings:
        lines.extend(["", "## Warnings"])
        lines.extend([f"- {item}" for item in warnings])

    return "\n".join(lines)


def build_history_rollup(snapshot: dict, history_events: list[dict], limit: int = 8) -> dict:
    tasks = snapshot["tasks"]
    by_updated = sorted(
        tasks,
        key=lambda task: (task.get("last_updated_at", ""), task["id"]),
        reverse=True,
    )
    recent_completed = [task_stub(task) for task in by_updated if task.get("status") == "done"][:limit]
    blocked = [task_stub(task) for task in by_updated if task.get("status") == "blocked"][:limit]
    needs_review = [
        task_stub(task) for task in by_updated if task.get("status") == "needs_review"
    ][:limit]

    return {
        "plan_id": snapshot["plan_id"],
        "generated_at": snapshot["generated_at"],
        "current_task_id": snapshot.get("current_task_id"),
        "status_counts": build_status_counts(tasks),
        "recent_completed_tasks": recent_completed,
        "recent_completed_task_ids": [task["id"] for task in recent_completed],
        "blocked_tasks": blocked,
        "blocked_task_ids": [task["id"] for task in blocked],
        "needs_review_tasks": needs_review,
        "needs_review_task_ids": [task["id"] for task in needs_review],
        "warning_count": len(snapshot.get("warnings", [])),
        "warnings": list(snapshot.get("warnings", []))[:8],
        "recent_events": history_events[-limit:],
    }


def render_history_rollup(history_rollup: dict) -> str:
    lines = [
        "# History Rollup",
        "",
        f"- Plan: {history_rollup.get('plan_id', 'unknown-plan')}",
        f"- Generated: {history_rollup.get('generated_at', 'unknown')}",
        f"- Current Task: {history_rollup.get('current_task_id', 'unknown')}",
        "",
        "## Status Counts",
    ]
    status_counts = history_rollup.get("status_counts", {})
    for status in sorted(status_counts):
        lines.append(f"- {status}: {status_counts[status]}")

    lines.extend(["", "## Recently Completed"])
    recent_completed = history_rollup.get("recent_completed_tasks", [])
    lines.extend(
        [
            f"- {task['id']} {task['title']} ({task['last_updated_at']})"
            for task in recent_completed
        ]
        or ["- none"]
    )

    lines.extend(["", "## Needs Review"])
    needs_review = history_rollup.get("needs_review_tasks", [])
    lines.extend(
        [
            f"- {task['id']} {task['title']} ({task.get('review_reason', task['status'])})"
            for task in needs_review
        ]
        or ["- none"]
    )

    lines.extend(["", "## Blocked"])
    blocked = history_rollup.get("blocked_tasks", [])
    lines.extend(
        [
            f"- {task['id']} {task['title']} ({task.get('blocked_reason', task['status'])})"
            for task in blocked
        ]
        or ["- none"]
    )

    lines.extend(["", "## Recent Events"])
    recent_events = history_rollup.get("recent_events", [])
    lines.extend(
        [
            f"- {event.get('timestamp', 'unknown')} {event.get('event', 'unknown')} -> {event.get('current_task_id', 'unknown')}"
            for event in recent_events
        ]
        or ["- none"]
    )

    warnings = history_rollup.get("warnings", [])
    if warnings:
        lines.extend(["", "## Warnings"])
        lines.extend([f"- {item}" for item in warnings])

    return "\n".join(lines)


def script_command(script_name: str) -> str:
    return f'python "{SCRIPTS_DIR / script_name}" --root .'


def render_local_playbook() -> str:
    lines = [
        "# Context Governor Playbook",
        "",
        "Keep human-readable planning files in `docs/implementation/` and machine state in `.codex/context/`.",
        "Treat `.codex/context/latest-snapshot.json` as the settlement point before starting or ending a session.",
        "",
        "## Daily Loop",
        f"1. Before work, run `{script_command('resume_context_governor.py')}`.",
        "2. Start from `.codex/context/active-context.md`, check `.codex/context/resume-manifest.json`, then copy `.codex/context/next-session-prompt.md` into the next Codex session.",
        "3. In `.codex/context/active-context.md`, obey the `Context Gate`: read `Read Now`, stop at `Stop Reading After`, and widen only through `Next Allowed Reads`.",
        f"4. After rewriting `docs/implementation/checklist.md`, run `{script_command('settle_checklist_context_governor.py')}`.",
        f"5. After a task changes status, run `{script_command('sync_progress_context_governor.py')} --task T-001 --status done --evidence shipped-checklist`.",
        f"6. Before stopping, run `{script_command('closeout_context_governor.py')}`.",
        "",
        "## Files To Trust First",
        "- `.codex/context/active-context.md`",
        "- `.codex/context/resume-manifest.json` (resume-only observability output; refreshed by `resume_context_governor.py`)",
        "- `.codex/context/session-delta.md`",
        "- `.codex/context/history-rollup.md`",
        "- `.codex/context/budget-report.md`",
        "- `.codex/context/latest-snapshot.json` (settled fallback)",
        "- `.codex/context/resume-pack.md` (auxiliary current-task recap)",
        "- `.codex/context/next-session-prompt.md`",
        "- `docs/implementation/checklist.md`",
        "- `docs/implementation/current-graph.mmd`",
        "",
        "## Reset Or Bootstrap",
        f"- First run: `{script_command('init_context_governor.py')}`",
        f"- Replace generated starters: `{script_command('init_context_governor.py')} --overwrite`",
        f"- Re-settle a rewritten checklist: `{script_command('settle_checklist_context_governor.py')}`",
        "",
        "## Minimal Resume Order",
        "- Start with `.codex/context/active-context.md`.",
        "- Use `.codex/context/resume-manifest.json` to inspect `recommended_files_to_read`, the current context level, and the next widening step.",
        "- In the `Context Gate`, read `Read Now`, stop at `Stop Reading After`, and widen only through `Next Allowed Reads`.",
        "- Treat `.codex/context/session-delta.md` as the first widening step.",
        "- Read `.codex/context/history-rollup.md` only after `.codex/context/session-delta.md` when broader recent history still matters.",
        "- Check `.codex/context/budget-report.md` before widening to `.codex/context/latest-snapshot.json`.",
        "- Read `.codex/context/latest-snapshot.json` only when the active slice is insufficient or structurally ambiguous.",
        "- Use `.codex/context/resume-pack.md` only as an auxiliary current-task recap, not as part of the primary widening ladder.",
        "",
        "## Working Rule",
        "- Do not re-paste the full PRD unless the narrow context cannot answer the current task safely.",
        "- If you changed task structure in the checklist, settle the checklist before syncing individual task progress.",
        "- When you finish or block a task, update the hidden state with evidence and refresh the settled outputs.",
        "- Keep task IDs stable so the checklist, graph, and snapshot keep pointing to the same work item.",
        "- Check `.codex/context/budget-report.md` when you want to quantify how much resume context the narrow path is saving.",
        "- Check `.codex/context/sync-history.ndjson` when you need the append-only trail of resume, sync, and closeout events.",
        "",
    ]
    return "\n".join(lines)


def render_conditional_policy_line(
    recommended_files: list[str],
    path: str,
    required_line: str,
    restrictive_line: str,
) -> str:
    if path in recommended_files:
        return required_line
    return restrictive_line


def render_next_session_prompt(
    snapshot: dict,
    current_task_id: str,
    doc_refs: list[str] | None = None,
    context_gate: dict | None = None,
) -> str:
    tasks = snapshot["tasks"]
    index = build_index(tasks)
    if current_task_id not in index:
        raise KeyError(f"Task not found: {current_task_id}")

    active = index[current_task_id]
    dependency_ids = list(active.get("depends_on", []))
    successor_ids = direct_successor_ids(tasks, current_task_id)
    files_to_read = ordered_unique([".codex/context/active-context.md", *(doc_refs or [])])
    fallback_files = ordered_unique(
        [
            ".codex/context/session-delta.md",
            ".codex/context/history-rollup.md",
            ".codex/context/latest-snapshot.json",
            "docs/prd/approved-prd.md",
        ]
    )
    recommended_files = files_to_read
    stop_reading_after = "active-context path"
    next_allowed_reads = [".codex/context/session-delta.md"]
    escalation_reasons = [
        "Current task, dependencies, successors, and doc anchors are resolved in the active slice."
    ]
    if context_gate:
        recommended_files = list(context_gate.get("recommended_files_to_read", files_to_read))
        stop_reading_after = context_gate.get("stop_reading_after", stop_reading_after)
        next_allowed_reads = list(context_gate.get("next_allowed_reads", next_allowed_reads))
        escalation_reasons = list(context_gate.get("escalation_reasons", escalation_reasons))

    snapshot_policy_line = render_conditional_policy_line(
        recommended_files,
        ".codex/context/latest-snapshot.json",
        "- Read .codex/context/latest-snapshot.json now because this task already requires the settled project structure.",
        "- Do not read .codex/context/latest-snapshot.json unless the active slice has missing anchors, conflicts, or structural warnings.",
    )
    prd_policy_line = render_conditional_policy_line(
        recommended_files,
        "docs/prd/approved-prd.md",
        "- Read docs/prd/approved-prd.md now because this task already requires the source requirement text.",
        "- Do not read docs/prd/approved-prd.md unless latest-snapshot.json still cannot resolve the referenced requirement safely.",
    )

    file_lines = [f"- {item}" for item in recommended_files] or ["- none"]
    fallback_lines = [
        f"- {item}" for item in fallback_files if item not in recommended_files
    ] or ["- none"]

    lines = [
        "# Next Session Prompt",
        "",
        f"Run this first: `{script_command('resume_context_governor.py')}`",
        "",
        "## Copy-Ready Prompt",
        "```text",
        "Use $context-governor to resume this project from .codex/context/active-context.md.",
        "",
        "Start with the smallest safe context:",
        f"- Current task: {current_task_id} {active['title']}",
        f"- Status: {active.get('status', 'todo')}",
        f"- Direct dependencies: {', '.join(dependency_ids) or 'none'}",
        f"- Direct successors: {', '.join(successor_ids) or 'none'}",
        "",
        "Read only these files now:",
        *file_lines,
        "",
        f"Stop after: {stop_reading_after}",
        "",
        "Current escalation reasons:",
        *([f"- {item}" for item in escalation_reasons] or ["- none"]),
        "",
        "Next allowed reads if this still is not enough:",
        *([f"- {item}" for item in next_allowed_reads] or ["- none"]),
        "",
        "Escalation policy:",
        "- Read .codex/context/session-delta.md when you need the smallest recent-change handoff from the previous session.",
        "- Read .codex/context/history-rollup.md only when blockers, needs_review state, or recent events affect the current task.",
        snapshot_policy_line,
        prd_policy_line,
        "",
        "Only if the active slice is insufficient, expand to:",
        *fallback_lines,
        "",
        "After reviewing the narrow context, continue from the current task,",
        "tell me which checklist item and graph node changed, and sync only the",
        "tasks supported by evidence from this session.",
        "```",
        "",
    ]
    return "\n".join(lines)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not content.endswith("\n"):
        content += "\n"
    path.write_text(content, encoding="utf-8")


def append_history(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload) + "\n")


def refresh_outputs(
    root: Path,
    current_task_id: str | None = None,
    event_name: str = "closeout",
    event_fields: dict | None = None,
) -> dict:
    context_dir = root / ".codex" / "context"
    docs_dir = root / "docs" / "implementation"

    doc_plan_path = context_dir / "doc-plan.json"
    state_path = context_dir / "latest-state.json"
    active_context_json_path = context_dir / "active-context.json"
    active_context_md_path = context_dir / "active-context.md"
    history_rollup_json_path = context_dir / "history-rollup.json"
    history_rollup_md_path = context_dir / "history-rollup.md"
    session_delta_json_path = context_dir / "session-delta.json"
    session_delta_md_path = context_dir / "session-delta.md"
    budget_report_json_path = context_dir / "budget-report.json"
    budget_report_md_path = context_dir / "budget-report.md"
    snapshot_path = context_dir / "latest-snapshot.json"
    graph_path = context_dir / "latest-task-graph.json"
    focus_path = context_dir / "focus-set.json"
    resume_path = context_dir / "resume-pack.md"
    history_path = context_dir / "sync-history.ndjson"
    checklist_path = docs_dir / "checklist.md"
    graph_render_path = docs_dir / "current-graph.mmd"
    next_session_prompt_path = context_dir / "next-session-prompt.md"

    doc_plan = load_json(doc_plan_path)
    state = load_json(state_path)
    snapshot = settle_snapshot(doc_plan, state)

    current_task_id = current_task_id or snapshot.get("current_task_id")
    index = build_index(snapshot["tasks"])
    if not current_task_id:
        raise KeyError("No current task available in snapshot")
    if current_task_id not in index:
        raise KeyError(f"Task not found: {current_task_id}")

    snapshot = apply_current_task(snapshot, current_task_id)
    graph = project_graph(snapshot)
    focus = build_focus_set(snapshot, root, current_task_id)
    active_context = build_active_context(snapshot, focus)
    active_context_markdown = render_active_context(active_context)
    resume_pack = render_resume_pack(snapshot, current_task_id)
    history_event = {
        "timestamp": now_utc(),
        "event": event_name,
        "plan_id": snapshot["plan_id"],
        "current_task_id": current_task_id,
        "current_task_status": index[current_task_id].get("status", "todo"),
        "warnings_count": len(snapshot.get("warnings", [])),
    }
    if event_fields:
        history_event.update(event_fields)
    history_events = load_history_events(history_path)
    combined_history_events = [*history_events, history_event]
    history_rollup = build_history_rollup(snapshot, combined_history_events)
    history_rollup_markdown = render_history_rollup(history_rollup)
    session_delta = build_session_delta(snapshot, combined_history_events)
    session_delta_markdown = render_session_delta(session_delta)
    checklist_markdown = render_checklist(doc_plan, snapshot)
    graph_markdown = render_mermaid(graph)
    content_map = {
        ".codex/context/active-context.md": active_context_markdown,
        ".codex/context/session-delta.md": session_delta_markdown,
        ".codex/context/history-rollup.md": history_rollup_markdown,
        ".codex/context/resume-pack.md": resume_pack,
        ".codex/context/latest-snapshot.json": render_json(snapshot),
        "docs/implementation/checklist.md": checklist_markdown,
        "docs/prd/approved-prd.md": load_optional_text(root / "docs" / "prd" / "approved-prd.md"),
    }
    context_gate = build_context_gate(root, snapshot, active_context, content_map)
    active_context = apply_context_gate(active_context, context_gate)
    active_context_markdown = render_active_context(active_context)
    content_map[".codex/context/active-context.md"] = active_context_markdown
    next_session_prompt = render_next_session_prompt(
        snapshot, current_task_id, focus.get("doc_refs", []), context_gate
    )
    budget_report = build_budget_report(root, snapshot, active_context, content_map, context_gate)
    budget_report_markdown = render_budget_report(budget_report)

    write_json(active_context_json_path, active_context)
    write_text(active_context_md_path, active_context_markdown)
    write_json(session_delta_json_path, session_delta)
    write_text(session_delta_md_path, session_delta_markdown)
    write_json(history_rollup_json_path, history_rollup)
    write_text(history_rollup_md_path, history_rollup_markdown)
    write_json(budget_report_json_path, budget_report)
    write_text(budget_report_md_path, budget_report_markdown)
    write_json(snapshot_path, snapshot)
    write_json(graph_path, graph)
    write_json(focus_path, focus)
    write_text(resume_path, resume_pack)
    write_text(next_session_prompt_path, next_session_prompt)
    write_text(checklist_path, checklist_markdown)
    write_text(graph_render_path, graph_markdown)
    append_history(history_path, history_event)

    return {
        "current_task_id": current_task_id,
        "snapshot": snapshot,
        "active_context_json_path": active_context_json_path,
        "active_context_md_path": active_context_md_path,
        "session_delta_json_path": session_delta_json_path,
        "session_delta_md_path": session_delta_md_path,
        "history_rollup_json_path": history_rollup_json_path,
        "history_rollup_md_path": history_rollup_md_path,
        "budget_report_json_path": budget_report_json_path,
        "budget_report_md_path": budget_report_md_path,
        "snapshot_path": snapshot_path,
        "graph_path": graph_path,
        "focus_path": focus_path,
        "resume_path": resume_path,
        "next_session_prompt_path": next_session_prompt_path,
        "checklist_path": checklist_path,
        "graph_render_path": graph_render_path,
        "history_path": history_path,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Refresh snapshot, graph, focus set, checklist, and resume pack after a work session."
    )
    parser.add_argument("--root", required=True, help="Project root using the recommended layout")
    parser.add_argument("--task", help="Optional current task override for the refreshed outputs")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    result = refresh_outputs(root, current_task_id=args.task)

    print(f"WRITE {result['snapshot_path']}")
    print(f"WRITE {result['graph_path']}")
    print(f"WRITE {result['focus_path']}")
    print(f"WRITE {result['active_context_json_path']}")
    print(f"WRITE {result['active_context_md_path']}")
    print(f"WRITE {result['session_delta_json_path']}")
    print(f"WRITE {result['session_delta_md_path']}")
    print(f"WRITE {result['history_rollup_json_path']}")
    print(f"WRITE {result['history_rollup_md_path']}")
    print(f"WRITE {result['budget_report_json_path']}")
    print(f"WRITE {result['budget_report_md_path']}")
    print(f"WRITE {result['resume_path']}")
    print(f"WRITE {result['next_session_prompt_path']}")
    print(f"WRITE {result['checklist_path']}")
    print(f"WRITE {result['graph_render_path']}")
    print(f"APPEND {result['history_path']}")
    print(f"READY {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
