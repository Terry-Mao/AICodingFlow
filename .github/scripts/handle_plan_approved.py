#!/usr/bin/env python3
"""Sync issue lifecycle state when a spec PR is labeled plan-approved."""

from __future__ import annotations

import argparse
import os
import subprocess
from typing import Any

from artifact_contracts import load_json, write_github_output
from github_api import fetch_default_branch, run_gh_json
from github_event import assignee_logins, label_names
from issue_refs import issue_number_from_branch, issue_number_from_strict_text


APPROVED_LABEL = "plan-approved"
READY_TO_SPEC_LABEL = "ready-to-spec"
READY_TO_IMPLEMENT_LABEL = "ready-to-implement"
IMPLEMENTATION_WORKFLOW = "create-implementation-from-issue.yml"


def run_gh(args: list[str]) -> None:
    subprocess.run(["gh", *args], check=True)


def load_event(path: str | None) -> dict[str, Any]:
    return load_json(path, default={})


def head_ref(pr: dict[str, Any]) -> str:
    head = pr.get("head") or {}
    return head.get("ref") or pr.get("headRefName") or ""


def head_repo_full_name(pr: dict[str, Any]) -> str:
    head = pr.get("head") or {}
    repo = head.get("repo") or {}
    return repo.get("full_name") or pr.get("headRepository", {}).get("nameWithOwner") or ""


def issue_number_from_explicit_text(text: str) -> int | None:
    return issue_number_from_strict_text(text)


def issue_number_from_spec_branch(branch: str) -> int | None:
    return issue_number_from_branch(branch, prefix="spec/issue-", include_suffix=False)


def resolve_linked_issue_number(pr: dict[str, Any]) -> int | None:
    for text in (pr.get("body") or "", pr.get("title") or ""):
        issue_number = issue_number_from_explicit_text(text)
        if issue_number is not None:
            return issue_number
    return issue_number_from_spec_branch(head_ref(pr))


def is_spec_pr(pr: dict[str, Any], issue_number: int) -> bool:
    return head_ref(pr) == f"spec/issue-{issue_number}"


def normalize_api_pr(pr: dict[str, Any], labels: list[dict[str, Any]]) -> dict[str, Any]:
    normalized = dict(pr)
    normalized["labels"] = labels
    return normalized


def fetch_pr(repo: str, pr_number: int) -> dict[str, Any]:
    pr = run_gh_json(["api", f"repos/{repo}/pulls/{pr_number}"])
    labels = run_gh_json(["api", f"repos/{repo}/issues/{pr_number}/labels?per_page=100"])
    if not isinstance(labels, list):
        raise SystemExit("unexpected pull request labels response")
    return normalize_api_pr(pr, labels)


def fetch_issue(repo: str, issue_number: int) -> dict[str, Any]:
    return run_gh_json(
        [
            "issue",
            "view",
            str(issue_number),
            "--repo",
            repo,
            "--json",
            "number,title,labels,assignees,url,state",
        ]
    )


