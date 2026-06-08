#!/usr/bin/env python3
"""Apply GitHub-side updates for respond-to-pr-comment."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from artifact_contracts import write_github_output
from github_api import flatten_gh_pages as flatten_pages

PAGE_SIZE = 100
PAGE_INFO = "pageInfo { hasNextPage endCursor }"


def run_gh(args: list[str], *, capture: bool = False, check: bool = True) -> str:
    result = subprocess.run(
        ["gh", *args],
        check=check,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
        text=True,
    )
    return result.stdout.strip() if capture else ""


def run_gh_json(args: list[str]) -> Any:
    return json.loads(run_gh(args, capture=True))


def run_graphql(query: str, variables: dict[str, Any]) -> Any:
    args = ["api", "graphql", "-f", f"query={query}"]
    for key, value in variables.items():
        args.extend(["-F", f"{key}={value}"])
    return run_gh_json(args)


def load_json(path: Path, *, required: bool = True) -> dict[str, Any]:
    if not path.exists():
        if required:
            raise SystemExit(f"{path} was not created")
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    return value


def open_pr_for_branch(repo: str, branch_name: str) -> dict[str, Any] | None:
    owner = repo.split("/", 1)[0]
    pages = run_gh_json(
        [
            "api",
            f"repos/{repo}/pulls?state=open&head={owner}:{branch_name}&per_page=100",
            "--paginate",
            "--slurp",
        ]
    )
    prs = flatten_pages(pages)
    return prs[0] if prs else None


def update_original_pr(repo: str, number: int, metadata: dict[str, Any]) -> str:
    pr = run_gh_json(["pr", "view", str(number), "--repo", repo, "--json", "url"])
    return str(pr["url"])


def create_or_update_followup_pr(repo: str, context: dict[str, Any], metadata: dict[str, Any]) -> str:
    branch = metadata["branch_name"]
    existing = open_pr_for_branch(repo, branch)
    if existing:
        run_gh(["pr", "edit", str(existing["number"]), "--repo", repo, "--title", metadata["pr_title"], "--body", metadata["pr_summary"]])
        return str(existing["html_url"])
    body = metadata["pr_summary"]
    if f"#{context['pr_number']}" not in body:
        body = f"Follow-up to #{context['pr_number']}.\n\n{body}"
    return run_gh(
        [
            "pr",
            "create",
            "--repo",
            repo,
            "--base",
            str(context["base_branch"]),
            "--head",
            branch,
            "--title",
            metadata["pr_title"],
            "--body",
            body,
            "--draft",
        ],
        capture=True,
    )


def reply_to_issue_comment(repo: str, pr_number: int, message: str) -> None:
    run_gh(["pr", "comment", str(pr_number), "--repo", repo, "--body", message])


def reply_to_review_comment(repo: str, pr_number: int, comment_id: int, message: str) -> None:
    run_gh(["api", f"repos/{repo}/pulls/{pr_number}/comments/{comment_id}/replies", "-f", f"body={message}"])


def response_summary(metadata: dict[str, Any]) -> str:
    summary = str(metadata.get("pr_summary") or "").strip()
    if not summary:
        return ""
    lines = [
        line
        for line in summary.splitlines()
        if line.strip() and not line.strip().lower().startswith(("refs #", "closes #", "fixes #"))
    ]
    return "\n".join(lines).strip()


def issue_reply_body(metadata: dict[str, Any], pr_url: str) -> str:
    body = f"Applied requested changes on `{metadata['branch_name']}`."
    summary = response_summary(metadata)
    if summary:
        body = f"{body}\n\nSummary:\n{summary}"
    return f"{body}\n\n{pr_url}"


def extend_connection(connection: dict[str, Any], page: dict[str, Any]) -> None:
    connection["nodes"].extend(page["nodes"])
    connection["pageInfo"] = page["pageInfo"]


def fetch_review_threads_page(owner: str, name: str, pr_number: int, after: str | None = None) -> dict[str, Any]:
    after_clause = ", after: $after" if after else ""
    query = f"""
      query($owner: String!, $name: String!, $prNumber: Int!{', $after: String!' if after else ''}) {{
        repository(owner: $owner, name: $name) {{
          pullRequest(number: $prNumber) {{
            reviewThreads(first: {PAGE_SIZE}{after_clause}) {{
              {PAGE_INFO}
              nodes {{
                id
                isResolved
                comments(first: {PAGE_SIZE}) {{
                  {PAGE_INFO}
                  nodes {{ databaseId }}
                }}
              }}
            }}
          }}
        }}
      }}
    """
    variables: dict[str, Any] = {"owner": owner, "name": name, "prNumber": pr_number}
    if after:
        variables["after"] = after
    data = run_graphql(query, variables)
    return data["data"]["repository"]["pullRequest"]["reviewThreads"]


def paginate_thread_comments(thread: dict[str, Any]) -> None:
    connection = thread["comments"]
    while connection["pageInfo"]["hasNextPage"]:
        query = f"""
          query($id: ID!, $after: String!) {{
            node(id: $id) {{
              ... on PullRequestReviewThread {{
                comments(first: {PAGE_SIZE}, after: $after) {{
                  {PAGE_INFO}
                  nodes {{ databaseId }}
                }}
              }}
            }}
          }}
        """
        data = run_graphql(query, {"id": thread["id"], "after": connection["pageInfo"]["endCursor"]})
        extend_connection(connection, data["data"]["node"]["comments"])


def fetch_all_review_threads(repo: str, pr_number: int) -> list[dict[str, Any]]:
    owner, name = repo.split("/", 1)
    connection = fetch_review_threads_page(owner, name, pr_number)
    while connection["pageInfo"]["hasNextPage"]:
        page = fetch_review_threads_page(owner, name, pr_number, connection["pageInfo"]["endCursor"])
        extend_connection(connection, page)
    for thread in connection["nodes"]:
        paginate_thread_comments(thread)
    return connection["nodes"]


def thread_for_comment(repo: str, pr_number: int, comment_id: int) -> dict[str, Any]:
    for thread in fetch_all_review_threads(repo, pr_number):
        comments = (thread.get("comments") or {}).get("nodes") or []
        if any(comment.get("databaseId") == comment_id for comment in comments):
            return thread
    return {}


def resolve_thread_best_effort(repo: str, pr_number: int, comment_id: int) -> str:
    try:
        thread = thread_for_comment(repo, pr_number, comment_id)
        thread_id = thread.get("id")
        if not thread_id or thread.get("isResolved"):
            return ""
        mutation = "mutation($threadId: ID!) { resolveReviewThread(input: {threadId: $threadId}) { thread { id } } }"
        run_graphql(mutation, {"threadId": thread_id})
    except subprocess.CalledProcessError as exc:
        return (exc.stderr or str(exc)).strip()
    return ""


def apply_result(repo: str, context: dict[str, Any], metadata: dict[str, Any], resolved: dict[str, Any]) -> dict[str, str]:
    if context.get("branch_strategy") == "push-head":
        pr_url = update_original_pr(repo, int(context["pr_number"]), metadata)
    else:
        pr_url = create_or_update_followup_pr(repo, context, metadata)

    reply_to_issue_comment(
        repo,
        int(context["pr_number"]),
        issue_reply_body(metadata, pr_url),
    )

    warnings: list[str] = []
    pr_number = int(context["pr_number"])
    for entry in resolved.get("resolved_review_comments") or []:
        comment_id = int(entry["comment_id"])
        reply_to_review_comment(repo, pr_number, comment_id, entry["summary"])
        warning = resolve_thread_best_effort(repo, pr_number, comment_id)
        if warning:
            warnings.append(f"{comment_id}: {warning}")
    return {"pr_url": pr_url, "resolve_warnings": "\n".join(warnings)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--context", default="pr_comment_context.json")
    parser.add_argument("--metadata", default="pr-metadata.json")
    parser.add_argument("--resolved", default="resolved_review_comments.json")
    parser.add_argument("--github-output", default="")
    args = parser.parse_args()

    result = apply_result(
        args.repo,
        load_json(Path(args.context)),
        load_json(Path(args.metadata)),
        load_json(Path(args.resolved), required=False),
    )
    print(result["pr_url"])
    if result["resolve_warnings"]:
        print(result["resolve_warnings"])
    write_github_output(args.github_output, result)


if __name__ == "__main__":
    main()
