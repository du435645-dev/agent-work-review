from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

from local_identity import resolve_person_id


DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
ARTIFACT_RE = re.compile(
    r"([A-Za-z]:\\[^\s]+|(?:Reports|project|SQL|Scripts)\\[^\s]+?\.(?:md|html|sql|py|pptx?|json|xlsx?))"
)


@dataclass
class Candidate:
    session_id: str
    title: str
    cwd: str
    started_at: str
    signals: list[str]
    impact_level: str
    impact_score: int
    reason: str
    artifact_paths: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect session candidates for work-review recaps.")
    parser.add_argument("--sessions-root", default=str(Path.home() / ".codex" / "sessions"))
    parser.add_argument("--preset", default="last30d")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--now")
    parser.add_argument("--person-id", help="Optional override; otherwise read from the local review config.")
    parser.add_argument("--agent-type", default="codex")
    parser.add_argument("--device-id", default="local")
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def utc_now(now_text: str | None) -> date:
    if now_text:
        return date.fromisoformat(now_text)
    return datetime.now(timezone.utc).date()


def resolve_range(args: argparse.Namespace) -> tuple[str, date, date]:
    if args.start and args.end:
        return "custom", date.fromisoformat(args.start), date.fromisoformat(args.end)

    today = utc_now(args.now)
    presets = {
        "last7d": 6,
        "last14d": 13,
        "last30d": 29,
        "last90d": 89,
    }
    if args.preset not in presets:
        raise SystemExit(f"Unsupported preset: {args.preset}")
    delta = presets[args.preset]
    return args.preset, today - timedelta(days=delta), today


def iter_session_files(root: Path, start: date, end: date) -> Iterable[Path]:
    for path in root.rglob("*.jsonl"):
        parts = path.parts
        try:
            year = int(parts[-4])
            month = int(parts[-3])
            day = int(parts[-2])
            current = date(year, month, day)
        except (ValueError, IndexError):
            continue
        if start <= current <= end:
            yield path


def collect_candidate(path: Path) -> Candidate | None:
    session_id = ""
    cwd = ""
    started_at = ""
    text_parts: list[str] = []
    signals: list[str] = []
    artifact_paths: list[str] = []

    bad_lines = 0
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not raw_line.strip():
            continue
        try:
            record = json.loads(raw_line)
        except json.JSONDecodeError:
            bad_lines += 1
            continue
        record_type = record.get("type", "")
        payload = record.get("payload", {})
        if record_type == "session_meta":
            session_id = payload.get("session_id") or payload.get("id") or path.stem
            cwd = payload.get("cwd", "")
            started_at = payload.get("timestamp", record.get("timestamp", ""))
        elif record_type == "response_item":
            item_type = payload.get("type")
            if item_type == "function_call":
                name = payload.get("name", "")
                if name:
                    signals.append(name)
                    text_parts.append(name)
            content_items = payload.get("content") or []
            for content in content_items:
                text = content.get("text")
                if text:
                    text_parts.append(text)
                    artifact_paths.extend(ARTIFACT_RE.findall(text))

    combined_text = " ".join(text_parts)
    has_output_signal = bool(set(signals) & {"apply_patch", "shell_command"}) or bool(artifact_paths)
    has_decision_signal = any(keyword in combined_text.lower() for keyword in ("decid", "recommended", "strategy", "keep", "split", "merge"))
    if not has_output_signal and not has_decision_signal:
        return None

    if has_output_signal:
        impact_level = "output"
        impact_score = 90 + min(len(artifact_paths), 5)
        reason = "Detected file-output or tool-execution signals."
    elif has_decision_signal:
        impact_level = "decision"
        impact_score = 70
        reason = "Detected explicit decision language without strong output signals."
    else:
        impact_level = "progress"
        impact_score = 50
        reason = "Detected progress activity."

    if bad_lines:
        reason = f"{reason} Skipped {bad_lines} malformed log line(s)."

    title = path.stem
    if artifact_paths:
        title = Path(artifact_paths[0]).stem

    signal_set = sorted(set(signals))
    return Candidate(
        session_id=session_id or path.stem,
        title=title,
        cwd=cwd or "unknown",
        started_at=started_at,
        signals=signal_set,
        impact_level=impact_level,
        impact_score=impact_score,
        reason=reason,
        artifact_paths=sorted(set(artifact_paths)),
    )


def workspace_sort_key(item: Candidate) -> tuple[int, str]:
    level_order = {"output": 0, "decision": 1, "progress": 2}
    return (level_order.get(item.impact_level, 9), item.started_at)


def main() -> int:
    args = parse_args()
    args.person_id = resolve_person_id(args.person_id, args.output)
    label, start, end = resolve_range(args)
    root = Path(args.sessions_root)
    grouped: dict[str, list[Candidate]] = defaultdict(list)

    for session_file in iter_session_files(root, start, end):
        candidate = collect_candidate(session_file)
        if candidate is None:
            continue
        grouped[candidate.cwd].append(candidate)

    workspaces = []
    for cwd in sorted(grouped):
        items = sorted(grouped[cwd], key=workspace_sort_key)
        workspaces.append(
            {
                "workspace": cwd,
                "candidates": [
                    {
                        "session_id": item.session_id,
                        "person_id": args.person_id,
                        "agent_type": args.agent_type,
                        "device_id": args.device_id,
                        "title": item.title,
                        "cwd": item.cwd,
                        "started_at": item.started_at,
                        "signals": item.signals,
                        "impact_level": item.impact_level,
                        "impact_score": item.impact_score,
                        "reason": item.reason,
                        "artifact_paths": item.artifact_paths,
                        "source_refs": [],
                        "source_agents": [args.agent_type],
                        "source_session_ids": [item.session_id],
                    }
                    for item in items
                ],
            }
        )

    output = {
        "person_id": args.person_id,
        "storage_mode": "local-only",
        "source_agents": [args.agent_type],
        "time_range": {"label": label, "start": start.isoformat(), "end": end.isoformat()},
        "workspaces": workspaces,
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
