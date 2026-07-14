# Agent Work Review

一个本地优先的跨 Agent 工作证据汇总工具，输出可复用的结构化总结和单文件 HTML 网页演示文稿。

产品核心不依赖某个特定 Agent。Codex 提供本地历史原生适配器；其他 Agent 可以通过 Markdown、JSON 或 JSONL 统一证据协议接入。

## 输出

- `review.json`：本次汇报的时间范围、状态和内容谱系
- `candidates.json`：按完成任务提取并跨 Agent 去重后的候选工作项
- `summary.draft.json`：由当前会话 Agent 总结和润色的工作草稿
- `summary.json`：机器可消费的核心总结
- `summary.md`：方便阅读和继续加工的核心总结
- `presentation.html`：可离线打开的单文件 HTML 网页演示文稿

结构化总结是长期真相源。HTML 是唯一内置展示格式；用户可以自行把总结转换成其他报告形式。

## 安装

```bash
git clone https://github.com/du435645-dev/agent-work-review.git
cd agent-work-review
python install.py
```

Windows 也可以运行：

```powershell
.\install.ps1
```

安装器会在 `~/.work-review` 下创建隔离运行环境和本地数据目录；检测到 Codex 时会自动安装 `agent-work-review` Skill。无需输入姓名或工号。

## 使用

```bash
work-review init
work-review start --start 2026-01-01 --end 2026-06-30 --language zh --title "2026年上半年工作总结" --review-id 2026-h1
work-review collect --source codex
work-review import --agent other-agent --input ./agent-export.md
work-review merge
work-review audit-candidates
work-review current
work-review prepare-draft

# 当前会话 Agent 读取 evidence_context，填写四段叙事，并处理所有 candidate_id
work-review validate-draft
work-review preview-draft
work-review save-draft --mode overwrite
work-review render-html
work-review current
```

半年报、年报、季度报等每次请求都会创建独立的 `reviews/<review-id>/`，通过 `list-reviews` 和 `use` 切换，不会覆盖其他时间范围。

这套流程参考周报工具的职责划分：脚本负责状态、收集、完成任务提取、去重、候选覆盖校验、历史备份和渲染；当前会话 Agent 负责筛选、归并、总结和润色。草稿必须处理全部候选，候选发生变化后旧草稿和 HTML 会显示过期。

自动提取只是召回层，不直接替代价值判断。会话 Agent 会按照内置价值判断指南，把候选区分为值得纳入、需要合并、证据不足或应排除；一般建议、只读排查和没有落地结果的问答不会直接成为最终汇报内容。

`work-review build` 仍可生成快速、未经会话 Agent 润色的脚手架，但不再是正式汇报的默认流程。

中文输出无需切换到 `--language en`。运行时代码采用 ASCII 安全的本地化资源，生成的 JSON、Markdown 和 HTML 均显式使用 UTF-8；即使某些 Agent 或 Windows shell 默认使用本地代码页，也不会破坏运行时中文文案。

默认数据目录是 `~/.work-review/data`。工具不会上传会话、证据、总结或 HTML 演示文稿。

v1.1 的旧平铺结果会复制到 `legacy-import` review，原文件不会删除。

统一证据协议见 [`schemas/work-evidence.schema.json`](schemas/work-evidence.schema.json)，总结草稿协议见 [`schemas/work-summary.schema.json`](schemas/work-summary.schema.json)，工作区协议见 [`schemas/review-workspace.schema.json`](schemas/review-workspace.schema.json)。
