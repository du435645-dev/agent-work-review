# 本地述职总结技能分发包

这个仓库用于在团队内分发两项能力：

- `work-review-ppt-summary`：在个人电脑上汇总 Codex、OpenCode、Hermes、WorkBuddy 和人工记录。
- `guizang-ppt-skill`：把确认后的述职摘要生成为网页 PPT。

共享的是技能和数据格式，不共享任何同事的会话、工作证据或述职产物。安装和更新脚本不会调用周律接口。

## 环境要求

- Windows PowerShell 5.1 或 PowerShell 7
- Python 3.10 或更高版本
- Node.js 仅在校验瑞士风网页 PPT 时需要
- Git 仅在通过仓库拉取更新时需要

## 一键安装

在 PowerShell 中进入本仓库后执行：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\install.ps1 -Target Auto -PersonId "姓名或工号"
```

`Auto` 始终安装通用核心到 `~/.work-review/skills`；检测到 `~/.codex` 时，同时安装 Codex skills 到 `~/.codex/skills`。

其他安装模式：

```powershell
.\install.ps1 -Target Codex
.\install.ps1 -Target Generic -PersonId "姓名或工号"
.\install.ps1 -Target All -PersonId "姓名或工号"
```

个人数据只保存在 `~/.work-review/data`。不要把该目录复制或提交回本仓库。

## 一键更新

```powershell
.\update.ps1 -Target Auto
```

如果当前目录是 Git 仓库，更新脚本先执行 `git pull --ff-only`。存在未提交改动时会停止，不会覆盖。旧技能会备份到 `~/.work-review/backups/<时间戳>/`，个人数据不会被修改。

使用 ZIP 分发、没有 `.git` 时，先用新 ZIP 覆盖本分发目录，再执行：

```powershell
.\update.ps1 -Target Auto -SkipPull
```

## Agent 接入

- Codex：读取 `agent-guides/codex.md`
- OpenCode：读取 `agent-guides/opencode.md`
- Hermes：读取 `agent-guides/hermes.md`
- WorkBuddy：读取 `agent-guides/workbuddy.md`
- 其他 Agent：读取 `agent-guides/generic-agent.md`

第一版只有 Codex 支持原生会话扫描。其他 Agent 将会话或工作记录导出为 Markdown、JSON 或 JSONL，再通过通用导入脚本接入。

## 发布到团队私有 Git

仓库验证完成后，可由维护者添加团队私有远端并推送：

```powershell
git remote add origin <团队私有仓库地址>
git push -u origin main
```

`guizang-ppt-skill` 来源于 `op7418/guizang-ppt-skill`，其许可证保留在 `skills/guizang-ppt-skill/LICENSE`。
