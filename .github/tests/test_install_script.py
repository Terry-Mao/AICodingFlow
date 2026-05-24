from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from script_imports import ROOT


INSTALL = ROOT / "install.sh"


class InstallScriptTest(unittest.TestCase):
    def setUp(self) -> None:
        if shutil.which("rsync") is None:
            self.skipTest("rsync is required for install.sh")

    def run_install(self, target: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(INSTALL), "--target", str(target), *args],
            cwd=ROOT,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def run_raw_install(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(INSTALL), *args],
            cwd=ROOT,
            check=check,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def run_piped_install(
        self,
        cwd: Path,
        *args: str,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["AICODINGFLOW_INSTALL_REPOSITORY"] = str(ROOT)
        return subprocess.run(
            ["bash", "-s", "--", *args],
            cwd=cwd,
            input=INSTALL.read_text(encoding="utf-8"),
            check=check,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def test_dry_run_does_not_write_target_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)

            result = self.run_install(target, "--dry-run")

            self.assertIn("Dry run complete", result.stdout)
            self.assertIn("Would sync", result.stdout)
            self.assertFalse((target / ".agents").exists())
            self.assertFalse((target / ".github").exists())

    def test_dry_run_reports_missing_target_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing"

            result = self.run_raw_install("--target", str(missing), "--dry-run", check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("target path is not a directory", result.stderr)

    def test_installs_regular_skill_and_github_workflow_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)

            self.run_install(target)

            self.assertTrue((target / ".agents/skills/create-issue/SKILL.md").is_file())
            self.assertTrue((target / ".agents/skills/git-branch/SKILL.md").is_file())
            self.assertFalse((target / ".agents/skills/review-pr-repo/SKILL.md").exists())
            self.assertFalse((target / ".agents/skills/review-spec-repo/SKILL.md").exists())
            self.assertFalse((target / ".agents/skills/triage-issue-repo/SKILL.md").exists())
            self.assertFalse((target / ".agents/skills/dedupe-issue-repo/SKILL.md").exists())
            self.assertTrue((target / ".github/scripts/validate_spec_output.py").is_file())
            self.assertFalse((target / ".github/tests").exists())
            self.assertTrue((target / ".github/aicodingflow-tests/test_validate_spec_output.py").is_file())
            self.assertFalse((target / ".github/aicodingflow-tests/test_install_script.py").exists())
            self.assertTrue((target / ".github/workflows/create-spec-from-issue.yml").is_file())

    def test_does_not_install_aicodingflow_repository_ci_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)

            self.run_install(target)

            self.assertFalse((target / ".github/workflows/ci.yml").exists())

    def test_overwrites_regular_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            existing = target / ".agents/skills/git-branch/SKILL.md"
            existing.parent.mkdir(parents=True)
            existing.write_text("old skill\n", encoding="utf-8")

            self.run_install(target)

            self.assertIn("name: git-branch", existing.read_text(encoding="utf-8"))

    def test_preserves_existing_repo_local_companion_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            existing = target / ".agents/skills/review-pr-repo/SKILL.md"
            existing.parent.mkdir(parents=True)
            existing.write_text("target repo guidance\n", encoding="utf-8")

            result = self.run_install(target)

            self.assertIn("Skipping repo-local companion skill", result.stdout)
            self.assertEqual(existing.read_text(encoding="utf-8"), "target repo guidance\n")

    def test_preserves_unrelated_github_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            existing = target / ".github/dependabot.yml"
            existing.parent.mkdir(parents=True)
            existing.write_text("version: 2\n", encoding="utf-8")

            self.run_install(target)

            self.assertEqual(existing.read_text(encoding="utf-8"), "version: 2\n")
            self.assertTrue((target / ".github/scripts/validate_spec_output.py").is_file())

    def test_help_documents_remote_installation(self) -> None:
        result = self.run_raw_install("--help")

        self.assertIn("curl -fsSL", result.stdout)
        self.assertIn("bash -s -- --target", result.stdout)

    def test_piped_install_clones_source_even_when_cwd_has_agents_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cwd = root / "cwd"
            target = root / "target"
            stale_skill = cwd / ".agents/skills/git-branch/SKILL.md"
            target.mkdir()
            stale_skill.parent.mkdir(parents=True)
            stale_skill.write_text("stale cwd skill\n", encoding="utf-8")

            self.run_piped_install(cwd, "--target", str(target))

            self.assertIn(
                "name: git-branch",
                (target / ".agents/skills/git-branch/SKILL.md").read_text(encoding="utf-8"),
            )
            self.assertNotEqual(
                (target / ".agents/skills/git-branch/SKILL.md").read_text(encoding="utf-8"),
                "stale cwd skill\n",
            )


if __name__ == "__main__":
    unittest.main()
