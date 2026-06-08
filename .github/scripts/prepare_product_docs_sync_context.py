#!/usr/bin/env python3
"""Prepare stable pull-request context for product docs synchronization."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from artifact_contracts import write_github_output
from github_api import fetch_default_branch, run_gh_json, run_gh_text
from issue_refs import issue_numbers_from_closing_refs
from ledger_contracts import entries_by_pr, load_ledger as load_pr_ledger

UTC = dt.timezone.utc
DEFAULT_LEDGER_PATH = "docs/product/.product-docs-sync-ledger.json"
PRODUCT_DOCS_SYNC_BRANCH_PREFIX = "docs/product-docs-sync"
PRODUCT_DOCS_SYNC_TITLE_PREFIXES = (
    "Update product docs for PR #",
    "Draft: Product docs sync for PR #",
    "Record product docs sync decision for PR #",
)
PRODUCT_DOCS_SYNC_TITLES = {"Update product docs"}
def parse_date(value: str) -> dt.date:
    return dt.date.fromisoformat(value)


def default_scan_window(days: int) -> tuple[dt.datetime, dt.datetime]:
    if days <= 0:
        raise SystemExit("--scan-days must be positive")
    end = dt.datetime.now(UTC).replace(microsecond=0)
    start = end - dt.timedelta(days=days)
    return start, end


def explicit_scan_window(start_date: str, end_date: str) -> tuple[dt.datetime, dt.datetime]:
    if not start_date or not end_date:
        raise SystemExit("--start-date and --end-date must be provided together")
    start = dt.datetime.combine(parse_date(start_date), dt.time.min, tzinfo=UTC)
    end = dt.datetime.combine(parse_date(end_date), dt.time.min, tzinfo=UTC)
    if end <= start:
        raise SystemExit("--end-date must be after --start-date")
    return start, end


def iso_z(value: dt.datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def fetch_pr(repo: str, pr_number: str) -> dict[str, Any]:
    return run_gh_json(
        [
            "pr",
            "view",
            pr_number,
            "--repo",
            repo,
            "--json",
            "number,title,body,url,state,isDraft,mergedAt,author,headRefName,baseRefName,mergeCommit,files,commits,closingIssuesReferences,labels",
        ]
    )


def search_merged_pr_numbers(repo: str, start: dt.datetime, end: dt.datetime, default_branch: str) -> list[int]:
    numbers: list[int] = []
    seen: set[int] = set()
    current_date = start.date()
    while current_date <= end.date():
        query = (
            f"repo:{repo} is:pr is:merged "
            f"merged:{current_date.isoformat()} "
            f"base:{default_branch}"
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
                if not isinstance(item, dict) or "pull_request" not in item:
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
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def pr_merged_in_window(pr: dict[str, Any], start: dt.datetime, end: dt.datetime) -> bool:
    merged_at = parse_github_datetime(str(pr.get("mergedAt") or ""))
    return bool(merged_at and start <= merged_at < end)


def is_product_docs_sync_pr(pr: dict[str, Any]) -> bool:
    branch = str(pr.get("headRefName") or "")
    title = str(pr.get("title") or "")
    return (
        branch.startswith(PRODUCT_DOCS_SYNC_BRANCH_PREFIX)
        or title.startswith(PRODUCT_DOCS_SYNC_TITLE_PREFIXES)
        or title in PRODUCT_DOCS_SYNC_TITLES
    )


def fetch_merged_prs(repo: str, start: dt.datetime, end: dt.datetime, default_branch: str) -> list[dict[str, Any]]:
    prs: list[dict[str, Any]] = []
    for number in search_merged_pr_numbers(repo, start, end, default_branch):
        pr = fetch_pr(repo, str(number))
        if pr_merged_in_window(pr, start, end) and not is_product_docs_sync_pr(pr):
            prs.append(pr)
    return sorted(prs, key=lambda pr: (pr.get("mergedAt") or "", int(pr.get("number") or 0)))


def load_ledger(path: Path) -> dict[str, Any]:
    return load_pr_ledger(path, ledger_name="product docs sync")


def ledger_entries_by_pr(ledger: dict[str, Any]) -> dict[int, dict[str, Any]]:
    return entries_by_pr(ledger)


def select_unprocessed_pr(prs: list[dict[str, Any]], ledger: dict[str, Any]) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    entries = ledger_entries_by_pr(ledger)
    skipped: list[dict[str, Any]] = []
    for pr in prs:
        number = int(pr.get("number") or 0)
        entry = entries.get(number)
        if entry:
            skipped.append(
                {
                    "number": number,
                    "title": pr.get("title") or "",
                    "url": pr.get("url") or "",
                    "mergedAt": pr.get("mergedAt") or "",
                    "recorded_at": entry.get("recorded_at") or "",
                    "docs_update": entry.get("docs_update") or "",
                }
            )
            continue
        return pr, skipped
    return None, skipped


def fetch_issue(repo: str, number: int) -> dict[str, Any]:
    return run_gh_json(
        [
            "issue",
            "view",
            str(number),
            "--repo",
            repo,
            "--json",
            "number,title,body,url,state,labels,comments",
        ]
    )


def fetch_existing_issues(repo: str, numbers: list[int]) -> tuple[list[dict[str, Any]], list[int]]:
    issues: list[dict[str, Any]] = []
    skipped: list[int] = []
    for number in numbers:
        try:
            issues.append(fetch_issue(repo, number))
        except subprocess.CalledProcessError:
            skipped.append(number)
    return issues, skipped


def fetch_pr_diff(repo: str, pr_number: str, max_chars: int) -> str:
    diff = run_gh_text(["pr", "diff", pr_number, "--repo", repo, "--patch"])
    if len(diff) <= max_chars:
        return diff
    return diff[:max_chars] + "\n\n[diff truncated by prepare_product_docs_sync_context.py]\n"


def issue_numbers(pr: dict[str, Any]) -> list[int]:
    return issue_numbers_from_closing_refs(pr)


def compact_author(value: dict[str, Any] | None) -> str:
    if not value:
        return ""
    return value.get("login") or value.get("name") or ""


def compact_files(files: list[dict[str, Any]], limit: int = 100) -> list[str]:
    paths = [str(item.get("path") or item.get("filename") or "") for item in files]
    paths = [path for path in paths if path]
    if len(paths) <= limit:
        return paths
    return [*paths[:limit], f"... {len(paths) - limit} more files"]


def read_existing_product_docs(root: Path) -> list[dict[str, str]]:
    docs_root = root / "docs/product"
    if not docs_root.exists():
        return []
    docs: list[dict[str, str]] = []
    for path in sorted(docs_root.rglob("*.md")):
        if not path.is_file():
            continue
        docs.append(
            {
                "path": path.relative_to(root).as_posix(),
                "content": path.read_text(encoding="utf-8"),
            }
        )
    return docs


def read_specs(root: Path, numbers: list[int]) -> list[dict[str, str]]:
    specs: list[dict[str, str]] = []
    for number in numbers:
        spec_dir = root / f"specs/issue-{number}"
        for name in ("product.md", "tech.md"):
            path = spec_dir / name
            if path.exists():
                specs.append(
                    {
                        "path": path.relative_to(root).as_posix(),
                        "content": path.read_text(encoding="utf-8"),
                    }
                )
    return specs


def write_context_json(
    path: Path,
    repo: str,
    default_branch: str,
    pr: dict[str, Any],
    issues: list[dict[str, Any]],
    specs: list[dict[str, str]],
    product_docs: list[dict[str, str]],
    ledger_path: str,
    scanned_pr_count: int,
    skipped_prs: list[dict[str, Any]],
    scan_window: dict[str, str] | None,
) -> None:
    payload = {
        "repo": repo,
        "default_branch": default_branch,
        "pr": pr,
        "linked_issues": issues,
        "specs": specs,
        "existing_product_docs": [{"path": doc["path"]} for doc in product_docs],
        "docs_update_decisions": ["required", "uncertain", "not-needed"],
        "result_path": "product-docs-sync-result.json",
        "ledger_path": ledger_path,
        "allowed_write_roots": ["docs/product/"],
        "scan_window": scan_window,
        "scanned_pr_count": scanned_pr_count,
        "skipped_processed_pr_count": len(skipped_prs),
        "skipped_processed_prs": skipped_prs,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_markdown(path: Path, pr: dict[str, Any], issues: list[dict[str, Any]], specs: list[dict[str, str]]) -> None:
    labels = [label.get("name", "") for label in pr.get("labels") or [] if label.get("name")]
    lines = [
        f"# Product docs sync context for PR #{pr.get('number')}",
        "",
        f"- URL: {pr.get('url') or ''}",
        f"- Title: {pr.get('title') or ''}",
        f"- State: {pr.get('state') or ''}",
        f"- Merged at: {pr.get('mergedAt') or ''}",
        f"- Author: {compact_author(pr.get('author'))}",
        f"- Branch: `{pr.get('headRefName') or ''}` -> `{pr.get('baseRefName') or ''}`",
        f"- Labels: {', '.join(labels) if labels else 'none'}",
        f"- Merge commit: {(pr.get('mergeCommit') or {}).get('oid') or ''}",
        "",
        "Changed files:",
    ]
    for changed_file in compact_files(pr.get("files") or []):
        lines.append(f"- `{changed_file}`")
    body = (pr.get("body") or "").strip()
    if body:
        lines.extend(["", "PR description:", "", body])
    if issues:
        lines.extend(["", "Linked issues:"])
        for issue in issues:
            lines.extend(
                [
                    "",
                    f"## Issue #{issue.get('number')}: {issue.get('title') or ''}",
                    "",
                    f"- URL: {issue.get('url') or ''}",
                    f"- State: {issue.get('state') or ''}",
                    "",
                    (issue.get("body") or "").strip(),
                ]
            )
            comments = issue.get("comments") or []
            if comments:
                lines.extend(["", "Issue comments:"])
                for comment in comments:
                    author = compact_author(comment.get("author"))
                    lines.extend(["", f"### Comment by {author}", "", (comment.get("body") or "").strip()])
    if specs:
        lines.extend(["", "Specs included:"])
        for spec in specs:
            lines.extend(["", f"## `{spec['path']}`", "", spec["content"].strip()])
    path.write_text("\n".join(lines), encoding="utf-8")


def write_existing_docs(path: Path, product_docs: list[dict[str, str]]) -> None:
    lines = ["# Existing product docs", ""]
    if not product_docs:
        lines.extend(["No existing `docs/product/` markdown files were found.", ""])
    for doc in product_docs:
        lines.extend([f"## `{doc['path']}`", "", doc["content"].strip(), ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--pr-number", default="")
    parser.add_argument("--start-date", default="")
    parser.add_argument("--end-date", default="")
    parser.add_argument("--scan-days", type=int, default=14)
    parser.add_argument("--context-output", default="product-docs-sync-context.json")
    parser.add_argument("--markdown-output", default="product-docs-sync-context.md")
    parser.add_argument("--diff-output", default="product-docs-sync-diff.md")
    parser.add_argument("--existing-docs-output", default="product-docs-existing.md")
    parser.add_argument("--github-output", default="")
    parser.add_argument("--ledger-path", default=DEFAULT_LEDGER_PATH)
    parser.add_argument("--max-diff-chars", type=int, default=100000)
    return parser.parse_args(argv)


def write_no_pr_outputs(
    args: argparse.Namespace,
    default_branch: str,
    product_docs: list[dict[str, str]],
    scanned_pr_count: int,
    skipped_prs: list[dict[str, Any]],
    scan_window_payload: dict[str, str] | None,
) -> None:
    write_context_json(
        Path(args.context_output),
        args.repo,
        default_branch,
        {},
        [],
        [],
        product_docs,
        args.ledger_path,
        scanned_pr_count,
        skipped_prs,
        scan_window_payload,
    )
    Path(args.markdown_output).write_text("No unprocessed merged PRs found.\n", encoding="utf-8")
    Path(args.diff_output).write_text("", encoding="utf-8")
    write_existing_docs(Path(args.existing_docs_output), product_docs)
    write_github_output(
        args.github_output,
        {
            "pr_number": "",
            "pr_title": "",
            "pr_url": "",
            "merged_at": "",
            "default_branch": default_branch,
            "ledger_path": args.ledger_path,
            "scanned_pr_count": str(scanned_pr_count),
            "skipped_processed_pr_count": str(len(skipped_prs)),
            "should_run": "false",
            "skip_reason": "no unprocessed merged pull requests found",
        },
    )


def write_selected_pr_outputs(
    args: argparse.Namespace,
    default_branch: str,
    pr: dict[str, Any],
    issues: list[dict[str, Any]],
    specs: list[dict[str, str]],
    product_docs: list[dict[str, str]],
    scanned_pr_count: int,
    skipped_prs: list[dict[str, Any]],
    scan_window_payload: dict[str, str] | None,
) -> None:
    write_context_json(
        Path(args.context_output),
        args.repo,
        default_branch,
        pr,
        issues,
        specs,
        product_docs,
        args.ledger_path,
        scanned_pr_count,
        skipped_prs,
        scan_window_payload,
    )
    write_markdown(Path(args.markdown_output), pr, issues, specs)
    selected_pr_number = str(pr.get("number") or args.pr_number)
    Path(args.diff_output).write_text(fetch_pr_diff(args.repo, selected_pr_number, args.max_diff_chars), encoding="utf-8")
    write_existing_docs(Path(args.existing_docs_output), product_docs)
    should_run = "true" if pr.get("mergedAt") else "false"
    write_github_output(
        args.github_output,
        {
            "pr_number": str(pr.get("number") or args.pr_number),
            "pr_title": str(pr.get("title") or ""),
            "pr_url": str(pr.get("url") or ""),
            "merged_at": str(pr.get("mergedAt") or ""),
            "default_branch": default_branch,
            "ledger_path": args.ledger_path,
            "scanned_pr_count": str(scanned_pr_count),
            "skipped_processed_pr_count": str(len(skipped_prs)),
            "should_run": should_run,
            "skip_reason": "" if should_run == "true" else "pull request is not merged",
        },
    )


def resolve_target_pr(
    args: argparse.Namespace,
    default_branch: str,
) -> tuple[dict[str, Any] | None, int, list[dict[str, Any]], dict[str, str] | None]:
    skipped_prs: list[dict[str, Any]] = []
    scanned_pr_count = 1
    scan_window_payload = None
    if args.pr_number:
        pr = fetch_pr(args.repo, args.pr_number)
    else:
        start, end = (
            explicit_scan_window(args.start_date, args.end_date)
            if args.start_date or args.end_date
            else default_scan_window(args.scan_days)
        )
        scan_window_payload = {
            "start_inclusive": iso_z(start),
            "end_exclusive": iso_z(end),
            "timezone": "UTC",
            "sort_order": "mergedAt ascending, then PR number ascending",
        }
        scanned_prs = fetch_merged_prs(args.repo, start, end, default_branch)
        scanned_pr_count = len(scanned_prs)
        pr, skipped_prs = select_unprocessed_pr(scanned_prs, load_ledger(Path(args.ledger_path)))
    return pr, scanned_pr_count, skipped_prs, scan_window_payload


def load_linked_context(root: Path, repo: str, pr: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    numbers = issue_numbers(pr)
    issues, _skipped_issue_numbers = fetch_existing_issues(repo, numbers)
    existing_issue_numbers = []
    for issue in issues:
        try:
            existing_issue_numbers.append(int(issue.get("number")))
        except (TypeError, ValueError):
            continue
    return issues, read_specs(root, existing_issue_numbers)


def run(args: argparse.Namespace) -> int:
    root = Path.cwd()
    default_branch = fetch_default_branch(args.repo, run_json=run_gh_json)
    pr, scanned_pr_count, skipped_prs, scan_window_payload = resolve_target_pr(args, default_branch)

    if pr is None:
        product_docs = read_existing_product_docs(root)
        write_no_pr_outputs(args, default_branch, product_docs, scanned_pr_count, skipped_prs, scan_window_payload)
        return 0

    issues, specs = load_linked_context(root, args.repo, pr)
    product_docs = read_existing_product_docs(root)
    write_selected_pr_outputs(
        args,
        default_branch,
        pr,
        issues,
        specs,
        product_docs,
        scanned_pr_count,
        skipped_prs,
        scan_window_payload,
    )
    return 0


def main() -> int:
    return run(parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
