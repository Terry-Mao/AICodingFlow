#!/usr/bin/env python3
"""Prepare stable pull-request context for product docs synchronization."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


def run_gh_json(args: list[str]) -> Any:
    result = subprocess.run(["gh", *args], check=True, stdout=subprocess.PIPE, text=True)
    return json.loads(result.stdout)


def run_gh_text(args: list[str]) -> str:
    result = subprocess.run(["gh", *args], check=True, stdout=subprocess.PIPE, text=True)
    return result.stdout


def fetch_default_branch(repo: str) -> str:
    data = run_gh_json(["repo", "view", repo, "--json", "defaultBranchRef"])
    branch = (data.get("defaultBranchRef") or {}).get("name")
    if not branch:
        raise SystemExit("could not determine default branch")
    return branch


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


def fetch_pr_diff(repo: str, pr_number: str, max_chars: int) -> str:
    diff = run_gh_text(["pr", "diff", pr_number, "--repo", repo, "--patch"])
    if len(diff) <= max_chars:
        return diff
    return diff[:max_chars] + "\n\n[diff truncated by prepare_product_docs_sync_context.py]\n"


def issue_numbers(pr: dict[str, Any]) -> list[int]:
    numbers: list[int] = []
    for issue in pr.get("closingIssuesReferences") or []:
        try:
            number = int(issue.get("number"))
        except (TypeError, ValueError):
            continue
        if number not in numbers:
            numbers.append(number)
    return numbers


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
        "allowed_write_roots": ["docs/product/"],
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


def write_github_output(path: str | None, values: dict[str, str]) -> None:
    if not path:
        return
    with Path(path).open("a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--pr-number", required=True)
    parser.add_argument("--context-output", default="product-docs-sync-context.json")
    parser.add_argument("--markdown-output", default="product-docs-sync-context.md")
    parser.add_argument("--diff-output", default="product-docs-sync-diff.md")
    parser.add_argument("--existing-docs-output", default="product-docs-existing.md")
    parser.add_argument("--github-output", default="")
    parser.add_argument("--max-diff-chars", type=int, default=100000)
    args = parser.parse_args()

    root = Path.cwd()
    default_branch = fetch_default_branch(args.repo)
    pr = fetch_pr(args.repo, args.pr_number)
    numbers = issue_numbers(pr)
    issues = [fetch_issue(args.repo, number) for number in numbers]
    specs = read_specs(root, numbers)
    product_docs = read_existing_product_docs(root)
    should_run = "true" if pr.get("mergedAt") else "false"

    write_context_json(Path(args.context_output), args.repo, default_branch, pr, issues, specs, product_docs)
    write_markdown(Path(args.markdown_output), pr, issues, specs)
    Path(args.diff_output).write_text(fetch_pr_diff(args.repo, args.pr_number, args.max_diff_chars), encoding="utf-8")
    write_existing_docs(Path(args.existing_docs_output), product_docs)
    write_github_output(
        args.github_output,
        {
            "pr_number": str(pr.get("number") or args.pr_number),
            "pr_title": str(pr.get("title") or ""),
            "pr_url": str(pr.get("url") or ""),
            "merged_at": str(pr.get("mergedAt") or ""),
            "default_branch": default_branch,
            "should_run": should_run,
            "skip_reason": "" if should_run == "true" else "pull request is not merged",
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
