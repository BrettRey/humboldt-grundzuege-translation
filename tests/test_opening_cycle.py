"""Cross-file integration checks; these do not certify translation fidelity."""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import alignment_store as store
import build_opening_cycle as cycle


class OpeningCycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = store.connect()
        cycle.build(cls.db)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_every_version_span_roundtrips_and_source_fingerprint_matches(self):
        bodies = {r['id']: r['body'] for r in self.db.execute('SELECT id, body FROM text_version')}
        for row in self.db.execute('SELECT * FROM text_version'):
            self.assertEqual(store.sha256(row['body'].encode()), row['body_sha256'])
            store.verify_file(row['source_path'], row['source_sha256'])
        for row in self.db.execute('SELECT * FROM unit_text'):
            self.assertEqual(row['text'], bodies[row['version_id']][row['start']:row['end']])

    def test_all_twenty_anchors_have_proposed_target_spans(self):
        expected = {r['source_id'] for r in cycle.load('alignments.json')['clauses']}
        found = set()
        for group in self.db.execute("SELECT * FROM alignment WHERE relation='proposed_clause_correspondence'"):
            self.assertEqual(group['status'], 'proposed')
            left = self.db.execute("SELECT unit_id FROM alignment_member WHERE alignment_id=? AND side='left'", (group['id'],)).fetchall()
            self.assertEqual(len(left), 1)
            found.add(left[0][0])
            targets = self.db.execute("SELECT count(*) FROM alignment_member WHERE alignment_id=? AND side='right'", (group['id'],)).fetchone()[0]
            self.assertGreaterEqual(targets, 1)
        self.assertEqual(found, expected)
        self.assertEqual(len(found), 20)

    def test_sentence_split_and_noncontiguous_predicate_mapping(self):
        split = self.db.execute("SELECT count(*) FROM alignment_member WHERE alignment_id=? AND side='right'", ('sentence:en-revised-v2:g:s6',)).fetchone()[0]
        self.assertEqual(split, 2)
        spans = self.db.execute('''SELECT u.start,u.end,u.text FROM alignment_member m JOIN unit_text u ON u.id=m.unit_id
            WHERE m.alignment_id='clause:a:s6c2' AND m.side='right' ORDER BY u.start''').fetchall()
        self.assertEqual(len(spans), 2)
        self.assertLess(spans[0]['end'], spans[1]['start'])
        self.assertTrue(spans[0]['text'].startswith('Throughout the period'))
        self.assertTrue(spans[1]['text'].startswith('came, free'))

    def test_lexical_group_disambiguates_repeated_English_word(self):
        with self.assertRaises(ValueError):
            cycle.unique_word(self.db, cycle.FINAL, 'distinctive')
        target = cycle.unique_word(self.db, cycle.FINAL, 'distinctive', 'g:s6')
        group = self.db.execute("SELECT side,count(*) FROM alignment_member WHERE alignment_id='lexical:distinctiveness' GROUP BY side").fetchall()
        self.assertEqual(dict(group), {'left': 2, 'right': 4})
        self.assertIsNotNone(self.db.execute("SELECT 1 FROM alignment_member WHERE alignment_id='lexical:distinctiveness' AND unit_id=?", (target,)).fetchone())
        trace = store.trace_word(self.db, target)
        self.assertIn('D003.3', [r['id'] for r in trace['decisions']])
        self.assertIn('D001', [r['id'] for r in trace['decisions']])

    def test_all_audit_findings_have_dispositions_and_exact_pre_revision_anchors(self):
        audits = cycle.load('audits.json')
        source = json.loads(store.PACKET.read_text())['versions'][0]['body']
        english = ' '.join(r['english'] for r in audits['audited_text']['sentences'])
        findings = {(a['id'], f['id']) for a in audits['audits'] for f in a['findings']}
        dispositions = {(d['auditor'], d['finding']) for d in cycle.load('decisions.json')['audit_dispositions']}
        self.assertEqual(findings, dispositions)
        self.assertEqual(len(findings), 12)
        for auditor in audits['audits']:
            for finding in auditor['findings']:
                self.assertIn(finding['source_quote'], source)
                self.assertIn(finding['english_quote'], english)

    def test_statuses_and_integrity_remain_separate(self):
        self.assertEqual(self.db.execute("SELECT status FROM decision WHERE id='D001'").fetchone()[0], 'adopted')
        self.assertEqual(self.db.execute("SELECT status FROM decision WHERE id='D003.6'").fetchone()[0], 'provisional')
        self.assertEqual(self.db.execute("SELECT claim_status FROM evidence WHERE id='E01'").fetchone()[0], 'reported_not_independently_verified')
        self.assertEqual(self.db.execute("SELECT claim_status FROM evidence WHERE id='AUDIT:muse:F4'").fetchone()[0], 'model_judgment_on_pre_revision_text')
        self.assertEqual(store.summary(self.db)['integrity'], 'ok')
        self.assertEqual(store.summary(self.db)['foreign_key_errors'], [])


if __name__ == '__main__':
    unittest.main()
