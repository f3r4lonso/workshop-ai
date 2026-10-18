import unittest

from workshop_ai import scan

from helpers import (FAKE_ANTHROPIC, FAKE_AWS, FAKE_GENERIC, FAKE_GITHUB, FAKE_KEY_HEADER,
                     FAKE_USER_PATH)


class ScanTests(unittest.TestCase):
    def test_each_secret_rule_blocks_without_echoing_the_value(self):
        for value, rule in ((FAKE_AWS, "aws-access-key"), (FAKE_ANTHROPIC, "anthropic-key"),
                            (FAKE_GITHUB, "github-token"), (FAKE_KEY_HEADER, "private-key"),
                            (FAKE_GENERIC, "generic-secret")):
            blocks, _ = scan.scan_text(f"line one\nx {value} y\n", "f.md")
            self.assertEqual(blocks, [f"f.md:2: {rule}"], value[:6])
            self.assertNotIn(value, " ".join(blocks))

    def test_clean_text_passes(self):
        self.assertEqual(scan.scan_text("token budget is small\npassword policy: see docs\n", "f"), ([], []))

    def test_user_paths_warn(self):
        for text in (FAKE_USER_PATH, FAKE_USER_PATH.replace("\\", "/").lower(), "/home/someone/x"):
            blocks, warnings = scan.scan_text(text, "f")
            self.assertEqual(blocks, [])
            self.assertEqual(len(warnings), 1, text)
        self.assertEqual(scan.scan_text("%USERPROFILE%\\workshop and C:\\Users\\<you>", "f")[1], [])

    def test_forbidden_names_and_folders(self):
        for rel in (".env", "config/.env.local", "auth.json", "x/id_rsa", "k.pem", "db.kdbx",
                    ".git/config", ".ssh/known_hosts", ".workshop-ai/tasks/t/task.md", "settings.local.json"):
            self.assertIsNotNone(scan.forbidden_reason(rel), rel)
        for rel in (".env.example", "src/app.py", "docs/keys.md"):
            self.assertIsNone(scan.forbidden_reason(rel), rel)


if __name__ == "__main__":
    unittest.main()
