import argparse
import json
from pathlib import Path


STATUS_CLASS = {
    "todo": "todo",
    "in_progress": "active",
    "done": "done",
    "blocked": "blocked",
    "needs_review": "review",
    "conflict": "conflict",
}


def render_mermaid(graph: dict) -> str:
    lines = ["flowchart TD"]
    for task in graph["tasks"]:
        task_id = task["id"]
        title = task["title"].replace('"', "'")
        status = STATUS_CLASS.get(task.get("status", "todo"), "todo")
        lines.append(f'    {task_id}["{task_id}: {title}"]:::{status}')
        for dep in task.get("depends_on", []):
            lines.append(f"    {dep} --> {task_id}")
    lines.extend(
        [
            "    classDef todo fill:#f3f4f6,stroke:#6b7280,color:#111827;",
            "    classDef active fill:#dbeafe,stroke:#2563eb,color:#1e3a8a;",
            "    classDef done fill:#dcfce7,stroke:#16a34a,color:#166534;",
            "    classDef blocked fill:#fee2e2,stroke:#dc2626,color:#7f1d1d;",
            "    classDef review fill:#fef3c7,stroke:#d97706,color:#78350f;",
            "    classDef conflict fill:#fce7f3,stroke:#db2777,color:#831843;",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a Mermaid task graph.")
    parser.add_argument("--input", required=True, help="Input task graph JSON path")
    parser.add_argument("--output", required=True, help="Output Mermaid file path")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    graph = json.loads(input_path.read_text(encoding="utf-8"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_mermaid(graph), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
