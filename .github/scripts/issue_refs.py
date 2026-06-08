"""Shared issue reference parsing helpers."""

from __future__ import annotations

import re
from typing import Any


EXPLICIT_ISSUE_PATTERNS = [
    re.compile(r"(?<![A-Za-z0-9-])(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?|refs?)\s+#(\d+)", re.IGNORECASE),
    re.compile(r"(?<![A-Za-z0-9-])(?:issue|gh)(?![A-Za-z0-9-])[-/\s#]*(\d+)", re.IGNORECASE),
    re.compile(r"(?<![A-Za-z0-9-])#(\d+)", re.IGNORECASE),
]
STRICT_ISSUE_PATTERNS = [
    re.compile(r"(?<![A-Za-z0-9-])(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?|refs?)\s+#(\d+)", re.IGNORECASE),
    re.compile(r"(?<![A-Za-z0-9-])issue(?![A-Za-z0-9-])\s+#?(\d+)(?![A-Za-z0-9-])", re.IGNORECASE),
]
BRANCH_SUFFIX_RE = re.compile(r"(?:^|/)[A-Za-z0-9-]+-(\d+)$")
ISSUE_REFERENCE_KEYWORD_RE = re.compile(
    r"\b(?:refs?|references?|relates\s+to|fixes?|closes?|resolves?)\b[:\s]+[^\n\r]*",
    re.IGNORECASE,
)
ISSUE_NUMBER_RE = re.compile(r"#(\d+)\b")
PULL_REQUEST_REFERENCE_PREFIX_RE = re.compile(r"(?:\bPR|\bpull\s+request)\s*$", re.IGNORECASE)


def issue_number_from_text(text: str, *, include_branch_suffix: bool = True) -> int | None:
    value = text or ""
    for pattern in EXPLICIT_ISSUE_PATTERNS:
        match = pattern.search(value)
        if match:
            return int(match.group(1))
    if include_branch_suffix:
        match = BRANCH_SUFFIX_RE.search(value)
        if match:
            return int(match.group(1))
    return None


def issue_number_from_strict_text(text: str) -> int | None:
    value = text or ""
    for pattern in STRICT_ISSUE_PATTERNS:
        match = pattern.search(value)
        if match:
            return int(match.group(1))
    return None


def issue_number_from_branch(branch: str, *, prefix: str = "spec/issue-", include_suffix: bool = True) -> int | None:
    value = branch or ""
    if prefix and value.startswith(prefix):
        suffix = value.removeprefix(prefix)
        return int(suffix) if suffix.isdigit() else None
    if not include_suffix:
        return None
    match = BRANCH_SUFFIX_RE.search(value)
    return int(match.group(1)) if match else None


def resolve_issue_number_from_pr(pr: dict[str, Any]) -> int | None:
    for text in (
        pr.get("body") or "",
        pr.get("title") or "",
        (pr.get("head") or {}).get("ref") or pr.get("headRefName") or "",
    ):
        issue_number = issue_number_from_text(str(text))
        if issue_number is not None:
            return issue_number
    return None


def issue_numbers_from_closing_refs(pr: dict[str, Any]) -> list[int]:
    numbers: list[int] = []

    def add_number(value: Any) -> None:
        try:
            number = int(value)
        except (TypeError, ValueError):
            return
        if number not in numbers:
            numbers.append(number)

    for issue in pr.get("closingIssuesReferences") or []:
        if isinstance(issue, dict):
            add_number(issue.get("number"))
    for text in (pr.get("title") or "", pr.get("body") or ""):
        for match in ISSUE_REFERENCE_KEYWORD_RE.finditer(str(text)):
            reference_text = match.group(0)
            for number_match in ISSUE_NUMBER_RE.finditer(reference_text):
                if PULL_REQUEST_REFERENCE_PREFIX_RE.search(reference_text[: number_match.start()]):
                    continue
                add_number(number_match.group(1))
    return numbers
