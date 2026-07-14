from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agent_work_review.drafts import current_state, prepare_draft, read_json, restore_history, save_draft, validate_draft  # noqa: E402
from agent_work_review.identity import initialize_home  # noqa: E402
from agent_work_review.pipeline import audit_candidates, merge_home, write_jsonl  # noqa: E402
from agent_work_review.renderer import write_html  # noqa: E402
from agent_work_review.review_sessions import get_active_review_id, list_reviews, migrate_legacy_review, resolve_review, set_active_review, start_review  # noqa: E402


def evidence(person_id: str, session_id: str, started_at: str, title: str) -> dict:
    return {
        "schema_version": "1.0",
        "person_id": person_id,
        "agent_type": "codex",
        "session_id": session_id,
        "started_at": started_at,
        "workspace": "demo",
        "title": title,
        "impact_level": "output",
        "artifact_paths": [f"reports/{session_id}.html"],
        "notes": f"Delivered {title}.",
        "impact": "Generated 22 reports.",
    }


def finish_draft(path: Path) -> dict:
    draft = read_json(path)
    draft["executive_summary"] = "Completed the selected work and verified its impact."
    for item in draft["outputs"]:
        context = item["evidence_context"]
        item.update({
            "background": context["background"] or "Required a reusable workflow.",
            "content": context["content"] or "Delivered the selected output.",
            "impact": context["impact"] or "Verified delivery.",
            "next_plan": "Continue the next stage.",
        })
    path.write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")
    return draft


