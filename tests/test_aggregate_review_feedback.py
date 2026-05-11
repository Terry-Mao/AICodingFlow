from __future__ import annotations

import unittest

from tests.script_imports import import_script


aggregate = import_script(
    ".agents/skills/update-pr-review/scripts/aggregate_review_feedback.py",
    "aggregate_review_feedback",
)


class AggregateReviewFeedbackTest(unittest.TestCase):
    def test_classify_spec_only_files(self) -> None:
        self.assertEqual(aggregate.classify_review_type(["specs/a.md", "specs/nested/b.md"]), "spec")

    def test_classify_mixed_files_as_code(self) -> None:
        self.assertEqual(aggregate.classify_review_type(["specs/a.md", "src/app.py"]), "code")

    def test_detects_severity_and_suggestion_blocks(self) -> None:
        body = "⚠️ [IMPORTANT] tighten this\n```suggestion\nx\n```"
        self.assertEqual(aggregate.severity(body), "IMPORTANT")
        self.assertTrue(aggregate.has_suggestion(body))

    def test_human_comment_excludes_missing_login(self) -> None:
        self.assertFalse(aggregate.is_human_comment({"author": None}, {"github-actions[bot]"}, False))

    def test_human_comment_excludes_agent_login(self) -> None:
        comment = {"author": {"__typename": "User", "login": "github-actions[bot]"}}
        self.assertFalse(aggregate.is_human_comment(comment, {"github-actions[bot]"}, False))

    def test_human_comment_excludes_other_bots_by_default(self) -> None:
        comment = {"author": {"__typename": "Bot", "login": "copilot-pull-request-reviewer[bot]"}}
        self.assertFalse(aggregate.is_human_comment(comment, {"github-actions[bot]"}, False))

    def test_human_comment_can_include_other_bots(self) -> None:
        comment = {"author": {"__typename": "Bot", "login": "copilot-pull-request-reviewer[bot]"}}
        self.assertTrue(aggregate.is_human_comment(comment, {"github-actions[bot]"}, True))

    def test_human_comment_includes_non_agent_user(self) -> None:
        comment = {"author": {"__typename": "User", "login": "maintainer"}}
        self.assertTrue(aggregate.is_human_comment(comment, {"github-actions[bot]"}, False))


if __name__ == "__main__":
    unittest.main()
