---
name: work-review-ppt-summary
description: Use when an Agent needs to privately summarize one person's work across a selected time range from Codex, OpenCode, Hermes, WorkBuddy, manual notes, or mixed local exports into a candidate output list, structured recap, guizang HTML PPT brief, and Markdown speaker notes. Trigger for stage reviews, periodic retrospectives, personal review prep, promotion-story drafting, or cross-Agent work-history consolidation where outputs and decisions matter more than chat length.
---

# Work Review PPT Summary

Build a local-only work-review package from one person's Agent histories and workspace artifacts. Share the skill and evidence format between teammates, but keep each teammate's evidence and outputs on their own machine.

## Privacy Boundary

- Do not call the 周律 API or reuse 周律 tokens, storage, or drafts.
- Do not upload raw conversations or review outputs.
- Keep one anonymous, stable `person_id` per local review workspace. Generate it automatically unless the user explicitly needs an override.
- Ignore evidence carrying a different `person_id` during merge.
- Treat network sync or team aggregation as out of scope unless the user explicitly requests it.

## Workflow

1. Initialize a private local workspace.

   ```powershell
   python -X utf8 scripts/init_local_review.py --root <local-review-root>
   ```

   This creates `inbox/<agent>/`, `review/`, `output/`, and a local-only `config.json`. Reuse the generated anonymous `person_id` automatically; do not ask for a name or employee number by default.

2. Confirm the review scene and time range.

   Supported scenes:
   - `phase-review`
   - `self-review`
   - `formal-report`

3. Collect or import evidence from every Agent used by the person.

   For Codex, use the native collector:

   ```powershell
   python -X utf8 scripts/collect_session_candidates.py --start <YYYY-MM-DD> --end <YYYY-MM-DD> --output <inbox>/codex/candidates.json
   ```

   For OpenCode, Hermes, WorkBuddy, manual notes, or another Agent, export Markdown, text, JSON, or JSONL and normalize it:

   ```powershell
   python -X utf8 scripts/import_agent_evidence.py --input <export-path> --agent-type <agent> --output <inbox>/<agent>/evidence.jsonl
   ```

   Do not claim native session access for an Agent unless its storage/API has been verified. Use the generic importer as the safe fallback.

4. Merge all local sources into one candidate list.

   ```powershell
   python -X utf8 scripts/merge_work_evidence.py --input-dir <inbox> --start <YYYY-MM-DD> --end <YYYY-MM-DD> --output <review>/candidates.json
   ```

   Merge exact source identities and shared artifact paths conservatively. Leave uncertain semantic merges for user review.

5. Review candidates before writing the summary.

   Group by workspace and order by `output`, `decision`, then `progress`. Allow:
   - keep
   - exclude
   - merge
   - split
   - rename
   - add note
   - manual addition

6. Build recap items by output line, not by Agent or thread.

   ```powershell
   python -X utf8 scripts/build_review_summary.py --input <review>/candidates.json --scenario self-review --output-dir <review>/summary
   ```

   Use this default structure:
   - `产出的背景`
   - `产出的内容`
   - `产出的成效`
   - `后续计划（如果有）`

7. Grade effects by evidence.

   - Use `quantified` for numerical evidence.
   - Use `qualified` for concrete adoption or workflow impact.
   - Use `progress` for unfinished work.

8. Prepare guizang inputs only after the recap is accepted.

   ```powershell
   python -X utf8 scripts/prepare_guizang_brief.py --input <review>/summary/structured_summary.json --output-dir <output>
   ```

   Default to guizang Swiss style, an HTML deck, and Markdown speaker notes. Hand the approved brief to `$guizang-ppt-skill`; do not jump from raw histories directly to slides.

## Scripts

- `scripts/init_local_review.py`: create the private local workspace.
- `scripts/collect_session_candidates.py`: collect native Codex candidates.
- `scripts/import_agent_evidence.py`: normalize generic Agent exports.
- `scripts/merge_work_evidence.py`: merge and deduplicate local evidence.
- `scripts/build_review_summary.py`: build the structured recap.
- `scripts/prepare_guizang_brief.py`: produce the PPT brief, outline, and notes.

## References

- Read `references/output_schema.md` when creating or debugging evidence exports.
- Read `references/review_modes.md` when choosing the recap scene.

## Guardrails

- Do not rank by chat length.
- Do not merge unrelated work because titles look similar.
- Do not overstate effects when only progress evidence exists.
- Do not mix different teammates in one local review workspace.
- Do not treat generic Markdown imports as complete conversation archives.
