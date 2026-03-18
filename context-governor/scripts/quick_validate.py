import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from build_resume_pack import render_resume_pack


SCRIPTS_DIR = Path(__file__).resolve().parent


def run_command(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
    )


def assert_ok(result: subprocess.CompletedProcess[str], label: str) -> None:
    if result.returncode == 0:
        return
    lines = [f"{label} failed with exit code {result.returncode}"]
    if result.stdout.strip():
        lines.append("STDOUT:")
        lines.append(result.stdout.strip())
    if result.stderr.strip():
        lines.append("STDERR:")
        lines.append(result.stderr.strip())
    raise RuntimeError("\n".join(lines))


def assert_failed(result: subprocess.CompletedProcess[str], label: str, expected_text: str) -> None:
    if result.returncode != 0:
        output = "\n".join(
            part for part in [result.stdout.strip(), result.stderr.strip()] if part
        )
        if expected_text in output:
            return
        raise RuntimeError(
            f"{label} failed as expected but did not include {expected_text!r}.\nOutput:\n{output}"
        )

    lines = [f"{label} unexpectedly succeeded"]
    if result.stdout.strip():
        lines.append("STDOUT:")
        lines.append(result.stdout.strip())
    if result.stderr.strip():
        lines.append("STDERR:")
        lines.append(result.stderr.strip())
    raise RuntimeError("\n".join(lines))


