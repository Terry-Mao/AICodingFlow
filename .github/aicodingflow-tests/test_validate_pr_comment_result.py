from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from script_imports import import_script


validator = import_script(".github/scripts/validate_pr_comment_result.py", "validate_pr_comment_result")


class ValidatePrCommentResultTest(unittest.TestCase):
    def write_json(self, directory: Path, name: str, value: dict) -> Path:
        path = directory / name
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def test_valid_metadata_and_resolved_comments_are_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            context = self.write_json(root, "pr_comment_context.json", {"agent_push_branch": "feature"})
            metadata = self.write_json(
                root,
                "pr-metadata.json",
                {
                    "branch_name": "feature",
                    "pr_title": "fix: update parser",
                    "pr_summary": "Refs #42\n\n## Summary\nUpdated parser.",
                    "intended_files": ["app.py"],
                },
            )
            resolved = self.write_json(
                root,
                "resolved_review_comments.json",
                {"resolved_review_comments": [{"comment_id": 123, "summary": "Updated `.github/workflows/review-pr.yml`."}]},
            )
            ids = self.write_json(root, "review_comment_ids.json", {"review_comments": [{"comment_id": 123}]})

            validator.validate_metadata(metadata, context, ["app.py"])
            validator.validate_resolved_comments(resolved, ids)

    def test_metadata_branch_must_match_agent_push_branch(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            context = self.write_json(root, "pr_comment_context.json", {"agent_push_branch": "feature"})
            metadata = self.write_json(
                root,
                "pr-metadata.json",
                {
                    "branch_name": "other",
                    "pr_title": "fix: update parser",
                    "pr_summary": "Refs #42\n\nBody",
                    "intended_files": ["app.py"],
                },
            )

            with self.assertRaisesRegex(SystemExit, "branch_name must equal"):
                validator.validate_metadata(metadata, context, ["app.py"])

    def test_metadata_rejects_handoff_and_unexpected_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            context = self.write_json(root, "pr_comment_context.json", {"agent_push_branch": "feature"})
            metadata = self.write_json(
                root,
                "pr-metadata.json",
                {
                    "branch_name": "feature",
                    "pr_title": "fix: update parser",
                    "pr_summary": "Refs #42\n\nBody",
                    "intended_files": ["pr_comment_context.json"],
                },
            )

            with self.assertRaisesRegex(SystemExit, "handoff"):
                validator.validate_metadata(metadata, context, ["app.py"])

            metadata.write_text(
                json.dumps(
                    {
                        "branch_name": "feature",
                        "pr_title": "fix: update parser",
                        "pr_summary": "Refs #42\n\nBody",
                        "intended_files": ["app.py"],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(SystemExit, "not listed"):
                validator.validate_metadata(metadata, context, ["app.py", "tests/test_app.py"])

    def test_metadata_ignores_runtime_skill_copy_but_not_tracked_skill_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            context = self.write_json(root, "pr_comment_context.json", {"agent_push_branch": "feature"})
            metadata = self.write_json(
                root,
                "pr-metadata.json",
                {
                    "branch_name": "feature",
                    "pr_title": "fix: update parser",
                    "pr_summary": "Refs #42\n\nBody",
                    "intended_files": ["app.py"],
                },
            )

            validator.validate_metadata(
                metadata,
                context,
                ["app.py", ".codex-runtime/skills/implement-specs/SKILL.md"],
            )

            with self.assertRaisesRegex(SystemExit, "not listed"):
                validator.validate_metadata(
                    metadata,
                    context,
                    ["app.py", ".github/skills/implement-specs/SKILL.md"],
                )

            metadata.write_text(
                json.dumps(
                    {
                        "branch_name": "feature",
                        "pr_title": "fix: update parser",
                        "pr_summary": "Refs #42\n\nBody",
                        "intended_files": [".codex-runtime/skills/implement-specs/SKILL.md"],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(SystemExit, "generated/cache"):
                validator.validate_metadata(metadata, context, [".codex-runtime/skills/implement-specs/SKILL.md"])

    def test_resolved_comments_reject_unknown_and_duplicate_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ids = self.write_json(root, "review_comment_ids.json", {"review_comments": [{"comment_id": 123}]})
            unknown = self.write_json(
                root,
                "resolved_review_comments.json",
                {"resolved_review_comments": [{"comment_id": 456, "summary": "Done."}]},
            )
            with self.assertRaisesRegex(SystemExit, "not a current PR review comment id"):
                validator.validate_resolved_comments(unknown, ids)

            duplicate = self.write_json(
                root,
                "resolved_review_comments.json",
                {
                    "resolved_review_comments": [
                        {"comment_id": 123, "summary": "Done."},
                        {"comment_id": 123, "summary": "Done again."},
                    ]
                },
            )
            with self.assertRaisesRegex(SystemExit, "duplicated"):
                validator.validate_resolved_comments(duplicate, ids)

    def test_main_uses_current_worktree_candidate_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_json(root, "pr_comment_context.json", {"agent_push_branch": "feature"})
            self.write_json(
                root,
                "pr-metadata.json",
                {
                    "branch_name": "feature",
                    "pr_title": "fix: update parser",
                    "pr_summary": "Refs #42\n\nBody",
                    "intended_files": ["app.py"],
                },
            )
            self.write_json(root, "review_comment_ids.json", {"review_comments": []})
            with (
                mock.patch.object(validator, "status_paths", return_value=["app.py", "pr-metadata.json"]),
                mock.patch(
                    "sys.argv",
                    [
                        "validate_pr_comment_result.py",
                        "--context",
                        str(root / "pr_comment_context.json"),
                        "--metadata",
                        str(root / "pr-metadata.json"),
                        "--resolved",
                        str(root / "resolved_review_comments.json"),
                        "--review-comment-ids",
                        str(root / "review_comment_ids.json"),
                    ],
                ),
            ):
                validator.main()


if __name__ == "__main__":
    unittest.main()
