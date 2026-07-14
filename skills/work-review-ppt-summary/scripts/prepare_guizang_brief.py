from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare guizang brief and speaker notes from structured review summary.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = json.loads(Path(args.input).read_text(encoding="utf-8"))
    outputs = summary.get("outputs", [])

    sections = [
        {
            "title": "阶段目标与范围",
            "points": ["围绕既定时间范围内的重要产出与关键决策，回顾阶段工作重点。"],
        }
    ]
    for item in outputs:
        sections.append(
            {
                "title": item["title"],
                "points": [
                    item["background"],
                    item["content"],
                    f"成效：{item['impact']}",
                    f"后续：{item['next_plan']}",
                ],
            }
        )

    brief = {
        "review_mode": summary.get("review_mode", "phase-review"),
        "visual_style": "swiss",
        "slide_count_hint": "10-14",
        "sections": sections,
    }

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    brief_path = output_dir / "brief.json"
    outline_path = output_dir / "outline.md"
    notes_path = output_dir / "speaker_notes.md"

    brief_path.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    outline_lines = ["# PPT 大纲", ""]
    notes_lines = ["# Speaker Notes", ""]
    for idx, section in enumerate(sections, start=1):
        outline_lines.extend([f"## {section['title']}", *[f"- {point}" for point in section["points"]], ""])
        notes_lines.extend([f"## Slide {idx}: {section['title']}", *[f"- {point}" for point in section["points"]], ""])

    outline_path.write_text("\n".join(outline_lines), encoding="utf-8")
    notes_path.write_text("\n".join(notes_lines), encoding="utf-8")
    print(str(brief_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
