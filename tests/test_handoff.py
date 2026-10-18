import json
import unittest
from unittest import mock

from workshop_ai.errors import OK, REFUSED, VALIDATION

from helpers import FAKE_GITHUB, FAKE_USER_PATH, ProjectCase

NO_GITLEAKS = mock.patch("workshop_ai.scan.shutil.which", return_value=None)


class HandoffTests(ProjectCase):
    def setUp(self):
        super().setUp()
        NO_GITLEAKS.start()
        self.addCleanup(NO_GITLEAKS.stop)
        self.run_cli("init")
        self.run_cli("task", "new", "t1", "--client", "claude", "--no-edit")
        self.fill_task("t1")
        path = self.task_path("t1")
        path.write_text(path.read_text().replace(
            "<!-- - D-001 (date): decision. Reason: ... -->", "- D-001 (2026-10-20): exit 0. Reason: normal case."))
        self.write("src/a.py", "x = 1\n")
        self.write("src/unrelated.py", "y = 2\n")
        self.run_cli("context", "add", "t1", "src/a.py")
        self.assertEqual(self.run_cli("checkpoint", "t1", answers=["y"])[0], OK)

    def package(self, name="t1-1"):
        return self.project / ".workshop-ai" / "handoffs" / name

    def manifest(self, name="t1-1"):
        return json.loads((self.package(name) / "manifest.json").read_text())

    def test_package_holds_only_selected_context(self):
        code, out, err = self.run_cli("handoff", "create", "t1", "--to", "codex")
        self.assertEqual(code, OK, err)
        files = sorted(f["path"] for f in self.manifest()["files"])
        self.assertEqual(files, ["context/src/a.py", "handoff.md"])
        handoff_md = (self.package() / "handoff.md").read_text()
        self.assertIn("D-001 (2026-10-20): exit 0", handoff_md)
        self.assertIn("Write the code.", handoff_md)
        self.assertEqual(self.manifest()["approval"]["status"], "pending")
        self.assertEqual(self.manifest()["scan"]["gitleaks"], "not installed")

    def test_requires_a_clean_checkpoint(self):
        path = self.task_path("t1")
        path.write_text(path.read_text() + "\nmore\n")
        code, _, err = self.run_cli("handoff", "create", "t1", "--to", "codex")
        self.assertEqual(code, VALIDATION)
        self.assertIn("not checkpointed", err)

    def test_unapproved_package_cannot_be_shown(self):
        self.run_cli("handoff", "create", "t1", "--to", "codex")
        code, _, err = self.run_cli("handoff", "show", "t1-1")
        self.assertEqual(code, REFUSED)
        self.assertIn("approval required", err)

    def test_approve_needs_manual_review_word_and_yes(self):
        self.run_cli("handoff", "create", "t1", "--to", "claude")
        self.assertEqual(self.run_cli("handoff", "approve", "t1-1", answers=["yes"])[0], REFUSED)
        self.assertEqual(self.manifest()["approval"]["status"], "pending")
        code, _, _ = self.run_cli("handoff", "approve", "t1-1", answers=["reviewed", "y"])
        self.assertEqual(code, OK)
        approval = self.manifest()["approval"]
        self.assertEqual(approval["status"], "approved")
        self.assertTrue(approval["manual_review"])
        code, out, _ = self.run_cli("handoff", "show", "t1-1")
        self.assertEqual(code, OK)
        self.assertIn("handoffs/t1-1/handoff.md", out)

    def test_no_terminal_cannot_approve(self):
        self.run_cli("handoff", "create", "t1", "--to", "codex")
        self.terminal = False
        code, _, err = self.run_cli("handoff", "approve", "t1-1")
        self.assertEqual(code, REFUSED)
        self.assertEqual(self.manifest()["approval"]["status"], "pending")

    def test_tampered_package_is_refused(self):
        self.run_cli("handoff", "create", "t1", "--to", "codex")
        (self.package() / "context" / "src" / "a.py").write_text("x = 2\n")
        (self.package() / "extra.txt").write_text("sneaked in\n")
        code, _, err = self.run_cli("handoff", "approve", "t1-1")
        self.assertEqual(code, VALIDATION)
        self.assertIn("changed after the scan", err)
        self.assertIn("extra.txt: added after the scan", err)

    def test_secret_in_context_blocks_package(self):
        self.write("src/a.py", f"TOKEN_VALUE = '{FAKE_GITHUB}'\n")
        code, out, _ = self.run_cli("handoff", "create", "t1", "--to", "codex")
        self.assertEqual(code, VALIDATION)
        self.assertIn("github-token", out)
        self.assertNotIn(FAKE_GITHUB, out)
        self.assertEqual(self.manifest()["approval"]["status"], "blocked")
        self.assertEqual(self.run_cli("handoff", "approve", "t1-1")[0], VALIDATION)

    def test_user_path_warns_and_new_package_never_overwrites(self):
        self.write("src/a.py", f"# {FAKE_USER_PATH}\n")
        self.run_cli("handoff", "create", "t1", "--to", "codex")
        self.assertTrue(self.manifest()["scan"]["warnings"])
        self.run_cli("handoff", "create", "t1", "--to", "codex")
        self.assertTrue(self.package("t1-2").is_dir())
        self.assertTrue(self.package("t1-1").is_dir())

    def test_gitleaks_finding_blocks(self):
        with mock.patch("workshop_ai.handoff.scan.run_gitleaks", return_value="fail"):
            code, _, _ = self.run_cli("handoff", "create", "t1", "--to", "codex")
        self.assertEqual(code, VALIDATION)
        self.assertEqual(self.manifest()["approval"]["status"], "blocked")


if __name__ == "__main__":
    unittest.main()
