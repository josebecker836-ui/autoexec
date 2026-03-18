# 中文极简操作手册

## 适用场景
当你想把一个长期项目的上下文压缩成可复用状态，而不是每次都重新粘贴 PRD、历史进度和待办说明时，就用这份手册。

如果你只想要一页能直接复制的超短版本，先看：
- `references/cheatsheet-zh.md`

如果你是在一个全新项目里第一次接入，先看：
- `references/new-project-template.md`

## 核心原则
- 人看 `docs/implementation/*`
- 机器看 `.codex/context/*`
- 两层都可以编辑，但每次都要结算到同一个 `latest-snapshot.json`
- 恢复上下文时默认按 `active-context -> session-delta -> history-rollup -> latest-snapshot -> PRD` 逐层扩容

## 第一次进入项目
在项目根目录运行：

```cmd
python C:\Users\WeiZhaoyuan\.codex\skills\context-governor\scripts\init_context_governor.py --root .
```

然后把 PRD 放到：

```text
docs/prd/approved-prd.md
```

再对 Codex 说：

```text
Use $context-governor to break docs/prd/approved-prd.md into an ordered checklist, dependency graph, and initial snapshot.
```

等 Codex 把 `docs/implementation/checklist.md` 写好或改好后，立刻结算一次：

```cmd
python C:\Users\WeiZhaoyuan\.codex\skills\context-governor\scripts\settle_checklist_context_governor.py --root .
```

如果结算失败，先修清单结构再重跑。重复任务 ID、缺失依赖目标、自依赖、依赖环都会在结算前被直接拦下，不会继续污染 snapshot。

## 日常开发只记 3 个动作

### 1. 完成或卡住一个任务后，立刻同步

```cmd
python C:\Users\WeiZhaoyuan\.codex\skills\context-governor\scripts\sync_progress_context_governor.py --root . --task T-001 --status done --evidence shipped-checklist
```

如果是阻塞：

```cmd
python C:\Users\WeiZhaoyuan\.codex\skills\context-governor\scripts\sync_progress_context_governor.py --root . --task T-001 --status blocked --blocked-reason waiting-on-api --evidence found-blocker
```

这一步会同时更新：
- `.codex/context/active-context.json`
- `.codex/context/active-context.md`
- `.codex/context/session-delta.json`
- `.codex/context/session-delta.md`
- `.codex/context/history-rollup.json`
- `.codex/context/history-rollup.md`
- `.codex/context/budget-report.json`
- `.codex/context/budget-report.md`
- `.codex/context/latest-state.json`
- `.codex/context/latest-snapshot.json`
- `.codex/context/latest-task-graph.json`
- `.codex/context/focus-set.json`
- `.codex/context/resume-pack.md`
- `.codex/context/next-session-prompt.md`
- `docs/implementation/checklist.md`
- `docs/implementation/current-graph.mmd`

还会追加一条事件到：
- `.codex/context/sync-history.ndjson`

如果你把任务同步成 `done`，但没有提供足够强的完成证据，系统会自动降级成 `needs_review`，并把原因写进 snapshot、resume pack 和 checklist 里的 `Review Reason`。

### 2. 下次继续开发前，先恢复最小上下文

```cmd
python C:\Users\WeiZhaoyuan\.codex\skills\context-governor\scripts\resume_context_governor.py --root .
```

这一步会同时刷新：
- `.codex/context/focus-set.json`
- `.codex/context/active-context.json`
- `.codex/context/active-context.md`
- `.codex/context/session-delta.json`
- `.codex/context/session-delta.md`
- `.codex/context/history-rollup.json`
- `.codex/context/history-rollup.md`
- `.codex/context/budget-report.json`
- `.codex/context/budget-report.md`
- `.codex/context/resume-pack.md`
- `.codex/context/next-session-prompt.md`
- `.codex/context/resume-manifest.json`

还会追加一条事件到：
- `.codex/context/sync-history.ndjson`

先看这个最小活跃上下文：

```text
.codex/context/active-context.md
```

如果你需要最近一次会话交接，再补看：

```text
.codex/context/session-delta.md
```

它是 `active-context` 之后的第一层扩容，只保留最近一次最关键的交接信息，不是新的 canonical 状态。

如果 `session-delta.md` 还不够，再补看：

```text
.codex/context/history-rollup.md
```

如果你想先量化“继续扩容上下文要多花多少输入”，再看：

```text
.codex/context/budget-report.md
```

然后优先复制这个文件里的提示词：

```text
.codex/context/next-session-prompt.md
```

