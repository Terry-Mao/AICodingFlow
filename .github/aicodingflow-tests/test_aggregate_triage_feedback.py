from __future__ import annotations

import unittest
from pathlib import Path

from script_imports import import_script


def script_path() -> str:
    target = Path(".github/skills/update-triage/scripts/aggregate_triage_feedback.py")
    if target.exists():
        return str(target)
    return ".codex-runtime/handoff/implementation-output/.github/skills/update-triage/scripts/aggregate_triage_feedback.py"


aggregate = import_script(script_path(), "aggregate_triage_feedback")


class AggregateTriageFeedbackTest(unittest.TestCase):
    def triaged_issue(self, number: int = 134) -> dict:
        return {
            "id": f"issue-{number}",
            "number": number,
            "title": "Needs triage correction",
            "url": f"https://github.com/o/r/issues/{number}",
            "state": "OPEN",
            "stateReason": None,
            "createdAt": "2026-06-01T00:00:00Z",
            "updatedAt": "2026-06-08T00:00:00Z",
            "closedAt": None,
            "repository": {"nameWithOwner": "o/r"},
            "author": {"__typename": "User", "login": "reporter"},
            "labels": {"nodes": [{"name": "triaged"}, {"name": "bug"}]},
            "timelineItems": {
                "nodes": [
                    {
                        "__typename": "LabeledEvent",
                        "createdAt": "2026-06-08T00:00:00Z",
                        "actor": {"__typename": "Bot", "login": "github-actions[bot]"},
                        "label": {"name": "triaged"},
                    },
                    {
                        "__typename": "LabeledEvent",
                        "createdAt": "2026-06-08T00:01:00Z",
                        "actor": {"__typename": "User", "login": "maintainer"},
                        "label": {"name": "enhancement"},
                    },
                    {
                        "__typename": "UnlabeledEvent",
                        "createdAt": "2026-06-08T00:02:00Z",
                        "actor": {"__typename": "User", "login": "maintainer"},
                        "label": {"name": "bug"},
                    },
                    {
                        "__typename": "ReopenedEvent",
                        "createdAt": "2026-06-08T00:03:00Z",
                        "actor": {"__typename": "User", "login": "maintainer"},
                    },
                ],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            },
            "comments": {
                "nodes": [
                    {
                        "author": {"__typename": "Bot", "login": "github-actions[bot]"},
                        "authorAssociation": "NONE",
                        "createdAt": "2026-06-08T00:00:30Z",
                        "url": "https://github.com/o/r/issues/134#issuecomment-0",
                        "body": "<!-- aicodingflow:triage-issue -->\n### Triage summary\n\nInitial triage.",
                    },
                    {
                        "author": {"__typename": "User", "login": "maintainer"},
                        "authorAssociation": "COLLABORATOR",
                        "createdAt": "2026-06-08T00:04:00Z",
                        "url": "https://github.com/o/r/issues/134#issuecomment-1",
                        "body": "Please include the workflow run URL.",
                    },
                    {
                        "author": {"__typename": "User", "login": "reporter"},
                        "authorAssociation": "NONE",
                        "createdAt": "2026-06-08T00:05:00Z",
                        "url": "https://github.com/o/r/issues/134#issuecomment-2",
                        "body": "Reporter-only comment.",
                    },
                ],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            },
        }

    def test_split_repo_requires_owner_and_name(self) -> None:
        self.assertEqual(aggregate.split_repo("owner/name"), ("owner", "name"))
        with self.assertRaises(SystemExit):
            aggregate.split_repo("owner-only")

    def test_search_issues_uses_updated_window_without_current_label_filter(self) -> None:
        calls = []

        def fake_run_graphql(query: str, variables: dict) -> dict:
            calls.append((query, variables))
            return {
                "data": {
                    "search": {
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                        "nodes": [],
                    }
                }
            }

        original = aggregate.run_graphql
        try:
            aggregate.run_graphql = fake_run_graphql
            issues = aggregate.search_issues("owner/repo", 7)
        finally:
            aggregate.run_graphql = original

        self.assertEqual(issues, [])
        query, variables = calls[0]
        self.assertIn("query($searchQuery: String!, $after: String)", query)
        self.assertIn("search(query: $searchQuery", query)
        self.assertNotIn("label:triaged", variables["searchQuery"])
        self.assertIn("updated:>=", variables["searchQuery"])

    def test_normalize_issue_collects_maintainer_events_and_comments(self) -> None:
        normalized, skipped = aggregate.normalize_issue(
            self.triaged_issue(),
            "o/r",
            maintainer_logins={"maintainer"},
        )

        self.assertIsNone(skipped)
        self.assertEqual(normalized["triaged_at"], "2026-06-08T00:00:30Z")
        self.assertEqual(normalized["triaged_at_source"], "bot_triage_comment")
        self.assertEqual([event["label"] for event in normalized["label_events"]], ["enhancement", "bug"])
        self.assertEqual(len(normalized["reopened_events"]), 1)
        self.assertEqual(len(normalized["maintainer_comments"]), 1)
        self.assertEqual(normalized["maintainer_comments"][0]["author_association"], "COLLABORATOR")

    def test_normalize_issue_accepts_removed_current_triaged_label_when_timestamp_exists(self) -> None:
        issue = self.triaged_issue()
        issue["labels"]["nodes"] = [{"name": "bug"}]

        normalized, skipped = aggregate.normalize_issue(
            issue,
            "o/r",
            maintainer_logins={"maintainer"},
        )

        self.assertIsNone(skipped)
        self.assertEqual(normalized["triaged_at"], "2026-06-08T00:00:30Z")
        self.assertEqual(normalized["triaged_at_source"], "bot_triage_comment")
        self.assertEqual([event["label"] for event in normalized["label_events"]], ["enhancement", "bug"])

    def test_normalize_issue_falls_back_to_bot_labeled_triaged_event(self) -> None:
        issue = self.triaged_issue()
        issue["comments"]["nodes"] = [
            comment
            for comment in issue["comments"]["nodes"]
            if aggregate.TRIAGE_COMMENT_MARKER not in comment.get("body", "")
        ]

        normalized, skipped = aggregate.normalize_issue(
            issue,
            "o/r",
            maintainer_logins={"maintainer"},
        )

        self.assertIsNone(skipped)
        self.assertEqual(normalized["triaged_at"], "2026-06-08T00:00:00Z")
        self.assertEqual(normalized["triaged_at_source"], "bot_labeled_triaged")

    def test_normalize_issue_filters_signals_before_triaged_at(self) -> None:
        issue = self.triaged_issue()
        issue["timelineItems"]["nodes"].insert(
            0,
            {
                "__typename": "LabeledEvent",
                "createdAt": "2026-06-07T23:59:00Z",
                "actor": {"__typename": "User", "login": "maintainer"},
                "label": {"name": "documentation"},
            },
        )
        issue["comments"]["nodes"].append(
            {
                "author": {"__typename": "User", "login": "maintainer"},
                "authorAssociation": "COLLABORATOR",
                "createdAt": "2026-06-07T23:58:00Z",
                "url": "https://github.com/o/r/issues/134#issuecomment-before",
                "body": "Before triage.",
            }
        )

        normalized, skipped = aggregate.normalize_issue(
            issue,
            "o/r",
            maintainer_logins={"maintainer"},
        )

        self.assertIsNone(skipped)
        self.assertEqual([event["label"] for event in normalized["label_events"]], ["enhancement", "bug"])
        self.assertEqual([comment["body"] for comment in normalized["maintainer_comments"]], ["Please include the workflow run URL."])

    def test_normalize_issue_skips_without_reliable_triage_timestamp(self) -> None:
        issue = self.triaged_issue()
        issue["timelineItems"]["nodes"] = [
            event
            for event in issue["timelineItems"]["nodes"]
            if event.get("label", {}).get("name") != "triaged"
        ]
        issue["comments"]["nodes"] = [
            comment
            for comment in issue["comments"]["nodes"]
            if aggregate.TRIAGE_COMMENT_MARKER not in comment.get("body", "")
        ]

        normalized, skipped = aggregate.normalize_issue(
            issue,
            "o/r",
            maintainer_logins={"maintainer"},
        )

        self.assertIsNone(normalized)
        self.assertEqual(skipped["reason"], "missing_reliable_triage_timestamp")

    def test_normalize_issue_skips_reporter_only_followup(self) -> None:
        issue = self.triaged_issue()
        issue["timelineItems"]["nodes"] = [
            event
            for event in issue["timelineItems"]["nodes"]
            if event.get("label", {}).get("name") == "triaged"
        ]
        issue["comments"]["nodes"][1]["authorAssociation"] = "NONE"

        normalized, skipped = aggregate.normalize_issue(issue, "o/r")

        self.assertIsNone(normalized)
        self.assertEqual(skipped["reason"], "no_maintainer_followup_signal")

    def test_normalize_issue_marks_duplicate_signals_as_skipped(self) -> None:
        issue = self.triaged_issue()
        issue["timelineItems"]["nodes"].append(
            {
                "__typename": "MarkedAsDuplicateEvent",
                "createdAt": "2026-06-08T00:06:00Z",
                "actor": {"__typename": "User", "login": "maintainer"},
            }
        )

        normalized, skipped = aggregate.normalize_issue(
            issue,
            "o/r",
            maintainer_logins={"maintainer"},
        )

        self.assertIsNone(skipped)
        self.assertEqual(
            normalized["skipped_signals"][0]["reason"],
            "marked_as_duplicate_owned_by_update_dedupe",
        )

    def test_build_label_change_groups_counts_distinct_issues(self) -> None:
        first, _ = aggregate.normalize_issue(self.triaged_issue(134), "o/r", maintainer_logins={"maintainer"})
        second, _ = aggregate.normalize_issue(self.triaged_issue(135), "o/r", maintainer_logins={"maintainer"})

        groups = aggregate.build_label_change_groups([first, second])

        enhancement = [item for item in groups if item["label"] == "enhancement"][0]
        self.assertEqual(enhancement["issue_numbers"], [134, 135])

    def test_org_member_fallback_uses_permission_cache(self) -> None:
        self.assertTrue(
            aggregate.is_maintainer_signal(
                repo="o/r",
                login="maintainer",
                permission_cache={"maintainer": "write"},
                org_member_fallback=True,
            )
        )

    def test_maintainer_login_adds_to_association_and_fallback_sources(self) -> None:
        self.assertTrue(
            aggregate.is_maintainer_signal(
                repo="o/r",
                login="other-maintainer",
                association="OWNER",
                maintainer_logins={"target-maintainer"},
            )
        )
        self.assertTrue(
            aggregate.is_maintainer_signal(
                repo="o/r",
                login="other-maintainer",
                maintainer_logins={"target-maintainer"},
                permission_cache={"other-maintainer": "write"},
                org_member_fallback=True,
            )
        )
        self.assertTrue(
            aggregate.is_maintainer_signal(
                repo="o/r",
                login="target-maintainer",
                maintainer_logins={"target-maintainer"},
            )
        )


if __name__ == "__main__":
    unittest.main()
