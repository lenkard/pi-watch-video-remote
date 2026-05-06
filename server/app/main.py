from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import JSONResponse, PlainTextResponse

API_KEY = os.environ.get("API_KEY", "").strip()
MODELS_DIR = Path(os.environ.get("MODELS_DIR", "/models"))
DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
WHISPER_CLI = os.environ.get("WHISPER_CLI", "/usr/local/bin/whisper-cli")
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "small-q5_0")
AUTO_DOWNLOAD = os.environ.get("WHISPER_MODEL_AUTO_DOWNLOAD", "1").lower() in {"1", "true", "yes", "on"}
MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "200"))
MAX_AUDIO_SECONDS = int(os.environ.get("MAX_AUDIO_SECONDS", "3600"))
KEEP_UPLOADS = os.environ.get("KEEP_UPLOADS", "0").lower() in {"1", "true", "yes", "on"}
THREADS = os.environ.get("WHISPER_THREADS", "")

MODEL_URLS = {
    "small-q5_0": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small-q5_0.bin",
}

DEFAULT_ALIASES = {
    "small": "ggml-small-q5_0.bin",
    "small-q5_0": "ggml-small-q5_0.bin",
    "base": "ggml-base-q5_0.bin",
    "base-q5_0": "ggml-base-q5_0.bin",
    "medium": "ggml-medium-q5_0.bin",
    "medium-q5_0": "ggml-medium-q5_0.bin",
}

CUE_RE = re.compile(r"(\d{2}):(\d{2}):(\d{2})[.,](\d{3})\s+-->\s+(\d{2}):(\d{2}):(\d{2})[.,](\d{3})")
HTML_RE = re.compile(r"<[^>]+>")
semaphore = asyncio.Semaphore(1)
app = FastAPI(title="pi-watch-video transcriber", version="0.1.0")


def aliases() -> dict[str, Path]:
    mapping = dict(DEFAULT_ALIASES)
    raw = os.environ.get("MODEL_ALIASES", "")
    for item in raw.split(","):
        if not item.strip() or ":" not in item:
            continue
        name, path = item.split(":", 1)
        mapping[name.strip()] = path.strip()
    out: dict[str, Path] = {}
    for name, value in mapping.items():
        path = Path(value)
        out[name] = path if path.is_absolute() else MODELS_DIR / path
    return out


def require_auth(authorization: str | None) -> None:
    if not API_KEY:
        raise HTTPException(500, "API_KEY is not configured")
    expected = f"Bearer {API_KEY}"
    if authorization != expected:
        raise HTTPException(401, "missing or invalid bearer token")


def model_path(name: str | None) -> Path:
    selected = name or DEFAULT_MODEL
    mapping = aliases()
    if selected not in mapping:
        raise HTTPException(400, f"unknown model '{selected}'. Available: {', '.join(sorted(mapping))}")
    path = mapping[selected]
    if not path.exists():
        raise HTTPException(404, f"model file missing: {path}. Mount it into /models or request the default auto-downloaded model.")
    return path


def download_default_model() -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    path = aliases().get(DEFAULT_MODEL)
    if not path or path.exists() or not AUTO_DOWNLOAD:
        return
    url = MODEL_URLS.get(DEFAULT_MODEL)
    if not url:
        return
    tmp = path.with_suffix(path.suffix + ".tmp")
    print(f"[transcriber] downloading default model {DEFAULT_MODEL} to {path}", flush=True)
    urllib.request.urlretrieve(url, tmp)
    tmp.replace(path)


def check_binary(name: str) -> bool:
    return shutil.which(name) is not None or Path(name).exists()


def run(cmd: list[str], timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f"command failed: {' '.join(cmd)}")
    return result


def seconds(groups: tuple[str, ...]) -> float:
    h, m, s, ms = groups
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def parse_vtt(path: Path) -> list[dict]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    items: list[dict] = []
    i = 0
    while i < len(lines):
        match = CUE_RE.match(lines[i])
        if not match:
            i += 1
            continue
        start = seconds(match.groups()[:4])
        end = seconds(match.groups()[4:])
        i += 1
        cue: list[str] = []
        while i < len(lines) and lines[i].strip():
            text = HTML_RE.sub("", lines[i]).replace("&nbsp;", " ").strip()
            if text:
                cue.append(text)
            i += 1
        if cue:
            items.append({"start": round(start, 2), "end": round(end, 2), "text": " ".join(cue)})
        i += 1
    return items


