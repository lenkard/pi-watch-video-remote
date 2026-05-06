#!/usr/bin/env python3
"""Minimal Whisper clients for Groq and OpenAI using only the Python stdlib."""
from __future__ import annotations

import io
import json
import mimetypes
import os
import shutil
import subprocess
import sys
import urllib.error
import uuid
from pathlib import Path
from urllib.request import Request, urlopen

CONFIG_FILE = Path.home() / ".config" / "pi-watch-video" / ".env"
GROQ_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
OPENAI_URL = "https://api.openai.com/v1/audio/transcriptions"


def _dotenv_value(path: Path, key: str) -> str | None:
    if not path.exists():
        return None
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, _, value = line.partition("=")
            if name.strip() == key:
                value = value.strip().strip('"\'')
                return value or None
    except OSError:
        return None
    return None


def select_key(preferred: str | None = None) -> tuple[str | None, str | None]:
    order = [("groq", "GROQ_API_KEY"), ("openai", "OPENAI_API_KEY")]
    if preferred:
        order = [pair for pair in order if pair[0] == preferred]
    for backend, env_name in order:
        value = os.environ.get(env_name) or _dotenv_value(CONFIG_FILE, env_name) or _dotenv_value(Path.cwd() / ".env", env_name)
        if value:
            return backend, value.strip()
    return None, None


def extract_audio(video: str, output: Path) -> Path:
    if shutil.which("ffmpeg") is None:
        raise SystemExit("ffmpeg is missing; cannot create audio for Whisper")
    output.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", video,
        "-vn", "-ac", "1", "-ar", "16000", "-b:a", "64k", str(output)
    ], text=True, capture_output=True)
    if result.returncode != 0:
        raise SystemExit(f"audio extraction failed: {result.stderr.strip()}")
    if output.stat().st_size <= 0:
        raise SystemExit("audio extraction produced an empty file")
    return output


def _multipart(fields: dict[str, str], file_path: Path) -> tuple[bytes, str]:
    boundary = "----PiWatchVideo" + uuid.uuid4().hex
    buf = io.BytesIO()
    for name, value in fields.items():
        buf.write(f"--{boundary}\r\n".encode())
        buf.write(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        buf.write(str(value).encode())
        buf.write(b"\r\n")
    mime = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    buf.write(f"--{boundary}\r\n".encode())
    buf.write(f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"\r\n'.encode())
    buf.write(f"Content-Type: {mime}\r\n\r\n".encode())
    buf.write(file_path.read_bytes())
    buf.write(f"\r\n--{boundary}--\r\n".encode())
    return buf.getvalue(), boundary


def _post(url: str, key: str, model: str, audio: Path) -> dict:
    body, boundary = _multipart({"model": model, "response_format": "verbose_json", "temperature": "0"}, audio)
    request = Request(url, data=body, method="POST", headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "User-Agent": "pi-watch-video/0.1",
    })
    try:
        with urlopen(request, timeout=300) as response:
            return json.loads(response.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise SystemExit(f"Whisper API failed: HTTP {exc.code}: {detail}")


def _segments(data: dict) -> list[dict]:
    output = []
    for segment in data.get("segments") or []:
        text = (segment.get("text") or "").strip()
        if text:
            output.append({"start": float(segment.get("start") or 0), "end": float(segment.get("end") or 0), "text": text})
    if not output and data.get("text"):
        output.append({"start": 0.0, "end": 0.0, "text": data["text"].strip()})
    return output


def transcribe(video: str, audio_path: Path, preferred: str | None = None) -> tuple[list[dict], str | None]:
    backend, key = select_key(preferred)
    if not backend or not key:
        return [], None
    audio = extract_audio(video, audio_path)
    print(f"[pi-watch-video] sending {audio.stat().st_size / 1024:.0f} KiB audio to {backend} Whisper", file=sys.stderr)
    if backend == "groq":
        data = _post(GROQ_URL, key, "whisper-large-v3", audio)
    else:
        data = _post(OPENAI_URL, key, "whisper-1", audio)
    return _segments(data), backend
