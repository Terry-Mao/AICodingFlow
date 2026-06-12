from __future__ import annotations

import unittest

from script_imports import import_script


writer = import_script(".github/scripts/write_update_triage_pr_body.py", "write_update_triage_pr_body")


class WriteUpdateTriagePrBodyTest(unittest.TestCase):
    def test_build_body_includes_evidence_source_and_changed_files(self) -> None:
        body = writer.build_body(
            reason="Two issues moved from bug to enhancement.",
            days="7",
            issue="all recent triaged issues",
            repo="owner/repo",
            changed_files=".github/skills/triage-issue-repo/SKILL.md\n.github/issue-triage/config.json\n",
        )

        self.assertIn("Evidence summary:\nTwo issues moved from bug to enhancement.", body)
        self.assertIn("- days: 7", body)
        self.assertIn("- issue: all recent triaged issues", body)
        self.assertIn("- repo: owner/repo", body)
        self.assertIn("- .github/skills/triage-issue-repo/SKILL.md", body)
        self.assertNotIn("Closes #", body)

    def test_build_body_neutralizes_closing_keywords_in_reason(self) -> None:
        body = writer.build_body(
            reason="Closes #123, fixes #124, and RESOLVED #125.",
            days="7",
            issue="all recent triaged issues",
            repo="owner/repo",
            changed_files="",
        )

        self.assertIn("Closes issue #123", body)
        self.assertIn("fixes issue #124", body)
        self.assertIn("RESOLVED issue #125", body)
        self.assertNotIn("Closes #123", body)
        self.assertNotIn("fixes #124", body)
        self.assertNotIn("RESOLVED #125", body)

    def test_build_body_neutralizes_cross_repo_and_url_closing_refs(self) -> None:
        body = writer.build_body(
            reason=(
                "fixes owner/repo#123 and resolves "
                "https://github.com/owner/repo/issues/124."
            ),
            days="7",
            issue="all recent triaged issues",
            repo="owner/repo",
            changed_files="",
        )

        self.assertIn("fixes issue owner/repo#123", body)
        self.assertIn("resolves issue https://github.com/owner/repo/issues/124", body)
        self.assertNotIn("fixes owner/repo#123", body)
        self.assertNotIn("resolves https://github.com/owner/repo/issues/124", body)


if __name__ == "__main__":
    unittest.main()
