from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from script_imports import import_script


apply_impl = import_script(
    ".github/scripts/apply_implementation_output.py",
    "apply_implementation_output",
)


class ApplyImplementationOutputTest(unittest.TestCase):
    def write_metadata(self, root: Path, intended_files: list[str]) -> Path:
        metadata = root / "pr-metadata.json"
        metadata.write_text(
            json.dumps(
                {
                    "branch_name": "spec/issue-125",
                    "pr_title": "feat: add skill",
                    "pr_summary": "Closes #125\n\n## Summary\n- Done",
                    "intended_files": intended_files,
                }
            ),
            encoding="utf-8",
        )
        return metadata

    def test_applies_agents_output_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "implementation-output"
            source = output / ".github/skills/update-dedupe/SKILL.md"
            source.parent.mkdir(parents=True)
            source.write_text("new skill\n", encoding="utf-8")
            metadata = self.write_metadata(root, [".github/skills/update-dedupe/SKILL.md"])

            applied = apply_impl.apply_output(output, root, metadata)

            self.assertEqual(applied, [".github/skills/update-dedupe/SKILL.md"])
            self.assertEqual(
                (root / ".github/skills/update-dedupe/SKILL.md").read_text(encoding="utf-8"),
                "new skill\n",
            )

    def test_empty_output_is_noop_without_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "implementation-output"
            output.mkdir()

            applied = apply_impl.apply_output(output, root, root / "pr-metadata.json")

            self.assertEqual(applied, [])

    def test_rejects_non_agents_output_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "implementation-output"
            source = output / ".github/workflows/new.yml"
            source.parent.mkdir(parents=True)
            source.write_text("name: test\n", encoding="utf-8")
            metadata = self.write_metadata(root, [".github/workflows/new.yml"])

            with self.assertRaisesRegex(SystemExit, "only contain .agents/, .github/skills/"):
                apply_impl.apply_output(output, root, metadata)

    def test_rejects_output_not_listed_in_intended_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "implementation-output"
            source = output / ".github/skills/update-dedupe/SKILL.md"
            source.parent.mkdir(parents=True)
            source.write_text("new skill\n", encoding="utf-8")
            metadata = self.write_metadata(root, [".github/skills/other/SKILL.md"])

            with self.assertRaisesRegex(SystemExit, "not listed"):
                apply_impl.apply_output(output, root, metadata)


if __name__ == "__main__":
    unittest.main()
