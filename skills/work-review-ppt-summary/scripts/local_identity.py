from __future__ import annotations

import json
import uuid
from pathlib import Path


def find_config(path_hint: str | Path) -> Path | None:
    path = Path(path_hint).expanduser().resolve()
    current = path.parent if path.suffix else path
    for candidate_root in (current, *current.parents):
        candidate = candidate_root / "config.json"
        if candidate.is_file():
            return candidate
    return None


def read_person_id(config_path: Path) -> str:
    config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    person_id = str(config.get("person_id") or "").strip()
    if not person_id:
        raise SystemExit(f"Missing person_id in local config: {config_path}")
    return person_id


def resolve_person_id(explicit: str | None, path_hint: str | Path) -> str:
    if explicit and explicit.strip():
        return explicit.strip()
    config_path = find_config(path_hint)
    if config_path:
        return read_person_id(config_path)
    raise SystemExit(
        "No local identity found. Run init_local_review.py first, or pass --person-id explicitly."
    )


def initialize_person_id(root: Path, explicit: str | None = None) -> str:
    config_path = root / "config.json"
    if config_path.is_file():
        existing = read_person_id(config_path)
        if explicit and explicit.strip() != existing:
            raise SystemExit(
                f"Local workspace already belongs to {existing}; refusing to replace it with {explicit.strip()}."
            )
        return existing
    return explicit.strip() if explicit and explicit.strip() else f"local-{uuid.uuid4().hex[:12]}"
