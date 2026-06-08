#!/usr/bin/env python3
"""Validate implementation workflow PR metadata."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from pr_metadata_contracts import (  # noqa: E402
    BASE_METADATA_FIELDS,
    load_json_object,
    validate_base_metadata,
    validate_intended_files,
)

REQUIRED_METADATA_FIELDS = {*BASE_METADATA_FIELDS, "intended_files"}


def load_json(path: Path) -> dict[str, Any]:
    return load_json_object(path)


def validate_metadata(metadata_path: Path, context_path: Path) -> dict[str, str]:
    if not metadata_path.exists():
        raise SystemExit("pr-metadata.json was not created")
    context = load_json(context_path)
    metadata = load_json(metadata_path)
    validate_base_metadata(metadata, required_fields=REQUIRED_METADATA_FIELDS)
    validate_intended_files(metadata)

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

    issue_number = context.get("issue_number")
    expected_first_line = f"Closes #{issue_number}"
    first_line = metadata["pr_summary"].splitlines()[0] if metadata["pr_summary"].splitlines() else ""
    if first_line != expected_first_line:
        raise SystemExit(f"pr-metadata.json pr_summary first line must be exactly {expected_first_line!r}")
    return {field: metadata[field] for field in REQUIRED_METADATA_FIELDS}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", default="issue_context.json")
    parser.add_argument("--metadata", default="pr-metadata.json")
    args = parser.parse_args()
    validate_metadata(Path(args.metadata), Path(args.context))


if __name__ == "__main__":
    main()
