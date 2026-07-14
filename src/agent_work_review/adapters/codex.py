from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Iterable


ARTIFACT_RE = re.compile(r"([A-Za-z]:\\[^\s]+|(?:reports|project|src|scripts|docs|output)[\\/][^\s]+?\.(?:md|html|sql|py|js|ts|json|xlsx?|csv))", re.IGNORECASE)
MUTATING_TOOL_NAMES = {"apply_patch", "write_file", "create_file", "edit_file"}
MUTATING_CALL_RE = re.compile(r"apply_patch|write_file|create_file|edit_file|git\s+commit|gh\s+release\s+create|pip\s+install", re.IGNORECASE)
OUTPUT_WORDS = ("created", "implemented", "generated", "fixed", "published", "completed", "delivered", "\u5df2\u5b8c\u6210", "\u5b8c\u6210\u4e86", "\u65b0\u589e", "\u4fee\u590d", "\u751f\u6210", "\u53d1\u5e03", "\u4ea4\u4ed8")
DECISION_WORDS = ("decision", "decided", "conclusion", "selected", "chose", "\u51b3\u5b9a", "\u51b3\u7b56", "\u7ed3\u8bba", "\u9009\u62e9", "\u53d6\u820d")
RECOMMENDATION_WORDS = ("recommend", "strategy", "proposal", "\u5efa\u8bae", "\u7b56\u7565", "\u65b9\u6848")
ANALYSIS_WORDS = ("analyze", "analysis", "evaluate", "review the effect", "compare", "\u5206\u6790", "\u8bc4\u4f30", "\u590d\u76d8", "\u6548\u679c", "\u5bf9\u6bd4", "\u5f52\u56e0")
PROGRESS_WORDS = ("in progress", "partial", "next step", "\u8fdb\u884c\u4e2d", "\u9636\u6bb5\u8fdb\u5c55", "\u4e0b\u4e00\u6b65")
IMPACT_WORDS = ("%", "increase", "decrease", "reduced", "improved", "passed", "\u63d0\u5347", "\u4e0b\u964d", "\u964d\u4f4e", "\u6539\u5584", "\u901a\u8fc7", "\u6d41\u6c34", "\u8f6c\u5316")
NEGATIVE_RESULT_RE = re.compile(r"\bno\s+(?:reportable\s+)?(?:decision|delivery|change|output)|\bnot\s+(?:completed|implemented|delivered)|\u6ca1\u6709(?:\u5f62\u6210|\u5b8c\u6210|\u4ea7\u51fa|\u7ed3\u8bba)|\u672a(?:\u5b8c\u6210|\u843d\u5730|\u4ea7\u51fa)", re.IGNORECASE)


def iter_sessions(root: Path, start: date, end: date) -> Iterable[Path]:
    for path in root.rglob("*.jsonl"):
        try:
            current = date(int(path.parts[-4]), int(path.parts[-3]), int(path.parts[-2]))
        except (ValueError, IndexError):
            continue
        if start <= current <= end:
            yield path


def message_text(payload: dict) -> str:
    values = []
    for content in payload.get("content") or []:
        if isinstance(content, dict) and content.get("text"):
            values.append(str(content["text"]))
    return "\n".join(values).strip()


def title_from_request(request: str, fallback: str) -> str:
    for marker in ("## My request for Codex:", "## My request:"):
        if marker in request:
            request = request.rsplit(marker, 1)[1]
            break
    ignored_prefixes = ("files mentioned by the user", "referenced chats with codex", "my request for codex", "<image", "<developer", "<system")
    for line in request.splitlines():
        value = line.strip().lstrip("#").strip()
        if value and not value.startswith("<") and not value.casefold().startswith(ignored_prefixes):
            return value[:120]
    return fallback


def select_sentences(text: str, keywords: tuple[str, ...], limit: int = 800) -> str:
    sentences = re.split(r"(?<=[.!?\u3002\uff01\uff1f])\s+|\n+", text)
    selected = [sentence.strip() for sentence in sentences if sentence.strip() and any(keyword in sentence.casefold() for keyword in keywords)]
    return " ".join(selected)[:limit]


def tool_signal(payload: dict) -> tuple[str | None, bool]:
    name = str(payload.get("name") or "") or None
    raw_input = str(payload.get("arguments") or payload.get("input") or "")
    mutating = bool(name in MUTATING_TOOL_NAMES or MUTATING_CALL_RE.search(raw_input))
    return name, mutating