def json_time(value: object, fallback: float = 0.0) -> float:
    if value is None:
        return fallback
    if isinstance(value, (int, float)):
        # whisper.cpp offsets are commonly milliseconds; OpenAI-style values are seconds.
        return float(value) / 1000 if value > 1000 else float(value)
    text = str(value).strip().replace(",", ".")
    match = re.match(r"^(\d{2}):(\d{2}):(\d{2})\.(\d{3})$", text)
    if match:
        return seconds(match.groups())
    try:
        return float(text)
    except ValueError:
        return fallback


def parse_json(path: Path) -> list[dict]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    source = data.get("transcription") or data.get("segments") or []
    items: list[dict] = []
    for item in source:
        timestamps = item.get("timestamps") or {}
        offsets = item.get("offsets") or {}
        start = item.get("start", offsets.get("from", timestamps.get("from", 0)))
        end = item.get("end", offsets.get("to", timestamps.get("to", 0)))
        text = (item.get("text") or "").strip()
        if text:
            items.append({"start": round(json_time(start), 2), "end": round(json_time(end), 2), "text": text})
    return items


def ffprobe_duration(path: Path) -> float:
    result = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)])
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


def transcribe_file(upload: Path, model: Path, language: str | None) -> dict:
    duration = ffprobe_duration(upload)
    if duration > MAX_AUDIO_SECONDS:
        raise HTTPException(413, f"audio duration {duration:.1f}s exceeds MAX_AUDIO_SECONDS={MAX_AUDIO_SECONDS}")
    wav = upload.with_suffix(".wav")
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(upload), "-vn", "-ac", "1", "-ar", "16000", str(wav)])
    prefix = upload.with_suffix("")
    cmd = [WHISPER_CLI, "-m", str(model), "-f", str(wav), "-oj", "-ovtt", "-of", str(prefix)]
    if language and language != "auto":
        cmd += ["-l", language]
    if THREADS:
        cmd += ["-t", THREADS]
    run(cmd, timeout=max(60, int(duration * 60) if duration else 3600))
    segments = parse_json(prefix.with_suffix(".json")) or parse_vtt(prefix.with_suffix(".vtt"))
    text = " ".join(item["text"] for item in segments).strip()
    return {"text": text, "segments": segments, "language": language or "auto", "duration": duration}


@app.on_event("startup")
def startup() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    download_default_model()


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/ready")
def ready(authorization: Annotated[str | None, Header()] = None) -> dict:
    require_auth(authorization)
    problems = []
    for binary in ["ffmpeg", "ffprobe", WHISPER_CLI]:
        if not check_binary(binary):
            problems.append(f"missing {binary}")
    try:
        model_path(DEFAULT_MODEL)
    except HTTPException as exc:
        problems.append(str(exc.detail))
    if problems:
        raise HTTPException(503, {"ok": False, "problems": problems})
    return {"ok": True, "backend": "whisper.cpp", "default_model": DEFAULT_MODEL}


@app.get("/v1/models")
def models(authorization: Annotated[str | None, Header()] = None) -> dict:
    require_auth(authorization)
    return {"object": "list", "data": [{"id": name, "object": "model", "owned_by": "local", "available": path.exists()} for name, path in sorted(aliases().items())]}


@app.post("/v1/audio/transcriptions")
async def transcriptions(
    authorization: Annotated[str | None, Header()] = None,
    file: UploadFile = File(...),
    model: str | None = Form(None),
    language: str | None = Form(None),
    response_format: str = Form("json"),
    temperature: str | None = Form(None),
) -> JSONResponse | PlainTextResponse:
    require_auth(authorization)
    if response_format not in {"json", "verbose_json", "text"}:
        raise HTTPException(400, "response_format must be one of: json, verbose_json, text")
    if semaphore.locked():
        raise HTTPException(429, "transcription server is busy")
    chosen_model = model_path(model)
    async with semaphore:
        work = Path(tempfile.mkdtemp(prefix="job-", dir=DATA_DIR))
        upload = work / (file.filename or "audio")
        try:
            size = 0
            with upload.open("wb") as out:
                while chunk := await file.read(1024 * 1024):
                    size += len(chunk)
                    if size > MAX_UPLOAD_MB * 1024 * 1024:
                        raise HTTPException(413, f"upload exceeds MAX_UPLOAD_MB={MAX_UPLOAD_MB}")
                    out.write(chunk)
            result = await asyncio.to_thread(transcribe_file, upload, chosen_model, language)
            if response_format == "text":
                return PlainTextResponse(result["text"])
            if response_format == "json":
                return JSONResponse({"text": result["text"]})
            return JSONResponse(result)
        finally:
            if not KEEP_UPLOADS:
                shutil.rmtree(work, ignore_errors=True)
            else:
                (work / "kept_at.txt").write_text(str(time.time()), encoding="utf-8")
