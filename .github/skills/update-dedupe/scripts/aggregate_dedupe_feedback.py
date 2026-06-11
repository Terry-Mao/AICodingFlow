#!/usr/bin/env python3
"""Aggregate recent GitHub duplicate issue closures for update-dedupe."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


PAGE_SIZE = 100
PAGE_INFO = "pageInfo { hasNextPage endCursor }"
AUTHOR_FIELDS = "author { __typename login }"
ISSUE_REF_FIELDS = """
  __typename
  ... on Issue {
    number
    title
    url
    repository { nameWithOwner }
  }
"""
MARKED_AS_DUPLICATE_EVENT_FIELDS = f"""
  id
  createdAt
  actor {{ __typename login }}
  canonical {{ {ISSUE_REF_FIELDS} }}
  duplicate {{ {ISSUE_REF_FIELDS} }}
"""
ISSUE_FIELDS = f"""
  id
  number
  title
  url
  state
  stateReason
  closedAt
  repository {{ nameWithOwner }}
  {AUTHOR_FIELDS}
  timelineItems(first: __PAGE_SIZE__, itemTypes: MARKED_AS_DUPLICATE_EVENT) {{
    __PAGE_INFO__
    nodes {{
      __typename
      ... on MarkedAsDuplicateEvent {{
        __MARKED_AS_DUPLICATE_EVENT_FIELDS__
      }}
    }}
  }}
"""


def run_gh_json(args: list[str]) -> Any:
    result = subprocess.run(["gh", *args], capture_output=True, text=True)
    if result.returncode != 0:
        if result.stderr:
            print(result.stderr, file=sys.stderr, end="" if result.stderr.endswith("\n") else "\n")
        raise subprocess.CalledProcessError(
            result.returncode,
            result.args,
            output=result.stdout,
            stderr=result.stderr,
        )
    text = result.stdout.strip()
    return json.loads(text) if text else None


def run_graphql(query: str, variables: dict[str, Any]) -> Any:
    args = ["api", "graphql", "-f", f"query={query}"]
    for key, value in variables.items():
        args.extend(["-F", f"{key}={value}"])
    return run_gh_json(args)


def default_repo() -> str:
    data = run_gh_json(["repo", "view", "--json", "nameWithOwner"])
    return data["nameWithOwner"]


def split_repo(repo: str) -> tuple[str, str]:
    if "/" not in repo:
        raise SystemExit("--repo must use owner/name")
    owner, name = repo.split("/", 1)
    if not owner or not name:
        raise SystemExit("--repo must use owner/name")
    return owner, name


def graphql_issue(owner: str, repo: str, number: int) -> dict[str, Any]:
    query = """
query($owner: String!, $repo: String!, $number: Int!) {
  repository(owner: $owner, name: $repo) {
    issue(number: $number) {
      __ISSUE_FIELDS__
    }
  }
}
"""
    query = issue_query(query)
    data = run_graphql(query, {"owner": owner, "repo": repo, "number": number})
    issue = data["data"]["repository"]["issue"]
    if issue is None:
        raise SystemExit(f"issue not found: {number}")
    paginate_issue_timeline(issue)
    return issue


def search_issues(repo: str, days: int) -> list[dict[str, Any]]:
    since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)).date().isoformat()
    search_query = f"repo:{repo} is:issue closed:>={since}"
    issues: list[dict[str, Any]] = []
    after = None

    while True:
        query = """
query($searchQuery: String!, $after: String) {
  search(query: $searchQuery, type: ISSUE, first: __PAGE_SIZE__, after: $after) {
    __PAGE_INFO__
    nodes {
      ... on Issue {
        __ISSUE_FIELDS__
      }
    }
  }
}
"""
        variables: dict[str, Any] = {"searchQuery": search_query}
        if after is not None:
            variables["after"] = after
        data = run_graphql(issue_query(query), variables)
        search = data["data"]["search"]
        for node in search["nodes"]:
            if node:
                paginate_issue_timeline(node)
                issues.append(node)
        if not search["pageInfo"]["hasNextPage"]:
            break
        after = search["pageInfo"]["endCursor"]

    return issues


def issue_query(query: str) -> str:
    return (
        query.replace("__ISSUE_FIELDS__", ISSUE_FIELDS)
        .replace("__MARKED_AS_DUPLICATE_EVENT_FIELDS__", MARKED_AS_DUPLICATE_EVENT_FIELDS)
        .replace("__PAGE_SIZE__", str(PAGE_SIZE))
        .replace("__PAGE_INFO__", PAGE_INFO)
    )


def extend_connection(connection: dict[str, Any], page: dict[str, Any]) -> None:
    connection["nodes"].extend(page["nodes"])
    connection["pageInfo"] = page["pageInfo"]


def paginate_issue_timeline(issue: dict[str, Any]) -> None:
    connection = issue["timelineItems"]
    while connection["pageInfo"]["hasNextPage"]:
        query = """
