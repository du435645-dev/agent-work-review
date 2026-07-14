from __future__ import annotations

import json
import os
import uuid
from pathlib import Path


AGENT_DIRS = ("codex", "generic", "manual")


def default_home() -> Path:
    configured = os.environ.get("WORK_REVIEW_HOME")
    return Path(configured).expanduser() if configured else Path.home() / ".work-review" / "data"


def initialize_home(root: Path, person_id: str | None = None) -> dict:
    root = root.expanduser().resolve()
    for agent in AGENT_DIRS:
        (root / "inbox" / agent).mkdir(parents=True, exist_ok=True)
    (root / "review").mkdir(parents=True, exist_ok=True)
    (root / "output").mkdir(parents=True, exist_ok=True)

    config_path = root / "config.json"
    if config_path.is_file():
        config = json.loads(config_path.read_text(encoding="utf-8-sig"))
        existing = str(config.get("person_id") or "").strip()
        if not existing:
            raise ValueError(f"Missing person_id in {config_path}")
        if person_id and person_id != existing:
            raise ValueError(f"Workspace already belongs to {existing}; refusing to replace its identity.")
        return config

    config = {
        "schema_version": "1.0",
        "person_id": person_id or f"local-{uuid.uuid4().hex[:12]}",
        "storage_mode": "local-only",
    }
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    return config


def load_config(root: Path) -> dict:
    config_path = root.expanduser().resolve() / "config.json"
    if not config_path.is_file():
        return initialize_home(root)
    return json.loads(config_path.read_text(encoding="utf-8-sig"))
