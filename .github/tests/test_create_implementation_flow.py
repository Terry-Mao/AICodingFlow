from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from script_imports import import_script


prepare_impl = import_script(
    ".github/scripts/prepare_issue_implementation_context.py",
    "prepare_issue_implementation_context_flow",
)
validate_impl = import_script(
    ".github/scripts/validate_implementation_output.py",
    "validate_implementation_output_flow",
)
finalize_impl = import_script(
    ".github/scripts/finalize_implementation_pr.py",
    "finalize_implementation_pr_flow",
)


class CreateImplementationFlowTest(unittest.TestCase):
    def test_standalone_directory_spec_flow_reaches_draft_pr_creation(self) -> None:
        issue = {
            "number": 18,
            "title": "Implement issue",
            "body": "",
            "author": {"login": "maintainer"},
            "labels": [{"name": "ready-to-implement"}],
            "assignees": [{"login": "codex"}],
            "url": "https://github.test/owner/repo/issues/18",
        }

        with tempfile.TemporaryDirectory() as directory:
            issue_context = Path(directory) / "issue_context.json"
            issue_comments = Path(directory) / "issue_comments.txt"
            spec_context = Path(directory) / "spec_context.md"
            metadata = Path(directory) / "pr-metadata.json"
            github_output = Path(directory) / "github_output.txt"
            event_path = Path(directory) / "event.json"
            event_path.write_text(
                json.dumps({"action": "labeled", "label": {"name": "ready-to-implement"}}),
                encoding="utf-8",
            )
            with (
                mock.patch.object(prepare_impl, "fetch_issue", return_value=issue),
                mock.patch.object(prepare_impl, "fetch_comments", return_value=[]),
                mock.patch.object(prepare_impl, "fetch_default_branch", return_value="main"),
                mock.patch.object(prepare_impl, "fetch_spec_prs", return_value=[]),
                mock.patch.object(
                    prepare_impl,
                    "collect_spec_entries",
                    return_value=[
                        {"path": "specs/issue-18/product.md", "content": "# Product\n"},
                        {"path": "specs/issue-18/tech.md", "content": "# Tech\n"},
                    ],
                ),
                mock.patch.object(prepare_impl, "has_existing_implementation_pr", return_value=False),
                mock.patch.object(prepare_impl, "best_effort_assign", return_value=""),
                mock.patch(
                    "sys.argv",
                    [
                        "prepare_issue_implementation_context.py",
                        "--repo",
                        "owner/repo",
                        "--issue",
                        "18",
                        "--event-name",
                        "issues",
                        "--event-path",
                        str(event_path),
                        "--agent-login",
                        "codex",
                        "--output",
                        str(issue_context),
                        "--comments-output",
                        str(issue_comments),
                        "--spec-context-output",
                        str(spec_context),
                        "--github-output",
                        str(github_output),
                    ],
                ),
            ):
                prepare_impl.main()

            context = json.loads(issue_context.read_text(encoding="utf-8"))
            self.assertTrue(context["should_run"])
            self.assertFalse(context["should_noop"])
            self.assertEqual(context["target_branch"], "spec/implement-issue-18")
            self.assertEqual(context["spec_context_source"], "directory")
            self.assertIn("## specs/issue-18/product.md", spec_context.read_text(encoding="utf-8"))

            metadata.write_text(
                json.dumps(
                    {
                        "branch_name": "spec/implement-issue-18",
                        "pr_title": "feat: implement issue workflow",
                        "pr_summary": "Closes #18\n\n## Summary\n- Implemented",
                        "intended_files": [".github/workflows/create-implementation-from-issue.yml"],
                    }
                ),
                encoding="utf-8",
            )
            validate_impl.validate_metadata(metadata, issue_context)

            with (
                mock.patch.object(finalize_impl, "open_pr_for_branch", return_value=None),
                mock.patch.object(
                    finalize_impl,
                    "create_pr",
                    return_value="https://github.test/owner/repo/pull/125",
                ) as create_pr,
            ):
                pr_url = finalize_impl.finalize(
                    "owner/repo",
                    context,
                    json.loads(metadata.read_text(encoding="utf-8")),
                )

        self.assertEqual(pr_url, "https://github.test/owner/repo/pull/125")
        create_pr.assert_called_once_with(
            "owner/repo",
            "main",
            "spec/implement-issue-18",
            "feat: implement issue workflow",
            "Closes #18\n\n## Summary\n- Implemented",
        )


if __name__ == "__main__":
    unittest.main()
