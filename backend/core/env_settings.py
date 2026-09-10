"""
Read/write backend/.env directly.

This is deliberately the ONLY store for the runtime configuration exposed
on the Settings page (MQTT connection, reconciliation timing, heartbeat
and alert retention) -- there is no parallel settings table in the
database. The .env file stays the single source of truth; the Settings
page is just a friendlier way to edit it.

Comments, blank lines, and any key this app doesn't ask to change are
copied through completely untouched when saving.
"""

import os
import re
from pathlib import Path

ENV_PATH = Path(
    os.getenv("MONITORING_ENV_FILE") or (Path(__file__).resolve().parent.parent / ".env")
)

# Matches "KEY=value" / "export KEY=value" lines, capturing the key and
# the (still possibly quoted) raw value.
_KV_RE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$")


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def _quote(value: str) -> str:
    """Quote a value only when it actually needs it (spaces, #, quotes)."""

    if value == "" or re.search(r"[\s#\"']", value):
        escaped = value.replace('"', '\\"')
        return f'"{escaped}"'
    return value


def read_env(path: Path | None = None) -> dict:
    """Parse every KEY=VALUE line in the .env file into a plain dict."""

    path = path or ENV_PATH
    values: dict[str, str] = {}

    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()

        if not stripped or stripped.startswith("#"):
            continue

        match = _KV_RE.match(raw_line)

        if not match:
            continue

        key, value = match.groups()
        values[key] = _strip_quotes(value)

    return values


def write_env(updates: dict, path: Path | None = None) -> None:
    """
    Rewrite backend/.env, replacing only the lines for keys present in
    `updates` (a {ENV_KEY: value} dict). Every comment, blank line, and
    every key not in `updates` is copied through unchanged. Keys in
    `updates` that don't already exist in the file are appended at the end.
    """

    path = path or ENV_PATH

    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []

    remaining = {key: str(value) for key, value in updates.items()}
    new_lines = []

    for raw_line in lines:
        stripped = raw_line.strip()

        if not stripped or stripped.startswith("#"):
            new_lines.append(raw_line)
            continue

        match = _KV_RE.match(raw_line)

        if not match:
            new_lines.append(raw_line)
            continue

        key = match.group(1)

        if key in remaining:
            new_lines.append(f"{key}={_quote(remaining.pop(key))}")
        else:
            new_lines.append(raw_line)

    for key, value in remaining.items():
        new_lines.append(f"{key}={_quote(value)}")

    path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
