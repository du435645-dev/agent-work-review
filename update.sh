#!/bin/sh
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ -d "$repo/.git" ]; then
  test -z "$(git -C "$repo" status --porcelain)" || { echo "The checkout has local changes." >&2; exit 1; }
  git -C "$repo" pull --ff-only
fi
python3 "$repo/install.py" "$@"
