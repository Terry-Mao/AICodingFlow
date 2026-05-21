from __future__ import annotations

import unittest

from script_imports import ROOT


def compact(text: str) -> str:
    return " ".join(text.split())


class ImplementationSkillGuidanceTest(unittest.TestCase):
    def test_implement_specs_prefers_stable_workflow_context_over_fetching(self) -> None:
        text = (ROOT / ".agents/skills/implement-specs/SKILL.md").read_text(encoding="utf-8")
        compact_text = compact(text)

        self.assertIn("workflow-provided files as the authoritative GitHub context snapshot", compact_text)
        self.assertIn("do not fetch additional GitHub context unless the workflow prompt explicitly permits it", compact_text)
        self.assertIn("If authentication is unavailable or the workflow prompt says not to call GitHub APIs", compact_text)
        self.assertNotIn("Fetch any additional GitHub issue or PR content on demand", text)

    def test_implement_issue_does_not_require_fetching_in_workflows(self) -> None:
        text = (ROOT / ".agents/skills/implement-issue/SKILL.md").read_text(encoding="utf-8")
        compact_text = compact(text)

        self.assertIn("Workflow-provided files are the authoritative context snapshot", compact_text)
        self.assertIn("Fetch issue discussion only when the prompt explicitly permits it", compact_text)
        self.assertIn("If authentication is unavailable or the prompt says not to call GitHub APIs", compact_text)
        self.assertNotIn("Fetch issue discussion on demand", text)

    def test_implement_issue_documents_resolved_review_comments_contract(self) -> None:
        text = (ROOT / ".agents/skills/implement-issue/SKILL.md").read_text(encoding="utf-8")
        compact_text = compact(text)

        self.assertIn('"resolved_review_comments"', text)
        self.assertIn('"comment_id": 3274519419', text)
        self.assertIn('"summary": "One to three sentence summary."', text)
        self.assertIn("numeric inline review comment id", compact_text)
        self.assertIn("review_comment_ids.json", text)
        self.assertIn("one to three sentences", compact_text)
        self.assertIn("omit `resolved_review_comments.json`", compact_text)

    def test_local_review_skills_follow_selected_skill_output(self) -> None:
        for path in (
            ".agents/skills/review-pr-local/SKILL.md",
            ".agents/skills/review-spec-local/SKILL.md",
        ):
            text = (ROOT / path).read_text(encoding="utf-8")
            compact_text = compact(text)

            self.assertIn("skill=<path>", text)
            self.assertIn("Read the skill path printed by the command", compact_text)
            self.assertIn("Follow the selected skill exactly", compact_text)


if __name__ == "__main__":
    unittest.main()
