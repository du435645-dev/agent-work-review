# Output Schema

## Local Workspace

`init_local_review.py` creates:

```text
<root>/
├── config.json
├── inbox/
│   ├── codex/
│   ├── opencode/
│   ├── hermes/
│   ├── workbuddy/
│   └── manual/
├── review/
└── output/
```

The directory is private to one `person_id`. It has no network or 周律 integration.

## Work Evidence

`import_agent_evidence.py` emits one JSON object per line:

```json
{
  "person_id": "du-guiyang",
  "agent_type": "opencode",
  "device_id": "local",
  "session_id": "session-123",
  "started_at": "2026-07-01T01:00:00Z",
  "workspace": "D:\\work",
  "title": "推送礼包机制复盘",
  "signals": ["report"],
  "impact_level": "output",
  "impact_score": 90,
  "reason": "Imported with artifact references.",
  "artifact_paths": ["D:\\work\\reports\\review.html"],
  "source_refs": ["D:\\exports\\session.md"],
  "notes": "可选的导出内容或人工说明"
}
```

Required identity fields are `person_id`, `agent_type`, and `session_id`. Keep `source_refs` local and auditable.

## Merged Candidates

`merge_work_evidence.py` emits:

```json
{
  "person_id": "du-guiyang",
  "storage_mode": "local-only",
  "time_range": {
    "label": "custom",
    "start": "2026-01-01",
    "end": "2026-07-14"
  },
  "source_agents": ["codex", "opencode"],
  "workspaces": [
    {
      "workspace": "D:\\work",
      "candidates": [
        {
          "title": "推送礼包机制复盘",
          "source_agents": ["codex", "opencode"],
          "source_session_ids": ["a", "b"],
          "artifact_paths": ["D:\\work\\reports\\review.html"]
        }
      ]
    }
  ]
}
```

The deterministic merger only combines exact source identities or a shared artifact path inside the same workspace.

## Structured Summary

`build_review_summary.py` emits `structured_summary.json` and `structured_summary.md`. Each output item contains:

- `title`
- `workspace`
- `evidence_level`: `quantified`, `qualified`, or `progress`
- `background`
- `content`
- `impact`
- `next_plan`
- `source_agents`
- `source_session_ids`
- `source_refs`

## PPT Preparation

`prepare_guizang_brief.py` consumes the approved summary and emits:

- `brief.json`
- `outline.md`
- `speaker_notes.md`

The default `brief.json` uses `visual_style: swiss` and `slide_count_hint: 10-14`.
