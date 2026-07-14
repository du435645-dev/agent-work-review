# 通用 Agent 接入

把下面规则加入 Agent 的个人指令、项目指令或常用提示词：

> 当用户要求阶段复盘、述职总结或晋升材料时，使用本机 `~/.work-review/skills/work-review-ppt-summary`。所有工作证据、候选清单和最终产物只能写入 `~/.work-review/data`。不得调用周律，不得上传原始会话，不得混入其他 person_id。当前 Agent 如果不能直接读取历史会话，先把选定时间范围的工作记录导出为 Markdown、JSON 或 JSONL，再调用 `import_agent_evidence.py`。

通用导入命令：

```powershell
python -X utf8 "$HOME\.work-review\skills\work-review-ppt-summary\scripts\import_agent_evidence.py" `
  --input "<导出文件或目录>" `
  --agent-type "<agent名称>" `
  --person-id "<姓名或工号>" `
  --output "$HOME\.work-review\data\inbox\<agent名称>\evidence.jsonl"
```

导入后运行合并：

```powershell
python -X utf8 "$HOME\.work-review\skills\work-review-ppt-summary\scripts\merge_work_evidence.py" `
  --input-dir "$HOME\.work-review\data\inbox" `
  --person-id "<姓名或工号>" `
  --start "<YYYY-MM-DD>" `
  --end "<YYYY-MM-DD>" `
  --output "$HOME\.work-review\data\review\candidates.json"
```

必须先让用户确认候选工作项，再生成结构化摘要和 PPT。
