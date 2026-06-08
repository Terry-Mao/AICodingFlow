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
            changed_files=".agents/skills/triage-issue-repo/SKILL.md\n.github/issue-triage/config.json\n",
        )

        self.assertIn("Evidence summary:\nTwo issues moved from bug to enhancement.", body)
        self.assertIn("- days: 7", body)
        self.assertIn("- issue: all recent triaged issues", body)
        self.assertIn("- repo: owner/repo", body)
        self.assertIn("- .agents/skills/triage-issue-repo/SKILL.md", body)
        self.assertNotIn("Closes #", body)


if __name__ == "__main__":
    unittest.main()
