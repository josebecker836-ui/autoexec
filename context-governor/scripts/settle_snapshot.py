import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


DOC_PRIORITY_FIELDS = {"title", "phase", "depends_on", "acceptance_criteria", "confidence"}
STATE_PRIORITY_FIELDS = {
    "status",
    "evidence",
    "blocked_reason",
    "review_reason",
    "current",
    "next",
    "last_updated_at",
}
WEAK_COMPLETION_EVIDENCE = {
    "",
    "draft",
    "n/a",
    "n a",
    "na",
    "needs review",
    "needs_review",
    "needs-review",
    "none",
    "partial",
    "pending",
    "placeholder",
    "review",
    "tbd",
    "todo",
    "unknown",
    "wip",
}


def now_utc() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def normalize_evidence_item(value: str) -> str:
    return " ".join(value.strip().lower().replace("-", " ").replace("_", " ").split())


def ordered_unique(values: list[str]) -> list[str]:
    seen = set()
    unique_values = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        unique_values.append(value)
    return unique_values


def completion_evidence_review_reason(evidence: list[str]) -> str | None:
    normalized = [normalize_evidence_item(item) for item in evidence if item.strip()]
    if not normalized:
        return "missing completion evidence"

    if any(item not in WEAK_COMPLETION_EVIDENCE for item in normalized):
        return None

    return "only placeholder completion evidence"


def settle_task(doc_task: dict, state_task: dict | None) -> tuple[dict, list[str]]:
    state_task = state_task or {}
    warnings = []
    structural_conflict = False

    for field in DOC_PRIORITY_FIELDS:
        if field in state_task and field in doc_task and state_task[field] != doc_task[field]:
            warnings.append(
                f"{doc_task['id']}: state attempted to override structural field '{field}'"
            )
            structural_conflict = True

    merged = {}
    for key in ("id", "title", "phase"):
        if key in doc_task:
            merged[key] = doc_task[key]

    merged["status"] = state_task.get("status", doc_task.get("status", "todo"))

    for key in ("depends_on", "acceptance_criteria", "confidence"):
        if key in doc_task:
            value = doc_task[key]
            if key == "depends_on":
                value = ordered_unique(list(value))
            merged[key] = value

    for key, value in doc_task.items():
        if key not in merged and key not in STATE_PRIORITY_FIELDS and key != "status":
            merged[key] = value

    merged["evidence"] = state_task.get("evidence", doc_task.get("evidence", []))
    if "blocked_reason" in state_task:
        merged["blocked_reason"] = state_task["blocked_reason"]
    if "review_reason" in state_task:
        merged["review_reason"] = state_task["review_reason"]
    merged["current"] = state_task.get("current", doc_task.get("current", False))
    merged["next"] = state_task.get("next", doc_task.get("next", []))
    merged["last_updated_at"] = state_task.get("last_updated_at", now_utc())

    review_reason = None
    review_warning = None
    if merged["status"] == "done":
        review_reason = completion_evidence_review_reason(merged["evidence"])
        if review_reason:
            review_warning = (
                f"{doc_task['id']}: downgraded from done to needs_review due to {review_reason}"
            )
    elif merged["status"] == "needs_review":
        review_reason = merged.get("review_reason") or completion_evidence_review_reason(
            merged["evidence"]
        )
        if review_reason:
            review_warning = f"{doc_task['id']}: needs_review due to {review_reason}"

    if review_warning:
        warnings.append(review_warning)

    if structural_conflict:
        merged["status"] = "conflict"
        merged.pop("blocked_reason", None)
        merged.pop("review_reason", None)
    elif review_reason:
        merged["status"] = "needs_review"
        merged.pop("blocked_reason", None)
        merged["review_reason"] = review_reason
    else:
        if merged["status"] != "blocked":
            merged.pop("blocked_reason", None)
        merged.pop("review_reason", None)

    return merged, warnings


def dependencies_done(task: dict, index: dict[str, dict]) -> bool:
    for dep in task.get("depends_on", []):
        if dep not in index:
            return False
        if index[dep]["status"] != "done":
            return False
    return True


def choose_current_task_id(tasks: list[dict], state: dict) -> tuple[str | None, list[str]]:
    index = {task["id"]: task for task in tasks}
    current_task_id = state.get("current_task_id")
    warnings = []
    if current_task_id in index and index[current_task_id]["status"] != "done":
        return current_task_id, warnings

    explicit_current_ids = [
        task["id"] for task in tasks if task.get("current") and task["status"] != "done"
    ]
    if len(explicit_current_ids) > 1:
        warnings.append(
            "Multiple non-done tasks were marked current; selected the first in plan order"
        )
    if explicit_current_ids:
        return explicit_current_ids[0], warnings

    ready_in_progress = [
        task["id"]
        for task in tasks
        if task["status"] == "in_progress" and dependencies_done(task, index)
    ]
    if len(ready_in_progress) > 1:
        warnings.append(
            "Multiple ready in-progress tasks found; selected the first in plan order"
        )
    if ready_in_progress:
        return ready_in_progress[0], warnings

    ready_todo = [
        task["id"]
        for task in tasks
        if task["status"] != "done" and dependencies_done(task, index)
    ]
    if len(ready_todo) > 1:
        warnings.append("Multiple ready tasks found; selected the first in plan order")
    if ready_todo:
        return ready_todo[0], warnings

    if current_task_id and current_task_id not in index:
        warnings.append(f"State referenced a missing current task '{current_task_id}'")

    return current_task_id, warnings


def settle_snapshot(doc_plan: dict, state: dict) -> dict:
    state_tasks = {task["id"]: task for task in state.get("tasks", [])}
    settled_tasks = []
    warnings = []

    for task in doc_plan["tasks"]:
        settled_task, task_warnings = settle_task(task, state_tasks.get(task["id"]))
        settled_tasks.append(settled_task)
        warnings.extend(task_warnings)

    current_task_id, selection_warnings = choose_current_task_id(settled_tasks, state)
    warnings.extend(selection_warnings)

    return {
        "plan_id": doc_plan["plan_id"],
        "generated_at": state.get("generated_at", now_utc()),
        "current_task_id": current_task_id,
        "tasks": settled_tasks,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Settle doc-plan and state into one snapshot.")
    parser.add_argument("--doc-plan", required=True, help="Normalized doc-plan JSON path")
    parser.add_argument("--state", required=True, help="Latest hidden state JSON path")
    parser.add_argument("--output", required=True, help="Output snapshot JSON path")
    args = parser.parse_args()

    doc_plan_path = Path(args.doc_plan)
    state_path = Path(args.state)
    output_path = Path(args.output)

    doc_plan = json.loads(doc_plan_path.read_text(encoding="utf-8"))
    state = json.loads(state_path.read_text(encoding="utf-8"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(settle_snapshot(doc_plan, state), indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
