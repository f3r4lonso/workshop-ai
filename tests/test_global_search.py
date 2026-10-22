from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'server'))
import conversation_store
import document_versions
import global_search


class GlobalSearchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.document = self.root / 'infra' / 'docs' / 'guide.md'
        self.document.parent.mkdir(parents=True)
        self.document.write_text('# Guía\n\nEl jardín tiene café molido.', encoding='utf-8')
        self.resource = SimpleNamespace(
            path=str(self.document), title='Guía de prueba', name='test-guide',
            section='Documentos', search_text='guide test', modified=datetime.now(timezone.utc),
        )
        self.snapshot = SimpleNamespace(workshop_root=str(self.root), by_id={'documentos:guide': self.resource})

    def test_search_finds_current_document_body_with_accent_insensitive_match(self):
        result = global_search.search(self.snapshot, {'query': 'jardin cafe'})
        self.assertTrue(result['ok'])
        self.assertEqual([entry['kind'] for entry in result['results']], ['resource'])
        self.assertEqual(result['results'][0]['item_id'], 'documentos:guide')
        self.assertIn('jardín', result['results'][0]['excerpt'])

    def test_search_finds_prior_document_version(self):
        document_versions.backup(
            self.root, 'infra/docs/guide.md',
            b'# Gu\xc3\xada antigua\n\nLa receta llevaba lim\xc3\xb3n.',
        )
        result = global_search.search(self.snapshot, {'query': 'receta limón'})
        matches = [entry for entry in result['results'] if entry['kind'] == 'version']
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]['item_id'], 'documentos:guide')
        self.assertIn('limón', matches[0]['excerpt'])

    def test_search_respects_shared_read_budget_across_versions_and_conversations(self):
        document_versions.backup(self.root, 'infra/docs/guide.md', b'El caf\xc3\xa9 anterior.')
        saved = conversation_store.save_conversation(self.snapshot, {
            'messages': [{'role': 'user', 'content': 'Recordar el café.'}],
        })
        self.assertTrue(saved['ok'], saved)
        budget = self.document.stat().st_size

        with patch.object(global_search, 'MAX_SCANNED_BYTES', budget):
            result = global_search.search(self.snapshot, {'query': 'café'})

        self.assertTrue(result['partial'])
        self.assertLessEqual(result['scanned_bytes'], budget)
        self.assertEqual([entry['kind'] for entry in result['results']], ['resource'])

    def test_search_finds_only_safe_saved_conversation_messages(self):
        saved = conversation_store.save_conversation(self.snapshot, {
            'messages': [{'role': 'user', 'content': 'Recordar filtro estacional de cultivos.'}],
        })
        self.assertTrue(saved['ok'], saved)
        result = global_search.search(self.snapshot, {'query': 'filtro estacional'})
        matches = [entry for entry in result['results'] if entry['kind'] == 'conversation']
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]['conversation_id'], saved['conversation']['id'])
        self.assertIn('filtro estacional', matches[0]['excerpt'])

    def test_search_hides_conversations_flagged_after_they_were_saved(self):
        saved = conversation_store.save_conversation(self.snapshot, {
            'messages': [{'role': 'user', 'content': 'A harmless gardening note.'}],
        })
        record_path = (self.root / '.workshop-ai' / 'conversations'
                       / f"{saved['conversation']['id']}.json")
        record = json.loads(record_path.read_text(encoding='utf-8'))
        record['messages'][0]['content'] = 'api_key=abcdefghijklmnop'
        record_path.write_text(json.dumps(record), encoding='utf-8')

        result = global_search.search(self.snapshot, {'query': 'abcdefghijklmnop'})

        self.assertFalse(any(entry['kind'] == 'conversation' for entry in result['results']))
        self.assertEqual(result['skipped'], 1)

    def test_search_rejects_empty_oversized_and_too_many_terms(self):
        for query in (' ', 'x' * (global_search.MAX_QUERY_LENGTH + 1), 'a b c d e f g h i'):
            with self.subTest(query_length=len(query)):
                result = global_search.search(self.snapshot, {'query': query})
                self.assertFalse(result['ok'])

    def test_search_does_not_return_personal_notes(self):
        notes = self.root / 'infra' / 'docs' / 'notes' / 'my-notes.txt'
        notes.parent.mkdir(parents=True)
        notes.write_text('private marker garden-cobalt', encoding='utf-8')
        self.snapshot.by_id['notes:private'] = SimpleNamespace(
            path=str(notes), title='Mis notas', name='my-notes',
            section='Documentos', search_text='private marker', modified=None,
        )
        result = global_search.search(self.snapshot, {'query': 'garden-cobalt'})
        self.assertEqual(result['results'], [])


if __name__ == '__main__':
    unittest.main()
