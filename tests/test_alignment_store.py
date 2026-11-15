"""Integrity tests for the disposable prototype, not tests of German fidelity."""

import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import alignment_store as store


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.db = store.connect()
        self.packet = store.build(self.db)

    def tearDown(self):
        self.db.close()

    def rejects(self, sql, params=()):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(sql, params)

    def unit(self, id='test', analysis='grund-layout', version='grundzuege-001-v1',
             start=0, end=4, parent=None):
        return (id, analysis, version, 'word', 'test', start, end, parent)

    def insert_unit(self, **kwargs):
        self.db.execute('''INSERT INTO unit
            (id,analysis_id,version_id,kind,label,start,end,parent_id) VALUES (?,?,?,?,?,?,?,?)''',
            self.unit(**kwargs))

    def test_roundtrip_every_span_and_hash(self):
        for version in self.packet['versions']:
            row = self.db.execute('SELECT * FROM text_version WHERE id=?', (version['id'],)).fetchone()
            self.assertEqual(row['body'], version['body'])
            self.assertEqual(store.sha256(row['body'].encode()), row['body_sha256'])
            for unit in self.db.execute('SELECT * FROM unit_text WHERE version_id=?', (version['id'],)):
                self.assertEqual(unit['text'], version['body'][unit['start']:unit['end']])

    def test_unicode_code_points_not_bytes_or_graphemes(self):
        body = 'Maße a\u0308 😀'
        v = dict(self.packet['versions'][0], id='unicode', body=body,
                 body_sha256=store.sha256(body.encode()))
        store.insert(self.db, 'text_version', v)
        store.insert(self.db, 'analysis', dict(id='unicode-analysis', version_id='unicode',
                     method='synthetic test', scope='test', status='proposed', supersedes=None))
        self.insert_unit(id='umlaut', analysis='unicode-analysis', version='unicode', start=5, end=7)
        self.insert_unit(id='emoji', analysis='unicode-analysis', version='unicode', start=8, end=9)
        self.assertEqual(self.db.execute("SELECT text FROM unit_text WHERE id='umlaut'").fetchone()[0], 'a\u0308')
        self.assertEqual(self.db.execute("SELECT text FROM unit_text WHERE id='emoji'").fetchone()[0], '😀')
        self.assertEqual(list(store.word_spans(body)), [(0, 4), (5, 7)])

    def test_negative_zero_fractional_and_outside_spans_rejected(self):
        for start, end in [(-1, 2), (0, 0), (2, 1), (0, 100000), (0.5, 4)]:
            with self.subTest(start=start, end=end), self.assertRaises(sqlite3.IntegrityError):
                self.insert_unit(start=start, end=end)

    def test_unknown_version_or_analysis_rejected(self):
        for kwargs in [dict(version='missing'), dict(analysis='missing'), dict(id=None)]:
            with self.subTest(kwargs=kwargs), self.assertRaises(sqlite3.IntegrityError):
                self.insert_unit(**kwargs)

    def test_analysis_and_version_must_agree(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.insert_unit(version='untersuchungen-excerpt-v1')

    def test_parent_containment_and_identity(self):
        for kwargs in [dict(parent='g:s7'), dict(parent='u:s1'),
                       dict(parent='a:s1c1'), dict(parent='missing')]:
            with self.subTest(kwargs=kwargs), self.assertRaises(sqlite3.IntegrityError):
                self.insert_unit(**kwargs)

    def test_immutable_versions_units_and_analyses(self):
        for table in ('text_version', 'unit', 'analysis'):
            self.rejects(f'UPDATE {table} SET id=id')
            self.rejects(f'DELETE FROM {table}')

    def test_nul_text_rejected(self):
        version = dict(self.packet['versions'][0], id='nul', body='a\x00b')
        with self.assertRaises(sqlite3.IntegrityError):
            store.insert(self.db, 'text_version', version)

    def test_quote_anchor_rejects_ambiguous_missing_and_overlapping_matches(self):
        for body, quote in [('abc abc', 'abc'), ('abc', 'xyz'), ('aaa', 'aa'), ('abc', '')]:
            with self.subTest(body=body, quote=quote), self.assertRaises(ValueError):
                store.anchor(body, quote)
        self.assertEqual(store.anchor('abc abc', 'abc', 4, 7), (4, 7))

    def test_source_and_body_hashes_checked_before_import(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'test.json'
            for key in ('source_sha256', 'body_sha256'):
                packet = json.loads(store.PACKET.read_text())
                packet['versions'][0][key] = '0' * 64
                path.write_text(json.dumps(packet))
                with store.connect() as db, self.assertRaises(ValueError):
                    store.build(db, path)

    def test_alignment_requires_both_sides_and_correct_versions(self):
        self.db.execute('''INSERT INTO alignment VALUES
            ('test', 'grundzuege-001-v1','untersuchungen-excerpt-v1','test','synthetic','draft')''')
        self.rejects("UPDATE alignment SET status='proposed' WHERE id='test'")
        self.db.execute("INSERT INTO alignment_member VALUES ('test','left','g:s1')")
        self.rejects("UPDATE alignment SET status='proposed' WHERE id='test'")
        self.rejects("INSERT INTO alignment_member VALUES ('test','right','g:s2')")
        self.db.execute("INSERT INTO alignment_member VALUES ('test','right','u:s1')")
        self.db.execute("UPDATE alignment SET status='proposed' WHERE id='test'")
        self.rejects("DELETE FROM alignment_member WHERE alignment_id='test'")
        self.rejects("INSERT INTO alignment_member VALUES ('test','left','g:s2')")
        self.rejects("UPDATE alignment SET left_version=right_version WHERE id='test'")
        self.rejects("UPDATE alignment SET status='draft' WHERE id='test'")

    def test_cannot_bypass_alignment_checks_at_creation(self):
        self.rejects('''INSERT INTO alignment VALUES
            ('test','grundzuege-001-v1','untersuchungen-excerpt-v1','test','test','proposed')''')
        self.rejects("INSERT INTO alignment_member VALUES ('missing','left','g:s1')")
        self.rejects("UPDATE alignment_member SET unit_id='g:s1'")

    def test_two_by_two_form_correspondence(self):
        for side in ('left', 'right'):
            rows = self.db.execute('''SELECT u.text FROM alignment_member m JOIN unit_text u
                ON u.id=m.unit_id WHERE m.alignment_id='A001' AND m.side=? ORDER BY u.start''', (side,)).fetchall()
            self.assertEqual([r[0] for r in rows], ['keine', 'Veranlassung'])

    def test_word_to_ancestors_evidence_decision_and_alternative_analyses(self):
        word = self.db.execute("SELECT id FROM unit_text WHERE kind='word' AND text='Sprachkunde' AND version_id='grundzuege-001-v1'").fetchone()[0]
        trace = store.trace_word(self.db, word)
        self.assertEqual([r['kind'] for r in trace['ancestry']], ['word', 'sentence', 'paragraph'])
        self.assertEqual([r['id'] for r in trace['decisions']], ['D001'])
        self.assertIn('E01', [r['id'] for r in trace['evidence']])
        self.assertEqual(self.db.execute("SELECT count(DISTINCT analysis_id) FROM unit WHERE id IN ('a:s7c2','b:s7c2')").fetchone()[0], 2)
        e01 = next(r for r in trace['evidence'] if r['id'] == 'E01')
        self.assertEqual(e01['quote_status'], 'scan_checked_by_coordinator')
        self.assertEqual(e01['claim_status'], 'reported_not_independently_verified')

    def test_integrity_and_foreign_keys(self):
        self.assertEqual(store.summary(self.db)['integrity'], 'ok')
        self.assertEqual(store.summary(self.db)['foreign_key_errors'], [])


if __name__ == '__main__':
    unittest.main()
