from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from script_imports import import_script


writer = import_script(".github/scripts/write_pr_description.py", "write_pr_description")


class WritePrDescriptionTest(unittest.TestCase):
    def test_main_reads_normalized_pr_event_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            event_path = Path(directory) / "pr_event.json"
            output_path = Path(directory) / "pr_description.txt"
            event_path.write_text(
                json.dumps(
                    {
                        "pull_request": {
                            "title": "Fix review",
                            "number": 71,
                            "user": {"login": "author"},
                            "base": {"ref": "main", "sha": "base123"},
                            "head": {"ref": "feature", "sha": "head456"},
                            "html_url": "https://github.test/pull/71",
                            "body": "Body text",
                        }
                    }
                ),
                encoding="utf-8",
            )

            with (
                mock.patch.dict("os.environ", {"PR_EVENT_PATH": str(event_path)}, clear=True),
                mock.patch("sys.argv", ["write_pr_description.py", "--output", str(output_path)]),
            ):
                writer.main()

            text = output_path.read_text(encoding="utf-8")
            self.assertIn("Title: Fix review", text)
            self.assertIn("Number: 71", text)
            self.assertIn("Base: main @ base123", text)
            self.assertIn("Head: feature @ head456", text)

    def test_main_rejects_unresolved_issue_comment_payload(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            event_path = Path(directory) / "event.json"
            event_path.write_text(json.dumps({"issue": {"number": 71}}), encoding="utf-8")

            with (
                mock.patch.dict("os.environ", {"PR_EVENT_PATH": str(event_path)}, clear=True),
                mock.patch("sys.argv", ["write_pr_description.py"]),
                self.assertRaisesRegex(SystemExit, "missing pull_request"),
            ):
                writer.main()


if __name__ == "__main__":
    unittest.main()
