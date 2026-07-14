from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

from local_identity import resolve_person_id


LEVEL_ORDER = {"output": 0, "decision": 1, "progress": 2}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Merge local evidence from multiple Agents into review candidates.")
    parser.add_argument("--input", action="append", default=[])
    parser.add_argument("--input-dir")
    parser.add_argument("--person-id", help="Optional override; otherwise read from the local review config.")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def iter_input_files(args: argparse.Namespace) -> Iterable[Path]:
    seen: set[Path] = set()
    for value in args.input:
        path = Path(value).resolve()
        if path not in seen:
            seen.add(path)
            yield path
    if args.input_dir:
        for path in sorted(Path(args.input_dir).rglob("*")):
            if path.is_file() and path.suffix.lower() in {".json", ".jsonl"}:
                resolved = path.resolve()
                if resolved not in seen:
                    seen.add(resolved)
                    yield resolved


def flatten_candidate_doc(doc: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for workspace in doc.get("workspaces", []):
        for candidate in workspace.get("candidates", []):
            row = dict(candidate)
            row.setdefault("workspace", workspace.get("workspace"))
            row.setdefault("cwd", row.get("workspace", "unknown"))
            rows.append(row)
    return rows


def read_rows(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".jsonl":
        return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(doc, dict) and "workspaces" in doc:
        return flatten_candidate_doc(doc)
    return doc if isinstance(doc, list) else [doc]


def record_date(item: dict[str, Any]) -> date | None:
    text = str(item.get("started_at") or "")
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None


def merge_key(item: dict[str, Any]) -> tuple[str, ...]:
    workspace = str(item.get("workspace") or item.get("cwd") or "unknown").casefold()
    artifacts = sorted(str(path).replace("/", "\\").casefold() for path in item.get("artifact_paths", []))
    if artifacts:
        return ("artifact", workspace, artifacts[0])
    return (
        "source",
        str(item.get("agent_type") or "codex").casefold(),
        str(item.get("session_id") or item.get("title") or "unknown").casefold(),
    )


def merge_items(current: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    current_level = str(current.get("impact_level") or "progress")
    incoming_level = str(incoming.get("impact_level") or "progress")
    if LEVEL_ORDER.get(incoming_level, 9) < LEVEL_ORDER.get(current_level, 9):
        current["impact_level"] = incoming_level
    current["impact_score"] = max(int(current.get("impact_score") or 0), int(incoming.get("impact_score") or 0))
    for field in ("signals", "artifact_paths", "source_refs", "source_session_ids", "source_agents"):
        current[field] = sorted(set([*current.get(field, []), *incoming.get(field, [])]))
    notes = [value for value in (current.get("notes"), incoming.get("notes")) if value]
    current["notes"] = "\n\n".join(dict.fromkeys(notes))
    if len(str(incoming.get("title") or "")) > len(str(current.get("title") or "")):
        current["title"] = incoming["title"]
    current["reason"] = "Merged conservatively by shared artifact path or exact source identity."
    return current


def normalize(item: dict[str, Any], person_id: str) -> dict[str, Any]:
    agent = str(item.get("agent_type") or "codex")
    session_id = str(item.get("session_id") or item.get("id") or item.get("title") or "unknown")
    workspace = str(item.get("workspace") or item.get("cwd") or "unknown")
    return {
        **item,
        "person_id": person_id,
        "agent_type": agent,
        "session_id": session_id,
        "workspace": workspace,
        "cwd": workspace,
        "source_agents": sorted(set([*item.get("source_agents", []), agent])),
        "source_session_ids": sorted(set([*item.get("source_session_ids", []), session_id])),
        "source_refs": sorted(set(item.get("source_refs", []))),
        "artifact_paths": sorted(set(item.get("artifact_paths", []))),
        "signals": sorted(set(item.get("signals", []))),
    }


def main() -> int:
    args = parse_args()
    args.person_id = resolve_person_id(args.person_id, args.output)
    start = date.fromisoformat(args.start) if args.start else None
    end = date.fromisoformat(args.end) if args.end else None
    merged: dict[tuple[str, ...], dict[str, Any]] = {}

    for path in iter_input_files(args):
        for raw in read_rows(path):
            if raw.get("person_id") and raw["person_id"] != args.person_id:
                continue
            item = normalize(raw, args.person_id)
            item_date = record_date(item)
            if start and item_date and item_date < start:
                continue
            if end and item_date and item_date > end:
                continue
            key = merge_key(item)
            merged[key] = merge_items(merged[key], item) if key in merged else item

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in merged.values():
        grouped[item["workspace"]].append(item)

    workspaces = []
    for workspace in sorted(grouped):
        candidates = sorted(
            grouped[workspace],
            key=lambda item: (
                LEVEL_ORDER.get(str(item.get("impact_level")), 9),
                -int(item.get("impact_score") or 0),
                str(item.get("started_at") or ""),
            ),
        )
        workspaces.append({"workspace": workspace, "candidates": candidates})

    output = {
        "person_id": args.person_id,
        "storage_mode": "local-only",
        "time_range": {"label": "custom", "start": args.start, "end": args.end},
        "source_agents": sorted({agent for item in merged.values() for agent in item.get("source_agents", [])}),
        "workspaces": workspaces,
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
