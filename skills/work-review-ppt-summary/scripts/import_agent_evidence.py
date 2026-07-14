from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from local_identity import resolve_person_id


ARTIFACT_RE = re.compile(
    r"([A-Za-z]:\\[^\s]+|(?:Reports|project|SQL|Scripts)[\\/][^\s]+?\.(?:md|html|sql|py|pptx?|json|xlsx?))"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import an Agent export into the local work-evidence format.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--agent-type", required=True)
    parser.add_argument("--person-id", help="Optional override; otherwise read from the local review config.")
    parser.add_argument("--workspace")
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def iter_files(path: Path) -> Iterable[Path]:
    if path.is_file():
        yield path
        return
    for child in sorted(path.rglob("*")):
        if child.is_file() and child.suffix.lower() in {".json", ".jsonl", ".md", ".txt"}:
            yield child


def base_evidence(args: argparse.Namespace, path: Path) -> dict[str, Any]:
    return {
        "person_id": args.person_id,
        "agent_type": args.agent_type,
        "device_id": "local",
        "session_id": f"{args.agent_type}:{path.stem}",
        "started_at": datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat(),
        "workspace": args.workspace or str(path.parent),
        "title": path.stem,
        "signals": [],
        "impact_level": "progress",
        "impact_score": 50,
        "reason": f"Imported from {args.agent_type} export.",
        "artifact_paths": [],
        "source_refs": [str(path.resolve())],
        "notes": "",
    }


def normalize_item(raw: dict[str, Any], args: argparse.Namespace, path: Path, index: int) -> dict[str, Any]:
    item = base_evidence(args, path)
    item.update({key: value for key, value in raw.items() if value is not None})
    item["person_id"] = args.person_id
    item["agent_type"] = args.agent_type
    item["session_id"] = str(raw.get("session_id") or raw.get("id") or f"{args.agent_type}:{path.stem}:{index}")
    item["workspace"] = str(raw.get("workspace") or raw.get("cwd") or args.workspace or path.parent)
    item["title"] = str(raw.get("title") or path.stem)
    item["started_at"] = str(raw.get("started_at") or raw.get("timestamp") or item["started_at"])
    item["artifact_paths"] = sorted(set(raw.get("artifact_paths") or raw.get("artifacts") or []))
    item["source_refs"] = sorted(set([*item.get("source_refs", []), str(path.resolve())]))
    item["signals"] = sorted(set(raw.get("signals") or []))
    level = str(raw.get("impact_level") or "progress")
    item["impact_level"] = level if level in {"output", "decision", "progress"} else "progress"
    item["impact_score"] = int(raw.get("impact_score") or {"output": 90, "decision": 70, "progress": 50}[item["impact_level"]])
    return item


def from_candidate_document(doc: dict[str, Any], args: argparse.Namespace, path: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for workspace in doc.get("workspaces", []):
        for candidate in workspace.get("candidates", []):
            raw = dict(candidate)
            raw.setdefault("workspace", workspace.get("workspace"))
            items.append(normalize_item(raw, args, path, len(items)))
    return items


def parse_json_file(path: Path, args: argparse.Namespace) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".jsonl":
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
        return [normalize_item(row, args, path, index) for index, row in enumerate(rows)]

    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(doc, dict) and "workspaces" in doc:
        return from_candidate_document(doc, args, path)
    rows = doc if isinstance(doc, list) else [doc]
    return [normalize_item(row, args, path, index) for index, row in enumerate(rows)]


def parse_text_file(path: Path, args: argparse.Namespace) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    item = base_evidence(args, path)
    heading = next((line.lstrip("# ").strip() for line in text.splitlines() if line.startswith("#")), "")
    item["title"] = heading or path.stem
    item["notes"] = text.strip()
    item["artifact_paths"] = sorted(set(ARTIFACT_RE.findall(text)))
    if item["artifact_paths"]:
        item["impact_level"] = "output"
        item["impact_score"] = 90 + min(len(item["artifact_paths"]), 5)
        item["reason"] = f"Imported from {args.agent_type} export with artifact references."
    elif any(keyword in text.lower() for keyword in ("决定", "结论", "decision", "recommend")):
        item["impact_level"] = "decision"
        item["impact_score"] = 70
        item["reason"] = f"Imported from {args.agent_type} export with decision language."
    return [item]


def main() -> int:
    args = parse_args()
    args.person_id = resolve_person_id(args.person_id, args.output)
    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"Input does not exist: {input_path}")

    evidence: list[dict[str, Any]] = []
    for path in iter_files(input_path):
        if path.suffix.lower() in {".json", ".jsonl"}:
            evidence.extend(parse_json_file(path, args))
        else:
            evidence.extend(parse_text_file(path, args))

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in evidence),
        encoding="utf-8",
    )
    print(str(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
