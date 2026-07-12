#!/usr/bin/env python3
"""Shared config helpers for pi-watch-video scripts."""
from __future__ import annotations

import os
from pathlib import Path

CONFIG_FILE = Path.home() / ".config" / "pi-watch-video" / ".env"


def dotenv_value(path: Path, key: str) -> str | None:
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
        value = os.environ.get(name) or dotenv_value(CONFIG_FILE, name) or dotenv_value(Path.cwd() / ".env", name)
        if value and value.strip():
            return value.strip()
    return None


def int_config(default: int, *names: str) -> int:
    value = config_value(*names)
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def truthy(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
