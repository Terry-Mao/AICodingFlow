#!/usr/bin/env python3
"""Validate a nightly review result and publish new, deduplicated GitHub issues."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from apply_issue_triage_result import MARKER as TRIAGE_COMMENT_MARKER
from github_api import flatten_gh_pages, run_gh_json
from prepare_nightly_review import focus_files, issue_snapshot, parse_cycle_days

OUTPUT_FILES = {
    "nightly-review-output/context.json",
    "nightly-review-output/issues.json",
    "nightly-review-output/findings.json",
}
FINDING_FIELDS = {
    "title", "path", "line", "trigger", "impact", "evidence",
    "confidence", "security", "duplicate_issue_number",
}
MAX_FINDINGS = 20


def load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Invalid or missing JSON file {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    return value


def validate_write_surface() -> None:
    result = subprocess.run(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        check=True, capture_output=True,
    )
    entries = [item.decode("utf-8") for item in result.stdout.split(b"\0") if item]
    for entry in entries:
        status, path = entry[:2], entry[3:]
        if status != "??" or path not in OUTPUT_FILES:
            raise SystemExit(f"Nightly review modified a repository file: {path}")


def validate_snapshot(context: dict[str, Any]) -> dict[str, int]:
    current_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()
    if context.get("commit") != current_commit:
        raise SystemExit("Nightly review commit changed")
    files = context.get("project_files")
    focus_entries = context.get("files")
    if not isinstance(files, list) or not isinstance(focus_entries, list):
        raise SystemExit("Nightly review context must contain project_files and files arrays")
    cycle_days = parse_cycle_days(str(context.get("cycle_days", "")))
    shard = context.get("shard")
    if type(shard) is not int or not 0 <= shard < cycle_days:
        raise SystemExit("Invalid nightly review shard")
    lines: dict[str, int] = {}
    for item in files:
        if not isinstance(item, dict):
            raise SystemExit("Invalid file entry in nightly review context")
        path = item.get("path")
        if not isinstance(path, str) or path.startswith("/") or ".." in Path(path).parts or path in lines:
            raise SystemExit("Invalid or duplicate file path in nightly review context")
        digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        if digest != item.get("sha256"):
            raise SystemExit(f"Nightly review source changed: {path}")
        line_count = item.get("line_count")
        if type(line_count) is not int or line_count < 0:
            raise SystemExit(f"Invalid line count for {path}")
        lines[path] = line_count
    expected = focus_files(files, shard, cycle_days)
    if focus_entries != expected:
        raise SystemExit("Nightly review focus files do not match the project inventory")
    return lines


def require_text(item: dict[str, Any], field: str, index: int, limit: int) -> str:
    value = item.get(field)
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise SystemExit(f"findings[{index}].{field} must be 1-{limit} characters")
    if any(ord(char) < 32 and char not in "\n\t" for char in value):
        raise SystemExit(f"findings[{index}].{field} contains control characters")
    return value.strip()


def validate_findings(result: dict[str, Any], lines: dict[str, int], issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if set(result) != {"findings"} or not isinstance(result["findings"], list):
        raise SystemExit("findings.json must contain only a findings array")
    if len(result["findings"]) > MAX_FINDINGS:
        raise SystemExit(f"findings.json exceeds {MAX_FINDINGS} findings")
    issue_numbers = {item.get("number") for item in issues if isinstance(item, dict)}
    validated = []
    for index, item in enumerate(result["findings"]):
        if not isinstance(item, dict) or set(item) != FINDING_FIELDS:
            raise SystemExit(f"findings[{index}] has missing or unknown fields")
        for field, limit in (("title", 120), ("trigger", 1200), ("impact", 1200), ("evidence", 1800)):
            require_text(item, field, index, limit)
        path = item.get("path")
        line = item.get("line")
        if path not in lines or type(line) is not int or not 1 <= line <= lines[path]:
            raise SystemExit(f"findings[{index}] must target a scanned file line")
        if item.get("confidence") != "high" or type(item.get("security")) is not bool:
            raise SystemExit(f"findings[{index}] must have high confidence and a boolean security flag")
        duplicate = item.get("duplicate_issue_number")
        if duplicate is not None and (type(duplicate) is not int or duplicate not in issue_numbers):
            raise SystemExit(f"findings[{index}] references an issue absent from the snapshot")
        if item["security"] and any("```" in item[field] for field in ("title", "trigger", "impact", "evidence")):
            raise SystemExit(f"findings[{index}] contains a security code block")
        validated.append(item)
    return validated


def normalized_title(title: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"^(?:bug|缺陷)\s*[:：]\s*", "", title.strip(), flags=re.I)).casefold()


def fingerprint(finding: dict[str, Any]) -> str:
    key = f"{finding['path']}\n{normalized_title(finding['title'])}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:20]


def matched_issue(finding: dict[str, Any], issues: list[dict[str, Any]]) -> dict[str, Any] | None:
    marker = f"nightly-review-fingerprint:{fingerprint(finding)}"
    title = normalized_title(finding["title"])
    matches = []
    for issue in issues:
        old_title = normalized_title(str(issue.get("title") or ""))
        old_body = str(issue.get("body") or "")
        if marker in old_body:
            matches.append(issue)
            continue
        if finding["path"] in old_body and (
            title == old_title or difflib.SequenceMatcher(None, title, old_title).ratio() >= 0.9
        ):
            matches.append(issue)
    return next((issue for issue in matches if issue.get("state") != "closed"), None) or (matches[0] if matches else None)


def issue_body(finding: dict[str, Any], context: dict[str, Any], *, closed_issue_number: int | None = None) -> str:
    marker = fingerprint(finding)
    previous_note = f"先前报告：#{closed_issue_number}（已关闭；当前扫描再次发现）。\n\n" if closed_issue_number else ""
    if finding["security"]:
        details = (
            "## 实际影响\n\n"
            f"{finding['impact'].strip()}\n\n"
            "> 安全问题：公开 Issue 省略具体触发步骤和核实细节。\n"
        )
    else:
        details = (
            f"## 触发条件\n\n{finding['trigger'].strip()}\n\n"
            f"## 实际影响\n\n{finding['impact'].strip()}\n\n"
            f"## 核实依据\n\n{finding['evidence'].strip()}\n"
        )
    return (
        f"<!-- nightly-review-fingerprint:{marker} -->\n"
        f"## 问题位置\n\n`{finding['path']}:{finding['line']}`\n\n"
        f"{details}\n"
        f"{previous_note}"
        f"扫描提交：`{context['commit']}`；扫描日期：{context['scan_date']}（北京时间）；"
        f"轮巡分片：{context['shard']}/{context['cycle_days']}。\n"
    )


def is_nightly_issue(issue: dict[str, Any]) -> bool:
    return str(issue.get("body") or "").lstrip().startswith("<!-- nightly-review-fingerprint:")


def has_triage_comment(repo: str, issue_number: int) -> bool:
    pages = run_gh_json([
        "api", f"repos/{repo}/issues/{issue_number}/comments?per_page=100",
        "--paginate", "--slurp",
    ])
    return any(TRIAGE_COMMENT_MARKER in str(item.get("body") or "") for item in flatten_gh_pages(pages))


def dispatch_triage(repo: str, default_branch: str, issue_number: int) -> None:
    subprocess.run([
        "gh", "workflow", "run", "triage-issue.yml", "--repo", repo,
        "--ref", default_branch, "-f", f"issue={issue_number}",
    ], check=True)
    print(f"Dispatched triage for issue #{issue_number}")


def publish(repo: str, default_branch: str, findings: list[dict[str, Any]], issues: list[dict[str, Any]], context: dict[str, Any]) -> tuple[int, int, list[int]]:
    created = skipped = 0
    failed_dispatches: list[int] = []
    seen: set[str] = set()
    checked_triage: set[int] = set()

    def try_dispatch(issue_number: int, *, check_existing: bool = False) -> None:
        try:
            if check_existing and has_triage_comment(repo, issue_number):
                return
            dispatch_triage(repo, default_branch, issue_number)
        except (OSError, subprocess.CalledProcessError) as exc:
            failed_dispatches.append(issue_number)
            print(f"Failed to dispatch triage for issue #{issue_number}: {exc}", file=sys.stderr)

    for finding in findings:
        marker = fingerprint(finding)
        if marker in seen:
            skipped += 1
            continue
        referenced = next(
            (issue for issue in issues if issue.get("number") == finding["duplicate_issue_number"]),
            None,
        ) if finding["duplicate_issue_number"] is not None else None
        matched = matched_issue(finding, issues)
        existing = next(
            (issue for issue in (referenced, matched) if issue and issue.get("state") != "closed"),
            None,
        )
        if existing:
            if existing and is_nightly_issue(existing):
                number = existing["number"]
                if number not in checked_triage:
                    checked_triage.add(number)
                    try_dispatch(number, check_existing=True)
            skipped += 1
            continue
        closed_issue = referenced or matched
        closed_number = closed_issue["number"] if closed_issue and closed_issue.get("state") == "closed" else None
        title = finding["title"].strip()
        if not title.lower().startswith("bug:"):
            title = f"bug: {title}"
        body = issue_body(finding, context, closed_issue_number=closed_number)
        response = run_gh_json([
            "api", f"repos/{repo}/issues", "--method", "POST",
            "-f", f"title={title}", "-f", f"body={body}",
        ])
        if not isinstance(response, dict) or not isinstance(response.get("number"), int):
            raise SystemExit("GitHub did not confirm issue creation")
        issues.append({"number": response["number"], "title": title, "body": body, "state": "open"})
        seen.add(marker)
        created += 1
        print(f"Created issue #{response['number']}: {title}")
        try_dispatch(response["number"])
    return created, skipped, failed_dispatches


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--default-branch", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()

    validate_write_surface()
    context = load_object(args.output_dir / "context.json")
    issues = json.loads((args.output_dir / "issues.json").read_text(encoding="utf-8"))
    if not isinstance(issues, list):
        raise SystemExit("issues.json must contain an array")
    lines = validate_snapshot(context)
    findings = validate_findings(load_object(args.output_dir / "findings.json"), lines, issues)
    # A new issue can appear while the agent is reviewing. Refresh before writes.
    current_issues = issue_snapshot(args.repo)
    created, skipped, failed_dispatches = publish(args.repo, args.default_branch, findings, current_issues, context)
    summary = f"夜间代码审查：分片 {context['shard']}/{context['cycle_days']}，项目代码 {len(lines)} 个文件，本轮重点 {len(context['files'])} 个文件，发现 {len(findings)} 项，创建 {created} 个 Issue，跳过 {skipped} 项重复发现。\n"
    if failed_dispatches:
        summary += "分诊调度失败，需补发：" + "、".join(f"#{number}" for number in failed_dispatches) + "。\n"
    print(summary, end="")
    if args.summary:
        with args.summary.open("a", encoding="utf-8") as output:
            output.write(summary)
    if failed_dispatches:
        raise SystemExit("Nightly review created issues but triage dispatch failed for: " + ", ".join(f"#{number}" for number in failed_dispatches))


if __name__ == "__main__":
    main()
