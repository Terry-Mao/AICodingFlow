from __future__ import annotations

import unittest
from pathlib import Path

from tests.script_imports import import_script


def script_path() -> str:
    target = Path(".agents/skills/update-dedupe/scripts/aggregate_dedupe_feedback.py")
    if target.exists():
        return str(target)
    return "implementation-output/.agents/skills/update-dedupe/scripts/aggregate_dedupe_feedback.py"


aggregate = import_script(script_path(), "aggregate_dedupe_feedback")


class AggregateDedupeFeedbackTest(unittest.TestCase):
    def duplicate_issue(self, number: int, canonical_number: int = 10) -> dict:
        return {
            "id": f"issue-{number}",
            "number": number,
            "title": f"Duplicate {number}",
            "url": f"https://github.com/o/r/issues/{number}",
            "state": "CLOSED",
            "stateReason": "DUPLICATE",
            "closedAt": "2026-05-19T00:00:00Z",
            "repository": {"nameWithOwner": "o/r"},
            "author": {"__typename": "User", "login": "reporter"},
            "timelineItems": {
                "nodes": [
                    {
                        "__typename": "MarkedAsDuplicateEvent",
                        "createdAt": "2026-05-19T00:01:00Z",
                        "actor": {"__typename": "User", "login": "maintainer"},
                        "canonical": {
                            "__typename": "Issue",
                            "number": canonical_number,
                            "title": "Canonical issue",
                            "url": f"https://github.com/o/r/issues/{canonical_number}",
                            "repository": {"nameWithOwner": "o/r"},
                        },
                        "duplicate": {
                            "__typename": "Issue",
                            "number": number,
                            "title": f"Duplicate {number}",
                            "url": f"https://github.com/o/r/issues/{number}",
                            "repository": {"nameWithOwner": "o/r"},
                        },
                    }
                ],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            },
        }

    def test_split_repo_requires_owner_and_name(self) -> None:
        self.assertEqual(aggregate.split_repo("owner/name"), ("owner", "name"))
        with self.assertRaises(SystemExit):
            aggregate.split_repo("owner-only")

    def test_normalize_issue_accepts_duplicate_with_canonical_event(self) -> None:
        normalized, skipped = aggregate.normalize_issue(self.duplicate_issue(11))

        self.assertIsNone(skipped)
        self.assertEqual(normalized["state_reason"], "duplicate")
        self.assertEqual(normalized["canonical"]["number"], 10)
        self.assertEqual(normalized["evidence"]["event_type"], "marked_as_duplicate")

    def test_normalize_issue_skips_non_duplicate_state_reason(self) -> None:
        issue = self.duplicate_issue(11)
        issue["stateReason"] = "COMPLETED"

        normalized, skipped = aggregate.normalize_issue(issue)

        self.assertIsNone(normalized)
        self.assertEqual(skipped["reason"], "state_reason_not_duplicate")

    def test_normalize_issue_skips_missing_canonical_event(self) -> None:
        issue = self.duplicate_issue(11)
        issue["timelineItems"]["nodes"] = []

        normalized, skipped = aggregate.normalize_issue(issue)

        self.assertIsNone(normalized)
        self.assertEqual(skipped["reason"], "missing_marked_as_duplicate_event")

    def test_normalize_issue_skips_event_for_different_duplicate_issue(self) -> None:
        issue = self.duplicate_issue(11)
        issue["timelineItems"]["nodes"][0]["duplicate"]["number"] = 99

        normalized, skipped = aggregate.normalize_issue(issue)

        self.assertIsNone(normalized)
        self.assertEqual(skipped["reason"], "duplicate_event_does_not_match_issue")

    def test_build_clusters_groups_by_canonical_issue(self) -> None:
        issues, skipped = aggregate.normalize_issues(
            [self.duplicate_issue(11), self.duplicate_issue(12), self.duplicate_issue(13, 20)]
        )

        clusters = aggregate.build_clusters(issues)

        self.assertEqual(skipped, [])
        self.assertEqual([cluster["canonical"]["number"] for cluster in clusters], [10, 20])
        self.assertEqual([item["number"] for item in clusters[0]["duplicates"]], [11, 12])

    def test_build_clusters_deduplicates_duplicate_issue_numbers(self) -> None:
        issue, _ = aggregate.normalize_issue(self.duplicate_issue(11))

        clusters = aggregate.build_clusters([issue, issue])

        self.assertEqual(len(clusters[0]["duplicates"]), 1)


if __name__ == "__main__":
    unittest.main()
