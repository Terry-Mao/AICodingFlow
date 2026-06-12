#!/usr/bin/env python3
"""Aggregate recent GitHub triage correction signals for update-triage."""

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
COMMENT_BODY_LIMIT = 1200
MAINTAINER_ASSOCIATIONS = {"OWNER", "MEMBER", "COLLABORATOR"}
MAINTAINER_PERMISSIONS = {"admin", "maintain", "write", "triage"}
TRIAGE_COMMENT_MARKER = "<!-- aicodingflow:triage-issue -->"
PAGE_INFO = "pageInfo { hasNextPage endCursor }"
AUTHOR_FIELDS = "author { __typename login }"
LABEL_FIELDS = "label { name }"
ACTOR_FIELDS = "actor { __typename login }"
COMMENT_FIELDS = f"""
  id
  author {{ __typename login }}
  authorAssociation
  createdAt
  url
  body
"""
TIMELINE_FIELDS = f"""
  __typename
  ... on LabeledEvent {{
    id
    createdAt
    {ACTOR_FIELDS}
    {LABEL_FIELDS}
  }}
  ... on UnlabeledEvent {{
    id
    createdAt
    {ACTOR_FIELDS}
    {LABEL_FIELDS}
  }}
  ... on ReopenedEvent {{
    id
    createdAt
    {ACTOR_FIELDS}
  }}
  ... on ClosedEvent {{
    id
    createdAt
    {ACTOR_FIELDS}
  }}
  ... on MarkedAsDuplicateEvent {{
    id
    createdAt
    {ACTOR_FIELDS}
  }}
"""
ISSUE_FIELDS = f"""
  id
  number
  title
  url
  state
  stateReason
  createdAt
  updatedAt
  closedAt
  repository {{ nameWithOwner }}
  {AUTHOR_FIELDS}
  labels(first: 100) {{
    nodes {{ name }}
  }}
  comments(first: __PAGE_SIZE__) {{
    __PAGE_INFO__
    nodes {{
      __COMMENT_FIELDS__
    }}
  }}
  timelineItems(
    first: __PAGE_SIZE__,
    itemTypes: [LABELED_EVENT, UNLABELED_EVENT, REOPENED_EVENT, CLOSED_EVENT, MARKED_AS_DUPLICATE_EVENT]
  ) {{
    __PAGE_INFO__
    nodes {{
      __TIMELINE_FIELDS__
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


def run_repo_api_json(path: str) -> Any:
    return run_gh_json(["api", path])


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


def issue_query(query: str) -> str:
    return (
        query.replace("__ISSUE_FIELDS__", ISSUE_FIELDS)
        .replace("__COMMENT_FIELDS__", COMMENT_FIELDS)
        .replace("__TIMELINE_FIELDS__", TIMELINE_FIELDS)
        .replace("__PAGE_SIZE__", str(PAGE_SIZE))
        .replace("__PAGE_INFO__", PAGE_INFO)
    )


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
    data = run_graphql(issue_query(query), {"owner": owner, "repo": repo, "number": number})
    issue = data["data"]["repository"]["issue"]
    if issue is None:
        raise SystemExit(f"issue not found: {number}")
    paginate_issue(issue)
    return issue


def search_issues(repo: str, days: int) -> list[dict[str, Any]]:
    since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)).date().isoformat()
    search_query = f"repo:{repo} is:issue updated:>={since}"
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
                paginate_issue(node)
                issues.append(node)
        if not search["pageInfo"]["hasNextPage"]:
            break
        after = search["pageInfo"]["endCursor"]

    return issues


def extend_connection(connection: dict[str, Any], page: dict[str, Any]) -> None:
    connection["nodes"].extend(page["nodes"])
    connection["pageInfo"] = page["pageInfo"]


def paginate_issue(issue: dict[str, Any]) -> None:
    paginate_issue_timeline(issue)
    paginate_issue_comments(issue)


def paginate_issue_timeline(issue: dict[str, Any]) -> None:
    connection = issue["timelineItems"]
    while connection["pageInfo"]["hasNextPage"]:
        query = """
