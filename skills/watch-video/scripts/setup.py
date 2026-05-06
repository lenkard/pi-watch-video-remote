#!/usr/bin/env python3
"""Instructional setup checker for pi-watch-video."""
from __future__ import annotations

import json
import os
import platform
import shutil
import stat
import sys
from pathlib import Path

NEEDED = ["ffmpeg", "ffprobe", "yt-dlp"]
CONFIG_DIR = Path.home() / ".config" / "pi-watch-video"
CONFIG_FILE = CONFIG_DIR / ".env"
TEMPLATE = """# pi-watch-video optional transcription settings
# Native captions are used first when available.
# Remote is any OpenAI-compatible /v1/audio/transcriptions endpoint.

PI_WATCH_TRANSCRIPTION_ORDER=remote,groq,openai
PI_WATCH_TRANSCRIPTION_ENDPOINT=
PI_WATCH_TRANSCRIPTION_API_KEY=
PI_WATCH_TRANSCRIPTION_MODEL=small
PI_WATCH_TRANSCRIPTION_LANGUAGE=auto
PI_WATCH_TRANSCRIPTION_TIMEOUT=1800
PI_WATCH_TRANSCRIPTION_FALLBACK_ON_BUSY=0
PI_WATCH_TRANSCRIPTION_PREFLIGHT=1

# Optional hosted fallbacks. Groq is preferred before OpenAI if both are in the order.
GROQ_API_KEY=
OPENAI_API_KEY=
"""


def missing_bins() -> list[str]:
    return [name for name in NEEDED if shutil.which(name) is None]


def read_env(name: str) -> str | None:
    if os.environ.get(name):
        return os.environ[name].strip()
    if not CONFIG_FILE.exists():
        return None
    for line in CONFIG_FILE.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        if key.strip() == name and value.strip():
            return value.strip().strip('"\'')
    return None


def transcription_backend() -> str | None:
    if read_env("PI_WATCH_TRANSCRIPTION_ENDPOINT") or read_env("TRANSCRIPTION_ENDPOINT"):
        return "remote"
    if read_env("GROQ_API_KEY"):
        return "groq"
    if read_env("OPENAI_API_KEY"):
        return "openai"
    return None


def ensure_config() -> bool:
    if CONFIG_FILE.exists():
        return False
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(TEMPLATE, encoding="utf-8")
    try:
        CONFIG_FILE.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass
    return True


def status() -> dict:
    missing = missing_bins()
    backend = transcription_backend()
    if not missing and backend:
        state = "ready"
    elif missing and not backend:
        state = "needs_binaries_and_transcription_config"
    elif missing:
        state = "needs_binaries"
    else:
        state = "needs_transcription_config"
    return {
        "status": state,
        "missing_binaries": missing,
        "transcription_backend": backend,
        "config_file": str(CONFIG_FILE),
        "platform": platform.system(),
    }


def install_hints(missing: list[str]) -> list[str]:
    system = platform.system()
    hints: list[str] = []
    needs_ffmpeg = "ffmpeg" in missing or "ffprobe" in missing
    needs_ytdlp = "yt-dlp" in missing
    if system == "Darwin":
        packages = []
        if needs_ffmpeg:
            packages.append("ffmpeg")
        if needs_ytdlp:
            packages.append("yt-dlp")
        hints.append("brew install " + " ".join(packages))
    elif system == "Linux":
        if needs_ffmpeg:
            hints.append("sudo apt install ffmpeg    # Debian/Ubuntu")
            hints.append("sudo dnf install ffmpeg    # Fedora/RHEL family")
        if needs_ytdlp:
            hints.append("pipx install yt-dlp        # recommended")
            hints.append("python3 -m pip install --user yt-dlp")
    elif system == "Windows":
        if needs_ffmpeg:
            hints.append("winget install Gyan.FFmpeg")
        if needs_ytdlp:
            hints.append("winget install yt-dlp.yt-dlp")
    else:
        hints.append("Install ffmpeg/ffprobe and yt-dlp with your system package manager.")
    return hints


def check() -> int:
    current = status()
    if current["status"] == "ready":
        return 0
    print(f"[pi-watch-video] setup status: {current['status']}", file=sys.stderr)
    print(f"[pi-watch-video] run: python3 {Path(__file__).resolve()} --doctor", file=sys.stderr)
    if current["missing_binaries"] and not current["transcription_backend"]:
        return 4
    if current["missing_binaries"]:
        return 2
    return 3


def doctor() -> int:
    created = ensure_config()
    current = status()
    print("# pi-watch-video setup doctor")
    print(f"Status: {current['status']}")
    print(f"Config: {CONFIG_FILE}" + (" (created)" if created else ""))
    if current["missing_binaries"]:
        print("\nMissing binaries: " + ", ".join(current["missing_binaries"]))
        print("Install suggestions:")
        for hint in install_hints(current["missing_binaries"]):
            print(f"  {hint}")
    else:
        print("Binaries: ok")
    if current["transcription_backend"]:
        print(f"Transcription fallback: ok ({current['transcription_backend']})")
    else:
        print("\nNo transcription fallback configured. Videos with captions still work.")
        print("For free remote transcription, configure:")
        print("  PI_WATCH_TRANSCRIPTION_ENDPOINT=https://.../v1/audio/transcriptions")
        print("  PI_WATCH_TRANSCRIPTION_API_KEY=...")
        print("Hosted fallbacks:")
        print("  GROQ_API_KEY=...    # Groq Whisper")
        print("  OPENAI_API_KEY=...  # OpenAI Whisper")
    return 0 if current["status"] == "ready" else 1


def main() -> int:
    if "--json" in sys.argv:
        print(json.dumps(status(), indent=2))
        return 0
    if "--check" in sys.argv:
        return check()
    return doctor()


if __name__ == "__main__":
    raise SystemExit(main())
