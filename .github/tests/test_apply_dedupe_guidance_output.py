from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from script_imports import import_script


def script_path() -> str:
    target = Path(".agents/skills/update-dedupe/scripts/apply_guidance_output.py")
    if target.exists():
        return str(target)
    return "implementation-output/.agents/skills/update-dedupe/scripts/apply_guidance_output.py"


apply_guidance = import_script(script_path(), "apply_dedupe_guidance_output")


class ApplyDedupeGuidanceOutputTest(unittest.TestCase):
    def test_applies_allowed_changed_file_and_creates_parent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "out"
            proposed = output / "dedupe-issue-repo"
            target = root / ".agents/skills/dedupe-issue-repo/SKILL.md"
            proposed.mkdir(parents=True)
            (proposed / "SKILL.md").write_text("new\n", encoding="utf-8")
            (output / "status.json").write_text(
                json.dumps(
                    {
                        "status": "changed",
                        "reason": "test",
                        "updated_files": [".agents/skills/dedupe-issue-repo/SKILL.md"],
                    }
                ),
                encoding="utf-8",
            )

            status = apply_guidance.apply_output(output, root)

            self.assertEqual(status, "changed")
            self.assertEqual(target.read_text(encoding="utf-8"), "new\n")

    def test_no_change_does_not_require_proposed_file(self) -> None:
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

    def test_blocks_core_dedupe_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "out"
            output.mkdir()
            (output / "status.json").write_text(
                json.dumps(
                    {
                        "status": "changed",
                        "reason": "test",
                        "updated_files": [".agents/skills/dedupe-issue/SKILL.md"],
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
                        "updated_files": [".agents/skills/dedupe-issue-repo/SKILL.md"],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaises(SystemExit):
                apply_guidance.apply_output(output, Path(tmp))

    def test_changed_status_rejects_symlink_proposed_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "out"
            proposed = output / "dedupe-issue-repo"
            proposed.mkdir(parents=True)
            outside = root / "outside.md"
            outside.write_text("outside\n", encoding="utf-8")
            (proposed / "SKILL.md").symlink_to(outside)
            (output / "status.json").write_text(
                json.dumps(
                    {
                        "status": "changed",
                        "reason": "test",
                        "updated_files": [".agents/skills/dedupe-issue-repo/SKILL.md"],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(SystemExit, "refusing to apply symlink output"):
                apply_guidance.apply_output(output, root)


if __name__ == "__main__":
    unittest.main()
