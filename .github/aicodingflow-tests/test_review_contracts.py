from __future__ import annotations

import json
import unittest

from script_imports import ROOT


class ReviewContractsTest(unittest.TestCase):
    def test_review_contract_documents_validator_and_schema(self) -> None:
        contract = (ROOT / ".agents/contracts/review.md").read_text(encoding="utf-8")
        schema = json.loads((ROOT / ".agents/contracts/review.schema.json").read_text(encoding="utf-8"))

        self.assertIn("PR_DIFF_V1", contract)
        self.assertIn("python3 .github/scripts/validate_review_json.py", contract)
        self.assertEqual(schema["required"], ["verdict", "body", "comments"])
        self.assertFalse(schema["additionalProperties"])

    def test_core_and_security_review_skills_reference_shared_contract(self) -> None:
        skill_paths = [
            ".github/skills/review-pr/SKILL.md",
            ".github/skills/review-spec/SKILL.md",
            ".github/skills/security-review-pr/SKILL.md",
            ".github/skills/security-review-spec/SKILL.md",
        ]

        for path in skill_paths:
            with self.subTest(path=path):
                text = (ROOT / path).read_text(encoding="utf-8")
                self.assertIn(".agents/contracts/review.md", text)

    def test_repo_review_companions_are_not_primary_entrypoints(self) -> None:
        companion_paths = [
            ".github/skills/review-pr-repo/SKILL.md",
            ".github/skills/review-spec-repo/SKILL.md",
        ]

        for path in companion_paths:
            with self.subTest(path=path):
                text = (ROOT / path).read_text(encoding="utf-8")
                self.assertIn("companion to the core", text)
                self.assertIn("Do not invoke this file as the primary", text)


if __name__ == "__main__":
    unittest.main()
