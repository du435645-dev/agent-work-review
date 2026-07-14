from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from .pipeline import summarize_candidates, write_summary
from .storage import atomic_write_json, atomic_write_text, digest_file, digest_json, timestamp_slug, utc_now


REQUIRED_OUTPUT_FIELDS = ("title", "workspace", "background", "content", "impact", "next_plan")
EVIDENCE_LEVELS = {"quantified", "qualified", "progress"}
REVISION_ID_RE = re.compile(r"^[0-9]{8}T[0-9]{6}_[0-9]{6}Z$")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def draft_path(review_dir: Path) -> Path:
    return review_dir / "summary.draft.json"


def canonical_digest(value: dict, field: str) -> str:
    return digest_json({key: item for key, item in value.items() if key != field})


def candidate_index(candidates: dict) -> dict[str, dict]:
    return {
        str(item.get("candidate_id")): item
        for group in candidates.get("workspaces", [])
        for item in group.get("candidates", [])
        if item.get("candidate_id")
    }


def coverage_state(draft: dict, candidates: dict) -> dict:
    known = set(candidate_index(candidates))
    included_list = [str(value) for item in draft.get("outputs", []) for value in item.get("candidate_ids", [])]
    excluded_list = [str(item.get("candidate_id") or "") for item in draft.get("excluded_candidates", []) if item.get("candidate_id")]
    included = set(included_list)
    excluded = set(excluded_list)
    duplicate_included = sorted({value for value in included_list if included_list.count(value) > 1})
    duplicate_excluded = sorted({value for value in excluded_list if excluded_list.count(value) > 1})
    return {
        "known": sorted(known),
        "included": sorted(included),
        "excluded": sorted(excluded),
        "pending": sorted(known - included - excluded),
        "unknown": sorted((included | excluded) - known),
        "overlap": sorted(included & excluded),
        "duplicate_included": duplicate_included,
        "duplicate_excluded": duplicate_excluded,
    }


def current_state(review_dir: Path, manifest: dict) -> dict:
    candidates_path = review_dir / "candidates.json"
    summary_draft = draft_path(review_dir)
    summary_path = review_dir / "summary.json"
    markdown_path = review_dir / "summary.md"
    presentation_path = review_dir / "presentation.html"
    presentation_meta_path = review_dir / "presentation.meta.json"
    candidates = read_json(candidates_path) if candidates_path.is_file() else {}
    draft = read_json(summary_draft) if summary_draft.is_file() else {}
    summary = read_json(summary_path) if summary_path.is_file() else {}
    presentation_meta = read_json(presentation_meta_path) if presentation_meta_path.is_file() else {}
    candidates_digest = str(candidates.get("candidates_digest") or "")
    coverage = coverage_state(draft, candidates) if draft and candidates else {"included": [], "excluded": [], "pending": [], "unknown": [], "overlap": [], "duplicate_included": [], "duplicate_excluded": []}
    return {
        "review_id": manifest.get("review_id"),
        "state": manifest.get("state"),
        "time_range": manifest.get("time_range"),
        "review_mode": manifest.get("review_mode"),
        "review_dir": str(review_dir),
        "candidates": {
            "exists": candidates_path.is_file(),
            "path": str(candidates_path),
            "count": len(candidate_index(candidates)),
            "digest": candidates_digest or None,
        },
        "draft": {
            "exists": summary_draft.is_file(),
            "path": str(summary_draft),
            "digest": canonical_digest(draft, "draft_digest") if draft else None,
            "fresh": bool(draft and candidates_digest and draft.get("based_on_candidates_digest") == candidates_digest),
            "coverage": {key: len(value) for key, value in coverage.items() if key != "known"},
        },
        "summary": {
            "exists": summary_path.is_file(),
            "path": str(summary_path),
            "digest": summary.get("summary_digest"),
            "fresh": bool(summary and candidates_digest and summary.get("based_on_candidates_digest") == candidates_digest),
        },
        "summary_markdown": {"exists": markdown_path.is_file(), "path": str(markdown_path)},
        "presentation": {
            "exists": presentation_path.is_file(),
            "path": str(presentation_path),
            "fresh": bool(summary and presentation_meta.get("summary_digest") == summary.get("summary_digest") and digest_file(presentation_path) == presentation_meta.get("presentation_digest")),
        },
        "history_count": len(list((review_dir / "history").glob("*/revision.json"))),
    }


