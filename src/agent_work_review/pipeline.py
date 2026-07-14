from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

from .locales import QUANTIFIED_TOKENS, SUMMARY_TEXT


LEVEL_ORDER = {"output": 0, "decision": 1, "progress": 2}


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in records), encoding="utf-8")


def append_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for item in records:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")


def read_records(path: Path) -> list[dict]:
    if path.suffix.lower() == ".jsonl":
        return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    document = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(document, dict) and "workspaces" in document:
        return [dict(item) for group in document["workspaces"] for item in group.get("candidates", [])]
    return document if isinstance(document, list) else [document]


def item_date(item: dict) -> date | None:
    value = str(item.get("started_at") or "")
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None


def merge_key(item: dict) -> tuple[str, ...]:
    workspace = str(item.get("workspace") or "unknown").casefold()
    artifacts = sorted(str(value).replace("/", "\\").casefold() for value in item.get("artifact_paths", []))
    if artifacts:
        return ("artifact", workspace, artifacts[0])
    return ("source", str(item.get("agent_type") or "generic").casefold(), str(item.get("session_id") or item.get("title") or "unknown").casefold())


def merge_pair(current: dict, incoming: dict) -> dict:
    if LEVEL_ORDER.get(str(incoming.get("impact_level")), 9) < LEVEL_ORDER.get(str(current.get("impact_level")), 9):
        current["impact_level"] = incoming["impact_level"]
    current["impact_score"] = max(int(current.get("impact_score") or 0), int(incoming.get("impact_score") or 0))
    for field in ("signals", "artifact_paths", "source_refs", "source_session_ids", "source_agents"):
        current[field] = sorted(set([*current.get(field, []), *incoming.get(field, [])]))
    for field in ("notes", "background", "impact", "next_plan"):
        values = [str(value).strip() for value in (current.get(field), incoming.get(field)) if str(value or "").strip()]
        current[field] = "\n\n".join(dict.fromkeys(values))
    current["reason"] = "Merged by exact source identity or shared artifact path."
    return current


def merge_home(home: Path, *, person_id: str, start: date | None = None, end: date | None = None) -> dict:
    merged: dict[tuple[str, ...], dict] = {}
    for path in sorted((home / "inbox").rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".json", ".jsonl"}:
            continue
        for raw in read_records(path):
            if raw.get("person_id") and raw["person_id"] != person_id:
                continue
            current_date = item_date(raw)
            if start and current_date and current_date < start:
                continue
            if end and current_date and current_date > end:
                continue
            item = {
                **raw,
                "schema_version": "1.0",
                "person_id": person_id,
                "workspace": str(raw.get("workspace") or raw.get("cwd") or "unknown"),
                "source_agents": sorted(set([*raw.get("source_agents", []), str(raw.get("agent_type") or "generic")])),
                "source_session_ids": sorted(set([*raw.get("source_session_ids", []), str(raw.get("session_id") or raw.get("title") or "unknown")])),
            }
            key = merge_key(item)
            merged[key] = merge_pair(merged[key], item) if key in merged else item

    grouped: dict[str, list[dict]] = defaultdict(list)
    for item in merged.values():
        grouped[item["workspace"]].append(item)
    workspaces = []
    for workspace in sorted(grouped):
        candidates = sorted(grouped[workspace], key=lambda item: (LEVEL_ORDER.get(str(item.get("impact_level")), 9), -int(item.get("impact_score") or 0), str(item.get("started_at") or "")))
        workspaces.append({"workspace": workspace, "candidates": candidates})
    result = {
        "schema_version": "1.0",
        "person_id": person_id,
        "storage_mode": "local-only",
        "time_range": {"start": start.isoformat() if start else None, "end": end.isoformat() if end else None},
        "source_agents": sorted({agent for item in merged.values() for agent in item.get("source_agents", [])}),
        "workspaces": workspaces,
    }
    output = home / "review" / "candidates.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def summarize_candidates(candidates: dict, *, scenario: str, language: str) -> dict:
    labels = SUMMARY_TEXT[language]
    outputs = []
    for group in candidates.get("workspaces", []):
        workspace = str(group.get("workspace") or "unknown")
        for item in group.get("candidates", []):
            level = str(item.get("impact_level") or "progress")
            artifacts = item.get("artifact_paths") or []
            content = str(item.get("notes") or "").strip()
            if not content and artifacts:
                content = ", ".join(artifacts[:3])
            if not content:
                content = labels["default_output"] if level == "output" else labels["default_decision"] if level == "decision" else labels["default_progress"]
            impact = str(item.get("impact") or "").strip()
            if not impact:
                impact = labels["default_output"] if level == "output" else labels["default_decision"] if level == "decision" else labels["default_progress"]
            evidence = "quantified" if any(token in (content + impact) for token in QUANTIFIED_TOKENS) else "qualified" if level in {"output", "decision"} else "progress"
            outputs.append({
                "title": str(item.get("title") or "Untitled work item"),
                "workspace": workspace,
                "evidence_level": evidence,
                "background": str(item.get("background") or "").strip() or labels["default_background"].format(workspace=Path(workspace).name or workspace),
                "content": content[:1200],
                "impact": impact[:800],
                "next_plan": str(item.get("next_plan") or "").strip() or labels["default_next"],
                "source_agents": item.get("source_agents") or [item.get("agent_type", "generic")],
                "source_session_ids": item.get("source_session_ids") or [item.get("session_id", "unknown")],
                "source_refs": item.get("source_refs", []),
            })
    return {
        "schema_version": "1.0",
        "review_mode": scenario,
        "language": language,
        "summary_structure": [labels["background"], labels["content"], labels["impact"], labels["next"]],
        "source_agents": candidates.get("source_agents", []),
        "time_range": candidates.get("time_range", {}),
        "outputs": outputs,
    }


def write_summary(home: Path, summary: dict) -> tuple[Path, Path]:
    review = home / "review"
    review.mkdir(parents=True, exist_ok=True)
    json_path = review / "summary.json"
    md_path = review / "summary.md"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    labels = SUMMARY_TEXT[summary.get("language", "en")]
    lines = [f"# {labels['title']}", ""]
    for item in summary.get("outputs", []):
        lines.extend([
            f"## {item['title']}",
            f"- {labels['background']}: {item['background']}",
            f"- {labels['content']}: {item['content']}",
            f"- {labels['impact']}: {item['impact']}",
            f"- {labels['next']}: {item['next_plan']}",
            "",
        ])
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path
