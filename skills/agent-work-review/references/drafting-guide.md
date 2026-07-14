# Agent Drafting Guide

## Responsibility split

The CLI collects, normalizes, deduplicates, validates, saves, and renders. The session Agent decides what matters and writes the report.

## Drafting rules

1. Read every selected candidate and its source references before rewriting.
2. Organize by output or workstream, not by Agent, session, or chat length.
3. Merge only when candidates share a clear workstream, artifact, or outcome.
4. Write one overall `executive_summary` that explains the main results and the common thread.
5. For each output, write background, delivered content, impact, and next plan.
6. Preserve all supporting `source_agents`, `source_session_ids`, and `source_refs` when combining candidates.
7. Use `quantified` only when numbers or explicit measured change support the impact.
8. Use `qualified` for demonstrated but non-numeric impact.
9. Use `progress` when work is incomplete or impact is not yet observable.
10. Never turn completed actions into unsupported business outcomes.

## Scenario emphasis

- `phase-review`: results, decisions, reusable methods, and next-stage plan.
- `self-review`: ownership, personal contribution, impact, capability growth, and future goals.
- `formal-report`: objective context, delivery, evidence, risks, and planned actions.

## Draft contract

Edit `review/summary.draft.json`. Keep these top-level fields:

- `schema_version`
- `review_mode`
- `language`
- `title`
- `subtitle`
- `executive_summary`
- `source_agents`
- `time_range`
- `outputs`

Each output must keep:

- `title`
- `workspace`
- `evidence_level`
- `background`
- `content`
- `impact`
- `next_plan`
- `source_agents`
- `source_session_ids`
- `source_refs`