class ReviewWorkspaceTests(unittest.TestCase):
    def test_read_only_decision_is_flagged_for_agent_review(self) -> None:
        candidates = {
            "source_agents": ["codex"],
            "workspaces": [{
                "workspace": "demo",
                "candidates": [{
                    "candidate_id": "candidate-decision",
                    "impact_level": "decision",
                    "signals": ["shell_command"],
                    "has_mutating_tool": False,
                    "artifact_paths": [],
                    "notes": "Decision: consider the proposal.",
                }],
            }],
        }
        audit = audit_candidates(candidates)
        self.assertEqual(audit["decision_only_candidate_ids"], ["candidate-decision"])
        self.assertEqual(audit["manual_review_candidate_ids"], ["candidate-decision"])

    def test_review_range_and_active_pointer_are_validated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary) / "home"
            initialize_home(home)
            with self.assertRaisesRegex(ValueError, "start must not be after end"):
                start_review(home, start="2026-07-01", end="2026-06-30", scenario="phase-review", language="en", title="Invalid")

            (home / "active-review.json").write_text(
                json.dumps({"review_id": "../outside"}), encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "review_id must use"):
                resolve_review(home)

    def test_restore_rejects_non_history_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            review_dir = Path(temporary) / "review"
            review_dir.mkdir()
            with self.assertRaisesRegex(ValueError, "revision returned by work-review history"):
                restore_history(review_dir, "../outside")

    def test_explicit_exclusion_completes_candidate_coverage(self) -> None:
        from datetime import date

        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary) / "home"
            config = initialize_home(home)
            write_jsonl(home / "inbox" / "codex" / "evidence.jsonl", [
                evidence(config["person_id"], "one", "2026-02-01T00:00:00Z", "First"),
                evidence(config["person_id"], "two", "2026-03-01T00:00:00Z", "Second"),
            ])
            review_dir, _ = start_review(home, start="2026-01-01", end="2026-06-30", scenario="phase-review", language="en", title="H1")
            candidates = merge_home(home, person_id=config["person_id"], start=date(2026, 1, 1), end=date(2026, 6, 30), review_dir=review_dir)
            path = prepare_draft(review_dir, candidates, scenario="phase-review", language="en", title="H1")
            draft = read_json(path)
            removed = draft["outputs"].pop()
            draft["excluded_candidates"] = [{"candidate_id": removed["candidate_ids"][0], "reason": "Duplicate supporting task."}]
            path.write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")
            finished = finish_draft(path)
            self.assertEqual(validate_draft(finished, candidates), [])

    def test_merge_respects_new_explicit_exclusion(self) -> None:
        from datetime import date

        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary) / "home"
            config = initialize_home(home)
            inbox = home / "inbox" / "codex" / "evidence.jsonl"
            first = evidence(config["person_id"], "one", "2026-02-01T00:00:00Z", "First")
            write_jsonl(inbox, [first])
            review_dir, _ = start_review(home, start="2026-01-01", end="2026-06-30", scenario="phase-review", language="en", title="H1")
            initial = merge_home(home, person_id=config["person_id"], start=date(2026, 1, 1), end=date(2026, 6, 30), review_dir=review_dir)
            initial_path = prepare_draft(review_dir, initial, scenario="phase-review", language="en", title="H1")
            initial_draft = finish_draft(initial_path)
            save_draft(review_dir, initial_draft, mode="error", candidates=initial)

            second = evidence(config["person_id"], "two", "2026-03-01T00:00:00Z", "Second")
            write_jsonl(inbox, [first, second])
            changed = merge_home(home, person_id=config["person_id"], start=date(2026, 1, 1), end=date(2026, 6, 30), review_dir=review_dir)
            changed_path = prepare_draft(review_dir, changed, scenario="phase-review", language="en", title="H1", force=True)
            changed_draft = read_json(changed_path)
            first_output = next(item for item in changed_draft["outputs"] if item["title"] == "First")
            first_id = first_output["candidate_ids"][0]
            changed_draft["outputs"].remove(first_output)
            changed_draft["excluded_candidates"] = [{"candidate_id": first_id, "reason": "No longer reportable."}]
            changed_path.write_text(json.dumps(changed_draft, ensure_ascii=False, indent=2), encoding="utf-8")
            reviewed = finish_draft(changed_path)

            merged_json, _, _ = save_draft(review_dir, reviewed, mode="merge", candidates=changed)
            merged = read_json(merged_json)
            included = {candidate_id for item in merged["outputs"] for candidate_id in item["candidate_ids"]}
            self.assertNotIn(first_id, included)
            self.assertEqual(merged["excluded_candidates"], [{"candidate_id": first_id, "reason": "No longer reportable."}])
            self.assertEqual(validate_draft(merged, changed), [])

    def test_generic_repository_files_do_not_force_false_merges(self) -> None:
        from datetime import date

        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary) / "home"
            config = initialize_home(home)
            rows = []
            for session_id, agent in (("one", "codex"), ("two", "opencode")):
                item = evidence(config["person_id"], session_id, "2026-02-01T00:00:00Z", session_id)
                item["agent_type"] = agent
                item["artifact_paths"] = ["README.md"]
                rows.append(item)
            write_jsonl(home / "inbox" / "generic" / "evidence.jsonl", rows)
            review_dir, _ = start_review(home, start="2026-01-01", end="2026-06-30", scenario="phase-review", language="en", title="H1")
            candidates = merge_home(home, person_id=config["person_id"], start=date(2026, 1, 1), end=date(2026, 6, 30), review_dir=review_dir)
            self.assertEqual(sum(len(group["candidates"]) for group in candidates["workspaces"]), 2)

    def test_half_year_and_year_reviews_do_not_overwrite_each_other(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary) / "home"
            config = initialize_home(home)
            write_jsonl(home / "inbox" / "codex" / "evidence.jsonl", [
                evidence(config["person_id"], "q1", "2026-03-10T00:00:00Z", "Q1 work"),
                evidence(config["person_id"], "q4", "2026-10-10T00:00:00Z", "Q4 work"),
            ])
            half_dir, half = start_review(home, start="2026-01-01", end="2026-06-30", scenario="phase-review", language="en", title="H1")
            half_candidates = merge_home(home, person_id=config["person_id"], start=__import__("datetime").date(2026, 1, 1), end=__import__("datetime").date(2026, 6, 30), review_dir=half_dir)
            year_dir, year = start_review(home, start="2026-01-01", end="2026-12-31", scenario="phase-review", language="en", title="Year")
            year_candidates = merge_home(home, person_id=config["person_id"], start=__import__("datetime").date(2026, 1, 1), end=__import__("datetime").date(2026, 12, 31), review_dir=year_dir)

            self.assertNotEqual(half["review_id"], year["review_id"])
            self.assertEqual(sum(len(group["candidates"]) for group in half_candidates["workspaces"]), 1)
            self.assertEqual(sum(len(group["candidates"]) for group in year_candidates["workspaces"]), 2)
            self.assertTrue((half_dir / "candidates.json").is_file())
            self.assertTrue((year_dir / "candidates.json").is_file())
            self.assertEqual(get_active_review_id(home), year["review_id"])
            set_active_review(home, half["review_id"])
            self.assertEqual(get_active_review_id(home), half["review_id"])
            self.assertEqual(len(list_reviews(home)), 2)

    def test_candidate_coverage_staleness_and_history_restore(self) -> None:
        from datetime import date

        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary) / "home"
            config = initialize_home(home)
            inbox = home / "inbox" / "codex" / "evidence.jsonl"
            write_jsonl(inbox, [evidence(config["person_id"], "one", "2026-02-01T00:00:00Z", "First")])
            review_dir, manifest = start_review(home, start="2026-01-01", end="2026-06-30", scenario="phase-review", language="en", title="H1")
            candidates = merge_home(home, person_id=config["person_id"], start=date(2026, 1, 1), end=date(2026, 6, 30), review_dir=review_dir)
            path = prepare_draft(review_dir, candidates, scenario="phase-review", language="en", title="H1")
            draft = finish_draft(path)
            self.assertEqual(validate_draft(draft, candidates), [])
            summary_json, _, _ = save_draft(review_dir, draft, mode="error", candidates=candidates)
            summary = read_json(summary_json)
            write_html(summary, review_dir / "presentation.html", title="H1")
            self.assertTrue(current_state(review_dir, manifest)["presentation"]["fresh"])

            draft["excluded_candidates"] = [{"candidate_id": draft["outputs"][0]["candidate_ids"][0], "reason": "Duplicate"}]
            self.assertIn("both included and excluded", "\n".join(validate_draft(draft, candidates)))

            write_jsonl(inbox, [
                evidence(config["person_id"], "one", "2026-02-01T00:00:00Z", "First"),
                evidence(config["person_id"], "two", "2026-03-01T00:00:00Z", "Second"),
            ])
            changed = merge_home(home, person_id=config["person_id"], start=date(2026, 1, 1), end=date(2026, 6, 30), review_dir=review_dir)
            self.assertIn("stale", "\n".join(validate_draft(read_json(path), changed)))
            state = current_state(review_dir, manifest)
            self.assertFalse(state["draft"]["fresh"])
            self.assertFalse(state["summary"]["fresh"])

            fresh_path = prepare_draft(review_dir, changed, scenario="phase-review", language="en", title="H1", force=True)
            fresh = finish_draft(fresh_path)
            save_draft(review_dir, fresh, mode="overwrite", candidates=changed)
            self.assertFalse(current_state(review_dir, manifest)["presentation"]["fresh"])
            history = sorted((review_dir / "history").glob("*/revision.json"))
            self.assertTrue(history)
            restored = restore_history(review_dir, history[0].parent.name)
            self.assertIn("summary.json", restored)

    def test_failed_overwrite_restores_previous_canonical_files(self) -> None:
        from datetime import date

        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary) / "home"
            config = initialize_home(home)
            write_jsonl(home / "inbox" / "codex" / "evidence.jsonl", [evidence(config["person_id"], "one", "2026-02-01T00:00:00Z", "First")])
            review_dir, _ = start_review(home, start="2026-01-01", end="2026-06-30", scenario="phase-review", language="en", title="H1")
            candidates = merge_home(home, person_id=config["person_id"], start=date(2026, 1, 1), end=date(2026, 6, 30), review_dir=review_dir)
            path = prepare_draft(review_dir, candidates, scenario="phase-review", language="en", title="H1")
            draft = finish_draft(path)
            save_draft(review_dir, draft, mode="error", candidates=candidates)
            original_json = (review_dir / "summary.json").read_text(encoding="utf-8")
            original_markdown = (review_dir / "summary.md").read_text(encoding="utf-8")
            with patch("agent_work_review.drafts.write_summary", side_effect=OSError("simulated write failure")):
                with self.assertRaises(OSError):
                    save_draft(review_dir, draft, mode="overwrite", candidates=candidates)
            self.assertEqual((review_dir / "summary.json").read_text(encoding="utf-8"), original_json)
            self.assertEqual((review_dir / "summary.md").read_text(encoding="utf-8"), original_markdown)

    def test_legacy_layout_is_copied_without_deletion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary) / "home"
            initialize_home(home)
            legacy = home / "review" / "summary.md"
            legacy.parent.mkdir(parents=True, exist_ok=True)
            legacy.write_text("# Legacy", encoding="utf-8")
            review_id = migrate_legacy_review(home)
            self.assertIsNotNone(review_id)
            self.assertTrue(legacy.is_file())
            self.assertTrue((home / "reviews" / str(review_id) / "summary.md").is_file())


if __name__ == "__main__":
    unittest.main()
