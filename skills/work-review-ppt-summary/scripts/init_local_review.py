from __future__ import annotations

import argparse
import json
from pathlib import Path


AGENT_DIRS = ("codex", "opencode", "hermes", "workbuddy", "manual")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize a local, private work-review workspace.")
    parser.add_argument("--root", required=True)
    parser.add_argument("--person-id", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root)
    for agent in AGENT_DIRS:
        (root / "inbox" / agent).mkdir(parents=True, exist_ok=True)
    (root / "review").mkdir(parents=True, exist_ok=True)
    (root / "output").mkdir(parents=True, exist_ok=True)

    config_path = root / "config.json"
    config = {
        "person_id": args.person_id,
        "storage_mode": "local-only",
        "agent_sources": list(AGENT_DIRS),
    }
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
