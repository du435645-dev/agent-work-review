from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from . import __version__
from .adapters import collect_codex, import_evidence
from .drafts import current_state, draft_path, prepare_draft, read_json, save_draft, validate_draft
from .identity import default_home, initialize_home, load_config
from .pipeline import append_jsonl, merge_home, summarize_candidates, write_jsonl, write_summary
from .renderer import write_html


def parse_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def home_from(args: argparse.Namespace) -> Path:
    return Path(args.home).expanduser().resolve()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="work-review", description="Local-first multi-agent work review and HTML presentation generator.")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--home", default=str(default_home()), help="Local data directory (default: ~/.work-review/data).")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="Initialize a private local workspace.")
    sub.add_parser("adapters", help="List built-in adapters.")
    sub.add_parser("current", help="Inspect local candidates, draft, canonical summary, and presentation state.")

    collect = sub.add_parser("collect", help="Collect evidence with a native adapter.")
    collect.add_argument("--source", choices=["codex"], required=True)
    collect.add_argument("--start", required=True)
    collect.add_argument("--end", required=True)
    collect.add_argument("--sessions-root", default=str(Path.home() / ".codex" / "sessions"))

    imported = sub.add_parser("import", help="Import Markdown, JSON, or JSONL from any Agent.")
    imported.add_argument("--agent", required=True)
    imported.add_argument("--input", required=True)
    imported.add_argument("--workspace")

    merge = sub.add_parser("merge", help="Merge and deduplicate all local evidence.")
    merge.add_argument("--start")
    merge.add_argument("--end")

    summarize = sub.add_parser("summarize", help="Create summary.json and summary.md from reviewed candidates.")
    summarize.add_argument("--scenario", choices=["phase-review", "self-review", "formal-report"], default="phase-review")
    summarize.add_argument("--language", choices=["en", "zh"], default="en")

    prepare = sub.add_parser("prepare-draft", help="Create a draft scaffold for the session Agent to rewrite and polish.")
    prepare.add_argument("--scenario", choices=["phase-review", "self-review", "formal-report"], default="phase-review")
    prepare.add_argument("--language", choices=["en", "zh"], default="en")
    prepare.add_argument("--title", default="Work Review")
    prepare.add_argument("--subtitle", default="")
    prepare.add_argument("--force", action="store_true")

    validate = sub.add_parser("validate-draft", help="Validate an Agent-authored draft against reviewed candidates.")
    validate.add_argument("--input")

    save = sub.add_parser("save-draft", help="Promote a validated draft to canonical summary.json and summary.md.")
    save.add_argument("--input")
    save.add_argument("--mode", choices=["error", "overwrite", "merge"], default="error")

    render = sub.add_parser("render-html", help="Create a standalone HTML presentation from summary.json.")
    render.add_argument("--title", default="Work Review")
    render.add_argument("--subtitle", default="")
    render.add_argument("--input")
    render.add_argument("--output")

    build = sub.add_parser("build", help="Merge evidence, summarize it, and render the HTML presentation.")
    build.add_argument("--start")
    build.add_argument("--end")
    build.add_argument("--scenario", choices=["phase-review", "self-review", "formal-report"], default="phase-review")
    build.add_argument("--language", choices=["en", "zh"], default="en")
    build.add_argument("--title", default="Work Review")
    build.add_argument("--subtitle", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    home = home_from(args)
    config = initialize_home(home)
    person_id = config["person_id"]

    if args.command == "init":
        print(json.dumps({"home": str(home), **config}, ensure_ascii=False, indent=2))
        return 0
    if args.command == "adapters":
        print("codex\tnative local session adapter")
        print("generic\tMarkdown/JSON/JSONL adapter for any Agent")
        return 0
    if args.command == "current":
        print(json.dumps(current_state(home), ensure_ascii=False, indent=2))
        return 0
    if args.command == "collect":
        records = collect_codex(Path(args.sessions_root), start=date.fromisoformat(args.start), end=date.fromisoformat(args.end), person_id=person_id)
        output = home / "inbox" / "codex" / "evidence.jsonl"
        write_jsonl(output, records)
        print(json.dumps({"records": len(records), "output": str(output)}, ensure_ascii=False))
        return 0
    if args.command == "import":
        records = import_evidence(Path(args.input), agent=args.agent, person_id=person_id, workspace=args.workspace)
        output = home / "inbox" / args.agent / "evidence.jsonl"
        append_jsonl(output, records)
        print(json.dumps({"records": len(records), "output": str(output)}, ensure_ascii=False))
        return 0
    if args.command == "merge":
        result = merge_home(home, person_id=person_id, start=parse_date(args.start), end=parse_date(args.end))
        print(json.dumps({"workspaces": len(result["workspaces"]), "output": str(home / "review" / "candidates.json")}, ensure_ascii=False))
        return 0
    if args.command == "summarize":
        candidates_path = home / "review" / "candidates.json"
        candidates = json.loads(candidates_path.read_text(encoding="utf-8-sig"))
        summary = summarize_candidates(candidates, scenario=args.scenario, language=args.language)
        paths = write_summary(home, summary)
        print(json.dumps({"summary_json": str(paths[0]), "summary_markdown": str(paths[1])}, ensure_ascii=False))
        return 0
    if args.command == "prepare-draft":
        candidates_path = home / "review" / "candidates.json"
        if not candidates_path.is_file():
            raise SystemExit("Missing candidates.json. Run merge after collecting or importing evidence.")
        try:
            output = prepare_draft(
                home,
                read_json(candidates_path),
                scenario=args.scenario,
                language=args.language,
                title=args.title,
                subtitle=args.subtitle,
                force=args.force,
            )
        except FileExistsError as exc:
            raise SystemExit(str(exc)) from exc
        print(str(output))
        return 0
    if args.command == "validate-draft":
        input_path = Path(args.input) if args.input else draft_path(home)
        candidates_path = home / "review" / "candidates.json"
        errors = validate_draft(read_json(input_path), read_json(candidates_path) if candidates_path.is_file() else None)
        if errors:
            print(json.dumps({"valid": False, "errors": errors}, ensure_ascii=False, indent=2))
            return 1
        print(json.dumps({"valid": True, "draft": str(input_path)}, ensure_ascii=False, indent=2))
        return 0
    if args.command == "save-draft":
        input_path = Path(args.input) if args.input else draft_path(home)
        candidates_path = home / "review" / "candidates.json"
        draft = read_json(input_path)
        errors = validate_draft(draft, read_json(candidates_path) if candidates_path.is_file() else None)
        if errors:
            print(json.dumps({"valid": False, "errors": errors}, ensure_ascii=False, indent=2))
            return 1
        try:
            paths = save_draft(home, draft, mode=args.mode)
        except FileExistsError as exc:
            raise SystemExit(str(exc)) from exc
        print(json.dumps({"summary_json": str(paths[0]), "summary_markdown": str(paths[1])}, ensure_ascii=False, indent=2))
        return 0
    if args.command == "render-html":
        input_path = Path(args.input) if args.input else home / "review" / "summary.json"
        output_path = Path(args.output) if args.output else home / "output" / "presentation.html"
        summary = json.loads(input_path.read_text(encoding="utf-8-sig"))
        title = args.title if args.title != "Work Review" else str(summary.get("title") or args.title)
        subtitle = args.subtitle or str(summary.get("subtitle") or "")
        write_html(summary, output_path, title=title, subtitle=subtitle)
        print(str(output_path))
        return 0
    if args.command == "build":
        candidates = merge_home(home, person_id=person_id, start=parse_date(args.start), end=parse_date(args.end))
        summary = summarize_candidates(candidates, scenario=args.scenario, language=args.language)
        summary_paths = write_summary(home, summary)
        html_path = write_html(summary, home / "output" / "presentation.html", title=args.title, subtitle=args.subtitle)
        print(json.dumps({"candidates": str(home / "review" / "candidates.json"), "summary_json": str(summary_paths[0]), "summary_markdown": str(summary_paths[1]), "presentation_html": str(html_path)}, ensure_ascii=False, indent=2))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
