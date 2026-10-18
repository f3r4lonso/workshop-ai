import unittest
from pathlib import Path
from unittest import mock

from workshop_ai import fsutil
from workshop_ai.errors import ENVIRONMENT, REFUSED, WaiError
from workshop_ai.state import Project

from helpers import ProjectCase


class StateTests(ProjectCase):
    def test_init_creates_layout_and_is_idempotent(self):
        project = Project(self.project, self.infra)
        self.assertTrue(project.init())
        self.assertTrue((self.project / ".workshop-ai" / "project-state.md").is_file())
        self.assertIn("handoffs/", (self.project / ".workshop-ai" / ".gitignore").read_text())
        before = project.state_file.read_text()
        self.assertFalse(project.init())
        self.assertEqual(project.state_file.read_text(), before)

    def test_refuses_to_store_state_inside_infra(self):
        inside = self.infra / "docs"
        inside.mkdir()
        with self.assertRaises(WaiError) as ctx:
            Project(inside, self.infra).init()
        self.assertEqual(ctx.exception.code, REFUSED)
        self.assertFalse((inside / ".workshop-ai").exists())

    def test_commands_need_init(self):
        with self.assertRaises(WaiError) as ctx:
            Project(self.project, self.infra).load_task("t1")
        self.assertEqual(ctx.exception.code, ENVIRONMENT)

    def test_context_must_be_project_files(self):
        project = Project(self.project, self.infra)
        project.init()
        self.write("src/a.py", "x = 1\n")
        self.write(".env", "X=1\n")
        (self.tmp / "outside.txt").write_text("secret\n")
        self.assertEqual(project.resolve_context("src/a.py"), "src/a.py")
        self.assertEqual(project.resolve_context(str(self.project / "src" / "a.py")), "src/a.py")
        for bad, code in (("../outside.txt", REFUSED), (str(self.tmp / "outside.txt"), REFUSED),
                          ("src", 1), (".env", REFUSED), ("missing.py", 1)):
            with self.assertRaises(WaiError, msg=bad) as ctx:
                project.resolve_context(bad)
            self.assertEqual(ctx.exception.code, code, bad)

    def test_atomic_write_keeps_old_file_on_failure(self):
        path = self.project / "f.txt"
        fsutil.atomic_write(path, "old\n")
        with mock.patch("os.replace", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                fsutil.atomic_write(path, "new\n")
        self.assertEqual(path.read_text(), "old\n")
        self.assertEqual([p.name for p in self.project.iterdir()], ["f.txt"])

    def test_hand_edit_of_project_state_is_kept_and_shown(self):
        project = Project(self.project, self.infra)
        project.init()
        text = project.state_file.read_text().replace("<!-- What this project is for. -->", "Hand-written goal.")
        project.state_file.write_text(text)
        self.assertIn("+Hand-written goal.", project.diff_since_checkpoint(project.state_file))


if __name__ == "__main__":
    unittest.main()
