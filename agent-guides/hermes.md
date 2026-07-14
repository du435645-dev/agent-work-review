# Hermes 接入

第一版不直接读取 Hermes 的内部数据库。让 Hermes 把选定时间范围内的工作摘要导出为 Markdown、JSON 或 JSONL，再按 `generic-agent.md` 导入，`agent-type` 使用 `hermes`。

推荐给 Hermes 的指令：

> 按工作产出整理指定时间范围内的历史任务，保留产物、决策、结果证据和可回查来源。只写入用户本机指定目录，不连接周律，不提交或上传述职材料。
