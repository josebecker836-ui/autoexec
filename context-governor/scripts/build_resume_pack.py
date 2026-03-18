import argparse
import json
from pathlib import Path


def build_index(tasks: list[dict]) -> dict[str, dict]:
    return {task["id"]: task for task in tasks}


def direct_successors(tasks: list[dict], task_id: str) -> list[dict]:
    return [task for task in tasks if task_id in task.get("depends_on", [])]


def bullet_lines(tasks: list[dict], fallback: str) -> list[str]:
    if not tasks:
        return [fallback]
    return [f"- {task['id']} {task['title']} ({task['status']})" for task in tasks]


def render_resume_pack(snapshot: dict, task_id: str) -> str:
    tasks = snapshot["tasks"]
    index = build_index(tasks)
    if task_id not in index:
        raise KeyError(f"Task not found: {task_id}")

    active = index[task_id]
    deps = []
    for dep in active.get("depends_on", []):
        if dep in index:
            deps.append(index[dep])
        else:
            deps.append(
                {
                    "id": dep,
                    "title": "Missing dependency",
                    "status": "conflict",
                }
            )
    next_tasks = direct_successors(tasks, task_id)
    acceptance = "; ".join(active.get("acceptance_criteria", [])) or "None recorded"
    evidence = active.get("evidence", [])
    review_reason = active.get("review_reason")
    blocked_reason = active.get("blocked_reason")

    lines = [
        f"# Resume Pack: {active['id']} {active['title']}",
        "",
        "## Use This File Carefully",
        "- Auxiliary only: start from `.codex/context/active-context.md` and obey its Context Gate first.",
        "- This file is a focused current-task recap, not part of the primary widening ladder.",
        "",
        "## Snapshot",
        f"- Plan: {snapshot.get('plan_id', 'unknown-plan')}",
        f"- Generated: {snapshot.get('generated_at', 'unknown')}",
        f"- Current Task: {task_id}",
        "",
        "## Current Task",
        f"- Status: {active.get('status', 'todo')}",
        f"- Acceptance: {acceptance}",
    ]
    if blocked_reason:
        lines.append(f"- Blocked Reason: {blocked_reason}")
    if review_reason:
        lines.append(f"- Review Reason: {review_reason}")
    lines.extend(["", "## Dependencies"])
    lines.extend(bullet_lines(deps, "- none No direct dependencies (n/a)"))
    lines.extend(["", "## Next Candidates"])
    lines.extend(bullet_lines(next_tasks, "- none No direct successors (n/a)"))
    lines.extend(["", "## Evidence"])
    lines.extend([f"- {item}" for item in evidence] or ["- none recorded"])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a minimal resume pack.")
    parser.add_argument("--snapshot", required=True, help="Canonical snapshot JSON path")
    parser.add_argument("--task", required=True, help="Task ID to focus on")
    parser.add_argument("--output", required=True, help="Output Markdown path")
    args = parser.parse_args()

    snapshot_path = Path(args.snapshot)
    output_path = Path(args.output)

    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        render_resume_pack(snapshot, args.task),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
