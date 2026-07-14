from __future__ import annotations

import json
import tempfile
from pathlib import Path

from agent_work_review import __version__
from agent_work_review.drafts import prepare_draft, read_json, save_draft, validate_draft
from agent_work_review.identity import initialize_home
from agent_work_review.pipeline import merge_home, write_jsonl
from agent_work_review.renderer import write_html


def main() -> int:
    with tempfile.TemporaryDirectory() as temporary:
        home = Path(temporary) / "home"
        config = initialize_home(home)
        write_jsonl(
            home / "inbox" / "codex" / "evidence.jsonl",
            [{
                "schema_version": "1.0",
                "person_id": config["person_id"],
                "agent_type": "codex",
                "session_id": "installed-smoke-1",
                "workspace": "demo",
                "title": "Generated reports",
                "impact_level": "output",
                "impact": "Generated 22 reports.",
            }],
        )
        candidates = merge_home(home, person_id=config["person_id"])
        path = prepare_draft(home, candidates, scenario="phase-review", language="zh", title="Installed workflow test")
        draft = read_json(path)
        if not validate_draft(draft, candidates):
            raise SystemExit("Unreviewed scaffold unexpectedly passed validation.")
        draft["executive_summary"] = "\u5df2\u5b8c\u6210\u4f1a\u8bdd Agent \u6da6\u8272\u548c\u6765\u6e90\u6821\u9a8c\u3002"
        path.write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")
        if validate_draft(read_json(path), candidates):
            raise SystemExit("Reviewed draft failed validation.")
        summary_json, _ = save_draft(home, read_json(path), mode="error")
        summary = read_json(summary_json)
        presentation = write_html(summary, home / "output" / "presentation.html", title=summary["title"])
        text = presentation.read_text(encoding="utf-8")
        if summary.get("summary_origin") != "agent-reviewed" or draft["executive_summary"] not in text:
            raise SystemExit("Installed draft workflow produced incomplete output.")
        print(f"Installed Agent draft workflow verified: {__version__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
