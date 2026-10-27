from __future__ import annotations

import unittest
import tempfile
import json
import subprocess
from pathlib import Path
from unittest import mock

from script_imports import import_script


rounds = import_script(".github/scripts/prepare_review_round_context.py", "prepare_review_round_context")


class ReviewRoundContextTests(unittest.TestCase):
    def test_main_generates_incremental_diff_from_prior_reviewed_commit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            heads = []
            for number in range(1, 5):
                (root / "example.py").write_text(f"VALUE = {number}\n", encoding="utf-8")
                subprocess.run(["git", "add", "example.py"], cwd=root, check=True)
                subprocess.run(["git", "commit", "-qm", f"change {number}"], cwd=root, check=True)
                heads.append(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip())
            reviews = [{
                "user": {"login": "github-actions[bot]"}, "state": "COMMENTED", "commit_id": sha,
                "body": f"<!-- aicodingflow-review base={'f' * 40} head={sha} -->",
            } for sha in heads[:3]]
            output = root / "round.json"
            incremental = root / "incremental.txt"
            with (
                mock.patch.object(rounds, "fetch_reviews", return_value=reviews),
                mock.patch("sys.argv", ["prepare_review_round_context.py", "--repo", "owner/repo", "--pr-number", "1", "--head-sha", heads[3], "--base-sha", "f" * 40, "--worktree", str(root), "--output", str(output), "--incremental-diff", str(incremental)]),
            ):
                rounds.main()
            self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["mode"], "incremental")
            self.assertIn("RIGHT", incremental.read_text(encoding="utf-8"))

    def test_check_existing_writes_early_skip_output(self) -> None:
        head = "a" * 40
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "github-output"
            with (
                mock.patch.object(rounds, "fetch_reviews", return_value=[{
                    "user": {"login": "github-actions[bot]"}, "state": "COMMENTED", "commit_id": head,
                }]),
                mock.patch.object(rounds, "is_ancestor") as ancestor,
                mock.patch("sys.argv", ["prepare_review_round_context.py", "--repo", "owner/repo", "--pr-number", "1", "--head-sha", head, "--check-existing", "--github-output", str(output)]),
            ):
                rounds.main()
            self.assertEqual(output.read_text(encoding="utf-8"), "already_reviewed=true\n")
            ancestor.assert_not_called()

    def test_counts_distinct_published_bot_heads_across_runs(self) -> None:
        heads = [character * 40 for character in "abcd"]
        reviews = [
            {"user": {"login": "github-actions[bot]"}, "state": "COMMENTED", "commit_id": sha,
             "body": f"ok\n<!-- aicodingflow-review base={'f' * 40} head={sha} -->"}
            for sha in heads[:3]
        ]
        reviews.append(dict(reviews[-1]))
        reviews.append({"user": {"login": "human"}, "state": "APPROVED", "commit_id": heads[3]})
        history = rounds.review_history(reviews, "github-actions[bot]")
        self.assertEqual(len(history), 3)
        self.assertEqual(rounds.round_context(history, heads[2], "f" * 40, True)["round"], 3)
        context = rounds.round_context(history, heads[3], "f" * 40, True)
        self.assertEqual((context["round"], context["mode"], context["previous_head_sha"]), (4, "incremental", heads[2]))

    def test_history_change_or_base_change_falls_back_to_full(self) -> None:
        history = [(character * 40, "f" * 40) for character in "abc"]
        self.assertEqual(rounds.round_context(history, "d" * 40, "e" * 40, True)["mode"], "full")
        self.assertEqual(rounds.round_context(history, "d" * 40, "f" * 40, False)["mode"], "full")


if __name__ == "__main__":
    unittest.main()
