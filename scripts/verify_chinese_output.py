from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    presentation = Path(sys.argv[1])
    text = presentation.read_text(encoding="utf-8")
    required = ("\u5de5\u4f5c\u603b\u7ed3", '<meta charset="utf-8">')
    missing = [token for token in required if token not in text]
    if missing:
        raise SystemExit(f"Missing expected UTF-8 content: {missing}")
    print(f"Chinese UTF-8 output verified: {presentation}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
