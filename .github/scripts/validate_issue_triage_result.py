#!/usr/bin/env python3
"""Validate issue triage agent output."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


PROTECTED_LABELS = {"plan-approved", "ready-to-implement", "ready-to-spec"}
REPRO_VALUES = {"high", "medium", "low", "unknown"}
CONFIDENCE_VALUES = {"high", "medium", "low"}
DUPLICATE_LABEL = "duplicate"
NEEDS_INFO_LABEL = "needs-info"
TRIAGED_LABEL = "triaged"


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"{path} was not created")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    return data


def configured_labels(context_path: Path | None) -> set[str]:
    if context_path is None:
        return set()
    context = load_json(context_path)
    config = context.get("triage_config") or {}
    labels = config.get("labels") or {}
    if not isinstance(labels, dict):
        raise SystemExit("triage_context.json field triage_config.labels must be an object")
    return {str(name) for name in labels}


def require_string_list(data: dict[str, Any], field: str) -> list[str]:
    value = data.get(field)
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise SystemExit(f"triage_result.json field {field} must be a list of non-empty strings")
    return value


def require_string(data: dict[str, Any], field: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise SystemExit(f"triage_result.json field {field} must be a non-empty string")
    return value


def validate_follow_up_questions(data: dict[str, Any]) -> list[dict[str, str]]:
    value = data.get("follow_up_questions")
    if not isinstance(value, list):
        raise SystemExit("triage_result.json field follow_up_questions must be a list")
    if len(value) > 5:
        raise SystemExit("follow_up_questions must contain at most 5 questions")
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise SystemExit(f"follow_up_questions[{index}] must be an object")
        question = item.get("question")
        reasoning = item.get("reasoning")
        if not isinstance(question, str) or not question.strip():
            raise SystemExit(f"follow_up_questions[{index}].question must be a non-empty string")
        if not isinstance(reasoning, str) or not reasoning.strip():
            raise SystemExit(f"follow_up_questions[{index}].reasoning must be a non-empty string")
    return value


def validate_duplicate_of(data: dict[str, Any]) -> list[dict[str, Any]]:
    value = data.get("duplicate_of")
    if not isinstance(value, list):
        raise SystemExit("triage_result.json field duplicate_of must be a list")
    seen: set[int] = set()
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise SystemExit(f"duplicate_of[{index}] must be an object")
        issue_number = item.get("issue_number")
        if not isinstance(issue_number, int) or issue_number <= 0:
            raise SystemExit(f"duplicate_of[{index}].issue_number must be a positive integer")
        if issue_number in seen:
            raise SystemExit(f"duplicate_of[{index}].issue_number is duplicated")
        seen.add(issue_number)
        for field in ("title", "similarity_reason"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                raise SystemExit(f"duplicate_of[{index}].{field} must be a non-empty string")
    if value and len(value) < 2:
        raise SystemExit("duplicate_of must contain at least 2 entries when populated")
    return value


def validate_labels(labels: list[str], allowed_labels: set[str]) -> None:
    protected = sorted(set(labels) & PROTECTED_LABELS)
    if protected:
        raise SystemExit("protected labels are not allowed in triage_result.json: " + ", ".join(protected))
    if allowed_labels:
        unknown = sorted(set(labels) - allowed_labels)
        if unknown:
            raise SystemExit("triage_result.json contains labels not present in triage config: " + ", ".join(unknown))


def validate_result(
    path: Path,
    *,
    require_issue_body: bool = False,
    context_path: Path | None = None,
) -> dict[str, Any]:
    data = load_json(path)
    allowed_labels = configured_labels(context_path)
    labels = require_string_list(data, "labels")
    validate_labels(labels, allowed_labels)

    repro = require_string(data, "repro")
    if repro not in REPRO_VALUES:
        raise SystemExit("triage_result.json field repro must be one of: " + ", ".join(sorted(REPRO_VALUES)))

    confidence = require_string(data, "confidence")
    if confidence not in CONFIDENCE_VALUES:
        raise SystemExit(
            "triage_result.json field confidence must be one of: "
            + ", ".join(sorted(CONFIDENCE_VALUES))
        )

    require_string_list(data, "related_files")
    require_string(data, "root_cause")
    require_string(data, "summary")
    follow_up_questions = validate_follow_up_questions(data)
    duplicate_of = validate_duplicate_of(data)

    if duplicate_of and follow_up_questions:
        raise SystemExit("duplicate_of and follow_up_questions are mutually exclusive")
    if duplicate_of and DUPLICATE_LABEL in allowed_labels and DUPLICATE_LABEL not in labels:
        raise SystemExit("triage_result.json must include the duplicate label when duplicate_of is populated")
    if duplicate_of and TRIAGED_LABEL in labels:
        raise SystemExit("triage_result.json must not include the triaged label when duplicate_of is populated")
    if follow_up_questions and NEEDS_INFO_LABEL in allowed_labels and NEEDS_INFO_LABEL not in labels:
        raise SystemExit("triage_result.json must include the needs-info label when follow_up_questions is populated")
    if not duplicate_of and not follow_up_questions and TRIAGED_LABEL in allowed_labels and TRIAGED_LABEL not in labels:
        raise SystemExit(
            "triage_result.json must include the triaged label when duplicate_of and follow_up_questions are empty"
        )

    issue_body = data.get("issue_body", "")
    if issue_body is None:
        issue_body = ""
    if not isinstance(issue_body, str):
        raise SystemExit("triage_result.json field issue_body must be a string when present")
    if require_issue_body and not issue_body.strip():
        raise SystemExit("triage_result.json field issue_body is required by the workflow")
    return data


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default="triage_result.json")
    parser.add_argument("--context", default="")
    parser.add_argument("--require-issue-body", action="store_true")
    args = parser.parse_args()
    validate_result(
        Path(args.path),
        require_issue_body=args.require_issue_body,
        context_path=Path(args.context) if args.context else None,
    )


if __name__ == "__main__":
    main()
