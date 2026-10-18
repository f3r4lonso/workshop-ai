import unittest

from workshop_ai import formats
from workshop_ai.errors import VALIDATION, WaiError

SAMPLE = """---
id: t1
client: claude
status: in-progress
created: 2026-10-20T10:02
revision: 2
---

Free text before the sections.

## Objective
Do it.

## Acceptance criteria
- [x] One.
- [ ] Two.

## My own notes
Keep me, with *formatting*.

## Next action
Next.
"""


class FormatTests(unittest.TestCase):
    def test_round_trip_keeps_free_text_and_unknown_sections(self):
        doc = formats.parse(SAMPLE)
        self.assertEqual(doc.dumps(), SAMPLE)

    def test_crlf_input_is_normalized(self):
        doc = formats.parse(SAMPLE.replace("\n", "\r\n"))
        self.assertEqual(doc.dumps(), SAMPLE)

    def test_set_section_replaces_only_that_section(self):
        doc = formats.parse(SAMPLE)
        doc.set_section("Next action", "Something else.")
        text = doc.dumps()
        self.assertIn("Something else.", text)
        self.assertIn("Keep me, with *formatting*.", text)
        self.assertIn("Free text before the sections.", text)

    def test_valid_task_has_no_problems(self):
        self.assertEqual(formats.task_problems(formats.parse(SAMPLE)), [])

    def test_missing_pieces_are_reported_plainly(self):
        doc = formats.parse("---\nid: t1\nclient: gpt\n---\n## Objective\n<!-- hint -->\n")
        problems = "\n".join(formats.task_problems(doc))
        self.assertIn('missing header key "status"', problems)
        self.assertIn("client must be one of", problems)
        self.assertIn('"Objective" is empty', problems)
        self.assertIn('missing section "Acceptance criteria"', problems)

    def test_minimal_check_ignores_next_action(self):
        doc = formats.parse("---\nclient: claude\n---\n## Objective\nX\n## Acceptance criteria\n- [ ] Y\n")
        self.assertEqual(formats.task_problems(doc, minimal=True), [])

    def test_bad_header_raises_validation_error(self):
        with self.assertRaises(WaiError) as ctx:
            formats.parse("no header\n")
        self.assertEqual(ctx.exception.code, VALIDATION)
        with self.assertRaises(WaiError):
            formats.parse("---\nid t1\n---\n")

    def test_task_id_rules(self):
        for good in ("t1", "t2-empty-csv", "a" * 64):
            formats.validate_task_id(good)
        for bad in ("", "../x", "T1", "-x", "a b", "a" * 65, "x/y"):
            with self.assertRaises(WaiError):
                formats.validate_task_id(bad)

    def test_context_paths_round_trip(self):
        doc = formats.parse(SAMPLE)
        formats.set_context_paths(doc, ["a.py", "b/c.py"])
        self.assertEqual(formats.context_paths(formats.parse(doc.dumps())), ["a.py", "b/c.py"])


if __name__ == "__main__":
    unittest.main()
