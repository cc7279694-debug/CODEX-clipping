"""Conservative, reversible review decisions. No media editing is implemented."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import math
from pathlib import PurePosixPath, PureWindowsPath
import re
from typing import Any, Iterable, Mapping

from .subtitles import validate_transcript_segments

_HASH = re.compile(r"[0-9a-fA-F]{64}\Z")
_STATES = {"pending", "accepted", "rejected"}


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise ValueError(f"{label} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def _source(source: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(source, Mapping):
        raise ValueError("source must be an object")
    digest = source.get("sha256")
    if not isinstance(digest, str) or not _HASH.fullmatch(digest):
        raise ValueError("source.sha256 must contain a complete SHA-256 digest")
    duration = _number(source.get("duration_seconds"), "source duration")
    if duration <= 0:
        raise ValueError("source duration must be positive")
    result = deepcopy(dict(source))
    result["sha256"] = digest.lower()
    result["duration_seconds"] = duration
    if "relative_path" in result:
        path = result["relative_path"]
        if not isinstance(path, str) or not path:
            raise ValueError("source.relative_path must be a nonempty relative path")
        posix = PurePosixPath(path.replace("\\", "/"))
        windows = PureWindowsPath(path)
        if posix.is_absolute() or windows.is_absolute() or windows.drive or ".." in posix.parts:
            raise ValueError("source.relative_path must stay within its project")
    return result


def _intervals(items: Iterable[Mapping[str, Any]], duration: float, label: str) -> list[dict[str, Any]]:
    result = []
    for index, item in enumerate(items):
        if not isinstance(item, Mapping):
            raise ValueError(f"{label} interval must be an object")
        start = _number(item.get("start"), f"{label} start")
        end = _number(item.get("end"), f"{label} end")
        if not 0 <= start < end <= duration:
            raise ValueError(f"{label} interval {index} is outside the source")
        entry = deepcopy(dict(item))
        entry.update(start=start, end=end)
        result.append(entry)
    result.sort(key=lambda item: (item["start"], item["end"]))
    return result


def build_decisions(
    source: Mapping[str, Any],
    transcript_segments: Iterable[Mapping[str, Any]],
    silence_candidates: Iterable[Mapping[str, Any]],
    *,
    protected_intervals: Iterable[Mapping[str, Any]] | None = None,
    asr: Mapping[str, Any] | None = None,
    min_silence_seconds: float = 2.0,
    padding_seconds: float = 0.35,
    min_suggestion_seconds: float = 0.5,
    speech_evidence_complete: bool = False,
) -> dict[str, Any]:
    """Build review-only suggestions in source seconds, with strict safety gates.

    ``speech_evidence_complete`` is an explicit upstream evidence assertion, not
    something inferred from a lack of ASR words. Leave it false if quiet speech,
    laughter or natural pauses have not been independently protected. Even when
    true, suggestions remain pending and can never execute a media operation.
    Overlaps with protected speech/laughter/pauses are excluded, not shortened or
    guessed around. Padding retains context at both ends of each low-level gap.
    """
    checked_source = _source(source)
    duration = checked_source["duration_seconds"]
    transcript = validate_transcript_segments(transcript_segments, duration)
    candidates = _intervals(silence_candidates, duration, "silence")
    for previous, current in zip(candidates, candidates[1:]):
        if current["start"] < previous["end"]:
            raise ValueError("overlapping silence candidates require explicit review")
    protected = _intervals(protected_intervals or [], duration, "protected")
    minimum = _number(min_silence_seconds, "min_silence_seconds")
    padding = _number(padding_seconds, "padding_seconds")
    min_suggestion = _number(min_suggestion_seconds, "min_suggestion_seconds")
    if minimum <= 0 or padding < 0 or min_suggestion <= 0:
        raise ValueError("invalid suggestion policy")
    if not isinstance(speech_evidence_complete, bool):
        raise ValueError("speech_evidence_complete must be a boolean")
    exclusions: list[dict[str, Any]] = []
    suggestions: list[dict[str, Any]] = []
    for index, candidate in enumerate(candidates, 1):
        start, end = candidate["start"], candidate["end"]
        reason = None
        if not speech_evidence_complete:
            reason = "speech_protection_evidence_incomplete"
        elif not transcript:
            reason = "no_recognized_speech_not_proof_of_silence"
        elif end - start < minimum or end - start - 2 * padding < min_suggestion:
            reason = "retain_short_or_natural_pause"
        elif any(start < min(duration, item["end"] + padding) and end > max(0, item["start"] - padding)
                 for item in transcript + protected):
            reason = "overlaps_protected_speech_laughter_or_pause"
        if reason:
            exclusions.append({"candidate_index": index, "start": start, "end": end, "reason": reason})
            continue
        suggestions.append({
            "id": f"cut-{index:04d}",
            "start": round(start + padding, 6),
            "end": round(end - padding, 6),
            "reason": "long_low_level_interval",
            "risk": "manual_review_required_not_verified_meaningless",
            "status": "pending",
        })
    document = {
        "schema_version": 1,
        "source": checked_source,
        "time_base": "source_seconds",
        "asr": deepcopy(dict(asr or {})),
        "transcript_segments": transcript,
        "suggestions": suggestions,
        "review_history": [],
        "excluded_candidates": exclusions,
        "policy": {
            "status": "PROPOSED",
            "min_silence_seconds": minimum,
            "padding_seconds": padding,
            "min_suggestion_seconds": min_suggestion,
            "speech_evidence_complete": speech_evidence_complete,
        },
        "execution_enabled": False,
    }
    validate_decisions(document)
    return document


def _replay(document: Mapping[str, Any]) -> tuple[dict[str, str], dict[str, list[dict[str, Any]]]]:
    source = _source(document.get("source"))
    if type(document.get("schema_version")) is not int or document.get("schema_version") != 1 or document.get("time_base") != "source_seconds":
        raise ValueError("unsupported decision schema or time base")
    if document.get("execution_enabled") is not False:
        raise ValueError("decision documents cannot enable media execution")
    transcript = document.get("transcript_segments")
    if not isinstance(transcript, list):
        raise ValueError("transcript_segments must be a list")
    validate_transcript_segments(transcript, source["duration_seconds"])
    suggestions = document.get("suggestions")
    if not isinstance(suggestions, list):
        raise ValueError("suggestions must be a list")
    states: dict[str, str] = {}
    stacks: dict[str, list[dict[str, Any]]] = {}
    previous_end = 0.0
    for suggestion in suggestions:
        if not isinstance(suggestion, Mapping):
            raise ValueError("each suggestion must be an object")
        identifier = suggestion.get("id")
        if not isinstance(identifier, str) or not identifier or identifier in states:
            raise ValueError("suggestion IDs must be nonempty and unique")
        _intervals([suggestion], source["duration_seconds"], "suggestion")
        if suggestion["start"] < previous_end:
            raise ValueError("suggestions must be ordered and nonoverlapping")
        previous_end = suggestion["end"]
        if suggestion.get("status") not in _STATES:
            raise ValueError("invalid review status")
        states[identifier] = "pending"
        stacks[identifier] = []
    history = document.get("review_history")
    if not isinstance(history, list):
        raise ValueError("review_history must be a list")
    for sequence, event in enumerate(history, 1):
        if not isinstance(event, Mapping):
            raise ValueError("each review event must be an object")
        identifier = event.get("suggestion_id")
        if type(event.get("event_id")) is not int or event.get("event_id") != sequence or identifier not in states:
            raise ValueError("invalid review event order or suggestion ID")
        if event.get("source_sha256") != source["sha256"]:
            raise ValueError("review event is bound to a different source hash")
        if event.get("from_status") != states[identifier]:
            raise ValueError("review history has an invalid prior status")
        action = event.get("action")
        if action in ("accept", "reject"):
            expected = "accepted" if action == "accept" else "rejected"
            if states[identifier] == expected or "target_event_id" in event:
                raise ValueError("invalid or redundant review event")
            stacks[identifier].append(dict(event))
        elif action == "undo":
            if not stacks[identifier]:
                raise ValueError("no review action remains to undo")
            target = stacks[identifier].pop()
            if event.get("target_event_id") != target["event_id"]:
                raise ValueError("undo does not target the latest active action")
            expected = target["from_status"]
        else:
            raise ValueError("unsupported review action")
        if event.get("to_status") != expected:
            raise ValueError("review history has an invalid resulting status")
        states[identifier] = expected
    for suggestion in suggestions:
        if suggestion["status"] != states[suggestion["id"]]:
            raise ValueError("current status does not match append-only review history")
    return states, stacks


def validate_decisions(document: Mapping[str, Any]) -> None:
    """Reject malformed/tampered review state; does not validate media contents."""
    if not isinstance(document, Mapping):
        raise ValueError("decision document must be an object")
    _replay(document)


def review_decision(
    document: Mapping[str, Any], suggestion_id: str, action: str, *,
    source_sha256: str, note: str = "", timestamp: str | None = None,
) -> dict[str, Any]:
    """Return a new document after accept/reject/undo, preserving every event.

    Caller must supply the current source-file hash; it must match the document.
    This function only updates JSON state. It never accepts or opens media paths.
    """
    states, stacks = _replay(document)
    if not isinstance(source_sha256, str) or source_sha256.lower() != document["source"]["sha256"].lower():
        raise ValueError("source file hash mismatch")
    if suggestion_id not in states or action not in ("accept", "reject", "undo"):
        raise ValueError("unknown suggestion or review action")
    if not isinstance(note, str):
        raise ValueError("review note must be text")
    event = {
        "event_id": len(document["review_history"]) + 1,
        "suggestion_id": suggestion_id,
        "source_sha256": source_sha256.lower(),
        "action": action,
        "from_status": states[suggestion_id],
        "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
        "note": note,
    }
    if action == "undo":
        if not stacks[suggestion_id]:
            raise ValueError("no review action remains to undo")
        target = stacks[suggestion_id][-1]
        event["target_event_id"] = target["event_id"]
        event["to_status"] = target["from_status"]
    else:
        event["to_status"] = "accepted" if action == "accept" else "rejected"
        if event["to_status"] == event["from_status"]:
            raise ValueError("review action would not change the status")
    result = deepcopy(dict(document))
    result["review_history"].append(event)
    for suggestion in result["suggestions"]:
        if suggestion["id"] == suggestion_id:
            suggestion["status"] = event["to_status"]
    validate_decisions(result)
    return result
