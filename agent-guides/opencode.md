# OpenCode 接入

第一版不假设 OpenCode 的内部会话存储格式。让 OpenCode 把选定时间范围内有产出、决策或阶段进展的工作导出为 Markdown、JSON 或 JSONL，再按 `generic-agent.md` 导入，`agent-type` 使用 `opencode`。

推荐给 OpenCode 的指令：

> 整理指定时间范围内有明确产出、决策或阶段进展的工作，不按聊天长度排序。每项保留时间、工作区、标题、产物路径、关键决策和成效证据。输出到用户指定的本地 Markdown 或 JSON 文件，不上传到外部服务。
