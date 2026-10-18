import tempfile
import unittest
from pathlib import Path

from workshop_ai import resources
from workshop_ai.errors import ENVIRONMENT, WaiError

from helpers import make_infra


class ResourceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.infra = make_infra(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_lists_every_contract(self):
        listed = resources.list_resources(self.infra)
        self.assertEqual([r["id"] for r in listed["clients"][0]], ["claude-code-cli"])
        agents, agent_warnings = listed["agents"]
        self.assertEqual([(a["area"], a["name"]) for a in agents], [("quality", "code-reviewer")])
        self.assertEqual(agents[0]["description"], "Reviews code.")
        self.assertEqual(len(agent_warnings), 1)  # broken.md
        self.assertEqual([s["name"] for s in listed["skills"][0]], ["engineering-lifecycle"])
        tasks, task_warnings = listed["tasks"]
        self.assertEqual({t["file"]: t["status"] for t in tasks},
                         {"no-status.md": "unknown", "some-task.md": "active."})
        self.assertEqual(len(task_warnings), 1)

    def test_missing_infra_is_an_environment_error(self):
        with self.assertRaises(WaiError) as ctx:
            resources.list_resources(Path(self.tmp.name) / "nowhere")
        self.assertEqual(ctx.exception.code, ENVIRONMENT)


if __name__ == "__main__":
    unittest.main()
