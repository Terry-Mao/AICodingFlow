#!/usr/bin/env python3
"""Validate generated issue spec files and PR metadata."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from pr_metadata_contracts import BASE_METADATA_FIELDS, load_json_object, validate_base_metadata  # noqa: E402


REQUIRED_METADATA_FIELDS = BASE_METADATA_FIELDS


def load_context(path: Path) -> dict[str, object]:
    return load_json_object(path)


def validate_metadata(path: Path, branch_name: str, issue_number: int | None = None) -> dict[str, str]:
    if not path.exists():
        raise SystemExit("pr-metadata.json was not created")
    metadata = load_json_object(path, display_name="pr-metadata.json")
    validate_base_metadata(metadata, required_fields=REQUIRED_METADATA_FIELDS)
    if metadata["branch_name"] != branch_name:
        raise SystemExit(
            f"pr-metadata.json branch_name must be {branch_name!r}, got {metadata['branch_name']!r}"
        )
    if issue_number is not None and f"Refs #{issue_number}" not in metadata["pr_summary"]:
        raise SystemExit(f"pr-metadata.json pr_summary must include Refs #{issue_number}")
    return metadata


def validate_spec_file(path: Path) -> None:
    if not path.exists():
        raise SystemExit(f"{path} was not created")
    if not path.is_file():
        raise SystemExit(f"{path} is not a file")
    text = path.read_text(encoding="utf-8").strip()
    if len(text) < 200:
        raise SystemExit(f"{path} is too short to be a useful spec")


def changed_paths() -> set[str]:
    result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    paths: set[str] = set()
    for line in result.stdout.splitlines():
        if not line:
            continue
        path_text = line[3:]
        if " -> " in path_text:
            path_text = path_text.rsplit(" -> ", 1)[1]
        paths.add(path_text)
    return paths


def is_ignored_generated_path(path: str) -> bool:
    parts = Path(path).parts
    return (
        bool(parts and parts[0] == ".codex-runtime")
        or "__pycache__" in parts
        or path.endswith((".pyc", ".pyo"))
    )


def validate_write_surface(allowed_paths: set[str]) -> None:
    unexpected = sorted(
        path for path in changed_paths() - allowed_paths if not is_ignored_generated_path(path)
    )
    if unexpected:
        raise SystemExit("unexpected files changed: " + ", ".join(unexpected))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", default="issue_context.json")
    parser.add_argument("--metadata", default="pr-metadata.json")
    args = parser.parse_args()

    context = load_context(Path(args.context))
    product_spec = Path(str(context["product_spec"]))
    tech_spec = Path(str(context["tech_spec"]))
    branch_name = str(context.get("target_branch") or context["branch_name"])
    issue_number = int(dict(context["issue"])["number"])

    validate_spec_file(product_spec)
    validate_spec_file(tech_spec)
    validate_metadata(Path(args.metadata), branch_name, issue_number)
    validate_write_surface(
        {
            str(product_spec),
            str(tech_spec),
            args.metadata,
            args.context,
            "issue_comments.txt",
        }
    )


if __name__ == "__main__":
    main()
