from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agent_work_review.adapters.generic import import_evidence  # noqa: E402
from agent_work_review.identity import initialize_home  # noqa: E402
from agent_work_review.pipeline import append_jsonl, merge_home, summarize_candidates, write_jsonl, write_summary  # noqa: E402
from agent_work_review.renderer import write_html  # noqa: E402


class EndToEndTests(unittest.TestCase):
    def test_chinese_outputs_survive_cross_platform_packaging(self) -> None:
        runtime_sources = [
            ROOT / "src" / "agent_work_review" / "locales.py",
            ROOT / "src" / "agent_work_review" / "pipeline.py",
            ROOT / "src" / "agent_work_review" / "renderer.py",
        ]
        for source in runtime_sources:
            self.assertTrue(source.read_bytes().isascii(), f"Runtime source must remain ASCII-safe: {source}")

        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary) / "home"
            candidates = {
                "source_agents": ["codex", "opencode"],
                "time_range": {"start": "2026-01-01", "end": "2026-06-30"},
                "workspaces": [{
                    "workspace": "demo",
                    "candidates": [{
                        "title": "\u4e2d\u6587\u5de5\u4f5c\u9879",
                        "impact_level": "output",
                        "impact": "\u5de5\u4f5c\u6548\u7387\u63d0\u5347 40%\u3002",
                        "source_agents": ["codex", "opencode"],
                    }],
                }],
            }
            summary = summarize_candidates(candidates, scenario="phase-review", language="zh")
            summary_json, summary_md = write_summary(home, summary)
            presentation = write_html(summary, home / "output" / "presentation.html", title="\u4e2d\u6587\u5de5\u4f5c\u603b\u7ed3")

            self.assertEqual(summary["summary_structure"], ["\u4ea7\u51fa\u7684\u80cc\u666f", "\u4ea7\u51fa\u7684\u5185\u5bb9", "\u4ea7\u51fa\u7684\u6210\u6548", "\u540e\u7eed\u8ba1\u5212"])
            self.assertIn("\u4e2d\u6587\u5de5\u4f5c\u9879", summary_json.read_text(encoding="utf-8"))
            self.assertIn("# \u7ed3\u6784\u5316\u5de5\u4f5c\u603b\u7ed3", summary_md.read_text(encoding="utf-8"))
            html_text = presentation.read_text(encoding="utf-8")
            self.assertIn('<meta charset="utf-8">', html_text)
            self.assertIn("\u4e2d\u6587\u5de5\u4f5c\u603b\u7ed3", html_text)
            self.assertIn("\u5148\u6c89\u6dc0\u8bc1\u636e", html_text)

    def test_multi_agent_review_to_standalone_html(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary) / "home"
            config = initialize_home(home)
            self.assertRegex(config["person_id"], r"^local-[0-9a-f]{12}$")

            codex_export = Path(temporary) / "codex.json"
            codex_export.write_text(
                json.dumps(
                    {
                        "session_id": "codex-1",
                        "workspace": "example-project",
                        "title": "Automated the reporting workflow",
                        "impact_level": "output",
                        "artifact_paths": ["reports/automation.html"],
                        "impact": "Reduced repeated manual preparation by 40%.",
                    }
                ),
                encoding="utf-8",
            )
            other_export = Path(temporary) / "other.md"
            other_export.write_text(
                "# Chose the rollout strategy\n\nDecision: ship the local-only path before optional sync.\n",
                encoding="utf-8",
            )
            first = import_evidence(codex_export, agent="codex", person_id=config["person_id"])
            second = import_evidence(other_export, agent="another-agent", person_id=config["person_id"], workspace="example-project")
            write_jsonl(home / "inbox" / "codex" / "evidence.jsonl", first)
            write_jsonl(home / "inbox" / "another-agent" / "evidence.jsonl", second)

            candidates = merge_home(home, person_id=config["person_id"])
            self.assertEqual(candidates["source_agents"], ["another-agent", "codex"])
            summary = summarize_candidates(candidates, scenario="phase-review", language="en")
            self.assertEqual(len(summary["outputs"]), 2)
            summary_json, summary_md = write_summary(home, summary)
            presentation = write_html(summary, home / "output" / "presentation.html", title="2026 Work Review")

            self.assertTrue(summary_json.is_file())
            self.assertTrue(summary_md.is_file())
            html_text = presentation.read_text(encoding="utf-8")
            self.assertIn("2026 Work Review", html_text)
            self.assertIn("Automated the reporting workflow", html_text)
            self.assertIn("Arrow keys", html_text)
            self.assertNotIn("PPTX", html_text)

    def test_append_import_and_safe_script_embedding(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary) / "home"
            config = initialize_home(home)
            path = home / "inbox" / "generic" / "evidence.jsonl"
            first = {"schema_version": "1.0", "person_id": config["person_id"], "agent_type": "generic", "session_id": "one", "workspace": "demo", "title": "First", "impact_level": "output"}
            second = {"schema_version": "1.0", "person_id": config["person_id"], "agent_type": "generic", "session_id": "two", "workspace": "demo", "title": "</script><script>alert(1)</script>", "impact_level": "decision"}
            append_jsonl(path, [first])
            append_jsonl(path, [second])
            candidates = merge_home(home, person_id=config["person_id"])
            summary = summarize_candidates(candidates, scenario="phase-review", language="en")
            presentation = write_html(summary, home / "output" / "presentation.html", title="Safe")
            html_text = presentation.read_text(encoding="utf-8")
            self.assertEqual(len(summary["outputs"]), 2)
            self.assertNotIn("</script><script>alert(1)</script>", html_text)
            self.assertIn("&lt;/script&gt;", html_text)

    def test_foreign_identity_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary) / "home"
            config = initialize_home(home)
            write_jsonl(
                home / "inbox" / "generic" / "evidence.jsonl",
                [{"schema_version": "1.0", "person_id": "someone-else", "agent_type": "generic", "session_id": "x", "workspace": "x", "title": "Foreign", "impact_level": "output"}],
            )
            candidates = merge_home(home, person_id=config["person_id"])
            self.assertEqual(candidates["workspaces"], [])


if __name__ == "__main__":
    unittest.main()
