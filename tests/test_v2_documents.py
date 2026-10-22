"""V2 recovery guarantees and document-scoped private history."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'server'))
import resource_interaction as resources
import document_versions


class V2DocumentsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'infra/docs/example.md'
        self.path.parent.mkdir(parents=True)
        self.path.write_bytes(b'original')
        self.snapshot = SimpleNamespace(workshop_root=str(self.root), by_id={})
        self.body = dict(path='infra/docs/example.md', base_sha256=resources.version(b'original'), text='new')

    def test_restore_itself_creates_recovery_version(self):
        saved = resources.save(self.snapshot, self.body)
        listed = resources.versions(self.snapshot, self.body)['versions']
        self.assertEqual(len(listed), 1)
        self.assertEqual(resources.read_version(self.snapshot, dict(self.body, version_id=listed[0]['id']))['text'], 'original')
        restored = resources.restore(self.snapshot, dict(self.body, base_sha256=saved['base_sha256'], version_id=listed[0]['id']))
        self.assertTrue(restored['ok'])
        self.assertEqual(self.path.read_text(), 'original')
        self.assertEqual(len(resources.versions(self.snapshot, self.body)['versions']), 2)

    def test_backup_failure_blocks_save(self):
        with patch.object(document_versions, 'backup', side_effect=OSError('blocked')):
            with self.assertRaises(OSError):
                resources.save(self.snapshot, self.body)
        self.assertEqual(self.path.read_bytes(), b'original')

    def test_replace_failure_leaves_recovery_bytes(self):
        with patch.object(resources.os, 'replace', side_effect=OSError('blocked')):
            with self.assertRaises(OSError):
                resources.save(self.snapshot, self.body)
        self.assertEqual(self.path.read_bytes(), b'original')
        self.assertEqual(len(resources.versions(self.snapshot, self.body)['versions']), 1)

    def test_concurrent_save_conflict_has_both_texts(self):
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda text: resources.save(self.snapshot, dict(self.body, text=text)), ['one', 'two']))
        self.assertEqual(sum(result['ok'] for result in results), 1)
        conflict = next(result for result in results if not result['ok'])
        self.assertNotEqual(conflict['submitted_text'], conflict['current_text'])
        self.assertEqual(conflict['current_sha256'], resources.version(self.path.read_bytes()))

    def test_version_is_scoped_to_document(self):
        resources.save(self.snapshot, self.body)
        selected = resources.versions(self.snapshot, self.body)['versions'][0]['id']
        other = self.root / 'infra/docs/other.md'
        other.write_text('other')
        with self.assertRaises(ValueError):
            resources.read_version(self.snapshot, dict(path='infra/docs/other.md', version_id=selected))
        for invalid in ['../outside', 'C:/file', selected + '/extra']:
            with self.assertRaises(ValueError):
                resources.read_version(self.snapshot, dict(self.body, version_id=invalid))

    def test_linked_private_store_is_rejected(self):
        target = self.root / 'elsewhere'
        target.mkdir()
        try:
            (self.root / '.workshop-ai').symlink_to(target, target_is_directory=True)
        except OSError:
            self.skipTest('Symlink creation unavailable')
        with self.assertRaises(ValueError):
            resources.save(self.snapshot, self.body)
        self.assertEqual(self.path.read_bytes(), b'original')

    def test_allowlist_and_note_internal_override(self):
        for relative in ['INDEX.md', 'WORKSHOP-CONTEXT.md', 'projects/music/track/notes.md']:
            self.assertTrue(resources.eligible(Path(relative)))
        self.assertFalse(resources.eligible(Path('projects/other/notes.md')))
        note = self.root / 'infra/docs/notes/my-notes.txt'
        note.parent.mkdir()
        note.write_text('private')
        with self.assertRaises(resources.ResourceError):
            resources.document(self.snapshot, dict(path='infra/docs/notes/my-notes.txt'))
        loaded = resources.document(self.snapshot, dict(path='infra/docs/notes/my-notes.txt'), allow_private_note=True)
        self.assertEqual(loaded['text'], 'private')

    def test_create_fixed_template_collision_and_naming(self):
        template = self.root / 'infra/docs/manuals/templates/document.md'
        template.parent.mkdir(parents=True)
        template.write_text('# New document')
        body = dict(template_id='document', path='infra/docs/new-document.md')
        self.assertTrue(resources.create(self.snapshot, body)['ok'])
        with self.assertRaises(resources.ResourceError):
            resources.create(self.snapshot, body)
        for relative in ['infra/docs/Bad Name.md', 'infra/docs/../outside.md', 'infra/docs/name.md:evil']:
            with self.assertRaises(resources.ResourceError):
                resources.create(self.snapshot, dict(body, path=relative))

    def test_create_draft_uses_fixed_destination_and_writes_reviewed_text(self):
        options = resources.templates(self.snapshot)
        self.assertEqual([item['id'] for item in options['destinations']], ['workshop-docs'])
        result = resources.create(self.snapshot, {
            'destination': 'workshop-docs', 'name': 'edited-before-save', 'text': '# Draft\n\nReady.',
        })
        self.assertEqual(result['path'], 'infra/docs/edited-before-save.md')
        self.assertEqual((self.root / result['path']).read_text(encoding='utf-8'), '# Draft\n\nReady.')
        with self.assertRaises(resources.ResourceError):
            resources.create(self.snapshot, {
                'destination': 'workshop-docs', 'name': 'edited-before-save', 'text': 'replacement',
            })

    def test_create_draft_rejects_unlisted_paths_and_invalid_names_or_content(self):
        invalid = [
            {'destination': 'C:/outside', 'name': 'note', 'text': 'x'},
            {'destination': 'workshop-docs', 'name': '../outside', 'text': 'x'},
            {'destination': 'workshop-docs', 'name': 'Bad Name', 'text': 'x'},
            {'destination': 'workshop-docs', 'name': 'note', 'text': 'x\x00y'},
            {'destination': 'workshop-docs', 'name': 'note', 'text': 'x' * (resources.MAX_TEXT_BYTES + 1)},
        ]
        for body in invalid:
            with self.subTest(body={key: value if key != 'text' else '<content>' for key, value in body.items()}):
                with self.assertRaises(resources.ResourceError):
                    resources.create(self.snapshot, body)
        self.assertFalse((self.root / 'outside.md').exists())

    def test_create_draft_publish_failure_leaves_no_final_or_temporary_file(self):
        with patch.object(resources.os, 'link', side_effect=OSError('blocked')):
            with self.assertRaises(OSError):
                resources.create(self.snapshot, {
                    'destination': 'workshop-docs', 'name': 'publish-failure', 'text': '# Draft',
                })
        self.assertFalse((self.root / 'infra/docs/publish-failure.md').exists())
        self.assertEqual(list((self.root / 'infra/docs').glob('.wai-create-*.tmp')), [])

    def test_header_updates_preserve_unknown_and_require_tool_review(self):
        parser = self.root / 'infra/scripts/resource_headers.py'
        parser.parent.mkdir(parents=True)
        shutil.copyfile(Path(__file__).resolve().parents[3] / 'infra/scripts/resource_headers.py', parser)
        path = self.root / 'infra/agents/quality/example.md'
        path.parent.mkdir(parents=True)
        old = '---\nname: example\ndescription: Example\ntools: Read\nmodel: inherit\ncustom: keep-this-exactly\n---\nBody'
        path.write_bytes(old.encode())
        body = dict(path='infra/agents/quality/example.md', text=old, base_sha256=resources.version(old.encode()),
                    header_fields={'tools': 'Read, Grep'})
        with self.assertRaises(resources.ResourceError):
            resources.save(self.snapshot, body)
        with patch.object(resources, '_maintenance', return_value=[]):
            saved = resources.save(self.snapshot, dict(body, review_tools_model=True))
        self.assertTrue(saved['ok'])
        self.assertIn('custom: keep-this-exactly\n', path.read_text())
        changed = dict(body, text=saved['text'], base_sha256=saved['base_sha256'], header_fields={'tools': 'Read, Agent'}, review_tools_model=True)
        with self.assertRaises(resources.ResourceError):
            resources.save(self.snapshot, changed)
        changed = dict(body, text=saved['text'].replace('keep-this-exactly', 'changed'), base_sha256=saved['base_sha256'], header_fields={})
        with self.assertRaises(resources.ResourceError):
            resources.save(self.snapshot, changed)

    def test_retention_keeps_last_fifty_or_recent(self):
        folder = document_versions._folder(self.root, Path(self.body['path']), create=True)
        for index in range(55):
            (folder / (f'20200101000000{index:06d}-' + 'a' * 32 + '.bak')).write_bytes(b'old')
        recent_id = document_versions.backup(self.root, Path(self.body['path']), b'recent')
        document_versions.prune(self.root, Path(self.body['path']))
        retained = document_versions.list_versions(self.root, Path(self.body['path']))
        self.assertEqual(len(retained), 50)
        self.assertIn(recent_id, [item['id'] for item in retained])
        for _ in range(55):
            document_versions.backup(self.root, Path(self.body['path']), b'recent')
        document_versions.prune(self.root, Path(self.body['path']))
        self.assertEqual(len(document_versions.list_versions(self.root, Path(self.body['path']))), 56)

    def test_advanced_header_rejects_escaped_agent_tool(self):
        parser = self.root / 'infra/scripts/resource_headers.py'
        parser.parent.mkdir(parents=True)
        shutil.copyfile(Path(__file__).resolve().parents[3] / 'infra/scripts/resource_headers.py', parser)
        path = self.root / 'infra/agents/quality/example.md'
        path.parent.mkdir(parents=True)
        old = '---\nname: example\ndescription: Example\ntools: Read\nmodel: inherit\n---\nBody'
        path.write_bytes(old.encode())
        # A reviewed advanced-mode change must still reject the decoded Agent tool.
        for encoded in ('"Read, \\u0041gent"', '"Read, A\\u0067ent"'):
            changed = old.replace('tools: Read', 'tools: ' + encoded)
            body = dict(path='infra/agents/quality/example.md', text=changed,
                        base_sha256=resources.version(old.encode()), review_tools_model=True)
            with self.subTest(encoded=encoded), patch.object(resources, '_maintenance') as maintenance:
                with self.assertRaisesRegex(resources.ResourceError, 'Agent'):
                    resources.save(self.snapshot, body)
                maintenance.assert_not_called()
                self.assertEqual(path.read_bytes(), old.encode())
                self.assertFalse((self.root / '.workshop-ai/versions').exists())


if __name__ == '__main__':
    unittest.main()