def assert_exists(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Expected file was not created: {path}")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_ndjson(path: Path) -> list[dict]:
    if not path.exists():
        return []

    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped:
            records.append(json.loads(stripped))
    return records


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not content.endswith("\n"):
        content += "\n"
    path.write_text(content, encoding="utf-8")


def assert_contains(text: str, expected: str, label: str) -> None:
    if expected not in text:
        raise RuntimeError(f"{label} is missing expected text: {expected}")


def extract_json_array_values(content: str, field_name: str) -> list[str]:
    pattern = rf'"{re.escape(field_name)}"\s*:\s*\[(.*?)\]'
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        raise RuntimeError(f"Missing JSON array field: {field_name}")
    return re.findall(r'"([^"]+)"', match.group(1))


def extract_prompt_fallback_files(prompt_text: str) -> list[str]:
    _, header, fallback_block = prompt_text.partition(
        "Only if the active slice is insufficient, expand to:"
    )
    if not header:
        raise RuntimeError("next-session-prompt.md is missing the fallback expansion block")
    block, _, _ = fallback_block.partition("After reviewing the narrow context")
    return [line[2:].strip() for line in block.splitlines() if line.startswith("- ")]


def assert_primary_widening_ladder(values: list[str], label: str) -> None:
    required_prefix = [
        ".codex/context/session-delta.md",
        ".codex/context/history-rollup.md",
        ".codex/context/latest-snapshot.json",
    ]
    if values[: len(required_prefix)] != required_prefix:
        raise RuntimeError(
            f"{label} did not start with the primary widening ladder: "
            f"{required_prefix!r}. Saw: {values!r}"
        )

    resume_pack = ".codex/context/resume-pack.md"
    if resume_pack in values and values.index(resume_pack) < len(required_prefix):
        raise RuntimeError(
            f"{label} placed {resume_pack} before the settled widening ladder. "
            "resume-pack.md should stay auxiliary to session-delta/history-rollup/latest-snapshot."
        )


def extract_markdown_section(content: str, heading: str) -> str:
    lines = content.splitlines()
    section_lines: list[str] = []
    capture = False
    heading_level = 0

    for line in lines:
        if not capture:
            if line.strip() == heading:
                capture = True
                heading_level = len(line) - len(line.lstrip("#"))
                section_lines.append(line)
            continue

        if line.startswith("#"):
            line_level = len(line) - len(line.lstrip("#"))
            if line_level <= heading_level:
                break
        section_lines.append(line)

    if not section_lines:
        raise RuntimeError(f"Missing markdown section: {heading}")
    return "\n".join(section_lines)


def assert_prompt_policy_alignment(prompt_text: str) -> None:
    before_stop, separator, _ = prompt_text.partition("Stop after:")
    if not separator:
        raise RuntimeError("next-session-prompt.md is missing the Stop after section")

    _, read_header, read_now_block = before_stop.partition("Read only these files now:")
    if not read_header:
        raise RuntimeError("next-session-prompt.md is missing the default read-now section")

    read_now_files = {
        line[2:].strip()
        for line in read_now_block.splitlines()
        if line.startswith("- ")
    }

    snapshot_restrictive_line = (
        "Do not read .codex/context/latest-snapshot.json unless the active slice has "
        "missing anchors, conflicts, or structural warnings."
    )
    snapshot_required_line = (
        "Read .codex/context/latest-snapshot.json now because this task already requires "
        "the settled project structure."
    )
    prd_restrictive_line = (
        "Do not read docs/prd/approved-prd.md unless latest-snapshot.json still cannot "
        "resolve the referenced requirement safely."
    )
    prd_required_line = (
        "Read docs/prd/approved-prd.md now because this task already requires the source "
        "requirement text."
    )

    if ".codex/context/latest-snapshot.json" in read_now_files:
        if snapshot_restrictive_line in prompt_text:
            raise RuntimeError(
                "next-session-prompt.md contradicts itself by requiring "
                ".codex/context/latest-snapshot.json in the read-now set while also "
                "telling the next session not to read it."
            )
        if snapshot_required_line not in prompt_text:
            raise RuntimeError(
                "next-session-prompt.md did not explain why latest-snapshot.json is already "
                "required in the read-now set"
            )
    elif snapshot_restrictive_line not in prompt_text:
        raise RuntimeError(
            "next-session-prompt.md dropped the restrictive snapshot policy when the file "
            "is not in the read-now set"
        )

    if "docs/prd/approved-prd.md" in read_now_files:
        if prd_restrictive_line in prompt_text:
            raise RuntimeError(
                "next-session-prompt.md contradicts itself by requiring "
                "docs/prd/approved-prd.md in the read-now set while also telling the next "
                "session not to read it."
            )
        if prd_required_line not in prompt_text:
            raise RuntimeError(
                "next-session-prompt.md did not explain why docs/prd/approved-prd.md is "
                "already required in the read-now set"
            )
    elif prd_restrictive_line not in prompt_text:
        raise RuntimeError(
            "next-session-prompt.md dropped the restrictive PRD policy when the file is "
            "not in the read-now set"
        )


def render_validation_checklist(plan_id: str, title: str) -> str:
    lines = [
        f"# Implementation Checklist: {title}",
        "",
        "## Metadata",
        f"- Plan ID: {plan_id}",
        "- Snapshot: .codex/context/latest-snapshot.json",
        "- Last Settled At: validation-seed",
        "",
        "## Tasks",
        "",
        "### T-001",
        "- Title: Normalize the approved PRD into a doc plan",
        "- Status: done",
        "- Phase: planning",
        "- Depends On: none",
        "- Confidence: confirmed",
        "- Acceptance Criteria:",
        "  - Approved PRD linked in docs/prd/approved-prd.md",
        "  - Planning scope captured with stable task IDs",
        "- Evidence:",
        "  - prd-normalized",
        "",
        "### T-002",
        "- Title: Write the ordered implementation checklist",
        "- Status: in_progress",
        "- Phase: planning",
        "- Depends On: T-001",
        "- Confidence: confirmed",
        "- Current: yes",
        "- Acceptance Criteria:",
        "  - Checklist saved to docs/implementation/checklist.md",
        "  - Dependencies recorded with stable task IDs",
        "- Evidence:",
        "  - checklist-written",
        "",
        "### T-003",
        "- Title: Implement the next task after checklist settlement",
        "- Status: todo",
        "- Phase: implementation",
        "- Depends On: T-002",
        "- Confidence: inferred",
        "- Acceptance Criteria:",
        "  - Successor activation verified after progress sync",
        "- Evidence:",
        "  - none",
        "",
    ]
    return "\n".join(lines)


def render_prd_escalation_checklist(plan_id: str, title: str) -> str:
    lines = [
        f"# Implementation Checklist: {title}",
        "",
        "## Metadata",
        f"- Plan ID: {plan_id}",
        "- Snapshot: .codex/context/latest-snapshot.json",
        "- Last Settled At: validation-prd-escalation",
        "",
        "## Tasks",
        "",
        "### T-001",
        "- Title: Normalize the approved PRD into a doc plan",
        "- Status: done",
        "- Phase: planning",
        "- Depends On: none",
        "- Confidence: confirmed",
        "- Acceptance Criteria:",
        "  - Approved PRD linked in docs/prd/approved-prd.md",
        "- Evidence:",
        "  - prd-normalized",
        "",
        "### T-002",
        "- Title: Implement the first execution slice from the approved plan",
        "- Status: in_progress",
        "- Phase: implementation",
        "- Depends On: T-001",
        "- Confidence: confirmed",
        "- Current: yes",
        "- Acceptance Criteria:",
        "- Evidence:",
        "  - active-work",
        "",
        "### T-003",
        "- Title: Verify the next successor after the first execution slice",
        "- Status: todo",
        "- Phase: verification",
        "- Depends On: T-002",
        "- Confidence: inferred",
        "- Acceptance Criteria:",
        "  - Successor activation verified after T-002 completes",
        "- Evidence:",
        "  - none",
        "",
    ]
    return "\n".join(lines)


def render_branching_checklist(plan_id: str, title: str) -> str:
    lines = [
        f"# Implementation Checklist: {title}",
        "",
        "## Metadata",
        f"- Plan ID: {plan_id}",
        "- Snapshot: .codex/context/latest-snapshot.json",
        "- Last Settled At: validation-branch",
        "",
        "## Tasks",
        "",
        "### T-001",
        "- Title: Finish the shared prerequisite",
        "- Status: todo",
        "- Phase: planning",
        "- Depends On: none",
        "- Confidence: confirmed",
        "- Current: yes",
        "- Acceptance Criteria:",
        "  - Shared prerequisite is complete",
        "- Evidence:",
        "  - none",
        "",
        "### T-002",
        "- Title: Build branch A",
        "- Status: todo",
        "- Phase: implementation",
        "- Depends On: T-001",
        "- Confidence: inferred",
        "- Acceptance Criteria:",
        "  - Branch A can start after T-001",
        "- Evidence:",
        "  - none",
        "",
        "### T-003",
        "- Title: Build branch B",
        "- Status: todo",
        "- Phase: implementation",
        "- Depends On: T-001",
        "- Confidence: inferred",
        "- Acceptance Criteria:",
        "  - Branch B can start after T-001",
        "- Evidence:",
        "  - none",
        "",
    ]
    return "\n".join(lines)


def render_invalid_checklist(plan_id: str, title: str, case: str) -> str:
    base_lines = [
        f"# Implementation Checklist: {title}",
        "",
        "## Metadata",
        f"- Plan ID: {plan_id}",
        "- Snapshot: .codex/context/latest-snapshot.json",
        f"- Last Settled At: validation-{case}",
        "",
        "## Tasks",
        "",
    ]

    cases = {
        "duplicate-id": [
            "### T-001",
            "- Title: First task",
            "- Status: todo",
            "- Phase: planning",
            "- Depends On: none",
            "- Confidence: confirmed",
            "- Acceptance Criteria:",
            "  - First task exists",
            "- Evidence:",
            "  - none",
            "",
            "### T-001",
            "- Title: Duplicate task",
            "- Status: todo",
            "- Phase: implementation",
            "- Depends On: none",
            "- Confidence: confirmed",
            "- Acceptance Criteria:",
            "  - Duplicate ID should fail",
            "- Evidence:",
            "  - none",
            "",
        ],
        "missing-dependency": [
            "### T-001",
            "- Title: Task with missing dependency target",
            "- Status: todo",
            "- Phase: planning",
            "- Depends On: T-999",
            "- Confidence: confirmed",
            "- Current: yes",
            "- Acceptance Criteria:",
            "  - Missing dependency should fail",
            "- Evidence:",
            "  - none",
            "",
        ],
        "self-dependency": [
            "### T-001",
            "- Title: Task with self dependency",
            "- Status: todo",
            "- Phase: planning",
            "- Depends On: T-001",
            "- Confidence: confirmed",
            "- Current: yes",
            "- Acceptance Criteria:",
            "  - Self dependency should fail",
            "- Evidence:",
            "  - none",
            "",
        ],
        "cycle": [
            "### T-001",
            "- Title: First cycle node",
            "- Status: todo",
            "- Phase: planning",
            "- Depends On: T-002",
            "- Confidence: confirmed",
            "- Acceptance Criteria:",
            "  - Cycle should fail",
            "- Evidence:",
            "  - none",
            "",
            "### T-002",
            "- Title: Second cycle node",
            "- Status: todo",
            "- Phase: implementation",
            "- Depends On: T-001",
            "- Confidence: confirmed",
            "- Acceptance Criteria:",
            "  - Cycle should fail",
            "- Evidence:",
            "  - none",
            "",
        ],
        "invalid-status": [
            "### T-001",
            "- Title: Task with unsupported status",
            "- Status: shipped",
            "- Phase: planning",
            "- Depends On: none",
            "- Confidence: confirmed",
            "- Current: yes",
            "- Acceptance Criteria:",
            "  - Unsupported status should fail",
            "- Evidence:",
            "  - none",
            "",
        ],
        "invalid-blocked-reason": [
            "### T-001",
            "- Title: Task with blocked reason on the wrong status",
            "- Status: todo",
            "- Phase: planning",
            "- Depends On: none",
            "- Confidence: confirmed",
            "- Current: yes",
            "- Blocked Reason: Waiting on an external answer",
            "- Acceptance Criteria:",
            "  - Blocked reason should fail unless status is blocked",
            "- Evidence:",
            "  - none",
            "",
        ],
        "invalid-review-reason": [
            "### T-001",
            "- Title: Task with review reason on the wrong status",
            "- Status: in_progress",
            "- Phase: planning",
            "- Depends On: none",
            "- Confidence: confirmed",
            "- Current: yes",
            "- Review Reason: Waiting for human approval",
            "- Acceptance Criteria:",
            "  - Review reason should fail unless status is needs_review",
            "- Evidence:",
            "  - none",
            "",
        ],
    }

    if case not in cases:
        raise KeyError(f"Unknown invalid checklist case: {case}")

    return "\n".join([*base_lines, *cases[case]])


def render_duplicate_dependency_checklist(plan_id: str, title: str) -> str:
    lines = [
        f"# Implementation Checklist: {title}",
        "",
        "## Metadata",
        f"- Plan ID: {plan_id}",
        "- Snapshot: .codex/context/latest-snapshot.json",
        "- Last Settled At: validation-duplicate-dependency",
        "",
        "## Tasks",
        "",
        "### T-001",
        "- Title: Finish the shared prerequisite",
        "- Status: done",
        "- Phase: planning",
        "- Depends On: none",
        "- Confidence: confirmed",
        "- Acceptance Criteria:",
        "  - Shared prerequisite is complete",
        "- Evidence:",
        "  - prerequisite-finished",
        "",
        "### T-002",
        "- Title: Build the dependent task",
        "- Status: in_progress",
        "- Phase: implementation",
        "- Depends On: T-001, T-001",
        "- Confidence: inferred",
        "- Current: yes",
        "- Acceptance Criteria:",
        "  - Duplicate dependency entries are normalized",
        "- Evidence:",
        "  - none",
        "",
    ]
    return "\n".join(lines)


def validate_py_compile() -> None:
    scripts = sorted(SCRIPTS_DIR.glob("*.py"))
    result = run_command([sys.executable, "-m", "py_compile", *[str(path) for path in scripts]])
    assert_ok(result, "py_compile")


def validate_reference_consistency() -> None:
    references_dir = SCRIPTS_DIR.parent / "references"
    skill_path = SCRIPTS_DIR.parent / "SKILL.md"
    readme_path = SCRIPTS_DIR.parent / "README.md"
    readme_zh_path = SCRIPTS_DIR.parent / "README-zh.md"
    new_project_template_path = references_dir / "new-project-template.md"

    readme = readme_path.read_text(encoding="utf-8")
    assert_contains(readme, "[README-zh.md](./README-zh.md)", "README docs section")
    assert_contains(
        readme,
        "[references/new-project-template.md](./references/new-project-template.md)",
        "README new project template link",
    )

    readme_zh = readme_zh_path.read_text(encoding="utf-8")
    assert_contains(readme_zh, "双层存储", "README-zh architecture language")
    assert_contains(readme_zh, "表面双主源，内部单结算点", "README-zh settlement language")
    assert_contains(
        readme_zh,
        "active-context.md",
        "README-zh token control ladder",
    )
    assert_contains(readme_zh, "quick_validate.py", "README-zh validation guidance")
    assert_contains(
        readme_zh,
        "[references/new-project-template.md](./references/new-project-template.md)",
        "README-zh new project template link",
    )

    new_project_template = new_project_template_path.read_text(encoding="utf-8")
    for expected in (
        "init_context_governor.py",
        "docs/prd/approved-prd.md",
        "settle_checklist_context_governor.py",
        "resume_context_governor.py",
        "sync_progress_context_governor.py",
        "closeout_context_governor.py",
        "quick_validate.py",
    ):
        assert_contains(new_project_template, expected, "new project template commands")

    skill_text = skill_path.read_text(encoding="utf-8")
    assert_contains(
        skill_text,
        "`references/new-project-template.md`",
        "SKILL references new project template",
    )

    quickstart = (references_dir / "quickstart.md").read_text(encoding="utf-8")
    assert_contains(
        quickstart,
        "`references/new-project-template.md`",
        "quickstart new project template link",
    )
    assert_contains(
        quickstart,
        "`docs/implementation/progress.md` (optional bootstrap and milestone log; not a live resume source)",
        "quickstart generated starter files",
    )
    quickstart_validation = extract_markdown_section(quickstart, "## One-Command Validation")
    assert_contains(
        quickstart_validation,
        "- reference-contract consistency for key docs",
        "quickstart validation section",
    )

    quickstart_zh = (references_dir / "quickstart-zh.md").read_text(encoding="utf-8")
    assert_contains(
        quickstart_zh,
        "`references/new-project-template.md`",
        "quickstart-zh new project template link",
    )
    quickstart_zh_validation = extract_markdown_section(quickstart_zh, "## 一条命令自检")
    assert_contains(
        quickstart_zh_validation,
        "- 关键参考文档和当前脚本行为是否保持契约一致",
        "quickstart-zh validation section",
    )
    cheatsheet_zh = (references_dir / "cheatsheet-zh.md").read_text(encoding="utf-8")
    assert_contains(
        cheatsheet_zh,
        "`.codex/context/resume-manifest.json`",
        "cheatsheet-zh resume guidance",
    )
    cheatsheet_zh_closeout = extract_markdown_section(
        cheatsheet_zh, "### 5. 会话结束后结算"
    )
    assert_contains(
        cheatsheet_zh_closeout,
        "`sync_progress_context_governor.py`",
        "cheatsheet-zh closeout section",
    )
    quickstart_sync = extract_markdown_section(
        quickstart_zh, "### 1. 完成或卡住一个任务后，立刻同步"
    )
    for expected in (
        "`.codex/context/budget-report.json`",
        "`.codex/context/budget-report.md`",
    ):
        assert_contains(quickstart_sync, expected, "quickstart-zh sync section")
    quickstart_session_startup = extract_markdown_section(quickstart, "## Session Startup")
    assert_contains(
        quickstart_session_startup,
        "`.codex/context/focus-set.json`",
        "quickstart session startup section",
    )
    quickstart_prompts = extract_markdown_section(quickstart, "## Next-Session Prompts")
    for expected in (
        "If today's task status or evidence has not been synced yet, sync it first.",
        "If you changed task structure in `docs/implementation/checklist.md`, settle the checklist first.",
    ):
        assert_contains(quickstart_prompts, expected, "quickstart next-session prompts section")
    for heading in ("## Progress Sync", "## Structural Rebuild", "## Session Closeout"):
        section = extract_markdown_section(quickstart, heading)
        assert_contains(
            section,
            "`.codex/context/sync-history.ndjson`",
            f"quickstart {heading} section",
        )
    quickstart_closeout = extract_markdown_section(quickstart, "## Session Closeout")
    assert_contains(
        quickstart_closeout,
        "`sync_progress_context_governor.py`",
        "quickstart session closeout section",
    )
    if "After you update `.codex/context/latest-state.json` with fresh evidence or task status, run:" in quickstart_closeout:
        raise RuntimeError(
            "quickstart session closeout section still tells operators to update "
            "latest-state.json directly before closeout instead of routing progress "
            "through sync_progress_context_governor.py first"
        )

    quickstart_zh_resume = extract_markdown_section(quickstart_zh, "### 2. 下次继续开发前，先恢复最小上下文")
    assert_contains(
        quickstart_zh_resume,
        "`.codex/context/focus-set.json`",
        "quickstart-zh resume section",
    )
    assert_contains(
        quickstart_sync,
        "`.codex/context/sync-history.ndjson`",
        "quickstart-zh sync section",
    )
    quickstart_zh_closeout = extract_markdown_section(
        quickstart_zh, "### 3. 结束今天的会话时，做一次结算"
    )
    assert_contains(
        quickstart_zh_closeout,
        "`sync_progress_context_governor.py`",
        "quickstart-zh closeout section",
    )
    quickstart_zh_prompts = extract_markdown_section(quickstart_zh, "## 常用提示词")
    assert_contains(
        quickstart_zh_prompts,
        "### 结束今天的会话并结算",
        "quickstart-zh prompt section",
    )

    workflow = (references_dir / "workflow.md").read_text(encoding="utf-8")

    plan_from_prd = extract_markdown_section(workflow, "### `plan-from-prd`")
    for expected in (
        "`active-context.*`",
        "`session-delta.*`",
        "`history-rollup.*`",
        "`budget-report.*`",
        "`focus-set.json`",
        "`resume-pack.md`",
        "`next-session-prompt.md`",
        "`sync-history.ndjson`",
    ):
        assert_contains(plan_from_prd, expected, "workflow plan-from-prd section")

    rebuild_from_docs = extract_markdown_section(workflow, "### `rebuild-from-docs`")
    for expected in (
        "`active-context.*`",
        "`session-delta.*`",
        "`history-rollup.*`",
        "`budget-report.*`",
        "`focus-set.json`",
        "`resume-pack.md`",
        "`next-session-prompt.md`",
        "`sync-history.ndjson`",
    ):
        assert_contains(rebuild_from_docs, expected, "workflow rebuild-from-docs section")

    resume_from_state = extract_markdown_section(workflow, "### `resume-from-state`")
    for expected in (
        "`focus-set.json`",
        "`next-session-prompt.md`",
        "`sync-history.ndjson`",
    ):
        assert_contains(resume_from_state, expected, "workflow resume-from-state section")
    assert_contains(
        resume_from_state,
        "auxiliary",
        "workflow resume-from-state section",
    )
    assert_contains(
        resume_from_state,
        "`resume-pack.md`",
        "workflow resume-from-state section",
    )

    track_progress = extract_markdown_section(workflow, "### `track-progress`")
    for expected in (
        "`doc-plan.json`",
        "`session-delta.*`",
        "`budget-report.*`",
        "`latest-task-graph.json`",
        "`next-session-prompt.md`",
        "`docs/implementation/current-graph.mmd`",
        "`sync-history.ndjson`",
    ):
        assert_contains(track_progress, expected, "workflow track-progress section")
    if "Current snapshot and active node" in track_progress:
        raise RuntimeError(
            "workflow track-progress section still claims sync reads the current "
            "snapshot by default, but sync_progress_context_governor.py rebuilds a "
            "fresh snapshot from doc-plan.json and latest-state.json"
        )

    schemas = (references_dir / "schemas.md").read_text(encoding="utf-8")
    active_context_schema = extract_markdown_section(schemas, "## Active Context")
    assert_contains(
        active_context_schema,
        "`fallback_files_to_read`",
        "schemas active context section",
    )
    assert_primary_widening_ladder(
        extract_json_array_values(active_context_schema, "fallback_files_to_read"),
        "schemas active context fallback_files_to_read",
    )
    resume_manifest_schema = extract_markdown_section(schemas, "## Resume Manifest Shape")
    assert_primary_widening_ladder(
        extract_json_array_values(resume_manifest_schema, "fallback_files_to_read"),
        "schemas resume manifest fallback_files_to_read",
    )
    session_delta_schema = extract_markdown_section(schemas, "## Session Delta")
    assert_contains(
        session_delta_schema,
        '"focus_transition": {\n    "from_task_id": "T-001",\n    "to_task_id": "T-002"\n  },',
        "schemas session delta focus transition contract",
    )
    canonical_snapshot_schema = extract_markdown_section(schemas, "## Canonical Snapshot")
    assert_contains(
        canonical_snapshot_schema,
        "resume consumes and sync/closeout regenerate",
        "schemas canonical snapshot section",
    )
    if "used for resume and sync" in canonical_snapshot_schema:
        raise RuntimeError(
            "schemas canonical snapshot section still implies sync reads the prior "
            "snapshot instead of regenerating a fresh canonical snapshot from hidden state"
        )
    sync_history_section = extract_markdown_section(schemas, "## Sync History Event Shape")
    for expected in (
        "`initialized`",
        "`settle_checklist`",
        "`resume`",
        "`sync_progress`",
        "`closeout`",
    ):
        assert_contains(sync_history_section, expected, "schemas sync history section")

    sync_rules = (references_dir / "sync-rules.md").read_text(encoding="utf-8")
    event_log_boundaries = extract_markdown_section(
        sync_rules, "## Event Log And Resume Boundaries"
    )
    for expected in (
        "`sync-history.ndjson`",
        "`initialized`",
        "`settle_checklist`",
        "`resume`",
        "`sync_progress`",
        "`closeout`",
        "`resume-manifest.json`",
        "`resume_context_governor.py`",
    ):
        assert_contains(
            event_log_boundaries,
            expected,
            "sync-rules event log and resume boundaries section",
        )

    openai_yaml = (SCRIPTS_DIR.parent / "agents" / "openai.yaml").read_text(encoding="utf-8")
    for expected in ("resume", "sync progress", "saved state"):
        assert_contains(openai_yaml, expected, "openai agent metadata")

    skill = skill_path.read_text(encoding="utf-8")
    resume_mode = extract_markdown_section(skill, "### `resume-from-state`")
    assert_contains(
        resume_mode,
        "`.codex/context/active-context.md`",
        "SKILL resume-from-state section",
    )
    if "latest canonical snapshot" in resume_mode:
        raise RuntimeError(
            "SKILL resume-from-state section still starts from the latest canonical snapshot "
            "instead of the active-context gate."
        )
    outputs_section = extract_markdown_section(skill, "## Outputs")
    for expected in (
        "`doc-plan.json`",
        "`focus-set.json`",
        "`resume-manifest.json`",
        "`sync-history.ndjson`",
    ):
        assert_contains(outputs_section, expected, "SKILL outputs section")

    helpers_section = extract_markdown_section(skill, "## Deterministic Helpers")
    for expected in (
        "`scripts/resume_context_governor.py` rebuilds the smallest safe startup context, refreshes `active-context`, `session-delta`, `history-rollup`, and `budget-report`, refreshes `focus-set.json` and `next-session-prompt.md`, and emits resume loading stats in `resume-manifest.json`",
        "`scripts/closeout_context_governor.py` settles end-of-session outputs into `active-context`, `session-delta`, `history-rollup`, `budget-report`, snapshot, checklist, graph, focus set, and the auxiliary resume pack",
    ):
        assert_contains(helpers_section, expected, "SKILL deterministic helpers section")


def validate_resume_pack_contract() -> None:
    blocked_resume_pack = render_resume_pack(
        {
            "plan_id": "validation-plan",
            "generated_at": "2026-03-15T00:00:00Z",
            "current_task_id": "T-001",
            "tasks": [
                {
                    "id": "T-001",
                    "title": "Investigate blocked task",
                    "status": "blocked",
                    "depends_on": [],
                    "acceptance_criteria": ["Blocker captured for the operator"],
                    "evidence": ["found-blocker"],
                    "blocked_reason": "waiting-on-api",
                }
            ],
            "warnings": [],
        },
        "T-001",
    )
    assert_contains(
        blocked_resume_pack,
        "- Blocked Reason: waiting-on-api",
        "resume-pack blocked task contract",
    )


def validate_smoke(project_root: Path) -> None:
    init_script = SCRIPTS_DIR / "init_context_governor.py"
    settle_script = SCRIPTS_DIR / "settle_checklist_context_governor.py"
    resume_script = SCRIPTS_DIR / "resume_context_governor.py"
    sync_script = SCRIPTS_DIR / "sync_progress_context_governor.py"
    closeout_script = SCRIPTS_DIR / "closeout_context_governor.py"

    init_result = run_command([sys.executable, str(init_script), "--root", str(project_root)])
    assert_ok(init_result, "init_context_governor")
    normalized_init_output = init_result.stdout.replace("\\", "/")
    if "WRITE .codex/context/session-delta.json" not in normalized_init_output:
        raise RuntimeError(
            "init_context_governor did not report session-delta.json in its output summary"
        )
    if "WRITE .codex/context/session-delta.md" not in normalized_init_output:
        raise RuntimeError(
            "init_context_governor did not report session-delta.md in its output summary"
        )

    context_dir = project_root / ".codex" / "context"
    docs_dir = project_root / "docs" / "implementation"
    checklist_path = docs_dir / "checklist.md"

    for path in (
        project_root / "docs" / "prd" / "approved-prd.md",
        checklist_path,
        docs_dir / "current-graph.mmd",
        docs_dir / "context-governor-playbook.md",
        context_dir / "budget-report.json",
        context_dir / "budget-report.md",
        context_dir / "doc-plan.json",
        context_dir / "active-context.json",
        context_dir / "active-context.md",
        context_dir / "history-rollup.json",
        context_dir / "history-rollup.md",
        context_dir / "session-delta.json",
        context_dir / "session-delta.md",
        context_dir / "latest-state.json",
        context_dir / "latest-snapshot.json",
        context_dir / "latest-task-graph.json",
        context_dir / "focus-set.json",
        context_dir / "resume-pack.md",
        context_dir / "next-session-prompt.md",
        context_dir / "sync-history.ndjson",
    ):
        assert_exists(path)

    seeded_next_prompt = (context_dir / "next-session-prompt.md").read_text(encoding="utf-8")
    if "Current task: T-001" not in seeded_next_prompt:
        raise RuntimeError("next-session-prompt.md did not start from the seeded T-001 task")
    assert_prompt_policy_alignment(seeded_next_prompt)

    playbook_text = (docs_dir / "context-governor-playbook.md").read_text(encoding="utf-8")
    for expected in (
        ".codex/context/resume-manifest.json",
        "Context Gate",
        "Read Now",
        "Stop Reading After",
        "Next Allowed Reads",
        ".codex/context/session-delta.md",
        ".codex/context/history-rollup.md",
        ".codex/context/budget-report.md",
        ".codex/context/sync-history.ndjson",
    ):
        if expected not in playbook_text:
            raise RuntimeError(
                "context-governor-playbook.md is missing the expected operator guidance: "
                f"{expected}"
            )
    for expected in (
        "- `.codex/context/latest-snapshot.json` (settled fallback)",
        "- `.codex/context/resume-pack.md` (auxiliary current-task recap)",
    ):
        if expected not in playbook_text:
            raise RuntimeError(
                "context-governor-playbook.md did not label the trust-first files with "
                f"their intended role: {expected}"
            )

    seeded_plan = load_json(context_dir / "doc-plan.json")
    write_text(
        checklist_path,
        render_validation_checklist(seeded_plan["plan_id"], seeded_plan["title"]),
    )

    settle_result = run_command([sys.executable, str(settle_script), "--root", str(project_root)])
    assert_ok(settle_result, "settle_checklist_context_governor")
    normalized_settle_output = settle_result.stdout.replace("\\", "/")
    for expected_path in (
        ".codex/context/active-context.json",
        ".codex/context/active-context.md",
        ".codex/context/session-delta.json",
        ".codex/context/session-delta.md",
        ".codex/context/history-rollup.json",
        ".codex/context/history-rollup.md",
    ):
        if (
            f"WRITE {expected_path}" not in normalized_settle_output
            and f"/{expected_path}" not in normalized_settle_output
        ):
            raise RuntimeError(
                "settle_checklist_context_governor did not report "
                f"{expected_path} in its output summary"
            )

    settled_doc_plan = load_json(context_dir / "doc-plan.json")
    settled_state = load_json(context_dir / "latest-state.json")
    settled_snapshot = load_json(context_dir / "latest-snapshot.json")
    focus_set = load_json(context_dir / "focus-set.json")

    if len(settled_doc_plan["tasks"]) != 3:
        raise RuntimeError("settle_checklist did not rebuild the expected 3-task doc plan")
    if settled_state.get("current_task_id") != "T-002":
        raise RuntimeError("settle_checklist did not keep T-002 as the active task")
    if settled_snapshot.get("current_task_id") != "T-002":
        raise RuntimeError("settled snapshot did not keep T-002 as the active task")
    if focus_set.get("current_task_id") != "T-002":
        raise RuntimeError("focus-set.json did not point at T-002 after checklist settlement")

    resume_result = run_command([sys.executable, str(resume_script), "--root", str(project_root)])
    assert_ok(resume_result, "resume_context_governor")

    active_context = load_json(context_dir / "active-context.json")
    history_rollup = load_json(context_dir / "history-rollup.json")
    session_delta = load_json(context_dir / "session-delta.json")
    resume_manifest = load_json(context_dir / "resume-manifest.json")
    budget_report = load_json(context_dir / "budget-report.json")
    progress_text = (project_root / "docs" / "implementation" / "progress.md").read_text(
        encoding="utf-8"
    )
    resume_pack_text = (context_dir / "resume-pack.md").read_text(encoding="utf-8")
    playbook_text = (
        project_root / "docs" / "implementation" / "context-governor-playbook.md"
    ).read_text(encoding="utf-8")
    if active_context.get("current_task_id") != "T-002":
        raise RuntimeError("active-context.json did not focus T-002 after checklist settlement")
    if active_context.get("recommended_context_level") != "active_only":
        raise RuntimeError("active-context.json did not keep the default resume path at active_only")
    if active_context.get("recommended_files_to_read") != [
        ".codex/context/active-context.md",
        "docs/implementation/checklist.md#t-002",
    ]:
        raise RuntimeError("active-context.json did not preserve the recommended active-only read set")
    if active_context.get("next_allowed_reads") != [".codex/context/session-delta.md"]:
        raise RuntimeError("active-context.json did not restrict the next allowed expansion step to session-delta.md")
    if resume_manifest.get("files_to_read") != [
        ".codex/context/active-context.md",
        "docs/implementation/checklist.md#t-002",
    ]:
        raise RuntimeError("resume_context_governor did not switch to the minimal active-context read set")
    if ".codex/context/latest-snapshot.json" in resume_manifest.get("files_to_read", []):
        raise RuntimeError("resume_context_governor still requires latest-snapshot.json in the default read set")
    if ".codex/context/session-delta.md" not in resume_manifest.get("fallback_files_to_read", []):
        raise RuntimeError("resume_context_governor did not advertise session-delta.md as a fallback read")
    if ".codex/context/history-rollup.md" not in resume_manifest.get("fallback_files_to_read", []):
        raise RuntimeError("resume_context_governor did not advertise history-rollup.md as a fallback read")
    assert_primary_widening_ladder(
        list(active_context.get("fallback_files_to_read", [])),
        "active-context.json fallback_files_to_read",
    )
    assert_primary_widening_ladder(
        list(resume_manifest.get("fallback_files_to_read", [])),
        "resume-manifest.json fallback_files_to_read",
    )
    if not history_rollup.get("recent_events"):
        raise RuntimeError("history-rollup.json did not capture recent events after resume")
    latest_resume_event = history_rollup["recent_events"][-1]
    if latest_resume_event.get("event") != "resume":
        raise RuntimeError("history-rollup.json did not record the resume event as the latest recent event")
    if latest_resume_event.get("current_task_status") != "in_progress":
        raise RuntimeError(
            "history-rollup.json did not preserve current_task_status on the latest resume event"
        )
    if session_delta.get("current_task_id") != "T-002":
        raise RuntimeError("session-delta.json did not focus T-002 after checklist settlement")
    latest_session_event = session_delta.get("latest_event", {})
    if latest_session_event.get("event") != "resume":
        raise RuntimeError("session-delta.json did not capture resume as the latest event")
    if latest_session_event.get("current_task_status") != "in_progress":
        raise RuntimeError(
            "session-delta.json did not preserve current_task_status on the latest resume event"
        )
    if "T-002" not in session_delta.get("touched_task_ids", []):
        raise RuntimeError("session-delta.json did not include the current task in touched_task_ids")
    if session_delta.get("next_read") != ".codex/context/history-rollup.md":
        raise RuntimeError("session-delta.json did not point to history-rollup.md as the next widening step")
    history_lines = (context_dir / "sync-history.ndjson").read_text(encoding="utf-8").strip().splitlines()
    latest_history_event = json.loads(history_lines[-1])
    if latest_history_event.get("event") != "resume":
        raise RuntimeError("sync-history.ndjson did not append the resume event after resume")
    if latest_history_event.get("current_task_status") != "in_progress":
        raise RuntimeError(
            "sync-history.ndjson did not append current_task_status on the resume event"
        )
    if resume_manifest.get("current_task_id") != "T-002":
        raise RuntimeError("resume_context_governor did not focus T-002 after checklist settlement")
    if resume_manifest.get("recommended_context_level") != "active_only":
        raise RuntimeError("resume-manifest.json did not keep the default recommendation at active_only")
    if resume_manifest.get("recommended_files_to_read") != [
        ".codex/context/active-context.md",
        "docs/implementation/checklist.md#t-002",
    ]:
        raise RuntimeError("resume-manifest.json did not preserve the active-only recommendation path")
    if resume_manifest.get("next_allowed_reads") != [".codex/context/session-delta.md"]:
        raise RuntimeError("resume-manifest.json did not restrict the next allowed expansion step to session-delta.md")
    if budget_report.get("current_task_id") != "T-002":
        raise RuntimeError("budget-report.json did not focus T-002 after checklist settlement")
    if "Auxiliary only" not in resume_pack_text:
        raise RuntimeError("resume-pack.md did not label itself as auxiliary-only")
    if "primary widening ladder" not in resume_pack_text:
        raise RuntimeError(
            "resume-pack.md did not warn operators that it is not part of the primary widening ladder"
        )
    if ".codex/context/active-context.md" not in resume_pack_text:
        raise RuntimeError(
            "resume-pack.md did not point operators back to active-context.md before using the recap"
        )
    if "resume-only observability output" not in playbook_text:
        raise RuntimeError(
            "context-governor-playbook.md did not label resume-manifest.json as resume-only observability"
        )
    if "- Bootstrap Focus:" not in progress_text:
        raise RuntimeError("progress.md did not label its seeded task as bootstrap-only context")
    if "not a live resume source" not in progress_text:
        raise RuntimeError("progress.md did not warn operators that it is not the live resume source")
    if "Use $context-governor to sync progress" not in progress_text:
        raise RuntimeError("progress.md did not use the user-facing sync progress wording")
    if "Use $context-governor track-progress" in progress_text:
        raise RuntimeError("progress.md still exposed the internal track-progress wording")
    if "- Current Task:" in progress_text:
        raise RuntimeError("progress.md still presents a seeded task as the live current task")
    if "resume_context_governor.py" not in playbook_text or "resume-manifest.json" not in playbook_text:
        raise RuntimeError(
            "context-governor-playbook.md did not explain that resume-manifest.json is refreshed by resume_context_governor.py"
        )
    if budget_report.get("active_context_path", {}).get("file_count") != 2:
        raise RuntimeError("budget-report.json did not record the default minimal read-set file count")
    active_refs = [
        item.get("path") for item in budget_report.get("active_context_path", {}).get("refs", [])
    ]
    if active_refs != [
        ".codex/context/active-context.md",
        "docs/implementation/checklist.md#t-002",
    ]:
        raise RuntimeError("budget-report.json did not preserve the active-context-first read set")
    fallback_refs = [
        item.get("path")
        for item in budget_report.get("snapshot_heavy_fallback_path", {}).get("refs", [])
    ]
    if ".codex/context/session-delta.md" not in fallback_refs:
        raise RuntimeError("budget-report.json did not include session-delta.md in the widened fallback path")
    if ".codex/context/latest-snapshot.json" not in fallback_refs:
        raise RuntimeError("budget-report.json did not compare against the snapshot-heavy fallback path")
    comparison = budget_report.get("comparison", {})
    if comparison.get("extra_bytes_if_fallback_needed", 0) <= 0:
        raise RuntimeError("budget-report.json did not report additional byte cost for the snapshot-heavy fallback path")
    if comparison.get("approx_tokens_saved_when_active_slice_is_enough", 0) <= 0:
        raise RuntimeError("budget-report.json did not report token savings for the active-context path")
    current_recommendation = budget_report.get("current_recommendation", {})
    if current_recommendation.get("recommended_context_level") != "active_only":
        raise RuntimeError("budget-report.json did not report active_only as the default recommendation")
    if not current_recommendation.get("active_slice_sufficient"):
        raise RuntimeError("budget-report.json did not mark the active slice as sufficient in the linear default case")
    if current_recommendation.get("next_allowed_reads") != [".codex/context/session-delta.md"]:
        raise RuntimeError("budget-report.json did not advertise session-delta.md as the next allowed widening step")
    recommended_path = current_recommendation.get("recommended_path", {})
    if current_recommendation.get("recommended_files_to_read") == active_refs:
        if recommended_path.get("bytes_total") != budget_report.get("active_context_path", {}).get(
            "bytes_total"
        ):
            raise RuntimeError(
                "budget-report.json used stale sizing for the current recommendation path"
            )
    budget_report_markdown = (context_dir / "budget-report.md").read_text(encoding="utf-8")
    if "Current Recommendation" not in budget_report_markdown:
        raise RuntimeError("budget-report.md did not render the current recommendation section")
    if "Active-Context Path" not in budget_report_markdown:
        raise RuntimeError("budget-report.md did not render the active-context comparison section")
    if "Snapshot-Heavy Fallback Path" not in budget_report_markdown:
        raise RuntimeError("budget-report.md did not render the snapshot-heavy fallback comparison section")
    session_delta_markdown = (context_dir / "session-delta.md").read_text(encoding="utf-8")
    if "Session Delta" not in session_delta_markdown:
        raise RuntimeError("session-delta.md did not render its title")
    if "Latest Event" not in session_delta_markdown:
        raise RuntimeError("session-delta.md did not render the latest event section")
    session_delta_bytes = len((context_dir / "session-delta.json").read_bytes())
    history_rollup_bytes = len((context_dir / "history-rollup.json").read_bytes())
    if session_delta_bytes >= history_rollup_bytes:
        raise RuntimeError("session-delta.json is not smaller than history-rollup.json")

    sync_result = run_command(
        [
            sys.executable,
            str(sync_script),
            "--root",
            str(project_root),
            "--task",
            "T-002",
            "--status",
            "done",
            "--evidence",
            "validation-sync",
        ]
    )
    assert_ok(sync_result, "sync_progress_context_governor")
    normalized_sync_output = sync_result.stdout.replace("\\", "/")
    for expected_path in (
        ".codex/context/active-context.json",
        ".codex/context/active-context.md",
        ".codex/context/session-delta.json",
        ".codex/context/session-delta.md",
        ".codex/context/history-rollup.json",
        ".codex/context/history-rollup.md",
    ):
        if (
            f"WRITE {expected_path}" not in normalized_sync_output
            and f"/{expected_path}" not in normalized_sync_output
        ):
            raise RuntimeError(
                "sync_progress_context_governor did not report "
                f"{expected_path} in its output summary"
            )

    synced_state = load_json(context_dir / "latest-state.json")
    synced_snapshot = load_json(context_dir / "latest-snapshot.json")
    synced_session_delta = load_json(context_dir / "session-delta.json")
    synced_session_delta_markdown = (context_dir / "session-delta.md").read_text(
        encoding="utf-8"
    )

    if synced_state.get("current_task_id") != "T-003":
        raise RuntimeError("sync_progress did not advance to the ready direct successor T-003")
    if synced_snapshot.get("current_task_id") != "T-003":
        raise RuntimeError("snapshot did not reflect successor advancement to T-003")
    if synced_session_delta.get("previous_current_task_id") != "T-002":
        raise RuntimeError(
            "session-delta.json did not preserve T-002 as previous_current_task_id "
            "after advancing to T-003"
        )
    if synced_session_delta.get("focus_transition") != {
        "from_task_id": "T-002",
        "to_task_id": "T-003",
    }:
        raise RuntimeError(
            "session-delta.json did not persist the structured T-002 -> T-003 focus_transition"
        )
    if "- T-002 -> T-003" not in synced_session_delta_markdown:
        raise RuntimeError(
            "session-delta.md did not render the human-readable T-002 -> T-003 focus transition"
        )

    next_prompt = (context_dir / "next-session-prompt.md").read_text(encoding="utf-8")
    default_prompt_slice = next_prompt.partition(
        "Only if the active slice is insufficient, expand to:"
    )[0]
    if "Current task: T-003" not in next_prompt:
        raise RuntimeError("next-session-prompt.md did not refresh to T-003")
    if "Use $context-governor to resume this project from .codex/context/active-context.md." not in next_prompt:
        raise RuntimeError("next-session-prompt.md did not start from active-context.md")
    if "- .codex/context/active-context.md" not in next_prompt:
        raise RuntimeError("next-session-prompt.md did not prioritize active-context.md in the default read set")
    if "- .codex/context/latest-snapshot.json" in default_prompt_slice:
        raise RuntimeError("next-session-prompt.md still includes latest-snapshot.json in the default read set")
    if "- .codex/context/session-delta.md" not in next_prompt:
        raise RuntimeError("next-session-prompt.md did not advertise session-delta.md in the widening path")
    if "Do not read .codex/context/latest-snapshot.json unless the active slice has missing anchors, conflicts, or structural warnings." not in next_prompt:
        raise RuntimeError("next-session-prompt.md did not add the snapshot escalation gate")
    if "Stop after: active-context path" not in next_prompt:
        raise RuntimeError("next-session-prompt.md did not state the active-only stop point")
    assert_prompt_policy_alignment(next_prompt)
    assert_primary_widening_ladder(
        extract_prompt_fallback_files(next_prompt),
        "next-session-prompt.md fallback expansion block",
    )

    closeout_result = run_command(
        [sys.executable, str(closeout_script), "--root", str(project_root)]
    )
    assert_ok(closeout_result, "closeout_context_governor")

    history_path = context_dir / "sync-history.ndjson"
    history_lines = history_path.read_text(encoding="utf-8").strip().splitlines()
    if len(history_lines) < 4:
        raise RuntimeError("sync-history.ndjson is missing expected validation events")

    weak_sync_result = run_command(
        [
            sys.executable,
            str(sync_script),
            "--root",
            str(project_root),
            "--task",
            "T-003",
            "--status",
            "done",
        ]
    )
    assert_ok(weak_sync_result, "sync_progress_context_governor weak evidence")

    weak_state = load_json(context_dir / "latest-state.json")
    weak_snapshot = load_json(context_dir / "latest-snapshot.json")
    weak_active_context = load_json(context_dir / "active-context.json")
    weak_history_rollup = load_json(context_dir / "history-rollup.json")
    weak_session_delta = load_json(context_dir / "session-delta.json")
    weak_tasks = {task["id"]: task for task in weak_snapshot["tasks"]}

    if weak_state["tasks"][-1]["status"] != "needs_review":
        raise RuntimeError("sync_progress did not downgrade weak done evidence to needs_review")
    if weak_tasks["T-003"]["status"] != "needs_review":
        raise RuntimeError("snapshot did not keep the needs_review downgrade for T-003")
    if weak_active_context.get("current_task_id") != "T-003":
        raise RuntimeError("active-context.json did not refresh to T-003 after weak evidence sync")
    if weak_active_context.get("review_reason") != "missing completion evidence":
        raise RuntimeError("active-context.json did not persist the weak-evidence review reason")
    if weak_active_context.get("recommended_context_level") != "active_plus_history":
        raise RuntimeError("active-context.json did not widen to active_plus_history for weak-evidence review flows")
    if ".codex/context/session-delta.md" not in weak_active_context.get("recommended_files_to_read", []):
        raise RuntimeError("active-context.json did not recommend session-delta.md for weak-evidence review flows")
    if ".codex/context/history-rollup.md" not in weak_active_context.get("recommended_files_to_read", []):
        raise RuntimeError("active-context.json did not recommend history-rollup.md for weak-evidence review flows")
    if "T-003" not in weak_history_rollup.get("needs_review_task_ids", []):
        raise RuntimeError("history-rollup.json did not surface T-003 in needs_review_task_ids")
    if weak_session_delta.get("latest_event", {}).get("event") != "sync_progress":
        raise RuntimeError("session-delta.json did not refresh to the latest sync_progress event")
    if "T-003" not in weak_session_delta.get("touched_task_ids", []):
        raise RuntimeError("session-delta.json did not include the weak-evidence task in touched_task_ids")
    if weak_tasks["T-003"].get("review_reason") != "missing completion evidence":
        raise RuntimeError("snapshot did not persist the weak-evidence review reason")
    if not any("needs_review due to missing completion evidence" in item for item in weak_snapshot["warnings"]):
        raise RuntimeError("snapshot warnings did not explain the weak-evidence review reason")


def validate_ambiguity(project_root: Path) -> None:
    init_script = SCRIPTS_DIR / "init_context_governor.py"
    settle_script = SCRIPTS_DIR / "settle_checklist_context_governor.py"
    sync_script = SCRIPTS_DIR / "sync_progress_context_governor.py"

    init_result = run_command([sys.executable, str(init_script), "--root", str(project_root)])
    assert_ok(init_result, "init_context_governor ambiguity")

    context_dir = project_root / ".codex" / "context"
    checklist_path = project_root / "docs" / "implementation" / "checklist.md"
    seeded_plan = load_json(context_dir / "doc-plan.json")
    write_text(
        checklist_path,
        render_branching_checklist(seeded_plan["plan_id"], seeded_plan["title"]),
    )

    settle_result = run_command([sys.executable, str(settle_script), "--root", str(project_root)])
    assert_ok(settle_result, "settle_checklist_context_governor ambiguity")

    sync_result = run_command(
        [
            sys.executable,
            str(sync_script),
            "--root",
            str(project_root),
            "--task",
            "T-001",
            "--status",
            "done",
            "--evidence",
            "shared-prerequisite-finished",
        ]
    )
    assert_ok(sync_result, "sync_progress_context_governor ambiguity")

    snapshot = load_json(context_dir / "latest-snapshot.json")
    active_context = load_json(context_dir / "active-context.json")
    if snapshot.get("current_task_id") != "T-002":
        raise RuntimeError("Ambiguous ready-task selection did not fall back to the first task")
    if not any("Multiple ready tasks found" in item for item in snapshot["warnings"]):
        raise RuntimeError("Snapshot warnings did not capture ambiguous ready-task selection")
    if active_context.get("recommended_context_level") != "snapshot_required":
        raise RuntimeError("active-context.json did not escalate ambiguous selection to snapshot_required")
    if ".codex/context/latest-snapshot.json" not in active_context.get("recommended_files_to_read", []):
        raise RuntimeError("active-context.json did not recommend latest-snapshot.json for ambiguous selection")
    if ".codex/context/session-delta.md" in active_context.get("recommended_files_to_read", []):
        raise RuntimeError("active-context.json should not include session-delta.md when snapshot access is already required")
    assert_prompt_policy_alignment(
        (context_dir / "next-session-prompt.md").read_text(encoding="utf-8")
    )


def validate_structure_lint(project_root: Path) -> None:
    init_script = SCRIPTS_DIR / "init_context_governor.py"
    settle_script = SCRIPTS_DIR / "settle_checklist_context_governor.py"

    cases = [
        ("duplicate-id", "Duplicate task ID"),
        ("missing-dependency", "Missing dependency target"),
        ("self-dependency", "Self dependency"),
        ("cycle", "Dependency cycle"),
        ("invalid-status", "Invalid status"),
        ("invalid-blocked-reason", "Invalid blocked reason"),
        ("invalid-review-reason", "Invalid review reason"),
    ]

    for case_name, expected_text in cases:
        case_root = project_root / case_name
        init_result = run_command([sys.executable, str(init_script), "--root", str(case_root)])
        assert_ok(init_result, f"init_context_governor {case_name}")

        context_dir = case_root / ".codex" / "context"
        checklist_path = case_root / "docs" / "implementation" / "checklist.md"
        seeded_plan = load_json(context_dir / "doc-plan.json")
        write_text(
            checklist_path,
            render_invalid_checklist(seeded_plan["plan_id"], seeded_plan["title"], case_name),
        )

        settle_result = run_command([sys.executable, str(settle_script), "--root", str(case_root)])
        assert_failed(settle_result, f"settle_checklist_context_governor {case_name}", expected_text)


def validate_resume_manifest_boundary(project_root: Path) -> None:
    init_script = SCRIPTS_DIR / "init_context_governor.py"
    settle_script = SCRIPTS_DIR / "settle_checklist_context_governor.py"
    resume_script = SCRIPTS_DIR / "resume_context_governor.py"
    sync_script = SCRIPTS_DIR / "sync_progress_context_governor.py"
    closeout_script = SCRIPTS_DIR / "closeout_context_governor.py"

    init_result = run_command([sys.executable, str(init_script), "--root", str(project_root)])
    assert_ok(init_result, "init_context_governor manifest-boundary")

    context_dir = project_root / ".codex" / "context"
    checklist_path = project_root / "docs" / "implementation" / "checklist.md"
    seeded_plan = load_json(context_dir / "doc-plan.json")
    write_text(
        checklist_path,
        render_validation_checklist(seeded_plan["plan_id"], seeded_plan["title"]),
    )

    settle_result = run_command([sys.executable, str(settle_script), "--root", str(project_root)])
    assert_ok(settle_result, "settle_checklist_context_governor manifest-boundary")

    resume_result = run_command([sys.executable, str(resume_script), "--root", str(project_root)])
    assert_ok(resume_result, "resume_context_governor manifest-boundary")

    manifest_path = context_dir / "resume-manifest.json"
    manifest_before = manifest_path.read_text(encoding="utf-8")

    sync_result = run_command(
        [
            sys.executable,
            str(sync_script),
            "--root",
            str(project_root),
            "--task",
            "T-002",
            "--status",
            "done",
            "--evidence",
            "manifest-boundary-sync",
        ]
    )
    assert_ok(sync_result, "sync_progress_context_governor manifest-boundary")

    closeout_result = run_command(
        [sys.executable, str(closeout_script), "--root", str(project_root)]
    )
    assert_ok(closeout_result, "closeout_context_governor manifest-boundary")

    manifest_after = manifest_path.read_text(encoding="utf-8")
    if manifest_after != manifest_before:
        raise RuntimeError(
            "resume-manifest.json changed after sync/closeout even though it should remain "
            "a resume-only observability output."
        )


def validate_prd_escalation(project_root: Path) -> None:
    init_script = SCRIPTS_DIR / "init_context_governor.py"
    settle_script = SCRIPTS_DIR / "settle_checklist_context_governor.py"
    resume_script = SCRIPTS_DIR / "resume_context_governor.py"

    init_result = run_command([sys.executable, str(init_script), "--root", str(project_root)])
    assert_ok(init_result, "init_context_governor prd-escalation")

    context_dir = project_root / ".codex" / "context"
    checklist_path = project_root / "docs" / "implementation" / "checklist.md"
    seeded_plan = load_json(context_dir / "doc-plan.json")
    write_text(
        checklist_path,
        render_prd_escalation_checklist(seeded_plan["plan_id"], seeded_plan["title"]),
    )

    settle_result = run_command([sys.executable, str(settle_script), "--root", str(project_root)])
    assert_ok(settle_result, "settle_checklist_context_governor prd-escalation")

    focus_path = context_dir / "focus-set.json"
    if focus_path.exists():
        focus_path.unlink()
    if checklist_path.exists():
        checklist_path.unlink()

    resume_result = run_command([sys.executable, str(resume_script), "--root", str(project_root)])
    assert_ok(resume_result, "resume_context_governor prd-escalation")

    active_context = load_json(context_dir / "active-context.json")
    resume_manifest = load_json(context_dir / "resume-manifest.json")
    budget_report = load_json(context_dir / "budget-report.json")
    next_prompt = (context_dir / "next-session-prompt.md").read_text(encoding="utf-8")

    expected_reads = [
        ".codex/context/active-context.md",
        ".codex/context/latest-snapshot.json",
        "docs/prd/approved-prd.md",
    ]
    for label, payload in (
        ("active-context.json", active_context),
        ("resume-manifest.json", resume_manifest),
    ):
        if payload.get("recommended_context_level") != "prd_required":
            raise RuntimeError(f"{label} did not escalate this path to prd_required")
        if payload.get("recommended_files_to_read") != expected_reads:
            raise RuntimeError(
                f"{label} did not order the PRD escalation path as active-context -> "
                f"latest-snapshot -> approved-prd. Saw: {payload.get('recommended_files_to_read')!r}"
            )
        if payload.get("next_allowed_reads") != []:
            raise RuntimeError(f"{label} did not terminate widening after the required PRD read")
        if payload.get("stop_reading_after") != "docs/prd/approved-prd.md":
            raise RuntimeError(f"{label} did not stop at docs/prd/approved-prd.md")

    if active_context.get("doc_refs") != ["docs/prd/approved-prd.md"]:
        raise RuntimeError("active-context.json did not expose the full-PRD fallback doc ref")
    if not active_context.get("gate_flags", {}).get("needs_full_prd"):
        raise RuntimeError("active-context.json did not mark the missing targeted-doc-ref path as needs_full_prd")
    if not resume_manifest.get("full_prd_fallback"):
        raise RuntimeError("resume-manifest.json did not record the full PRD fallback")

    current_recommendation = budget_report.get("current_recommendation", {})
    if current_recommendation.get("recommended_context_level") != "prd_required":
        raise RuntimeError("budget-report.json did not reflect the prd_required escalation")
    if current_recommendation.get("recommended_files_to_read") != expected_reads:
        raise RuntimeError(
            "budget-report.json did not preserve the PRD escalation order through "
            "latest-snapshot.json before the full PRD"
        )

    if "Read .codex/context/latest-snapshot.json now because this task already requires the settled project structure." not in next_prompt:
        raise RuntimeError(
            "next-session-prompt.md did not explain why latest-snapshot.json is required for the PRD escalation path"
        )
    if "Read docs/prd/approved-prd.md now because this task already requires the source requirement text." not in next_prompt:
        raise RuntimeError(
            "next-session-prompt.md did not explain why docs/prd/approved-prd.md is required for the PRD escalation path"
        )
    if "Do not read docs/prd/approved-prd.md unless latest-snapshot.json still cannot resolve the referenced requirement safely." in next_prompt:
        raise RuntimeError(
            "next-session-prompt.md kept the restrictive PRD line even though the PRD is already required"
        )
    assert_prompt_policy_alignment(next_prompt)


def validate_closeout_lifecycle(project_root: Path) -> None:
    init_script = SCRIPTS_DIR / "init_context_governor.py"
    settle_script = SCRIPTS_DIR / "settle_checklist_context_governor.py"
    resume_script = SCRIPTS_DIR / "resume_context_governor.py"
    sync_script = SCRIPTS_DIR / "sync_progress_context_governor.py"
    closeout_script = SCRIPTS_DIR / "closeout_context_governor.py"

    init_result = run_command([sys.executable, str(init_script), "--root", str(project_root)])
    assert_ok(init_result, "init_context_governor closeout-lifecycle")

    context_dir = project_root / ".codex" / "context"
    checklist_path = project_root / "docs" / "implementation" / "checklist.md"
    seeded_plan = load_json(context_dir / "doc-plan.json")
    write_text(
        checklist_path,
        render_validation_checklist(seeded_plan["plan_id"], seeded_plan["title"]),
    )

    settle_result = run_command([sys.executable, str(settle_script), "--root", str(project_root)])
    assert_ok(settle_result, "settle_checklist_context_governor closeout-lifecycle")

    resume_result = run_command([sys.executable, str(resume_script), "--root", str(project_root)])
    assert_ok(resume_result, "resume_context_governor closeout-lifecycle")

    sync_result = run_command(
        [
            sys.executable,
            str(sync_script),
            "--root",
            str(project_root),
            "--task",
            "T-002",
            "--status",
            "done",
            "--evidence",
            "closeout-lifecycle-sync",
        ]
    )
    assert_ok(sync_result, "sync_progress_context_governor closeout-lifecycle")

    history_path = context_dir / "sync-history.ndjson"
    history_before = load_ndjson(history_path)
    expected_current_task_id = load_json(context_dir / "latest-snapshot.json").get("current_task_id")

    closeout_result = run_command(
        [sys.executable, str(closeout_script), "--root", str(project_root)]
    )
    assert_ok(closeout_result, "closeout_context_governor closeout-lifecycle")

    history_after = load_ndjson(history_path)
    if len(history_after) != len(history_before) + 1:
        raise RuntimeError("closeout did not append exactly one event to sync-history.ndjson")
    if history_after[:-1] != history_before:
        raise RuntimeError("sync-history.ndjson was rewritten instead of growing append-only on closeout")

    latest_history_event = history_after[-1]
    if latest_history_event.get("event") != "closeout":
        raise RuntimeError("sync-history.ndjson did not append closeout as the latest event")

    session_delta = load_json(context_dir / "session-delta.json")
    history_rollup = load_json(context_dir / "history-rollup.json")
    snapshot = load_json(context_dir / "latest-snapshot.json")
    focus_set = load_json(context_dir / "focus-set.json")

    latest_session_event = session_delta.get("latest_event", {})
    if latest_session_event.get("event") != "closeout":
        raise RuntimeError("session-delta.json did not refresh latest_event to closeout")
    if latest_session_event.get("current_task_id") != expected_current_task_id:
        raise RuntimeError("session-delta.json did not preserve the closeout current task")
    if not history_rollup.get("recent_events"):
        raise RuntimeError("history-rollup.json dropped recent events during closeout")
    if history_rollup["recent_events"][-1].get("event") != "closeout":
        raise RuntimeError("history-rollup.json did not append closeout as the latest recent event")
    if snapshot.get("current_task_id") != expected_current_task_id:
        raise RuntimeError("closeout changed current_task_id unexpectedly")
    if focus_set.get("current_task_id") != expected_current_task_id:
        raise RuntimeError("focus-set.json changed current_task_id unexpectedly during closeout")


def validate_stale_blocker_cleanup(project_root: Path) -> None:
    init_script = SCRIPTS_DIR / "init_context_governor.py"
    settle_script = SCRIPTS_DIR / "settle_checklist_context_governor.py"
    closeout_script = SCRIPTS_DIR / "closeout_context_governor.py"

    init_result = run_command([sys.executable, str(init_script), "--root", str(project_root)])
    assert_ok(init_result, "init_context_governor stale-blocker-cleanup")

    context_dir = project_root / ".codex" / "context"
    checklist_path = project_root / "docs" / "implementation" / "checklist.md"
    seeded_plan = load_json(context_dir / "doc-plan.json")
    write_text(
        checklist_path,
        render_validation_checklist(seeded_plan["plan_id"], seeded_plan["title"]),
    )

    settle_result = run_command([sys.executable, str(settle_script), "--root", str(project_root)])
    assert_ok(settle_result, "settle_checklist_context_governor stale-blocker-cleanup")

    state_path = context_dir / "latest-state.json"
    state = load_json(state_path)
    state_index = {task["id"]: task for task in state["tasks"]}
    state_index["T-002"]["blocked_reason"] = "stale blocker should not survive settlement"
    write_text(state_path, json.dumps(state, indent=2))

    closeout_result = run_command([sys.executable, str(closeout_script), "--root", str(project_root)])
    assert_ok(closeout_result, "closeout_context_governor stale-blocker-cleanup")

    snapshot = load_json(context_dir / "latest-snapshot.json")
    snapshot_index = {task["id"]: task for task in snapshot["tasks"]}
    active_context = load_json(context_dir / "active-context.json")
    checklist_text = checklist_path.read_text(encoding="utf-8")

    if "blocked_reason" in snapshot_index["T-002"]:
        raise RuntimeError("latest-snapshot.json kept blocked_reason on a non-blocked task")
    if active_context.get("blocked_reason"):
        raise RuntimeError("active-context.json kept blocked_reason on a non-blocked current task")
    if "stale blocker should not survive settlement" in checklist_text:
        raise RuntimeError("checklist.md rendered a stale blocked reason for a non-blocked task")


def validate_sync_state_reason_cleanup(project_root: Path) -> None:
    init_script = SCRIPTS_DIR / "init_context_governor.py"
    settle_script = SCRIPTS_DIR / "settle_checklist_context_governor.py"
    sync_script = SCRIPTS_DIR / "sync_progress_context_governor.py"

    init_result = run_command([sys.executable, str(init_script), "--root", str(project_root)])
    assert_ok(init_result, "init_context_governor sync-state-reason-cleanup")

    context_dir = project_root / ".codex" / "context"
    checklist_path = project_root / "docs" / "implementation" / "checklist.md"
    seeded_plan = load_json(context_dir / "doc-plan.json")
    write_text(
        checklist_path,
        render_validation_checklist(seeded_plan["plan_id"], seeded_plan["title"]),
    )

    settle_result = run_command([sys.executable, str(settle_script), "--root", str(project_root)])
    assert_ok(settle_result, "settle_checklist_context_governor sync-state-reason-cleanup")

    state_path = context_dir / "latest-state.json"
    state = load_json(state_path)
    state_index = {task["id"]: task for task in state["tasks"]}
    state_index["T-001"]["review_reason"] = "stale review should not survive sync normalization"
    state_index["T-003"]["blocked_reason"] = "stale blocker should not survive sync normalization"
    write_text(state_path, json.dumps(state, indent=2))

    sync_result = run_command(
        [
            sys.executable,
            str(sync_script),
            "--root",
            str(project_root),
            "--task",
            "T-002",
            "--status",
            "in_progress",
            "--evidence",
            "active-work",
        ]
    )
    assert_ok(sync_result, "sync_progress_context_governor sync-state-reason-cleanup")

    synced_state = load_json(state_path)
    synced_index = {task["id"]: task for task in synced_state["tasks"]}

    if "review_reason" in synced_index["T-001"]:
        raise RuntimeError(
            "latest-state.json kept review_reason on a non-needs_review task after sync normalization"
        )
    if "blocked_reason" in synced_index["T-003"]:
        raise RuntimeError(
            "latest-state.json kept blocked_reason on a non-blocked task after sync normalization"
        )


def validate_projection_dedup(project_root: Path) -> None:
    init_script = SCRIPTS_DIR / "init_context_governor.py"
    settle_script = SCRIPTS_DIR / "settle_checklist_context_governor.py"

    init_result = run_command([sys.executable, str(init_script), "--root", str(project_root)])
    assert_ok(init_result, "init_context_governor projection-dedup")

    context_dir = project_root / ".codex" / "context"
    checklist_path = project_root / "docs" / "implementation" / "checklist.md"
    graph_render_path = project_root / "docs" / "implementation" / "current-graph.mmd"
    seeded_plan = load_json(context_dir / "doc-plan.json")
    write_text(
        checklist_path,
        render_duplicate_dependency_checklist(seeded_plan["plan_id"], seeded_plan["title"]),
    )

    settle_result = run_command([sys.executable, str(settle_script), "--root", str(project_root)])
    assert_ok(settle_result, "settle_checklist_context_governor projection-dedup")

    doc_plan = load_json(context_dir / "doc-plan.json")
    snapshot = load_json(context_dir / "latest-snapshot.json")
    graph = load_json(context_dir / "latest-task-graph.json")
    checklist_text = checklist_path.read_text(encoding="utf-8")
    graph_text = graph_render_path.read_text(encoding="utf-8")

    doc_index = {task["id"]: task for task in doc_plan["tasks"]}
    snapshot_index = {task["id"]: task for task in snapshot["tasks"]}
    graph_index = {task["id"]: task for task in graph["tasks"]}

    expected_dependencies = ["T-001"]
    if doc_index["T-002"].get("depends_on") != expected_dependencies:
        raise RuntimeError("doc-plan.json did not normalize duplicate dependency entries")
    if snapshot_index["T-002"].get("depends_on") != expected_dependencies:
        raise RuntimeError("latest-snapshot.json did not normalize duplicate dependency entries")
    if graph_index["T-002"].get("depends_on") != expected_dependencies:
        raise RuntimeError("latest-task-graph.json did not normalize duplicate dependency entries")
    if "- Depends On: T-001, T-001" in checklist_text:
        raise RuntimeError("checklist.md still rendered duplicate dependency entries")
    if "- Depends On: T-001" not in checklist_text:
        raise RuntimeError("checklist.md did not preserve the normalized dependency entry")
    if graph_text.count("T-001 --> T-002") != 1:
        raise RuntimeError("current-graph.mmd did not project the dependency edge exactly once")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a quick validation pass for the context-governor skill."
    )
    parser.add_argument(
        "--keep-temp",
        action="store_true",
        help="Keep the temporary smoke-test project instead of deleting it",
    )
    args = parser.parse_args()

    validate_py_compile()
    print("PASS py_compile")
    validate_reference_consistency()
    print("PASS references")
    validate_resume_pack_contract()
    print("PASS resume-pack-contract")

    with tempfile.TemporaryDirectory(prefix="context-governor-validate-") as temp_dir:
        temp_root = Path(temp_dir)
        validate_smoke(temp_root / "linear-flow")
        print(f"PASS smoke {temp_root / 'linear-flow'}")
        validate_resume_manifest_boundary(temp_root / "resume-manifest-boundary")
        print(f"PASS resume-manifest-boundary {temp_root / 'resume-manifest-boundary'}")
        validate_prd_escalation(temp_root / "prd-escalation")
        print(f"PASS prd-escalation {temp_root / 'prd-escalation'}")
        validate_closeout_lifecycle(temp_root / "closeout-lifecycle")
        print(f"PASS closeout-lifecycle {temp_root / 'closeout-lifecycle'}")
        validate_ambiguity(temp_root / "branch-ambiguity")
        print(f"PASS ambiguity {temp_root / 'branch-ambiguity'}")
        validate_structure_lint(temp_root / "structure-lint")
        print(f"PASS structure-lint {temp_root / 'structure-lint'}")
        validate_sync_state_reason_cleanup(temp_root / "sync-state-reason-cleanup")
        print(f"PASS sync-state-reason-cleanup {temp_root / 'sync-state-reason-cleanup'}")
        validate_stale_blocker_cleanup(temp_root / "stale-blocker-cleanup")
        print(f"PASS stale-blocker-cleanup {temp_root / 'stale-blocker-cleanup'}")
        validate_projection_dedup(temp_root / "projection-dedup")
        print(f"PASS projection-dedup {temp_root / 'projection-dedup'}")

        if args.keep_temp:
            kept_root = temp_root.parent / f"{temp_root.name}-kept"
            if kept_root.exists():
                raise FileExistsError(f"Keep target already exists: {kept_root}")
            temp_root.rename(kept_root)
            print(f"KEEP {kept_root}")

    print("READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
