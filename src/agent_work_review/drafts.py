from __future__ import annotations

import json
from pathlib import Path

from .pipeline import summarize_candidates, write_summary


REQUIRED_OUTPUT_FIELDS = ("title", "workspace", "background", "content", "impact", "next_plan")
EVIDENCE_LEVELS = {"quantified", "qualified", "progress"}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def draft_path(home: Path) -> Path:
    return home / "review" / "summary.draft.json"


def current_state(home: Path) -> dict:
    candidates_path = home / "review" / "candidates.json"
    summary_draft = draft_path(home)
    summary_path = home / "review" / "summary.json"
    markdown_path = home / "review" / "summary.md"
    presentation_path = home / "output" / "presentation.html"
    candidates = read_json(candidates_path) if candidates_path.is_file() else {}
    return {
        "home": str(home),
        "candidates": {
            "exists": candidates_path.is_file(),
            "path": str(candidates_path),
            "count": sum(len(group.get("candidates", [])) for group in candidates.get("workspaces", [])),
        },
        "draft": {"exists": summary_draft.is_file(), "path": str(summary_draft)},
        "summary": {"exists": summary_path.is_file(), "path": str(summary_path)},
        "summary_markdown": {"exists": markdown_path.is_file(), "path": str(markdown_path)},
        "presentation": {"exists": presentation_path.is_file(), "path": str(presentation_path)},
    }


def prepare_draft(
    home: Path,
    candidates: dict,
    *,
    scenario: str,
    language: str,
    title: str,
    subtitle: str = "",
    force: bool = False,
) -> Path:
    output = draft_path(home)
    if output.exists() and not force:
        raise FileExistsError(f"Draft already exists: {output}. Use --force only after deciding to replace it.")
    summary = summarize_candidates(candidates, scenario=scenario, language=language)
    summary.update({
        "title": title,
        "subtitle": subtitle,
        "executive_summary": "",
        "draft_status": "agent-review-required",
    })
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def validate_draft(draft: dict, candidates: dict | None = None) -> list[str]:
    errors: list[str] = []
    if draft.get("schema_version") != "1.0":
        errors.append("schema_version must be 1.0")
    if draft.get("language") not in {"en", "zh"}:
        errors.append("language must be en or zh")
    if draft.get("review_mode") not in {"phase-review", "self-review", "formal-report"}:
        errors.append("review_mode must be phase-review, self-review, or formal-report")
    if not str(draft.get("title") or "").strip():
        errors.append("title is required")
    if not str(draft.get("executive_summary") or "").strip():
        errors.append("executive_summary is required after Agent drafting")
    outputs = draft.get("outputs")
    if not isinstance(outputs, list) or not outputs:
        errors.append("outputs must be a non-empty list")
        return errors

    known_sessions = {
        str(session_id)
        for group in (candidates or {}).get("workspaces", [])
        for item in group.get("candidates", [])
        for session_id in item.get("source_session_ids", [item.get("session_id")])
        if session_id
    }
    for index, item in enumerate(outputs, 1):
        prefix = f"outputs[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        for field in REQUIRED_OUTPUT_FIELDS:
            if not str(item.get(field) or "").strip():
                errors.append(f"{prefix}.{field} is required")
        if item.get("evidence_level") not in EVIDENCE_LEVELS:
            errors.append(f"{prefix}.evidence_level must be quantified, qualified, or progress")
        source_agents = item.get("source_agents")
        source_sessions = item.get("source_session_ids")
        if not isinstance(source_agents, list) or not source_agents:
            errors.append(f"{prefix}.source_agents must be a non-empty list")
        if not isinstance(source_sessions, list) or not source_sessions:
            errors.append(f"{prefix}.source_session_ids must be a non-empty list")
        elif known_sessions and not any(str(value) in known_sessions for value in source_sessions):
            errors.append(f"{prefix}.source_session_ids do not match reviewed candidates")
    return errors


def merge_summaries(current: dict, incoming: dict) -> dict:
    merged = {**current, **incoming}
    combined: dict[tuple[str, str], dict] = {}
    order: list[tuple[str, str]] = []
    for item in [*current.get("outputs", []), *incoming.get("outputs", [])]:
        key = (str(item.get("workspace") or "").casefold(), str(item.get("title") or "").casefold())
        if key not in combined:
            order.append(key)
        combined[key] = item
    merged["outputs"] = [combined[key] for key in order]
    merged["source_agents"] = sorted(set([*current.get("source_agents", []), *incoming.get("source_agents", [])]))
    return merged


def save_draft(home: Path, draft: dict, *, mode: str) -> tuple[Path, Path]:
    summary_path = home / "review" / "summary.json"
    if summary_path.exists():
        if mode == "error":
            raise FileExistsError("A canonical summary already exists. Choose --mode overwrite or --mode merge explicitly.")
        if mode == "merge":
            draft = merge_summaries(read_json(summary_path), draft)
    draft = {**draft, "draft_status": "approved", "summary_origin": "agent-reviewed"}
    return write_summary(home, draft)
