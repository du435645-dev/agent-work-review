from __future__ import annotations

import argparse
import json
from pathlib import Path

from local_identity import initialize_person_id


AGENT_DIRS = ("codex", "opencode", "hermes", "workbuddy", "manual")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize a local, private work-review workspace.")
    parser.add_argument("--root", required=True)
    parser.add_argument("--person-id", help="Optional stable identity override; defaults to an anonymous local ID.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root)
    person_id = initialize_person_id(root, args.person_id)
    for agent in AGENT_DIRS:
        (root / "inbox" / agent).mkdir(parents=True, exist_ok=True)
    (root / "review").mkdir(parents=True, exist_ok=True)
    (root / "output").mkdir(parents=True, exist_ok=True)

    config_path = root / "config.json"
    config = {
        "person_id": person_id,
        "storage_mode": "local-only",
        "agent_sources": list(AGENT_DIRS),
    }
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"root": str(root), "person_id": person_id}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
