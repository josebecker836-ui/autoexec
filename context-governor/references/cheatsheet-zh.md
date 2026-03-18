# 中文单屏速查卡

## 你只需要记住这 5 条命令

### 1. 初始化项目
```cmd
python C:\Users\WeiZhaoyuan\.codex\skills\context-governor\scripts\init_context_governor.py --root .
```

### 2. 改了清单结构后结算
```cmd
python C:\Users\WeiZhaoyuan\.codex\skills\context-governor\scripts\settle_checklist_context_governor.py --root .
```

如果这里报错，先修 `checklist.md`。重复 ID、缺失依赖、自依赖、依赖环现在都会被直接拦下。

### 3. 完成或卡住一个任务后同步
```cmd
python C:\Users\WeiZhaoyuan\.codex\skills\context-governor\scripts\sync_progress_context_governor.py --root . --task T-001 --status done --evidence shipped-checklist
```

阻塞时：
```cmd
python C:\Users\WeiZhaoyuan\.codex\skills\context-governor\scripts\sync_progress_context_governor.py --root . --task T-001 --status blocked --blocked-reason waiting-on-api --evidence found-blocker
```

### 4. 下次开工前恢复最小上下文
```cmd
python C:\Users\WeiZhaoyuan\.codex\skills\context-governor\scripts\resume_context_governor.py --root .
```

恢复后优先复制：
```text
.codex/context/next-session-prompt.md
```

如果你想先确认这一轮建议读取哪些文件，再看 `.codex/context/resume-manifest.json`：
```text
.codex/context/resume-manifest.json
```

恢复后默认先看：
```text
.codex/context/active-context.md
```

并且先看里面这三行：
- `Read Now`
- `Stop Reading After`
- `Next Allowed Reads`

只有需要最近一次会话交接时再看：
```text
.codex/context/session-delta.md
```

如果 `session-delta.md` 还不够，再看：
```text
.codex/context/history-rollup.md
```

要先估算继续扩容上下文要花多少输入时，看：
```text
.codex/context/budget-report.md
```

### 5. 会话结束后结算
当天任务状态和证据先通过 `sync_progress_context_governor.py` 同步后，再运行：

```cmd
python C:\Users\WeiZhaoyuan\.codex\skills\context-governor\scripts\closeout_context_governor.py --root .
```

## 你只需要记住这 3 句提示词

### 从 PRD 建立计划
```text
Use $context-governor to break docs/prd/approved-prd.md into an ordered checklist, dependency graph, and initial snapshot.
```

写完或重写 `checklist.md` 后，记得执行一次 `settle_checklist_context_governor.py`。

### 同步今天的进度
```text
Use $context-governor to sync progress after today's work and only mark tasks done where evidence exists.
```

### 用最小上下文继续开发
```text
Use $context-governor to resume this project from .codex/context/active-context.md, widen to .codex/context/session-delta.md before broader history, fall back to .codex/context/latest-snapshot.json only if needed, and tell me the next task with the smallest necessary context.
```

## 状态速记
- `todo`: 未开始
- `in_progress`: 正在做
- `done`: 完成且有证据
- `blocked`: 被阻塞
- `needs_review`: 待复核
- `conflict`: 状态冲突

如果把任务标成 `done` 但没有有效证据，它会自动落回 `needs_review`，并补一条 `Review Reason`。

## 最重要的习惯
- 不要重复粘贴整份 PRD
- 不要靠聊天记录记状态
- 做完一个 `T-xxx` 就同步
- 下次优先复制 `.codex/context/next-session-prompt.md`
- 下次先 `resume` 再继续
- 扩容到 snapshot 之前，先看一眼 `.codex/context/budget-report.md`

## 最省 token 的固定顺序
1. 运行 `resume_context_governor.py`
2. 读取 `.codex/context/active-context.md`
3. 按 `Read Now` 读取，并在 `Stop Reading After` 停住
4. 先看 `.codex/context/budget-report.md` 判断这次推荐层级的成本
5. 只按 `Next Allowed Reads` 逐层扩容，默认第一跳是 `.codex/context/session-delta.md`
6. 如果第一跳还不够，再补看 `.codex/context/history-rollup.md`
7. 只有当前切片仍然不够时再读 `.codex/context/latest-snapshot.json`
8. 只围绕当前任务继续
