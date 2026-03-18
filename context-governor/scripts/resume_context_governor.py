import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from closeout_context_governor import (
    apply_context_gate,
    apply_current_task,
    build_active_context,
    build_budget_report,
    build_context_gate,
    build_history_rollup,
    build_session_delta,
    load_history_events,
    load_optional_text,
    render_budget_report,
    render_json,
    render_active_context,
    render_history_rollup,
    render_next_session_prompt,
    render_session_delta,
)
from build_resume_pack import render_resume_pack


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


def derive_doc_refs(root: Path, focus_set: dict | None, task_id: str) -> list[str]:
    if focus_set and focus_set.get("current_task_id") == task_id and focus_set.get("doc_refs"):
        return list(focus_set["doc_refs"])

    checklist_path = root / "docs" / "implementation" / "checklist.md"
    prd_path = root / "docs" / "prd" / "approved-prd.md"
    if checklist_path.exists():
        return [f"docs/implementation/checklist.md#{task_id.lower()}"]
    if prd_path.exists():
        return ["docs/prd/approved-prd.md"]
    return []


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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Rebuild the smallest resume context from the latest snapshot."
    )
    parser.add_argument("--root", required=True, help="Project root using the recommended layout")
    parser.add_argument("--task", help="Optional current task override for the resume outputs")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    context_dir = root / ".codex" / "context"
    snapshot_path = context_dir / "latest-snapshot.json"
    focus_path = context_dir / "focus-set.json"
    active_context_json_path = context_dir / "active-context.json"
    active_context_md_path = context_dir / "active-context.md"
    history_rollup_json_path = context_dir / "history-rollup.json"
    history_rollup_md_path = context_dir / "history-rollup.md"
    session_delta_json_path = context_dir / "session-delta.json"
    session_delta_md_path = context_dir / "session-delta.md"
    budget_report_json_path = context_dir / "budget-report.json"
    budget_report_md_path = context_dir / "budget-report.md"
    resume_path = context_dir / "resume-pack.md"
    manifest_path = context_dir / "resume-manifest.json"
    history_path = context_dir / "sync-history.ndjson"
    next_session_prompt_path = context_dir / "next-session-prompt.md"

    snapshot = load_json(snapshot_path)
    stored_focus = load_json(focus_path) if focus_path.exists() else None

    current_task_id = args.task or snapshot.get("current_task_id")
    resume_snapshot = apply_current_task(snapshot, current_task_id) if current_task_id else snapshot
    tasks = resume_snapshot["tasks"]
    index = build_index(tasks)

    if not current_task_id:
        raise KeyError("No current task available in snapshot")
    if current_task_id not in index:
        raise KeyError(f"Task not found: {current_task_id}")

    active = index[current_task_id]
    dependency_ids = list(active.get("depends_on", []))
    successor_ids = direct_successor_ids(tasks, current_task_id)
    doc_refs = derive_doc_refs(root, stored_focus, current_task_id)
    focus_set = {
        "current_task_id": current_task_id,
        "dependency_ids": dependency_ids,
        "successor_ids": successor_ids,
        "doc_refs": doc_refs,
    }
    loaded_task_ids = ordered_unique([current_task_id, *dependency_ids, *successor_ids])
    resume_pack = render_resume_pack(resume_snapshot, current_task_id)
    active_context = build_active_context(resume_snapshot, focus_set)
    active_context_markdown = render_active_context(active_context)
    files_to_read = list(active_context["files_to_read"])
    fallback_files_to_read = list(active_context["fallback_files_to_read"])
    full_prd_fallback = any(ref.startswith("docs/prd/approved-prd.md") for ref in doc_refs)
    history_event = {
        "timestamp": now_utc(),
        "event": "resume",
        "plan_id": resume_snapshot["plan_id"],
        "current_task_id": current_task_id,
        "current_task_status": active.get("status", "todo"),
        "tasks_loaded_count": len(loaded_task_ids),
        "doc_refs_count": len(doc_refs),
        "full_prd_fallback": full_prd_fallback,
    }
    history_events = load_history_events(history_path)
    combined_history_events = [*history_events, history_event]
    history_rollup = build_history_rollup(resume_snapshot, combined_history_events)
    history_rollup_markdown = render_history_rollup(history_rollup)
    session_delta = build_session_delta(resume_snapshot, combined_history_events)
    session_delta_markdown = render_session_delta(session_delta)
    content_map = {
        ".codex/context/active-context.md": active_context_markdown,
        ".codex/context/session-delta.md": session_delta_markdown,
        ".codex/context/history-rollup.md": history_rollup_markdown,
        ".codex/context/resume-pack.md": resume_pack,
        ".codex/context/latest-snapshot.json": render_json(resume_snapshot),
        "docs/implementation/checklist.md": load_optional_text(
            root / "docs" / "implementation" / "checklist.md"
        ),
        "docs/prd/approved-prd.md": load_optional_text(root / "docs" / "prd" / "approved-prd.md"),
    }
    context_gate = build_context_gate(root, resume_snapshot, active_context, content_map)
    active_context = apply_context_gate(active_context, context_gate)
    active_context_markdown = render_active_context(active_context)
    content_map[".codex/context/active-context.md"] = active_context_markdown
    budget_report = build_budget_report(
        root, resume_snapshot, active_context, content_map, context_gate
    )
    budget_report_markdown = render_budget_report(budget_report)
    manifest = {
        "plan_id": resume_snapshot["plan_id"],
        "snapshot_generated_at": resume_snapshot.get("generated_at"),
        "current_task_id": current_task_id,
        "current_task_title": active["title"],
        "loaded_task_ids": loaded_task_ids,
        "dependency_ids": dependency_ids,
        "successor_ids": successor_ids,
        "doc_refs": doc_refs,
        "files_to_read": files_to_read,
        "fallback_files_to_read": fallback_files_to_read,
        "recommended_context_level": context_gate["recommended_context_level"],
        "recommended_files_to_read": list(context_gate["recommended_files_to_read"]),
        "stop_reading_after": context_gate["stop_reading_after"],
        "next_allowed_reads": list(context_gate["next_allowed_reads"]),
        "escalation_reasons": list(context_gate["escalation_reasons"]),
        "full_prd_fallback": full_prd_fallback,
        "tasks_loaded_count": len(loaded_task_ids),
        "doc_refs_count": len(doc_refs),
        "active_context_bytes": len(active_context_markdown.encode("utf-8")),
        "session_delta_bytes": len(session_delta_markdown.encode("utf-8")),
        "history_rollup_bytes": len(history_rollup_markdown.encode("utf-8")),
        "resume_pack_bytes": len(resume_pack.encode("utf-8")),
        "warnings_count": len(resume_snapshot.get("warnings", [])),
    }

    write_json(focus_path, focus_set)
    write_json(active_context_json_path, active_context)
    write_text(active_context_md_path, active_context_markdown)
    write_json(session_delta_json_path, session_delta)
    write_text(session_delta_md_path, session_delta_markdown)
    write_json(history_rollup_json_path, history_rollup)
    write_text(history_rollup_md_path, history_rollup_markdown)
    write_json(budget_report_json_path, budget_report)
    write_text(budget_report_md_path, budget_report_markdown)
    write_text(resume_path, resume_pack)
    write_text(
        next_session_prompt_path,
        render_next_session_prompt(resume_snapshot, current_task_id, doc_refs, context_gate),
    )
    write_json(manifest_path, manifest)
    append_history(history_path, history_event)

    print(f"WRITE {focus_path}")
    print(f"WRITE {active_context_json_path}")
    print(f"WRITE {active_context_md_path}")
    print(f"WRITE {session_delta_json_path}")
    print(f"WRITE {session_delta_md_path}")
    print(f"WRITE {history_rollup_json_path}")
    print(f"WRITE {history_rollup_md_path}")
    print(f"WRITE {budget_report_json_path}")
    print(f"WRITE {budget_report_md_path}")
    print(f"WRITE {resume_path}")
    print(f"WRITE {next_session_prompt_path}")
    print(f"WRITE {manifest_path}")
    print(f"APPEND {history_path}")
    print(f"FOCUS {current_task_id}")
    print(f"LOAD_COUNT {len(loaded_task_ids)}")
    print(f"DOC_REFS {len(doc_refs)}")
    print(f"PRD_FALLBACK {'yes' if full_prd_fallback else 'no'}")
    for ref in files_to_read:
        print(f"LOAD {ref}")
    print(f"READY {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
