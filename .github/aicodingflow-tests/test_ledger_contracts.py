from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from script_imports import import_script


ledger_contracts = import_script(".github/scripts/ledger_contracts.py", "ledger_contracts")


class LedgerContractsTest(unittest.TestCase):
    def test_load_ledger_defaults_and_indexes_entries_by_pr(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "ledger.json"
            ledger = ledger_contracts.load_ledger(missing, ledger_name="test")

        self.assertEqual(ledger, {"version": 1, "entries": []})
        self.assertEqual(
            ledger_contracts.entries_by_pr({"entries": [{"pr": "1"}, {"pr": None}, {"pr": 2}]}),
            {1: {"pr": "1"}, 2: {"pr": 2}},
        )

    def test_load_ledger_rejects_invalid_entries_shape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.json"
            path.write_text('{"entries": {}}', encoding="utf-8")

            with self.assertRaisesRegex(SystemExit, "invalid test ledger entries"):
                ledger_contracts.load_ledger(path, ledger_name="test")

    def test_set_sorted_entries_orders_by_merge_time_and_pr_number(self) -> None:
        ledger = ledger_contracts.set_sorted_entries(
            {},
            [
                {"pr": 3, "merged_at": "2026-06-02T00:00:00Z"},
                {"pr": 1, "merged_at": "2026-06-01T00:00:00Z"},
                {"pr": 2, "merged_at": "2026-06-01T00:00:00Z"},
            ],
        )

        self.assertEqual([entry["pr"] for entry in ledger["entries"]], [1, 2, 3])
        self.assertEqual(ledger["version"], 1)


if __name__ == "__main__":
    unittest.main()
