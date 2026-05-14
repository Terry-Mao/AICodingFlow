from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests.script_imports import import_script


validate_impl = import_script(
    ".github/scripts/validate_implementation_output.py",
    "validate_implementation_output",
)


class ValidateImplementationOutputTest(unittest.TestCase):
    def write_json(self, directory: str, name: str, value: object) -> Path:
        path = Path(directory) / name
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def test_accepts_standalone_target_branch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            context = self.write_json(
                directory,
                "issue_context.json",
                {
                    "issue_number": 18,
                    "target_branch": "spec/implement-issue-18",
                    "implementation_branch_prefix": "spec/implement-issue-18",
                    "spec_context_source": "directory",
                },
            )
            metadata = self.write_json(
                directory,
                "pr-metadata.json",
                {
                    "branch_name": "spec/implement-issue-18",
                    "pr_title": "feat: add implementation workflow",
                    "pr_summary": "Closes #18\n\n## Summary\n- Done",
                },
            )

            result = validate_impl.validate_metadata(metadata, context)

        self.assertEqual(result["branch_name"], "spec/implement-issue-18")

    def test_accepts_standalone_branch_slug_extension(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            context = self.write_json(
                directory,
                "issue_context.json",
                {
                    "issue_number": 18,
                    "target_branch": "spec/implement-issue-18",
                    "implementation_branch_prefix": "spec/implement-issue-18",
                    "spec_context_source": "",
                },
            )
            metadata = self.write_json(
                directory,
                "pr-metadata.json",
                {
                    "branch_name": "spec/implement-issue-18-workflow",
                    "pr_title": "feat: add implementation workflow",
                    "pr_summary": "Closes #18\n\n## Summary\n- Done",
                },
            )

            result = validate_impl.validate_metadata(metadata, context)

        self.assertEqual(result["branch_name"], "spec/implement-issue-18-workflow")

    def test_rejects_approved_spec_pr_branch_extension(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            context = self.write_json(
                directory,
                "issue_context.json",
                {
                    "issue_number": 18,
                    "target_branch": "spec/issue-18",
                    "implementation_branch_prefix": "spec/implement-issue-18",
                    "spec_context_source": "approved-pr",
                },
            )
            metadata = self.write_json(
                directory,
                "pr-metadata.json",
                {
                    "branch_name": "spec/issue-18-workflow",
                    "pr_title": "feat: add implementation workflow",
                    "pr_summary": "Closes #18\n\n## Summary\n- Done",
                },
            )

            with self.assertRaises(SystemExit) as cm:
                validate_impl.validate_metadata(metadata, context)

        self.assertIn("must keep", str(cm.exception))

    def test_rejects_non_conventional_title(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            context = self.write_json(
                directory,
                "issue_context.json",
                {
                    "issue_number": 18,
                    "target_branch": "spec/implement-issue-18",
                    "implementation_branch_prefix": "spec/implement-issue-18",
                    "spec_context_source": "",
                },
            )
            metadata = self.write_json(
                directory,
                "pr-metadata.json",
                {
                    "branch_name": "spec/implement-issue-18",
                    "pr_title": "Add implementation workflow",
                    "pr_summary": "Closes #18\n\n## Summary\n- Done",
                },
            )

            with self.assertRaises(SystemExit) as cm:
                validate_impl.validate_metadata(metadata, context)

        self.assertIn("conventional commit", str(cm.exception))

    def test_rejects_summary_without_closing_first_line(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            context = self.write_json(
                directory,
                "issue_context.json",
                {
                    "issue_number": 18,
                    "target_branch": "spec/implement-issue-18",
                    "implementation_branch_prefix": "spec/implement-issue-18",
                    "spec_context_source": "",
                },
            )
            metadata = self.write_json(
                directory,
                "pr-metadata.json",
                {
                    "branch_name": "spec/implement-issue-18",
                    "pr_title": "feat: add implementation workflow",
                    "pr_summary": "Refs #18\n\n## Summary\n- Done",
                },
            )

            with self.assertRaises(SystemExit) as cm:
                validate_impl.validate_metadata(metadata, context)

        self.assertIn("first line", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