def build_candidate(
    *,
    path: Path,
    person_id: str,
    session_id: str,
    cwd: str,
    started_at: str,
    turn_index: int,
    request: str,
    final_text: str,
    signals: list[str],
    mutating: bool,
    bad_lines: int,
) -> dict | None:
    combined = f"{request}\n{final_text}"
    folded = combined.casefold()
    final_folded = final_text.casefold()
    artifacts = sorted(set(ARTIFACT_RE.findall(final_text)))
    has_output_language = any(word in final_folded for word in OUTPUT_WORDS)
    has_decision = any(word in final_folded for word in DECISION_WORDS)
    has_supported_recommendation = any(word in final_folded for word in RECOMMENDATION_WORDS) and bool(mutating or artifacts)
    has_progress = any(word in final_folded for word in PROGRESS_WORDS)
    has_impact = any(word in folded for word in IMPACT_WORDS) or bool(re.search(r"(?<!\w)\d+(?:\.\d+)?\s*(?:%|reports?|tests?|\u4efd|\u4e2a|\u6b21)", combined, re.IGNORECASE))
    has_analysis_result = has_impact and any(word in request.casefold() for word in ANALYSIS_WORDS)
    has_output = bool(mutating or artifacts) and has_output_language
    if NEGATIVE_RESULT_RE.search(final_text) and not mutating and not artifacts and not has_impact:
        return None
    if not has_output and not has_decision and not has_supported_recommendation and not has_analysis_result and not (has_progress and (signals or artifacts)):
        return None
    level = "output" if has_output else "decision" if has_decision or has_supported_recommendation or has_analysis_result else "progress"
    reason_parts = []
    if mutating:
        reason_parts.append("Detected a mutating tool call.")
    if artifacts:
        reason_parts.append("Detected delivered artifact references.")
    if has_decision:
        reason_parts.append("Detected explicit decision or conclusion language.")
    if has_supported_recommendation:
        reason_parts.append("Detected a recommendation backed by execution or artifacts.")
    if has_impact:
        reason_parts.append("Detected measurable impact evidence.")
    if bad_lines:
        reason_parts.append(f"Skipped {bad_lines} malformed line(s).")
    source_id = f"{session_id}:turn-{turn_index}"
    return {
        "schema_version": "1.0",
        "person_id": person_id,
        "agent_type": "codex",
        "device_id": "local",
        "session_id": source_id,
        "started_at": started_at,
        "workspace": cwd,
        "title": title_from_request(request, Path(artifacts[0]).stem if artifacts else source_id),
        "signals": sorted(set(signals)),
        "has_mutating_tool": mutating,
        "impact_level": level,
        "impact_score": (90 if level == "output" else 72 if level == "decision" else 52) + min(len(artifacts), 5) + (3 if has_impact else 0),
        "reason": " ".join(reason_parts) or "Detected reportable work.",
        "artifact_paths": artifacts,
        "source_refs": [f"{path.resolve()}#turn-{turn_index}"],
        "notes": final_text[:5000],
        "background": request[:1200],
        "impact": select_sentences(final_text, IMPACT_WORDS),
        "next_plan": select_sentences(final_text, ("next", "follow-up", "\u4e0b\u4e00\u6b65", "\u540e\u7eed", "\u8ba1\u5212"), 600),
    }


def parse_session(path: Path, person_id: str) -> list[dict]:
    session_id = path.stem
    cwd = "unknown"
    session_started_at = ""
    bad_lines = 0
    records = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            bad_lines += 1
            continue
        payload = record.get("payload") or {}
        if record.get("type") == "session_meta":
            session_id = str(payload.get("session_id") or payload.get("id") or session_id)
            cwd = str(payload.get("cwd") or cwd)
            session_started_at = str(payload.get("timestamp") or record.get("timestamp") or session_started_at)
        if record.get("type") == "response_item":
            records.append((record, payload))

    candidates = []
    request = ""
    started_at = session_started_at
    assistant_parts: list[str] = []
    signals: list[str] = []
    mutating = False
    turn_index = 0

    def flush_turn(final_text: str) -> None:
        nonlocal assistant_parts, signals, mutating, turn_index
        if not request or not final_text.strip():
            assistant_parts = []
            signals = []
            mutating = False
            return
        turn_index += 1
        candidate = build_candidate(
            path=path,
            person_id=person_id,
            session_id=session_id,
            cwd=cwd,
            started_at=started_at,
            turn_index=turn_index,
            request=request,
            final_text=final_text,
            signals=signals,
            mutating=mutating,
            bad_lines=bad_lines,
        )
        if candidate:
            candidates.append(candidate)
        assistant_parts = []
        signals = []
        mutating = False

    for record, payload in records:
        payload_type = payload.get("type")
        if payload_type == "message" and payload.get("role") == "user":
            if assistant_parts:
                flush_turn(assistant_parts[-1])
            request = message_text(payload) or request
            started_at = str(record.get("timestamp") or started_at)
            assistant_parts = []
            signals = []
            mutating = False
            continue
        if payload_type in {"function_call", "custom_tool_call"}:
            name, is_mutating = tool_signal(payload)
            if name:
                signals.append(name)
            mutating = mutating or is_mutating
            continue
        if payload_type != "message" or payload.get("role") != "assistant":
            continue
        text = message_text(payload)
        if text:
            assistant_parts.append(text)
        if payload.get("phase") not in {"final", "final_answer"}:
            continue
        flush_turn(text or assistant_parts[-1])
    if assistant_parts:
        flush_turn(assistant_parts[-1])
    return candidates


def collect_codex(root: Path, *, start: date, end: date, person_id: str) -> list[dict]:
    records = []
    for path in iter_sessions(root, start, end):
        records.extend(parse_session(path, person_id))
    return records
