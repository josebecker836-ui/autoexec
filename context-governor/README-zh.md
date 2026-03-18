# Context Governor 中文说明

可复用的 Codex skill，适合长期项目里的上下文治理：把 PRD 结算成实现清单和依赖关系，把人类可读文档与机器状态同步起来，并且让后续会话尽量从最小上下文恢复，而不是反复重喂整份项目背景。

## 它解决什么问题

- 把已确认的 PRD 转成有稳定任务 ID 的实现清单。
- 生成依赖关系图或 Mermaid 任务图。
- 让 `docs/implementation/*` 和 `.codex/context/*` 持续同步。
- 每次完成目标后，把完成证据同步回清单、图和 snapshot。
- 下次继续开发时，直接知道应该从哪个任务接着做，而不是重新读完整项目。

## 为什么它能压缩输入 Token

这个 skill 采用你已经认可的结构：

- 双层存储
- 表面双主源，内部单结算点

也就是：

- 表层给人看：`docs/implementation/*`
- 隐层给机器看：`.codex/context/*`
- 最终统一结算到：`.codex/context/latest-snapshot.json`

恢复上下文时默认只按这条扩容梯度读取：

1. `.codex/context/active-context.md`
2. `.codex/context/session-delta.md`
3. `.codex/context/history-rollup.md`
4. `.codex/context/latest-snapshot.json`
5. PRD 切片或完整 PRD

这样做的核心价值是：把“每次都重新输入完整 PRD、历史进度、依赖说明”的模式，改成“默认只读取当前任务和少量依赖”的模式。长期项目里，这通常会明显降低重复输入占比。

## 安装与复用

### 新机器

```cmd
git clone https://github.com/josebecker836-ui/Product_context_management..git %USERPROFILE%\.codex\skills\context-governor
```

### 当前机器

这个 skill 已经在全局技能目录中，可直接复用：

```text
C:\Users\WeiZhaoyuan\.codex\skills\context-governor
```

安装后重启 Codex，让 skill 列表刷新即可。

## 验证安装

```cmd
cd %USERPROFILE%\.codex\skills\context-governor
python scripts\quick_validate.py
```

期望最后一行输出：

```text
READY
```

## 新项目一键上手

如果你要把它接入一个全新的项目，直接看这份可复制模板：

- [references/new-project-template.md](./references/new-project-template.md)

最短初始化命令：

```cmd
python %USERPROFILE%\.codex\skills\context-governor\scripts\init_context_governor.py --root . --plan-id my-project --plan-title "My Project Plan"
```

## 日常使用

典型循环只有 4 步：

1. 从 PRD 生成 `docs/implementation/checklist.md`
2. 用 `settle_checklist_context_governor.py` 结算结构
3. 做完任务后用 `sync_progress_context_governor.py` 同步状态和证据
4. 下次开工先 `resume`，结束当天再 `closeout`

常用命令：

```cmd
python scripts\init_context_governor.py --root . --plan-id my-project --plan-title "My Project Plan"
python scripts\settle_checklist_context_governor.py --root .
python scripts\resume_context_governor.py --root .
python scripts\sync_progress_context_governor.py --root . --task T-014 --status done --evidence shipped-checklist
python scripts\closeout_context_governor.py --root .
python scripts\quick_validate.py
```

## 常用提示词

```text
Use $context-governor to break this approved PRD into an ordered checklist, dependency graph, and initial snapshot.
Use $context-governor to resume this project from .codex/context/active-context.md with the smallest necessary context.
Use $context-governor to sync progress from today's work and only mark tasks done where evidence exists.
```

## 文档入口

- [README.md](./README.md)
- [references/new-project-template.md](./references/new-project-template.md)
- [references/quickstart-zh.md](./references/quickstart-zh.md)
- [references/cheatsheet-zh.md](./references/cheatsheet-zh.md)
- [references/quickstart.md](./references/quickstart.md)
- [references/workflow.md](./references/workflow.md)
- [references/schemas.md](./references/schemas.md)
- [references/sync-rules.md](./references/sync-rules.md)
