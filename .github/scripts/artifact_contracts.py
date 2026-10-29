"""Shared artifact helpers for GitHub workflow scripts."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any


def load_json(path: str | Path | None, *, default: Any = None) -> Any:
    if not path:
        return default
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, payload: Any, *, ensure_ascii: bool = False) -> None:
    Path(path).write_text(json.dumps(payload, ensure_ascii=ensure_ascii, indent=2) + "\n", encoding="utf-8")


def write_github_output(path: str | Path | None, values: dict[str, str]) -> None:
    if not path:
        return
    with Path(path).open("a", encoding="utf-8") as handle:
        for key, value in values.items():
            if "\n" not in value and "\r" not in value:
                handle.write(f"{key}={value}\n")
                continue
            lines = set(value.splitlines())
            delimiter = f"ghadelimiter_{uuid.uuid4().hex}"
            while delimiter in lines:
                delimiter = f"ghadelimiter_{uuid.uuid4().hex}"
            handle.write(f"{key}<<{delimiter}\n{value}\n{delimiter}\n")