query($id: ID!, $after: String!) {
  node(id: $id) {
    ... on Issue {
      timelineItems(
        first: __PAGE_SIZE__,
        itemTypes: [LABELED_EVENT, UNLABELED_EVENT, REOPENED_EVENT, CLOSED_EVENT, MARKED_AS_DUPLICATE_EVENT],
        after: $after
      ) {
        __PAGE_INFO__
        nodes {
          __TIMELINE_FIELDS__
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


def paginate_issue_comments(issue: dict[str, Any]) -> None:
    connection = issue["comments"]
    while connection["pageInfo"]["hasNextPage"]:
        query = """
query($id: ID!, $after: String!) {
  node(id: $id) {
    ... on Issue {
      comments(first: __PAGE_SIZE__, after: $after) {
        __PAGE_INFO__
        nodes {
          __COMMENT_FIELDS__
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
        page = data["data"]["node"]["comments"]
        extend_connection(connection, page)


def login_from_user(node: dict[str, Any] | None) -> str:
    if not node:
        return ""
    return str(node.get("login") or "")


def author_login(node: dict[str, Any] | None) -> str:
    if not node:
        return ""
    return login_from_user(node.get("author"))


def actor_login(node: dict[str, Any] | None) -> str:
    if not node:
        return ""
    return login_from_user(node.get("actor"))


def typename_from_user(node: dict[str, Any] | None) -> str:
    return str((node or {}).get("__typename") or "")


def is_bot_user(login: str, typename: str = "") -> bool:
    return typename == "Bot" or login.endswith("[bot]") or login.lower().endswith("-bot")


def parse_timestamp(value: object) -> dt.datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = dt.datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def created_after(value: object, timestamp: dt.datetime) -> bool:
    parsed = parse_timestamp(value)
    return parsed is not None and parsed > timestamp


def repo_permission(repo: str, login: str, cache: dict[str, str]) -> str:
    if login in cache:
        return cache[login]
    try:
        data = run_repo_api_json(f"repos/{repo}/collaborators/{login}/permission")
    except (subprocess.CalledProcessError, KeyError, TypeError, json.JSONDecodeError):
        cache[login] = ""
    else:
        cache[login] = str(data.get("permission") or "")
    return cache[login]


def is_maintainer_signal(
    *,
    repo: str,
    login: str,
    association: str = "",
    typename: str = "",
    maintainer_logins: set[str] | None = None,
    include_bots: bool = False,
    permission_cache: dict[str, str] | None = None,
    org_member_fallback: bool = False,
) -> bool:
    if not login:
        return False
    if is_bot_user(login, typename) and not include_bots:
        return False
    if maintainer_logins and login in maintainer_logins:
        return True
    if association in MAINTAINER_ASSOCIATIONS:
        return True
    if org_member_fallback:
        cache = permission_cache if permission_cache is not None else {}
        return repo_permission(repo, login, cache) in MAINTAINER_PERMISSIONS
    return False


def label_name(event: dict[str, Any]) -> str:
    return str((event.get("label") or {}).get("name") or "")


def current_labels(issue: dict[str, Any]) -> list[str]:
    labels = (issue.get("labels") or {}).get("nodes") or []
    return sorted(str(label.get("name") or "") for label in labels if label and label.get("name"))


def truncated_body(body: str) -> str:
    text = body.strip()
    if len(text) <= COMMENT_BODY_LIMIT:
        return text
    return text[: COMMENT_BODY_LIMIT - 1].rstrip() + "…"


def triage_comment_created_at(issue: dict[str, Any]) -> str:
    candidates: list[tuple[dt.datetime, str]] = []
    for comment in (issue.get("comments") or {}).get("nodes") or []:
        if not comment:
            continue
        author = comment.get("author") or {}
        if TRIAGE_COMMENT_MARKER not in str(comment.get("body") or ""):
            continue
        if not is_bot_user(login_from_user(author), typename_from_user(author)):
            continue
        created_at = str(comment.get("createdAt") or "")
        parsed = parse_timestamp(created_at)
        if parsed is not None:
            candidates.append((parsed, created_at))
    return max(candidates, default=(dt.datetime.min.replace(tzinfo=dt.timezone.utc), ""))[1]


def triaged_label_created_at(issue: dict[str, Any]) -> str:
    candidates: list[tuple[dt.datetime, str]] = []
    for event in (issue.get("timelineItems") or {}).get("nodes") or []:
        if not event or event.get("__typename") != "LabeledEvent" or label_name(event) != "triaged":
            continue
        actor = event.get("actor") or {}
        if not is_bot_user(login_from_user(actor), typename_from_user(actor)):
            continue
        created_at = str(event.get("createdAt") or "")
        parsed = parse_timestamp(created_at)
        if parsed is not None:
            candidates.append((parsed, created_at))
    return max(candidates, default=(dt.datetime.min.replace(tzinfo=dt.timezone.utc), ""))[1]


def issue_triaged_at(issue: dict[str, Any]) -> tuple[str, str]:
    comment_created_at = triage_comment_created_at(issue)
    if comment_created_at:
        return comment_created_at, "bot_triage_comment"
    label_created_at = triaged_label_created_at(issue)
    if label_created_at:
        return label_created_at, "bot_labeled_triaged"
    return "", ""


def duplicate_skip_reason(issue: dict[str, Any], event: dict[str, Any]) -> str:
    if event.get("__typename") == "MarkedAsDuplicateEvent":
        return "marked_as_duplicate_owned_by_update_dedupe"
    if event.get("__typename") == "ClosedEvent" and str(issue.get("stateReason") or "").lower() == "duplicate":
        return "duplicate_closure_owned_by_update_dedupe"
    if str(issue.get("stateReason") or "").lower() == "duplicate":
        return "state_reason_duplicate_owned_by_update_dedupe"
    if label_name(event).lower() == "closed-as-duplicate":
        return "closed_as_duplicate_label_owned_by_update_dedupe"
    return ""


def normalize_label_event(
    repo: str,
    event: dict[str, Any],
    maintainer_logins: set[str],
    include_bots: bool,
    permission_cache: dict[str, str],
    org_member_fallback: bool,
) -> dict[str, Any] | None:
    event_type_by_graphql = {
        "LabeledEvent": "labeled",
        "UnlabeledEvent": "unlabeled",
    }
    event_type = event_type_by_graphql.get(str(event.get("__typename") or ""))
    label = label_name(event)
    if not event_type or not label:
        return None
    actor = event.get("actor") or {}
    login = login_from_user(actor)
    if not is_maintainer_signal(
        repo=repo,
        login=login,
        typename=typename_from_user(actor),
        maintainer_logins=maintainer_logins,
        include_bots=include_bots,
        permission_cache=permission_cache,
        org_member_fallback=org_member_fallback,
    ):
        return None
    return {
        "event_type": event_type,
        "label": label,
        "actor": login,
        "actor_type": typename_from_user(actor),
        "created_at": event.get("createdAt"),
    }


def normalize_reopened_event(
    repo: str,
    event: dict[str, Any],
    maintainer_logins: set[str],
    include_bots: bool,
    permission_cache: dict[str, str],
    org_member_fallback: bool,
) -> dict[str, Any] | None:
    if event.get("__typename") != "ReopenedEvent":
        return None
    actor = event.get("actor") or {}
    login = login_from_user(actor)
    if not is_maintainer_signal(
        repo=repo,
        login=login,
        typename=typename_from_user(actor),
        maintainer_logins=maintainer_logins,
        include_bots=include_bots,
        permission_cache=permission_cache,
        org_member_fallback=org_member_fallback,
    ):
        return None
    return {
        "event_type": "reopened",
        "actor": login,
        "actor_type": typename_from_user(actor),
        "created_at": event.get("createdAt"),
    }


def normalize_comment(
    repo: str,
    comment: dict[str, Any],
    maintainer_logins: set[str],
    include_bots: bool,
    permission_cache: dict[str, str],
    org_member_fallback: bool,
) -> dict[str, Any] | None:
    author = comment.get("author") or {}
    login = login_from_user(author)
    if not is_maintainer_signal(
        repo=repo,
        login=login,
        association=str(comment.get("authorAssociation") or ""),
        typename=typename_from_user(author),
        maintainer_logins=maintainer_logins,
        include_bots=include_bots,
        permission_cache=permission_cache,
        org_member_fallback=org_member_fallback,
    ):
        return None
    return {
        "author": login,
        "author_type": typename_from_user(author),
        "author_association": str(comment.get("authorAssociation") or ""),
        "created_at": comment.get("createdAt"),
        "url": comment.get("url") or "",
        "body": truncated_body(str(comment.get("body") or "")),
    }


def normalize_issue(
    issue: dict[str, Any],
    repo: str,
    maintainer_logins: set[str] | None = None,
    include_bots: bool = False,
    permission_cache: dict[str, str] | None = None,
    org_member_fallback: bool = False,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    maintainer_logins = maintainer_logins or set()
    permission_cache = permission_cache if permission_cache is not None else {}
    labels = current_labels(issue)
    base = {
        "number": issue.get("number"),
        "title": issue.get("title") or "",
        "url": issue.get("url") or "",
        "state": issue.get("state") or "",
        "state_reason": issue.get("stateReason"),
        "created_at": issue.get("createdAt"),
        "updated_at": issue.get("updatedAt"),
        "closed_at": issue.get("closedAt"),
        "author": author_login(issue),
        "current_labels": labels,
    }

    triaged_at, triaged_at_source = issue_triaged_at(issue)
    if not triaged_at:
        return None, {**base, "reason": "missing_reliable_triage_timestamp"}
    triaged_timestamp = parse_timestamp(triaged_at)
    if triaged_timestamp is None:
        return None, {
            **base,
            "reason": "invalid_triage_timestamp",
            "triaged_at": triaged_at,
            "triaged_at_source": triaged_at_source,
        }
    if str(issue.get("stateReason") or "").lower() == "duplicate":
        return None, {
            **base,
            "reason": "state_reason_duplicate_owned_by_update_dedupe",
            "triaged_at": triaged_at,
            "triaged_at_source": triaged_at_source,
        }

    label_events: list[dict[str, Any]] = []
    reopened_events: list[dict[str, Any]] = []
    skipped_signals: list[dict[str, Any]] = []
    seen_label_events: set[tuple[str, str, str, str]] = set()

    for event in (issue.get("timelineItems") or {}).get("nodes") or []:
        if not event:
            continue
        if not created_after(event.get("createdAt"), triaged_timestamp):
            continue
        skip_reason = duplicate_skip_reason(issue, event)
        if skip_reason:
            skipped_signals.append(
                {
                    "event_type": event.get("__typename") or "",
                    "actor": actor_login(event),
                    "created_at": event.get("createdAt"),
                    "reason": skip_reason,
                }
            )
            continue

        label_event = normalize_label_event(
            repo,
            event,
            maintainer_logins,
            include_bots,
            permission_cache,
            org_member_fallback,
        )
        if label_event:
            key = (
                label_event["event_type"],
                label_event["label"],
                label_event["actor"],
                str(label_event["created_at"] or ""),
            )
            if key not in seen_label_events:
                seen_label_events.add(key)
                label_events.append(label_event)
            continue

        reopened_event = normalize_reopened_event(
            repo,
            event,
            maintainer_logins,
            include_bots,
            permission_cache,
            org_member_fallback,
        )
        if reopened_event:
            reopened_events.append(reopened_event)

    maintainer_comments = [
        comment
        for comment in (
            normalize_comment(
                repo,
                raw_comment,
                maintainer_logins,
                include_bots,
                permission_cache,
                org_member_fallback,
            )
            for raw_comment in (issue.get("comments") or {}).get("nodes") or []
            if raw_comment and created_after(raw_comment.get("createdAt"), triaged_timestamp)
        )
        if comment
    ]

    if not label_events and not reopened_events and not maintainer_comments:
        return None, {
            **base,
            "triaged_at": triaged_at,
            "triaged_at_source": triaged_at_source,
            "reason": "no_maintainer_followup_signal",
            "skipped_signals": skipped_signals,
        }

    return (
        {
            **base,
            "triaged_at": triaged_at,
            "triaged_at_source": triaged_at_source,
            "label_events": label_events,
            "reopened_events": reopened_events,
            "maintainer_comments": maintainer_comments,
            "skipped_signals": skipped_signals,
        },
        None,
    )


def normalize_issues(
    raw_issues: list[dict[str, Any]],
    repo: str,
    maintainer_logins: set[str],
    include_bots: bool,
    org_member_fallback: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    issues = []
    skipped = []
    permission_cache: dict[str, str] = {}
    for raw_issue in raw_issues:
        normalized, skip = normalize_issue(
            raw_issue,
            repo,
            maintainer_logins,
            include_bots,
            permission_cache,
            org_member_fallback,
        )
        if normalized:
            issues.append(normalized)
        elif skip:
            skipped.append(skip)
    return issues, skipped


def build_label_change_groups(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], dict[str, Any]] = {}
    for issue in issues:
        for event in issue.get("label_events", []):
            key = (event["event_type"], event["label"])
            group = groups.setdefault(
                key,
                {
                    "event_type": event["event_type"],
                    "label": event["label"],
                    "issue_numbers": [],
                },
            )
            if issue["number"] not in group["issue_numbers"]:
                group["issue_numbers"].append(issue["number"])
    return sorted(groups.values(), key=lambda item: (item["event_type"], item["label"]))


def parse_maintainer_logins(values: list[str]) -> set[str]:
    logins: set[str] = set()
    for value in values:
        for login in value.split(","):
            stripped = login.strip()
            if stripped:
                logins.add(stripped)
    return logins


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--issue", type=int)
    parser.add_argument("--maintainer-login", action="append", default=[])
    parser.add_argument("--org-member-fallback", action="store_true")
    parser.add_argument("--include-bots", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args()

    repo = args.repo or default_repo()
    owner, name = split_repo(repo)
    raw_issues = [graphql_issue(owner, name, args.issue)] if args.issue else search_issues(repo, args.days)
    issues, skipped = normalize_issues(
        raw_issues,
        repo,
        parse_maintainer_logins(args.maintainer_login),
        args.include_bots,
        args.org_member_fallback,
    )
    payload = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "repo": repo,
        "days": args.days,
        "issue": args.issue,
        "issues": issues,
        "groups": {
            "label_changes": build_label_change_groups(issues),
        },
        "skipped": skipped,
    }

    if args.output:
        output = Path(args.output)
    else:
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        handle = tempfile.NamedTemporaryFile(
            prefix=f"update-triage-feedback-{stamp}-",
            suffix=".json",
            delete=False,
        )
        output = Path(handle.name)
        handle.close()
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
