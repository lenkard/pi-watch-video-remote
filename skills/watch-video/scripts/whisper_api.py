#!/usr/bin/env python3
"""Transcription clients for Groq, OpenAI, and OpenAI-compatible remotes."""
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
from urllib.parse import urlparse, urlunparse
from urllib.request import Request, urlopen

CONFIG_FILE = Path.home() / ".config" / "pi-watch-video" / ".env"
GROQ_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
OPENAI_URL = "https://api.openai.com/v1/audio/transcriptions"
DEFAULT_TIMEOUT = 1800


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


def config_value(*names: str) -> str | None:
    for name in names:
        value = os.environ.get(name) or _dotenv_value(CONFIG_FILE, name) or _dotenv_value(Path.cwd() / ".env", name)
        if value and value.strip():
            return value.strip()
    return None


def truthy(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def int_config(default: int, *names: str) -> int:
    value = config_value(*names)
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def provider_order(forced: str | None = None) -> list[str]:
    if forced:
        return [forced]
    raw = config_value("PI_WATCH_TRANSCRIPTION_ORDER", "TRANSCRIPTION_ORDER")
    if raw:
        return [item.strip() for item in raw.split(",") if item.strip()]
    if config_value("PI_WATCH_TRANSCRIPTION_ENDPOINT", "TRANSCRIPTION_ENDPOINT"):
        return ["remote", "groq", "openai"]
    return ["groq", "openai"]


def _key_for(backend: str) -> str | None:
    if backend == "groq":
        return config_value("GROQ_API_KEY")
    if backend == "openai":
        return config_value("OPENAI_API_KEY")
    if backend == "remote":
        return config_value("PI_WATCH_TRANSCRIPTION_API_KEY", "TRANSCRIPTION_API_KEY")
    return None


def extract_audio(video: str, output: Path, start: float | None = None, end: float | None = None) -> Path:
    if shutil.which("ffmpeg") is None:
        raise SystemExit("ffmpeg is missing; cannot create audio for transcription")
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    if start is not None:
        cmd += ["-ss", str(start)]
    cmd += ["-i", video]
    if end is not None:
        duration = end - (start or 0)
        if duration <= 0:
            raise SystemExit("audio extraction range is empty")
        cmd += ["-t", str(duration)]
    cmd += ["-vn", "-ac", "1", "-ar", "16000", "-b:a", "64k", str(output)]
    result = subprocess.run(cmd, text=True, capture_output=True)
    if result.returncode != 0:
        raise SystemExit(f"audio extraction failed: {result.stderr.strip()}")
    if output.stat().st_size <= 0:
        raise SystemExit("audio extraction produced an empty file")
    return output


def _multipart(fields: dict[str, str], file_path: Path) -> tuple[bytes, str]:
    boundary = "----PiWatchVideo" + uuid.uuid4().hex
    buf = io.BytesIO()
    for name, value in fields.items():
        if value is None:
            continue
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


def _ready_url(endpoint: str) -> str:
    parsed = urlparse(endpoint)
    path = parsed.path
    marker = "/v1/audio/transcriptions"
    if path.endswith(marker):
        path = path[: -len(marker)] + "/ready"
    else:
        path = "/ready"
    return urlunparse(parsed._replace(path=path, params="", query="", fragment=""))


def _preflight(endpoint: str, key: str | None, timeout: int) -> None:
    if not truthy(config_value("PI_WATCH_TRANSCRIPTION_PREFLIGHT", "TRANSCRIPTION_PREFLIGHT"), True):
        return
    headers = {"User-Agent": "pi-watch-video/0.1"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    request = Request(_ready_url(endpoint), method="GET", headers=headers)
    try:
        with urlopen(request, timeout=min(timeout, 30)) as response:
            if response.status >= 400:
                raise SystemExit(f"remote transcription server is not ready: HTTP {response.status}")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            print("[pi-watch-video] remote /ready not found; continuing", file=sys.stderr)
            return
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise SystemExit(f"remote transcription server is not ready: HTTP {exc.code}: {detail}")
    except urllib.error.URLError as exc:
        raise SystemExit(f"remote transcription preflight failed: {exc}")


def _post(url: str, key: str | None, model: str, audio: Path, timeout: int, language: str | None = None) -> dict:
    fields = {"model": model, "response_format": "verbose_json", "temperature": "0"}
    if language and language != "auto":
        fields["language"] = language
    body, boundary = _multipart(fields, audio)
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}", "User-Agent": "pi-watch-video/0.1"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    request = Request(url, data=body, method="POST", headers=headers)
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {"text": raw}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        if exc.code == 429 and not truthy(config_value("PI_WATCH_TRANSCRIPTION_FALLBACK_ON_BUSY", "TRANSCRIPTION_FALLBACK_ON_BUSY"), False):
            raise SystemExit("remote transcription server is busy (HTTP 429). Try again later or set PI_WATCH_TRANSCRIPTION_FALLBACK_ON_BUSY=1.")
        raise RuntimeError(f"HTTP {exc.code}: {detail}")


def _segments(data: dict, offset: float = 0.0) -> list[dict]:
    output = []
    for segment in data.get("segments") or []:
        text = (segment.get("text") or "").strip()
        if text:
            output.append({
                "start": float(segment.get("start") or 0) + offset,
                "end": float(segment.get("end") or 0) + offset,
                "text": text,
            })
    if not output and data.get("text"):
        output.append({"start": offset, "end": offset, "text": data["text"].strip()})
    return output


def _try_backend(backend: str, audio: Path, language: str | None) -> tuple[list[dict], str | None]:
    timeout = int_config(DEFAULT_TIMEOUT, "PI_WATCH_TRANSCRIPTION_TIMEOUT", "TRANSCRIPTION_TIMEOUT")
    if backend == "remote":
        endpoint = config_value("PI_WATCH_TRANSCRIPTION_ENDPOINT", "TRANSCRIPTION_ENDPOINT")
        if not endpoint:
            return [], None
        key = _key_for("remote")
        model = config_value("PI_WATCH_TRANSCRIPTION_MODEL", "TRANSCRIPTION_MODEL") or "small"
        _preflight(endpoint, key, timeout)
        print(f"[pi-watch-video] sending {audio.stat().st_size / 1024:.0f} KiB audio to remote transcription endpoint", file=sys.stderr)
        return _segments(_post(endpoint, key, model, audio, timeout, language)), "remote"
    key = _key_for(backend)
    if not key:
        return [], None
    if backend == "groq":
        print(f"[pi-watch-video] sending {audio.stat().st_size / 1024:.0f} KiB audio to Groq Whisper", file=sys.stderr)
        return _segments(_post(GROQ_URL, key, "whisper-large-v3", audio, timeout, language)), "groq"
    if backend == "openai":
        print(f"[pi-watch-video] sending {audio.stat().st_size / 1024:.0f} KiB audio to OpenAI Whisper", file=sys.stderr)
        return _segments(_post(OPENAI_URL, key, "whisper-1", audio, timeout, language)), "openai"
    return [], None


def transcribe(
    video: str,
    audio_path: Path,
    preferred: str | None = None,
    language: str | None = None,
    start: float | None = None,
    end: float | None = None,
) -> tuple[list[dict], str | None]:
    language = language or config_value("PI_WATCH_TRANSCRIPTION_LANGUAGE", "TRANSCRIPTION_LANGUAGE")
    if language == "auto":
        language = None
    audio = extract_audio(video, audio_path, start=start, end=end)
    offset = start or 0.0
    last_error: Exception | None = None
    for backend in provider_order(preferred):
        try:
            segments, used = _try_backend(backend, audio, language)
            if segments or used:
                if offset:
                    segments = [{**item, "start": item["start"] + offset, "end": item["end"] + offset} for item in segments]
                return segments, used
        except SystemExit:
            raise
        except Exception as exc:
            last_error = exc
            print(f"[pi-watch-video] transcription provider {backend} failed: {exc}", file=sys.stderr)
            continue
    if last_error:
        raise SystemExit(f"transcription failed: {last_error}")
    return [], None
