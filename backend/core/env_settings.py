# reads and writes the .env file used by the running process (the settings page edits it)
# MONITORING_ENV_FILE points to the file, in dev it is backend/.env and in production backend/.env.prod
# comments, blank lines and keys that are not changed are kept as they are

import os
import re
from pathlib import Path

_DEFAULT_ENV_FILENAME = ".env" if os.getenv("DEBUG") == "True" else ".env.prod"

ENV_PATH = Path(
    os.getenv("MONITORING_ENV_FILE")
    or (Path(__file__).resolve().parent.parent / _DEFAULT_ENV_FILENAME)
)

# matches KEY=value and export KEY=value lines, the value can still have quotes
_KV_RE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$")


# removes the quotes around a value
def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


# adds quotes to a value only when it has spaces, # or quotes
def _quote(value: str) -> str:
    if value == "" or re.search(r"[\s#\"']", value):
        escaped = value.replace('"', '\\"')
        return f'"{escaped}"'
    return value


# reads every KEY=VALUE line of the .env file into a dict
def read_env(path: Path | None = None) -> dict:
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


# rewrites the .env file, changing only the keys that were given and keeping the rest
def write_env(updates: dict, path: Path | None = None) -> None:
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
