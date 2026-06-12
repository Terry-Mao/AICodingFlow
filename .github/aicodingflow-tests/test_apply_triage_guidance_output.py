from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from script_imports import import_script


def script_path() -> str:
    target = Path(".github/skills/update-triage/scripts/apply_guidance_output.py")
    if target.exists():
        return str(target)
    return ".codex-runtime/handoff/implementation-output/.github/skills/update-triage/scripts/apply_guidance_output.py"


apply_guidance = import_script(script_path(), "apply_triage_guidance_output")


class ApplyTriageGuidanceOutputTest(unittest.TestCase):
    def write_status(self, output: Path, updated_files: list[str], status: str = "changed") -> None:
        (output / "status.json").write_text(
            json.dumps({"status": status, "reason": "test", "updated_files": updated_files}),
            encoding="utf-8",
        )

    def test_applies_allowed_companion_skill_and_creates_parent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "out"
            proposed = output / "triage-issue-repo"
            target = root / ".github/skills/triage-issue-repo/SKILL.md"
            proposed.mkdir(parents=True)
            (proposed / "SKILL.md").write_text("new\n", encoding="utf-8")
            self.write_status(output, [".github/skills/triage-issue-repo/SKILL.md"])

            status = apply_guidance.apply_output(output, root)

            self.assertEqual(status, "changed")
            self.assertEqual(target.read_text(encoding="utf-8"), "new\n")

    def test_applies_label_config_after_json_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "out"
            proposed = output / "issue-triage"
            target = root / ".github/issue-triage/config.json"
            proposed.mkdir(parents=True)
            (proposed / "config.json").write_text('{"labels": []}', encoding="utf-8")
            self.write_status(output, [".github/issue-triage/config.json"])

            apply_guidance.apply_output(output, root)

            self.assertEqual(json.loads(target.read_text(encoding="utf-8")), {"labels": []})
            self.assertTrue(target.read_text(encoding="utf-8").endswith("\n"))

    def test_no_change_does_not_require_proposed_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "out"
            output.mkdir()
            self.write_status(output, [], status="no_change")

            status = apply_guidance.apply_output(output, root)

            self.assertEqual(status, "no_change")

    def test_error_status_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "out"
            output.mkdir()
            self.write_status(output, [], status="error")

            with self.assertRaises(SystemExit):
                apply_guidance.apply_output(output, Path(tmp))

    def test_blocks_core_triage_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "out"
            output.mkdir()
            self.write_status(output, [".github/skills/triage-issue/SKILL.md"])

            with self.assertRaises(SystemExit):
                apply_guidance.apply_output(output, Path(tmp))

    def test_changed_status_rejects_symlink_proposed_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "out"
            proposed = output / "triage-issue-repo"
            proposed.mkdir(parents=True)
            outside = root / "outside.md"
            outside.write_text("outside\n", encoding="utf-8")
            (proposed / "SKILL.md").symlink_to(outside)
            self.write_status(output, [".github/skills/triage-issue-repo/SKILL.md"])

            with self.assertRaisesRegex(SystemExit, "refusing to apply symlink output"):
                apply_guidance.apply_output(output, root)

    def test_changed_status_rejects_symlink_parent_escape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "out"
            output.mkdir()
            outside = root / "outside"
            outside.mkdir()
            (outside / "SKILL.md").write_text("outside\n", encoding="utf-8")
            (output / "triage-issue-repo").symlink_to(outside, target_is_directory=True)
            self.write_status(output, [".github/skills/triage-issue-repo/SKILL.md"])

            with self.assertRaisesRegex(SystemExit, "outside output dir"):
                apply_guidance.apply_output(output, root)

    def test_invalid_config_json_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "out"
            proposed = output / "issue-triage"
            proposed.mkdir(parents=True)
            (proposed / "config.json").write_text("[]", encoding="utf-8")
            self.write_status(output, [".github/issue-triage/config.json"])

            with self.assertRaisesRegex(SystemExit, "must be a JSON object"):
                apply_guidance.apply_output(output, root)


if __name__ == "__main__":
    unittest.main()
