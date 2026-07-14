from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ARTIFACT_RE = re.compile(
    r"([A-Za-z]:\\[^\s]+|(?:reports|project|src|scripts|docs|output)[\\/][^\s]+?\.(?:md|html|sql|py|js|ts|json|xlsx?|csv))",
    re.IGNORECASE,
)


def iter_files(path: Path) -> Iterable[Path]:
    if path.is_file():
        yield path
        return
    for child in sorted(path.rglob("*")):
        if child.is_file() and child.suffix.lower() in {".json", ".jsonl", ".md", ".txt"}:
            yield child


def normalize(raw: dict[str, Any], *, agent: str, person_id: str, source: Path, index: int, workspace: str | None) -> dict:
    session_id = str(raw.get("session_id") or raw.get("id") or f"{agent}:{source.stem}:{index}")
    level = str(raw.get("impact_level") or "progress")
    if level not in {"output", "decision", "progress"}:
        level = "progress"
    return {
        "schema_version": "1.0",
        "person_id": person_id,
        "agent_type": agent,
        "device_id": str(raw.get("device_id") or "local"),
        "session_id": session_id,
        "started_at": str(
            raw.get("started_at")
            or raw.get("timestamp")
            or datetime.fromtimestamp(source.stat().st_mtime, tz=timezone.utc).isoformat()
        ),
        "workspace": str(raw.get("workspace") or raw.get("cwd") or workspace or source.parent),
        "title": str(raw.get("title") or source.stem),
        "signals": sorted(set(raw.get("signals") or [])),
        "has_mutating_tool": bool(raw.get("has_mutating_tool", False)),
        "impact_level": level,
        "impact_score": int(raw.get("impact_score") or {"output": 90, "decision": 70, "progress": 50}[level]),
        "reason": str(raw.get("reason") or f"Imported from {agent}."),
        "artifact_paths": sorted(set(raw.get("artifact_paths") or raw.get("artifacts") or [])),
        "source_refs": sorted(set([*raw.get("source_refs", []), str(source.resolve())])),
        "notes": str(raw.get("notes") or raw.get("content") or ""),
        "background": str(raw.get("background") or ""),
        "impact": str(raw.get("impact") or ""),
        "next_plan": str(raw.get("next_plan") or ""),
    }


def parse_file(path: Path, *, agent: str, person_id: str, workspace: str | None) -> list[dict]:
    if path.suffix.lower() == ".jsonl":
        rows = []
        for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return [normalize(row, agent=agent, person_id=person_id, source=path, index=i, workspace=workspace) for i, row in enumerate(rows)]
    if path.suffix.lower() == ".json":
        document = json.loads(path.read_text(encoding="utf-8-sig"))
        if isinstance(document, dict) and "workspaces" in document:
            rows = []
            for group in document.get("workspaces", []):
                for item in group.get("candidates", []):
                    row = dict(item)
                    row.setdefault("workspace", group.get("workspace"))
                    rows.append(row)
        else:
            rows = document if isinstance(document, list) else [document]
        return [normalize(row, agent=agent, person_id=person_id, source=path, index=i, workspace=workspace) for i, row in enumerate(rows)]

    text = path.read_text(encoding="utf-8-sig", errors="replace")
    title = next((line.lstrip("# ").strip() for line in text.splitlines() if line.startswith("#")), path.stem)
    artifacts = sorted(set(ARTIFACT_RE.findall(text)))
    level = "output" if artifacts else "decision" if any(word in text.lower() for word in ("decision", "decided", "\u51b3\u5b9a", "\u7ed3\u8bba")) else "progress"
    return [
        normalize(
            {
                "title": title,
                "notes": text.strip(),
                "artifact_paths": artifacts,
                "impact_level": level,
            },
            agent=agent,
            person_id=person_id,
            source=path,
            index=0,
            workspace=workspace,
        )
    ]


def import_evidence(path: Path, *, agent: str, person_id: str, workspace: str | None = None) -> list[dict]:
    records: list[dict] = []
    for source in iter_files(path):
        records.extend(parse_file(source, agent=agent, person_id=person_id, workspace=workspace))
    return records
