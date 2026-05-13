#!/usr/bin/env python3
"""Validate generated issue spec files and PR metadata."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path


REQUIRED_METADATA_FIELDS = {"branch_name", "pr_title", "pr_summary"}
CONVENTIONAL_TITLE_RE = re.compile(r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore)(\([a-z0-9._-]+\))?: .+")


def load_context(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_metadata(path: Path, branch_name: str, issue_number: int | None = None) -> dict[str, str]:
    if not path.exists():
        raise SystemExit("pr-metadata.json was not created")
    try:
        metadata = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"pr-metadata.json is invalid JSON: {exc}") from exc
    if not isinstance(metadata, dict):
        raise SystemExit("pr-metadata.json must contain a JSON object")
    missing = sorted(REQUIRED_METADATA_FIELDS - set(metadata))
    if missing:
        raise SystemExit(f"pr-metadata.json is missing fields: {', '.join(missing)}")
    for field in REQUIRED_METADATA_FIELDS:
        if not isinstance(metadata.get(field), str) or not metadata[field].strip():
            raise SystemExit(f"pr-metadata.json field {field} must be a non-empty string")
    if metadata["branch_name"] != branch_name:
        raise SystemExit(
            f"pr-metadata.json branch_name must be {branch_name!r}, got {metadata['branch_name']!r}"
        )
    if not CONVENTIONAL_TITLE_RE.match(metadata["pr_title"]):
        raise SystemExit("pr-metadata.json pr_title must use conventional commit style")
    if issue_number is not None and f"Refs #{issue_number}" not in metadata["pr_summary"]:
        raise SystemExit(f"pr-metadata.json pr_summary must include Refs #{issue_number}")
    if "\n" not in metadata["pr_summary"]:
        raise SystemExit("pr-metadata.json pr_summary must be a complete markdown body, not a one-line note")
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
    return "__pycache__" in parts or path.endswith((".pyc", ".pyo"))


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
