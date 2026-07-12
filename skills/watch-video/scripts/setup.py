#!/usr/bin/env python3
"""Instructional setup checker for pi-watch-video."""
from __future__ import annotations

import json
import platform
import shutil
import stat
import sys
from pathlib import Path

from config import config_value

CONFIG_DIR = Path.home() / ".config" / "pi-watch-video"
CONFIG_FILE = CONFIG_DIR / ".env"
TEMPLATE = """# pi-watch-video settings
# Public URLs can run locally.
# For gated URLs on a remote browser host, set PI_WATCH_FETCH_MODE=remote_browser.
# For heavy processing on a remote worker like Kinkaid, set PI_WATCH_PROCESS_MODE=remote.
# Keep this file private; do not commit browser profiles, SSH keys, endpoint URLs, or API keys.

PI_WATCH_TRANSCRIPTION_ENDPOINT=
PI_WATCH_TRANSCRIPTION_API_KEY=
PI_WATCH_TRANSCRIPTION_MODEL=whisper
PI_WATCH_TRANSCRIPTION_LANGUAGE=auto
PI_WATCH_TRANSCRIPTION_TIMEOUT=1800
PI_WATCH_TRANSCRIPTION_PREFLIGHT=1

# Optional yt-dlp cookies file for local fetches.
PI_WATCH_YTDLP_COOKIES=

# local | remote_browser
PI_WATCH_FETCH_MODE=local
PI_WATCH_REMOTE_FETCH_HOST=
PI_WATCH_REMOTE_FETCH_USER=
PI_WATCH_REMOTE_FETCH_PORT=22
PI_WATCH_REMOTE_FETCH_SSH_KEY=
PI_WATCH_REMOTE_FETCH_CONTAINER=
PI_WATCH_REMOTE_FETCH_HOST_JOBS_DIR=/opt/pi-watch-video/browser/data/jobs
PI_WATCH_REMOTE_FETCH_SCRIPT=/usr/local/bin/fetch-url
PI_WATCH_REMOTE_FETCH_KEEP=0

# local | remote
PI_WATCH_PROCESS_MODE=local
PI_WATCH_REMOTE_PROCESS_HOST=
PI_WATCH_REMOTE_PROCESS_USER=
PI_WATCH_REMOTE_PROCESS_PORT=22
PI_WATCH_REMOTE_PROCESS_SSH_KEY=
PI_WATCH_REMOTE_PROCESS_HOST_JOBS_DIR=/opt/pi-watch-video/jobs
PI_WATCH_REMOTE_PROCESS_SCRIPT=/opt/pi-watch-video/skills/watch-video/scripts/process_bundle.py
PI_WATCH_REMOTE_PROCESS_PYTHON=python3
PI_WATCH_REMOTE_PROCESS_KEEP=0
"""


def read_env(name: str) -> str | None:
    value = config_value(name)
    return value.strip() if value else None


def fetch_mode() -> str:
    return (read_env("PI_WATCH_FETCH_MODE") or "local").lower()


def process_mode() -> str:
    return (read_env("PI_WATCH_PROCESS_MODE") or "local").lower()


def needed_bins() -> list[str]:
    bins: list[str] = []
    if fetch_mode() != "remote_browser":
        bins.append("yt-dlp")
    if process_mode() != "remote":
        bins.extend(["ffmpeg", "ffprobe"])
    if fetch_mode() == "remote_browser" or process_mode() == "remote":
        bins.extend(["ssh", "rsync"])
    out: list[str] = []
    for name in bins:
        if name not in out:
            out.append(name)
    return out


def missing_bins() -> list[str]:
    return [name for name in needed_bins() if shutil.which(name) is None]


def local_transcription_backend() -> str | None:
    if read_env("PI_WATCH_TRANSCRIPTION_ENDPOINT") or read_env("TRANSCRIPTION_ENDPOINT"):
        return "endpoint"
    return None


def missing_remote_fetch() -> list[str]:
    if fetch_mode() != "remote_browser":
        return []
    required = [
        "PI_WATCH_REMOTE_FETCH_HOST",
        "PI_WATCH_REMOTE_FETCH_USER",
        "PI_WATCH_REMOTE_FETCH_CONTAINER",
    ]
    return [name for name in required if not read_env(name)]


