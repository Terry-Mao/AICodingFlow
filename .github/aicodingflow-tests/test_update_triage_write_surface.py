from __future__ import annotations

import unittest
from pathlib import Path

from script_imports import import_script


def script_path() -> str:
    target = Path(".github/skills/update-triage/scripts/validate_write_surface.py")
    if target.exists():
        return str(target)
    return ".codex-runtime/handoff/implementation-output/.github/skills/update-triage/scripts/validate_write_surface.py"


validator = import_script(script_path(), "validate_update_triage_write_surface")


class UpdateTriageWriteSurfaceTest(unittest.TestCase):
    def test_allows_triage_companion_skill(self) -> None:
        self.assertEqual(
            validator.invalid_paths([".github/skills/triage-issue-repo/SKILL.md"]),
            [],
        )

    def test_blocks_other_triage_companion_files(self) -> None:
        self.assertEqual(
            validator.invalid_paths([".github/skills/triage-issue-repo/extra.md"]),
            [".github/skills/triage-issue-repo/extra.md"],
        )

    def test_allows_exact_label_config_file(self) -> None:
        self.assertEqual(
            validator.invalid_paths([".github/issue-triage/config.json"]),
            [],
        )

    def test_blocks_other_label_config_files(self) -> None:
        self.assertEqual(
            validator.invalid_paths([".github/issue-triage/other.json"]),
            [".github/issue-triage/other.json"],
        )

    def test_blocks_core_triage_skill(self) -> None:
        self.assertEqual(
            validator.invalid_paths([".github/skills/triage-issue/SKILL.md"]),
            [".github/skills/triage-issue/SKILL.md"],
        )

    def test_blocks_dedupe_companion_skill(self) -> None:
        self.assertEqual(
            validator.invalid_paths([".github/skills/dedupe-issue-repo/SKILL.md"]),
            [".github/skills/dedupe-issue-repo/SKILL.md"],
        )

    def test_blocks_workflow_file(self) -> None:
        self.assertEqual(
            validator.invalid_paths([".github/workflows/update-triage.yml"]),
            [".github/workflows/update-triage.yml"],
        )

    def test_blocks_product_code(self) -> None:
        self.assertEqual(validator.invalid_paths(["src/app.py"]), ["src/app.py"])


if __name__ == "__main__":
    unittest.main()
