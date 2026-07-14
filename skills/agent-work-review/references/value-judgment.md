# Value Judgment Guide

Candidate extraction is recall, not the final judgment. The session Agent must read evidence and decide whether each candidate belongs in the report.

## Keep

Keep a candidate when evidence supports at least one of these:

- A concrete deliverable was completed, published, adopted, or put into use.
- A decision or tradeoff was adopted and materially guided later work.
- A measured business, quality, speed, coverage, reliability, or cost result exists.
- A reusable workflow, rule, tool, template, or method was established.
- Meaningful progress reached a named milestone and the unfinished boundary is explicit.

## Exclude

Exclude a candidate when it is only:

- General advice or Q&A with no adopted decision or follow-up action.
- Read-only inspection, environment setup, or status checking with no resulting output.
- A repeated update already represented by a stronger candidate.
- A failed or abandoned attempt with no reusable lesson.
- Vague activity that cannot be grounded in a source or artifact.
- Unrelated to the requested reporting range or scenario.

Use `insufficient evidence` as the reason when the work may matter but the available export is too weak. Ask for a manual evidence import instead of inventing impact.

## Merge

Merge candidates only when they advance the same outcome. Shared topic words alone are not enough. Strong anchors include the same artifact, project milestone, business adjustment, decision chain, or reportable result.

When merging:

- Preserve all candidate IDs and source provenance.
- Remove repeated process narration.
- Write one output-centered title and one coherent narrative.
- Keep distinct outcomes separate even when they belong to the same workspace.

## Evidence level

- `quantified`: measured values, counts, percentages, time saved, coverage, quality, or verified test results.
- `qualified`: demonstrated non-numeric effect supported by delivery or adoption evidence.
- `progress`: milestone reached, but final effect is not yet observable.

Do not rank value by chat length, number of tool calls, or writing style. Prefer evidence and impact.
