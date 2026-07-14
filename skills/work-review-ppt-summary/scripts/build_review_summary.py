from __future__ import annotations

import argparse
import json
from pathlib import Path


STRUCTURES = {
    "phase-review": ["产出的背景", "产出的内容", "产出的成效", "后续计划（如果有）"],
    "self-review": ["产出的背景", "产出的内容", "产出的成效", "后续计划（如果有）"],
    "formal-report": ["产出的背景", "产出的内容", "产出的成效", "后续计划（如果有）"],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build structured review summary from candidate sessions.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--scenario", default="phase-review", choices=sorted(STRUCTURES))
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


def evidence_level(candidate: dict) -> str:
    notes = str(candidate.get("notes") or "")
    if any(char.isdigit() for char in notes) and any(token in notes for token in ("%", "+", "提升", "下降", "增长")):
        return "quantified"
    if candidate["impact_level"] == "output":
        return "qualified"
    if candidate["impact_level"] == "decision":
        return "qualified"
    return "progress"


def build_background(candidate: dict) -> str:
    workspace_name = Path(candidate["cwd"]).name if candidate["cwd"] != "unknown" else "当前工作区"
    return f"在 {workspace_name} 工作线中，为推进相关任务，开展了本轮处理与整理。"


def build_content(candidate: dict) -> str:
    if candidate.get("artifact_paths"):
        return f"围绕 {candidate['title']} 相关产物推进，涉及 {', '.join(candidate['artifact_paths'][:3])}。"
    if candidate.get("notes"):
        return str(candidate["notes"]).strip()[:800]
    if candidate.get("signals"):
        return f"主要通过 {', '.join(candidate['signals'])} 等动作推进该项工作。"
    return f"围绕 {candidate['title']} 推进了相关工作。"


def build_impact(candidate: dict) -> str:
    if candidate["impact_level"] == "output":
        return "形成了可复用产物或明确交付结果，为后续复盘与汇报提供了直接材料。"
    if candidate["impact_level"] == "decision":
        return "沉淀了明确的处理决策与取舍原则，降低了后续执行偏差。"
    return "完成了阶段性推进，为后续正式产出或决策打下基础。"


def build_next(candidate: dict) -> str:
    if candidate["impact_level"] == "progress":
        return "继续补齐证据与最终产物，视需要再收敛为正式结论。"
    return "如后续需要，可继续沿该主线补充验证、整理材料并转化为正式汇报。"


def main() -> int:
    args = parse_args()
    candidates_doc = json.loads(Path(args.input).read_text(encoding="utf-8"))
    outputs = []

    for workspace in candidates_doc.get("workspaces", []):
        for candidate in workspace.get("candidates", []):
            outputs.append(
                {
                    "title": candidate["title"],
                    "workspace": candidate["cwd"],
                    "evidence_level": evidence_level(candidate),
                    "background": build_background(candidate),
                    "content": build_content(candidate),
                    "impact": build_impact(candidate),
                    "next_plan": build_next(candidate),
                    "source_session_ids": candidate.get("source_session_ids") or [candidate["session_id"]],
                    "source_agents": candidate.get("source_agents") or [candidate.get("agent_type", "codex")],
                    "source_refs": candidate.get("source_refs", []),
                }
            )

    summary = {
        "review_mode": args.scenario,
        "summary_structure": STRUCTURES[args.scenario],
        "outputs": outputs,
    }

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    structured_path = output_dir / "structured_summary.json"
    markdown_path = output_dir / "structured_summary.md"

    structured_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = ["# 结构化复盘摘要", ""]
    for item in outputs:
        lines.extend(
            [
                f"## {item['title']}",
                f"- 产出的背景：{item['background']}",
                f"- 产出的内容：{item['content']}",
                f"- 产出的成效：{item['impact']}",
                f"- 后续计划：{item['next_plan']}",
                "",
            ]
        )
    markdown_path.write_text("\n".join(lines), encoding="utf-8")
    print(str(structured_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
