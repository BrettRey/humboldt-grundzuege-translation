"""Bounded pilot coverage, meaningful span regressions and preserved old state."""
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import alignment_store as store
import build_difficult_pilot as pilot


class DifficultPilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db=store.connect();pilot.build(cls.db)

    @classmethod
    def tearDownClass(cls):cls.db.close()

    def test_complete_source_and_each_rendering_version(self):
        source=pilot.read('source.json')
        self.assertEqual(' '.join(s['text'] for s in source['sentences']),source['body'])
        self.assertEqual(len(source['sentences']),18)
        self.assertTrue(source['body'].startswith('Es darf aber hier ein Umstand'))
        self.assertTrue(source['body'].endswith('in verschiednen Epochen kennen.'))
        versions=['en147-'+w+'-v1' for w in ['claude','muse','codex']]+['en147-synthesis-v1','en147-revised-v2']
        for version in versions:
            self.assertEqual(self.db.execute('SELECT count(*) FROM unit WHERE version_id=? AND kind=?',(version,'rendering')).fetchone()[0],18)
            self.assertEqual(self.db.execute('SELECT count(*) FROM alignment WHERE left_version=? AND right_version=? AND relation=?',(pilot.GERMAN,version,'source_sentence_rendering')).fetchone()[0],18)
        self.assertEqual(store.summary(self.db)['integrity'],'ok')
        self.assertEqual(store.summary(self.db)['foreign_key_errors'],[])

    def test_critical_spans_scope_and_typed_terminology_links(self):
        for anchor in pilot.read('alignments.json')['anchors']:
            for suffix,field in [('de','german'),('en','english')]:
                row=self.db.execute('SELECT * FROM unit_text WHERE id=?',('p147:'+anchor['id']+':'+suffix,)).fetchone()
                self.assertEqual(row['text'],anchor[field])
        final={s['id']:s['text'] for s in pilot.read('revised.json')['sentences']}
        self.assertIn('and that the manner of indication',final['s05'])
        self.assertIn('not itself recognizable merely by its position',final['s06'])
        self.assertIn('provided one pays no attention',final['s10'])
        self.assertIn('from the language alone',final['s18'])
        for link in pilot.read('term-links.json'):
            u=self.db.execute('SELECT * FROM unit_text WHERE id=?',('p147:term:'+link['id'],)).fetchone()
            self.assertEqual(u['text'],link['quote'])
            row=self.db.execute('SELECT decision_id FROM unit_decision WHERE unit_id=?',(u['id'],)).fetchone()
            self.assertEqual(row[0],'D009.'+link['sense_id'])
        for row in self.db.execute("SELECT u.*,v.body FROM unit_text u JOIN text_version v ON v.id=u.version_id WHERE u.version_id LIKE 'en147-%' OR u.version_id=?",(pilot.GERMAN,)):
            self.assertEqual(row['body'][row['start']:row['end']],row['text'])

    def test_every_audit_finding_dispositioned_and_candidates_frozen(self):
        audits=pilot.read('audits.json')
        actual={(a['id'],f['id']) for a in audits['audits'] for f in a['findings']}
        self.assertEqual(actual,{(d['audit'],d['finding']) for d in audits['dispositions']})
        self.assertEqual(len(actual),13)
        expected={f's{n:02}' for n in range(1,19)}
        for a in audits['audits']:self.assertEqual(set(a['checked_sentences']),expected)
        self.assertTrue(any(d['finding']=='F01' and d['status']=='accepted' for d in audits['dispositions']))
        freeze=json.loads((store.ROOT/'tmp/difficult-147/candidate-freeze.json').read_text())
        self.assertEqual(store.sha256((pilot.PILOT/'candidates.json').read_bytes()),freeze['sha256'])
        candidates=pilot.read('candidates.json')['candidates']
        self.assertEqual(len(candidates),3)
        self.assertEqual(len({m for c in candidates for m in c['models']}),3)
        self.assertEqual(len({c['prompt_sha256'] for c in candidates}),1)
        notes=pilot.read('notes.json')
        self.assertIn('98',notes['author_note']['source'])
        self.assertIn('editor',notes['editor_note']['English'])
        self.assertIn('ì',final_text:=' '.join(s['text'] for s in pilot.read('revised.json')['sentences']))

    def test_sealed_sources_and_earlier_database_rows_remain_unchanged(self):
        for path,digest in pilot.read('baseline.json').items():
            self.assertEqual(hashlib.sha256((store.ROOT/path).read_bytes()).hexdigest(),digest,path)
        old=sqlite3.connect((store.ROOT/'tmp/termbase-v2/termbase-final.sqlite').resolve().as_uri()+'?mode=ro',uri=True)
        try:
            for table in ['text_version','analysis','unit','evidence','decision','alignment','alignment_member']:
                old.row_factory=sqlite3.Row
                for row in old.execute('SELECT * FROM '+table):
                    keys=list(row.keys());where=' AND '.join(k+' IS ?' for k in keys)
                    self.assertEqual(self.db.execute('SELECT count(*) FROM '+table+' WHERE '+where,tuple(row)).fetchone()[0],1,table)
        finally:old.close()


if __name__=='__main__':unittest.main()
