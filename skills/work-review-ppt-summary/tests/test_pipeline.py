from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
FIXTURES = SKILL_ROOT / "tests" / "fixtures" / "sessions"


class PipelineTests(unittest.TestCase):
    def test_review_pipeline_from_sample_sessions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            local_root = tmp_path / "local-review"
            candidates_path = tmp_path / "candidates.json"
            imported_path = local_root / "inbox" / "opencode" / "evidence.jsonl"
            foreign_path = local_root / "inbox" / "manual" / "foreign.jsonl"
            merged_path = local_root / "review" / "candidates.json"
            summary_dir = tmp_path / "summary"
            ppt_dir = tmp_path / "ppt"

            init_cmd = [
                sys.executable,
                "-X",
                "utf8",
                str(SCRIPTS / "init_local_review.py"),
                "--root",
                str(local_root),
                "--person-id",
                "tester",
            ]
            init_proc = subprocess.run(init_cmd, capture_output=True, text=True)
            self.assertEqual(init_proc.returncode, 0, init_proc.stderr)
            config = json.loads((local_root / "config.json").read_text(encoding="utf-8"))
            self.assertEqual(config["storage_mode"], "local-only")

            opencode_export = tmp_path / "opencode-export.md"
            opencode_export.write_text(
                "# OpenCode 分析报告\n\n形成产物 project/demo/reports/result.html。\n",
                encoding="utf-8",
            )
            import_cmd = [
                sys.executable,
                "-X",
                "utf8",
                str(SCRIPTS / "import_agent_evidence.py"),
                "--input",
                str(opencode_export),
                "--agent-type",
                "opencode",
                "--person-id",
                "tester",
                "--workspace",
                str(tmp_path / "shared-workspace"),
                "--output",
                str(imported_path),
            ]
            import_proc = subprocess.run(import_cmd, capture_output=True, text=True)
            self.assertEqual(import_proc.returncode, 0, import_proc.stderr)
            foreign_path.parent.mkdir(parents=True, exist_ok=True)
            foreign_path.write_text(
                json.dumps(
                    {
                        "person_id": "another-person",
                        "agent_type": "manual",
                        "session_id": "foreign-session",
                        "workspace": "foreign-workspace",
                        "title": "不应混入的工作",
                        "impact_level": "output",
                        "impact_score": 99,
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            collect_cmd = [
                sys.executable,
                "-X",
                "utf8",
                str(SCRIPTS / "collect_session_candidates.py"),
                "--sessions-root",
                str(FIXTURES),
                "--preset",
                "last30d",
                "--now",
                "2026-07-06",
                "--person-id",
                "tester",
                "--output",
                str(candidates_path),
            ]
            collect_proc = subprocess.run(collect_cmd, capture_output=True, text=True)
            self.assertEqual(collect_proc.returncode, 0, collect_proc.stderr)

            candidates = json.loads(candidates_path.read_text(encoding="utf-8"))
            self.assertEqual(len(candidates["workspaces"]), 2)
            first_candidate = candidates["workspaces"][0]["candidates"][0]
            self.assertIn(first_candidate["impact_level"], {"output", "decision", "progress"})

            merge_cmd = [
                sys.executable,
                "-X",
                "utf8",
                str(SCRIPTS / "merge_work_evidence.py"),
                "--input",
                str(candidates_path),
                "--input",
                str(imported_path),
                "--input",
                str(foreign_path),
                "--person-id",
                "tester",
                "--start",
                "2026-01-01",
                "--end",
                "2026-12-31",
                "--output",
                str(merged_path),
            ]
            merge_proc = subprocess.run(merge_cmd, capture_output=True, text=True)
            self.assertEqual(merge_proc.returncode, 0, merge_proc.stderr)
            merged = json.loads(merged_path.read_text(encoding="utf-8"))
            self.assertEqual(merged["storage_mode"], "local-only")
            self.assertEqual(merged["source_agents"], ["codex", "opencode"])
            self.assertFalse(any(item["title"] == "不应混入的工作" for ws in merged["workspaces"] for item in ws["candidates"]))

            summary_cmd = [
                sys.executable,
                "-X",
                "utf8",
                str(SCRIPTS / "build_review_summary.py"),
                "--input",
                str(merged_path),
                "--scenario",
                "phase-review",
                "--output-dir",
                str(summary_dir),
            ]
            summary_proc = subprocess.run(summary_cmd, capture_output=True, text=True)
            self.assertEqual(summary_proc.returncode, 0, summary_proc.stderr)

            structured_summary = json.loads((summary_dir / "structured_summary.json").read_text(encoding="utf-8"))
            self.assertGreaterEqual(len(structured_summary["outputs"]), 1)
            self.assertTrue(any("opencode" in item["source_agents"] for item in structured_summary["outputs"]))
            self.assertEqual(
                structured_summary["summary_structure"],
                ["产出的背景", "产出的内容", "产出的成效", "后续计划（如果有）"],
            )

            brief_cmd = [
                sys.executable,
                "-X",
                "utf8",
                str(SCRIPTS / "prepare_guizang_brief.py"),
                "--input",
                str(summary_dir / "structured_summary.json"),
                "--output-dir",
                str(ppt_dir),
            ]
            brief_proc = subprocess.run(brief_cmd, capture_output=True, text=True)
            self.assertEqual(brief_proc.returncode, 0, brief_proc.stderr)

            brief = json.loads((ppt_dir / "brief.json").read_text(encoding="utf-8"))
            notes = (ppt_dir / "speaker_notes.md").read_text(encoding="utf-8")
            self.assertEqual(brief["visual_style"], "swiss")
            self.assertIn("Slide 1", notes)


if __name__ == "__main__":
    unittest.main()
