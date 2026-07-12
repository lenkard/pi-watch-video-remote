#!/usr/bin/env python3
"""Fetch a gated URL on a remote browser host and rsync it locally."""
from __future__ import annotations

import shlex
import subprocess
import uuid
from pathlib import Path

from config import config_value, int_config, truthy

DEFAULT_FETCH_SCRIPT = "/usr/local/bin/fetch-url"
DEFAULT_JOBS_DIR = "/opt/pi-watch-video/browser/data/jobs"


def remote_fetch_enabled() -> bool:
    return (config_value("PI_WATCH_FETCH_MODE") or "").strip().lower() == "remote_browser"


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


def fetch_url(url: str, local_dir: Path) -> Path:
    ssh_base, target, port, key = _ssh_target("FETCH")
    container = _required("PI_WATCH_REMOTE_FETCH_CONTAINER")
    host_jobs_dir = config_value("PI_WATCH_REMOTE_FETCH_HOST_JOBS_DIR") or DEFAULT_JOBS_DIR
    fetch_script = config_value("PI_WATCH_REMOTE_FETCH_SCRIPT") or DEFAULT_FETCH_SCRIPT
    keep_remote = truthy(config_value("PI_WATCH_REMOTE_FETCH_KEEP"), False)
    job_id = f"job-{uuid.uuid4().hex[:12]}"
    local_dir = Path(local_dir).expanduser().resolve()
    local_dir.mkdir(parents=True, exist_ok=True)

    remote_cmd = "docker exec {container} {script} {url} {job} >/dev/null".format(
        container=shlex.quote(container),
        script=shlex.quote(fetch_script),
        url=shlex.quote(url),
        job=shlex.quote(job_id),
    )
    _run([*ssh_base, target, remote_cmd])
    _run(["rsync", "-a", "-e", _rsync_shell(port, key), f"{target}:{host_jobs_dir.rstrip('/')}/{job_id}/", f"{local_dir}/"])
    if not keep_remote:
        _run([*ssh_base, target, f"rm -rf {shlex.quote(host_jobs_dir.rstrip('/') + '/' + job_id)}"])
    return local_dir
