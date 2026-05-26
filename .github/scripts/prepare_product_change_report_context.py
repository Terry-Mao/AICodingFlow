#!/usr/bin/env python3
"""Prepare stable merged-PR context for a product change report."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
from pathlib import Path
from typing import Any


UTC = dt.timezone.utc
DEFAULT_LEDGER_PATH = "docs/updates/.product-change-report-ledger.json"


def run_gh_json(args: list[str]) -> Any:
    result = subprocess.run(["gh", *args], check=True, stdout=subprocess.PIPE, text=True)
    return json.loads(result.stdout)


def run_gh_text(args: list[str]) -> str:
    result = subprocess.run(["gh", *args], check=True, stdout=subprocess.PIPE, text=True)
    return result.stdout


def parse_report_date(value: str) -> dt.date:
    if value:
        return dt.date.fromisoformat(value)
    return dt.datetime.now(UTC).date() - dt.timedelta(days=1)


def scan_window(report_date: dt.date) -> tuple[dt.datetime, dt.datetime]:
    start = dt.datetime.combine(report_date, dt.time.min, tzinfo=UTC)
    end = start + dt.timedelta(days=1)
    return start, end


def iso_z(value: dt.datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def fetch_default_branch(repo: str) -> str:
    data = run_gh_json(["repo", "view", repo, "--json", "defaultBranchRef"])
    branch = (data.get("defaultBranchRef") or {}).get("name")
    if not branch:
        raise SystemExit("could not determine default branch")
    return branch


def search_merged_pr_numbers(repo: str, start: dt.datetime, end: dt.datetime) -> list[int]:
    query = (
        f"repo:{repo} is:pr is:merged "
        f"merged:>={start.date().isoformat()} merged:<{end.date().isoformat()} "
        f"base:{fetch_default_branch(repo)}"
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
    numbers: list[int] = []
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
            numbers.append(number)
    return numbers


def fetch_merged_prs(repo: str, start: dt.datetime, end: dt.datetime) -> list[dict[str, Any]]:
    numbers = search_merged_pr_numbers(repo, start, end)
    prs = [fetch_pr_details(repo, number) for number in numbers]
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
    if not path.exists():
        return {"version": 1, "entries": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"invalid product change report ledger: {path}")
    entries = data.get("entries")
    if entries is None:
        data["entries"] = []
    elif not isinstance(entries, list):
        raise SystemExit(f"invalid product change report ledger entries: {path}")
    data.setdefault("version", 1)
    return data


def ledger_entries_by_pr(ledger: dict[str, Any]) -> dict[int, dict[str, Any]]:
    entries: dict[int, dict[str, Any]] = {}
    for entry in ledger.get("entries") or []:
        try:
            pr_number = int(entry.get("pr"))
        except (TypeError, ValueError):
            continue
        entries[pr_number] = entry
    return entries


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
    report_date: dt.date,
    start: dt.datetime,
    end: dt.datetime,
    reportable_prs: list[dict[str, Any]],
    scanned_pr_count: int,
    already_reported_prs: list[dict[str, Any]],
    ledger_path: str,
) -> None:
    report_path = f"docs/updates/auto-update-{report_date.isoformat()}.md"
    payload = {
        "repo": repo,
        "default_branch": default_branch,
        "report_date": report_date.isoformat(),
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
    report_date: dt.date,
    start: dt.datetime,
    end: dt.datetime,
    reportable_prs: list[dict[str, Any]],
    already_reported_prs: list[dict[str, Any]],
) -> None:
    lines = [
        f"# Product change report context for {report_date.isoformat()}",
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
        commits = pr.get("commits") or []
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
                f"- Merge commit: {(pr.get('mergeCommit') or {}).get('oid') or ''}",
                f"- Commits: {len(commits)}",
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


def write_github_output(path: str | None, values: dict[str, str]) -> None:
    if not path:
        return
    with Path(path).open("a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--report-date", default="")
    parser.add_argument("--context-output", default="product-change-report-context.json")
    parser.add_argument("--markdown-output", default="product-change-report-context.md")
    parser.add_argument("--diff-output", default="product-change-report-diffs.md")
    parser.add_argument("--github-output", default="")
    parser.add_argument("--ledger-path", default=DEFAULT_LEDGER_PATH)
    parser.add_argument("--max-diff-chars-per-pr", type=int, default=60000)
    args = parser.parse_args()

    report_date = parse_report_date(args.report_date)
    start, end = scan_window(report_date)
    default_branch = fetch_default_branch(args.repo)
    report_path = f"docs/updates/auto-update-{report_date.isoformat()}.md"
    scanned_prs = fetch_merged_prs(args.repo, start, end)
    ledger = load_ledger(Path(args.ledger_path))
    reportable_prs, already_reported_prs = split_prs_by_ledger(scanned_prs, ledger, report_path)

    write_context_json(
        Path(args.context_output),
        args.repo,
        default_branch,
        report_date,
        start,
        end,
        reportable_prs,
        len(scanned_prs),
        already_reported_prs,
        args.ledger_path,
    )
    write_markdown(Path(args.markdown_output), report_date, start, end, reportable_prs, already_reported_prs)
    write_diffs(Path(args.diff_output), args.repo, reportable_prs, args.max_diff_chars_per_pr)
    write_github_output(
        args.github_output,
        {
            "report_date": report_date.isoformat(),
            "report_path": report_path,
            "ledger_path": args.ledger_path,
            "scanned_pr_count": str(len(scanned_prs)),
            "reportable_pr_count": str(len(reportable_prs)),
            "already_reported_pr_count": str(len(already_reported_prs)),
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
