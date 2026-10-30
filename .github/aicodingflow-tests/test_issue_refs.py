from __future__ import annotations

import unittest

from script_imports import import_script


issue_refs = import_script(".github/scripts/issue_refs.py", "issue_refs")


class IssueRefsTest(unittest.TestCase):
    def test_issue_number_from_text_uses_explicit_tokens_and_branch_suffix(self) -> None:
        self.assertEqual(issue_refs.issue_number_from_text("Refs #42"), 42)
        self.assertEqual(issue_refs.issue_number_from_text("GH-42"), 42)
        self.assertEqual(issue_refs.issue_number_from_text("issue 42"), 42)
        self.assertEqual(issue_refs.issue_number_from_text("feat/thing-42"), 42)
        self.assertIsNone(issue_refs.issue_number_from_text("walk through 42 cases"))
        self.assertIsNone(issue_refs.issue_number_from_text("highlight gh42 as text"))

    def test_issue_number_from_branch_accepts_spec_branch_prefix(self) -> None:
        self.assertEqual(issue_refs.issue_number_from_branch("spec/issue-57", prefix="spec/issue-"), 57)
        self.assertIsNone(issue_refs.issue_number_from_branch("spec/issue-not-a-number", prefix="spec/issue-"))

    def test_issue_number_from_strict_text_ignores_bare_hash_and_gh_refs(self) -> None:
        self.assertEqual(issue_refs.issue_number_from_strict_text("Refs #42"), 42)
        self.assertEqual(issue_refs.issue_number_from_strict_text("issue 42"), 42)
        self.assertEqual(issue_refs.issue_number_from_strict_text("issue #42"), 42)
        self.assertIsNone(issue_refs.issue_number_from_strict_text("See #99 for context"))
        self.assertIsNone(issue_refs.issue_number_from_strict_text("GH-99"))

    def test_resolve_issue_number_from_pr_ignores_pr_references(self) -> None:
        self.assertIsNone(
            issue_refs.resolve_issue_number_from_pr(
                {"body": "Follow-up to #123", "title": "Review changes", "head": {"ref": "spec/respond-pr-42"}}
            )
        )
        self.assertEqual(
            issue_refs.resolve_issue_number_from_pr(
                {"body": "Follow-up to #123", "title": "Refs #302", "head": {"ref": "spec/respond-pr-42"}}
            ),
            302,
        )

    def test_resolve_issue_number_from_pr_accepts_explicit_branch(self) -> None:
        self.assertEqual(issue_refs.resolve_issue_number_from_pr({"headRefName": "spec/issue-42"}), 42)
        self.assertIsNone(issue_refs.resolve_issue_number_from_pr({"headRefName": "feat/thing-42"}))

    def test_resolve_issue_number_from_local_issue_branches(self) -> None:
        for branch in ("feat/thing-42", "fix/local-review-issue-refs-42", "spec/implement-issue-42",
                       "spec/implement-issue-42-add-retry-logic"):
            with self.subTest(branch=branch):
                self.assertEqual(
                    issue_refs.resolve_issue_number_from_pr({"number": "", "head": {"ref": branch}}),
                    42,
                )

        for branch in ("spec/respond-pr-42", "feat/thing-42-extra", "other/thing-42"):
            with self.subTest(branch=branch):
                self.assertIsNone(issue_refs.resolve_issue_number_from_pr({"number": "", "head": {"ref": branch}}))

        self.assertIsNone(issue_refs.resolve_issue_number_from_pr({"number": 7, "headRefName": "feat/thing-42"}))
        self.assertEqual(
            issue_refs.resolve_issue_number_from_pr({"number": "", "body": "Refs #99", "headRefName": "feat/thing-42"}),
            99,
        )

    def test_issue_numbers_from_closing_refs_ignores_pr_references(self) -> None:
        pr = {
            "title": "Implement flow refs #90",
            "body": "Refs #88, #89 and PR #123\n\nReferenced pull request #124 should not count.\nFixes #91",
            "closingIssuesReferences": [{"number": 87}, {"number": "87"}, {"number": 88}],
        }

        self.assertEqual(issue_refs.issue_numbers_from_closing_refs(pr), [87, 88, 90, 89, 91])


if __name__ == "__main__":
    unittest.main()