def prepare_draft(
    review_dir: Path,
    candidates: dict,
    *,
    scenario: str,
    language: str,
    title: str,
    subtitle: str = "",
    force: bool = False,
) -> Path:
    output = draft_path(review_dir)
    if output.exists() and not force:
        raise FileExistsError(f"Draft already exists: {output}. Use --force only after deciding to replace it.")
    summary = summarize_candidates(candidates, scenario=scenario, language=language)
    source_candidates = candidate_index(candidates)
    for item in summary.get("outputs", []):
        source = source_candidates.get(str(item.get("candidate_ids", [""])[0]), {})
        item["evidence_context"] = {
            "background": item.get("background", ""),
            "content": item.get("content", ""),
            "impact": item.get("impact", ""),
            "next_plan": item.get("next_plan", ""),
            "source_refs": item.get("source_refs", []),
            "artifact_paths": source.get("artifact_paths", []),
            "signals": source.get("signals", []),
            "has_mutating_tool": bool(source.get("has_mutating_tool")),
            "reason": source.get("reason", ""),
            "started_at": source.get("started_at", ""),
        }
        item["background"] = ""
        item["content"] = ""
        item["impact"] = ""
        item["next_plan"] = ""
    summary.update({
        "title": title,
        "subtitle": subtitle,
        "executive_summary": "",
        "draft_status": "agent-review-required",
        "based_on_candidates_digest": candidates.get("candidates_digest"),
        "excluded_candidates": [],
    })
    review_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_json(output, summary)
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
    if candidates and draft.get("based_on_candidates_digest") != candidates.get("candidates_digest"):
        errors.append("draft is stale because candidates_digest changed")
    outputs = draft.get("outputs")
    if not isinstance(outputs, list) or not outputs:
        errors.append("outputs must be a non-empty list")
        return errors

    index = candidate_index(candidates or {})
    coverage = coverage_state(draft, candidates or {})
    if coverage["pending"]:
        errors.append(f"pending candidates must be included or excluded: {coverage['pending']}")
    if coverage["unknown"]:
        errors.append(f"unknown candidate_ids: {coverage['unknown']}")
    if coverage["overlap"]:
        errors.append(f"candidate_ids cannot be both included and excluded: {coverage['overlap']}")
    if coverage["duplicate_included"]:
        errors.append(f"candidate_ids cannot appear in multiple outputs: {coverage['duplicate_included']}")
    if coverage["duplicate_excluded"]:
        errors.append(f"candidate_ids cannot be excluded more than once: {coverage['duplicate_excluded']}")

    for exclusion in draft.get("excluded_candidates", []):
        if not str(exclusion.get("reason") or "").strip():
            errors.append(f"excluded candidate {exclusion.get('candidate_id')} requires a reason")

    for position, item in enumerate(outputs, 1):
        prefix = f"outputs[{position}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        candidate_ids = [str(value) for value in item.get("candidate_ids", [])]
        if not candidate_ids:
            errors.append(f"{prefix}.candidate_ids must be a non-empty list")
        for field in REQUIRED_OUTPUT_FIELDS:
            if not str(item.get(field) or "").strip():
                errors.append(f"{prefix}.{field} is required after Agent drafting")
        if item.get("evidence_level") not in EVIDENCE_LEVELS:
            errors.append(f"{prefix}.evidence_level must be quantified, qualified, or progress")
        source_agents = set(str(value) for value in item.get("source_agents", []))
        source_sessions = set(str(value) for value in item.get("source_session_ids", []))
        source_refs = set(str(value) for value in item.get("source_refs", []))
        if not source_agents:
            errors.append(f"{prefix}.source_agents must be a non-empty list")
        if not source_sessions:
            errors.append(f"{prefix}.source_session_ids must be a non-empty list")
        expected_agents = {str(agent) for candidate_id in candidate_ids for agent in index.get(candidate_id, {}).get("source_agents", [])}
        expected_sessions = {str(session) for candidate_id in candidate_ids for session in index.get(candidate_id, {}).get("source_session_ids", [])}
        expected_refs = {str(ref) for candidate_id in candidate_ids for ref in index.get(candidate_id, {}).get("source_refs", [])}
        if expected_agents - source_agents:
            errors.append(f"{prefix}.source_agents are missing reviewed sources: {sorted(expected_agents - source_agents)}")
        if expected_sessions - source_sessions:
            errors.append(f"{prefix}.source_session_ids are missing reviewed sources: {sorted(expected_sessions - source_sessions)}")
        if expected_refs - source_refs:
            errors.append(f"{prefix}.source_refs are missing reviewed sources: {sorted(expected_refs - source_refs)}")
    return errors


def merge_summaries(current: dict, incoming: dict) -> dict:
    incoming_ids = {str(value) for item in incoming.get("outputs", []) for value in item.get("candidate_ids", [])}
    excluded_ids = {str(item.get("candidate_id")) for item in incoming.get("excluded_candidates", []) if item.get("candidate_id")}
    covered_ids = incoming_ids | excluded_ids
    retained = [item for item in current.get("outputs", []) if not covered_ids.intersection(str(value) for value in item.get("candidate_ids", []))]
    merged = {**current, **incoming}
    merged["outputs"] = [*retained, *incoming.get("outputs", [])]
    merged["source_agents"] = sorted(set([*current.get("source_agents", []), *incoming.get("source_agents", [])]))
    return merged


def backup_current(review_dir: Path, *, operation: str) -> Path | None:
    names = ("summary.json", "summary.md", "presentation.html", "presentation.meta.json")
    existing = [review_dir / name for name in names if (review_dir / name).is_file()]
    if not existing:
        return None
    revision_dir = review_dir / "history" / timestamp_slug()
    revision_dir.mkdir(parents=True, exist_ok=False)
    for source in existing:
        shutil.copy2(source, revision_dir / source.name)
    atomic_write_json(revision_dir / "revision.json", {
        "created_at": utc_now(),
        "operation": operation,
        "summary_digest": read_json(review_dir / "summary.json").get("summary_digest") if (review_dir / "summary.json").is_file() else None,
        "files": [path.name for path in existing],
    })
    return revision_dir


