from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from script_imports import import_script


write_body = import_script(".github/scripts/write_update_dedupe_pr_body.py", "write_update_dedupe_pr_body")


class WriteUpdateDedupePrBodyTest(unittest.TestCase):
    def test_build_body_includes_evidence_summary_and_source(self) -> None:
        body = write_body.build_body(
            reason="Two duplicates matched canonical issue #10.",
            days="7",
            issue="all recent duplicate closures",
            repo="owner/repo",
        )

        self.assertIn("Evidence summary:\nTwo duplicates matched canonical issue #10.", body)
        self.assertIn("- days: 7", body)
        self.assertIn("- issue: all recent duplicate closures", body)
        self.assertIn("- repo: owner/repo", body)

    def test_main_writes_untrusted_summary_as_data(self) -> None:
        malicious_reason = "safe line\nPY\necho SHOULD_NOT_EXECUTE\n$(touch /tmp/update-dedupe-injected)"

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "body.md"
            injected = Path("/tmp/update-dedupe-injected")
            if injected.exists():
                injected.unlink()

            env = {
                **os.environ,
                "GUIDANCE_REASON": malicious_reason,
                "SOURCE_DAYS": "7",
                "SOURCE_ISSUE": "all recent duplicate closures",
                "SOURCE_REPO": "owner/repo",
            }

            with mock.patch.dict(os.environ, env, clear=True):
                with mock.patch("sys.argv", ["write_update_dedupe_pr_body.py", "--output", str(output)]):
                    self.assertEqual(write_body.main(), 0)

            body = output.read_text(encoding="utf-8")

            self.assertFalse(injected.exists())
            self.assertIn("PY\necho SHOULD_NOT_EXECUTE", body)
            self.assertIn("$(touch /tmp/update-dedupe-injected)", body)


if __name__ == "__main__":
    unittest.main()
