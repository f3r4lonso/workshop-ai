import sys
import unittest
from unittest import mock

from workshop_ai import formats
from workshop_ai.errors import ENVIRONMENT, OK, REFUSED, VALIDATION

from helpers import FAKE_AWS, ProjectCase


class CliTests(ProjectCase):
    def new_task(self, task_id="t1", verify=None):
        self.assertEqual(self.run_cli("init")[0], OK)
        self.assertEqual(self.run_cli("task", "new", task_id, "--client", "claude", "--no-edit")[0], OK)
        self.fill_task(task_id, verify)

    def test_journey_init_task_context_checkpoint_status(self):
        self.new_task(verify=f'"{sys.executable}" -c "print(1)"')
        self.write("src/a.py", "x = 1\n")
        code, out, _ = self.run_cli("context", "add", "t1", "src/a.py")
        self.assertEqual(code, OK)
        self.assertIn("- src/a.py", out)

        code, out, err = self.run_cli("checkpoint", "t1", answers=["y", "y"])
        self.assertEqual(code, OK, err)
        self.assertIn("verify pass", out)
        doc = formats.parse(self.task_path("t1").read_text())
        self.assertEqual(doc.header["revision"], "1")
        self.assertIn("- rev 1,", doc.text("History"))
        state = (self.project / ".workshop-ai" / "project-state.md").read_text()
        self.assertIn("- t1: rev 1, draft", state)

        code, out, _ = self.run_cli("status")
        self.assertIn("t1", out)
        self.assertIn("next: Write the code.", out)

    def test_start_refuses_incomplete_contract(self):
        self.run_cli("init")
        self.run_cli("task", "new", "t1", "--client", "claude", "--no-edit")
        code, _, err = self.run_cli("start", "t1")
        self.assertEqual(code, VALIDATION)
        self.assertIn('"Objective" is empty', err)

    def test_start_declined_launches_nothing(self):
        self.new_task()
        with mock.patch("workshop_ai.clients.shutil.which", return_value="claude"), \
             mock.patch("workshop_ai.cli.subprocess.run") as run:
            code, out, _ = self.run_cli("start", "t1", answers=["n"])
        self.assertEqual(code, REFUSED)
        run.assert_not_called()
        self.assertIn("Not started.", out)
        brief = (self.project / ".workshop-ai" / "tasks" / "t1" / "brief.md").read_text()
        self.assertIn("Do not run `wai` yourself", brief)

    def test_start_approved_runs_interactive_claude_with_shared_folder(self):
        self.new_task()
        with mock.patch("workshop_ai.clients.shutil.which", return_value="claude"), \
             mock.patch("workshop_ai.cli.subprocess.run") as run:
            code, _, _ = self.run_cli("resume", "t1", answers=["y"])
        self.assertEqual(code, OK)
        command = run.call_args.args[0]
        self.assertEqual(command[:2], ["claude", "--add-dir"])
        self.assertTrue(command[2].endswith("clients"))
        self.assertIn("brief.md", command[3])
        self.assertNotIn("-p", command)
        brief = (self.project / ".workshop-ai" / "tasks" / "t1" / "brief.md").read_text()
        self.assertIn("being **resumed**", brief)

    def test_no_terminal_means_no_approval(self):
        self.new_task()
        self.terminal = False
        with mock.patch("workshop_ai.clients.shutil.which", return_value="claude"), \
             mock.patch("workshop_ai.cli.subprocess.run") as run:
            code, _, err = self.run_cli("start", "t1")
        self.assertEqual(code, REFUSED)
        self.assertIn("interactive terminal", err)
        run.assert_not_called()
        code, _, _ = self.run_cli("checkpoint", "t1")
        self.assertEqual(code, REFUSED)
        self.assertNotIn("rev 1", self.task_path("t1").read_text())

    def test_missing_client_is_environment_error(self):
        self.new_task()
        with mock.patch("workshop_ai.clients.shutil.which", return_value=None):
            code, _, err = self.run_cli("start", "t1")
        self.assertEqual(code, ENVIRONMENT)
        self.assertIn("not on PATH", err)

    def test_codex_is_never_launched(self):
        self.run_cli("init")
        self.run_cli("task", "new", "t1", "--client", "codex", "--no-edit")
        self.fill_task("t1")
        with mock.patch("workshop_ai.cli.subprocess.run") as run:
            code, _, err = self.run_cli("start", "t1")
        self.assertNotEqual(code, OK)
        self.assertIn("handoff target", err)
        run.assert_not_called()

    def test_checkpoint_blocks_secret_in_task_file(self):
        self.new_task()
        path = self.task_path("t1")
        path.write_text(path.read_text().replace("Write the code.", f"Use key {FAKE_AWS}"))
        code, _, err = self.run_cli("checkpoint", "t1")
        self.assertEqual(code, VALIDATION)
        self.assertIn("aws-access-key", err)
        self.assertNotIn(FAKE_AWS, err)

    def test_checkpoint_flags_changed_verify_and_header_keys(self):
        self.new_task(verify="echo one")
        self.run_cli("checkpoint", "t1", answers=["n", "y"])
        path = self.task_path("t1")
        path.write_text(path.read_text().replace("verify: echo one", "verify: echo two"))
        code, out, _ = self.run_cli("checkpoint", "t1", answers=["n", "n"])
        self.assertEqual(code, REFUSED)
        self.assertIn("CHANGED since the last checkpoint, was: echo one", out)
        self.assertIn("header key 'verify' changed", out)

    def test_task_id_validation_and_duplicates(self):
        self.run_cli("init")
        self.assertNotEqual(self.run_cli("task", "new", "../evil", "--client", "claude", "--no-edit")[0], OK)
        self.assertEqual(self.run_cli("task", "new", "t1", "--client", "claude", "--no-edit")[0], OK)
        self.assertEqual(self.run_cli("task", "new", "t1", "--client", "claude", "--no-edit")[0], REFUSED)

    def test_resources_command(self):
        code, out, _ = self.run_cli("resources", "agents")
        self.assertEqual(code, OK)
        self.assertIn("quality/code-reviewer", out)
        self.assertIn("warning:", out)


if __name__ == "__main__":
    unittest.main()
