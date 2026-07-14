---
name: agent-work-review
description: Aggregate one person's work evidence from multiple AI coding agents or exported Markdown/JSON histories, review and deduplicate output-centered candidates, create a reusable structured summary, and render a standalone HTML presentation. Use for work reviews, retrospectives, self-reviews, promotion narratives, or cross-agent history consolidation. Keep all data local and treat summary.json and summary.md as the canonical outputs.
---

# Agent Work Review

Use the cross-platform `work-review` CLI as the deterministic engine. Keep the structured summary as the source of truth; HTML is the only built-in presentation format.

## Workflow

1. Initialize local storage:

   ```bash
   work-review init
   ```

2. Collect native Codex history when available:

   ```bash
   work-review collect --source codex --start YYYY-MM-DD --end YYYY-MM-DD
   ```

3. Import exports from any other Agent:

   ```bash
   work-review import --agent <agent-name> --input <markdown-json-or-jsonl>
   ```

4. Merge evidence and inspect `~/.work-review/data/review/candidates.json` with the user. Keep, exclude, rename, split, or merge candidates conservatively.

5. Build the canonical summary and HTML presentation:

   ```bash
   work-review build --start YYYY-MM-DD --end YYYY-MM-DD --language <en-or-zh> --title "Work Review"
   ```

   Match the output language to the user's request. Chinese output is supported directly and does not require an English fallback.

6. Improve `summary.json` or `summary.md` with the user when semantic judgment is needed, then rerun `work-review render-html`. Do not invent outcomes that lack evidence.

## Outputs

- `review/candidates.json`: reviewed cross-agent work candidates
- `review/summary.json`: canonical machine-readable summary
- `review/summary.md`: canonical human-readable summary
- `output/presentation.html`: standalone HTML presentation

Do not generate PPTX, PDF, DOCX, or other report formats. Users may transform the canonical summary with their own tools.

## Privacy

- Keep all evidence local unless the user explicitly exports it.
- Never ask for a real name or employee number by default.
- Never merge evidence carrying another local identity.
- Never call unrelated report systems or upload raw conversations.
