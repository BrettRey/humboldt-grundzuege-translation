"""Coverage, provenance and relational checks, not a German-meaning benchmark."""
from collections import Counter
import json
from pathlib import Path
import re
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import alignment_store as store
import assemble_termbase as assembly
import terminology_candidates as candidates
import termbase_store as termbase


class TermbaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog=json.loads(termbase.CATALOG.read_text())
        cls.db=store.connect();termbase.build(cls.db)

    @classmethod
    def tearDownClass(cls):cls.db.close()

    def test_every_candidate_and_page_has_a_disposition(self):
        pages=json.loads((store.ROOT/'sources/terminology/search-pages.json').read_text())
        all_ids=set()
        for name,(a,b) in candidates.RANGES.items():
            derived=candidates.inventory(pages,a,b,name)
            supplied=json.loads((termbase.DATA/f'{name}-candidates.json').read_text())
            self.assertEqual(derived,supplied)
            all_ids.update(x['id'] for x in supplied)
        actual=Counter(x['id'] for x in self.catalog['candidate_reviews'])
        self.assertEqual(set(actual),all_ids)
        self.assertTrue(all(n==1 for n in actual.values()))
        self.assertTrue(all(r['disposition']!='needs_review' and r['reason'] for r in self.catalog['candidate_reviews']))
        self.assertEqual(Counter(r['page'] for r in self.catalog['page_reviews']),Counter(range(364,474)))
        self.assertEqual(self.catalog['issues'],[])
        self.assertEqual(self.catalog,json.loads(json.dumps(assembly.assemble())))

    def test_original_labels_map_without_inflating_variants(self):
        old=json.loads((store.ROOT/'sources/terminology/register.json').read_text())
        expected={form for entry in old['entries'] for form in entry['forms']}
        self.assertEqual({x['old_label'] for x in self.catalog['carry_forward']},expected)
        self.assertEqual(len(self.catalog['carry_forward']),len(expected))
        for head in ['Geist','Verstand','Vernunft','Seele','Gemüth','Einbildungskraft','Vermögen']:
            self.assertEqual(len(termbase.query(self.db,head)),1,head)
        self.assertEqual(termbase.query(self.db,'Organe')[0]['id'],termbase.query(self.db,'Organ')[0]['id'])
        self.assertEqual(termbase.query(self.db,'Adjectiva')[0]['id'],termbase.query(self.db,'Adjectivum')[0]['id'])
        # Grammatical-number variants and two different lexemes are distinct decisions.
        self.assertNotEqual(termbase.query(self.db,'Geist')[0]['id'],termbase.query(self.db,'geistig')[0]['id'])
        self.assertEqual([r['headword'] for r in termbase.query(self.db,'Denkenden')],['Denkender'])
        self.assertNotIn('Denkenden',[f['form'] for f in termbase.query(self.db,'Sprechender')[0]['forms']])

    def test_each_use_has_checked_primary_evidence_and_true_source_coordinates(self):
        pages={p['printed_page']:p for p in json.loads((store.ROOT/'sources/terminology/search-pages.json').read_text())}
        maps={int(p['printed_page']):p for p in json.loads((store.ROOT/'sources/page-map.json').read_text())['pages']}
        for t in self.catalog['terms']:
            for s in t['senses']:
                self.assertTrue(s['renderings'] and s['definition'] and s['rule'])
                self.assertEqual({u['id'] for u in s['uses']},{e['use_id'] for e in s['evidence']})
                for e in s['evidence']:
                    self.assertTrue(e['checked_quote'])
                    if e['evidence_role']=='direct_occurrence':self.assertIsNotNone(re.search(r'(?<!\w)'+re.escape(e['term_form'])+r'(?!\w)',e['checked_quote'],re.I))
                    else:self.assertIsNone(e['term_form'])
                    if e.get('page_span'):
                        a,b=e['page_span'];self.assertEqual(pages[e['printed_page']]['text'][a:b],e['ocr_quote'])
                        self.assertEqual(e['pdf_page'],maps[e['printed_page']]['pdf_page'])
                        self.assertEqual(e['scan_leaf'],maps[e['printed_page']]['scan_leaf'])

    def test_checked_text_and_ocr_windows_are_separate_and_roundtrip(self):
        for row in self.db.execute('''SELECT a.*,c.text AS checked,o.text AS ocr,x.text AS expression
          FROM sense_attestation a JOIN unit_text c ON c.id=a.checked_context_unit
          LEFT JOIN unit_text x ON x.id=a.checked_expression_unit LEFT JOIN unit_text o ON o.id=a.ocr_context_unit'''):
            if row['evidence_role']=='direct_occurrence':self.assertEqual(row['expression'],row['term_form'])
            else:self.assertIsNone(row['checked_expression_unit'])
            if row['ocr_context_unit']:
                window=self.db.execute('SELECT * FROM unit WHERE id=?',(row['ocr_context_unit'],)).fetchone()
                page=self.db.execute('SELECT * FROM unit WHERE id=?',(row['source_page_unit'],)).fetchone()
                self.assertLessEqual(page['start'],window['start']);self.assertGreaterEqual(page['end'],window['end'])
        self.assertEqual(self.db.execute("SELECT transcription_status FROM text_version WHERE id='grundzuege-search-v1'").fetchone()[0],'uncorrected_search_text')
        self.assertEqual(self.db.execute("SELECT transcription_status FROM text_version WHERE id='grundzuege-checked-term-excerpts-v2'").fetchone()[0],'model_image_checked_excerpts')
        self.assertEqual(store.summary(self.db)['integrity'],'ok')
        self.assertEqual(store.summary(self.db)['foreign_key_errors'],[])

    def test_supporting_context_and_word_fragments_are_not_false_variants(self):
        self.assertNotIn('lex:form',[r['id'] for r in termbase.query(self.db,'Operationen')])
        self.assertNotIn('lex:schoepfungsvermoegen',[r['id'] for r in termbase.query(self.db,'vermögen')])
        joined=termbase.query(self.db,'Schöpfungsvermögen')[0]['composite_attestations']
        self.assertEqual(joined[0]['joined_form'],'Schöpfungsvermögen')
        rows=self.db.execute('''SELECT a.printed_page FROM composite_member m JOIN sense_attestation a ON a.id=m.attestation_id WHERE m.group_id=? ORDER BY part_order''',(joined[0]['id'],)).fetchall()
        self.assertEqual([r[0] for r in rows],[424,425])
        item=self.db.execute("SELECT a.checked_expression_unit FROM sense_attestation a JOIN term_sense s ON s.id=a.sense_id JOIN lexeme l ON l.id=s.lexeme_id WHERE l.headword='Verstand' AND a.evidence_role='direct_occurrence' LIMIT 1").fetchone()[0]
        self.assertEqual(termbase.trace(self.db,item)['matches'][0]['headword'],'Verstand')

    def test_local_sense_guards_and_historical_controls_remain_explicit(self):
        verstand=termbase.query(self.db,'Verstand')[0]
        self.assertTrue(any('sense' in s['definition'].casefold() or 'idiom' in s['label'].casefold() for s in verstand['senses']))
        form=termbase.query(self.db,'grammatische Form')[0]
        material=' '.join(s['definition']+' '+s['rule']+' '+s['caution'] for s in form['senses'])
        self.assertIn('independent',material.casefold())
        self.assertTrue(termbase.query(self.db,'Gemüth')[0]['controls'])
        self.assertEqual(termbase.query(self.db,'no-such-source-term'),[])
        self.assertEqual(termbase.query(self.db,'VERSTAND')[0]['id'],verstand['id'])

    def test_preserved_inputs_and_exact_anchor_failure(self):
        for path,fingerprint in json.loads((termbase.DATA/'baseline.json').read_text()).items():
            self.assertEqual(store.sha256((store.ROOT/path).read_bytes()),fingerprint,path)
        with self.assertRaises(ValueError):assembly.span('Form und Form','Form')
        with self.assertRaises(ValueError):assembly.span('Form','not in source')
        self.assertEqual(assembly.span('eine Form hier','Form'),(5,9))


if __name__=='__main__':unittest.main()
