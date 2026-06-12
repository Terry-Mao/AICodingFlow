from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from script_imports import import_script


apply_guidance = import_script(
    ".github/skills/update-pr-review/scripts/apply_guidance_output.py",
    "apply_guidance_output",
)


class ApplyGuidanceOutputTest(unittest.TestCase):
    def test_applies_allowed_changed_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "out"
            proposed = output / "review-pr-repo"
            target = root / ".github/skills/review-pr-repo/SKILL.md"
            proposed.mkdir(parents=True)
            target.parent.mkdir(parents=True)
            target.write_text("old\n", encoding="utf-8")
            (proposed / "SKILL.md").write_text("new\n", encoding="utf-8")
            (output / "status.json").write_text(
                json.dumps(
                    {
                        "status": "changed",
                        "reason": "test",
                        "updated_files": [".github/skills/review-pr-repo/SKILL.md"],
                    }
                ),
                encoding="utf-8",
            )

            status = apply_guidance.apply_output(output, root)

            self.assertEqual(status, "changed")
            self.assertEqual(target.read_text(encoding="utf-8"), "new\n")

    def test_no_change_does_not_modify_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "out"
            output.mkdir()
            (output / "status.json").write_text(
                json.dumps({"status": "no_change", "reason": "insufficient evidence", "updated_files": []}),
                encoding="utf-8",
            )

            status = apply_guidance.apply_output(output, root)

            self.assertEqual(status, "no_change")

    def test_error_status_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "out"
            output.mkdir()
            (output / "status.json").write_text(
                json.dumps({"status": "error", "reason": "could not parse feedback", "updated_files": []}),
                encoding="utf-8",
            )

            with self.assertRaises(SystemExit):
                apply_guidance.apply_output(output, Path(tmp))

    def test_blocks_disallowed_output_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "out"
            output.mkdir()
            (output / "status.json").write_text(
                json.dumps(
                    {
                        "status": "changed",
                        "reason": "test",
                        "updated_files": [".github/skills/review-pr/SKILL.md"],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaises(SystemExit):
                apply_guidance.apply_output(output, Path(tmp))

    def test_changed_status_requires_proposed_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "out"
            output.mkdir()
            (output / "status.json").write_text(
                json.dumps(
                    {
                        "status": "changed",
                        "reason": "test",
                        "updated_files": [".github/skills/review-spec-repo/SKILL.md"],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaises(SystemExit):
                apply_guidance.apply_output(output, Path(tmp))


if __name__ == "__main__":
    unittest.main()
