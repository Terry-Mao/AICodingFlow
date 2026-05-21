from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from script_imports import import_script


selector = import_script(".github/scripts/select_review_skill.py", "select_review_skill")


class SelectReviewSkillTest(unittest.TestCase):
    def run_in_tempdir(self, callback) -> None:
        cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            try:
                callback(Path(tmpdir))
            finally:
                os.chdir(cwd)

    def test_selects_spec_review_for_spec_only_diff(self) -> None:
        def scenario(directory: Path) -> None:
            pr_diff = "\n".join(
                [
                    "# PR_DIFF_V1",
                    "FILE specs/issue-1/product.md",
                    "END_FILE",
                    "FILE specs/issue-1/tech.md",
                    "END_FILE",
                    "",
                ]
            )

            self.assertEqual(selector.select_skill(pr_diff), selector.SPEC_REVIEW_SKILL)

        self.run_in_tempdir(scenario)

    def test_selects_code_review_for_mixed_diff(self) -> None:
        def scenario(directory: Path) -> None:
            pr_diff = "\n".join(
                [
                    "# PR_DIFF_V1",
                    "FILE specs/issue-1/product.md",
                    "END_FILE",
                    "FILE .github/workflows/review-pr.yml",
                    "END_FILE",
                    "",
                ]
            )

            self.assertEqual(selector.select_skill(pr_diff), selector.CODE_REVIEW_SKILL)

        self.run_in_tempdir(scenario)

    def test_selects_code_review_when_no_files_are_present(self) -> None:
        def scenario(directory: Path) -> None:
            self.assertEqual(selector.select_skill("# PR_DIFF_V1\n"), selector.CODE_REVIEW_SKILL)

        self.run_in_tempdir(scenario)

    def test_selects_existing_companion_when_present(self) -> None:
        def scenario(directory: Path) -> None:
            companion = directory / selector.CODE_REVIEW_COMPANION_SKILL
            companion.parent.mkdir(parents=True)
            companion.write_text("---\nname: review-pr-repo\n---\n", encoding="utf-8")

            self.assertEqual(selector.select_skill("# PR_DIFF_V1\n"), selector.CODE_REVIEW_COMPANION_SKILL)

        self.run_in_tempdir(scenario)

    def test_spec_context_is_only_needed_for_code_review(self) -> None:
        self.assertFalse(selector.needs_spec_context(selector.SPEC_REVIEW_SKILL))
        self.assertTrue(selector.needs_spec_context(selector.CODE_REVIEW_SKILL))
        self.assertTrue(selector.needs_spec_context(selector.CODE_REVIEW_COMPANION_SKILL))

    def test_writes_github_output_when_configured(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "github_output.txt"
            with mock.patch.dict(os.environ, {"GITHUB_OUTPUT": str(output)}):
                selector.write_github_output("path", selector.SPEC_REVIEW_SKILL)

            self.assertEqual(output.read_text(encoding="utf-8"), f"path={selector.SPEC_REVIEW_SKILL}\n")

    def test_main_writes_skill_and_spec_context_outputs(self) -> None:
        def scenario(directory: Path) -> None:
            diff = directory / "pr_diff.txt"
            output = directory / "github_output.txt"
            diff.write_text("# PR_DIFF_V1\nFILE specs/issue-1/product.md\nEND_FILE\n", encoding="utf-8")

            with (
                mock.patch.dict(os.environ, {"GITHUB_OUTPUT": str(output)}),
                mock.patch("sys.argv", ["select_review_skill.py", "--diff", str(diff)]),
            ):
                self.assertEqual(selector.main(), 0)

            self.assertEqual(
                output.read_text(encoding="utf-8"),
                f"path={selector.SPEC_REVIEW_SKILL}\nneeds_spec_context=false\n",
            )

        self.run_in_tempdir(scenario)


if __name__ == "__main__":
    unittest.main()
