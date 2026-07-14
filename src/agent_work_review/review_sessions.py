from __future__ import annotations

import json
import re
import shutil
from datetime import date
from pathlib import Path

from .storage import atomic_write_json, utc_now


REVIEW_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,79}$")


def reviews_root(home: Path) -> Path:
    return home / "reviews"


def active_path(home: Path) -> Path:
    return home / "active-review.json"


def manifest_path(review_dir: Path) -> Path:
    return review_dir / "review.json"


def default_review_id(start: str, end: str, scenario: str) -> str:
    return f"{start}_to_{end}_{scenario}"


def validate_review_id(review_id: str) -> str:
    normalized = review_id.strip().lower().replace(" ", "-")
    if not REVIEW_ID_RE.fullmatch(normalized):
        raise ValueError("review_id must use 1-80 lowercase letters, digits, dots, underscores, or hyphens")
    return normalized


def start_review(
    home: Path,
    *,
    start: str,
    end: str,
    scenario: str,
    language: str,
    title: str,
    subtitle: str = "",
    review_id: str | None = None,
    activate: bool = True,
) -> tuple[Path, dict]:
    try:
        start_value = date.fromisoformat(start)
        end_value = date.fromisoformat(end)
    except ValueError as exc:
        raise ValueError("start and end must use YYYY-MM-DD") from exc
    if start_value > end_value:
        raise ValueError("start must not be after end")
    selected_id = validate_review_id(review_id or default_review_id(start, end, scenario))
    review_dir = reviews_root(home) / selected_id
    if review_dir.exists():
        raise FileExistsError(f"Review already exists: {selected_id}")
    now = utc_now()
    manifest = {
        "schema_version": "1.0",
        "review_id": selected_id,
        "time_range": {"start": start, "end": end},
        "review_mode": scenario,
        "language": language,
        "title": title,
        "subtitle": subtitle,
        "state": "collecting",
        "created_at": now,
        "updated_at": now,
    }
    review_dir.mkdir(parents=True, exist_ok=False)
    atomic_write_json(manifest_path(review_dir), manifest)
    if activate:
        set_active_review(home, selected_id)
    return review_dir, manifest


def read_manifest(review_dir: Path) -> dict:
    path = manifest_path(review_dir)
    if not path.is_file():
        raise FileNotFoundError(f"Missing review manifest: {path}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def update_manifest(review_dir: Path, **changes: object) -> dict:
    manifest = read_manifest(review_dir)
    manifest.update(changes)
    manifest["updated_at"] = utc_now()
    atomic_write_json(manifest_path(review_dir), manifest)
    return manifest


def set_active_review(home: Path, review_id: str) -> dict:
    selected_id = validate_review_id(review_id)
    review_dir = reviews_root(home) / selected_id
    if not manifest_path(review_dir).is_file():
        raise FileNotFoundError(f"Unknown review: {selected_id}")
    active = {"review_id": selected_id, "updated_at": utc_now()}
    atomic_write_json(active_path(home), active)
    return active


def get_active_review_id(home: Path) -> str | None:
    path = active_path(home)
    if not path.is_file():
        return None
    return str(json.loads(path.read_text(encoding="utf-8-sig")).get("review_id") or "") or None


def resolve_review(home: Path, review_id: str | None = None) -> tuple[Path, dict]:
    migrate_legacy_review(home)
    selected_value = review_id or get_active_review_id(home)
    if not selected_value:
        raise FileNotFoundError("No active review. Run work-review start or work-review use first.")
    selected_id = validate_review_id(selected_value)
    review_dir = reviews_root(home) / selected_id
    return review_dir, read_manifest(review_dir)


def list_reviews(home: Path) -> list[dict]:
    migrate_legacy_review(home)
    active_id = get_active_review_id(home)
    reviews = []
    for path in sorted(reviews_root(home).glob("*/review.json")):
        manifest = json.loads(path.read_text(encoding="utf-8-sig"))
        manifest["active"] = manifest.get("review_id") == active_id
        reviews.append(manifest)
    return reviews


def migrate_legacy_review(home: Path) -> str | None:
    marker = home / ".legacy-review-migrated"
    if marker.exists():
        return None
    legacy_review = home / "review"
    legacy_output = home / "output"
    legacy_files = [path for path in [legacy_review / "candidates.json", legacy_review / "summary.draft.json", legacy_review / "summary.json", legacy_review / "summary.md", legacy_output / "presentation.html"] if path.is_file()]
    if not legacy_files:
        marker.touch()
        return None

    review_id = "legacy-import"
    suffix = 1
    while (reviews_root(home) / review_id).exists():
        suffix += 1
        review_id = f"legacy-import-{suffix}"
    review_dir = reviews_root(home) / review_id
    review_dir.mkdir(parents=True, exist_ok=False)
    for source in legacy_files:
        destination_name = "presentation.html" if source.name == "presentation.html" else source.name
        shutil.copy2(source, review_dir / destination_name)

    summary = {}
    candidates = {}
    if (review_dir / "summary.json").is_file():
        summary = json.loads((review_dir / "summary.json").read_text(encoding="utf-8-sig"))
    if (review_dir / "candidates.json").is_file():
        candidates = json.loads((review_dir / "candidates.json").read_text(encoding="utf-8-sig"))
    now = utc_now()
    manifest = {
        "schema_version": "1.0",
        "review_id": review_id,
        "time_range": summary.get("time_range") or candidates.get("time_range") or {"start": None, "end": None},
        "review_mode": summary.get("review_mode") or "phase-review",
        "language": summary.get("language") or "en",
        "title": summary.get("title") or "Legacy imported review",
        "subtitle": summary.get("subtitle") or "",
        "state": "migrated",
        "created_at": now,
        "updated_at": now,
        "migrated_from": "v1.1-flat-layout",
    }
    atomic_write_json(manifest_path(review_dir), manifest)
    if not get_active_review_id(home):
        set_active_review(home, review_id)
    marker.touch()
    return review_id
