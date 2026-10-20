"""Engine registry (v2 V1) and the `workshop` plugin check that replaced `--add-dir`."""

import copy
import json
import os
import sys
import time
import unittest
from unittest import mock

from workshop_ai import clients, engines, formats, procutil

from helpers import ProjectCase

OK = 0
PLUGIN_ENABLED = """Installed plugins:

  \u276f workshop@workshop-local
    Version: 0.1.0
    Read from: C:\\somewhere\\infra
    Scope: user
    Status: \u2714 enabled
"""


def registry_data():
    with open(engines.REGISTRY_PATH, encoding="utf-8") as handle:
        return json.load(handle)


class RegistryTests(unittest.TestCase):
    def test_registry_lists_the_ten_engines_of_engines_md(self):
        ids = [engine["id"] for engine in engines.load()]
        self.assertEqual(ids, ["claude", "codex", "gemini", "copilot", "dsh", "ollama", "suno",
                               "claude-ai-projects", "claude-desktop", "ableton-mcp"])

    def test_levels_match_engines_md(self):
        levels = {engine["id"]: engine["level"] for engine in engines.load()}
        self.assertEqual(levels["claude"], 2)
        for eid in ("codex", "gemini", "copilot"):
            self.assertEqual(levels[eid], 1)
        for eid in ("dsh", "ollama", "suno", "claude-ai-projects", "claude-desktop", "ableton-mcp"):
            self.assertEqual(levels[eid], 0)

    def test_console_engines_are_the_four_fixed_clients(self):
        consoles = [engine["id"] for engine in engines.load() if engine["console"]]
        self.assertEqual(consoles, ["claude", "codex", "gemini", "copilot"])

    def test_wai_clients_come_from_the_registry(self):
        self.assertEqual(engines.wai_clients(), ("claude", "codex"))
        self.assertEqual(formats.CLIENTS, ("claude", "codex"))

    def test_every_engine_has_spanish_texts(self):
        for engine in engines.load():
            self.assertTrue(engine["good_for"].strip(), engine["id"])
            self.assertTrue(engine["next_step"].strip(), engine["id"])

    def test_validation_rejects_bad_entries(self):
        cases = [
            lambda d: d["engines"].append(copy.deepcopy(d["engines"][0])),            # repeated id
            lambda d: d["engines"][0].update(level=5),                                 # level out of range
            lambda d: d["engines"][1].update(level=3),                                 # level above target
            lambda d: d["engines"][0].update(command="claude --yolo"),                 # not a bare program
            lambda d: d["engines"][0].update(command="..\\claude"),                    # path, not a program
            lambda d: d["engines"][6].update(console=True),                            # console without command
            lambda d: d["engines"][4].update(console=True),                            # console at level 0
            lambda d: d["engines"][0].update(url="http://example.com"),                # not https
            lambda d: d["engines"][0].pop("good_for"),                                 # missing key
            lambda d: d.update(schema="other"),
            lambda d: d["engines"][2].update(wai_client=True),                         # gemini: no wai code
            lambda d: d["engines"][0].update(level=True),                              # bool is not a level
            lambda d: d["engines"][0].update(console="yes"),                           # not true/false
            lambda d: d["engines"][0].update(guide=7),                                 # not text
            lambda d: d["engines"][0].update(command="cláude"),             # non-ASCII program
        ]
        for change in cases:
            data = registry_data()
            change(data)
            with self.assertRaises(engines.RegistryError):
                engines.validate(data)