def missing_remote_process() -> list[str]:
    if process_mode() != "remote":
        return []
    required = [
        "PI_WATCH_REMOTE_PROCESS_HOST",
        "PI_WATCH_REMOTE_PROCESS_USER",
    ]
    return [name for name in required if not read_env(name)]


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
    fetch = fetch_mode()
    process = process_mode()
    missing_fetch = missing_remote_fetch()
    missing_process = missing_remote_process()
    backend = local_transcription_backend()
    needs_local_whisper = process != "remote"
    transcription_ok = bool(backend) or not needs_local_whisper
    problems: list[str] = []
    if missing:
        problems.append("missing_binaries")
    if missing_fetch:
        problems.append("remote_fetch_config")
    if missing_process:
        problems.append("remote_process_config")
    if not transcription_ok:
        problems.append("transcription_endpoint_config")
    return {
        "status": "ready" if not problems else "needs_setup",
        "problems": problems,
        "missing_binaries": missing,
        "fetch_mode": fetch,
        "process_mode": process,
        "missing_remote_fetch": missing_fetch,
        "missing_remote_process": missing_process,
        "transcription_backend": backend,
        "config_file": str(CONFIG_FILE),
        "platform": platform.system(),
    }


def install_hints(missing: list[str]) -> list[str]:
    system = platform.system()
    hints: list[str] = []
    names = set(missing)
    if system == "Darwin":
        packages = []
        for name in ("ffmpeg", "yt-dlp", "rsync"):
            if name in names:
                packages.append(name)
        if packages:
            hints.append("brew install " + " ".join(packages))
        if "ssh" in names:
            hints.append("Install OpenSSH client if it is missing from PATH.")
    elif system == "Linux":
        if "ffmpeg" in names or "ffprobe" in names:
            hints.append("sudo apt install ffmpeg    # Debian/Ubuntu")
            hints.append("sudo dnf install ffmpeg    # Fedora/RHEL family")
        if "yt-dlp" in names:
            hints.append("pipx install yt-dlp        # recommended")
            hints.append("python3 -m pip install --user yt-dlp")
        if "rsync" in names:
            hints.append("sudo apt install rsync     # Debian/Ubuntu")
        if "ssh" in names:
            hints.append("sudo apt install openssh-client")
    elif system == "Windows":
        if "ffmpeg" in names or "ffprobe" in names:
            hints.append("winget install Gyan.FFmpeg")
        if "yt-dlp" in names:
            hints.append("winget install yt-dlp.yt-dlp")
        if "rsync" in names or "ssh" in names:
            hints.append("Install OpenSSH client and an rsync port (or use WSL).")
    else:
        hints.append("Install the missing binaries with your system package manager.")
    return hints


def check() -> int:
    current = status()
    if current["status"] == "ready":
        return 0
    print(f"[pi-watch-video] setup status: {current['status']}", file=sys.stderr)
    print(f"[pi-watch-video] run: python3 {Path(__file__).resolve()} --doctor", file=sys.stderr)
    return 1


def doctor() -> int:
    created = ensure_config()
    current = status()
    print("# pi-watch-video setup doctor")
    print(f"Status: {current['status']}")
    print(f"Config: {CONFIG_FILE}" + (" (created)" if created else ""))
    print(f"Fetch mode: {current['fetch_mode']}")
    print(f"Process mode: {current['process_mode']}")
    if current["missing_binaries"]:
        print("\nMissing binaries: " + ", ".join(current["missing_binaries"]))
        print("Install suggestions:")
        for hint in install_hints(current["missing_binaries"]):
            print(f"  {hint}")
    else:
        print("Binaries: ok")

    if current["missing_remote_fetch"]:
        print("\nRemote fetch config missing:")
        for name in current["missing_remote_fetch"]:
            print(f"  {name}=")

    if current["missing_remote_process"]:
        print("\nRemote process config missing:")
        for name in current["missing_remote_process"]:
            print(f"  {name}=")

    if current["process_mode"] == "remote":
        print("Remote processing: Kinkaid/worker handles Whisper and ffmpeg.")
    elif current["transcription_backend"]:
        print("Transcription endpoint: ok")
    else:
        print("\nNo transcription endpoint configured. Videos with captions still work.")
        print("Configure exactly one OpenAI-compatible endpoint:")
        print("  PI_WATCH_TRANSCRIPTION_ENDPOINT=https://.../v1/audio/transcriptions")
        print("  PI_WATCH_TRANSCRIPTION_API_KEY=...    # leave empty only if your endpoint has no auth")
        print("  PI_WATCH_TRANSCRIPTION_MODEL=whisper")
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