query($id: ID!, $after: String!) {
  node(id: $id) {
    ... on Issue {
      timelineItems(first: __PAGE_SIZE__, itemTypes: MARKED_AS_DUPLICATE_EVENT, after: $after) {
        __PAGE_INFO__
        nodes {
          __typename
          ... on MarkedAsDuplicateEvent {
            __MARKED_AS_DUPLICATE_EVENT_FIELDS__
          }
        }
      }
    }
  }
}
"""
        data = run_graphql(
            issue_query(query),
            {"id": issue["id"], "after": connection["pageInfo"]["endCursor"]},
        )
        page = data["data"]["node"]["timelineItems"]
        extend_connection(connection, page)


def author_login(node: dict[str, Any] | None) -> str | None:
    if not node:
        return None
    author = node.get("author")
    return author.get("login") if author else None


def actor_login(node: dict[str, Any] | None) -> str | None:
    if not node:
        return None
    actor = node.get("actor")
    return actor.get("login") if actor else None


def issue_ref(node: dict[str, Any] | None) -> dict[str, Any] | None:
    if not node or node.get("__typename") != "Issue":
        return None
    return {
        "number": node.get("number"),
        "title": node.get("title") or "",
        "url": node.get("url") or "",
        "repository": (node.get("repository") or {}).get("nameWithOwner") or "",
    }


def duplicate_event(issue: dict[str, Any]) -> dict[str, Any] | None:
    latest_event = None
    for event in issue.get("timelineItems", {}).get("nodes", []):
        if event and event.get("__typename") == "MarkedAsDuplicateEvent":
            canonical = issue_ref(event.get("canonical"))
            duplicate = issue_ref(event.get("duplicate"))
            if canonical and duplicate:
                latest_event = {
                    "event_type": "marked_as_duplicate",
                    "actor": actor_login(event) or "",
                    "created_at": event.get("createdAt"),
                    "canonical": canonical,
                    "duplicate": duplicate,
                }
    return latest_event


def normalize_issue(issue: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    base = {
        "number": issue.get("number"),
        "title": issue.get("title") or "",
        "url": issue.get("url") or "",
        "state": issue.get("state") or "",
        "state_reason": issue.get("stateReason") or "",
        "closed_at": issue.get("closedAt"),
        "repository": (issue.get("repository") or {}).get("nameWithOwner") or "",
        "author": author_login(issue) or "",
    }

    if str(base["state_reason"]).lower() != "duplicate":
        return None, {**base, "reason": "state_reason_not_duplicate"}

    event = duplicate_event(issue)
    if event is None:
        return None, {**base, "reason": "missing_marked_as_duplicate_event"}

    duplicate = event["duplicate"]
    if duplicate["number"] != base["number"] or (
        base["repository"] and duplicate["repository"] and duplicate["repository"] != base["repository"]
    ):
        return None, {**base, "reason": "duplicate_event_does_not_match_issue"}

    canonical = event["canonical"]
    normalized = {
        **base,
        "state_reason": "duplicate",
        "canonical": {
            "number": canonical["number"],
            "title": canonical["title"],
            "url": canonical["url"],
            "repository": canonical["repository"],
        },
        "evidence": {
            "event_type": event["event_type"],
            "actor": event["actor"],
            "created_at": event["created_at"],
        },
    }
    return normalized, None


def issue_summary(issue: dict[str, Any]) -> dict[str, Any]:
    return {
        "number": issue["number"],
        "title": issue["title"],
        "url": issue["url"],
    }


def build_clusters(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_canonical: dict[tuple[str, int], dict[str, Any]] = {}
    seen_duplicates: set[int] = set()

    for issue in sorted(issues, key=lambda item: item["number"]):
        if issue["number"] in seen_duplicates:
            continue
        seen_duplicates.add(issue["number"])
        canonical = issue["canonical"]
        key = (canonical.get("repository") or "", int(canonical["number"]))
        cluster = by_canonical.setdefault(
            key,
            {
                "canonical": canonical,
                "duplicates": [],
            },
        )
        cluster["duplicates"].append(issue_summary(issue))

    return sorted(
        by_canonical.values(),
        key=lambda cluster: (
            cluster["canonical"].get("repository") or "",
            int(cluster["canonical"]["number"]),
        ),
    )


def normalize_issues(raw_issues: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    issues = []
    skipped = []
    for raw_issue in raw_issues:
        normalized, skip = normalize_issue(raw_issue)
        if normalized:
            issues.append(normalized)
        elif skip:
            skipped.append(skip)
    return issues, skipped


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--issue", type=int)
    parser.add_argument("--output")
    args = parser.parse_args()

    repo = args.repo or default_repo()
    owner, name = split_repo(repo)
    raw_issues = [graphql_issue(owner, name, args.issue)] if args.issue else search_issues(repo, args.days)
    issues, skipped = normalize_issues(raw_issues)
    payload = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "repo": repo,
        "days": args.days,
        "issue": args.issue,
        "issues": issues,
        "clusters": build_clusters(issues),
        "skipped": skipped,
    }

    if args.output:
        output = Path(args.output)
    else:
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        handle = tempfile.NamedTemporaryFile(
            prefix=f"update-dedupe-feedback-{stamp}-",
            suffix=".json",
            delete=False,
        )
        output = Path(handle.name)
        handle.close()
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
