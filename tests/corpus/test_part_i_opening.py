"""Whole-unit provenance and recoverable source/English links for passages8–15."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'translations/part-i-opening'
sys.path.insert(0,str(ROOT/'src'))
from humboldt.ingest import load


def read(name):return json.loads((P/name).read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


class PartIOpeningRecord(unittest.TestCase):
    def test_complete_unit_independent_inputs_and_dispositions(self):
        source=read('source.json');candidates=read('candidates.json');audit=read('audits.json');final=read('revised.json');record=read('record.json')
        ids=[s['id'] for p in source['paragraphs'] for s in p['sentences']]
        self.assertEqual([p['number'] for p in source['paragraphs']],list(range(8,16)))
        self.assertEqual(len(ids),51)
        self.assertEqual(candidates['packet_sha256'],sha(P/'candidate-packet.md'))
        self.assertEqual(len(candidates['candidates']),3)
        self.assertEqual(len({tuple(c['models']) for c in candidates['candidates']}),3)
        for c in candidates['candidates']:
            self.assertEqual([s['source_id'] for s in c['sentences']],ids)
            self.assertTrue(c['source_status_acknowledged'])
        self.assertEqual(len(audit['auditors']),2)
        for a in audit['auditors']:
            self.assertEqual(set(a['coverage']),set(ids));self.assertEqual(len(a['coverage']),len(ids))
        findings={(a['auditor'],f['id']) for a in audit['auditors'] for f in a['findings']}
        self.assertEqual(findings,{(d['auditor'],d['finding_id']) for d in audit['dispositions']})
        self.assertTrue(all(d['resolution'] for d in audit['dispositions']))
        self.assertEqual([s['source_id'] for p in final['paragraphs'] for s in p['sentences']],ids)
        for key in ['source','synthesis','final','source_unit_map','prompts']:
            self.assertEqual(record[key]['sha256'],sha(ROOT/record[key]['path']))
        for stage,recipe in read('prompts.json')['recipes'].items():
            prompt=''.join((ROOT/x['file']).read_text() if 'file' in x else x['literal'] for x in recipe['parts'])
            digest=hashlib.sha256(prompt.encode()).hexdigest()
            self.assertEqual(digest,recipe['sha256'])
            self.assertTrue(all(r['prompt_sha256']==digest and r['exit_code']==0 for r in record['runs'] if r['stage']==stage))
        self.assertEqual(record['whole_work_context']['sha256'],sha(ROOT/record['whole_work_context']['path']))
        self.assertIn('pending',final['review_status'])
        # Scan leaves have a real gap here; PDF and leaf offsets are not constant.
        self.assertIn('leaves381,384',source['paragraphs'][1]['locator'])
        self.assertIn('leaves386',source['paragraphs'][-1]['locator'])

    def test_reading_defaults_and_bidirectional_source_links(self):
        tables,_=load(ROOT,changes=True);versions={r['id']:r for r in tables['text_version']};units={r['id']:r for r in tables['unit']};mapping=read('source-unit-map.json')
        defaults={r['section']:r for r in json.loads((ROOT/'edition/manifest.json').read_text())['reading_defaults']}
        for p in read('revised.json')['paragraphs']:
            n=p['number'];target=f'en{n}-revised-v2';self.assertEqual(defaults[str(n)]['target_id'],target)
            self.assertEqual(versions[target]['body'],' '.join(s['english'] for s in p['sentences']))
            for s in p['sentences']:
                m=mapping[s['source_id']];de=units[m['source_unit']];en=units[m['final_English_unit']]
                self.assertEqual(versions[de['version_id']]['body'][de['start']:de['end']],m['source_text'])
                self.assertEqual(versions[target]['body'][en['start']:en['end']],s['english'])
                groups={r['alignment_id'] for r in tables['alignment_member'] if r['side']=='right' and r['unit_id']==en['id']}
                self.assertTrue(any(r['alignment_id'] in groups and r['side']=='left' and r['unit_id']==de['id'] for r in tables['alignment_member']))
            self.assertIn('**'+str(n)+'** '+' '.join(s['english'] for s in p['sentences']),(P/'revised.md').read_text())


if __name__=='__main__':unittest.main()
