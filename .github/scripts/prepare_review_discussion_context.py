#!/usr/bin/env python3
"""Prepare prior review discussion context for AI PR reviews."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from prepare_pr_comment_context import (  # noqa: E402
    AUTHORIZED_ASSOCIATIONS,
    association,
    author_login,
    fetch_review_comments,
    fetch_review_threads,
    review_thread_state_by_comment,
)


DEFAULT_REVIEW_BOT_LOGIN = "github-actions[bot]"
DISMISSAL_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\b(no need|not needed|unnecessary|by design|won't fix|wont fix)\b",
        r"\b(keep as is|leave as is|works as intended|works as designed|intended behavior|expected behavior)\b",
        r"\b(this is intentional|this is an intentional change)\b",
        r"不需要改|不用改|无需修改|无需改|不用修改|不必修改|不是问题|按现状|保持现状|预期行为",
    )
)


def is_review_bot(comment: dict[str, Any], bot_login: str) -> bool:
    login = author_login(comment).lower()
    expected_login = (bot_login or DEFAULT_REVIEW_BOT_LOGIN).lower()
    return bool(login and login == expected_login)


def is_authorized_reply(comment: dict[str, Any]) -> bool:
    return association(comment).upper() in AUTHORIZED_ASSOCIATIONS


def is_dismissal_reply(body: str) -> bool:
    return any(pattern.search(body or "") for pattern in DISMISSAL_PATTERNS)


def discussion_item(
    comment: dict[str, Any],
    thread_state: dict[str, Any],
    *,
    reason: str,
    maintainer_reply: dict[str, Any] | None = None,
    authorized_replies: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    item = {
        "comment_id": comment.get("id"),
        "review_thread_node_id": thread_state.get("review_thread_node_id") or "",
        "path": comment.get("path") or "",
        "line": comment.get("line") or comment.get("original_line"),
        "is_resolved": thread_state.get("is_resolved"),
        "is_outdated": thread_state.get("is_outdated"),
        "reason": reason,
        "body": comment.get("body") or "",
        "diff_hunk": comment.get("diff_hunk") or "",
        "url": comment.get("html_url") or "",
    }
    if maintainer_reply is not None:
        item["maintainer_reply"] = {
            "comment_id": maintainer_reply.get("id"),
            "author": author_login(maintainer_reply),
            "body": maintainer_reply.get("body") or "",
            "url": maintainer_reply.get("html_url") or "",
        }
    if authorized_replies:
        item["authorized_replies"] = [
            {
                "comment_id": reply.get("id"),
                "author": author_login(reply),
                "body": reply.get("body") or "",
                "url": reply.get("html_url") or "",
            }
            for reply in authorized_replies
        ]
    return item


def build_review_discussion_context(
    comments: list[dict[str, Any]],
    threads: list[dict[str, Any]],
    *,
    bot_login: str = DEFAULT_REVIEW_BOT_LOGIN,
) -> dict[str, Any]:
    thread_states = review_thread_state_by_comment(threads)
    replies_by_parent: dict[int, list[dict[str, Any]]] = {}
    for comment in comments:
        parent_id = comment.get("in_reply_to_id")
        if isinstance(parent_id, int):
            replies_by_parent.setdefault(parent_id, []).append(comment)

    suppressed: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    for comment in comments:
        comment_id = comment.get("id")
        if not isinstance(comment_id, int) or comment.get("in_reply_to_id") is not None:
            continue
        if not is_review_bot(comment, bot_login):
            continue

        thread_state = thread_states.get(comment_id, {})
        authorized_replies = [reply for reply in replies_by_parent.get(comment_id, []) if is_authorized_reply(reply)]
        dismissal_reply = next(
            (
                reply
                for reply in authorized_replies
                if is_dismissal_reply(reply.get("body") or "")
            ),
            None,
        )
        if dismissal_reply is not None:
            suppressed.append(
                discussion_item(
                    comment,
                    thread_state,
                    reason="maintainer_dismissed",
                    maintainer_reply=dismissal_reply,
                    authorized_replies=authorized_replies,
                )
            )
            continue
        if thread_state.get("is_resolved") is True:
            suppressed.append(
                discussion_item(
                    comment,
                    thread_state,
                    reason="thread_resolved",
                    authorized_replies=authorized_replies,
                )
            )
            continue
        if thread_state.get("is_resolved") is False:
            unresolved.append(
                discussion_item(
                    comment,
                    thread_state,
                    reason="thread_unresolved",
                    authorized_replies=authorized_replies,
                )
            )

    return {
        "suppressed_review_comments": suppressed,
        "unresolved_review_comments": unresolved,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--pr-number", required=True, type=int)
    parser.add_argument("--output", default="review_discussion_context.json")
    parser.add_argument("--review-bot-login", default=os.environ.get("REVIEW_BOT_LOGIN") or DEFAULT_REVIEW_BOT_LOGIN)
    args = parser.parse_args()

    comments = fetch_review_comments(args.repo, args.pr_number)
    threads = fetch_review_threads(args.repo, args.pr_number)
    context = build_review_discussion_context(comments, threads, bot_login=args.review_bot_login)
    Path(args.output).write_text(json.dumps(context, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
