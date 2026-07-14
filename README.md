# Agent Work Review

Local-first work evidence aggregation across AI agents, with reusable structured summaries and a standalone HTML presentation.

Agent Work Review does not depend on a specific Agent product. Codex has a native local-history adapter; every other Agent can participate through the versioned Markdown/JSON/JSONL evidence interface.

## What it produces

- `review.json`: isolated reporting range, workflow state, and content lineage
- `candidates.json`: completed-turn, deduplicated, reviewable work items
- `summary.draft.json`: working draft written and polished by the current session Agent
- `summary.json`: canonical machine-readable summary
- `summary.md`: canonical human-readable summary
- `presentation.html`: standalone HTML presentation

The structured summary is the source of truth. HTML is the only built-in presentation format. Users can transform the summary into any other report format with their own tools.

## Install

### Universal local installer

```bash
git clone https://github.com/du435645-dev/agent-work-review.git
cd agent-work-review
python install.py
```

The installer creates an isolated runtime under `~/.work-review`, initializes private local data, and installs the Codex Skill automatically when Codex is detected.

Platform wrappers are also available:

```powershell
.\install.ps1
```

```bash
./install.sh
```

### Python package

```bash
pipx install git+https://github.com/du435645-dev/agent-work-review.git
```

## Quick start

```bash
work-review init

# Create one isolated workspace per reporting request
work-review start --start 2026-01-01 --end 2026-06-30 --language en --title "2026 H1 Work Review" --review-id 2026-h1

# Native Codex history
work-review collect --source codex

# Export from any other Agent as Markdown, JSON, or JSONL
work-review import --agent my-agent --input ./agent-export.md

# Merge, audit, and prepare an Agent-writing scaffold
work-review merge
work-review audit-candidates
work-review prepare-draft

# The session Agent rewrites reviews/<review-id>/summary.draft.json, then validates and saves it
work-review validate-draft
work-review preview-draft
work-review save-draft --mode overwrite
work-review render-html
work-review current
```

Chinese output is supported directly:

```bash
work-review start --start 2026-01-01 --end 2026-06-30 --language zh --title "2026 H1 Work Review" --review-id 2026-h1-zh
```

Runtime source files are ASCII-safe and generated JSON, Markdown, and HTML files are explicitly written as UTF-8. This avoids mojibake when an Agent or Windows shell reads source files using a legacy local code page.

If the installer directory is not on `PATH`, run:

```bash
~/.work-review/bin/work-review current
```

## Multi-Agent model

"Multi-Agent" means work history may come from several Agent products. It does not require those Agents to run simultaneously or share credentials.

```text
Agent histories and exports
        -> adapters
        -> evidence.jsonl
        -> isolated review range
        -> completed-turn extraction and deterministic merge
        -> user candidate review
        -> session Agent drafting and polishing
        -> local draft validation and save
        -> summary.json / summary.md
        -> presentation.html
```

Built-in adapters:

- `codex`: reads local Codex JSONL archives and extracts completed user turns, final answers, artifacts, decisions, and measured outcomes
- `generic`: imports Markdown, JSON, or JSONL from any Agent

Third-party adapters should emit records conforming to [`schemas/work-evidence.schema.json`](schemas/work-evidence.schema.json).
Agent-authored drafts conform to [`schemas/work-summary.schema.json`](schemas/work-summary.schema.json).

Extraction is intentionally a recall layer. It captures completed turns and preserves evidence; the current session Agent applies the bundled value-judgment guide to keep, merge, or explicitly exclude candidates. This mirrors the Agent-owned writing model used by mature weekly-report workflows while adding cross-Agent provenance and coverage checks.

## Review workspaces and draft lifecycle

Each half-year, annual, quarterly, promotion, or custom-range request gets its own directory under `~/.work-review/data/reviews/<review-id>`. Use `list-reviews` and `use` to switch without overwriting another report.

The workflow follows the same responsibility split as mature weekly-report tooling: deterministic scripts manage state and evidence, while the current session Agent writes and polishes the report. `current` reports fresh or stale state; `validate-draft` requires every candidate to be included or explicitly excluded; `save-draft` backs up an existing canonical summary before overwrite or merge; `history` and `restore` provide recovery.

`work-review build` remains available as a quick unreviewed scaffold, but it is not the recommended final-report path.

## Local-first privacy

- No conversation, evidence, summary, or presentation is uploaded.
- Data is stored under `~/.work-review/data` by default.
- A random local identity prevents accidental cross-person merges without asking for a real name.
- Set `WORK_REVIEW_HOME` to use another private data directory.
- Existing v1.1 flat outputs are copied into a `legacy-import` review without deleting the originals.

## Agent integration

The CLI is the product core. Agent-specific Skills or prompts are thin wrappers around it.

- Codex Skill: [`skills/agent-work-review`](skills/agent-work-review)
- Any other Agent: run the CLI directly or emit the public evidence schema

## Development

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
```

CI runs on Windows, macOS, and Linux with Python 3.10 and 3.12.

## License

MIT. See [`LICENSE`](LICENSE).

Chinese documentation: [`README.zh-CN.md`](README.zh-CN.md).
