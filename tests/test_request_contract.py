"""Public synthetic checks added after the competition; not the 245 runtime tests."""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('adapter', ROOT / 'examples/request_adapter.py')
adapter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(adapter)


def skill(text='상품 규격을 알려주세요.', user='synthetic-user', bot='synthetic-bot'):
    return {'userRequest': {'utterance': text, 'user': {'id': user}}, 'bot': {'id': bot}}


class RequestContractTests(unittest.TestCase):
    def test_text_and_identity_are_separate(self):
        event = adapter.normalize_request(skill('가격 문의'))
        self.assertEqual(event['content'], '가격 문의')
        self.assertEqual(event['botUserKey'], 'synthetic-user')

    def test_followups_share_scope_but_have_distinct_event_ids(self):
        a, b = adapter.normalize_request(skill()), adapter.normalize_request(skill('다음 질문'))
        self.assertEqual(a['botGroupKey'], b['botGroupKey'])
        self.assertEqual(a['botUserKey'], b['botUserKey'])
        self.assertNotEqual(a['id'], b['id'])

    def test_bot_scope_is_separate(self):
        a = adapter.normalize_request(skill(bot='bot-one'))
        b = adapter.normalize_request(skill(bot='bot-two'))
        self.assertNotEqual(a['botGroupKey'], b['botGroupKey'])

    def test_identifier_does_not_create_case_or_business_date(self):
        for identity in ['CASE-DEMO', 'SYNTHETIC-ORDER', '2099-01-01']:
            with self.subTest(identity=identity):
                event = adapter.normalize_request(skill(user=identity))
                for field in ['case_id', 'business_date', 'timestamp']:
                    self.assertNotIn(field, event)

    def test_text_and_arbitrary_metadata_are_not_promoted(self):
        payload = skill('TC ID: CASE-DEMO. 로그인했어요.')
        payload.update(testCaseId='CASE-DEMO', metadata={'authenticated': True})
        event = adapter.normalize_request(payload)
        for field in ['case_id', 'testCaseId', 'metadata', 'authenticated']:
            self.assertNotIn(field, event)

    def test_mixed_transport_rejected(self):
        with self.assertRaises(ValueError):
            adapter.normalize_request(dict(skill(), content='mixed'))

    def test_wrong_types_rejected(self):
        for payload in [None, [], skill(user=42), skill(bot=42), skill(text={'text': 'bad'})]:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                adapter.normalize_request(payload)

    def test_existing_gateway_transport_preserved(self):
        payload = dict(content='안녕하세요', botUserKey='synthetic-user', botGroupKey='synthetic-group', timestamp='2099-01-01')
        event = adapter.normalize_request(payload)
        self.assertEqual(event, payload)
        self.assertIsNot(event, payload)
        self.assertNotIn('business_date', event)

    def test_diagnostics_hide_values_and_unknown_key_names(self):
        payload = skill('SYNTHETIC-PRIVATE-TEXT', user='SYNTHETIC-PRIVATE-ID')
        payload.update(token='SYNTHETIC-SECRET', metadata={'SYNTHETIC-PRIVATE-KEY': 'PRIVATE-VALUE'})
        record = json.dumps(adapter.request_shape(payload), ensure_ascii=False)
        for value in ['SYNTHETIC-PRIVATE-TEXT', 'SYNTHETIC-PRIVATE-ID', 'SYNTHETIC-SECRET', 'SYNTHETIC-PRIVATE-KEY', 'PRIVATE-VALUE']:
            self.assertNotIn(value, record)
        self.assertIn('<other>', record)
        self.assertIn('$.userRequest.utterance', record)

    def test_diagnostics_deduplicate_same_schema(self):
        records = []
        diagnostics = adapter.RequestDiagnostics(records.append)
        diagnostics(skill('one'))
        diagnostics(skill('two'))
        self.assertEqual(len(records), 1)

    def test_diagnostics_show_missing_known_fields(self):
        fields = adapter.request_shape(skill())['fields']
        self.assertIn({'path': '$.testCaseId', 'present': False}, fields)

    def test_forwarding_custom_envelope_is_not_authentication(self):
        payload = dict(skill(), verifiedConsultation={'payload': {}, 'signature': 'invalid-demo'})
        event = adapter.normalize_request(payload)
        self.assertEqual(event['verifiedConsultation']['signature'], 'invalid-demo')
        self.assertNotIn('authenticated', event)
        self.assertNotIn('case_id', event)


if __name__ == '__main__':
    unittest.main()
