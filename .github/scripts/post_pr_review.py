#!/usr/bin/env python3
"""Post review.json as a GitHub pull request review."""

from __future__ import annotations

import argparse
import fnmatch
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


class CodeownersRule(NamedTuple):
    pattern: str
    owners: tuple[str, ...]


def load_event() -> dict[str, Any]:
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        raise SystemExit("GITHUB_EVENT_PATH is not set")
    return json.loads(Path(event_path).read_text(encoding="utf-8"))


def request_json(url: str, token: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"GitHub API request failed: {exc.code} {detail}") from exc


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


def changed_files_from_diff(path: Path) -> list[str]:
    if not path.exists():
        return []
    files: list[str] = []
    seen: set[str] = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        file_match = FILE_RE.match(raw_line)
        if not file_match:
            continue
        changed_file = file_match.group(1).strip()
        if changed_file and changed_file not in seen:
            files.append(changed_file)
            seen.add(changed_file)
    return files


def is_spec_only(files: list[str]) -> bool:
    return bool(files) and all(path.startswith("specs/") for path in files)


def is_bot_author(pr: dict[str, Any]) -> bool:
    user = pr.get("user")
    if not isinstance(user, dict):
        return False
    if user.get("type") == "Bot":
        return True
    login = user.get("login")
    return isinstance(login, str) and login.endswith("[bot]")


def is_non_member_author(pr: dict[str, Any]) -> bool:
    association = pr.get("author_association")
    if not isinstance(association, str) or not association:
        return False
    if association in ORG_MEMBER_ASSOCIATIONS:
        return False
    return not is_bot_author(pr)


def review_event_for(pr: dict[str, Any], files: list[str], verdict: str) -> str:
    if is_spec_only(files):
        return "COMMENT"
    if not is_non_member_author(pr):
        return "COMMENT"
    if verdict == "REJECT":
        return "REQUEST_CHANGES"
    return "COMMENT"


def should_request_human_reviewer(pr: dict[str, Any], files: list[str], verdict: str) -> bool:
    return verdict == "APPROVE" and is_non_member_author(pr) and not is_spec_only(files)


def normalize_owner(owner: str) -> str:
    return owner[1:] if owner.startswith("@") else owner


def parse_codeowners(path: Path) -> list[CodeownersRule]:
    if not path.exists():
        return []
    rules: list[CodeownersRule] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        line = line.split(" #", 1)[0].strip()
        parts = line.split()
        if len(parts) < 2:
            continue
        pattern, owners = parts[0], tuple(parts[1:])
        rules.append(CodeownersRule(pattern=pattern, owners=owners))
    return rules


def codeowners_rule_matches(pattern: str, changed_path: str) -> bool:
    pattern = pattern.lstrip("/")
    if not pattern:
        return False
    if pattern.endswith("/"):
        return changed_path.startswith(pattern)
    if "/" not in pattern:
        return fnmatch.fnmatch(Path(changed_path).name, pattern) or fnmatch.fnmatch(changed_path, pattern)
    return fnmatch.fnmatch(changed_path, pattern)


def codeowners_candidates_for_file(rules: list[CodeownersRule], changed_path: str) -> list[str]:
    matched: CodeownersRule | None = None
    for rule in rules:
        if codeowners_rule_matches(rule.pattern, changed_path):
            matched = rule
    return list(matched.owners) if matched else []


def codeowners_owner_set(rules: list[CodeownersRule]) -> set[str]:
    return {normalize_owner(owner) for rule in rules for owner in rule.owners}


def eligible_owner(owner: str, pr_author_login: str, all_codeowners: set[str]) -> bool:
    normalized = normalize_owner(owner)
    if not normalized or normalized == pr_author_login:
        return False
    if "/" in normalized:
        return False
    return normalized in all_codeowners


def select_reviewer(
    review: dict[str, Any],
    rules: list[CodeownersRule],
    changed_files: list[str],
    pr_author_login: str,
) -> str | None:
    all_codeowners = codeowners_owner_set(rules)
    recommended = review.get("recommended_reviewers")
    if isinstance(recommended, list) and len(recommended) == 1 and isinstance(recommended[0], str):
        reviewer = recommended[0]
        if eligible_owner(reviewer, pr_author_login, all_codeowners):
            return normalize_owner(reviewer)

    for changed_file in changed_files:
        for owner in codeowners_candidates_for_file(rules, changed_file):
            if eligible_owner(owner, pr_author_login, all_codeowners):
                return normalize_owner(owner)

    for rule in rules:
        for owner in rule.owners:
            if eligible_owner(owner, pr_author_login, all_codeowners):
                return normalize_owner(owner)
    return None


def request_reviewer(repo: str, token: str, pr_number: int, reviewer: str) -> None:
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/requested_reviewers"
    request_json(url, token, {"reviewers": [reviewer]})


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review", default="review.json")
    parser.add_argument("--diff", default="pr_diff.txt")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not token:
        raise SystemExit("GITHUB_TOKEN is not set")
    if not repo:
        raise SystemExit("GITHUB_REPOSITORY is not set")

    event = load_event()
    pr = event["pull_request"]
    review = json.loads(Path(args.review).read_text(encoding="utf-8"))
    diff_path = Path(args.diff)
    changed_files = changed_files_from_diff(diff_path)
    verdict = review["verdict"]

    body = review.get("body") or ""
    raw_comments = review.get("comments") or []
    comments = []
    if raw_comments:
        positions = parse_diff_positions(diff_path)
        comments = normalize_comments(raw_comments, positions)
    if not body and not comments:
        print("review.json has no body or comments; skipping PR review")
        return

    review_event = review_event_for(pr, changed_files, verdict)
    payload = {
        "event": review_event,
        "commit_id": pr["head"]["sha"],
        "body": body,
        "comments": comments,
    }
    url = f"https://api.github.com/repos/{repo}/pulls/{pr['number']}/reviews"
    response = request_json(url, token, payload)
    print(f"Posted PR review {response.get('id')} with event {review_event}")

    if should_request_human_reviewer(pr, changed_files, verdict):
        user = pr.get("user") if isinstance(pr.get("user"), dict) else {}
        pr_author_login = user.get("login") if isinstance(user.get("login"), str) else ""
        rules = parse_codeowners(Path(".github/CODEOWNERS"))
        reviewer = select_reviewer(review, rules, changed_files, pr_author_login)
        if not reviewer:
            print("No eligible CODEOWNERS reviewer found; skipping reviewer request")
            return
        try:
            request_reviewer(repo, token, pr["number"], reviewer)
        except SystemExit as exc:
            print(f"Reviewer request failed; continuing after review post: {exc}")
        else:
            print(f"Requested reviewer {reviewer}")


if __name__ == "__main__":
    main()
