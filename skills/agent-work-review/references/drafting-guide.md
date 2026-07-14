# Agent Drafting Guide

## Responsibility split

The CLI collects completed work turns, normalizes sources, deduplicates candidates, tracks freshness, validates coverage, saves history, and renders HTML. The session Agent decides what matters and writes the report.

## Candidate review

1. Read every candidate and its `evidence_context` and `source_refs`.
2. Organize by output or workstream, not Agent, session, or chat length.
3. Merge candidates only when they share an outcome, artifact, or clear workstream.
4. Preserve every merged candidate ID in the destination output.
5. Move unused candidates to `excluded_candidates` with a concrete reason.
6. Import missing manual evidence before drafting instead of inventing an unsupported output.

## Narrative rules

1. Write an `executive_summary` that states the main results and common thread.
2. Rewrite `background`, `content`, `impact`, and `next_plan`; do not copy the scaffold mechanically.
3. Use `quantified` only for measured numbers or explicit changes.
4. Use `qualified` for demonstrated non-numeric impact.
5. Use `progress` when impact is not yet observable.
6. Separate completed actions from outcomes and never manufacture business impact.
7. Preserve all `source_agents`, `source_session_ids`, and `source_refs` represented by the output's `candidate_ids`.

## Scenario emphasis

- `phase-review`: results, decisions, reusable methods, and next-stage plan.
- `self-review`: ownership, personal contribution, impact, capability growth, and goals.
- `formal-report`: objective context, delivery, evidence, risks, and planned actions.

## Freshness contract

Do not edit `based_on_candidates_digest`. If validation reports a stale draft, rerun merge and prepare a new draft. Do not use `--allow-stale` for a normal final report.
