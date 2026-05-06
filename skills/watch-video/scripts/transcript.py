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


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: transcript.py <captions.vtt>")
    print(format_lines(read_vtt(sys.argv[1])))
