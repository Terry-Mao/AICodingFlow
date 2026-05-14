#!/usr/bin/env python3
"""Validate implementation workflow PR metadata."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from implementation_file_filters import TEMP_WORKFLOW_PATHS, is_generated_path


REQUIRED_METADATA_FIELDS = {"branch_name", "pr_title", "pr_summary", "intended_files"}
STRING_METADATA_FIELDS = {"branch_name", "pr_title", "pr_summary"}
CONVENTIONAL_TITLE_RE = re.compile(r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore)(\([a-z0-9._-]+\))?: .+")


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path} is invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    return value


def validate_metadata(metadata_path: Path, context_path: Path) -> dict[str, str]:
    if not metadata_path.exists():
        raise SystemExit("pr-metadata.json was not created")
    context = load_json(context_path)
    metadata = load_json(metadata_path)
    missing = sorted(REQUIRED_METADATA_FIELDS - set(metadata))
    if missing:
        raise SystemExit(f"pr-metadata.json is missing fields: {', '.join(missing)}")
    for field in STRING_METADATA_FIELDS:
        if not isinstance(metadata.get(field), str) or not metadata[field].strip():
            raise SystemExit(f"pr-metadata.json field {field} must be a non-empty string")
    intended_files = metadata.get("intended_files")
    if not isinstance(intended_files, list) or not intended_files:
        raise SystemExit("pr-metadata.json field intended_files must be a non-empty list")
    for index, path in enumerate(intended_files):
        if not isinstance(path, str) or not path.strip():
            raise SystemExit(f"pr-metadata.json intended_files[{index}] must be a non-empty string")
        if Path(path).is_absolute() or ".." in Path(path).parts:
            raise SystemExit(f"pr-metadata.json intended_files[{index}] must be a repository-relative path")
        if path in TEMP_WORKFLOW_PATHS:
            raise SystemExit(f"pr-metadata.json intended_files[{index}] must not include workflow handoff files")
        if is_generated_path(path):
            raise SystemExit(f"pr-metadata.json intended_files[{index}] must not include generated/cache files")

    branch_name = metadata["branch_name"].strip()
    target_branch = str(context.get("target_branch") or "").strip()
    branch_prefix = str(context.get("implementation_branch_prefix") or target_branch).strip()
    if not target_branch:
        raise SystemExit("issue_context.json target_branch is required")

    if context.get("spec_context_source") == "approved-pr":
        if branch_name != target_branch:
            raise SystemExit("approved spec PR implementations must keep pr-metadata.json branch_name equal to target_branch")
    elif branch_name != target_branch and not branch_name.startswith(f"{branch_prefix}-"):
        raise SystemExit(
            "standalone implementation branch_name must equal target_branch or start with "
            f"{branch_prefix}-"
        )

    if not CONVENTIONAL_TITLE_RE.match(metadata["pr_title"]):
        raise SystemExit("pr-metadata.json pr_title must use conventional commit style")

    issue_number = context.get("issue_number")
    expected_first_line = f"Closes #{issue_number}"
    first_line = metadata["pr_summary"].splitlines()[0] if metadata["pr_summary"].splitlines() else ""
    if first_line != expected_first_line:
        raise SystemExit(f"pr-metadata.json pr_summary first line must be exactly {expected_first_line!r}")
    if "\n" not in metadata["pr_summary"]:
        raise SystemExit("pr-metadata.json pr_summary must be a complete markdown body, not a one-line note")

    return {field: metadata[field] for field in REQUIRED_METADATA_FIELDS}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", default="issue_context.json")
    parser.add_argument("--metadata", default="pr-metadata.json")
    args = parser.parse_args()
    validate_metadata(Path(args.metadata), Path(args.context))


if __name__ == "__main__":
    main()
