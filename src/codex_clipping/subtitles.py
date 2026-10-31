"""Strict source-time subtitle formatting; this module never performs ASR."""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Iterable, Mapping


def _seconds(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a finite number of source seconds")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def validate_transcript_segments(
    segments: Iterable[Mapping[str, Any]], duration_seconds: float
) -> list[dict[str, Any]]:
    """Validate existing transcript text without inventing words or timestamps.

    Empty input is valid (no recognized speech), and produces an empty SRT.
    Out-of-order, overlapping, zero-length or out-of-source intervals fail closed.
    """
    duration = _seconds(duration_seconds, "duration_seconds")
    if duration <= 0:
        raise ValueError("source duration must be positive")
    result: list[dict[str, Any]] = []
    previous_end = 0.0
    ids: set[str] = set()
    for index, item in enumerate(segments):
        if not isinstance(item, Mapping):
            raise ValueError(f"segment {index} must be an object")
        start = _seconds(item.get("start"), f"segment {index} start")
        end = _seconds(item.get("end"), f"segment {index} end")
        if not 0 <= start < end <= duration:
            raise ValueError(f"segment {index} is outside the source timeline")
        if start < previous_end:
            raise ValueError(f"segment {index} overlaps or is out of order")
        if round(end * 1000) <= round(start * 1000):
            raise ValueError(f"segment {index} has no representable SRT duration")
        text = item.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"segment {index} has no recognized text")
        text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
        if "\n\n" in text:
            raise ValueError(f"segment {index} contains an SRT block separator")
        entry: dict[str, Any] = {"start": start, "end": end, "text": text}
        if "id" in item:
            identifier = item["id"]
            if not isinstance(identifier, str) or not identifier or identifier in ids:
                raise ValueError("transcript segment IDs must be nonempty and unique")
            ids.add(identifier)
            entry["id"] = identifier
        result.append(entry)
        previous_end = end
    return result


def _timestamp(seconds: float) -> str:
    milliseconds = round(seconds * 1000)
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    whole_seconds, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02}:{minutes:02}:{whole_seconds:02},{milliseconds:03}"


def render_srt(segments: Iterable[Mapping[str, Any]], duration_seconds: float) -> str:
    """Return UTF-8-compatible SRT text from supplied, validated ASR segments."""
    checked = validate_transcript_segments(segments, duration_seconds)
    blocks = [
        f"{index}\n{_timestamp(item['start'])} --> {_timestamp(item['end'])}\n{item['text']}"
        for index, item in enumerate(checked, 1)
    ]
    return "\n\n".join(blocks) + ("\n" if blocks else "")


def write_srt(
    path: str | Path, segments: Iterable[Mapping[str, Any]], duration_seconds: float
) -> Path:
    """Write a new subtitle file exclusively; an existing file is never replaced."""
    target = Path(path)
    text = render_srt(segments, duration_seconds)
    with target.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(text)
    return target
