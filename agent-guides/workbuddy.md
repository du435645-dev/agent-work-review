# WorkBuddy 接入

第一版通过通用导入协议接入 WorkBuddy。把选定时间范围内的工作记录导出为 Markdown、JSON 或 JSONL，再按 `generic-agent.md` 导入，`agent-type` 使用 `workbuddy`。

推荐给 WorkBuddy 的指令：

> 从当前可访问的任务记录中整理有明确产出、决策或阶段进展的工作项。每项包含时间、工作区、标题、产物、成效和来源；输出到用户指定的本地文件，不上传到其他系统。