class PluginStatusTests(unittest.TestCase):
    def check(self, stdout, returncode=0):
        with mock.patch("workshop_ai.clients.procutil.run_bounded", return_value=(returncode, stdout)) as run:
            status = clients.plugin_status("claude.exe")
        argv = run.call_args.args[0]
        self.assertEqual(argv, ["claude.exe", "plugin", "list"])
        return status

    def test_enabled(self):
        self.assertEqual(self.check(PLUGIN_ENABLED), "enabled")

    def test_disabled(self):
        self.assertEqual(self.check(PLUGIN_ENABLED.replace("\u2714 enabled", "\u2718 disabled")), "missing")

    def test_absent(self):
        self.assertEqual(self.check("Installed plugins:\n\n  \u276f other@market\n    Status: \u2714 enabled\n"),
                         "missing")

    def test_other_plugin_after_workshop_does_not_leak_its_status(self):
        text = ("  \u276f workshop@workshop-local\n    Status: \u2718 disabled\n"
                "  \u276f other@market\n    Status: \u2714 enabled\n")
        self.assertEqual(self.check(text), "missing")

    def test_failure_is_unknown(self):
        self.assertEqual(self.check("", returncode=1), "unknown")
        with mock.patch("workshop_ai.clients.procutil.run_bounded", return_value=None):
            self.assertEqual(clients.plugin_status("claude.exe"), "unknown")

    def test_other_marker_and_second_scope(self):
        text = ("  • workshop@workshop-local\n    Status: ✘ disabled\n"
                "  • workshop@workshop-local\n    Status: ✔ enabled\n")
        self.assertEqual(self.check(text), "enabled")


class BoundedRunTests(unittest.TestCase):
    def test_returns_output(self):
        self.assertEqual(procutil.run_bounded([sys.executable, "-c", "print('1.2.3')"], timeout=20)[1].strip(), "1.2.3")

    def test_timeout_ends_the_process_tree_quickly(self):
        child = "import subprocess,sys,time; subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']); time.sleep(60)"
        started = time.monotonic()
        self.assertIsNone(procutil.run_bounded([sys.executable, "-c", child], timeout=1))
        self.assertLess(time.monotonic() - started, 15)


class TrustedPathTests(unittest.TestCase):
    def test_trusted_path_rules(self):
        base = os.path.abspath("trusted-path-test")
        bin_dir, project = os.path.join(base, "bin"), os.path.join(base, "project")
        with mock.patch.dict(os.environ, {"PATH": os.pathsep.join([bin_dir, "relative"])}):
            self.assertTrue(clients._from_trusted_path(os.path.join(bin_dir, "claude.exe"), [project]))
            self.assertFalse(clients._from_trusted_path(os.path.join(project, "claude.cmd"), [project]))
            self.assertFalse(clients._from_trusted_path(os.path.join(base, "other", "claude.exe"), [project]))
            self.assertFalse(clients._from_trusted_path(os.path.join(bin_dir, "claude.exe"), [base]))


class StartWithoutPluginTests(ProjectCase):
    def new_task(self):
        self.assertEqual(self.run_cli("init")[0], OK)
        self.assertEqual(self.run_cli("task", "new", "t1", "--client", "claude", "--no-edit")[0], OK)
        self.fill_task("t1")

    def test_missing_plugin_warns_and_does_not_block(self):
        self.new_task()
        self.plugin = "missing"
        with mock.patch("workshop_ai.clients.shutil.which", return_value="claude"), \
             mock.patch("workshop_ai.cli.subprocess.run") as run:
            code, out, _ = self.run_cli("start", "t1", answers=["y"])
        self.assertEqual(code, OK)
        self.assertIn("plugin is not installed or not enabled", out)
        run.assert_called_once()
        self.assertNotIn("--add-dir", run.call_args.args[0])

    def test_enabled_plugin_shows_no_warning(self):
        self.new_task()
        with mock.patch("workshop_ai.clients.shutil.which", return_value="claude"), \
             mock.patch("workshop_ai.cli.subprocess.run"):
            _, out, _ = self.run_cli("start", "t1", answers=["y"])
        self.assertNotIn("plugin", out)

    def test_untrusted_claude_is_not_run_before_approval(self):
        self.new_task()
        self.trusted_claude = False
        with mock.patch("workshop_ai.clients.shutil.which", return_value="claude"),              mock.patch("workshop_ai.clients.plugin_status") as status,              mock.patch("workshop_ai.cli.subprocess.run"):
            _, out, _ = self.run_cli("start", "t1", answers=["n"])
        status.assert_not_called()
        self.assertIn("plugin check was skipped", out)

    def test_handoff_steps_for_claude_have_no_add_dir(self):
        steps = "\n".join(clients.handoff_steps("claude", self.infra, self.project, "t1-1"))
        self.assertNotIn("--add-dir", steps)
        self.assertIn("workshop plugin", steps)


if __name__ == "__main__":
    unittest.main()
