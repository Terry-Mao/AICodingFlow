from __future__ import annotations

import unittest
from pathlib import Path

from script_imports import import_script


def script_path() -> str:
    target = Path(".github/skills/update-dedupe/scripts/validate_write_surface.py")
    if target.exists():
        return str(target)
    return "implementation-output/.github/skills/update-dedupe/scripts/validate_write_surface.py"


validator = import_script(script_path(), "validate_update_dedupe_write_surface")


class UpdateDedupeWriteSurfaceTest(unittest.TestCase):
    def test_allows_dedupe_companion_skill(self) -> None:
        self.assertEqual(
            validator.invalid_paths([".github/skills/dedupe-issue-repo/SKILL.md"]),
            [],
        )

    def test_blocks_core_dedupe_skill(self) -> None:
        self.assertEqual(
            validator.invalid_paths([".github/skills/dedupe-issue/SKILL.md"]),
            [".github/skills/dedupe-issue/SKILL.md"],
        )

    def test_blocks_workflow_file(self) -> None:
        self.assertEqual(
            validator.invalid_paths([".github/workflows/update-dedupe.yml"]),
            [".github/workflows/update-dedupe.yml"],
        )

    def test_blocks_product_code(self) -> None:
        self.assertEqual(validator.invalid_paths(["src/app.py"]), ["src/app.py"])


if __name__ == "__main__":
    unittest.main()
