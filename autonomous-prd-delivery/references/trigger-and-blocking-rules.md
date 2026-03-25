# Trigger And Blocking Rules

## Invocation Cues

Treat requests like these as strong signals to use this skill:

- `根据 PRD 自动研发直到全部完成`
- `按流程图继续做，不要中途打断`
- `continue until all required work is done`
- `keep shipping from the PRD without milestone pauses`
- `自动研发`
- `继续做到全部完成`
- `不要中途打断`
- `别问我要不要继续，直接做完`

## Recognizable Durable Project Inputs

Treat any of these as strong repo-level execution inputs when they define scope, sequencing, execution rules, or current status:

- `Prompt.md`, `Plan.md`, `Implement.md`, `Documentation.md`
- `docs/Prompt.md`, `docs/Plan.md`, `docs/Implement.md`, `docs/Documentation.md`
- similarly named files under `docs/project/`, `docs/delivery/`, `docs/protocol/`, or `.codex/`

## Recognizable PRD And Spec Inputs

Treat any of these as qualifying written inputs when they describe scope, requirements, flows, or acceptance criteria:

- `PRD.md`, `prd.md`, `requirements.md`, `spec.md`, `design.md`
- `approved-prd.md`
- files under `docs/prd/`, `docs/specs/`, `docs/design/`, `docs/requirements/`
- product or feature docs that define modules, user flows, or acceptance criteria

## Recognizable Flow Inputs

Treat any of these as qualifying flow representations:

- Mermaid in markdown: `flowchart`, `graph TD`, `graph LR`, `stateDiagram`, `sequenceDiagram`
- drawio files: `*.drawio`
- diagrams named with `flow`, `workflow`, `state`, `sequence`, `process`
- images or PDFs that clearly represent process or state flow

## Trigger Scan Order

Scan for entry signals in this order so resume is narrow and deterministic:

1. explicit user request for autonomous execution or no interruption
2. `.codex/context/active-context.md`
3. `.codex/context/latest-snapshot.json`
4. repo `Documentation.md`
5. repo `Plan.md`
6. repo `Prompt.md`, the approved PRD, or another spec doc
7. repo `Implement.md`
8. repo-local flowchart artifacts
9. task or progress docs that identify the next ready task

If the user explicitly asks for uninterrupted PRD-driven execution, do not wait for a second confirmation when the repo already contains enough context to proceed.

## Repo Protocol Priority

When repo protocol docs exist, use them with this split of authority:

- scope and acceptance: `Prompt.md` or approved PRD
- execution discipline: `Implement.md`
- ordering and current status: `Plan.md` and `Documentation.md`
- machine-readable resume state: `.codex/context/`
- final reality check: current code plus fresh verification evidence

If a status doc conflicts with current code or tests, repair the stale doc instead of obeying it blindly.

## Session Fallback Invocation

If the current session does not recognize `$autonomous-prd-delivery`, treat that as a session-visibility problem first, not proof that the skill is missing from disk.

Preferred recovery:

1. start a new session in the target repo
2. invoke `$autonomous-prd-delivery` again

If a new session is not practical, use a direct file-path fallback so the model can read the skill body as instructions:

- `Read and follow C:\Users\WeiZhaoyuan\.codex\skills\autonomous-prd-delivery\SKILL.md as the process guide for this task. Detect Prompt.md, Plan.md, Implement.md, Documentation.md, the PRD/specs, and flowcharts in this repo, resume from repo docs plus .codex/context/ when available, keep implementing and verifying the next ready task without milestone permission checkpoints, and stop only for real blockers.`
- `Read and follow C:\Users\WeiZhaoyuan\.codex\skills\autonomous-prd-delivery\SKILL.md. Continue from the repo PRD, project docs, and flowcharts until all required work is complete, updating repo progress docs and .codex/context/ as you go and only stopping for true blockers.`

## Resume Order

When resuming after interruption or a new session, reload in this order:

1. `.codex/context/active-context.md`
2. `.codex/context/latest-snapshot.json`
3. `Documentation.md`
4. `Plan.md`
5. the last completed task and the next ready task
6. `Prompt.md`, the PRD/spec, and only the flow slices needed for the resumed task
7. broader repo context only if the saved state is incomplete

Favor narrow recovery over full rediscovery.

## Continue Vs Stop

| Situation | Action | Why |
|--------|--------|-----|
| A task finished and the next task is clear | Continue | Progress alone is not a blocker |
| Minor naming or copy detail is missing | Continue and log assumption | Low risk |
| The repo docs and `.codex/context/` need syncing | Continue and sync them | Normal execution |
| The user has not explicitly said "continue" | Continue | This skill removes checkpoint pauses |
| Core PRD sections contradict each other | Stop | Requirement conflict |
| Auth, billing, schema, or security decision is unresolved | Stop | High risk |
| Credentials or required services are unavailable | Stop | External blocker |
| Verification keeps failing after debugging | Stop | Likely wrong path or broken environment |

## Low-Risk Assumption Examples

- choosing a neutral button label
- selecting a local helper name
- defaulting a non-critical optional field to empty string or false
- sequencing two independent tasks based on dependency order
- creating obvious fixture data for tests

## False Blockers

Do not stop for these alone:

- finishing a phase, milestone, or checklist section
- wanting to summarize before the next task
- the user not explicitly typing `continue`
- minor copy, naming, or placeholder content choices
- needing to sync repo progress docs or `.codex/context/`
- finding an obvious next task in the existing plan
- waiting for permission to run the default next verification step

These are normal execution conditions, not blockers.

## High-Risk Pause Examples

- deciding whether a destructive migration is allowed
- inventing payment refund rules
- choosing who may access an admin-only endpoint
- changing a public webhook contract without a source requirement
- weakening production security defaults to get tests unstuck

## Smoke Check Prompts

Use prompts like these when checking whether the skill reads clearly:

- `Use $autonomous-prd-delivery to detect Prompt.md, Plan.md, Implement.md, Documentation.md, the PRD, and Mermaid flows, then keep implementing until all required tasks are complete.`
- `Use $autonomous-prd-delivery to resume from repo docs plus .codex/context/ and continue shipping instead of stopping after each milestone.`
- `Use $autonomous-prd-delivery to stop only for real blockers while working through the approved PRD and repo delivery docs.`
- `Use $autonomous-prd-delivery to continue from the repo PRD, keep syncing project docs and saved state, and do not ask permission between milestones.`
- `使用 $autonomous-prd-delivery 根据 Prompt.md、Plan.md、PRD 和流程图自动研发，继续做到全部完成。`
- `使用 $autonomous-prd-delivery，不要中途打断，持续同步 Documentation.md 和 .codex/context/，除非遇到真实阻塞再停。`
- `Read and follow C:\Users\WeiZhaoyuan\.codex\skills\autonomous-prd-delivery\SKILL.md as the process guide for this task, then continue from the repo PRD and project docs until all required work is complete.`