def remove_ready_to_spec_label(repo: str, issue_number: int, dry_run: bool = False) -> bool:
    if dry_run:
        return True
    result = subprocess.run(
        ["gh", "api", f"repos/{repo}/issues/{issue_number}/labels/{READY_TO_SPEC_LABEL}", "-X", "DELETE"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode == 0:
        return True
    error_text = f"{result.stdout}\n{result.stderr}"
    if "HTTP 404" in error_text or "Not Found" in error_text:
        return False
    raise subprocess.CalledProcessError(
        result.returncode,
        result.args,
        output=result.stdout,
        stderr=result.stderr,
    )


def dispatch_implementation(repo: str, default_branch: str, issue_number: int, agent_login: str, dry_run: bool = False) -> None:
    if dry_run:
        return
    run_gh(
        [
            "workflow",
            "run",
            IMPLEMENTATION_WORKFLOW,
            "--repo",
            repo,
            "--ref",
            default_branch,
            "-f",
            f"issue={issue_number}",
            "-f",
            f"agent_login={agent_login}",
        ]
    )


def event_pr_number(event: dict[str, Any]) -> int | None:
    pr = event.get("pull_request") or {}
    number = pr.get("number") or event.get("number")
    return int(number) if number else None


def event_pull_request(event: dict[str, Any]) -> dict[str, Any] | None:
    pr = event.get("pull_request")
    return pr if isinstance(pr, dict) else None


def repository_default_branch(event: dict[str, Any]) -> str:
    repository = event.get("repository") or {}
    return repository.get("default_branch") or ""


def resolve_event_pr(args: argparse.Namespace, event: dict[str, Any]) -> dict[str, Any] | None:
    pr = event_pull_request(event)
    if pr:
        return pr
    pr_number = int(args.pr_number) if args.pr_number else event_pr_number(event)
    return fetch_pr(args.repo, pr_number) if pr_number else None


def validate_spec_pr(pr: dict[str, Any]) -> tuple[int | None, str]:
    issue_number = resolve_linked_issue_number(pr)
    if issue_number is None:
        return None, "linked issue not found"
    if not is_spec_pr(pr, issue_number):
        return issue_number, "pull request is not a spec PR"
    if APPROVED_LABEL not in label_names(pr):
        return issue_number, "pull request is missing plan-approved"
    return issue_number, ""


def implementation_skip_reason(
    *,
    has_ready_to_implement: bool,
    agent_login: str,
    has_agent_assignee: bool,
) -> str:
    if not has_ready_to_implement:
        return f"missing {READY_TO_IMPLEMENT_LABEL}"
    if not agent_login:
        return "missing agent login"
    if not has_agent_assignee:
        return "missing bot assignee"
    return ""


def handle_plan_approved(args: argparse.Namespace) -> dict[str, str]:
    event = load_event(args.event_path)
    pr = resolve_event_pr(args, event)
    if not pr:
        return build_outputs(skip_reason="pull request is not available")

    issue_number, skip_reason = validate_spec_pr(pr)
    if skip_reason:
        return build_outputs(issue_number=issue_number, skip_reason=skip_reason)

    issue = fetch_issue(args.repo, issue_number)
    issue_labels = set(label_names(issue))
    issue_assignees = set(assignee_logins(issue))

    removed_ready_to_spec = False
    if READY_TO_SPEC_LABEL in issue_labels:
        removed_ready_to_spec = remove_ready_to_spec_label(args.repo, issue_number, args.dry_run)

    agent_login = args.agent_login.strip()
    has_ready_to_implement = READY_TO_IMPLEMENT_LABEL in issue_labels
    has_agent_assignee = bool(agent_login and agent_login in issue_assignees)
    default_branch = repository_default_branch(event) or fetch_default_branch(args.repo)

    skip_reason = implementation_skip_reason(
        has_ready_to_implement=has_ready_to_implement,
        agent_login=agent_login,
        has_agent_assignee=has_agent_assignee,
    )
    implementation_dispatched = not skip_reason
    if implementation_dispatched:
        dispatch_implementation(args.repo, default_branch, issue_number, agent_login, args.dry_run)

    return build_outputs(
        issue_number=issue_number,
        removed_ready_to_spec=removed_ready_to_spec,
        has_ready_to_implement=has_ready_to_implement,
        has_agent_assignee=has_agent_assignee,
        implementation_dispatched=implementation_dispatched,
        skip_reason=skip_reason,
    )


def build_outputs(
    *,
    issue_number: int | None = None,
    removed_ready_to_spec: bool = False,
    has_ready_to_implement: bool = False,
    has_agent_assignee: bool = False,
    implementation_dispatched: bool = False,
    skip_reason: str = "",
) -> dict[str, str]:
    return {
        "issue_number": str(issue_number or ""),
        "removed_ready_to_spec": "true" if removed_ready_to_spec else "false",
        "has_ready_to_implement": "true" if has_ready_to_implement else "false",
        "has_agent_assignee": "true" if has_agent_assignee else "false",
        "implementation_dispatched": "true" if implementation_dispatched else "false",
        "skip_reason": skip_reason,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--event-name", default=os.environ.get("GITHUB_EVENT_NAME", ""))
    parser.add_argument("--event-path", default=os.environ.get("GITHUB_EVENT_PATH", ""))
    parser.add_argument("--pr-number", default="")
    parser.add_argument("--agent-login", default="")
    parser.add_argument("--github-output", default=os.environ.get("GITHUB_OUTPUT", ""))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    outputs = handle_plan_approved(args)
    for key, value in outputs.items():
        print(f"{key}={value}")
    write_github_output(args.github_output, outputs)


if __name__ == "__main__":
    main()
