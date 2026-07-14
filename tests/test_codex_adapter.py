from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agent_work_review.adapters.codex import parse_session  # noqa: E402


def row(record_type: str, payload: dict, timestamp: str = "2026-07-14T00:00:00Z") -> str:
    return json.dumps({"type": record_type, "timestamp": timestamp, "payload": payload}, ensure_ascii=False)


def message(role: str, text: str, phase: str | None = None) -> dict:
    value = {"type": "message", "role": role, "content": [{"type": "input_text", "text": text}]}
    if phase:
        value["phase"] = phase
    return value


class CodexAdapterTests(unittest.TestCase):
    def test_supports_older_unphased_final_messages(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "legacy.jsonl"
            path.write_text("\n".join([
                row("session_meta", {"id": "legacy", "cwd": "D:/demo"}),
                row("response_item", message("user", "Create the summary file.")),
                row("response_item", {"type": "function_call", "name": "apply_patch", "arguments": "{}"}),
                row("response_item", message("assistant", "Completed and created reports/summary.md.")),
            ]), encoding="utf-8")
            candidates = parse_session(path, "local-test")
            self.assertEqual(len(candidates), 1)
            self.assertEqual(candidates[0]["impact_level"], "output")

    def test_extracts_completed_turns_and_ignores_read_only_shell(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "rollout.jsonl"
            lines = [
                row("session_meta", {"id": "session-1", "cwd": "D:/demo", "timestamp": "2026-07-14T00:00:00Z"}),
                row("response_item", message("user", "Inspect the repository only.")),
                row("response_item", {"type": "function_call", "name": "shell_command", "arguments": json.dumps({"command": "git status"})}),
                row("response_item", message("assistant", "The repository was inspected. No reportable decision or delivery was made.", "final_answer")),
                row("response_item", message("user", "Build the activity report workflow.")),
                row("response_item", {"type": "custom_tool_call", "name": "exec", "input": "await tools.apply_patch('create report')"}),
                row("response_item", message("assistant", "Completed and generated reports/activity.html. Generated 22 reports and all tests passed.", "final_answer")),
                row("response_item", message("user", "Choose the rollout strategy.")),
                row("response_item", message("assistant", "Decision: use the local-only strategy before optional synchronization.", "final_answer")),
            ]
            path.write_text("\n".join(lines), encoding="utf-8")
            candidates = parse_session(path, "local-test")

            self.assertEqual(len(candidates), 2)
            output, decision = candidates
            self.assertEqual(output["impact_level"], "output")
            self.assertEqual(output["title"], "Build the activity report workflow.")
            self.assertIn("22 reports", output["impact"])
            self.assertEqual(output["artifact_paths"], ["reports/activity.html"])
            self.assertTrue(output["has_mutating_tool"])
            self.assertTrue(output["source_refs"][0].endswith("#turn-2"))
            self.assertEqual(decision["impact_level"], "decision")
            self.assertFalse(decision["has_mutating_tool"])
            self.assertIn("local-only strategy", decision["notes"])


if __name__ == "__main__":
    unittest.main()
