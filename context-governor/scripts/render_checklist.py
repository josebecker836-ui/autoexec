import argparse
import json
from pathlib import Path


def build_index(tasks: list[dict]) -> dict[str, dict]:
    return {task["id"]: task for task in tasks}


def merge_task(doc_task: dict, snapshot_task: dict | None) -> dict:
    merged = dict(doc_task)
    if snapshot_task:
        merged.update(snapshot_task)
    return merged


def render_checklist(doc_plan: dict, snapshot: dict) -> str:
    snapshot_index = build_index(snapshot.get("tasks", []))
    current_task_id = snapshot.get("current_task_id")

    lines = [
        f"# Implementation Checklist: {doc_plan['title']}",
        "",
        "## Metadata",
        f"- Plan ID: {doc_plan['plan_id']}",
        "- Snapshot: .codex/context/latest-snapshot.json",
        f"- Last Settled At: {snapshot.get('generated_at', 'unknown')}",
        "",
        "## Tasks",
        "",
    ]

    for doc_task in doc_plan.get("tasks", []):
        task = merge_task(doc_task, snapshot_index.get(doc_task["id"]))
        depends_on = ", ".join(task.get("depends_on", [])) or "none"
        evidence = task.get("evidence", [])

        lines.extend(
            [
                f"### {task['id']}",
                f"- Title: {task['title']}",
                f"- Status: {task.get('status', 'todo')}",
                f"- Phase: {task.get('phase', 'planning')}",
                f"- Depends On: {depends_on}",
                f"- Confidence: {task.get('confidence', 'confirmed')}",
            ]
        )

        if task["id"] == current_task_id:
            lines.append("- Current: yes")

        if "blocked_reason" in task:
            lines.append(f"- Blocked Reason: {task['blocked_reason']}")
        if "review_reason" in task:
            lines.append(f"- Review Reason: {task['review_reason']}")

        lines.append("- Acceptance Criteria:")
        for criterion in task.get("acceptance_criteria", []):
            lines.append(f"  - {criterion}")

        lines.append("- Evidence:")
        if evidence:
            for item in evidence:
                lines.append(f"  - {item}")
        else:
            lines.append("  - none")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render checklist markdown from a doc plan and snapshot.")
    parser.add_argument("--doc-plan", required=True, help="Normalized doc-plan JSON path")
    parser.add_argument("--snapshot", required=True, help="Settled snapshot JSON path")
    parser.add_argument("--output", required=True, help="Output checklist Markdown path")
    args = parser.parse_args()

    doc_plan_path = Path(args.doc_plan)
    snapshot_path = Path(args.snapshot)
    output_path = Path(args.output)

    doc_plan = json.loads(doc_plan_path.read_text(encoding="utf-8"))
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_checklist(doc_plan, snapshot) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
