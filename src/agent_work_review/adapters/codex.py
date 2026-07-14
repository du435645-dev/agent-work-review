from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Iterable


ARTIFACT_RE = re.compile(r"([A-Za-z]:\\[^\s]+|(?:reports|project|src|scripts|docs)[\\/][^\s]+?\.(?:md|html|sql|py|js|ts|json|xlsx?))", re.IGNORECASE)


def iter_sessions(root: Path, start: date, end: date) -> Iterable[Path]:
    for path in root.rglob("*.jsonl"):
        try:
            current = date(int(path.parts[-4]), int(path.parts[-3]), int(path.parts[-2]))
        except (ValueError, IndexError):
            continue
        if start <= current <= end:
            yield path


def parse_session(path: Path, person_id: str) -> dict | None:
    session_id = path.stem
    cwd = "unknown"
    started_at = ""
    text_parts: list[str] = []
    signals: list[str] = []
    artifacts: list[str] = []
    bad_lines = 0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            bad_lines += 1
            continue
        payload = record.get("payload") or {}
        if record.get("type") == "session_meta":
            session_id = str(payload.get("session_id") or payload.get("id") or session_id)
            cwd = str(payload.get("cwd") or cwd)
            started_at = str(payload.get("timestamp") or record.get("timestamp") or started_at)
        if record.get("type") != "response_item":
            continue
        if payload.get("type") == "function_call" and payload.get("name"):
            signals.append(str(payload["name"]))
        for content in payload.get("content") or []:
            text = content.get("text") if isinstance(content, dict) else None
            if text:
                text_parts.append(text)
                artifacts.extend(ARTIFACT_RE.findall(text))

    combined = " ".join(text_parts)
    has_output = bool(set(signals) & {"apply_patch", "shell_command"}) or bool(artifacts)
    has_decision = any(word in combined.lower() for word in ("decision", "decided", "recommended", "strategy", "决定", "结论"))
    if not has_output and not has_decision:
        return None
    level = "output" if has_output else "decision"
    reason = "Detected tool execution or artifact references." if has_output else "Detected decision language."
    if bad_lines:
        reason += f" Skipped {bad_lines} malformed line(s)."
    return {
        "schema_version": "1.0",
        "person_id": person_id,
        "agent_type": "codex",
        "device_id": "local",
        "session_id": session_id,
        "started_at": started_at,
        "workspace": cwd,
        "title": Path(artifacts[0]).stem if artifacts else path.stem,
        "signals": sorted(set(signals)),
        "impact_level": level,
        "impact_score": 90 + min(len(set(artifacts)), 5) if has_output else 70,
        "reason": reason,
        "artifact_paths": sorted(set(artifacts)),
        "source_refs": [str(path.resolve())],
        "notes": "",
        "background": "",
        "impact": "",
        "next_plan": "",
    }


def collect_codex(root: Path, *, start: date, end: date, person_id: str) -> list[dict]:
    records = []
    for path in iter_sessions(root, start, end):
        record = parse_session(path, person_id)
        if record:
            records.append(record)
    return records
