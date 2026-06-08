#!/usr/bin/env python3
"""Prepare stable merged-PR context for a product change report."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from artifact_contracts import write_github_output
from github_api import fetch_default_branch, run_gh_json, run_gh_text
from ledger_contracts import entries_by_pr, load_ledger as load_pr_ledger

UTC = dt.timezone.utc
DEFAULT_LEDGER_PATH = "docs/updates/.product-change-report-ledger.json"


def parse_date(value: str) -> dt.date:
    return dt.date.fromisoformat(value)


def parse_report_date(value: str) -> dt.date:
    if value:
        return parse_date(value)
    return dt.datetime.now(UTC).date() - dt.timedelta(days=1)


def scan_window(report_date: dt.date) -> tuple[dt.datetime, dt.datetime]:
    start = dt.datetime.combine(report_date, dt.time.min, tzinfo=UTC)
    end = start + dt.timedelta(days=1)
    return start, end


def range_window(start_date: dt.date, end_date: dt.date) -> tuple[dt.datetime, dt.datetime]:
    if end_date <= start_date:
        raise SystemExit("--end-date must be after --start-date")
    start = dt.datetime.combine(start_date, dt.time.min, tzinfo=UTC)
    end = dt.datetime.combine(end_date, dt.time.min, tzinfo=UTC)
    return start, end


def resolve_scan_window(
    report_date_value: str,
    start_date_value: str,
    end_date_value: str,
) -> tuple[str, dt.datetime, dt.datetime]:
    has_range = bool(start_date_value or end_date_value)
    if has_range:
        if report_date_value:
            raise SystemExit("--report-date cannot be combined with --start-date or --end-date")
        if not start_date_value or not end_date_value:
            raise SystemExit("--start-date and --end-date must be provided together")
        start, end = range_window(parse_date(start_date_value), parse_date(end_date_value))
        return report_id_for_window(start, end), start, end

    report_date = parse_report_date(report_date_value)
    start, end = scan_window(report_date)
    return report_date.isoformat(), start, end


def report_id_for_window(start: dt.datetime, end: dt.datetime) -> str:
    start_date = start.date()
    last_included_date = (end - dt.timedelta(days=1)).date()
    if start_date == last_included_date:
        return start_date.isoformat()
    return f"{start_date.isoformat()}-to-{last_included_date.isoformat()}"


def report_path_for_id(report_id: str) -> str:
    return f"docs/updates/auto-update-{report_id}.md"


def iso_z(value: dt.datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def search_merged_pr_numbers(repo: str, start: dt.datetime, end: dt.datetime) -> list[int]:
    branch = fetch_default_branch(repo, run_json=run_gh_json)
    numbers: list[int] = []
    seen: set[int] = set()
    current_date = start.date()
    while current_date < end.date():
        query = (
            f"repo:{repo} is:pr is:merged "
            f"merged:{current_date.isoformat()} "
            f"base:{branch}"
        )
        pages = run_gh_json(
            [
                "api",
                "--method",
                "GET",
                "search/issues",
                "-f",
                f"q={query}",
                "-f",
                "per_page=100",
                "--paginate",
                "--slurp",
            ]
        )
        for page in pages or []:
            if not isinstance(page, dict):
                continue
            for item in page.get("items") or []:
                if not isinstance(item, dict):
                    continue
                if "pull_request" not in item:
                    continue
                try:
                    number = int(item["number"])
                except (KeyError, TypeError, ValueError):
                    continue
                if number in seen:
                    continue
                seen.add(number)
                numbers.append(number)
        current_date += dt.timedelta(days=1)
    return numbers


def parse_github_datetime(value: str) -> dt.datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = dt.datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def pr_merged_in_window(pr: dict[str, Any], start: dt.datetime, end: dt.datetime) -> bool:
    merged_at = parse_github_datetime(str(pr.get("mergedAt") or ""))
    return bool(merged_at and start <= merged_at < end)


def fetch_merged_prs(repo: str, start: dt.datetime, end: dt.datetime) -> list[dict[str, Any]]:
    numbers = search_merged_pr_numbers(repo, start, end)
    prs: list[dict[str, Any]] = []
    for number in numbers:
        pr = fetch_pr_details(repo, number)
        if pr_merged_in_window(pr, start, end):
            prs.append(pr)
    return sorted(prs, key=lambda pr: (pr.get("mergedAt") or "", int(pr.get("number") or 0)))


def fetch_pr_details(repo: str, number: int) -> dict[str, Any]:
    return run_gh_json(
        [
            "pr",
            "view",
            str(number),
            "--repo",
            repo,
            "--json",
            "number,title,body,url,mergedAt,author,headRefName,baseRefName,mergeCommit,files,commits,closingIssuesReferences,labels",
        ]
    )


def fetch_pr_diff(repo: str, number: int, max_chars: int) -> str:
    diff = run_gh_text(["pr", "diff", str(number), "--repo", repo, "--patch"])
    if len(diff) <= max_chars:
        return diff
    return diff[:max_chars] + "\n\n[diff truncated by prepare_product_change_report_context.py]\n"


def compact_author(value: dict[str, Any] | None) -> str:
    if not value:
        return ""
    return value.get("login") or value.get("name") or ""


def compact_files(files: list[dict[str, Any]], limit: int = 80) -> list[str]:
    paths = [str(item.get("path") or item.get("filename") or "") for item in files]
    paths = [path for path in paths if path]
    if len(paths) <= limit:
        return paths
    return [*paths[:limit], f"... {len(paths) - limit} more files"]


def issue_refs(pr: dict[str, Any]) -> list[str]:
    refs = []
    for issue in pr.get("closingIssuesReferences") or []:
        number = issue.get("number")
        url = issue.get("url")
        title = issue.get("title")
        if number:
            refs.append(f"#{number} {title or ''} {url or ''}".strip())
    return refs


def load_ledger(path: Path) -> dict[str, Any]:
    return load_pr_ledger(path, ledger_name="product change report")


def ledger_entries_by_pr(ledger: dict[str, Any]) -> dict[int, dict[str, Any]]:
    return entries_by_pr(ledger)


def split_prs_by_ledger(
    prs: list[dict[str, Any]],
    ledger: dict[str, Any],
    report_path: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    entries = ledger_entries_by_pr(ledger)
    reportable: list[dict[str, Any]] = []
    already_reported: list[dict[str, Any]] = []
    for pr in prs:
        number = int(pr.get("number") or 0)
        ledger_entry = entries.get(number)
        if ledger_entry and ledger_entry.get("report_path") != report_path:
            already_reported.append(
                {
                    "number": number,
                    "title": pr.get("title") or "",
                    "url": pr.get("url") or "",
                    "mergedAt": pr.get("mergedAt") or "",
                    "recorded_report_date": ledger_entry.get("report_date") or "",
                    "recorded_report_path": ledger_entry.get("report_path") or "",
                }
            )
            continue
        reportable.append(pr)
    return reportable, already_reported


def write_context_json(
    path: Path,
    repo: str,
    default_branch: str,
    report_id: str,
    start: dt.datetime,
    end: dt.datetime,
    reportable_prs: list[dict[str, Any]],
    scanned_pr_count: int,
    already_reported_prs: list[dict[str, Any]],
    ledger_path: str,
) -> None:
    report_path = report_path_for_id(report_id)
    payload = {
        "repo": repo,
        "default_branch": default_branch,
        "report_date": report_id,
        "report_path": report_path,
        "ledger_path": ledger_path,
        "scan_window": {
            "start_inclusive": iso_z(start),
            "end_exclusive": iso_z(end),
            "timezone": "UTC",
            "sort_order": "mergedAt ascending, then PR number ascending",
        },
        "scanned_pr_count": scanned_pr_count,
        "reportable_pr_count": len(reportable_prs),
        "already_reported_pr_count": len(already_reported_prs),
        "reportable_prs": reportable_prs,
        "already_reported_prs": already_reported_prs,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_markdown(
    path: Path,
    report_id: str,
    start: dt.datetime,
    end: dt.datetime,
    reportable_prs: list[dict[str, Any]],
    already_reported_prs: list[dict[str, Any]],
) -> None:
    lines = [
        f"# Product change report context for {report_id}",
        "",
        f"Scan window: `{iso_z(start)}` inclusive to `{iso_z(end)}` exclusive.",
        "",
        "Processing order: mergedAt ascending, then PR number ascending.",
        "",
    ]
    if already_reported_prs:
        lines.extend(["Already reported PRs skipped for this report:", ""])
        for pr in already_reported_prs:
            lines.append(
                f"- PR #{pr.get('number')}: already recorded in `{pr.get('recorded_report_path')}`"
            )
        lines.append("")
    if not reportable_prs:
        lines.extend(["No unreported merged PRs found in the scan window.", ""])
    for pr in reportable_prs:
        labels = [label.get("name", "") for label in pr.get("labels") or [] if label.get("name")]
        lines.extend(
            [
                f"## PR #{pr.get('number')}: {pr.get('title') or ''}",
                "",
                f"- URL: {pr.get('url') or ''}",
                f"- Merged at: {pr.get('mergedAt') or ''}",
                f"- Author: {compact_author(pr.get('author'))}",
                f"- Branch: `{pr.get('headRefName') or ''}` -> `{pr.get('baseRefName') or ''}`",
                f"- Labels: {', '.join(labels) if labels else 'none'}",
                f"- Closing issues: {', '.join(issue_refs(pr)) if issue_refs(pr) else 'none'}",
                "",
                "Changed files:",
            ]
        )
        for changed_file in compact_files(pr.get("files") or []):
            lines.append(f"- `{changed_file}`")
        body = (pr.get("body") or "").strip()
        if body:
            lines.extend(["", "PR description:", "", body])
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_diffs(path: Path, repo: str, prs: list[dict[str, Any]], max_chars_per_pr: int) -> None:
    lines: list[str] = []
    for pr in prs:
        number = int(pr["number"])
        lines.extend([f"# Diff for PR #{number}: {pr.get('title') or ''}", ""])
        lines.append(fetch_pr_diff(repo, number, max_chars_per_pr))
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--report-date", default="")
    parser.add_argument("--start-date", default="")
    parser.add_argument("--end-date", default="")
    parser.add_argument("--context-output", default="product-change-report-context.json")
    parser.add_argument("--markdown-output", default="product-change-report-context.md")
    parser.add_argument("--diff-output", default="product-change-report-diffs.md")
    parser.add_argument("--github-output", default="")
    parser.add_argument("--ledger-path", default=DEFAULT_LEDGER_PATH)
    parser.add_argument("--max-diff-chars-per-pr", type=int, default=60000)
    return parser.parse_args(argv)


def run(args: argparse.Namespace) -> int:
    report_id, start, end = resolve_scan_window(args.report_date, args.start_date, args.end_date)
    default_branch = fetch_default_branch(args.repo)
    report_path = report_path_for_id(report_id)
    scanned_prs = fetch_merged_prs(args.repo, start, end)
    ledger = load_ledger(Path(args.ledger_path))
    reportable_prs, already_reported_prs = split_prs_by_ledger(scanned_prs, ledger, report_path)

    write_context_json(
        Path(args.context_output),
        args.repo,
        default_branch,
        report_id,
        start,
        end,
        reportable_prs,
        len(scanned_prs),
        already_reported_prs,
        args.ledger_path,
    )
    write_markdown(Path(args.markdown_output), report_id, start, end, reportable_prs, already_reported_prs)
    write_diffs(Path(args.diff_output), args.repo, reportable_prs, args.max_diff_chars_per_pr)
    write_github_output(
        args.github_output,
        {
            "report_date": report_id,
            "report_path": report_path,
            "ledger_path": args.ledger_path,
            "scanned_pr_count": str(len(scanned_prs)),
            "reportable_pr_count": str(len(reportable_prs)),
            "already_reported_pr_count": str(len(already_reported_prs)),
        },
    )
    return 0


def main() -> int:
    return run(parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
