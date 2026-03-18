import argparse
from pathlib import Path

from closeout_context_governor import load_json, now_utc, refresh_outputs, write_json
from settle_snapshot import completion_evidence_review_reason


ALLOWED_STATUSES = {
    "todo",
    "in_progress",
    "done",
    "blocked",
    "needs_review",
    "conflict",
}


def build_index(tasks: list[dict]) -> dict[str, dict]:
    return {task["id"]: task for task in tasks}


def direct_successor_ids(tasks: list[dict], task_id: str) -> list[str]:
    successors = []
    for task in tasks:
        if task_id in task.get("depends_on", []):
            successors.append(task["id"])
    return successors


def normalize_state(doc_plan: dict, state: dict, timestamp: str) -> dict:
    state_index = build_index(state.get("tasks", []))
    normalized_tasks = []

    for doc_task in doc_plan["tasks"]:
        state_task = dict(state_index.get(doc_task["id"], {}))
        normalized_task = {
            "id": doc_task["id"],
            "status": state_task.get("status", doc_task.get("status", "todo")),
            "evidence": list(state_task.get("evidence", [])),
            "current": state_task.get("current", False),
            "next": direct_successor_ids(doc_plan["tasks"], doc_task["id"]),
            "last_updated_at": state_task.get("last_updated_at", timestamp),
        }
        if normalized_task["status"] == "blocked" and "blocked_reason" in state_task:
            normalized_task["blocked_reason"] = state_task["blocked_reason"]
        if normalized_task["status"] == "needs_review" and "review_reason" in state_task:
            normalized_task["review_reason"] = state_task["review_reason"]
        normalized_tasks.append(normalized_task)

    state["tasks"] = normalized_tasks
    return state


def append_unique(existing: list[str], additions: list[str]) -> tuple[list[str], int]:
    merged = []
    seen = set()
    added_count = 0

    for item in [*existing, *additions]:
        if item in seen:
            continue
        seen.add(item)
        merged.append(item)
        if item in additions and item not in existing:
            added_count += 1

    return merged, added_count


def dependencies_done(task: dict, doc_index: dict[str, dict], state_index: dict[str, dict]) -> bool:
    for dep in doc_index[task["id"]].get("depends_on", []):
        dep_state = state_index.get(dep)
        if not dep_state or dep_state.get("status") != "done":
            return False
    return True


def choose_current_task_id(task_id: str, status: str, doc_plan: dict, state: dict) -> tuple[str, str]:
    if status != "done":
        return task_id, "touched-task"

    state_index = build_index(state["tasks"])
    doc_index = build_index(doc_plan["tasks"])
    ready_successors = []

    for successor_id in direct_successor_ids(doc_plan["tasks"], task_id):
        successor = state_index[successor_id]
        if successor.get("status") == "done":
            continue
        if dependencies_done(successor, doc_index, state_index):
            ready_successors.append(successor_id)

    if len(ready_successors) == 1:
        return ready_successors[0], "single-ready-successor"

    return task_id, "canonical-fallback"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync task progress into hidden state, checklist, graph, and snapshot."
    )
    parser.add_argument("--root", required=True, help="Project root using the recommended layout")
    parser.add_argument("--task", required=True, help="Task ID to update")
    parser.add_argument("--status", required=True, choices=sorted(ALLOWED_STATUSES))
    parser.add_argument(
        "--evidence",
        action="append",
        default=[],
        help="Evidence string to append. Repeat the flag to add multiple items.",
    )
    parser.add_argument(
        "--blocked-reason",
        help="Optional blocker text. Only valid with --status blocked.",
    )
    args = parser.parse_args()

    if args.blocked_reason and args.status != "blocked":
        raise ValueError("--blocked-reason can only be used with --status blocked")

    root = Path(args.root).resolve()
    context_dir = root / ".codex" / "context"
    doc_plan_path = context_dir / "doc-plan.json"
    state_path = context_dir / "latest-state.json"

    timestamp = now_utc()
    doc_plan = load_json(doc_plan_path)
    state = normalize_state(doc_plan, load_json(state_path), timestamp)
    state_index = build_index(state["tasks"])

    if args.task not in build_index(doc_plan["tasks"]):
        raise KeyError(f"Task not found in doc plan: {args.task}")
    if args.task not in state_index:
        raise KeyError(f"Task not found in state: {args.task}")

    task_state = state_index[args.task]
    task_state["evidence"], evidence_added_count = append_unique(
        task_state.get("evidence", []), args.evidence
    )
    task_state["last_updated_at"] = timestamp

    applied_status = args.status
    downgrade_reason = None
    if args.status == "done":
        downgrade_reason = completion_evidence_review_reason(task_state.get("evidence", []))
        if downgrade_reason:
            applied_status = "needs_review"

    task_state["status"] = applied_status

    if applied_status == "blocked":
        if args.blocked_reason:
            task_state["blocked_reason"] = args.blocked_reason
    else:
        task_state.pop("blocked_reason", None)

    if applied_status == "needs_review":
        if downgrade_reason:
            task_state["review_reason"] = downgrade_reason
    else:
        task_state.pop("review_reason", None)

    current_task_id, selection_mode = choose_current_task_id(
        args.task, applied_status, doc_plan, state
    )
    state["generated_at"] = timestamp
    state["current_task_id"] = current_task_id

    for item in state["tasks"]:
        item["current"] = item["id"] == current_task_id and item.get("status") != "done"

    write_json(state_path, state)

    result = refresh_outputs(
        root,
        current_task_id=None,
        event_name="sync_progress",
        event_fields={
            "updated_task_id": args.task,
            "requested_task_status": args.status,
            "updated_task_status": applied_status,
            "evidence_added_count": evidence_added_count,
            "blocked_reason_present": "blocked_reason" in task_state,
            "review_reason_present": "review_reason" in task_state,
            "current_task_selection": selection_mode,
            "completion_status_downgraded": applied_status != args.status,
            "downgrade_reason": downgrade_reason,
        },
    )

    print(f"WRITE {state_path}")
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
    print(f"TASK {args.task}")
    print(f"REQUESTED_STATUS {args.status}")
    print(f"STATUS {applied_status}")
    print(f"CURRENT {result['current_task_id']}")
    print(f"SELECTION {selection_mode}")
    print(f"EVIDENCE_ADDED {evidence_added_count}")
    if downgrade_reason:
        print(f"DOWNGRADED {downgrade_reason}")
    if "review_reason" in task_state:
        print(f"REVIEW_REASON {task_state['review_reason']}")
    print(f"READY {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
