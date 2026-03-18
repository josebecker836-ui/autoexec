# autoexec-skills

这是一个面向 Codex 的 skills 仓库，用来沉淀可复用的研发流程、协作规范和工具工作流。每个目录都是一个独立 skill，核心说明写在各自的 `SKILL.md` 里。

## System Skills

- `.system/openai-docs`: 查询 OpenAI 官方文档、模型/API 选型和升级说明。
- `.system/skill-creator`: 创建或改造 skill 的结构、文案和工作流。
- `.system/skill-installer`: 从本地或 GitHub 仓库安装 skill 到本机 skills 库。

## Skills

- `autonomous-prd-delivery`: 根据 PRD、流程图和进度文档持续推进研发，非真实阻塞不中断。
- `brainstorming`: 在动手前先澄清需求、拆解方案并形成设计。
- `chatgpt-apps`: 搭建、改造和调试 ChatGPT Apps SDK 应用与 MCP/UI 集成。
- `context-governor`: 长任务恢复上下文、按现有清单继续推进并同步进度。
- `dispatching-parallel-agents`: 把互不依赖的任务分发给并行 agent 提速。
- `executing-plans`: 按既有实施计划逐步执行并在检查点回看。
- `figma`: 从 Figma 拉设计上下文、变量和资源并转成代码。
- `finishing-a-development-branch`: 分支开发完成后决定合并、提 PR 或清理收尾。
- `linear`: 读取、创建和更新 Linear 任务。
- `receiving-code-review`: 收到 code review 后先核实建议，再谨慎落实。
- `requesting-code-review`: 开发完成后发起系统化代码审查。
- `subagent-driven-development`: 在当前会话内按计划拆任务并交给子 agent 执行。
- `systematic-debugging`: 遇到 bug、异常或测试失败时做系统化排查。
- `test-driven-development`: 先写测试再实现功能或修复。
- `using-git-worktrees`: 为新任务创建隔离 worktree，减少相互干扰。
- `using-superpowers`: 会话开始时先判断并加载合适的 skill。
- `verification-before-completion`: 宣称完成前先做验证，避免无证据收口。
- `writing-plans`: 根据需求或 spec 先写实施计划再编码。
- `writing-skills`: 创建、修改和验证 skill 本身。
