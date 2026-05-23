#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from script_imports import import_script


validate_spec_output = import_script(".github/scripts/validate_spec_output.py", "validate_spec_output")


class ValidateSpecOutputTest(unittest.TestCase):
    def test_validate_metadata_accepts_required_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            metadata_path = Path(directory) / "pr-metadata.json"
            metadata_path.write_text(
                json.dumps(
                    {
                        "branch_name": "spec/issue-32",
                        "pr_title": "docs(spec): create issue 32 specs",
                        "pr_summary": "## Summary\n\nCreate specs.\n\nRefs #32\n",
                    }
                ),
                encoding="utf-8",
            )

            self.assertEqual(
                validate_spec_output.validate_metadata(metadata_path, "spec/issue-32", 32)["pr_title"],
                "docs(spec): create issue 32 specs",
            )

    def test_main_uses_context_target_branch_for_metadata_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            product = root / "specs/example-32/product.md"
            tech = root / "specs/example-32/tech.md"
            product.parent.mkdir(parents=True)
            product.write_text("# Product\n\n" + "a" * 220, encoding="utf-8")
            tech.write_text("# Tech\n\n" + "b" * 220, encoding="utf-8")
            context = root / "issue_context.json"
            context.write_text(
                json.dumps(
                    {
                        "issue": {"number": 32},
                        "product_spec": str(product),
                        "tech_spec": str(tech),
                        "branch_name": "legacy",
                        "target_branch": "spec/issue-32",
                    }
                ),
                encoding="utf-8",
            )
            metadata = root / "pr-metadata.json"
            metadata.write_text(
                json.dumps(
                    {
                        "branch_name": "spec/issue-32",
                        "pr_title": "docs(spec): create issue 32 specs",
                        "pr_summary": "## Summary\n\nCreate specs.\n\nRefs #32\n",
                    }
                ),
                encoding="utf-8",
            )

            with (
                mock.patch("sys.argv", ["validate_spec_output.py", "--context", str(context), "--metadata", str(metadata)]),
                mock.patch.object(validate_spec_output, "validate_write_surface"),
            ):
                validate_spec_output.main()

    def test_validate_metadata_rejects_wrong_branch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            metadata_path = Path(directory) / "pr-metadata.json"
            metadata_path.write_text(
                json.dumps(
                    {
                        "branch_name": "wrong",
                        "pr_title": "docs(spec): create issue 32 specs",
                        "pr_summary": "## Summary\n\nCreate specs.\n\nRefs #32\n",
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(SystemExit, "branch_name must be 'spec/issue-32'"):
                validate_spec_output.validate_metadata(metadata_path, "spec/issue-32")

    def test_validate_metadata_rejects_non_conventional_title(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            metadata_path = Path(directory) / "pr-metadata.json"
            metadata_path.write_text(
                json.dumps(
                    {
                        "branch_name": "spec/issue-32",
                        "pr_title": "Spec: example",
                        "pr_summary": "## Summary\n\nCreate specs.\n\nRefs #32\n",
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(SystemExit, "conventional commit style"):
                validate_spec_output.validate_metadata(metadata_path, "spec/issue-32", 32)

    def test_validate_metadata_requires_refs_footer(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            metadata_path = Path(directory) / "pr-metadata.json"
            metadata_path.write_text(
                json.dumps(
                    {
                        "branch_name": "spec/issue-32",
                        "pr_title": "docs(spec): create issue 32 specs",
                        "pr_summary": "## Summary\n\nCreate specs.\n",
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(SystemExit, "must include Refs #32"):
                validate_spec_output.validate_metadata(metadata_path, "spec/issue-32", 32)

    def test_validate_metadata_requires_markdown_body(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            metadata_path = Path(directory) / "pr-metadata.json"
            metadata_path.write_text(
                json.dumps(
                    {
                        "branch_name": "spec/issue-32",
                        "pr_title": "docs(spec): create issue 32 specs",
                        "pr_summary": "Refs #32",
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(SystemExit, "complete markdown body"):
                validate_spec_output.validate_metadata(metadata_path, "spec/issue-32", 32)

    def test_validate_spec_file_rejects_tiny_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            spec_path = Path(directory) / "product.md"
            spec_path.write_text("too short", encoding="utf-8")

            with self.assertRaisesRegex(SystemExit, "too short"):
                validate_spec_output.validate_spec_file(spec_path)

    def test_validate_write_surface_allows_only_expected_files(self) -> None:
        result = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=" M specs/example/product.md\n?? pr-metadata.json\n M issue_context.json\n M src/app.py\n",
        )

        with mock.patch.object(validate_spec_output.subprocess, "run", return_value=result):
            with self.assertRaisesRegex(SystemExit, "unexpected files changed: src/app.py"):
                validate_spec_output.validate_write_surface(
                    {
                        "specs/example/product.md",
                        "specs/example/tech.md",
                        "pr-metadata.json",
                        "issue_context.json",
                    }
                )

    def test_validate_write_surface_ignores_python_cache_files(self) -> None:
        result = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=(
                " M specs/example/product.md\n"
                "?? .github/scripts/__pycache__/validate_spec_output.cpython-312.pyc\n"
                "?? tests/__pycache__/script_imports.cpython-312.pyc\n"
            ),
        )

        with mock.patch.object(validate_spec_output.subprocess, "run", return_value=result):
            validate_spec_output.validate_write_surface(
                {
                    "specs/example/product.md",
                    "specs/example/tech.md",
                    "pr-metadata.json",
                    "issue_context.json",
                }
            )


if __name__ == "__main__":
    unittest.main()
