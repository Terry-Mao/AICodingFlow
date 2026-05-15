#!/usr/bin/env python3
"""Validate review.json against PR_DIFF_V1 line annotations."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


SEVERITIES = (
    "🚨 [CRITICAL]",
    "⚠️ [IMPORTANT]",
    "💡 [SUGGESTION]",
    "🧹 [NIT]",
)
VERDICTS = ("APPROVE", "REJECT")

FILE_RE = re.compile(r"^FILE\s+(.+?)\s*$")
LINE_RE = re.compile(r"^(LEFT|RIGHT|BOTH)\s+(\d+)\s+\|")


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def parse_diff(path: Path) -> dict[tuple[str, str], set[int]]:
    allowed: dict[tuple[str, str], set[int]] = {}
    current_file: str | None = None

    for index, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        file_match = FILE_RE.match(raw_line)
        if file_match:
            current_file = file_match.group(1).strip()
            if not current_file:
                fail(f"{path}:{index}: empty FILE path")
            continue

        if raw_line == "END_FILE":
            current_file = None
            continue

        line_match = LINE_RE.match(raw_line)
        if not line_match:
            continue
        if current_file is None:
            fail(f"{path}:{index}: line annotation outside FILE section")

        side, number_text = line_match.groups()
        if side == "BOTH":
            continue
        allowed.setdefault((current_file, side), set()).add(int(number_text))

    return allowed


def require_type(value: Any, expected: type, label: str) -> None:
    if type(value) is not expected:
        fail(f"{label} must be {expected.__name__}")


def validate_comment(comment: Any, index: int, allowed: dict[tuple[str, str], set[int]]) -> None:
    label = f"comments[{index}]"
    require_type(comment, dict, label)

    for key in ("path", "side", "line", "body"):
        if key not in comment:
            fail(f"{label}.{key} is required")

    path = comment["path"]
    side = comment["side"]
    line = comment["line"]
    body = comment["body"]

    require_type(path, str, f"{label}.path")
    require_type(side, str, f"{label}.side")
    require_type(line, int, f"{label}.line")
    require_type(body, str, f"{label}.body")

    if side not in ("LEFT", "RIGHT"):
        fail(f"{label}.side must be LEFT or RIGHT")
    if line <= 0:
        fail(f"{label}.line must be positive")
    if not any(body.startswith(severity) for severity in SEVERITIES):
        fail(f"{label}.body must start with a required severity label")

    changed_lines = allowed.get((path, side), set())
    if line not in changed_lines:
        fail(f"{label} targets {path}/{side}/{line}, which is not a changed diff line")

    start_line = comment.get("start_line")
    if start_line is not None:
        require_type(start_line, int, f"{label}.start_line")
        if start_line <= 0:
            fail(f"{label}.start_line must be positive")
        if start_line > line:
            fail(f"{label}.start_line must be <= line")
        if line - start_line + 1 > 10:
            fail(f"{label} range must not exceed 10 lines")
        missing = [number for number in range(start_line, line + 1) if number not in changed_lines]
        if missing:
            fail(f"{label} range includes unchanged or missing {path}/{side} lines: {missing}")

    has_suggestion = "```suggestion\n" in body
    if body.startswith("🧹 [NIT]") and not has_suggestion:
        fail(f"{label} uses NIT without a suggestion block")
    if has_suggestion:
        if side != "RIGHT":
            fail(f"{label} has a suggestion block but side is not RIGHT")
        if body.count("```suggestion\n") != 1:
            fail(f"{label} must contain exactly one suggestion block opener")
        if body.count("```") < 2:
            fail(f"{label} suggestion block is not closed")


def validate_reviewers(reviewers: Any) -> None:
    require_type(reviewers, list, "review.recommended_reviewers")
    if len(reviewers) > 1:
        fail("review.recommended_reviewers must contain at most 1 reviewer")
    for index, reviewer in enumerate(reviewers):
        require_type(reviewer, str, f"review.recommended_reviewers[{index}]")


def main() -> None:
    if len(sys.argv) != 3:
        fail("usage: validate_review_json.py <pr_diff.txt> <review.json>")

    diff_path = Path(sys.argv[1])
    review_path = Path(sys.argv[2])
    if not diff_path.exists():
        fail(f"missing diff file: {diff_path}")
    if not review_path.exists():
        fail(f"missing review file: {review_path}")

    allowed = parse_diff(diff_path)
    try:
        review = json.loads(review_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"review.json is not valid JSON: {exc}")
    require_type(review, dict, "review")

    allowed_keys = {"verdict", "body", "comments", "recommended_reviewers"}
    if set(review) - allowed_keys:
        fail(f"review contains unknown keys: {sorted(set(review) - allowed_keys)}")
    for key in ("verdict", "body", "comments"):
        if key not in review:
            fail(f"review.{key} is required")

    require_type(review["verdict"], str, "review.verdict")
    if review["verdict"] not in VERDICTS:
        fail("review.verdict must be APPROVE or REJECT")
    require_type(review["body"], str, "review.body")
    require_type(review["comments"], list, "review.comments")
    if "recommended_reviewers" in review:
        validate_reviewers(review["recommended_reviewers"])

    for index, comment in enumerate(review["comments"]):
        validate_comment(comment, index, allowed)

    print("OK")


if __name__ == "__main__":
    main()
