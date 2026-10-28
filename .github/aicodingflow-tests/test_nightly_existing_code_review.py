from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from script_imports import ROOT, import_script

prepare = import_script(".github/scripts/prepare_nightly_review.py", "prepare_nightly_review")
publish = import_script(".github/scripts/publish_nightly_findings.py", "publish_nightly_findings")


def finding(**changes: object) -> dict[str, object]:
    value: dict[str, object] = {
        "title": "缺少边界检查导致异常",
        "path": "src/example.py",
        "line": 2,
        "trigger": "输入为空列表时进入索引分支",
        "impact": "请求抛出异常",
        "evidence": "第二行直接读取列表首项，调用方允许空列表",
        "confidence": "high",
        "security": False,
        "duplicate_issue_number": None,
    }
    value.update(changes)
    return value


class NightlyExistingCodeReviewTest(unittest.TestCase):
    def test_configured_cycle_covers_every_shard_once(self) -> None:
        start = dt.date(2026, 10, 28)
        for days in (1, 7, 30):
            with self.subTest(days=days):
                self.assertEqual(
                    {prepare.selected_shard("", start + dt.timedelta(days=offset), days) for offset in range(days)},
                    set(range(days)),
                )
                self.assertEqual(prepare.shard_for_path("src/example.py", days), prepare.shard_for_path("src/example.py", days))
                self.assertEqual(prepare.parse_cycle_days(str(days)), days)
        with self.assertRaises(SystemExit):
            prepare.selected_shard("7", start, 7)
        for value in ("0", "91", "x"):
            with self.subTest(value=value), self.assertRaises(SystemExit):
                prepare.parse_cycle_days(value)

    def test_only_code_and_operational_skills_are_targets(self) -> None:
        self.assertTrue(prepare.is_reviewable_path("src/server.ts"))
        self.assertTrue(prepare.is_reviewable_path(".github/workflows/ci.yml"))
        self.assertTrue(prepare.is_reviewable_path(".agents/skills/create-pr/SKILL.md"))
        self.assertFalse(prepare.is_reviewable_path("docs/architecture/workflow.md"))
        self.assertFalse(prepare.is_reviewable_path("tests/test_server.py"))
        self.assertFalse(prepare.is_reviewable_path(".github/aicodingflow-tests/test_script.py"))
        self.assertFalse(prepare.is_reviewable_path("vendor/lib.py"))
        self.assertFalse(prepare.is_reviewable_path("package-lock.json"))

    def test_snapshot_selects_only_matching_text_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            (root / "src/example.py").write_text("x = 1\n", encoding="utf-8")
            (root / "src/link.py").symlink_to(root / "src/example.py")
            files = prepare.snapshot_files(root, ["src/example.py", "src/link.py", "docs/readme.md"])
            self.assertEqual([item["path"] for item in files], ["src/example.py"])
            self.assertEqual(files[0]["line_count"], 1)

    def test_empty_hash_bucket_still_has_a_focus_file(self) -> None:
        project_files = [{"path": "src/example.py", "sha256": "a", "line_count": 2}]
        for shard in range(30):
            self.assertEqual(prepare.focus_files(project_files, shard, 30), project_files)

    def test_findings_require_scanned_line_high_confidence_and_known_duplicate(self) -> None:
        lines = {"src/example.py": 3, "src/shared.py": 2}
        issues = [{"number": 5, "title": "旧问题", "body": ""}]
        self.assertEqual(len(publish.validate_findings({"findings": [finding()]}, lines, issues)), 1)
        self.assertEqual(len(publish.validate_findings({"findings": [finding(path="src/shared.py")]}, lines, issues)), 1)
        for changed in (
            {"line": 4}, {"path": "src/other.py"}, {"confidence": "medium"},
            {"duplicate_issue_number": 6}, {"security": "false"},
        ):
            with self.subTest(changed=changed), self.assertRaises(SystemExit):
                publish.validate_findings({"findings": [finding(**changed)]}, lines, issues)
        with self.assertRaises(SystemExit):
            publish.validate_findings({"findings": [finding(security=True, evidence="```bad```")]}, lines, issues)

    def test_snapshot_detects_changed_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "example.py"
            source.write_text("a\nb\n", encoding="utf-8")
            shared = root / "shared.py"
            shared.write_text("c\n", encoding="utf-8")
            inventory = [
                {"path": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "line_count": len(path.read_text().splitlines())}
                for path in (source, shared)
            ]
            context = {
                "commit": "a" * 40,
                "cycle_days": 7,
                "shard": prepare.shard_for_path("example.py", 7),
                "project_files": inventory,
            }
            context["files"] = prepare.focus_files(inventory, context["shard"], 7)
            command = mock.Mock(stdout="a" * 40 + "\n")
            old = Path.cwd()
            try:
                os.chdir(root)
                with mock.patch.object(publish.subprocess, "run", return_value=command):
                    self.assertEqual(publish.validate_snapshot(context), {"example.py": 2, "shared.py": 1})
                    shared.write_text("changed\n", encoding="utf-8")
                    with self.assertRaises(SystemExit):
                        publish.validate_snapshot(context)
            finally:
                os.chdir(old)

    def test_duplicate_detection_and_rerun_suppression(self) -> None:
        item = finding()
        context = {"commit": "a" * 40, "scan_date": "2026-10-28", "shard": 3, "cycle_days": 7}
        prior = [{"number": 7, "title": "other", "body": publish.issue_body(item, context)}]
        self.assertEqual(publish.matched_issue(item, prior)["number"], 7)
        same_title_other_path = [{"number": 9, "title": item["title"], "body": "`src/other.py:2`"}]
        self.assertIsNone(publish.matched_issue(item, same_title_other_path))
        with mock.patch.object(publish, "has_triage_comment", return_value=True), mock.patch.object(publish, "run_gh_json") as create, mock.patch.object(publish, "dispatch_triage") as dispatch:
            self.assertEqual(publish.publish("owner/repo", "main", [item], prior, context), (0, 1, []))
            create.assert_not_called()
            dispatch.assert_not_called()
        with mock.patch.object(publish, "run_gh_json", return_value={"number": 8}) as create, mock.patch.object(publish, "dispatch_triage") as dispatch:
            self.assertEqual(publish.publish("owner/repo", "main", [item, item], [], context), (1, 1, []))
            create.assert_called_once()
            dispatch.assert_called_once_with("owner/repo", "main", 8)

    def test_long_issue_body_keeps_late_path_for_deduplication(self) -> None:
        item = finding()
        body = "背景说明" * 1000 + "\n`src/example.py:2`"
        self.assertGreater(len(body), 4000)
        response = [[{
            "number": 23,
            "title": item["title"],
            "body": body,
            "state": "open",
            "html_url": "https://github.com/owner/repo/issues/23",
        }]]
        with mock.patch.object(prepare, "run_gh_json", return_value=response):
            issues = prepare.issue_snapshot("owner/repo")
        self.assertEqual(issues[0]["body"], body)
        self.assertEqual(publish.matched_issue(item, issues)["number"], 23)

    def test_dispatch_failure_does_not_stop_remaining_issue_creation(self) -> None:
        first = finding()
        second = finding(title="另一处状态判断错误", path="src/second.py")
        context = {"commit": "a" * 40, "scan_date": "2026-10-28", "shard": 3, "cycle_days": 7}
        failure = publish.subprocess.CalledProcessError(1, ["gh", "workflow", "run"])
        with (
            mock.patch.object(publish, "run_gh_json", side_effect=[{"number": 10}, {"number": 11}]) as create,
            mock.patch.object(publish, "dispatch_triage", side_effect=[failure, None]) as dispatch,
        ):
            self.assertEqual(publish.publish("owner/repo", "main", [first, second], [], context), (2, 0, [10]))
            self.assertEqual(create.call_count, 2)
            self.assertEqual(dispatch.call_count, 2)

    def test_triage_lookup_failure_does_not_stop_remaining_issue_creation(self) -> None:
        first = finding()
        second = finding(title="另一处状态判断错误", path="src/second.py")
        context = {"commit": "a" * 40, "scan_date": "2026-10-28", "shard": 3, "cycle_days": 7}
        prior = [{"number": 7, "title": "other", "body": publish.issue_body(first, context)}]
        failure = publish.subprocess.CalledProcessError(1, ["gh", "api"])
        with (
            mock.patch.object(publish, "has_triage_comment", side_effect=failure),
            mock.patch.object(publish, "run_gh_json", return_value={"number": 11}) as create,
            mock.patch.object(publish, "dispatch_triage") as dispatch,
        ):
            self.assertEqual(publish.publish("owner/repo", "main", [first, second], prior, context), (1, 1, [7]))
            create.assert_called_once()
            dispatch.assert_called_once_with("owner/repo", "main", 11)

    def test_rerun_dispatches_untriaged_nightly_issue_without_recreating_it(self) -> None:
        item = finding()
        context = {"commit": "a" * 40, "scan_date": "2026-10-28", "shard": 3, "cycle_days": 7}
        prior = [{"number": 7, "title": "other", "body": publish.issue_body(item, context)}]
        with mock.patch.object(publish, "has_triage_comment", return_value=False), mock.patch.object(publish, "run_gh_json") as create, mock.patch.object(publish, "dispatch_triage") as dispatch:
            self.assertEqual(publish.publish("owner/repo", "main", [item], prior, context), (0, 1, []))
            create.assert_not_called()
            dispatch.assert_called_once_with("owner/repo", "main", 7)

    def test_user_created_duplicate_never_triggers_nightly_triage_dispatch(self) -> None:
        item = finding()
        issue = {"number": 9, "title": item["title"], "body": "`src/example.py:2`"}
        with mock.patch.object(publish, "dispatch_triage") as dispatch:
            self.assertEqual(publish.publish("owner/repo", "main", [item], [issue], {}), (0, 1, []))
            dispatch.assert_not_called()

    def test_triage_comment_lookup_and_dispatch_command(self) -> None:
        with mock.patch.object(publish, "run_gh_json", return_value=[[{"body": publish.TRIAGE_COMMENT_MARKER}]]) as fetch:
            self.assertTrue(publish.has_triage_comment("owner/repo", 7))
            fetch.assert_called_once()
        with mock.patch.object(publish.subprocess, "run") as run:
            publish.dispatch_triage("owner/repo", "main", 7)
            run.assert_called_once_with([
                "gh", "workflow", "run", "triage-issue.yml", "--repo", "owner/repo",
                "--ref", "main", "-f", "issue=7",
            ], check=True)
        with mock.patch.object(
            publish.subprocess, "run",
            side_effect=publish.subprocess.CalledProcessError(1, ["gh", "workflow", "run"]),
        ):
            with self.assertRaises(publish.subprocess.CalledProcessError):
                publish.dispatch_triage("owner/repo", "main", 7)

    def test_public_security_issue_omits_trigger_and_evidence(self) -> None:
        item = finding(security=True, trigger="private trigger", evidence="private evidence")
        body = publish.issue_body(item, {"commit": "a" * 40, "scan_date": "2026-10-28", "shard": 3, "cycle_days": 7})
        self.assertNotIn("private trigger", body)
        self.assertNotIn("private evidence", body)
        self.assertIn("src/example.py:2", body)

    def test_publication_refreshes_issues_after_agent_review(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output / "context.json").write_text(json.dumps({"commit": "a" * 40, "scan_date": "2026-10-28", "shard": 3, "cycle_days": 7, "files": [{"path": "src/example.py"}]}))
            (output / "issues.json").write_text("[]")
            (output / "findings.json").write_text(json.dumps({"findings": [finding()]}))
            current = [{"number": 9, "title": "缺少边界检查导致异常", "body": "`src/example.py:2`"}]
            with (
                mock.patch("sys.argv", ["publish_nightly_findings.py", "--repo", "owner/repo", "--default-branch", "main", "--output-dir", str(output)]),
                mock.patch.object(publish, "validate_write_surface"),
                mock.patch.object(publish, "validate_snapshot", return_value={"src/example.py": 3}),
                mock.patch.object(publish, "issue_snapshot", return_value=current) as refresh,
                mock.patch.object(publish, "run_gh_json") as create,
            ):
                publish.main()
            refresh.assert_called_once_with("owner/repo")
            create.assert_not_called()

    def test_dispatch_failures_are_reported_after_publication(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output / "context.json").write_text(json.dumps({"commit": "a" * 40, "scan_date": "2026-10-28", "shard": 3, "cycle_days": 7, "files": [{"path": "src/example.py"}]}))
            (output / "issues.json").write_text("[]")
            (output / "findings.json").write_text(json.dumps({"findings": [finding()]}))
            summary = output / "summary.md"
            with (
                mock.patch("sys.argv", ["publish_nightly_findings.py", "--repo", "owner/repo", "--default-branch", "main", "--output-dir", str(output), "--summary", str(summary)]),
                mock.patch.object(publish, "validate_write_surface"),
                mock.patch.object(publish, "validate_snapshot", return_value={"src/example.py": 3}),
                mock.patch.object(publish, "issue_snapshot", return_value=[]),
                mock.patch.object(publish, "publish", return_value=(2, 0, [10])),
            ):
                with self.assertRaises(SystemExit) as failure:
                    publish.main()
            self.assertIn("#10", str(failure.exception))
            self.assertIn("分诊调度失败，需补发：#10", summary.read_text(encoding="utf-8"))

    def test_workflow_schedules_beijing_night_and_publishes_outside_agent(self) -> None:
        workflow = (ROOT / ".github/workflows/review-existing-code.yml").read_text(encoding="utf-8")
        self.assertIn('cron: "30 18 * * *"', workflow)
        self.assertIn("NIGHTLY_REVIEW_CYCLE_DAYS", workflow)
        self.assertIn("publish_nightly_findings.py", workflow)
        self.assertIn("actions: write", workflow)
        self.assertIn("if: always()", workflow)


if __name__ == "__main__":
    unittest.main()
