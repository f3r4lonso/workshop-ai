import json
from pathlib import Path
import sys
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'server'))
import conversation_store


class ConversationStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.snapshot = SimpleNamespace(workshop_root=self.temp.name)
        self.messages = [
            {'role': 'user', 'content': 'Explain the approach.', 'client': 'claude', 'model': 'sonnet',
             'effort': 'medium', 'agent': ''},
            {'role': 'assistant', 'content': 'A concise answer.', 'client': 'claude', 'model': 'sonnet',
             'effort': 'medium', 'agent': ''},
        ]

    def test_save_load_and_delete_are_scoped_to_generated_id(self):
        saved = conversation_store.save_conversation(self.snapshot, {'messages': self.messages})
        self.assertTrue(saved['ok'])
        self.assertEqual(saved['retention_days'], 90)
        loaded = conversation_store.load_conversation(self.snapshot, {'id': saved['conversation']['id']})
        self.assertTrue(loaded['ok'])
        self.assertEqual(loaded['conversation']['messages'], self.messages)
        self.assertEqual(conversation_store.list_conversations(self.snapshot)['conversations'][0]['title'],
                         'Explain the approach.')
        self.assertTrue(conversation_store.delete_conversation(self.snapshot, {'id': saved['conversation']['id']})['ok'])
        self.assertFalse(conversation_store.load_conversation(self.snapshot, {'id': saved['conversation']['id']})['ok'])
        for value in ('../outside', 'C:/outside', 'x' * 32):
            self.assertFalse(conversation_store.load_conversation(self.snapshot, {'id': value})['ok'])

    def test_sensitive_text_is_not_persisted(self):
        for content in ('api_key=abcdefghijklmnop', r'C:\Users\Someone\private\file.md'):
            result = conversation_store.save_conversation(self.snapshot, {
                'messages': [{'role': 'user', 'content': content}],
            })
            self.assertFalse(result['ok'])
            self.assertTrue(result['flagged'])
        for field in ('client', 'model', 'effort', 'agent'):
            result = conversation_store.save_conversation(self.snapshot, {
                'messages': [{'role': 'user', 'content': 'safe', field: 'api_key=abcdefghijklmnop'}],
            })
            self.assertFalse(result['ok'])
        self.assertFalse((Path(self.temp.name) / '.workshop-ai').exists())

    def test_expired_conversation_is_removed_after_ninety_days(self):
        saved = conversation_store.save_conversation(self.snapshot, {'messages': self.messages})
        path = Path(self.temp.name) / '.workshop-ai' / 'conversations' / f"{saved['conversation']['id']}.json"
        record = json.loads(path.read_text(encoding='utf-8'))
        record['updated_at'] = (datetime.now(timezone.utc) - timedelta(days=91)).isoformat()
        path.write_text(json.dumps(record), encoding='utf-8')
        self.assertEqual(conversation_store.list_conversations(self.snapshot)['conversations'], [])
        self.assertFalse(path.exists())

    def test_direct_load_removes_expired_conversation(self):
        saved = conversation_store.save_conversation(self.snapshot, {'messages': self.messages})
        path = Path(self.temp.name) / '.workshop-ai' / 'conversations' / f"{saved['conversation']['id']}.json"
        record = json.loads(path.read_text(encoding='utf-8'))
        record['updated_at'] = (datetime.now(timezone.utc) - timedelta(days=91)).isoformat()
        path.write_text(json.dumps(record), encoding='utf-8')
        loaded = conversation_store.load_conversation(self.snapshot, {'id': saved['conversation']['id']})
        self.assertFalse(loaded['ok'])
        self.assertFalse(path.exists())

    def test_flagged_history_uses_generic_title(self):
        saved = conversation_store.save_conversation(self.snapshot, {'messages': self.messages})
        path = Path(self.temp.name) / '.workshop-ai' / 'conversations' / f"{saved['conversation']['id']}.json"
        record = json.loads(path.read_text(encoding='utf-8'))
        record['messages'][0]['content'] = 'api_key=abcdefghijklmnop'
        path.write_text(json.dumps(record), encoding='utf-8')
        listing = conversation_store.list_conversations(self.snapshot)
        self.assertTrue(listing['conversations'][0]['flagged'])
        self.assertEqual(listing['conversations'][0]['title'], 'Conversación marcada para revisión')
        self.assertNotIn('abcdefghijklmnop', json.dumps(listing))

    def test_conversation_count_limit_rejects_new_records_without_overwriting(self):
        from unittest.mock import patch

        first = conversation_store.save_conversation(self.snapshot, {'messages': self.messages})
        with patch.object(conversation_store, 'MAX_CONVERSATIONS', 1):
            second = conversation_store.save_conversation(self.snapshot, {'messages': self.messages})
        self.assertFalse(second['ok'])
        self.assertIn('Elimina alguna', second['message'])
        self.assertTrue(conversation_store.load_conversation(
            self.snapshot, {'id': first['conversation']['id']})['ok'])

    def test_new_record_publish_failure_leaves_no_conversation_or_temp_file(self):
        from unittest.mock import patch

        with patch.object(conversation_store.os, 'link', side_effect=OSError('blocked')):
            with self.assertRaises(OSError):
                conversation_store.save_conversation(self.snapshot, {'messages': self.messages})
        folder = Path(self.temp.name) / '.workshop-ai' / 'conversations'
        self.assertEqual(list(folder.glob('*.json')), [])
        self.assertEqual(list(folder.glob('.wai-chat-*.tmp')), [])


if __name__ == '__main__':
    unittest.main()
