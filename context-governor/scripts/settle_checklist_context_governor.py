import argparse
from pathlib import Path

from closeout_context_governor import now_utc, refresh_outputs, write_json


ALLOWED_STATUSES = {
    "todo",
    "in_progress",
    "done",
    "blocked",
    "needs_review",
    "conflict",
}


def slugify(value: str) -> str:
    cleaned = []
    previous_dash = False
    for char in value.strip().lower():
        if char.isalnum():
            cleaned.append(char)
            previous_dash = False
            continue
        if not previous_dash:
            cleaned.append("-")
            previous_dash = True
    return "".join(cleaned).strip("-") or "project-plan"


def default_plan_title(root: Path) -> str:
    words = root.name.replace("-", " ").replace("_", " ").strip()
    return f"{words.title() or 'Project'} Plan"


def ordered_unique(values: list[str]) -> list[str]:
    seen = set()
    unique_values = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        unique_values.append(value)
    return unique_values


def split_csv(value: str) -> list[str]:
    if value.strip().lower() == "none":
        return []
    return ordered_unique([item.strip() for item in value.split(",") if item.strip()])


def build_index(tasks: list[dict]) -> dict[str, dict]:
    return {task["id"]: task for task in tasks}


def find_dependency_cycle(tasks: list[dict]) -> list[str]:
    index = build_index(tasks)
    visited = set()
    active = set()
    trail: list[str] = []

    def visit(task_id: str) -> list[str]:
        visited.add(task_id)
        active.add(task_id)
        trail.append(task_id)

        for dependency_id in index[task_id].get("depends_on", []):
            if dependency_id not in index:
                continue
            if dependency_id in active:
                cycle_start = trail.index(dependency_id)
                return [*trail[cycle_start:], dependency_id]
            if dependency_id in visited:
                continue
            cycle = visit(dependency_id)
            if cycle:
                return cycle

        active.remove(task_id)
        trail.pop()
        return []

    for task in tasks:
        task_id = task["id"]
        if task_id in visited:
            continue
        cycle = visit(task_id)
        if cycle:
            return cycle

    return []


def validate_task_structure(tasks: list[dict]) -> None:
    issues = []
    task_id_counts: dict[str, int] = {}

    for task in tasks:
        task_id = task["id"]
        task_id_counts[task_id] = task_id_counts.get(task_id, 0) + 1

    for task_id, count in task_id_counts.items():
        if count > 1:
            issues.append(f"Duplicate task ID: {task_id}")

    known_task_ids = set(task_id_counts)
    for task in tasks:
        task_id = task["id"]
        status = task.get("status", "todo")
        if status not in ALLOWED_STATUSES:
            issues.append(f"Invalid status: {task_id} uses unsupported status {status}")
        if "blocked_reason" in task and status != "blocked":
            issues.append(
                f"Invalid blocked reason: {task_id} uses Blocked Reason while status is {status}"
            )
        if "review_reason" in task and status != "needs_review":
            issues.append(
                f"Invalid review reason: {task_id} uses Review Reason while status is {status}"
            )
        for dependency_id in task.get("depends_on", []):
            if dependency_id == task_id:
                issues.append(f"Self dependency: {task_id} depends on itself")
                continue
            if dependency_id not in known_task_ids:
                issues.append(
                    f"Missing dependency target: {task_id} depends on unknown task {dependency_id}"
                )

    if not issues:
        cycle = find_dependency_cycle(tasks)
        if cycle:
            issues.append(f"Dependency cycle: {' -> '.join(cycle)}")

    if issues:
        rendered_issues = "\n".join(f"- {issue}" for issue in issues)
        raise ValueError(f"Checklist structure is invalid:\n{rendered_issues}")


def parse_checklist(content: str, root: Path) -> dict:
    lines = content.splitlines()
    title = default_plan_title(root)
    plan_id = slugify(root.name)
    tasks = []
    in_tasks = False
    current_task = None
    active_section = None

    for raw_line in lines:
        stripped = raw_line.strip()

        if stripped.startswith("# Implementation Checklist:"):
            title = stripped.partition(":")[2].strip() or title
            continue

        if not in_tasks:
            if stripped.startswith("- Plan ID:"):
                plan_id = stripped.partition(":")[2].strip() or plan_id
                continue
            if stripped == "## Tasks":
                in_tasks = True
                continue
            continue

        if stripped.startswith("### "):
            if current_task:
                tasks.append(current_task)
            current_task = {
                "id": stripped[4:].strip(),
                "title": "",
                "status": "todo",
                "phase": "planning",
                "depends_on": [],
                "confidence": "confirmed",
                "acceptance_criteria": [],
                "evidence": [],
                "current": False,
            }
            active_section = None
            continue

        if current_task is None:
            continue

        if raw_line.startswith("  - "):
            item = raw_line[4:].strip()
            if active_section == "acceptance_criteria":
                if item:
                    current_task["acceptance_criteria"].append(item)
            elif active_section == "evidence":
                if item and item.lower() != "none":
                    current_task["evidence"].append(item)
            continue

        if not stripped:
            active_section = None
            continue

        active_section = None

        if stripped.startswith("- Title:"):
            current_task["title"] = stripped.partition(":")[2].strip()
        elif stripped.startswith("- Status:"):
            current_task["status"] = stripped.partition(":")[2].strip() or "todo"
        elif stripped.startswith("- Phase:"):
            current_task["phase"] = stripped.partition(":")[2].strip() or "planning"
        elif stripped.startswith("- Depends On:"):
            current_task["depends_on"] = split_csv(stripped.partition(":")[2].strip())
        elif stripped.startswith("- Confidence:"):
            current_task["confidence"] = stripped.partition(":")[2].strip() or "confirmed"
        elif stripped.startswith("- Current:"):
            current_task["current"] = stripped.partition(":")[2].strip().lower() == "yes"
        elif stripped.startswith("- Blocked Reason:"):
            blocked_reason = stripped.partition(":")[2].strip()
            if blocked_reason:
                current_task["blocked_reason"] = blocked_reason
        elif stripped.startswith("- Review Reason:"):
            review_reason = stripped.partition(":")[2].strip()
            if review_reason:
                current_task["review_reason"] = review_reason
        elif stripped == "- Acceptance Criteria:":
            active_section = "acceptance_criteria"
        elif stripped == "- Evidence:":
            active_section = "evidence"

    if current_task:
        tasks.append(current_task)

    if not tasks:
        raise ValueError("Checklist does not contain any task sections")

    for task in tasks:
        if not task["id"]:
            raise ValueError("Checklist contains a task without an ID")
        if not task["title"]:
            raise ValueError(f"Checklist task {task['id']} is missing a title")

    validate_task_structure(tasks)

    return {
        "plan_id": plan_id,
        "title": title,
        "tasks": tasks,
    }


