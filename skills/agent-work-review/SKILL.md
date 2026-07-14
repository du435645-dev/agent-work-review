---
name: agent-work-review
description: Create isolated half-year, annual, quarterly, promotion, or custom-range work reviews from Codex, OpenCode, Hermes, WorkBuddy, and Markdown/JSON histories. Extract output- and decision-centered evidence, audit and deduplicate candidates, have the current session Agent write grounded narratives, validate complete candidate coverage and freshness, save versioned summary.json/summary.md, and render a standalone local HTML presentation. Keep all data local.
---

# Agent Work Review

Use `work-review` for deterministic collection, workspace state, evidence lineage, validation, history, and rendering. The current session Agent owns semantic selection and writing. Treat `summary.json` and `summary.md` as canonical; HTML is the only built-in presentation format.

## Workflow

1. List existing reviews, then create or select the exact reporting range. Never reuse a review with a different period.

   ```bash
   work-review list-reviews
   work-review start --start YYYY-MM-DD --end YYYY-MM-DD --scenario phase-review --language zh --title "Work Review" --review-id <stable-id>
   work-review use <review-id>
   work-review current
   ```

2. Collect Codex history for the active range and import exports from other Agents. Codex collection extracts completed user turns, final answers, artifacts, decisions, and measured outcomes; it does not treat read-only shell usage as an output.

   ```bash
   work-review collect --source codex
   work-review import --agent <agent-name> --input <markdown-json-or-jsonl>
   ```

3. Merge and audit candidates.

   ```bash
   work-review merge
   work-review audit-candidates
   ```

   Read `references/value-judgment.md`, then inspect `candidates.json`. Extraction is recall, not final value judgment. Prefer explicit outputs, adopted decisions, measured outcomes, reusable methods, and verified progress over chat length. Review every `manual_review_candidate_id` and exclude advice-only or no-op work unless later evidence shows adoption.

4. Prepare the evidence scaffold.

   ```bash
   work-review prepare-draft
   ```

5. Read `references/drafting-guide.md` and rewrite `summary.draft.json`. Evidence lives under `evidence_context`; final narrative fields start empty and must be written by the session Agent. Group related candidates by output. Preserve `candidate_ids` and source provenance. Put every candidate in exactly one output or `excluded_candidates` with a reason.

6. Validate and preview before saving.

   ```bash
   work-review validate-draft
   work-review preview-draft
   ```

   Stop if the draft is stale, any candidate is pending, a source is missing, or any narrative remains empty.

7. Show the draft to the user. If a canonical summary exists, explicitly agree on overwrite, merge, or cancel. Save, then verify current state.

   ```bash
   work-review save-draft --mode overwrite
   work-review current
   ```

8. Render only from a fresh canonical summary, then verify again.

   ```bash
   work-review render-html
   work-review current
   ```

Use `history` and `restore <revision-id>` for recovery. Use `build` only when the user explicitly accepts a quick unreviewed scaffold.

## Outputs

- `reviews/<review-id>/review.json`: period, mode, state, and lineage
- `reviews/<review-id>/candidates.json`: deduplicated completed-turn candidates
- `reviews/<review-id>/summary.draft.json`: Agent writing workspace
- `reviews/<review-id>/summary.json`: validated canonical summary
- `reviews/<review-id>/summary.md`: validated report document
- `reviews/<review-id>/presentation.html`: standalone HTML presentation
- `reviews/<review-id>/history/`: recoverable prior revisions

## Boundaries

- Keep all evidence and outputs local unless the user explicitly exports them.
- Never ask for a real name or employee number by default.
- Import manual additions as evidence before drafting; do not bypass candidate coverage.
- Never call weekly-report systems or upload conversations.
- Do not generate PPTX, PDF, DOCX, or other built-in report formats.
