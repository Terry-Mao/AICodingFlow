#!/usr/bin/env python3
"""Shared path filters for implementation workflow outputs."""

from __future__ import annotations

from pathlib import Path


TEMP_WORKFLOW_PATHS = {
    "issue_context.json",
    "issue_comments.txt",
    "spec_context.md",
    "branch-start-shas.json",
    "implementation_summary.md",
    "pr-metadata.json",
    "pr_comment_context.json",
    "pr_event.json",
    "pr_description.md",
    "pr_description.txt",
    "pr_diff.txt",
    "review_discussion_context.json",
    "review.json",
    "review_comment_ids.json",
    "resolved_review_comments.json",
    ".local_review_baseline.status",
    "validation-output.txt",
    "validation-error.txt",
}

RUNTIME_WORKFLOW_DIRS = {".codex-runtime", "implementation-output"}


def is_generated_path(path: str) -> bool:
    parts = Path(path).parts
    return (
        bool(parts and parts[0] in RUNTIME_WORKFLOW_DIRS)
        or "__pycache__" in parts
        or ".pytest_cache" in parts
        or ".mypy_cache" in parts
        or ".ruff_cache" in parts
        or path.endswith((".pyc", ".pyo", ".pyd"))
    )


def is_github_workflow_path(path: str) -> bool:
    parts = Path(path).parts
    return len(parts) >= 3 and parts[0] == ".github" and parts[1] == "workflows"
