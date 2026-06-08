from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from script_imports import import_script


contracts = import_script(".github/scripts/pr_metadata_contracts.py", "pr_metadata_contracts")


class PrMetadataContractTests(unittest.TestCase):
    def write_json(self, directory: str, name: str, value: object) -> Path:
        path = Path(directory) / name
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def test_validate_base_metadata_accepts_common_contract(self) -> None:
        metadata = {
            "branch_name": "feature",
            "pr_title": "feat: add workflow",
            "pr_summary": "Refs #1\n\n## Summary\nDone.",
        }

        contracts.validate_base_metadata(metadata)

    def test_validate_base_metadata_rejects_missing_string_and_title(self) -> None:
        with self.assertRaisesRegex(SystemExit, "missing fields: pr_summary"):
            contracts.validate_base_metadata({"branch_name": "feature", "pr_title": "feat: ok"})

        with self.assertRaisesRegex(SystemExit, "branch_name must be a non-empty string"):
            contracts.validate_base_metadata({"branch_name": "", "pr_title": "feat: ok", "pr_summary": "x\nx"})

        with self.assertRaisesRegex(SystemExit, "conventional commit style"):
            contracts.validate_base_metadata(
                {"branch_name": "feature", "pr_title": "Add workflow", "pr_summary": "x\nx"}
            )

    def test_validate_intended_files_normalizes_and_rejects_unsafe_paths(self) -> None:
        self.assertEqual(
            contracts.validate_intended_files({"intended_files": [" app.py ", "tests/test_app.py"]}),
            ["app.py", "tests/test_app.py"],
        )

        with self.assertRaisesRegex(SystemExit, "repository-relative"):
            contracts.validate_intended_files({"intended_files": ["../app.py"]})

        with self.assertRaisesRegex(SystemExit, "handoff"):
            contracts.validate_intended_files({"intended_files": ["pr-metadata.json"]})

        with self.assertRaisesRegex(SystemExit, "generated/cache"):
            contracts.validate_intended_files({"intended_files": [".codex-runtime/skills/example/SKILL.md"]})

    def test_load_json_object_validates_required_object(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_json(directory, "metadata.json", {"branch_name": "feature"})
            self.assertEqual(contracts.load_json_object(path), {"branch_name": "feature"})

            missing = Path(directory) / "missing.json"
            self.assertEqual(contracts.load_json_object(missing, required=False), {})

            invalid = self.write_json(directory, "list.json", [])
            with self.assertRaisesRegex(SystemExit, "must contain a JSON object"):
                contracts.load_json_object(invalid)


if __name__ == "__main__":
    unittest.main()
