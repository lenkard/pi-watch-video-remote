#!/usr/bin/env python3
"""Process a staged media bundle on a remote worker and rsync back the result."""
from __future__ import annotations

import shlex
import subprocess
import uuid
from pathlib import Path

from config import config_value, int_config, truthy

DEFAULT_JOBS_DIR = "/opt/pi-watch-video/jobs"
DEFAULT_PROCESS_SCRIPT = "/opt/pi-watch-video/skills/watch-video/scripts/process_bundle.py"
DEFAULT_PYTHON = "python3"


def remote_process_enabled() -> bool:
    return (config_value("PI_WATCH_PROCESS_MODE") or "").strip().lower() == "remote"


def _required(name: str) -> str:
    value = config_value(name)
    if not value:
        raise SystemExit(f"{name} is not configured")
    return value


def _ssh_target(prefix: str) -> tuple[list[str], str, str, str | None]:
    host = _required(f"PI_WATCH_REMOTE_{prefix}_HOST")
    user = _required(f"PI_WATCH_REMOTE_{prefix}_USER")
    port = str(int_config(22, f"PI_WATCH_REMOTE_{prefix}_PORT"))
    key = config_value(f"PI_WATCH_REMOTE_{prefix}_SSH_KEY")
    base = ["ssh", "-p", port]
    if key:
        base.extend(["-i", str(Path(key).expanduser())])
    return base, f"{user}@{host}", port, key


def _rsync_shell(port: str, key: str | None) -> str:
    shell = f"ssh -p {port}"
    if key:
        shell += f" -i {shlex.quote(str(Path(key).expanduser()))}"
    return shell


def _run(command: list[str]) -> None:
    result = subprocess.run(command, text=True)
    if result.returncode != 0:
        raise SystemExit(f"command failed ({result.returncode}): {' '.join(command)}")


def process_bundle_remote(
    source_dir: Path,
    result_dir: Path,
    source_label: str | None = None,
    start: str | None = None,
    end: str | None = None,
    max_frames: int = 80,
    resolution: int = 512,
    fps: float | None = None,
    no_whisper: bool = False,
    transcription_language: str | None = None,
) -> Path:
    ssh_base, target, port, key = _ssh_target("PROCESS")
    jobs_dir = config_value("PI_WATCH_REMOTE_PROCESS_HOST_JOBS_DIR") or DEFAULT_JOBS_DIR
    process_script = config_value("PI_WATCH_REMOTE_PROCESS_SCRIPT") or DEFAULT_PROCESS_SCRIPT
    python = config_value("PI_WATCH_REMOTE_PROCESS_PYTHON") or DEFAULT_PYTHON
    keep_remote = truthy(config_value("PI_WATCH_REMOTE_PROCESS_KEEP"), False)
    job_id = f"job-{uuid.uuid4().hex[:12]}"
    remote_root = f"{jobs_dir.rstrip('/')}/{job_id}"
    remote_source = f"{remote_root}/source"
    remote_result = f"{remote_root}/result"

    source_dir = Path(source_dir).expanduser().resolve()
    result_dir = Path(result_dir).expanduser().resolve()
    result_dir.mkdir(parents=True, exist_ok=True)

    _run([*ssh_base, target, f"mkdir -p {shlex.quote(remote_source)} {shlex.quote(remote_result)}"])
    _run(["rsync", "-a", "-e", _rsync_shell(port, key), f"{source_dir}/", f"{target}:{remote_source}/"])

    remote_cmd = [python, process_script, remote_source, "--out-dir", remote_result, "--max-frames", str(max_frames), "--resolution", str(resolution)]
    if source_label:
        remote_cmd.extend(["--source-label", source_label])
    if start:
        remote_cmd.extend(["--start", start])
    if end:
        remote_cmd.extend(["--end", end])
    if fps is not None:
        remote_cmd.extend(["--fps", str(fps)])
    if no_whisper:
        remote_cmd.append("--no-whisper")
    if transcription_language:
        remote_cmd.extend(["--transcription-language", transcription_language])
    _run([*ssh_base, target, shlex.join(remote_cmd) + " >/dev/null"])

    _run(["rsync", "-a", "-e", _rsync_shell(port, key), f"{target}:{remote_result}/", f"{result_dir}/"])
    report_path = result_dir / "report.md"
    if report_path.exists():
        report_path.write_text(report_path.read_text(encoding="utf-8").replace(remote_result, str(result_dir)), encoding="utf-8")
    if not keep_remote:
        _run([*ssh_base, target, f"rm -rf {shlex.quote(remote_root)}"])
    return result_dir
