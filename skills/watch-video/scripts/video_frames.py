#!/usr/bin/env python3
"""Video probing, timestamp parsing, and frame extraction."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

MAX_FPS = 2.0


def parse_timestamp(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    parts = value.split(":")
    try:
        if len(parts) == 1:
            return float(parts[0])
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    except ValueError:
        pass
    raise SystemExit(f"Could not parse timestamp {value!r}; use SS, MM:SS, or HH:MM:SS")


def human_time(seconds: float) -> str:
    seconds_i = int(round(seconds))
    hours, remainder = divmod(seconds_i, 3600)
    minutes, seconds_i = divmod(remainder, 60)
    return f"{hours}:{minutes:02d}:{seconds_i:02d}" if hours else f"{minutes:02d}:{seconds_i:02d}"


def probe(video: str) -> dict:
    if shutil.which("ffprobe") is None:
        raise SystemExit("ffprobe is missing. Install ffmpeg, then run setup doctor again.")
    result = subprocess.run([
        "ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", video
    ], text=True, capture_output=True)
    if result.returncode != 0:
        raise SystemExit(f"ffprobe failed: {result.stderr.strip()}")
    data = json.loads(result.stdout or "{}")
    streams = data.get("streams", [])
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
    fmt = data.get("format", {})
    duration = float(fmt.get("duration") or video_stream.get("duration") or 0)
    return {
        "duration": duration,
        "width": video_stream.get("width"),
        "height": video_stream.get("height"),
        "codec": video_stream.get("codec_name"),
        "has_video": bool(video_stream),
        "has_audio": audio_stream is not None,
    }


def _budget(duration: float, focused: bool, max_frames: int) -> int:
    if duration <= 0:
        return 1
    if focused:
        if duration <= 15:
            desired = int(round(duration * 2))
        elif duration <= 30:
            desired = 60
        elif duration <= 60:
            desired = 80
        else:
            desired = max_frames
        return min(max_frames, max(8, desired))
    if duration <= 30:
        desired = int(round(duration))
    elif duration <= 60:
        desired = 40
    elif duration <= 180:
        desired = 60
    elif duration <= 600:
        desired = 80
    else:
        desired = max_frames
    return min(max_frames, max(8, desired))


def choose_fps(duration: float, focused: bool, max_frames: int, override: float | None = None) -> tuple[float, int]:
    if override is not None:
        fps = max(0.001, min(float(override), MAX_FPS))
        return fps, min(max_frames, max(1, int(round(duration * fps))))
    target = _budget(duration, focused, max_frames)
    fps = min(MAX_FPS, target / duration) if duration > 0 else 1.0
    return fps, target


def extract_frames(video: str, out_dir: Path, fps: float, width: int, max_frames: int, start: float | None, end: float | None) -> list[dict]:
    if shutil.which("ffmpeg") is None:
        raise SystemExit("ffmpeg is missing. Run: python3 scripts/setup.py --doctor")
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("frame-*.jpg"):
        old.unlink()

    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    if start is not None:
        command.extend(["-ss", f"{start:.3f}"])
    if end is not None:
        command.extend(["-to", f"{end:.3f}"])
    command.extend([
        "-i", video,
        "-vf", f"fps={fps},scale={width}:-2",
        "-frames:v", str(max_frames),
        "-q:v", "4",
        str(out_dir / "frame-%04d.jpg"),
    ])
    result = subprocess.run(command, text=True, capture_output=True)
    if result.returncode != 0:
        raise SystemExit(f"ffmpeg failed to extract frames: {result.stderr.strip()}")

    base = start or 0.0
    frames = []
    for index, path in enumerate(sorted(out_dir.glob("frame-*.jpg"))):
        frames.append({"path": str(path), "time": round(base + (index / fps), 2), "index": index})
    return frames
