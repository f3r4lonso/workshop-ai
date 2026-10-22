"""Private-note, fixed launch and HTTP boundary checks; no real desktop applications run."""
import http.client
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'server'))
import desktop_actions as desktop
import resource_interaction as documents
import server
import workshop_data
from workshop_ai.scan import forbidden_reason


class DesktopActionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        (self.root / 'infra').mkdir()
        self.snapshot = SimpleNamespace(workshop_root=str(self.root), by_id={})
        self.note = self.root / desktop.NOTE_PATH
        self.find = lambda command, root: str(self.root.parent / 'git.exe')

    def test_first_creation_and_reopen_never_truncate(self):
        with patch.object(desktop, '_ignored'):
            desktop.ensure_note(self.snapshot, self.find)
            self.assertEqual(self.note.read_bytes(), b'')
            self.note.write_bytes(b'Owner ideas')
            desktop.ensure_note(self.snapshot, self.find)
            self.assertEqual(self.note.read_bytes(), b'Owner ideas')

    def test_failed_ignore_check_prevents_creation(self):
        with patch.object(desktop.subprocess, 'run', return_value=SimpleNamespace(returncode=1)):
            with self.assertRaises(documents.ResourceError):
                desktop.ensure_note(self.snapshot, self.find)
        self.assertFalse(self.note.exists())

    def test_tracked_note_refused_even_when_ignored(self):
        with patch.object(desktop.subprocess, 'run', return_value=SimpleNamespace(returncode=0)):
            with self.assertRaises(documents.ResourceError):
                desktop.ensure_note(self.snapshot, self.find)
        self.assertFalse(self.note.exists())

    def test_note_excluded_from_catalogue_context_and_generic_access(self):
        self.note.parent.mkdir(parents=True)
        self.note.write_text('Owner ideas', encoding='utf-8')
        self.assertTrue(workshop_data.is_excluded_path(str(self.note)))
        for path in ('infra/docs/notes/my-notes.txt', 'docs/notes/MY-NOTES.TXT'):
            self.assertIsNotNone(forbidden_reason(path))
        for action in ('document', 'read', 'save', 'versions'):
            result = documents.handle(action, self.snapshot,
                                      {'path': desktop.NOTE_PATH, 'text': 'Draft'}, self.find)
            self.assertFalse(result['ok'], action)

    def test_note_external_edit_conflicts_preserving_both_texts(self):
        with patch.object(desktop, '_ignored'):
            loaded = desktop.handle('notes-document', self.snapshot, {}, self.find)
            self.assertTrue(loaded['ok'], loaded)
            self.note.write_text('External', encoding='utf-8')
            result = desktop.handle('notes-save', self.snapshot,
                                    {'base_sha256': loaded['version'], 'text': 'Draft'}, self.find)
            self.assertEqual(result['code'], 'conflict')
            self.assertEqual(result['current_text'], 'External')
            self.assertEqual(result['submitted_text'], 'Draft')
            self.assertEqual(self.note.read_text(), 'External')

    def test_empty_note_save_is_valid(self):
        with patch.object(desktop, '_ignored'):
            loaded = desktop.handle('notes-document', self.snapshot, {}, self.find)
            result = desktop.handle('notes-save', self.snapshot,
                                    {'base_sha256': loaded['version'], 'text': ''}, self.find)
            self.assertTrue(result['ok'], result)

    def test_windows_text_encoding_and_line_endings_survive_save_restore(self):
        path = self.root / 'infra/docs/windows.md'
        path.parent.mkdir(parents=True)
        original = b'\xef\xbb\xbf# Original\r\nBody\r\n'
        path.write_bytes(original)
        body = {'path': 'infra/docs/windows.md'}
        loaded = documents.document(self.snapshot, body)
        saved = documents.save(self.snapshot, dict(body, text='# Draft\nBody\n',
                                                  base_sha256=loaded['version']))
        self.assertEqual(path.read_bytes(), b'\xef\xbb\xbf# Draft\r\nBody\r\n')
        prior = documents.versions(self.snapshot, body)['versions'][0]['id']
        restored = documents.restore(self.snapshot, dict(body, version_id=prior,
                                                         base_sha256=saved['version']))
        self.assertTrue(restored['ok'])
        self.assertEqual(path.read_bytes(), original)

    def test_client_paths_never_launch(self):
        with patch.object(desktop, '_launch') as launch:
            for action in ('notes-open', 'open-workshop', 'notes-document'):
                result = desktop.handle(action, self.snapshot, {'path': 'other.txt'}, self.find)
                self.assertFalse(result['ok'])
            launch.assert_not_called()

    def test_open_actions_use_only_configured_targets(self):
        with patch.object(desktop, '_ignored'), patch.object(desktop, '_launch') as launch:
            result = desktop.handle('notes-open', self.snapshot, {}, self.find)
            self.assertTrue(result['ok'])
            self.assertIn('solicitado', result['message'])
            self.assertEqual(launch.call_args.args[1:], ('notepad', self.note))
            result = desktop.handle('open-workshop', self.snapshot, {}, self.find)
            self.assertTrue(result['ok'])
            self.assertEqual(launch.call_args.args[1:], ('explorer', self.root))

    @unittest.skipUnless(os.name == 'nt', 'Windows desktop command')
    def test_notepad_uses_trusted_executable_and_argument_array(self):
        # An isolated fake Windows tree is only inspected; Popen is mocked.
        with tempfile.TemporaryDirectory() as folder:
            windows = Path(folder)
            (windows / 'System32').mkdir()
            exe = windows / 'System32/notepad.exe'
            exe.write_bytes(b'')
            with patch.dict(os.environ, {'SystemRoot': str(windows)}), patch.object(desktop.subprocess, 'Popen') as launch:
                desktop._launch(self.snapshot, 'notepad', self.note)
            self.assertEqual(launch.call_args.args[0], [str(exe), str(self.note)])
            self.assertFalse(launch.call_args.kwargs['shell'])