同时看 `active-context.md` 里的 `Context Gate`：
- `Read Now` 是这一轮真正建议读取的文件
- `Stop Reading After` 是默认停读点
- `Next Allowed Reads` 是下一层唯一允许扩容的入口

或者只对 Codex 说：

```text
Use $context-governor to resume this project from .codex/context/active-context.md, widen to .codex/context/session-delta.md before broader history, fall back to .codex/context/latest-snapshot.json only if needed, and tell me the next task with the smallest necessary context.
```

### 3. 结束今天的会话时，做一次结算
当日任务状态和证据已经通过 `sync_progress_context_governor.py` 同步进 `.codex/context/latest-state.json` 后，再运行：

```cmd
python C:\Users\WeiZhaoyuan\.codex\skills\context-governor\scripts\closeout_context_governor.py --root .
```

如果你这次改的是任务结构本身，比如重排依赖、补全任务、从 PRD 重新整理清单，不要只做 closeout，要先运行：

```cmd
python C:\Users\WeiZhaoyuan\.codex\skills\context-governor\scripts\settle_checklist_context_governor.py --root .
```

这里如果报结构错误，不要跳过，先修 `checklist.md` 再继续。

项目内固定操作手册位置：

```text
docs/implementation/context-governor-playbook.md
```

## 一条命令自检
当你改过这个 skill，或者想确认整套脚本还能协同工作时，运行：

```cmd
python C:\Users\WeiZhaoyuan\.codex\skills\context-governor\scripts\quick_validate.py
```

它会自动验证：
- 所有脚本能否通过编译
- 关键参考文档和当前脚本行为是否保持契约一致
- `init`
- `settle_checklist`
- 结构 lint 是否能拦住重复 ID、缺失依赖、自依赖、依赖环
- `resume`
- `next-session-prompt` 是否保持自洽，不会一边要求读取某个文件一边又写成“不要读”
- `sync_progress`
- 弱证据完成时是否自动降级为 `needs_review` 并写入 `Review Reason`
- 多个 ready 任务并列时是否写入歧义 warning
- `closeout`

## 最省 token 的使用方式
不要每次都重新输入：
- 完整 PRD
- 已完成历史
- 当前做到哪里
- 依赖关系说明

改成固定顺序：
1. 运行 `resume_context_governor.py`
2. 先让 Codex 从 `.codex/context/active-context.md` 开始
3. 先按 `Context Gate` 的 `Read Now` 读取，并在 `Stop Reading After` 停住
4. 先看 `.codex/context/budget-report.md`，判断这次推荐层级的成本
5. 只按 `Next Allowed Reads` 逐层扩容，第一跳通常是 `.codex/context/session-delta.md`
6. 如果最近一次交接还不够，再继续到 `.codex/context/history-rollup.md`
7. 只有当前切片仍然不够时再回退到 `.codex/context/latest-snapshot.json`
8. 只围绕当前 `T-xxx` 任务继续

## 常用提示词

### 从 PRD 生成实现清单

```text
Use $context-governor to break docs/prd/approved-prd.md into an ordered checklist, dependency graph, and initial snapshot.
```

### 从零散文档重建计划

```text
Use $context-governor to rebuild this project from scattered docs and mark which tasks are confirmed versus inferred.
```

重建后的清单也要再跑一次：

```cmd
python C:\Users\WeiZhaoyuan\.codex\skills\context-governor\scripts\settle_checklist_context_governor.py --root .
```

### 同步今天的开发进度

```text
Use $context-governor to sync progress after today's work and only mark tasks done where evidence exists.
```

### 用最小上下文恢复项目

```text
Use $context-governor to resume this project from .codex/context/active-context.md, widen to .codex/context/session-delta.md before broader history, fall back to .codex/context/latest-snapshot.json only if needed, and tell me the next task with the smallest necessary context.
```

### 结束今天的会话并结算

```text
Use $context-governor to close out today's session. If today's task status or evidence has not been synced yet, sync it first. If you changed task structure in `docs/implementation/checklist.md`, settle the checklist first. Then refresh the latest snapshot, graph, and resume pack for the next session.
```

## 状态怎么用
- `todo`: 还没开始
- `in_progress`: 正在做
- `done`: 已完成，而且有证据
- `blocked`: 卡住了，需要 blocker
- `needs_review`: 做了，但还需要复核
- `conflict`: 文档、代码或状态互相冲突

## 你真正要养成的习惯
- 不要靠聊天记录记项目状态
- 不要靠整份 PRD 反复喂模型
- 做完一个任务就同步一次
- 下次开工先恢复，再继续写代码

如果你照这个流程走，后续会话的输入会从“整项目背景”收缩成“当前任务和少量依赖”。
