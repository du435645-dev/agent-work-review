from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from . import __version__
from .adapters import collect_codex, import_evidence
from .drafts import canonical_digest, current_state, draft_path, list_history, prepare_draft, preview_draft, read_json, restore_history, save_draft, validate_draft
from .identity import default_home, initialize_home
from .pipeline import append_jsonl, audit_candidates, merge_home, summarize_candidates, write_jsonl, write_summary
from .renderer import write_html
from .review_sessions import list_reviews, migrate_legacy_review, resolve_review, set_active_review, start_review, update_manifest


SCENARIOS = ["phase-review", "self-review", "formal-report"]


def parse_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def home_from(args: argparse.Namespace) -> Path:
    return Path(args.home).expanduser().resolve()


def add_review_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--review-id")


def resolve_cli_review(home: Path, review_id: str | None) -> tuple[Path, dict]:
    try:
        return resolve_review(home, review_id)
    except (FileNotFoundError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc


def review_period(manifest: dict) -> tuple[date, date]:
    period = manifest.get("time_range") or {}
    try:
        return date.fromisoformat(str(period["start"])), date.fromisoformat(str(period["end"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise SystemExit("The active review has no valid time range.") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="work-review", description="Local-first multi-agent work review and HTML presentation generator.")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--home", default=str(default_home()), help="Local data directory (default: ~/.work-review/data).")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="Initialize a private local workspace.")
    sub.add_parser("adapters", help="List built-in adapters.")

    start = sub.add_parser("start", help="Create and activate an isolated review workspace for one reporting range.")
    start.add_argument("--start", required=True)
    start.add_argument("--end", required=True)
    start.add_argument("--scenario", choices=SCENARIOS, default="phase-review")
    start.add_argument("--language", choices=["en", "zh"], default="en")
    start.add_argument("--title", default="Work Review")
    start.add_argument("--subtitle", default="")
    start.add_argument("--review-id")

    sub.add_parser("list-reviews", help="List all isolated local review workspaces.")
    use = sub.add_parser("use", help="Set the active review workspace.")
    use.add_argument("review_id")
    current = sub.add_parser("current", help="Inspect freshness, coverage, history, and output state.")
    add_review_argument(current)

    collect = sub.add_parser("collect", help="Collect evidence with a native adapter.")
    collect.add_argument("--source", choices=["codex"], required=True)
    collect.add_argument("--start")
    collect.add_argument("--end")
    collect.add_argument("--sessions-root", default=str(Path.home() / ".codex" / "sessions"))
    add_review_argument(collect)

    imported = sub.add_parser("import", help="Import Markdown, JSON, or JSONL from any Agent.")
    imported.add_argument("--agent", required=True)
    imported.add_argument("--input", required=True)
    imported.add_argument("--workspace")

    merge = sub.add_parser("merge", help="Merge shared evidence into the selected review range.")
    add_review_argument(merge)
    audit = sub.add_parser("audit-candidates", help="Audit whether selected candidates contain reportable context.")
    add_review_argument(audit)

    summarize = sub.add_parser("summarize", help="Create a quick unreviewed canonical summary for compatibility.")
    add_review_argument(summarize)

    prepare = sub.add_parser("prepare-draft", help="Create an evidence scaffold for the session Agent to rewrite and polish.")
    prepare.add_argument("--title")
    prepare.add_argument("--subtitle")
    prepare.add_argument("--force", action="store_true")
    add_review_argument(prepare)

    validate = sub.add_parser("validate-draft", help="Validate Agent narratives, candidate coverage, and evidence freshness.")
    validate.add_argument("--input")
    add_review_argument(validate)

    preview = sub.add_parser("preview-draft", help="Preview validation, coverage, and changes before saving.")
    preview.add_argument("--input")
    add_review_argument(preview)

    save = sub.add_parser("save-draft", help="Promote a validated draft to canonical summary.json and summary.md.")
    save.add_argument("--input")
    save.add_argument("--mode", choices=["error", "overwrite", "merge"], default="error")
    add_review_argument(save)

    render = sub.add_parser("render-html", help="Create a standalone HTML presentation from the canonical summary.")
    render.add_argument("--title")
    render.add_argument("--subtitle")
    render.add_argument("--input")
    render.add_argument("--output")
    render.add_argument("--allow-stale", action="store_true")
    add_review_argument(render)

    history = sub.add_parser("history", help="List backed-up canonical revisions.")
    add_review_argument(history)
    restore = sub.add_parser("restore", help="Restore a backed-up canonical revision.")
    restore.add_argument("revision_id")
    add_review_argument(restore)

    build = sub.add_parser("build", help="Create a quick unreviewed summary and HTML scaffold.")
    build.add_argument("--start")
    build.add_argument("--end")
    build.add_argument("--scenario", choices=SCENARIOS, default="phase-review")
    build.add_argument("--language", choices=["en", "zh"], default="en")
    build.add_argument("--title", default="Work Review")
    build.add_argument("--subtitle", default="")
    add_review_argument(build)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    home = home_from(args)
    config = initialize_home(home)
    migrate_legacy_review(home)
    person_id = config["person_id"]

    if args.command == "init":
        print(json.dumps({"home": str(home), **config, "reviews": len(list_reviews(home))}, ensure_ascii=False, indent=2))
        return 0
    if args.command == "adapters":
        print("codex\tnative local session adapter with completed-turn extraction")
        print("generic\tMarkdown/JSON/JSONL adapter for any Agent")
        return 0
    if args.command == "start":
        try:
            review_dir, manifest = start_review(home, start=args.start, end=args.end, scenario=args.scenario, language=args.language, title=args.title, subtitle=args.subtitle, review_id=args.review_id)
        except (FileExistsError, ValueError) as exc:
            raise SystemExit(str(exc)) from exc
        print(json.dumps({"review_id": manifest["review_id"], "review_dir": str(review_dir), "active": True}, ensure_ascii=False, indent=2))
        return 0
    if args.command == "list-reviews":
        print(json.dumps({"reviews": list_reviews(home)}, ensure_ascii=False, indent=2))
        return 0
    if args.command == "use":
        try:
            active = set_active_review(home, args.review_id)
        except (FileNotFoundError, ValueError) as exc:
            raise SystemExit(str(exc)) from exc
        print(json.dumps(active, ensure_ascii=False, indent=2))
        return 0
    if args.command == "current":
        review_dir, manifest = resolve_cli_review(home, args.review_id)
        print(json.dumps(current_state(review_dir, manifest), ensure_ascii=False, indent=2))
        return 0
    if args.command == "collect":
        if bool(args.start) != bool(args.end):
            raise SystemExit("Provide both --start and --end, or omit both to use the selected review range.")
        if args.start and args.end:
            try:
                start_value, end_value = date.fromisoformat(args.start), date.fromisoformat(args.end)
            except ValueError as exc:
                raise SystemExit("--start and --end must use YYYY-MM-DD") from exc
            if start_value > end_value:
                raise SystemExit("--start must not be after --end")
        else:
            _, manifest = resolve_cli_review(home, args.review_id)
            start_value, end_value = review_period(manifest)
        records = collect_codex(Path(args.sessions_root), start=start_value, end=end_value, person_id=person_id)
        output = home / "inbox" / "codex" / f"{start_value.isoformat()}_to_{end_value.isoformat()}.jsonl"
        write_jsonl(output, records)
        print(json.dumps({"records": len(records), "output": str(output)}, ensure_ascii=False))
        return 0
    if args.command == "import":
        records = import_evidence(Path(args.input), agent=args.agent, person_id=person_id, workspace=args.workspace)
        output = home / "inbox" / args.agent / "evidence.jsonl"
        append_jsonl(output, records)
        print(json.dumps({"records": len(records), "output": str(output)}, ensure_ascii=False))
        return 0

    review_id = getattr(args, "review_id", None)
    if args.command == "build":
        try:
            review_dir, manifest = resolve_review(home, review_id)
        except FileNotFoundError:
            if not args.start or not args.end:
                raise SystemExit("No active review. Provide --start and --end or run work-review start first.")
            review_dir, manifest = start_review(home, start=args.start, end=args.end, scenario=args.scenario, language=args.language, title=args.title, subtitle=args.subtitle, review_id=review_id)
        if args.start or args.end:
            if not args.start or not args.end:
                raise SystemExit("Provide both --start and --end when building with an explicit range.")
            requested_range = {"start": args.start, "end": args.end}
            if manifest.get("time_range") != requested_range:
                raise SystemExit(
                    "The selected review uses a different time range. Run work-review start "
                    "with a new --review-id instead of reusing it."
                )
    else:
        review_dir, manifest = resolve_cli_review(home, review_id)
    start_value, end_value = review_period(manifest)

    if args.command == "merge":
        result = merge_home(home, person_id=person_id, start=start_value, end=end_value, review_dir=review_dir)
        update_manifest(review_dir, state="reviewing", candidates_digest=result.get("candidates_digest"))
        print(json.dumps({"review_id": manifest["review_id"], "workspaces": len(result["workspaces"]), "candidates": len([item for group in result["workspaces"] for item in group.get("candidates", [])]), "output": str(review_dir / "candidates.json")}, ensure_ascii=False, indent=2))
        return 0
    if args.command == "audit-candidates":
        candidates_path = review_dir / "candidates.json"
        if not candidates_path.is_file():
            raise SystemExit("Missing candidates.json. Run merge first.")
        print(json.dumps(audit_candidates(read_json(candidates_path)), ensure_ascii=False, indent=2))
        return 0
    if args.command == "summarize":
        candidates = read_json(review_dir / "candidates.json")
        summary = summarize_candidates(candidates, scenario=manifest["review_mode"], language=manifest["language"])
        summary.update({"title": manifest["title"], "subtitle": manifest.get("subtitle", ""), "based_on_candidates_digest": candidates.get("candidates_digest")})
        paths = write_summary(review_dir, summary, review_dir=review_dir)
        update_manifest(review_dir, state="unreviewed-summary")
        print(json.dumps({"summary_json": str(paths[0]), "summary_markdown": str(paths[1])}, ensure_ascii=False))
        return 0
    if args.command == "prepare-draft":
        candidates_path = review_dir / "candidates.json"
        if not candidates_path.is_file():
            raise SystemExit("Missing candidates.json. Run merge after collecting or importing evidence.")
        try:
            output = prepare_draft(review_dir, read_json(candidates_path), scenario=manifest["review_mode"], language=manifest["language"], title=args.title or manifest["title"], subtitle=args.subtitle if args.subtitle is not None else manifest.get("subtitle", ""), force=args.force)
        except FileExistsError as exc:
            raise SystemExit(str(exc)) from exc
        update_manifest(review_dir, state="drafting", draft_digest=canonical_digest(read_json(output), "draft_digest"))
        print(str(output))
        return 0
    if args.command in {"validate-draft", "preview-draft", "save-draft"}:
        input_path = Path(args.input) if args.input else draft_path(review_dir)
        candidates_path = review_dir / "candidates.json"
        draft = read_json(input_path)
        candidates = read_json(candidates_path) if candidates_path.is_file() else {}
        if args.command == "validate-draft":
            errors = validate_draft(draft, candidates)
            print(json.dumps({"valid": not errors, "errors": errors, "draft": str(input_path)}, ensure_ascii=False, indent=2))
            return 1 if errors else 0
        if args.command == "preview-draft":
            result, output = preview_draft(review_dir, draft, candidates)
            result["preview_markdown"] = str(output)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 1 if result["errors"] else 0
        errors = validate_draft(draft, candidates)
        if errors:
            print(json.dumps({"valid": False, "errors": errors}, ensure_ascii=False, indent=2))
            return 1
        try:
            summary_json, summary_markdown, backup = save_draft(review_dir, draft, mode=args.mode, candidates=candidates)
        except (FileExistsError, ValueError) as exc:
            raise SystemExit(str(exc)) from exc
        summary = read_json(summary_json)
        update_manifest(review_dir, state="approved", draft_digest=canonical_digest(draft, "draft_digest"), summary_digest=summary.get("summary_digest"))
        print(json.dumps({"summary_json": str(summary_json), "summary_markdown": str(summary_markdown), "backup": str(backup) if backup else None, "verified": True}, ensure_ascii=False, indent=2))
        return 0
    if args.command == "render-html":
        input_path = Path(args.input) if args.input else review_dir / "summary.json"
        output_path = Path(args.output) if args.output else review_dir / "presentation.html"
        summary = read_json(input_path)
        candidates = read_json(review_dir / "candidates.json") if (review_dir / "candidates.json").is_file() else {}
        if not args.allow_stale and summary.get("based_on_candidates_digest") != candidates.get("candidates_digest"):
            raise SystemExit("Canonical summary is stale. Rebuild the draft or use --allow-stale explicitly.")
        write_html(summary, output_path, title=args.title or str(summary.get("title") or manifest["title"]), subtitle=args.subtitle if args.subtitle is not None else str(summary.get("subtitle") or ""))
        update_manifest(review_dir, state="rendered", presentation_summary_digest=summary.get("summary_digest"))
        print(str(output_path))
        return 0
    if args.command == "history":
        print(json.dumps({"review_id": manifest["review_id"], "revisions": list_history(review_dir)}, ensure_ascii=False, indent=2))
        return 0
    if args.command == "restore":
        restored = restore_history(review_dir, args.revision_id)
        update_manifest(review_dir, state="restored")
        print(json.dumps({"review_id": manifest["review_id"], "restored": restored}, ensure_ascii=False, indent=2))
        return 0
    if args.command == "build":
        candidates = merge_home(home, person_id=person_id, start=start_value, end=end_value, review_dir=review_dir)
        summary = summarize_candidates(candidates, scenario=manifest["review_mode"], language=manifest["language"])
        summary.update({"title": manifest["title"], "subtitle": manifest.get("subtitle", ""), "based_on_candidates_digest": candidates.get("candidates_digest")})
        summary_paths = write_summary(review_dir, summary, review_dir=review_dir)
        saved_summary = read_json(summary_paths[0])
        html_path = write_html(saved_summary, review_dir / "presentation.html", title=manifest["title"], subtitle=manifest.get("subtitle", ""))
        update_manifest(review_dir, state="unreviewed-rendered", candidates_digest=candidates.get("candidates_digest"), summary_digest=saved_summary.get("summary_digest"))
        print(json.dumps({"review_id": manifest["review_id"], "candidates": str(review_dir / "candidates.json"), "summary_json": str(summary_paths[0]), "summary_markdown": str(summary_paths[1]), "presentation_html": str(html_path)}, ensure_ascii=False, indent=2))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
