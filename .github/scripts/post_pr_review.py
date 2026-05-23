#!/usr/bin/env python3
"""Post review.json as a GitHub pull request review."""

from __future__ import annotations

import argparse
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, NamedTuple


FILE_RE = re.compile(r"^FILE\s+(.+?)\s*$")
LINE_RE = re.compile(r"^(LEFT|RIGHT|BOTH)\s+(\d+)\s+\|")
ORG_MEMBER_ASSOCIATIONS = {"COLLABORATOR", "MEMBER", "OWNER"}
NON_MEMBER_ASSOCIATIONS = {"CONTRIBUTOR", "FIRST_TIMER", "FIRST_TIME_CONTRIBUTOR", "NONE"}
DEFAULT_REVIEW_BOT_LOGIN = "github-actions[bot]"


class CodeownersRule(NamedTuple):
    pattern: str
    owners: list[str]


class GitHubResponse(NamedTuple):
    data: Any
    headers: Any


def load_event() -> dict[str, Any]:
    event_path = os.environ.get("PR_EVENT_PATH") or os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        raise SystemExit("PR_EVENT_PATH or GITHUB_EVENT_PATH is required")
    return json.loads(Path(event_path).read_text(encoding="utf-8"))


def github_api_json(
    url: str,
    token: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
) -> Any:
    return github_api_response(url, token, method=method, payload=payload).data


def github_api_response(
    url: str,
    token: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
) -> GitHubResponse:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(request) as response:
            body = response.read().decode("utf-8")
            return GitHubResponse(json.loads(body) if body else {}, response.headers)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"GitHub API request failed: {exc.code} {detail}") from exc


