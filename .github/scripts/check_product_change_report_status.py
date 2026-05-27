#!/usr/bin/env python3
"""Classify generated product change report output for workflow gating."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any


NO_CHANGE_PLACEHOLDER_PATTERN = re.compile(
    r"(?:no[\s-]+(?:reportable[\s-]+)?(?:product[\s-]+)?changes(?:[\s\w-]*merged[\s\w-]*window)?"
    r"|no[\s-]+update[\s-]+report[\s-]+needed"
    r"|nothing[\s-]+to[\s-]+report"
    r"|empty[\s-]+report)[\s.。!！]*",
    re.IGNORECASE,
)
COMMIT_ID_PATTERN = re.compile(
    r"\bcommit\s+`?[0-9a-f]{7,40}`?\b"
    r"|(?<![0-9A-Za-z])(?=[0-9a-f]{7,40}(?![0-9A-Za-z]))[0-9a-f]*[a-f][0-9a-f]*(?![0-9A-Za-z])",
    re.IGNORECASE,
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_git(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def is_tracked(path: Path) -> bool:
    return run_git(["ls-files", "--error-unmatch", str(path)]).returncode == 0


def has_worktree_change(path: Path) -> bool:
    result = run_git(["status", "--porcelain", "--", str(path)])
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or f"git status failed for {path}")
    return bool(result.stdout.strip())


def report_references_pr(report_text: str, pr: dict[str, Any]) -> bool:
    number = int(pr.get("number") or 0)
    url = str(pr.get("url") or "")
    if url and url in report_text:
        return True
    return bool(re.search(rf"(?<!\d)#\s*{number}(?!\d)|\bPR\s*#?\s*{number}\b", report_text, re.IGNORECASE))


def current_prs_are_referenced(report_text: str, context: dict[str, Any]) -> bool:
    prs = context.get("reportable_prs") or []
    return bool(prs) and all(report_references_pr(report_text, pr) for pr in prs)


def linked_issues(context: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    seen: set[int] = set()
    for pr in context.get("reportable_prs") or []:
        for issue in pr.get("closingIssuesReferences") or []:
            try:
                number = int(issue.get("number"))
            except (TypeError, ValueError):
                continue
            if number in seen:
                continue
            seen.add(number)
            issues.append({"number": number, "url": str(issue.get("url") or "")})
    return issues


def validate_report_references(report_text: str, context: dict[str, Any]) -> None:
    if COMMIT_ID_PATTERN.search(report_text):
        raise SystemExit("product change report must not include commit IDs")

    for issue in linked_issues(context):
        number = issue["number"]
        url = issue["url"]
        mentions_issue = bool(
            re.search(rf"(?<!\d)#\s*{number}(?!\d)|\bissue\s*#?\s*{number}\b", report_text, re.IGNORECASE)
        )
        if mentions_issue and url and url not in report_text:
            raise SystemExit(f"related issue #{number} must reference the issue URL: {url}")


def placeholder_body(report_text: str) -> str:
    body_lines: list[str] = []
    for line in report_text.strip().splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        if stripped.lower().startswith("scan window:"):
            continue
        body_lines.append(stripped)
    return " ".join(body_lines).strip()


def is_no_change_placeholder(report_text: str) -> bool:
    body = placeholder_body(report_text)
    if not body:
        return False
    if len(body) > 300:
        return False
    return bool(NO_CHANGE_PLACEHOLDER_PATTERN.fullmatch(body))


def write_github_output(path: str, values: dict[str, str]) -> None:
    if not path:
        for key, value in values.items():
            print(f"{key}={value}")
        return
    with Path(path).open("a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def classify_report(context: dict[str, Any], report_path: Path) -> dict[str, str]:
    if not report_path.exists():
        return {"has_report": "false", "ledger_status": "scanned_no_update", "ledger_should_update": "true"}

    report_text = report_path.read_text(encoding="utf-8")
    is_empty = not report_text.strip()
    no_change_placeholder = is_no_change_placeholder(report_text)
    if is_empty or no_change_placeholder:
        if is_tracked(report_path):
            raise SystemExit(f"existing report was replaced with an empty or no-change placeholder: {report_path}")
        report_path.unlink(missing_ok=True)
        return {"has_report": "false", "ledger_status": "scanned_no_update", "ledger_should_update": "true"}

    validate_report_references(report_text, context)

    if has_worktree_change(report_path):
        return {"has_report": "true", "ledger_status": "reported", "ledger_should_update": "true"}

    if current_prs_are_referenced(report_text, context):
        return {"has_report": "true", "ledger_status": "reported", "ledger_should_update": "true"}

    return {"has_report": "false", "ledger_status": "scanned_no_update", "ledger_should_update": "true"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", default="product-change-report-context.json")
    parser.add_argument("--github-output", default="")
    args = parser.parse_args()

    context = load_json(Path(args.context))
    values = classify_report(context, Path(context["report_path"]))
    write_github_output(args.github_output, values)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
