"""Shared validation helpers for agent-authored PR metadata."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from implementation_file_filters import TEMP_WORKFLOW_PATHS, is_generated_path


CONVENTIONAL_TITLE_RE = re.compile(r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore)(\([a-z0-9._-]+\))?: .+")
BASE_METADATA_FIELDS = {"branch_name", "pr_title", "pr_summary"}
INTENDED_FILES_FIELD = "intended_files"


def load_json_object(path: Path, *, required: bool = True, display_name: str | None = None) -> dict[str, Any]:
    name = display_name or str(path)
    if not path.exists():
        if required:
            raise SystemExit(f"{name} was not created")
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{name} is invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit(f"{name} must contain a JSON object")
    return value


def require_fields(metadata: dict[str, Any], required: set[str], *, display_name: str = "pr-metadata.json") -> None:
    missing = sorted(required - set(metadata))
    if missing:
        raise SystemExit(f"{display_name} is missing fields: {', '.join(missing)}")


def require_non_empty_strings(
    metadata: dict[str, Any],
    fields: set[str],
    *,
    display_name: str = "pr-metadata.json",
) -> None:
    for field in fields:
        if not isinstance(metadata.get(field), str) or not metadata[field].strip():
            raise SystemExit(f"{display_name} field {field} must be a non-empty string")


def require_conventional_title(title: str, *, display_name: str = "pr-metadata.json") -> None:
    if not CONVENTIONAL_TITLE_RE.match(title):
        raise SystemExit(f"{display_name} pr_title must use conventional commit style")


def require_markdown_summary(summary: str, *, display_name: str = "pr-metadata.json") -> None:
    if "\n" not in summary:
        raise SystemExit(f"{display_name} pr_summary must be a complete markdown body, not a one-line note")


def validate_base_metadata(
    metadata: dict[str, Any],
    *,
    required_fields: set[str] | None = None,
    string_fields: set[str] | None = None,
    display_name: str = "pr-metadata.json",
) -> None:
    required = required_fields or BASE_METADATA_FIELDS
    strings = string_fields or BASE_METADATA_FIELDS
    require_fields(metadata, required, display_name=display_name)
    require_non_empty_strings(metadata, strings, display_name=display_name)
    require_conventional_title(metadata["pr_title"], display_name=display_name)
    require_markdown_summary(metadata["pr_summary"], display_name=display_name)


def validate_intended_path(path: object, index: int, *, display_name: str = "pr-metadata.json") -> str:
    if not isinstance(path, str) or not path.strip():
        raise SystemExit(f"{display_name} intended_files[{index}] must be a non-empty string")
    normalized = path.strip()
    if Path(normalized).is_absolute() or ".." in Path(normalized).parts:
        raise SystemExit(f"{display_name} intended_files[{index}] must be a repository-relative path")
    if normalized in TEMP_WORKFLOW_PATHS:
        raise SystemExit(f"{display_name} intended_files[{index}] must not include workflow handoff files")
    if is_generated_path(normalized):
        raise SystemExit(f"{display_name} intended_files[{index}] must not include generated/cache files")
    return normalized


def validate_intended_files(metadata: dict[str, Any], *, display_name: str = "pr-metadata.json") -> list[str]:
    raw_files = metadata.get(INTENDED_FILES_FIELD)
    if not isinstance(raw_files, list) or not raw_files:
        raise SystemExit(f"{display_name} field intended_files must be a non-empty list")
    return [validate_intended_path(path, index, display_name=display_name) for index, path in enumerate(raw_files)]
