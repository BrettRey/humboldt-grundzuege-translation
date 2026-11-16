"""Frozen passage-cycle record contracts; no source PDF or model call needed."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'translations/paragraph-005'


class Paragraph005Record(unittest.TestCase):
    def test_source_candidates_audits_and_final_have_complete_frozen_coverage(self):
        source=json.loads((P/'source.json').read_text())
        candidates=json.loads((P/'candidates.json').read_text())
        audit=json.loads((P/'audits.json').read_text())
        final=json.loads((P/'revised.json').read_text())
        ids=[f'p5:s{i}' for i in range(1,8)]
        self.assertEqual([s['id'] for s in source['sentences']],ids)
        self.assertEqual(source['body'],' '.join(s['text'] for s in source['sentences']))
        self.assertEqual(hashlib.sha256(source['body'].encode()).hexdigest(),source['body_sha256'])
        self.assertEqual(candidates['packet_sha256'],hashlib.sha256((P/'packet.md').read_bytes()).hexdigest())
        self.assertEqual(len(candidates['candidates']),3)
        for candidate in candidates['candidates']:
            self.assertEqual([s['source_id'] for s in candidate['sentences']],ids)
            self.assertTrue(candidate['source_status_acknowledged'])
        self.assertEqual(len(audit['auditors']),2)
        for auditor in audit['auditors']:self.assertEqual(set(auditor['coverage']),set(ids))
        findings={(a['auditor'],f['id']) for a in audit['auditors'] for f in a['findings']}
        self.assertEqual(findings,{(d['auditor'],d['finding_id']) for d in audit['dispositions']})
        self.assertEqual(len(findings),14)
        self.assertEqual([s['source_id'] for s in final['sentences']],ids)
        self.assertIn('pending',final['review_status'])
        self.assertIn('first seven paragraphs',final['source_status'])
        record=json.loads((P/'record.json').read_text())
        self.assertEqual(record['candidate_freeze']['sha256'],hashlib.sha256((P/'candidates.json').read_bytes()).hexdigest())
        self.assertEqual(record['synthesis']['sha256'],audit['synthesis_sha256'])
        self.assertEqual(audit['synthesis_sha256'],hashlib.sha256((P/'synthesis.json').read_bytes()).hexdigest())
        self.assertEqual(record['final']['sha256'],hashlib.sha256((P/'revised.json').read_bytes()).hexdigest())
        self.assertTrue(all(run['exit_code']==0 and run['models'] for run in record['runs']))
        bundle=json.loads((ROOT/'edition/passages/passage-0005/records.json').read_text())
        spans=[r for r in bundle['tables']['alignment'] if r['relation']=='provisional_translation_correspondence']
        self.assertEqual(len(spans),12)


    def test_readability_feedback_changes_metadata_without_changing_previous_English(self):
        import sys
        sys.path.insert(0,str(ROOT/'src'))
        from humboldt.ingest import load
        tables,_=load(ROOT,changes=True)
        version=next(r for r in tables['text_version'] if r['id']=='en4-revised-v2')
        previous=json.loads((ROOT/'translations/paragraph-004/revised.json').read_text())
        approval=json.loads((ROOT/'translations/paragraph-004/approval-2026-11-16.json').read_text())
        self.assertEqual(version['body'],' '.join(s['english'] for s in previous['sentences']))
        self.assertEqual(version['body_sha256'],approval['body_sha256'])
        self.assertIn('completed English-readability review',version['provenance'])
        self.assertTrue(approval['review_completed'])
        self.assertIn('no German-fidelity certification',approval['scope'])
        self.assertIn('pending',previous['review_status'])
        evidence=next(r for r in tables['evidence'] if r['id']=='E004.English-review:2026-11-16')
        self.assertEqual(evidence['excerpt'],approval['comment'])
        self.assertEqual(evidence['source_sha256'],hashlib.sha256((ROOT/evidence['source_path']).read_bytes()).hexdigest())


if __name__=='__main__':unittest.main()
