#!/usr/bin/env python3
"""Validate respond-to-pr-comment agent outputs."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from commit_implementation_branch import implementation_paths, status_paths  # noqa: E402
from implementation_file_filters import TEMP_WORKFLOW_PATHS, is_generated_path  # noqa: E402


REQUIRED_METADATA_FIELDS = {"branch_name", "pr_title", "pr_summary", "intended_files"}
STRING_METADATA_FIELDS = {"branch_name", "pr_title", "pr_summary"}
CONVENTIONAL_TITLE_RE = re.compile(r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore)(\([a-z0-9._-]+\))?: .+")
SENTENCE_END_RE = re.compile(r"[.!?](?:\s+|$)")


def load_json(path: Path, *, required: bool = True) -> dict[str, Any]:
    if not path.exists():
        if required:
            raise SystemExit(f"{path} was not created")
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path} is invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    return value


def validate_intended_path(path: object, index: int) -> str:
    if not isinstance(path, str) or not path.strip():
        raise SystemExit(f"pr-metadata.json intended_files[{index}] must be a non-empty string")
    normalized = path.strip()
    if Path(normalized).is_absolute() or ".." in Path(normalized).parts:
        raise SystemExit(f"pr-metadata.json intended_files[{index}] must be a repository-relative path")
    if normalized in TEMP_WORKFLOW_PATHS:
        raise SystemExit(f"pr-metadata.json intended_files[{index}] must not include workflow handoff files")
    if is_generated_path(normalized):
        raise SystemExit(f"pr-metadata.json intended_files[{index}] must not include generated/cache files")
    return normalized


def validate_metadata(metadata_path: Path, context_path: Path, candidate_paths: list[str] | None = None) -> dict[str, Any]:
    context = load_json(context_path)
    metadata = load_json(metadata_path)
    missing = sorted(REQUIRED_METADATA_FIELDS - set(metadata))
    if missing:
        raise SystemExit(f"pr-metadata.json is missing fields: {', '.join(missing)}")
    for field in STRING_METADATA_FIELDS:
        if not isinstance(metadata.get(field), str) or not metadata[field].strip():
            raise SystemExit(f"pr-metadata.json field {field} must be a non-empty string")
    if metadata["branch_name"].strip() != str(context.get("agent_push_branch") or "").strip():
        raise SystemExit("pr-metadata.json branch_name must equal pr_comment_context.json agent_push_branch")
    if not CONVENTIONAL_TITLE_RE.match(metadata["pr_title"]):
        raise SystemExit("pr-metadata.json pr_title must use conventional commit style")
    if "\n" not in metadata["pr_summary"]:
        raise SystemExit("pr-metadata.json pr_summary must be a complete markdown body, not a one-line note")

    raw_files = metadata.get("intended_files")
    if not isinstance(raw_files, list) or not raw_files:
        raise SystemExit("pr-metadata.json field intended_files must be a non-empty list")
    intended = sorted(dict.fromkeys(validate_intended_path(path, index) for index, path in enumerate(raw_files)))

    candidates = implementation_paths(candidate_paths if candidate_paths is not None else status_paths())
    missing_changes = sorted(set(intended) - set(candidates))
    unexpected = sorted(set(candidates) - set(intended))
    if missing_changes:
        raise SystemExit("intended_files contains files without PR comment changes: " + ", ".join(missing_changes))
    if unexpected:
        raise SystemExit("PR comment changed files not listed in intended_files: " + ", ".join(unexpected))
    return metadata


def valid_review_comment_ids(index: dict[str, Any]) -> set[int]:
    comments = index.get("review_comments") or []
    ids: set[int] = set()
    if not isinstance(comments, list):
        raise SystemExit("review_comment_ids.json field review_comments must be a list")
    for item in comments:
        if isinstance(item, dict) and isinstance(item.get("comment_id"), int):
            ids.add(item["comment_id"])
    return ids


def validate_resolved_comments(resolved_path: Path, review_comment_ids_path: Path) -> None:
    if not resolved_path.exists():
        return
    resolved = load_json(resolved_path)
    index = load_json(review_comment_ids_path)
    valid_ids = valid_review_comment_ids(index)
    entries = resolved.get("resolved_review_comments")
    if not isinstance(entries, list):
        raise SystemExit("resolved_review_comments.json field resolved_review_comments must be a list")
    seen: set[int] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise SystemExit(f"resolved_review_comments[{index}] must be an object")
        comment_id = entry.get("comment_id")
        if not isinstance(comment_id, int):
            raise SystemExit(f"resolved_review_comments[{index}].comment_id must be an integer")
        if comment_id not in valid_ids:
            raise SystemExit(f"resolved_review_comments[{index}].comment_id is not a current PR review comment id")
        if comment_id in seen:
            raise SystemExit(f"resolved_review_comments[{index}].comment_id is duplicated")
        seen.add(comment_id)
        summary = entry.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            raise SystemExit(f"resolved_review_comments[{index}].summary must be a non-empty string")
        sentence_count = len(SENTENCE_END_RE.findall(summary.strip())) or 1
        if sentence_count > 3:
            raise SystemExit(f"resolved_review_comments[{index}].summary must be 1-3 sentences")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", default="pr_comment_context.json")
    parser.add_argument("--metadata", default="pr-metadata.json")
    parser.add_argument("--resolved", default="resolved_review_comments.json")
    parser.add_argument("--review-comment-ids", default="review_comment_ids.json")
    args = parser.parse_args()

    validate_metadata(Path(args.metadata), Path(args.context))
    validate_resolved_comments(Path(args.resolved), Path(args.review_comment_ids))


if __name__ == "__main__":
    main()
