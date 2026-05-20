from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from script_imports import import_script


validator = import_script(
    ".github/scripts/validate_issue_triage_result.py",
    "validate_issue_triage_result",
)


class ValidateIssueTriageResultTest(unittest.TestCase):
    def write_result(self, directory: str, data: dict) -> Path:
        path = Path(directory) / "triage_result.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def valid_result(self) -> dict:
        return {
            "labels": ["bug", "needs-info", "repro:unknown"],
            "repro": "unknown",
            "confidence": "medium",
            "related_files": ["app.py"],
            "root_cause": "The current report does not include enough evidence to confirm a root cause.",
            "summary": "Needs more information before implementation.",
            "follow_up_questions": [
                {
                    "question": "Can you share the exact command and full error output?",
                    "reasoning": "The report does not include enough reproduction context.",
                }
            ],
            "duplicate_of": [],
            "issue_body": "### Triage\n\nNeeds more information.",
        }

    def write_context(self, directory: str, labels: list[str]) -> Path:
        path = Path(directory) / "triage_context.json"
        path.write_text(
            json.dumps(
                {
                    "triage_config": {
                        "labels": {label: {"color": "cccccc", "description": label} for label in labels}
                    }
                }
            ),
            encoding="utf-8",
        )
        return path

    def test_accepts_valid_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_result(directory, self.valid_result())
            context = self.write_context(directory, ["bug", "needs-info", "repro:unknown"])
            self.assertEqual(validator.validate_result(path, context_path=context)["repro"], "unknown")

    def test_accepts_valid_result_with_context_label_config(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_result(directory, self.valid_result())
            context = self.write_context(directory, ["bug", "needs-info", "repro:unknown"])

            self.assertEqual(validator.validate_result(path, context_path=context)["repro"], "unknown")

    def test_rejects_follow_up_questions_without_needs_info_when_configured(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            data = self.valid_result()
            data["labels"] = ["bug", "repro:unknown"]
            path = self.write_result(directory, data)
            context = self.write_context(directory, ["bug", "needs-info", "repro:unknown"])

            with self.assertRaisesRegex(SystemExit, "needs-info label"):
                validator.validate_result(path, context_path=context)

    def test_rejects_empty_follow_up_questions_without_triaged_when_configured(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            data = self.valid_result()
            data["labels"] = ["bug", "repro:unknown"]
            data["follow_up_questions"] = []
            path = self.write_result(directory, data)
            context = self.write_context(directory, ["bug", "triaged", "repro:unknown"])

            with self.assertRaisesRegex(SystemExit, "triaged label"):
                validator.validate_result(path, context_path=context)

    def test_allows_empty_follow_up_questions_without_triaged_when_not_configured(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            data = self.valid_result()
            data["labels"] = ["bug", "repro:unknown"]
            data["follow_up_questions"] = []
            path = self.write_result(directory, data)
            context = self.write_context(directory, ["bug", "repro:unknown"])

            self.assertEqual(validator.validate_result(path, context_path=context)["follow_up_questions"], [])

    def test_rejects_protected_labels(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            for label in ("plan-approved", "ready-to-implement", "ready-to-spec"):
                with self.subTest(label=label):
                    data = self.valid_result()
                    data["labels"] = [label]
                    path = self.write_result(directory, data)
                    context = self.write_context(directory, [label, "repro:unknown"])
                    with self.assertRaisesRegex(SystemExit, "protected labels"):
                        validator.validate_result(path, context_path=context)

    def test_rejects_labels_not_present_in_context_config(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_result(directory, self.valid_result())
            context = self.write_context(directory, ["bug", "repro:unknown"])

            with self.assertRaisesRegex(SystemExit, "not present in triage config"):
                validator.validate_result(path, context_path=context)

    def test_rejects_invalid_repro_value(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            data = self.valid_result()
            data["repro"] = "sometimes"
            path = self.write_result(directory, data)
            context = self.write_context(directory, ["bug", "needs-info", "repro:unknown"])

            with self.assertRaisesRegex(SystemExit, "repro must be one of"):
                validator.validate_result(path, context_path=context)

    def test_rejects_follow_up_and_duplicates_together(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            data = self.valid_result()
            data["labels"] = ["bug", "duplicate", "repro:unknown"]
            data["duplicate_of"] = [
                {"issue_number": 1, "title": "same", "similarity_reason": "same failure"},
                {"issue_number": 2, "title": "same again", "similarity_reason": "same failure"},
            ]
            path = self.write_result(directory, data)
            context = self.write_context(directory, ["bug", "duplicate", "repro:unknown"])
            with self.assertRaisesRegex(SystemExit, "mutually exclusive"):
                validator.validate_result(path, context_path=context)

    def test_rejects_single_duplicate_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            data = self.valid_result()
            data["follow_up_questions"] = []
            data["duplicate_of"] = [{"issue_number": 1, "title": "same", "similarity_reason": "same failure"}]
            path = self.write_result(directory, data)
            context = self.write_context(directory, ["bug", "needs-info", "repro:unknown"])
            with self.assertRaisesRegex(SystemExit, "at least 2"):
                validator.validate_result(path, context_path=context)

    def test_rejects_duplicate_without_duplicate_label_when_configured(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            data = self.valid_result()
            data["follow_up_questions"] = []
            data["duplicate_of"] = [
                {"issue_number": 1, "title": "same", "similarity_reason": "same failure"},
                {"issue_number": 2, "title": "same again", "similarity_reason": "same failure"},
            ]
            path = self.write_result(directory, data)
            context = self.write_context(directory, ["bug", "needs-info", "duplicate", "repro:unknown"])
            with self.assertRaisesRegex(SystemExit, "duplicate label"):
                validator.validate_result(path, context_path=context)

    def test_rejects_duplicate_with_triaged(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            data = self.valid_result()
            data["labels"] = ["duplicate", "triaged", "repro:unknown"]
            data["follow_up_questions"] = []
            data["duplicate_of"] = [
                {"issue_number": 1, "title": "same", "similarity_reason": "same failure"},
                {"issue_number": 2, "title": "same again", "similarity_reason": "same failure"},
            ]
            path = self.write_result(directory, data)
            context = self.write_context(directory, ["bug", "duplicate", "triaged", "repro:unknown"])
            with self.assertRaisesRegex(SystemExit, "must not include the triaged label"):
                validator.validate_result(path, context_path=context)

    def test_allows_duplicate_without_triaged_when_configured(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            data = self.valid_result()
            data["labels"] = ["duplicate", "repro:unknown"]
            data["follow_up_questions"] = []
            data["duplicate_of"] = [
                {"issue_number": 1, "title": "same", "similarity_reason": "same failure"},
                {"issue_number": 2, "title": "same again", "similarity_reason": "same failure"},
            ]
            path = self.write_result(directory, data)
            context = self.write_context(directory, ["duplicate", "triaged", "repro:unknown"])

            self.assertEqual(validator.validate_result(path, context_path=context)["labels"], data["labels"])

    def test_allows_duplicate_without_duplicate_label_when_not_configured(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            data = self.valid_result()
            data["follow_up_questions"] = []
            data["duplicate_of"] = [
                {"issue_number": 1, "title": "same", "similarity_reason": "same failure"},
                {"issue_number": 2, "title": "same again", "similarity_reason": "same failure"},
            ]
            path = self.write_result(directory, data)
            context = self.write_context(directory, ["bug", "needs-info", "repro:unknown"])
            self.assertEqual(validator.validate_result(path, context_path=context)["duplicate_of"][0]["issue_number"], 1)

    def test_requires_issue_body_when_workflow_requests_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            data = self.valid_result()
            data["issue_body"] = ""
            path = self.write_result(directory, data)
            context = self.write_context(directory, ["bug", "needs-info", "repro:unknown"])
            with self.assertRaisesRegex(SystemExit, "issue_body is required"):
                validator.validate_result(path, require_issue_body=True, context_path=context)


if __name__ == "__main__":
    unittest.main()
