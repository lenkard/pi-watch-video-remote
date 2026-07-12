#!/usr/bin/env python3
"""Resolve or stage media into a local bundle directory."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

from config import config_value

VIDEO_SUFFIXES = {".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi", ".flv", ".wmv"}
AUDIO_SUFFIXES = {".mp3", ".m4a", ".wav", ".aac", ".ogg", ".flac", ".opus"}
MEDIA_SUFFIXES = VIDEO_SUFFIXES | AUDIO_SUFFIXES
SUB_LANGS = "en,en-US,en-GB,en-orig"


def is_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"}


def _find_media(directory: Path) -> Path | None:
    candidates = [p for p in directory.glob("source.*") if p.suffix.lower() in MEDIA_SUFFIXES]
    return sorted(candidates)[0] if candidates else None


def _find_subtitles(directory: Path) -> Path | None:
    subs = sorted(directory.glob("source*.vtt"))
    if not subs:
        return None
    english = [p for p in subs if any(tag in p.name for tag in (".en.", ".en-US.", ".en-GB.", ".en-orig."))]
    return english[0] if english else subs[0]


def _read_info(directory: Path) -> dict:
    info_path = directory / "source.info.json"
    if not info_path.exists():
        return {}
    try:
        raw = json.loads(info_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[pi-watch-video] could not parse info json: {exc}", file=sys.stderr)
        return {}
    if "title" in raw or "uploader" in raw or "duration" in raw or "source" in raw:
        return raw
    return {
        "title": raw.get("title"),
        "uploader": raw.get("uploader") or raw.get("channel"),
        "duration": raw.get("duration"),
        "source": raw.get("webpage_url") or raw.get("original_url") or raw.get("url"),
    }


def resolve_bundle(directory: Path) -> dict:
    directory = Path(directory).expanduser().resolve()
    media = _find_media(directory)
    if media is None:
        raise SystemExit(f"No staged media found in {directory}")
    metadata = _read_info(directory) or {"title": media.name, "source": str(media)}
    subtitles = _find_subtitles(directory)
    return {
        "video": str(media),
        "subtitles": str(subtitles) if subtitles else None,
        "metadata": metadata,
        "downloaded": True,
    }


def stage_local(source: str, directory: Path) -> dict:
    path = Path(source).expanduser().resolve()
    if not path.exists():
        raise SystemExit(f"Video file not found: {path}")
    directory.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lower() or ".bin"
    target = directory / f"source{suffix}"
    shutil.copy2(path, target)
    metadata = {"title": path.name, "source": str(path)}
    (directory / "source.info.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    if suffix not in MEDIA_SUFFIXES:
        print(f"[pi-watch-video] warning: unknown media suffix {path.suffix}; continuing", file=sys.stderr)
    return resolve_bundle(directory)


def _write_fetch_metadata(directory: Path, fetcher: str) -> None:
    try:
        (directory / "source.fetcher.txt").write_text(fetcher + "\n", encoding="utf-8")
        version = subprocess.run(["yt-dlp", "--version"], capture_output=True, text=True)
        if version.returncode == 0 and version.stdout.strip():
            (directory / "source.ytdlp-version.txt").write_text(version.stdout.strip() + "\n", encoding="utf-8")
    except Exception:
        pass


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
    cookies = config_value("PI_WATCH_YTDLP_COOKIES", "YTDLP_COOKIES")
    if cookies:
        command.extend(["--cookies", cookies])
    command.append(url)
    result = subprocess.run(command, stdout=sys.stderr, stderr=sys.stderr)
    if result.returncode != 0:
        raise SystemExit(f"yt-dlp failed to fetch {url} (exit {result.returncode})")
    _write_fetch_metadata(directory, "yt-dlp")
    return resolve_bundle(directory)


def stage_source(source: str, directory: Path) -> dict:
    return download_url(source, directory) if is_url(source) else stage_local(source, directory)


def resolve_source(source: str, directory: Path) -> dict:
    return stage_source(source, directory)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: media_source.py <url-or-file> <out-dir>")
    print(json.dumps(stage_source(sys.argv[1], Path(sys.argv[2])), indent=2))
