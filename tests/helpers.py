"""Shared test fixtures: a fake infra tree, a temporary project, scripted approvals."""

import contextlib
import io
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from workshop_ai import approval, cli


def make_infra(root):
    infra = Path(root) / "infra"
    (infra / "clients" / "claude-code-cli").mkdir(parents=True)
    (infra / "clients" / "claude-code-cli" / "README.md").write_text("# Client guide: Claude Code CLI\n")
    (infra / "agents" / "quality").mkdir(parents=True)
    (infra / "agents" / "quality" / "code-reviewer.md").write_text(
        "---\nname: code-reviewer\ndescription: Reviews code. Second sentence.\ntools: Read, Grep\n---\nbody\n")
    (infra / "agents" / "quality" / "broken.md").write_text("no frontmatter\n")
    (infra / "skills" / "engineering-lifecycle").mkdir(parents=True)
    (infra / "skills" / "engineering-lifecycle" / "SKILL.md").write_text(
        "---\nname: engineering-lifecycle\ndescription: Generic workflow.\n---\n")
    (infra / "tasks").mkdir()
    (infra / "tasks" / "README.md").write_text("# Tasks\n")
    (infra / "tasks" / "some-task.md").write_text("# TASK — Something\n\nStatus: active.\n", encoding="utf-8")
    (infra / "tasks" / "no-status.md").write_text("# TASK — Other\n", encoding="utf-8")
    (infra / "AGENTS.md").write_text("# rules\n")
    return infra


class ProjectCase(unittest.TestCase):
    """Temporary infra + project; run(...) calls the CLI and captures output."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="wai-test-"))
        self.infra = make_infra(self.tmp)
        self.project = self.tmp / "project"
        self.project.mkdir()
        self.answers = []
        self.terminal = True
        self.plugin = "enabled"
        self.trusted_claude = True
        patches = [
            mock.patch.object(approval, "_is_terminal", lambda: self.terminal),
            mock.patch.object(approval, "_ask", self._answer),
            mock.patch("workshop_ai.clients.plugin_status", lambda exe: self.plugin),
            mock.patch("workshop_ai.clients._from_trusted_path", lambda exe, roots: self.trusted_claude),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _answer(self, prompt):
        if not self.answers:
            raise AssertionError(f"unexpected prompt: {prompt}")
        return self.answers.pop(0)

    def run_cli(self, *argv, answers=()):
        self.answers = list(answers)
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = cli.main(list(argv) + ["--project", str(self.project), "--infra", str(self.infra)])
        return code, stdout.getvalue(), stderr.getvalue()

    def write(self, rel, text):
        path = self.project / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def task_path(self, task_id):
        return self.project / ".workshop-ai" / "tasks" / task_id / "task.md"

    def fill_task(self, task_id, verify=None):
        """Simulate the user filling the contract in the editor."""
        path = self.task_path(task_id)
        text = path.read_text(encoding="utf-8")
        text = text.replace("<!-- What must be true when this task is done? -->", "Make the thing work.")
        text = text.replace("- [ ] \n", "- [ ] The thing works.\n")
        text = text.replace("<!-- The very next step. -->", "Write the code.")
        if verify:
            text = text.replace("revision: 0\n", f"revision: 0\nverify: {verify}\n")
        path.write_text(text, encoding="utf-8")


# Synthetic secret-like strings, assembled at runtime so no secret scanner flags this source file.
FAKE_AWS = "AKIA" + "ABCDEFGHIJKLMNOP"
FAKE_ANTHROPIC = "sk-" + "ant-" + "x" * 30
FAKE_GITHUB = "ghp" + "_" + "a" * 36
FAKE_KEY_HEADER = "-----BEGIN " + "RSA PRIVATE KEY-----"
FAKE_GENERIC = "pass" + "word = " + "q" * 16
FAKE_USER_PATH = "C:" + "\\Users\\" + "someone\\file.txt"
