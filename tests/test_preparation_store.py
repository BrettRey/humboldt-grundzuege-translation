"""Discovery/provenance regressions; these do not test translation fidelity."""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import alignment_store as store
import preparation_store as preparation


class PreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = store.connect()
        preparation.build(cls.db)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_main_text_coverage_uses_actual_scan_map(self):
        pages = json.loads((store.ROOT / 'sources/page-map.json').read_text())['pages']
        found = self.db.execute('SELECT DISTINCT printed_page,pdf_page,scan_leaf FROM word_index ORDER BY printed_page').fetchall()
        self.assertEqual([r['printed_page'] for r in found], list(range(364, 474)))
        # The scan has discontinuities; do not recreate leaf IDs arithmetically.
        by_printed = {int(p['printed_page']): p for p in pages}
        for row in found:
            for key in ('pdf_page', 'scan_leaf'):
                self.assertEqual(row[key], by_printed[row['printed_page']][key])

    def test_lookup_preserves_text_and_offsets(self):
        body = self.db.execute("SELECT body FROM text_version WHERE id='grundzuege-search-v1'").fetchone()[0]
        for row in self.db.execute('SELECT w.query_form,u.text,u.start,u.end FROM word_index w JOIN unit_text u ON u.id=w.unit_id'):
            self.assertEqual(row['text'], body[row['start']:row['end']])
            self.assertEqual(row['query_form'], row['text'].casefold())
        lower = preparation.query(self.db, word='weltansicht')
        self.assertEqual(lower, preparation.query(self.db, word='WELTANSICHT'))
        self.assertTrue(any(r['printed_page'] == 387 for r in lower))

    def test_headers_recovery_and_overlapping_families_remain_visible(self):
        type_hits = preparation.query(self.db, family='type', limit=200)
        self.assertTrue(any(r['zone'] == 'header_candidate' for r in type_hits))
        self.assertTrue(any(r['zone'] == 'body_or_note' and r['printed_page'] == 373 for r in type_hits))
        self.assertEqual(self.db.execute('SELECT DISTINCT extraction FROM word_index WHERE printed_page=410').fetchone()[0], 'recovery-ocr')
        self.assertIsNotNone(self.db.execute('SELECT unit_id FROM term_occurrence GROUP BY unit_id HAVING count(*)>1').fetchone())
        source = self.db.execute("SELECT transcription_status,provenance FROM text_version WHERE id='grundzuege-search-v1'").fetchone()
        self.assertEqual(source[0], 'uncorrected_search_text')
        self.assertIn('apparatus', source[1])

    def test_register_is_traceable_without_certifying_all_occurrences(self):
        entries = preparation.load('register.json')['entries']
        for entry in entries:
            result = preparation.query(self.db, term=entry['id'])
            self.assertEqual({r['id'] for r in result['evidence']}, set(entry['evidence_ids']))
            self.assertEqual(self.db.execute('SELECT status FROM decision WHERE id=?', ('D007.' + entry['id'],)).fetchone()[0], 'provisional')
        supplied = preparation.query(self.db, term='T23')
        self.assertIn('speakers and hearers', supplied['rule'])
        self.assertIn('independently of position', supplied['exceptions'])
        self.assertEqual(preparation.query(self.db, term='DOES-NOT-EXIST'), [])
        self.assertTrue(self.db.execute("SELECT count(*) FROM unit_decision WHERE decision_id='D007.T27'").fetchone()[0])
        self.assertIsNotNone(self.db.execute("SELECT 1 FROM unit_evidence WHERE unit_id='whole:p443' AND evidence_id='prep:C23'").fetchone())
        self.assertEqual(store.summary(self.db)['integrity'], 'ok')
        self.assertEqual(store.summary(self.db)['foreign_key_errors'], [])

    def test_preserved_versions_and_all_audit_dispositions(self):
        for path, fingerprint in preparation.load('preserved-inputs.json').items():
            self.assertEqual(store.sha256((store.ROOT / path).read_bytes()), fingerprint, path)
        for version_id in ('en-revised-v2', 'en2-revised-v2'):
            version = self.db.execute('SELECT * FROM text_version WHERE id=?', (version_id,)).fetchone()
            self.assertEqual(store.sha256(version['body'].encode()), version['body_sha256'])
        findings = preparation.load('register-audit.json')
        self.assertEqual(len(findings), 6)
        self.assertTrue(all(f['disposition'] == 'accepted' and f['resolution'] for f in findings))


if __name__ == '__main__':
    unittest.main()
