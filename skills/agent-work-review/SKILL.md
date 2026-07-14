---
name: agent-work-review
description: Aggregate one person's work evidence from Codex, OpenCode, Hermes, WorkBuddy, or exported Markdown/JSON histories; review and deduplicate output-centered candidates; have the current session Agent draft and polish a grounded work-review document; validate and save canonical summary.json/summary.md; and render a standalone HTML presentation. Use for work reviews, retrospectives, self-reviews, promotion narratives, formal reports, or cross-agent history consolidation. Keep all data local.
---

# Agent Work Review

Use `work-review` for deterministic collection, state management, validation, and rendering. The current session Agent owns semantic selection, synthesis, and writing. Treat `summary.json` and `summary.md` as canonical; HTML is the only built-in presentation format.

## Workflow

1. Inspect local state before changing anything:

   ```bash
   work-review current
   ```

2. Collect native Codex history and import exports from other Agents:

   ```bash
   work-review collect --source codex --start YYYY-MM-DD --end YYYY-MM-DD
   work-review import --agent <agent-name> --input <markdown-json-or-jsonl>
   ```

3. Merge evidence, then inspect `review/candidates.json` with the user:

   ```bash
   work-review merge --start YYYY-MM-DD --end YYYY-MM-DD
   ```

   Keep, exclude, rename, split, or conservatively merge candidates. Prefer outputs and decisions over conversation length.

4. Create a local scaffold:

   ```bash
   work-review prepare-draft --language <en-or-zh> --scenario <phase-review-or-self-review-or-formal-report> --title "Work Review"
   ```

5. Read `references/drafting-guide.md`, then rewrite `review/summary.draft.json`. Do not leave template prose as final content. Add an executive summary, merge related candidates into output-centered narratives, preserve source IDs, distinguish quantified impact from qualitative impact and progress, and never invent outcomes.

6. Validate the Agent-authored draft:

   ```bash
   work-review validate-draft
   ```

7. Show the draft to the user. Before saving, run `work-review current`. If a canonical summary already exists, explicitly agree on `overwrite`, `merge`, or cancel. Then save:

   ```bash
   work-review save-draft --mode overwrite
   ```

8. Render only from the saved canonical summary:

   ```bash
   work-review render-html
   ```

Use `work-review build` only for an explicitly requested quick, unreviewed scaffold. It is not the default final-report workflow.

## Outputs

- `review/candidates.json`: reviewed cross-Agent candidates
- `review/summary.draft.json`: session Agent working draft
- `review/summary.json`: validated canonical summary
- `review/summary.md`: validated human-readable report
- `output/presentation.html`: standalone HTML presentation

## Privacy

- Keep evidence and outputs local unless the user explicitly exports them.
- Never ask for a real name or employee number by default.
- Never merge another local identity.
- Never call weekly-report systems or upload raw conversations.
- Do not generate PPTX, PDF, DOCX, or other built-in report formats.
