"""Complete-section provenance and real versioned-clarification regressions."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'translations/introduction'
sys.path.insert(0,str(ROOT/'src'))
from humboldt.ingest import load


def read(name):return json.loads((P/name).read_text())


class IntroductionRecord(unittest.TestCase):
    def test_full_section_coverage_independence_and_printed_paragraphs(self):
        source=read('source.json');candidates=read('candidates.json');audit=read('audits.json');final=read('revised.json');record=read('record.json')
        ids=[s['id'] for p in source['paragraphs'] for s in p['sentences']]
        targets=[s['id'] for p in source['paragraphs'] if p['number'] in (6,7) for s in p['sentences']]
        self.assertEqual(len(ids),38);self.assertEqual(len(targets),13)
        self.assertEqual(candidates['packet_sha256'],hashlib.sha256((P/'packet.md').read_bytes()).hexdigest())
        self.assertEqual(len(candidates['candidates']),3)
        self.assertEqual(len({tuple(c['models']) for c in candidates['candidates']}),3)
        for c in candidates['candidates']:
            self.assertEqual([s['source_id'] for s in c['sentences']],targets)
            self.assertTrue(c['source_status_acknowledged'])
        self.assertEqual(len(audit['auditors']),2)
        for a in audit['auditors']:self.assertEqual(set(a['coverage']),set(ids))
        findings={(a['auditor'],f['id']) for a in audit['auditors'] for f in a['findings']}
        self.assertEqual(len(findings),27)
        self.assertEqual(findings,{(d['auditor'],d['finding_id']) for d in audit['dispositions']})
        self.assertEqual(source['paragraphs'][6]['typographic_groups'],[list(range(1,8)),[8,9]])
        self.assertEqual(final['paragraphs'][6]['typographic_groups'],source['paragraphs'][6]['typographic_groups'])
        self.assertEqual([s['source_id'] for p in final['paragraphs'] for s in p['sentences']],ids)
        for key in ['source','synthesis','final','source_unit_map','apparatus','audit_source']:
            self.assertEqual(record[key]['sha256'],hashlib.sha256((ROOT/record[key]['path']).read_bytes()).hexdigest())
        self.assertTrue(all(r['exit_code']==0 for r in record['runs']))
        prompts=read('prompts.json')['recipes']
        for stage,recipe in prompts.items():
            prompt=''.join((ROOT/part['file']).read_text() if 'file' in part else part['literal'] for part in recipe['parts'])
            digest=hashlib.sha256(prompt.encode()).hexdigest()
            self.assertEqual(digest,recipe['sha256'])
            self.assertTrue(all(r['prompt_sha256']==digest for r in record['runs'] if r['stage']==stage))
        self.assertEqual(record['whole_work_context']['sha256'],hashlib.sha256((ROOT/record['whole_work_context']['path']).read_bytes()).hexdigest())
        self.assertIn('pending',final['review_status'])

    def test_attributed_clarifications_preserve_bodies_and_have_explicit_new_links(self):
        tables,_=load(ROOT,changes=True);versions={r['id']:r for r in tables['text_version']};units={r['id']:r for r in tables['unit']};mapping=read('source-unit-map.json');final=read('revised.json');edits=read('clarifications.json')['events']
        self.assertEqual({e['number'] for e in edits},{1,4})
        for e in edits:
            old=versions[e['old_version']];new=versions[e['new_version']]
            self.assertEqual(new['body'],old['body'].replace(e['before'],e['after']))
            self.assertEqual(new['body'],' '.join(s['english'] for s in final['paragraphs'][e['number']-1]['sentences']))
            self.assertFalse(json.loads(new['provenance'])['source_verification_inherited'])
            for s in final['paragraphs'][e['number']-1]['sentences']:
                m=mapping[s['source_id']];unit=units[m['final_English_unit']]
                self.assertEqual(unit['version_id'],new['id'])
                self.assertEqual(new['body'][unit['start']:unit['end']],s['english'])
                groups={r['alignment_id'] for r in tables['alignment_member'] if r['unit_id']==unit['id'] and r['side']=='right'}
                self.assertTrue(any(r['alignment_id'] in groups and r['unit_id']==m['source_unit'] and r['side']=='left' for r in tables['alignment_member']))
        for number,path in [(2,'translations/paragraph-002/revised.json'),(3,'translations/paragraph-003/revised.json'),(5,'translations/paragraph-005/revised.json')]:
            old=json.loads((ROOT/path).read_text())
            self.assertEqual([s['english'] for s in old['sentences']],[s['english'] for s in final['paragraphs'][number-1]['sentences']])


if __name__=='__main__':unittest.main()
