#!/usr/bin/env python3
"""Resolve and write stable spec context for PR review."""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any


APPROVED_LABEL = "plan-approved"
SPEC_CONTEXT_NONE = "Spec Context: No approved or repository spec context was found for this PR."
DIFF_FILE_RE = re.compile(r"^FILE\s+(.+?)\s*$")


def run_gh_json(args: list[str]) -> Any:
    result = subprocess.run(["gh", *args], check=True, stdout=subprocess.PIPE, text=True)
    return json.loads(result.stdout)


def flatten_pages(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list) and value and all(isinstance(page, list) for page in value):
        return [item for page in value for item in page]
    if isinstance(value, list):
        return value
    raise SystemExit("unexpected GitHub API response")


def load_event(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def issue_number_from_text(text: str) -> int | None:
    patterns = [
        r"(?<![A-Za-z0-9-])(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?|refs?)\s+#(\d+)",
        r"(?<![A-Za-z0-9-])(?:issue|gh)(?![A-Za-z0-9-])[-/\s#]*(\d+)",
        r"(?:^|/)[A-Za-z0-9-]+-(\d+)$",
        r"(?<![A-Za-z0-9-])#(\d+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text or "", re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def resolve_issue_number(pr: dict[str, Any]) -> int | None:
    for text in (
        pr.get("body") or "",
        pr.get("title") or "",
        (pr.get("head") or {}).get("ref") or "",
    ):
        issue_number = issue_number_from_text(text)
        if issue_number is not None:
            return issue_number
    return None


def spec_file_paths(issue_number: int) -> list[str]:
    spec_dir = f"specs/issue-{issue_number}"
    return [f"{spec_dir}/product.md", f"{spec_dir}/tech.md"]


def changed_files_from_pr_files(pr_files: list[dict[str, Any]]) -> list[str]:
    return [item.get("filename", "") for item in pr_files if item.get("filename")]


def changed_files_from_diff_text(pr_diff_text: str) -> list[str]:
    files: list[str] = []
    for line in pr_diff_text.splitlines():
        match = DIFF_FILE_RE.match(line)
        if match:
            path = match.group(1).strip()
            if path:
                files.append(path)
    return files


def fetch_pr_files(repo: str, pr_number: int) -> list[dict[str, Any]]:
    pages = run_gh_json(["api", f"repos/{repo}/pulls/{pr_number}/files?per_page=100", "--paginate", "--slurp"])
    return flatten_pages(pages)


def label_names(pr: dict[str, Any]) -> list[str]:
    return [label.get("name", "") for label in pr.get("labels", []) if label.get("name")]


def pr_head_ref(pr: dict[str, Any]) -> str:
    return (pr.get("head") or {}).get("ref") or ""


def pr_head_repo_full_name(pr: dict[str, Any]) -> str:
    return ((pr.get("head") or {}).get("repo") or {}).get("full_name") or ""


def spec_pr_summary(pr: dict[str, Any], paths: list[str]) -> dict[str, Any]:
    return {
        "number": pr.get("number"),
        "url": pr.get("html_url") or "",
        "updated_at": pr.get("updated_at") or "",
        "head_ref_name": pr_head_ref(pr),
        "head_repo_full_name": pr_head_repo_full_name(pr),
        "spec_files": paths,
    }


def fetch_spec_prs(repo: str, issue_number: int) -> list[dict[str, Any]]:
    owner = repo.split("/", 1)[0]
    branch = f"spec/issue-{issue_number}"
    pages = run_gh_json(
        [
            "api",
            f"repos/{repo}/pulls?state=open&head={owner}:{branch}&per_page=100",
            "--paginate",
            "--slurp",
        ]
    )
    return [pr for pr in flatten_pages(pages) if pr_head_ref(pr) == branch]


def fetch_file_content(repo: str, path: str, ref: str) -> str | None:
    try:
        response = run_gh_json(["api", f"repos/{repo}/contents/{path}?ref={ref}"])
    except subprocess.CalledProcessError:
        return None
    if not isinstance(response, dict) or response.get("encoding") != "base64":
        return None
    content = response.get("content") or ""
    return base64.b64decode(content).decode("utf-8")


def collect_spec_entries(repo: str, paths: list[str], ref: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for path in paths:
        content = fetch_file_content(repo, path, ref)
        if content is not None:
            entries.append({"path": path, "content": content})
    return entries


def build_empty_context(issue_number: int | None, changed_files: list[str], pr_files: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "issue_number": issue_number,
        "spec_context_source": "",
        "selected_spec_pr": None,
        "approved_spec_prs": [],
        "unapproved_spec_prs": [],
        "spec_entries": [],
        "changed_files": changed_files,
        "pr_files": pr_files,
    }


def resolve_spec_context(
    repo: str,
    event: dict[str, Any],
    changed_files: list[str] | None = None,
) -> dict[str, Any]:
    pr = event["pull_request"]
    issue_number = resolve_issue_number(pr)
    if changed_files is None:
        pr_number = int(pr["number"])
        pr_files = fetch_pr_files(repo, pr_number)
        resolved_changed_files = changed_files_from_pr_files(pr_files)
    else:
        resolved_changed_files = changed_files
        pr_files = [{"filename": path} for path in changed_files]
    context = build_empty_context(issue_number, resolved_changed_files, pr_files)

    if issue_number is None:
        return context

    paths = spec_file_paths(issue_number)
    spec_prs = fetch_spec_prs(repo, issue_number)
    approved = [spec_pr_summary(pr, paths) for pr in spec_prs if APPROVED_LABEL in label_names(pr)]
    unapproved = [spec_pr_summary(pr, paths) for pr in spec_prs if APPROVED_LABEL not in label_names(pr)]
    approved.sort(key=lambda item: item["updated_at"], reverse=True)
    unapproved.sort(key=lambda item: item["updated_at"], reverse=True)
    context["approved_spec_prs"] = approved
    context["unapproved_spec_prs"] = unapproved

    if approved:
        selected = approved[0]
        entries = collect_spec_entries(
            selected["head_repo_full_name"],
            paths,
            selected["head_ref_name"],
        )
        if entries:
            context["spec_context_source"] = "approved-pr"
            context["selected_spec_pr"] = selected
            context["spec_entries"] = entries
            return context

    base = pr.get("base") or {}
    default_branch = (base.get("repo") or {}).get("default_branch") or "main"
    fallback_ref = base.get("sha") or base.get("ref") or default_branch
    entries = collect_spec_entries(repo, paths, fallback_ref)
    if entries:
        context["spec_context_source"] = "directory"
        context["spec_entries"] = entries

    return context


def format_spec_context_text(context: dict[str, Any]) -> str:
    entries = context.get("spec_entries") or []
    if not entries:
        return SPEC_CONTEXT_NONE + "\n"

    lines: list[str] = []
    if context.get("spec_context_source") == "approved-pr":
        selected = context.get("selected_spec_pr") or {}
        lines.append(f"Linked approved spec PR: [#{selected.get('number')}]({selected.get('url')})")
        lines.append("")
    elif context.get("spec_context_source") == "directory":
        lines.append("Repository spec context was found in `specs/`.")
        lines.append("")

    for entry in entries:
        lines.append(f"## {entry['path']}")
        lines.append("")
        lines.append(entry["content"].rstrip())
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--event-path", default=os.environ.get("PR_EVENT_PATH") or os.environ.get("GITHUB_EVENT_PATH", ""))
    parser.add_argument("--changed-files-from-diff", default="")
    parser.add_argument("--output", default="spec_context.md")
    args = parser.parse_args()

    if not args.repo:
        raise SystemExit("--repo or GITHUB_REPOSITORY is required")
    if not args.event_path:
        raise SystemExit("--event-path, PR_EVENT_PATH, or GITHUB_EVENT_PATH is required")

    changed_files = None
    if args.changed_files_from_diff:
        changed_files = changed_files_from_diff_text(Path(args.changed_files_from_diff).read_text(encoding="utf-8"))
    context = resolve_spec_context(args.repo, load_event(args.event_path), changed_files)
    output_path = Path(args.output)
    if context.get("spec_entries"):
        output_path.write_text(format_spec_context_text(context), encoding="utf-8")
    elif output_path.exists():
        output_path.unlink()
    print(f"spec_context_source={context['spec_context_source'] or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
