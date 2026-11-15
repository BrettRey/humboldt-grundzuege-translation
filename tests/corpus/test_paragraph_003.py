"""Frozen passage-cycle record contracts; no source PDF or model call needed."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'translations/paragraph-003'


class Paragraph003Record(unittest.TestCase):
    def test_source_candidates_audits_and_final_have_complete_frozen_coverage(self):
        source=json.loads((P/'source.json').read_text())
        candidates=json.loads((P/'candidates.json').read_text())
        audit=json.loads((P/'audits.json').read_text())
        final=json.loads((P/'revised.json').read_text())
        ids=[f'p3:s{i}' for i in range(1,6)]
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


if __name__=='__main__':unittest.main()