def request_json(url: str, token: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = github_api_json(url, token, method="POST", payload=payload)
    return response if isinstance(response, dict) else {}


def changed_files_from_diff(path: Path) -> list[str]:
    if not path.exists():
        return []
    files: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        file_match = FILE_RE.match(raw_line)
        if file_match:
            changed_path = file_match.group(1).strip()
            if changed_path:
                files.append(changed_path)
    return files


def is_spec_only(files: list[str]) -> bool:
    return bool(files) and all(path.startswith("specs/") for path in files)


def is_bot_author(pr: dict[str, Any]) -> bool:
    user = pr.get("user")
    if not isinstance(user, dict):
        return False
    user_type = user.get("type")
    login = user.get("login")
    if isinstance(user_type, str) and user_type.lower() == "bot":
        return True
    return isinstance(login, str) and login.lower().endswith("[bot]")


def is_non_member_author(pr: dict[str, Any]) -> bool:
    association = pr.get("author_association")
    if not isinstance(association, str) or not association:
        return False
    normalized = association.upper()
    if normalized in ORG_MEMBER_ASSOCIATIONS:
        return False
    if normalized not in NON_MEMBER_ASSOCIATIONS:
        return False
    return not is_bot_author(pr)


def is_non_member_code_review_subject(pr: dict[str, Any], files: list[str]) -> bool:
    return not is_spec_only(files) and is_non_member_author(pr)


def review_event_for(pr: dict[str, Any], files: list[str], verdict: str) -> str:
    if not is_non_member_code_review_subject(pr, files):
        return "COMMENT"
    if verdict == "REJECT":
        return "REQUEST_CHANGES"
    return "COMMENT"


def should_request_human_reviewer(pr: dict[str, Any], files: list[str], verdict: str) -> bool:
    return verdict == "APPROVE" and is_non_member_code_review_subject(pr, files)


def parse_diff_positions(path: Path) -> dict[tuple[str, str, int], int]:
    positions: dict[tuple[str, str, int], int] = {}
    current_file: str | None = None
    position = 0
    saw_hunk = False

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        file_match = FILE_RE.match(raw_line)
        if file_match:
            current_file = file_match.group(1).strip()
            position = 0
            saw_hunk = False
            continue

        if raw_line == "END_FILE":
            current_file = None
            saw_hunk = False
            continue

        if raw_line.startswith("HUNK "):
            if saw_hunk:
                position += 1
            saw_hunk = True
            continue

        line_match = LINE_RE.match(raw_line)
        if not line_match or current_file is None or not saw_hunk:
            continue

        position += 1
        side, number_text = line_match.groups()
        if side != "BOTH":
            positions[(current_file, side, int(number_text))] = position

    return positions


def normalize_comments(
    comments: list[dict[str, Any]],
    positions: dict[tuple[str, str, int], int],
) -> list[dict[str, Any]]:
    normalized = []
    for comment in comments:
        key = (comment["path"], comment["side"], comment["line"])
        position = positions.get(key)
        if position is None:
            raise SystemExit(f"comment target is missing from diff positions: {key[0]}/{key[1]}/{key[2]}")
        if "start_line" in comment:
            normalized_comment = {
                "path": comment["path"],
                "line": comment["line"],
                "side": comment["side"],
                "start_line": comment["start_line"],
                "start_side": comment["side"],
                "body": comment["body"],
            }
        else:
            normalized_comment = {
                "path": comment["path"],
                "position": position,
                "body": comment["body"],
            }
        normalized.append(normalized_comment)
    return normalized


def parse_codeowners(path: Path) -> list[CodeownersRule]:
    if not path.exists():
        return []

    rules: list[CodeownersRule] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        pattern = parts[0]
        owners = [owner for owner in parts[1:] if not owner.startswith("#")]
        if owners:
            rules.append(CodeownersRule(pattern=pattern, owners=owners))
    return rules


def codeowners_pattern_regex(pattern: str) -> re.Pattern[str]:
    regex = ["^"]
    index = 0
    while index < len(pattern):
        char = pattern[index]
        if char == "*":
            if index + 1 < len(pattern) and pattern[index + 1] == "*":
                regex.append(".*")
                index += 2
            else:
                regex.append("[^/]*")
                index += 1
        elif char == "?":
            regex.append("[^/]")
            index += 1
        else:
            regex.append(re.escape(char))
            index += 1
    regex.append("$")
    return re.compile("".join(regex))


def codeowners_pattern_matches(pattern: str, changed_path: str) -> bool:
    normalized_pattern = pattern.lstrip("/")
    normalized_path = changed_path.lstrip("/")

    if normalized_pattern.endswith("/"):
        return normalized_path.startswith(normalized_pattern)
    if "/" not in normalized_pattern:
        return bool(codeowners_pattern_regex(normalized_pattern).match(Path(normalized_path).name))
    return bool(codeowners_pattern_regex(normalized_pattern).match(normalized_path))


def codeowners_candidates_for_file(rules: list[CodeownersRule], changed_path: str) -> list[str]:
    candidates: list[str] = []
    for rule in rules:
        if codeowners_pattern_matches(rule.pattern, changed_path):
            candidates = rule.owners
    return candidates


def normalize_owner(owner: str) -> str:
    return owner.strip().lstrip("@")


def all_codeowners(rules: list[CodeownersRule]) -> set[str]:
    return {normalize_owner(owner).lower() for rule in rules for owner in rule.owners}


def eligible_owner(owner: str, pr_author_login: str, codeowners: set[str]) -> bool:
    normalized = normalize_owner(owner)
    if not normalized:
        return False
    if "/" in normalized:
        return False
    if pr_author_login and normalized.lower() == pr_author_login.lower():
        return False
    return normalized.lower() in codeowners


def first_eligible_owner(owners: list[str], pr_author_login: str, codeowners: set[str]) -> str | None:
    for owner in owners:
        if eligible_owner(owner, pr_author_login, codeowners):
            return normalize_owner(owner)
    return None


def select_reviewer(
    review: dict[str, Any],
    rules: list[CodeownersRule],
    changed_files: list[str],
    pr_author_login: str,
) -> str | None:
    codeowners = all_codeowners(rules)
    recommended = review.get("recommended_reviewers")
    if isinstance(recommended, list) and len(recommended) == 1 and isinstance(recommended[0], str):
        reviewer = first_eligible_owner(recommended, pr_author_login, codeowners)
        if reviewer:
            return reviewer

    for changed_path in changed_files:
        reviewer = first_eligible_owner(
            codeowners_candidates_for_file(rules, changed_path),
            pr_author_login,
            codeowners,
        )
        if reviewer:
            return reviewer

    return first_eligible_owner([owner for rule in rules for owner in rule.owners], pr_author_login, codeowners)


def request_reviewer(repo: str, token: str, pr_number: int, reviewer: str) -> None:
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/requested_reviewers"
    request_json(url, token, {"reviewers": [reviewer]})


def review_author_matches_bot(review: dict[str, Any], bot_login: str) -> bool:
    user = review.get("user")
    if not isinstance(user, dict):
        return False
    login = user.get("login")
    if not isinstance(login, str) or not login:
        return False
    return login.lower() == bot_login.lower() and is_bot_author(review)


def dismiss_review(repo: str, token: str, pr_number: int, review_id: int, message: str) -> None:
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/reviews/{review_id}/dismissals"
    github_api_json(url, token, method="PUT", payload={"message": message, "event": "DISMISS"})


def next_link(headers: Any) -> str:
    link_header = headers.get("Link", "") if hasattr(headers, "get") else ""
    for part in link_header.split(","):
        sections = [section.strip() for section in part.split(";")]
        if len(sections) < 2:
            continue
        if 'rel="next"' not in sections[1:]:
            continue
        url = sections[0]
        if url.startswith("<") and url.endswith(">"):
            return url[1:-1]
    return ""


def list_pull_request_reviews(repo: str, token: str, pr_number: int) -> list[dict[str, Any]]:
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/reviews?per_page=100"
    reviews: list[dict[str, Any]] = []
    while url:
        response = github_api_response(url, token)
        if not isinstance(response.data, list):
            raise SystemExit("GitHub reviews response was not a list")
        reviews.extend(review for review in response.data if isinstance(review, dict))
        url = next_link(response.headers)
    return reviews


def dismiss_stale_bot_request_changes(
    repo: str,
    token: str,
    pr: dict[str, Any],
    bot_login: str,
) -> None:
    pr_number = pr["number"]
    try:
        reviews = list_pull_request_reviews(repo, token, pr_number)
    except SystemExit as exc:
        print(f"Could not read PR reviews; skipping stale request-changes dismissal: {exc}")
        return

    dismissed = 0
    for review in reviews:
        if review.get("state") != "CHANGES_REQUESTED":
            continue
        review_id = review.get("id")
        if not isinstance(review_id, int):
            continue
        if not review_author_matches_bot(review, bot_login):
            continue
        try:
            dismiss_review(repo, token, pr_number, review_id, "Superseded by a later bot approval.")
        except SystemExit as exc:
            print(f"Dismiss stale request changes failed; continuing: {exc}")
            continue
        dismissed += 1

    if dismissed:
        print(f"Dismissed {dismissed} stale bot request-changes review(s)")


def request_human_reviewer_if_needed(
    repo: str,
    token: str,
    pr: dict[str, Any],
    review: dict[str, Any],
    changed_files: list[str],
    verdict: str,
) -> None:
    if not should_request_human_reviewer(pr, changed_files, verdict):
        return

    pr_author = pr.get("user", {}).get("login", "")
    rules = parse_codeowners(Path(".github/CODEOWNERS"))
    reviewer = select_reviewer(review, rules, changed_files, pr_author if isinstance(pr_author, str) else "")
    if reviewer is None:
        print("No eligible CODEOWNERS reviewer found; skipping reviewer request")
        return
    try:
        request_reviewer(repo, token, pr["number"], reviewer)
    except SystemExit as exc:
        print(f"Reviewer request failed; continuing after review publish: {exc}")
        return
    print(f"Requested reviewer {reviewer}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review", default="review.json")
    parser.add_argument("--diff", default="pr_diff.txt")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    bot_login = os.environ.get("REVIEW_BOT_LOGIN") or DEFAULT_REVIEW_BOT_LOGIN
    if not token:
        raise SystemExit("GITHUB_TOKEN is not set")
    if not repo:
        raise SystemExit("GITHUB_REPOSITORY is not set")

    event = load_event()
    pr = event["pull_request"]
    review = json.loads(Path(args.review).read_text(encoding="utf-8"))
    diff_path = Path(args.diff)
    changed_files = changed_files_from_diff(diff_path)
    verdict = review.get("verdict", "APPROVE")

    body = review.get("body") or ""
    raw_comments = review.get("comments") or []
    comments = []
    if raw_comments:
        positions = parse_diff_positions(diff_path)
        comments = normalize_comments(raw_comments, positions)
    if not body and not comments:
        print("review.json has no body or comments; skipping PR review")
        if verdict == "APPROVE" and is_non_member_code_review_subject(pr, changed_files):
            dismiss_stale_bot_request_changes(repo, token, pr, bot_login)
        request_human_reviewer_if_needed(repo, token, pr, review, changed_files, verdict)
        return

    payload = {
        "event": review_event_for(pr, changed_files, verdict),
        "commit_id": pr["head"]["sha"],
        "body": body,
        "comments": comments,
    }
    url = f"https://api.github.com/repos/{repo}/pulls/{pr['number']}/reviews"
    response = request_json(url, token, payload)
    print(f"Posted PR review {response.get('id')}")

    if verdict == "APPROVE" and is_non_member_code_review_subject(pr, changed_files):
        dismiss_stale_bot_request_changes(repo, token, pr, bot_login)

    request_human_reviewer_if_needed(repo, token, pr, review, changed_files, verdict)


if __name__ == "__main__":
    main()