class V2RouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        (cls.root / 'infra/docs').mkdir(parents=True)
        cls.document = cls.root / 'infra/docs/example.md'
        cls.document.write_text('Original', encoding='utf-8')
        cls.state = server.AppState(str(cls.root / 'infra'), str(cls.root / 'dist'), quiet=True)
        cls.httpd = server.create_server(cls.state, 0, 0)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.temp.cleanup()

    def post(self, action, body=None, *, token=True, origin=True):
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['X-Workshop-Token'] = self.state.token
        if origin:
            headers['Origin'] = f'http://127.0.0.1:{self.state.port}' if origin is True else origin
        conn = http.client.HTTPConnection('127.0.0.1', self.state.port, timeout=10)
        self.addCleanup(conn.close)
        # Forbidden requests are rejected before reading their body. Avoid unread bytes
        # that Windows can turn into a TCP reset while the server closes that socket.
        data = json.dumps(body or {}) if token and origin is True else None
        conn.request('POST', '/api/interaction/' + action, data, headers)
        response = conn.getresponse()
        return response.status, json.loads(response.read())

    def test_all_private_actions_require_token_and_exact_origin(self):
        for action in ('versions', 'version', 'restore', 'create', 'templates', 'notes-open',
                       'notes-document', 'notes-save', 'notes-versions', 'notes-version',
                       'notes-restore', 'open-workshop'):
            with self.subTest(action=action):
                self.assertEqual(self.post(action, token=False)[0], 403)
                self.assertEqual(self.post(action, origin=False)[0], 403)
                self.assertEqual(self.post(action, origin='https://foreign.example')[0], 403)

    def test_conflict_http_status_and_texts(self):
        status, result = self.post('save', {'path': 'infra/docs/example.md',
                                          'base_sha256': 'stale', 'text': 'Draft'})
        self.assertEqual(status, 409)
        self.assertEqual(result['current_text'], 'Original')
        self.assertEqual(result['submitted_text'], 'Draft')

    def test_version_texts_have_no_get_route(self):
        conn = http.client.HTTPConnection('127.0.0.1', self.state.port, timeout=10)
        self.addCleanup(conn.close)
        conn.request('GET', '/api/interaction/versions')
        response = conn.getresponse()
        response.read()
        self.assertEqual(response.status, 404)


if __name__ == '__main__':
    unittest.main()
