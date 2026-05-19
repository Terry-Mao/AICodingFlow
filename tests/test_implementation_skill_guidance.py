from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


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


if __name__ == "__main__":
    unittest.main()
