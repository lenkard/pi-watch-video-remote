#!/usr/bin/env python3
"""Caption parsing and transcript formatting."""
from __future__ import annotations

import re
import sys
from pathlib import Path

CUE_RE = re.compile(r"(\d{2}):(\d{2}):(\d{2})[.,](\d{3})\s+-->\s+(\d{2}):(\d{2}):(\d{2})[.,](\d{3})")
HTML_RE = re.compile(r"<[^>]+>")


def _seconds(h: str, m: str, s: str, ms: str) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def _clean(text: str) -> str:
    return HTML_RE.sub("", text).replace("&nbsp;", " ").strip()


def collapse_duplicates(items: list[dict]) -> list[dict]:
    output: list[dict] = []
    for item in items:
        if output and item["text"] == output[-1]["text"]:
            output[-1]["end"] = item["end"]
            continue
        if output and item["text"].startswith(output[-1]["text"] + " "):
            output[-1].update(text=item["text"], end=item["end"])
            continue
        output.append(item)
    return output


def read_vtt(path: str) -> list[dict]:
    lines = Path(path).read_text(encoding="utf-8", errors="ignore").splitlines()
    items: list[dict] = []
    i = 0
    while i < len(lines):
        match = CUE_RE.match(lines[i])
        if not match:
            i += 1
            continue
        start = _seconds(*match.groups()[:4])
        end = _seconds(*match.groups()[4:])
        i += 1
        cue: list[str] = []
        while i < len(lines) and lines[i].strip():
            value = _clean(lines[i])
            if value:
                cue.append(value)
            i += 1
        text = " ".join(cue).strip()
        if text:
            items.append({"start": round(start, 2), "end": round(end, 2), "text": text})
        i += 1
    return collapse_duplicates(items)


def in_range(items: list[dict], start: float | None, end: float | None) -> list[dict]:
    lo = start if start is not None else float("-inf")
    hi = end if end is not None else float("inf")
    return [item for item in items if item["end"] >= lo and item["start"] <= hi]


def format_lines(items: list[dict]) -> str:
    lines = []
    for item in items:
        stamp = int(item["start"])
        lines.append(f"[{stamp // 60:02d}:{stamp % 60:02d}] {item['text']}")
    return "\n".join(lines)


def _srt_time(value: float) -> str:
    total_ms = max(0, int(round(value * 1000)))
    hours, rem = divmod(total_ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    seconds, ms = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{ms:03d}"


def format_srt(items: list[dict]) -> str:
    blocks = []
    for index, item in enumerate(items, 1):
        start = _srt_time(float(item.get("start") or 0.0))
        end_value = float(item.get("end") or item.get("start") or 0.0)
        if end_value <= float(item.get("start") or 0.0):
            end_value = float(item.get("start") or 0.0) + 1.0
        end = _srt_time(end_value)
        blocks.append(f"{index}\n{start} --> {end}\n{item['text']}")
    return "\n\n".join(blocks) + ("\n" if blocks else "")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: transcript.py <captions.vtt>")
    print(format_lines(read_vtt(sys.argv[1])))
