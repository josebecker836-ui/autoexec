import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from closeout_context_governor import refresh_outputs, render_local_playbook
from settle_snapshot import settle_snapshot


ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"
DEFAULT_TASKS = [
    {
        "id": "T-001",
        "title": "Normalize the approved PRD into a doc plan",
        "phase": "planning",
        "status": "todo",
        "depends_on": [],
        "acceptance_criteria": [
            "Approved PRD linked in docs/prd/approved-prd.md",
            "Planning scope captured with stable task IDs",
        ],
        "confidence": "confirmed",
    },
    {
        "id": "T-002",
        "title": "Write the ordered implementation checklist",
        "phase": "planning",
        "status": "todo",
        "depends_on": ["T-001"],
        "acceptance_criteria": [
            "Checklist saved to docs/implementation/checklist.md",
            "Dependencies recorded with stable task IDs",
        ],
        "confidence": "confirmed",
    },
]


def now_utc() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return cleaned or "project-plan"


def default_plan_title(root: Path) -> str:
    words = re.sub(r"[-_]+", " ", root.name).strip()
    if not words:
        words = "Project"
    return f"{words.title()} Plan"


def load_json_template(name: str) -> dict:
    return json.loads((ASSETS_DIR / name).read_text(encoding="utf-8"))


def starter_doc_plan(plan_id: str, plan_title: str) -> dict:
    return {
        "plan_id": plan_id,
        "title": plan_title,
        "tasks": DEFAULT_TASKS,
    }


def starter_state(timestamp: str) -> dict:
    template = load_json_template("plan-state-template.json")
    template["generated_at"] = timestamp
    template["current_task_id"] = "T-001"
    template["tasks"] = [
        {
            "id": "T-001",
            "status": "todo",
            "evidence": [],
            "current": True,
            "next": ["T-002"],
            "last_updated_at": timestamp,
        },
        {
            "id": "T-002",
            "status": "todo",
            "evidence": [],
            "current": False,
            "next": [],
            "last_updated_at": timestamp,
        },
    ]
    return template


def render_prd(plan_title: str) -> str:
    lines = [
        f"# Approved PRD: {plan_title}",
        "",
        "Replace this starter text with the approved PRD before running plan-from-prd.",
        "",
        "## Problem",
        "- Describe the user or business problem.",
        "",
        "## Goals",
        "- List the intended outcomes.",
        "",
        "## Non-Goals",
        "- List what this project will not do.",
        "",
        "## Acceptance Criteria",
        "- Add the conditions that define success.",
        "",
    ]
    return "\n".join(lines)


def render_progress(snapshot: dict) -> str:
    current_task_id = snapshot.get("current_task_id", "unknown")
    current_title = "Unknown task"
    for task in snapshot.get("tasks", []):
        if task["id"] == current_task_id:
            current_title = task["title"]
            break

    lines = [
        "# Progress Log",
        "",
        f"- Snapshot: .codex/context/latest-snapshot.json",
        f"- Bootstrap Focus: {current_task_id} {current_title}",
        "- This file is an optional bootstrap and milestone log, not a live resume source.",
        "- For live resume context, trust .codex/context/active-context.md before widening further.",
        "- Update this file only when you need a human-readable milestone log.",
        "- Use $context-governor to sync progress and settle changes back into the canonical snapshot.",
        "",
        "## Session Notes",
        "- Initialization complete.",
        "",
    ]
    return "\n".join(lines)


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, content: str, overwrite: bool, actions: list[str], root: Path) -> None:
    ensure_parent(path)
    relative = path.relative_to(root)
    if path.exists() and not overwrite:
        actions.append(f"SKIP {relative}")
        return
    if not content.endswith("\n"):
        content += "\n"
    status = "OVERWRITE" if path.exists() else "CREATE"
    path.write_text(content, encoding="utf-8")
    actions.append(f"{status} {relative}")


def write_json(path: Path, payload: dict, overwrite: bool, actions: list[str], root: Path) -> None:
    write_text(
        path,
        json.dumps(payload, indent=2),
        overwrite=overwrite,
        actions=actions,
        root=root,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize starter files for context-governor.")
    parser.add_argument("--root", required=True, help="Project root to initialize")
    parser.add_argument("--plan-id", help="Override the generated plan ID")
    parser.add_argument("--plan-title", help="Override the generated plan title")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace generated files if they already exist",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    root.mkdir(parents=True, exist_ok=True)

    plan_id = args.plan_id or slugify(root.name)
    plan_title = args.plan_title or default_plan_title(root)
    timestamp = now_utc()

    doc_plan = starter_doc_plan(plan_id, plan_title)
    state = starter_state(timestamp)
    snapshot = settle_snapshot(doc_plan, state)

    outputs = {
        root / "docs" / "prd" / "approved-prd.md": render_prd(plan_title),
        root
        / "docs"
        / "implementation"
        / "context-governor-playbook.md": render_local_playbook(),
        root / "docs" / "implementation" / "progress.md": render_progress(snapshot),
    }
    json_outputs = {
        root / ".codex" / "context" / "doc-plan.json": doc_plan,
        root / ".codex" / "context" / "latest-state.json": state,
    }

    actions: list[str] = []
    for path, content in outputs.items():
        write_text(path, content, args.overwrite, actions, root)
    for path, payload in json_outputs.items():
        write_json(path, payload, args.overwrite, actions, root)

    result = refresh_outputs(
        root,
        current_task_id=state["current_task_id"],
        event_name="initialized",
    )

    for action in actions:
        print(action)
    print(f"WRITE {result['active_context_json_path'].relative_to(root)}")
    print(f"WRITE {result['active_context_md_path'].relative_to(root)}")
    print(f"WRITE {result['session_delta_json_path'].relative_to(root)}")
    print(f"WRITE {result['session_delta_md_path'].relative_to(root)}")
    print(f"WRITE {result['history_rollup_json_path'].relative_to(root)}")
    print(f"WRITE {result['history_rollup_md_path'].relative_to(root)}")
    print(f"WRITE {result['budget_report_json_path'].relative_to(root)}")
    print(f"WRITE {result['budget_report_md_path'].relative_to(root)}")
    print(f"WRITE {result['snapshot_path'].relative_to(root)}")
    print(f"WRITE {result['graph_path'].relative_to(root)}")
    print(f"WRITE {result['focus_path'].relative_to(root)}")
    print(f"WRITE {result['resume_path'].relative_to(root)}")
    print(f"WRITE {result['next_session_prompt_path'].relative_to(root)}")
    print(f"WRITE {result['checklist_path'].relative_to(root)}")
    print(f"WRITE {result['graph_render_path'].relative_to(root)}")
    print(f"APPEND {result['history_path'].relative_to(root)}")

    print(f"READY {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
