#!/usr/bin/env python3
"""Resolve a video source into a local file plus optional subtitles."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

VIDEO_SUFFIXES = {".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi", ".flv", ".wmv"}
SUB_LANGS = "en,en-US,en-GB,en-orig"


def is_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"}


def _first_existing(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def _find_video(directory: Path) -> Path | None:
    candidates = [p for p in directory.glob("source.*") if p.suffix.lower() in VIDEO_SUFFIXES]
    return sorted(candidates)[0] if candidates else None


def _find_subtitles(directory: Path) -> Path | None:
    subs = sorted(directory.glob("source*.vtt"))
    if not subs:
        return None
    english = [p for p in subs if any(tag in p.name for tag in (".en.", ".en-US.", ".en-GB.", ".en-orig."))]
    return english[0] if english else subs[0]


def resolve_local(source: str) -> dict:
    path = Path(source).expanduser().resolve()
    if not path.exists():
        raise SystemExit(f"Video file not found: {path}")
    if path.suffix.lower() not in VIDEO_SUFFIXES:
        print(f"[pi-watch-video] warning: unknown video suffix {path.suffix}; continuing", file=sys.stderr)
    return {
        "video": str(path),
        "subtitles": None,
        "metadata": {"title": path.name, "source": str(path)},
        "downloaded": False,
    }


def _config_value(name: str) -> str | None:
    if os.environ.get(name):
        return os.environ[name].strip()
    config_file = Path.home() / ".config" / "pi-watch-video" / ".env"
    if not config_file.exists():
        return None
    for line in config_file.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        if key.strip() == name and value.strip():
            return value.strip().strip('"\'')
    return None


def download_url(url: str, directory: Path) -> dict:
    if shutil.which("yt-dlp") is None:
        raise SystemExit("yt-dlp is missing. Run: python3 scripts/setup.py --doctor")

    directory.mkdir(parents=True, exist_ok=True)
    template = str(directory / "source.%(ext)s")
    command = [
        "yt-dlp",
        "--no-playlist",
        "--merge-output-format", "mp4",
        "-f", "bv*[height<=720]+ba/b[height<=720]/bv+ba/b",
        "--write-info-json",
        "--write-subs",
        "--write-auto-subs",
        "--sub-langs", SUB_LANGS,
        "--sub-format", "vtt",
        "--convert-subs", "vtt",
        "-o", template,
    ]
    cookies = _config_value("PI_WATCH_YTDLP_COOKIES") or _config_value("YTDLP_COOKIES")
    if cookies:
        command.extend(["--cookies", cookies])
    command.append(url)
    result = subprocess.run(command, stdout=sys.stderr, stderr=sys.stderr)
    video = _find_video(directory)
    if video is None:
        raise SystemExit(f"yt-dlp failed to create a video in {directory} (exit {result.returncode})")

    info = {}
    info_path = _first_existing([directory / "source.info.json"])
    if info_path:
        try:
            raw = json.loads(info_path.read_text(encoding="utf-8"))
            info = {
                "title": raw.get("title"),
                "uploader": raw.get("uploader") or raw.get("channel"),
                "duration": raw.get("duration"),
                "source": raw.get("webpage_url") or url,
            }
        except Exception as exc:  # metadata is useful but not required
            print(f"[pi-watch-video] could not parse info json: {exc}", file=sys.stderr)

    return {
        "video": str(video),
        "subtitles": str(_find_subtitles(directory)) if _find_subtitles(directory) else None,
        "metadata": info or {"source": url},
        "downloaded": True,
    }


def resolve_source(source: str, directory: Path) -> dict:
    return download_url(source, directory) if is_url(source) else resolve_local(source)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: media_source.py <url-or-file> <out-dir>")
    print(json.dumps(resolve_source(sys.argv[1], Path(sys.argv[2])), indent=2))
