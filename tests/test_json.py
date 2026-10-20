import json

from workshop_ai.errors import ENVIRONMENT, OK, REFUSED, USAGE

from helpers import ProjectCase


class JsonOutputTests(ProjectCase):
    def run_json(self, *argv):
        code, out, err = self.run_cli(*argv, "--json")
        lines = out.splitlines()
        self.assertEqual(len(lines), 1, out)
        payload = json.loads(lines[0])
        self.assertEqual(payload["schema"], "wai.v1")
        return code, payload, err

    def test_init_reports_created_then_unchanged(self):
        code, payload, _ = self.run_json("init")
        self.assertEqual((code, payload["created"]), (OK, True))
        code, payload, _ = self.run_json("init")
        self.assertEqual((code, payload["created"]), (OK, False))

    def test_status_lists_tasks_with_client_status_and_file(self):
        self.run_cli("init")
        code, payload, _ = self.run_json("status")
        self.assertEqual((code, payload["tasks"]), (OK, []))

        code, payload, _ = self.run_json("task", "new", "t1", "--client", "codex", "--no-edit")
        self.assertEqual(code, OK)
        self.assertEqual(payload["task_file"], ".workshop-ai/tasks/t1/task.md")
        self.assertTrue((self.project / payload["task_file"]).is_file())

        self.fill_task("t1")
        _, payload, _ = self.run_json("status")
        self.assertEqual(payload["tasks"], [{
            "id": "t1", "client": "codex", "status": "draft", "last_checkpoint": None,
            "next_action": "Write the code.", "task_file": ".workshop-ai/tasks/t1/task.md"}])

    def test_status_reports_unreadable_task_without_failing(self):
        self.run_cli("init")
        self.write(".workshop-ai/tasks/bad/task.md", "not a task\n")
        code, payload, _ = self.run_json("status")
        self.assertEqual(code, OK)
        self.assertEqual(payload["tasks"][0]["id"], "bad")
        self.assertIn("error", payload["tasks"][0])

    def test_context_add_and_list(self):
        self.run_cli("init")
        self.run_cli("task", "new", "t1", "--client", "claude", "--no-edit")
        self.write("src/a.py", "x = 1\n")
        code, payload, _ = self.run_json("context", "add", "t1", "src/a.py")
        self.assertEqual((code, payload["context"]), (OK, ["src/a.py"]))
        _, payload, _ = self.run_json("context", "list", "t1")
        self.assertEqual(payload, {"schema": "wai.v1", "task": "t1", "context": ["src/a.py"]})

    def test_resources_lists_items_and_warnings(self):
        code, payload, _ = self.run_json("resources", "agents")
        self.assertEqual(code, OK)
        self.assertEqual([a["name"] for a in payload["agents"]["items"]], ["code-reviewer"])
        self.assertTrue(payload["agents"]["warnings"])

    def test_errors_are_json_on_stdout_with_exit_code(self):
        code, payload, err = self.run_json("status")
        self.assertEqual(code, ENVIRONMENT)
        self.assertEqual(payload["error"]["code"], ENVIRONMENT)
        self.assertIn("wai init", payload["error"]["message"])
        self.assertEqual(err, "")

        self.run_cli("init")
        self.run_cli("task", "new", "t1", "--client", "claude", "--no-edit")
        code, payload, _ = self.run_json("task", "new", "t1", "--client", "claude", "--no-edit")
        self.assertEqual((code, payload["error"]["code"]), (REFUSED, REFUSED))

    def test_non_ascii_task_text_survives_any_console_encoding(self):
        self.run_cli("init")
        self.run_cli("task", "new", "t1", "--client", "claude", "--no-edit")
        path = self.task_path("t1")
        path.write_text(path.read_text(encoding="utf-8").replace("<!-- The very next step. -->",
                                                                 "Revisar señal → ok…"), encoding="utf-8")
        code, out, _ = self.run_cli("status", "--json")
        self.assertEqual(code, OK)
        out.encode("ascii")  # the line is pure ASCII
        self.assertEqual(json.loads(out)["tasks"][0]["next_action"], "Revisar señal → ok…")

    def test_usage_error_is_json_with_usage_code(self):
        code, payload, _ = self.run_json("status", "--bogus")
        self.assertEqual((code, payload["error"]["code"]), (USAGE, USAGE))

    def test_text_output_unchanged_without_flag(self):
        self.run_cli("init")
        code, out, _ = self.run_cli("status")
        self.assertEqual(code, OK)
        self.assertIn("No tasks yet.", out)