def restore_revision_files(review_dir: Path, revision_dir: Path, *, exact: bool = True) -> list[str]:
    revision = read_json(revision_dir / "revision.json")
    revision_files = {str(name) for name in revision.get("files", [])}
    if exact:
        for name in ("summary.json", "summary.md", "presentation.html", "presentation.meta.json"):
            if name not in revision_files:
                (review_dir / name).unlink(missing_ok=True)
    restored = []
    for name in revision_files:
        source = revision_dir / str(name)
        if source.is_file():
            atomic_write_text(review_dir / source.name, source.read_text(encoding="utf-8"))
            restored.append(source.name)
    return restored


def save_draft(review_dir: Path, draft: dict, *, mode: str, candidates: dict | None = None) -> tuple[Path, Path, Path | None]:
    summary_path = review_dir / "summary.json"
    backup = None
    if summary_path.exists():
        if mode == "error":
            raise FileExistsError("A canonical summary already exists. Choose --mode overwrite or --mode merge explicitly.")
        if mode == "merge":
            draft = merge_summaries(read_json(summary_path), draft)
    if candidates:
        errors = validate_draft(draft, candidates)
        if errors:
            raise ValueError("Merged draft failed validation: " + "; ".join(errors))
    if summary_path.exists():
        backup = backup_current(review_dir, operation=mode)
    draft = {
        **draft,
        "draft_status": "approved",
        "summary_origin": "agent-reviewed",
        "approved_at": utc_now(),
    }
    draft.pop("draft_digest", None)
    had_summary = summary_path.exists()
    had_markdown = (review_dir / "summary.md").exists()
    try:
        paths = write_summary(review_dir, draft, review_dir=review_dir)
        saved = read_json(paths[0])
        if saved.get("summary_digest") != canonical_digest(saved, "summary_digest"):
            raise RuntimeError("Post-save summary digest verification failed")
        if not paths[1].read_text(encoding="utf-8").strip():
            raise RuntimeError("Post-save Markdown verification failed")
    except Exception:
        if backup:
            restore_revision_files(review_dir, backup)
        else:
            if not had_summary:
                summary_path.unlink(missing_ok=True)
            if not had_markdown:
                (review_dir / "summary.md").unlink(missing_ok=True)
        raise
    return paths[0], paths[1], backup


def preview_draft(review_dir: Path, draft: dict, candidates: dict) -> tuple[dict, Path]:
    errors = validate_draft(draft, candidates)
    coverage = coverage_state(draft, candidates)
    current = read_json(review_dir / "summary.json") if (review_dir / "summary.json").is_file() else {"outputs": []}
    current_ids = {str(value) for item in current.get("outputs", []) for value in item.get("candidate_ids", [])}
    draft_ids = {str(value) for item in draft.get("outputs", []) for value in item.get("candidate_ids", [])}
    result = {
        "valid": not errors,
        "errors": errors,
        "draft_digest": canonical_digest(draft, "draft_digest"),
        "coverage": {key: values for key, values in coverage.items() if key != "known"},
        "changes": {
            "new_candidate_ids": sorted(draft_ids - current_ids),
            "removed_candidate_ids": sorted(current_ids - draft_ids),
            "retained_candidate_ids": sorted(current_ids & draft_ids),
        },
    }
    lines = [
        "# Draft Preview",
        "",
        f"- Valid: {result['valid']}",
        f"- Included candidates: {len(coverage['included'])}",
        f"- Excluded candidates: {len(coverage['excluded'])}",
        f"- Pending candidates: {len(coverage['pending'])}",
        f"- New candidates: {len(result['changes']['new_candidate_ids'])}",
        f"- Removed candidates: {len(result['changes']['removed_candidate_ids'])}",
    ]
    if errors:
        lines.extend(["", "## Validation errors", "", *[f"- {error}" for error in errors]])
    output = review_dir / "summary.preview.md"
    atomic_write_text(output, "\n".join(lines) + "\n")
    return result, output


def list_history(review_dir: Path) -> list[dict]:
    revisions = []
    for path in sorted((review_dir / "history").glob("*/revision.json"), reverse=True):
        value = read_json(path)
        value["revision_id"] = path.parent.name
        revisions.append(value)
    return revisions


def restore_history(review_dir: Path, revision_id: str) -> list[str]:
    if not REVISION_ID_RE.fullmatch(revision_id):
        raise ValueError("revision_id must be a revision returned by work-review history")
    revision_dir = review_dir / "history" / revision_id
    read_json(revision_dir / "revision.json")
    backup_current(review_dir, operation=f"before-restore-{revision_id}")
    restored = restore_revision_files(review_dir, revision_dir)
    if not restored:
        raise RuntimeError(f"Revision contains no restorable files: {revision_id}")
    return restored
