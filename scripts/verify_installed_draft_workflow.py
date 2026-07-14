from __future__ import annotations

import json
import tempfile
from datetime import date
from pathlib import Path

from agent_work_review import __version__
from agent_work_review.drafts import current_state, prepare_draft, read_json, save_draft, validate_draft
from agent_work_review.identity import initialize_home
from agent_work_review.pipeline import merge_home, write_jsonl
from agent_work_review.renderer import write_html
from agent_work_review.review_sessions import start_review


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
        review_dir, manifest = start_review(home, start="2026-01-01", end="2026-06-30", scenario="phase-review", language="zh", title="Installed workflow test", review_id="installed-smoke")
        candidates = merge_home(home, person_id=config["person_id"], start=date(2026, 1, 1), end=date(2026, 6, 30), review_dir=review_dir)
        path = prepare_draft(review_dir, candidates, scenario="phase-review", language="zh", title="Installed workflow test")
        draft = read_json(path)
        if not validate_draft(draft, candidates):
            raise SystemExit("Unreviewed scaffold unexpectedly passed validation.")
        draft["executive_summary"] = "\u5df2\u5b8c\u6210\u4f1a\u8bdd Agent \u6da6\u8272\u548c\u6765\u6e90\u6821\u9a8c\u3002"
        for item in draft["outputs"]:
            context = item["evidence_context"]
            item["background"] = context["background"] or "\u9700\u8981\u5efa\u7acb\u53ef\u590d\u7528\u6d41\u7a0b\u3002"
            item["content"] = context["content"] or "\u5b8c\u6210\u660e\u786e\u4ea4\u4ed8\u3002"
            item["impact"] = context["impact"] or "\u5f62\u6210\u53ef\u9a8c\u8bc1\u7ed3\u679c\u3002"
            item["next_plan"] = "\u7ee7\u7eed\u63a8\u8fdb\u4e0b\u4e00\u9636\u6bb5\u3002"
        path.write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")
        if validate_draft(read_json(path), candidates):
            raise SystemExit("Reviewed draft failed validation.")
        summary_json, _, _ = save_draft(review_dir, read_json(path), mode="error", candidates=candidates)
        summary = read_json(summary_json)
        presentation = write_html(summary, review_dir / "presentation.html", title=summary["title"])
        text = presentation.read_text(encoding="utf-8")
        if summary.get("summary_origin") != "agent-reviewed" or draft["executive_summary"] not in text:
            raise SystemExit("Installed draft workflow produced incomplete output.")
        if not current_state(review_dir, manifest)["presentation"]["fresh"]:
            raise SystemExit("Installed presentation freshness verification failed.")
        print(f"Installed Agent draft workflow verified: {__version__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
