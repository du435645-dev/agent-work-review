# Codex 接入

安装后新建一个 Codex 任务，使用下面的请求：

> 使用 `$work-review-ppt-summary`，按指定时间范围汇总我本机的工作。先扫描 Codex 会话，再导入其他 Agent 的本地导出，给我确认候选工作项后再生成摘要和 PPT。

Codex 原生采集入口：

```powershell
python -X utf8 "$HOME\.codex\skills\work-review-ppt-summary\scripts\collect_session_candidates.py" `
  --start "<YYYY-MM-DD>" `
  --end "<YYYY-MM-DD>" `
  --output "$HOME\.work-review\data\inbox\codex\candidates.json"
```

Codex 只读取当前电脑可见的 `~/.codex/sessions`，不会自动获得其他设备或 Agent 的历史。