def direct_successor_ids(tasks: list[dict], task_id: str) -> list[str]:
    successors = []
    for task in tasks:
        if task_id in task.get("depends_on", []):
            successors.append(task["id"])
    return successors


def dependencies_done(task: dict, index: dict[str, dict]) -> bool:
    for dependency_id in task.get("depends_on", []):
        dependency = index.get(dependency_id)
        if not dependency or dependency.get("status") != "done":
            return False
    return True


def choose_current_task_id(tasks: list[dict]) -> str:
    index = build_index(tasks)
    explicit_current_ids = [task["id"] for task in tasks if task.get("current")]

    for task_id in explicit_current_ids:
        if index[task_id].get("status") != "done":
            return task_id

    ready_in_progress = [
        task["id"]
        for task in tasks
        if task.get("status") == "in_progress" and dependencies_done(task, index)
    ]
    if ready_in_progress:
        return ready_in_progress[0]

    ready_non_done = [
        task["id"]
        for task in tasks
        if task.get("status") != "done" and dependencies_done(task, index)
    ]
    if ready_non_done:
        return ready_non_done[0]

    return tasks[-1]["id"]


def build_doc_plan(parsed: dict) -> dict:
    return {
        "plan_id": parsed["plan_id"],
        "title": parsed["title"],
        "tasks": [
            {
                "id": task["id"],
                "title": task["title"],
                "phase": task.get("phase", "planning"),
                "status": task.get("status", "todo"),
                "depends_on": list(task.get("depends_on", [])),
                "acceptance_criteria": list(task.get("acceptance_criteria", [])),
                "confidence": task.get("confidence", "confirmed"),
            }
            for task in parsed["tasks"]
        ],
    }


def build_state(parsed: dict, timestamp: str) -> dict:
    current_task_id = choose_current_task_id(parsed["tasks"])
    tasks = []
    for task in parsed["tasks"]:
        state_task = {
            "id": task["id"],
            "status": task.get("status", "todo"),
            "evidence": list(task.get("evidence", [])),
            "current": task["id"] == current_task_id and task.get("status") != "done",
            "next": direct_successor_ids(parsed["tasks"], task["id"]),
            "last_updated_at": timestamp,
        }
        if "blocked_reason" in task:
            state_task["blocked_reason"] = task["blocked_reason"]
        if task.get("status") == "needs_review" and "review_reason" in task:
            state_task["review_reason"] = task["review_reason"]
        tasks.append(state_task)

    return {
        "generated_at": timestamp,
        "current_task_id": current_task_id,
        "tasks": tasks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Settle docs/implementation/checklist.md into hidden state, snapshot, graph, and resume outputs."
    )
    parser.add_argument("--root", required=True, help="Project root using the recommended layout")
    parser.add_argument(
        "--checklist",
        help="Optional checklist Markdown path. Defaults to docs/implementation/checklist.md under --root.",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    checklist_path = (
        Path(args.checklist).resolve()
        if args.checklist
        else root / "docs" / "implementation" / "checklist.md"
    )
    context_dir = root / ".codex" / "context"
    doc_plan_path = context_dir / "doc-plan.json"
    state_path = context_dir / "latest-state.json"

    parsed = parse_checklist(checklist_path.read_text(encoding="utf-8"), root)
    timestamp = now_utc()
    doc_plan = build_doc_plan(parsed)
    state = build_state(parsed, timestamp)

    write_json(doc_plan_path, doc_plan)
    write_json(state_path, state)

    explicit_current_count = sum(1 for task in parsed["tasks"] if task.get("current"))
    result = refresh_outputs(
        root,
        current_task_id=state["current_task_id"],
        event_name="settle_checklist",
        event_fields={
            "parsed_task_count": len(parsed["tasks"]),
            "explicit_current_count": explicit_current_count,
            "checklist_source": str(checklist_path.relative_to(root)),
        },
    )

    print(f"WRITE {doc_plan_path}")
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
    print(f"CURRENT {result['current_task_id']}")
    print(f"TASKS {len(parsed['tasks'])}")
    print(f"EXPLICIT_CURRENT {explicit_current_count}")
    print(f"READY {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
