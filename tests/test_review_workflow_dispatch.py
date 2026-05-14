from __future__ import annotations

import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def workflow(path: str) -> dict:
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))


def steps(workflow_data: dict, job: str) -> list[dict]:
    return workflow_data["jobs"][job]["steps"]


class ReviewWorkflowDispatchTest(unittest.TestCase):
    def test_review_workflow_keeps_pull_request_trigger_and_adds_manual_pr_number(self) -> None:
        data = workflow(".github/workflows/review-pr.yml")
        triggers = data[True]

        self.assertIn("pull_request", triggers)
        self.assertEqual(
            triggers["pull_request"]["types"],
            ["opened", "synchronize", "reopened", "ready_for_review", "edited"],
        )
        self.assertTrue(triggers["workflow_dispatch"]["inputs"]["pr_number"]["required"])
        self.assertEqual(
            data["jobs"]["review"]["if"],
            "github.event_name == 'workflow_dispatch' || (github.event.pull_request.draft == false && github.event.pull_request.head.repo.full_name == github.repository)",
        )

    def test_review_workflow_resolves_pr_before_checkout_and_uses_normalized_event(self) -> None:
        data = workflow(".github/workflows/review-pr.yml")
        names = [step.get("name") or step.get("uses") for step in steps(data, "review")]

        self.assertLess(names.index("Checkout workflow scripts"), names.index("Resolve pull request"))
        self.assertLess(names.index("Resolve pull request"), names.index("Checkout PR head"))

        review_steps = steps(data, "review")
        resolve_step = next(step for step in review_steps if step.get("name") == "Resolve pull request")
        self.assertIn(".github/scripts/resolve_pr_event.py", resolve_step["run"])
        self.assertIn("--output \"$RUNNER_TEMP/pr_event.json\"", resolve_step["run"])

        description_step = next(step for step in review_steps if step.get("name") == "Snapshot PR description")
        post_step = next(step for step in review_steps if step.get("name") == "Post PR review")
        self.assertEqual(description_step["env"]["GITHUB_EVENT_PATH"], "${{ steps.pr.outputs.event_path }}")
        self.assertEqual(post_step["env"]["GITHUB_EVENT_PATH"], "${{ steps.pr.outputs.event_path }}")

    def test_create_spec_workflow_dispatches_review_after_pr_creation(self) -> None:
        data = workflow(".github/workflows/create-spec-from-issue.yml")
        self.assertEqual(data["permissions"]["actions"], "write")

        create_steps = steps(data, "create-spec")
        create_pr = next(step for step in create_steps if step.get("name") == "Create or update spec pull request")
        dispatch = next(step for step in create_steps if step.get("name") == "Dispatch AI PR review")

        self.assertEqual(create_pr["id"], "pr")
        self.assertEqual(create_pr["run"].count("--json number --jq .number"), 1)
        self.assertIn("echo \"pr_number=$pr_number\" >> \"$GITHUB_OUTPUT\"", create_pr["run"])
        self.assertIn("steps.pr.outputs.pr_number != ''", dispatch["if"])
        self.assertIn("gh workflow run review-pr.yml", dispatch["run"])
        self.assertIn("-f pr_number=\"$PR_NUMBER\"", dispatch["run"])
        self.assertEqual(dispatch["env"]["PR_NUMBER"], "${{ steps.pr.outputs.pr_number }}")


if __name__ == "__main__":
    unittest.main()
