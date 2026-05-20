from __future__ import annotations

import base64
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from script_imports import import_script


write_spec_context = import_script(".github/scripts/write_spec_context.py", "write_spec_context")


def pr_event(body: str = "Refs #42", head_ref: str = "feat/thing-42") -> dict:
    return {
        "pull_request": {
            "number": 7,
            "title": "feat: implement thing",
            "body": body,
            "head": {"ref": head_ref},
            "base": {"ref": "main", "sha": "base-sha", "repo": {"default_branch": "main"}},
        }
    }


class WriteSpecContextTest(unittest.TestCase):
    def test_resolves_approved_spec_pr_before_directory(self) -> None:
        spec_pr = {
            "number": 123,
            "html_url": "https://github.test/owner/repo/pull/123",
            "updated_at": "2026-05-13T10:20:30Z",
            "labels": [{"name": "plan-approved"}],
            "head": {"ref": "spec/issue-42", "repo": {"full_name": "owner/repo"}},
        }

        with (
            mock.patch.object(
                write_spec_context,
                "fetch_pr_files",
                return_value=[{"filename": "core/foo.py"}, {"filename": "tests/test_foo.py"}],
            ),
            mock.patch.object(write_spec_context, "fetch_spec_prs", return_value=[spec_pr]),
            mock.patch.object(
                write_spec_context,
                "collect_spec_entries",
                return_value=[
                    {"path": "specs/issue-42/product.md", "content": "# Product\n"},
                    {"path": "specs/issue-42/tech.md", "content": "# Tech\n"},
                ],
            ) as collect_spec_entries,
        ):
            context = write_spec_context.resolve_spec_context("owner/repo", pr_event())

        self.assertEqual(context["issue_number"], 42)
        self.assertEqual(context["spec_context_source"], "approved-pr")
        self.assertEqual(context["selected_spec_pr"]["number"], 123)
        self.assertEqual(context["changed_files"], ["core/foo.py", "tests/test_foo.py"])
        collect_spec_entries.assert_called_once_with(
            "owner/repo",
            ["specs/issue-42/product.md", "specs/issue-42/tech.md"],
            "spec/issue-42",
        )

    def test_selects_newest_approved_spec_pr(self) -> None:
        older = {
            "number": 122,
            "html_url": "https://github.test/owner/repo/pull/122",
            "updated_at": "2026-05-12T10:20:30Z",
            "labels": [{"name": "plan-approved"}],
            "head": {"ref": "spec/issue-42", "repo": {"full_name": "owner/repo"}},
        }
        newer = {
            "number": 123,
            "html_url": "https://github.test/owner/repo/pull/123",
            "updated_at": "2026-05-13T10:20:30Z",
            "labels": [{"name": "plan-approved"}],
            "head": {"ref": "spec/issue-42", "repo": {"full_name": "owner/repo"}},
        }

        with (
            mock.patch.object(write_spec_context, "fetch_pr_files", return_value=[]),
            mock.patch.object(write_spec_context, "fetch_spec_prs", return_value=[older, newer]),
            mock.patch.object(
                write_spec_context,
                "collect_spec_entries",
                return_value=[{"path": "specs/issue-42/product.md", "content": "# Product\n"}],
            ) as collect_spec_entries,
        ):
            context = write_spec_context.resolve_spec_context("owner/repo", pr_event())

        self.assertEqual(context["selected_spec_pr"]["number"], 123)
        self.assertEqual([item["number"] for item in context["approved_spec_prs"]], [123, 122])
        collect_spec_entries.assert_called_once_with(
            "owner/repo",
            ["specs/issue-42/product.md", "specs/issue-42/tech.md"],
            "spec/issue-42",
        )

    def test_falls_back_to_directory_when_approved_pr_has_no_spec_entries(self) -> None:
        approved = {
            "number": 123,
            "html_url": "https://github.test/owner/repo/pull/123",
            "updated_at": "2026-05-13T10:20:30Z",
            "labels": [{"name": "plan-approved"}],
            "head": {"ref": "spec/issue-42", "repo": {"full_name": "owner/repo"}},
        }

        with (
            mock.patch.object(write_spec_context, "fetch_pr_files", return_value=[]),
            mock.patch.object(write_spec_context, "fetch_spec_prs", return_value=[approved]),
            mock.patch.object(
                write_spec_context,
                "collect_spec_entries",
                side_effect=[
                    [],
                    [{"path": "specs/issue-42/tech.md", "content": "# Tech\n"}],
                ],
            ) as collect_spec_entries,
        ):
            context = write_spec_context.resolve_spec_context("owner/repo", pr_event())

        self.assertEqual(context["spec_context_source"], "directory")
        self.assertIsNone(context["selected_spec_pr"])
        self.assertEqual(context["approved_spec_prs"][0]["number"], 123)
        self.assertEqual(collect_spec_entries.call_count, 2)

    def test_falls_back_to_default_branch_directory_without_approved_pr(self) -> None:
        unapproved = {
            "number": 122,
            "html_url": "https://github.test/owner/repo/pull/122",
            "updated_at": "2026-05-12T10:20:30Z",
            "labels": [],
            "head": {"ref": "spec/issue-42", "repo": {"full_name": "owner/repo"}},
        }

        with (
            mock.patch.object(write_spec_context, "fetch_pr_files", return_value=[{"filename": "core/foo.py"}]),
            mock.patch.object(write_spec_context, "fetch_spec_prs", return_value=[unapproved]),
            mock.patch.object(
                write_spec_context,
                "collect_spec_entries",
                return_value=[{"path": "specs/issue-42/product.md", "content": "# Product\n"}],
            ) as collect_spec_entries,
        ):
            context = write_spec_context.resolve_spec_context("owner/repo", pr_event())

        self.assertEqual(context["spec_context_source"], "directory")
        self.assertIsNone(context["selected_spec_pr"])
        self.assertEqual(context["unapproved_spec_prs"][0]["number"], 122)
        collect_spec_entries.assert_called_once_with(
            "owner/repo",
            ["specs/issue-42/product.md", "specs/issue-42/tech.md"],
            "base-sha",
        )

    def test_directory_fallback_uses_base_ref_before_default_branch_when_base_sha_missing(self) -> None:
        event = pr_event()
        event["pull_request"]["base"].pop("sha")
        event["pull_request"]["base"]["ref"] = "release/1.0"
        event["pull_request"]["base"]["repo"]["default_branch"] = "main"

        with (
            mock.patch.object(write_spec_context, "fetch_pr_files", return_value=[]),
            mock.patch.object(write_spec_context, "fetch_spec_prs", return_value=[]),
            mock.patch.object(
                write_spec_context,
                "collect_spec_entries",
                return_value=[{"path": "specs/issue-42/product.md", "content": "# Product\n"}],
            ) as collect_spec_entries,
        ):
            context = write_spec_context.resolve_spec_context("owner/repo", event)

        self.assertEqual(context["spec_context_source"], "directory")
        collect_spec_entries.assert_called_once_with(
            "owner/repo",
            ["specs/issue-42/product.md", "specs/issue-42/tech.md"],
            "release/1.0",
        )

    def test_returns_empty_context_without_issue_number(self) -> None:
        with mock.patch.object(write_spec_context, "fetch_pr_files", return_value=[{"filename": "core/foo.py"}]):
            context = write_spec_context.resolve_spec_context("owner/repo", pr_event(body="", head_ref="feat/thing"))

        self.assertIsNone(context["issue_number"])
        self.assertEqual(context["spec_context_source"], "")
        self.assertEqual(context["spec_entries"], [])
        self.assertEqual(context["changed_files"], ["core/foo.py"])

    def test_resolve_spec_context_accepts_local_changed_files(self) -> None:
        with (
            mock.patch.object(write_spec_context, "fetch_pr_files") as fetch_pr_files,
            mock.patch.object(write_spec_context, "fetch_spec_prs", return_value=[]),
            mock.patch.object(write_spec_context, "collect_spec_entries", return_value=[]),
        ):
            context = write_spec_context.resolve_spec_context(
                "owner/repo",
                pr_event(),
                ["core/foo.py", "tests/test_foo.py"],
            )

        fetch_pr_files.assert_not_called()
        self.assertEqual(context["changed_files"], ["core/foo.py", "tests/test_foo.py"])
        self.assertEqual(context["pr_files"], [{"filename": "core/foo.py"}, {"filename": "tests/test_foo.py"}])

    def test_changed_files_from_diff_text_reads_pr_diff_file_entries(self) -> None:
        self.assertEqual(
            write_spec_context.changed_files_from_diff_text(
                "\n".join(["# PR_DIFF_V1", "FILE core/foo.py", "END_FILE", "FILE tests/test_foo.py", "END_FILE"])
            ),
            ["core/foo.py", "tests/test_foo.py"],
        )

    def test_resolves_issue_number_from_branch_suffix(self) -> None:
        self.assertEqual(
            write_spec_context.resolve_issue_number(pr_event(body="", head_ref="feat/thing-42")["pull_request"]),
            42,
        )

    def test_issue_number_token_boundaries_avoid_matching_words(self) -> None:
        self.assertIsNone(write_spec_context.issue_number_from_text("walk through 42 cases"))
        self.assertIsNone(write_spec_context.issue_number_from_text("highlight gh42 as text"))

    def test_issue_number_accepts_explicit_issue_tokens(self) -> None:
        self.assertEqual(write_spec_context.issue_number_from_text("Refs #42"), 42)
        self.assertEqual(write_spec_context.issue_number_from_text("GH-42"), 42)
        self.assertEqual(write_spec_context.issue_number_from_text("issue 42"), 42)

    def test_formats_approved_pr_context(self) -> None:
        text = write_spec_context.format_spec_context_text(
            {
                "spec_context_source": "approved-pr",
                "selected_spec_pr": {"number": 123, "url": "https://github.test/owner/repo/pull/123"},
                "spec_entries": [{"path": "specs/issue-42/product.md", "content": "# Product\n"}],
            }
        )

        self.assertIn("Linked approved spec PR: [#123](https://github.test/owner/repo/pull/123)", text)
        self.assertIn("## specs/issue-42/product.md\n\n# Product", text)

    def test_formats_directory_context(self) -> None:
        text = write_spec_context.format_spec_context_text(
            {
                "spec_context_source": "directory",
                "spec_entries": [{"path": "specs/issue-42/tech.md", "content": "# Tech\n"}],
            }
        )

        self.assertIn("Repository spec context was found in `specs/`.", text)
        self.assertIn("## specs/issue-42/tech.md\n\n# Tech", text)

    def test_formats_missing_context(self) -> None:
        self.assertEqual(
            write_spec_context.format_spec_context_text({"spec_entries": []}),
            "Spec Context: No approved or repository spec context was found for this PR.\n",
        )

    def test_decodes_base64_file_content(self) -> None:
        encoded = base64.b64encode("# Product\n".encode("utf-8")).decode("ascii")
        with mock.patch.object(
            write_spec_context,
            "run_gh_json",
            return_value={"encoding": "base64", "content": encoded},
        ):
            content = write_spec_context.fetch_file_content("owner/repo", "specs/issue-42/product.md", "main")

        self.assertEqual(content, "# Product\n")

    def test_missing_file_returns_none(self) -> None:
        with mock.patch.object(
            write_spec_context,
            "run_gh_json",
            side_effect=subprocess.CalledProcessError(1, ["gh"]),
        ):
            self.assertIsNone(write_spec_context.fetch_file_content("owner/repo", "missing.md", "main"))

    def test_fetch_spec_prs_filters_exact_spec_branch(self) -> None:
        with mock.patch.object(
            write_spec_context,
            "run_gh_json",
            return_value=[
                [
                    {"number": 1, "head": {"ref": "spec/issue-42", "repo": {"full_name": "owner/repo"}}},
                    {"number": 2, "head": {"ref": "spec/issue-420", "repo": {"full_name": "owner/repo"}}},
                ]
            ],
        ) as run_gh_json:
            prs = write_spec_context.fetch_spec_prs("owner/repo", 42)

        self.assertEqual([pr["number"] for pr in prs], [1])
        run_gh_json.assert_called_once_with(
            [
                "api",
                "repos/owner/repo/pulls?state=open&head=owner:spec/issue-42&per_page=100",
                "--paginate",
                "--slurp",
            ]
        )

    def test_main_removes_output_when_no_spec_context_exists(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            event_path = Path(directory) / "event.json"
            output_path = Path(directory) / "spec_context.md"
            event_path.write_text('{"pull_request": {"number": 7, "body": "", "title": "", "head": {"ref": "feat/no-issue"}}}', encoding="utf-8")
            output_path.write_text("stale", encoding="utf-8")

            with (
                mock.patch.object(
                    write_spec_context,
                    "resolve_spec_context",
                    return_value={"spec_context_source": "", "spec_entries": []},
                ),
                mock.patch(
                    "sys.argv",
                    [
                        "write_spec_context.py",
                        "--repo",
                        "owner/repo",
                        "--event-path",
                        str(event_path),
                        "--output",
                        str(output_path),
                    ],
                ),
            ):
                self.assertEqual(write_spec_context.main(), 0)

            self.assertFalse(output_path.exists())

    def test_main_writes_output_when_spec_context_exists(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            event_path = Path(directory) / "event.json"
            output_path = Path(directory) / "spec_context.md"
            event_path.write_text('{"pull_request": {"number": 7}}', encoding="utf-8")

            with (
                mock.patch.object(
                    write_spec_context,
                    "resolve_spec_context",
                    return_value={
                        "spec_context_source": "directory",
                        "spec_entries": [{"path": "specs/issue-42/product.md", "content": "# Product\n"}],
                    },
                ),
                mock.patch(
                    "sys.argv",
                    [
                        "write_spec_context.py",
                        "--repo",
                        "owner/repo",
                        "--event-path",
                        str(event_path),
                        "--output",
                        str(output_path),
                    ],
                ),
            ):
                self.assertEqual(write_spec_context.main(), 0)

            self.assertIn("## specs/issue-42/product.md", output_path.read_text(encoding="utf-8"))

    def test_main_can_use_changed_files_from_diff(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            event_path = Path(directory) / "event.json"
            diff_path = Path(directory) / "pr_diff.txt"
            output_path = Path(directory) / "spec_context.md"
            event_path.write_text('{"pull_request": {"number": ""}}', encoding="utf-8")
            diff_path.write_text("# PR_DIFF_V1\nFILE core/foo.py\nEND_FILE\n", encoding="utf-8")

            with (
                mock.patch.object(
                    write_spec_context,
                    "resolve_spec_context",
                    return_value={
                        "spec_context_source": "directory",
                        "spec_entries": [{"path": "specs/issue-42/product.md", "content": "# Product\n"}],
                    },
                ) as resolve_spec_context,
                mock.patch(
                    "sys.argv",
                    [
                        "write_spec_context.py",
                        "--repo",
                        "owner/repo",
                        "--event-path",
                        str(event_path),
                        "--changed-files-from-diff",
                        str(diff_path),
                        "--output",
                        str(output_path),
                    ],
                ),
            ):
                self.assertEqual(write_spec_context.main(), 0)

        resolve_spec_context.assert_called_once_with("owner/repo", {"pull_request": {"number": ""}}, ["core/foo.py"])


if __name__ == "__main__":
    unittest.main()
