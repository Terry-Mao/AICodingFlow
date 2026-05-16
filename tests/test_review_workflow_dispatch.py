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
    def test_workflows_use_node24_action_runtime(self) -> None:
        workflow_jobs = {
            ".github/workflows/create-implementation-from-issue.yml": "create-implementation",
            ".github/workflows/create-spec-from-issue.yml": "create-spec",
            ".github/workflows/review-pr.yml": "review",
            ".github/workflows/update-pr-review.yml": "update",
        }

        for path, job_name in workflow_jobs.items():
            with self.subTest(path=path):
                data = workflow(path)
                job = data["jobs"][job_name]
                self.assertEqual(job["env"]["FORCE_JAVASCRIPT_ACTIONS_TO_NODE24"], "true")
                used_actions = [step.get("uses", "") for step in steps(data, job_name) if "uses" in step]
                self.assertNotIn("actions/checkout@v4", used_actions)
                self.assertNotIn("actions/upload-artifact@v4", used_actions)

                for action in used_actions:
                    if action.startswith("actions/checkout@"):
                        self.assertEqual(action, "actions/checkout@v6")
                    if action.startswith("actions/upload-artifact@"):
                        self.assertEqual(action, "actions/upload-artifact@v7")

    def test_review_workflow_keeps_pull_request_trigger_and_adds_manual_pr_number(self) -> None:
        data = workflow(".github/workflows/review-pr.yml")
        triggers = data[True]

        self.assertIn("pull_request", triggers)
        self.assertEqual(triggers["pull_request"]["types"], ["opened", "reopened", "synchronize", "ready_for_review"])
        self.assertNotIn("pull_request_target", triggers)
        self.assertEqual(triggers["issue_comment"]["types"], ["created"])
        self.assertTrue(triggers["workflow_dispatch"]["inputs"]["pr_number"]["required"])
        job_gate = data["jobs"]["preflight"]["if"]
        self.assertIn("github.event_name == 'workflow_dispatch'", job_gate)
        self.assertIn("github.event_name == 'pull_request'", job_gate)
        self.assertIn("github.event.pull_request.head.repo.full_name == github.repository", job_gate)
        self.assertIn("github.event_name == 'issue_comment'", job_gate)
        self.assertIn("github.event.issue.pull_request != null", job_gate)
        self.assertIn("contains(github.event.comment.body, format('@{0}', vars.AGENT_LOGIN))", job_gate)
        self.assertEqual(data["jobs"]["review"]["needs"], "preflight")
        self.assertEqual(data["jobs"]["review"]["if"], "needs.preflight.outputs.reviewable == 'true'")

    def test_review_workflow_resolves_pr_before_checkout_and_uses_normalized_event(self) -> None:
        data = workflow(".github/workflows/review-pr.yml")
        names = [step.get("name") or step.get("uses") for step in steps(data, "review")]

        self.assertLess(names.index("Checkout workflow scripts"), names.index("Resolve pull request"))
        self.assertLess(names.index("Resolve pull request"), names.index("Checkout PR head"))

        review_steps = steps(data, "review")
        checkout_pr_head = next(step for step in review_steps if step.get("name") == "Checkout PR head")
        self.assertEqual(checkout_pr_head["with"]["persist-credentials"], False)
        self.assertEqual(checkout_pr_head["with"]["repository"], "${{ steps.pr.outputs.head_repo }}")
        self.assertEqual(checkout_pr_head["with"]["ref"], "${{ steps.pr.outputs.head_sha }}")
        self.assertEqual(checkout_pr_head["with"]["path"], "pr-worktree")

        resolve_step = next(step for step in review_steps if step.get("name") == "Resolve pull request")
        self.assertIn(".github/scripts/resolve_pr_event.py", resolve_step["run"])
        self.assertIn("--output \"$RUNNER_TEMP/pr_event.json\"", resolve_step["run"])

        preflight_steps = steps(data, "preflight")
        preflight_resolve = next(step for step in preflight_steps if step.get("name") == "Resolve pull request")
        self.assertIn(".github/scripts/resolve_pr_event.py", preflight_resolve["run"])
        self.assertIn("--github-output \"$GITHUB_OUTPUT\"", preflight_resolve["run"])
        self.assertIn("reviewable", data["jobs"]["preflight"]["outputs"])

        description_step = next(step for step in review_steps if step.get("name") == "Snapshot PR description")
        spec_context_step = next(step for step in review_steps if step.get("name") == "Snapshot spec context")
        post_step = next(step for step in review_steps if step.get("name") == "Post PR review")
        self.assertEqual(description_step["env"]["PR_EVENT_PATH"], "${{ steps.pr.outputs.event_path }}")
        self.assertIn("--output pr-worktree/pr_description.txt", description_step["run"])
        self.assertEqual(spec_context_step["env"]["PR_EVENT_PATH"], "${{ steps.pr.outputs.event_path }}")
        self.assertIn("--output pr-worktree/spec_context.md", spec_context_step["run"])
        self.assertEqual(post_step["env"]["PR_EVENT_PATH"], "${{ steps.pr.outputs.event_path }}")
        self.assertIn("--review pr-worktree/review.json", post_step["run"])
        self.assertIn("--diff pr-worktree/pr_diff.txt", post_step["run"])

        diff_step = next(step for step in review_steps if step.get("name") == "Snapshot PR diff")
        self.assertEqual(diff_step["working-directory"], "pr-worktree")
        self.assertIn("git remote add base", diff_step["run"])
        self.assertIn("../.github/scripts/build_pr_diff.py", diff_step["run"])
        self.assertIn("--output pr_diff.txt", diff_step["run"])

        select_step = next(step for step in review_steps if step.get("name") == "Select review skill")
        self.assertIn("--diff pr-worktree/pr_diff.txt", select_step["run"])

        prepare_step = next(step for step in review_steps if step.get("name") == "Prepare review workspace")
        self.assertIn("rm -rf pr-worktree/.agents/skills", prepare_step["run"])
        self.assertIn("cp -R .agents/skills pr-worktree/.agents/skills", prepare_step["run"])

        ai_step = next(step for step in review_steps if step.get("name") == "Run AI review")
        self.assertIn("First change directory to pr-worktree", ai_step["with"]["prompt"])
        self.assertIn("Write review.json in pr-worktree", ai_step["with"]["prompt"])

        validate_step = next(step for step in review_steps if step.get("name") == "Validate review output")
        self.assertIn("pr-worktree/pr_diff.txt pr-worktree/review.json", validate_step["run"])

    def test_create_spec_workflow_does_not_dispatch_review_after_pr_creation(self) -> None:
        data = workflow(".github/workflows/create-spec-from-issue.yml")
        self.assertNotIn("actions", data["permissions"])

        create_steps = steps(data, "create-spec")
        create_pr = next(step for step in create_steps if step.get("name") == "Create or update spec pull request")
        step_names = [step.get("name") for step in create_steps]

        self.assertIn(".github/scripts/finalize_spec_pr.py", create_pr["run"])
        self.assertNotIn("--github-output", create_pr["run"])
        self.assertNotIn("id", create_pr)
        self.assertNotIn("Dispatch AI PR review", step_names)

    def test_create_implementation_workflow_does_not_dispatch_review_after_pr_creation(self) -> None:
        data = workflow(".github/workflows/create-implementation-from-issue.yml")
        self.assertNotIn("actions", data["permissions"])

        create_steps = steps(data, "create-implementation")
        commit = next(step for step in create_steps if step.get("name") == "Commit and push implementation branch")
        create_pr = next(step for step in create_steps if step.get("name") == "Create or update implementation pull request")
        step_names = [step.get("name") for step in create_steps]

        self.assertEqual(commit["env"]["WORKFLOW_UPDATE_TOKEN"], "${{ secrets.WORKFLOW_UPDATE_TOKEN }}")
        self.assertEqual(create_pr["id"], "pr")
        self.assertIn("--github-output \"$GITHUB_OUTPUT\"", create_pr["run"])
        self.assertNotIn("Dispatch AI PR review", step_names)


if __name__ == "__main__":
    unittest.main()
