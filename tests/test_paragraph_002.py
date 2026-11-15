"""Cumulative-store and provenance checks, not a German fidelity benchmark."""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import alignment_store as store
import build_paragraph_002 as paragraph


class Paragraph002Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = store.connect()
        paragraph.build(cls.db)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_roundtrips_and_complete_written_token_coverage(self):
        for version in self.db.execute('SELECT * FROM text_version'):
            self.assertEqual(store.sha256(version['body'].encode()), version['body_sha256'])
            for unit in self.db.execute('SELECT * FROM unit_text WHERE version_id=?', (version['id'],)):
                self.assertEqual(unit['text'], version['body'][unit['start']:unit['end']])
            expected = list(store.word_spans(version['body']))
            actual = [tuple(r) for r in self.db.execute("SELECT start,end FROM unit WHERE version_id=? AND kind='word' ORDER BY start", (version['id'],))]
            self.assertEqual(actual, expected)

    def test_followup_versions_and_alignments_name_the_correct_paragraph(self):
        versions = self.db.execute("SELECT * FROM text_version WHERE id LIKE 'en2-%'").fetchall()
        self.assertEqual(len(versions), 5)
        for version in versions:
            self.assertIn('§2', version['title'])
            self.assertIn('g2:s1', version['locator'])
            self.assertNotIn('g:s7', version['locator'])
        groups = self.db.execute("SELECT * FROM alignment WHERE id LIKE 'sentence:en2-%'").fetchall()
        self.assertEqual(len(groups), 15)
        for group in groups:
            self.assertEqual(group['left_version'], paragraph.GERMAN)

    def test_all_eleven_anchors_link_to_proposed_target_spans(self):
        expected = {r['source_id'] for r in paragraph.load('alignments.json')['clauses']}
        found = set()
        for group in self.db.execute("SELECT * FROM alignment WHERE id LIKE 'clause:p2:%'"):
            self.assertEqual(group['status'], 'proposed')
            self.assertEqual(group['left_version'], paragraph.GERMAN)
            self.assertEqual(group['right_version'], paragraph.FINAL)
            found.update(r[0] for r in self.db.execute("SELECT unit_id FROM alignment_member WHERE alignment_id=? AND side='left'", (group['id'],)))
            self.assertGreater(self.db.execute("SELECT count(*) FROM alignment_member WHERE alignment_id=? AND side='right'", (group['id'],)).fetchone()[0], 0)
        self.assertEqual(found, expected)
        self.assertEqual(len(found), 11)
        self.assertEqual(self.db.execute("SELECT count(*) FROM alignment_member WHERE alignment_id='sentence:en2-revised-v2:g2:s3' AND side='right'").fetchone()[0], 2)

    def test_repeated_similarity_and_word_to_decision_query(self):
        rows = self.db.execute("SELECT side,count(*) FROM alignment_member WHERE alignment_id='lexical:p2-similarity' GROUP BY side").fetchall()
        self.assertEqual(dict(rows), {'left': 2, 'right': 2})
        word = paragraph.word(self.db, paragraph.FINAL, 'g2:s3', 'similarity')
        trace = store.trace_word(self.db, word)
        self.assertIn('D005.4', [d['id'] for d in trace['decisions']])
        self.assertIn('D001', [d['id'] for d in trace['decisions']])
        self.assertEqual(trace['ancestry'][-1]['kind'], 'paragraph')

    def test_all_six_audit_findings_have_anchored_dispositions(self):
        audits = paragraph.load('audits.json')
        source = json.loads(paragraph.PACKET.read_text())['versions'][0]['body']
        english = ' '.join(s['english'] for s in audits['audited_text']['sentences'])
        findings = {(a['id'],f['id']) for a in audits['audits'] for f in a['findings']}
        dispositions = {(d['auditor'],d['finding']) for d in paragraph.load('decisions.json')['audit_dispositions']}
        self.assertEqual(findings, dispositions)
        self.assertEqual(len(findings), 6)
        for auditor in audits['audits']:
            for finding in auditor['findings']:
                self.assertIn(finding['source_quote'], source)
                self.assertIn(finding['english_quote'], english)

    def test_human_editorial_approval_is_separate_from_fidelity(self):
        decision = self.db.execute("SELECT * FROM decision WHERE id='D004'").fetchone()
        self.assertEqual(decision['status'], 'adopted')
        self.assertIn('Does not certify fidelity', decision['resolution'])
        self.assertIsNotNone(self.db.execute("SELECT 1 FROM unit_decision WHERE unit_id='en-revised-v2:p1' AND decision_id='D004'").fetchone())
        self.assertEqual(self.db.execute("SELECT status FROM decision WHERE id='D005.2'").fetchone()[0], 'provisional')
        self.assertEqual(self.db.execute("SELECT claim_status FROM evidence WHERE id='E01'").fetchone()[0], 'reported_not_independently_verified')
        self.assertEqual(store.summary(self.db)['integrity'], 'ok')
        self.assertEqual(store.summary(self.db)['foreign_key_errors'], [])


if __name__ == '__main__':
    unittest.main()
