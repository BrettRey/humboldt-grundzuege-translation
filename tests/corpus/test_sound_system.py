"""Whole-unit coverage, print apparatus, durable provenance and reader attachment."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / 'translations/sound-system'
sys.path.insert(0, str(ROOT / 'src'))
from humboldt.ingest import load


def read(name):
    return json.loads((P / name).read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def block_ids():
    source = read('source.json')
    result = []
    for p in source['paragraphs']:
        result.extend(h['id'] for h in source['headings'] if h['before'] == p['number'])
        result.extend(s['id'] for s in p['sentences'])
        result.extend(n['id'] for n in source['source_notes'] if n['number'] == p['number'])
    return result


class SoundSystemRecord(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tables, _ = load(ROOT)
        cls.versions = {r['id']: r for r in cls.tables['text_version']}
        cls.units = {r['id']: r for r in cls.tables['unit']}

    def test_frozen_independent_coverage_and_all_dispositions(self):
        ids = block_ids()
        self.assertEqual(len(ids), 120)
        self.assertEqual(len(set(ids)), 120)
        candidates, audit = read('candidates.json'), read('audits.json')
        self.assertEqual(candidates['packet_sha256'], sha(P / 'candidate-packet.md'))
        self.assertEqual(audit['synthesis_sha256'], sha(P / 'synthesis.json'))
        self.assertEqual(len(candidates['candidates']), 3)
        self.assertEqual(len({tuple(c['models']) for c in candidates['candidates']}), 3)
        for c in candidates['candidates']:
            self.assertEqual([s['source_id'] for s in c['sentences']], ids)
            self.assertTrue(c['source_status_acknowledged'])
        self.assertEqual(len(audit['auditors']), 2)
        for a in audit['auditors']:
            self.assertEqual(a['coverage'], ids)
        findings = {(a['auditor'], f['id']) for a in audit['auditors'] for f in a['findings']}
        self.assertEqual(findings, {(d['auditor'], d['finding_id']) for d in audit['dispositions']})
        self.assertTrue(all(d['resolution'] for d in audit['dispositions']))
        for stage, recipe in read('prompts.json')['recipes'].items():
            prompt = ''.join((ROOT / x['file']).read_text() if 'file' in x else x['literal'] for x in recipe['parts'])
            digest = hashlib.sha256(prompt.encode()).hexdigest()
            self.assertEqual(digest, recipe['sha256'])
            for run in read('record.json')['runs']:
                if run['stage'] == stage:
                    self.assertEqual(run['prompt_sha256'], digest)
        self.assertEqual(len(read('record.json')['failed_runs']), 1)
        self.assertNotEqual(read('record.json')['failed_runs'][0]['exit_code'], 0)
        for entry in read('record.json')['artifacts']:
            self.assertEqual(entry['sha256'], sha(ROOT / entry['path']))

    def test_print_boundaries_ancillary_versions_and_trace(self):
        source, final, mapping = read('source.json'), read('revised.json'), read('source-unit-map.json')
        self.assertEqual([p['number'] for p in source['paragraphs']], [56,57,58,59,60,61,62,'62a','62b',63,64,65,66,67,68,69,70,71])
        self.assertEqual(sum(len(p['sentences']) for p in source['paragraphs']), 108)
        self.assertEqual([h['marker'] for h in source['headings']], ['b.', 'α.'])
        self.assertEqual(len(source['source_notes']), 10)
        self.assertEqual(sum(n['authorship'] == 'humboldt' for n in source['source_notes']), 7)
        self.assertEqual(sum(n['authorship'] == 'editor1906' for n in source['source_notes']), 3)
        self.assertIn('gestrichene Polnische l', mapping['p62:s3']['source_text'])
        self.assertIn('kurzes e und o', mapping['p65:s4']['source_text'])
        self.assertIn('weil weniger üblichen', mapping['note:sanskrit-pronouns']['source_text'])
        self.assertEqual(set(mapping), set(block_ids()))
        defaults = {r['section']: r for r in json.loads((ROOT / 'edition/manifest.json').read_text())['reading_defaults']}
        members = {}
        for r in self.tables['alignment_member']:
            members.setdefault(r['alignment_id'], set()).add((r['side'], r['unit_id']))
        for p in final['paragraphs']:
            self.assertEqual(defaults[str(p['number'])]['target_id'], f'en{p["number"]}-revised-v2')
        for sid, m in mapping.items():
            de, en = self.units[m['source_unit']], self.units[m['final_English_unit']]
            self.assertEqual(self.versions[de['version_id']]['body'][de['start']:de['end']], m['source_text'])
            self.assertTrue(any({('left', de['id']), ('right', en['id'])} <= pair for pair in members.values()), sid)
        from humboldt import database, ingest, queries
        db = database.connect()
        try:
            ingest._populate(db, ROOT)
            ordered = [r['section'] for r in queries.sections(db)]
            self.assertEqual(ordered[ordered.index('62'):ordered.index('63')+1], ['62','62a','62b','63'])
            for label in ['62a','62b']:
                result = queries.passage(db,label)
                self.assertEqual(result['reading_defaults']['source_id'], f'grundzuege-062{label[-1]}-v1')
                self.assertEqual(result['reading_defaults']['target_id'], f'en{label}-revised-v2')
        finally:
            db.close()
        self.assertIn('pending', final['review_status'])

    def test_single_sequence_semantic_note_anchors_and_regeneration(self):
        annotations, mapping = read('notes.json'), read('source-unit-map.json')
        self.assertEqual([n['display_number'] for n in annotations['notes']], list(range(1, len(annotations['notes']) + 1)))
        self.assertEqual(sum(n['attribution'] == 'Humboldt' for n in annotations['notes']), 7)
        self.assertEqual(sum(n['attribution'] == '1906 Ed.' for n in annotations['notes']), 3)
        text = (P / 'reading.md').read_text()
        refs = re.findall(r'\[\^([^\]]+)\]', text.split('## Notes\n', 1)[0])
        definitions = re.findall(r'^\[\^([^\]]+)\]: ', text, re.M)
        self.assertEqual(refs, definitions)
        self.assertEqual(definitions, [n['id'] for n in annotations['notes']])
        for n in annotations['notes']:
            m = mapping[n['source_id']]
            self.assertEqual(n['source_unit'], m['source_unit'])
            v = self.versions[n['target_version']]
            self.assertEqual(n['target_body_sha256'], v['body_sha256'])
            self.assertIn(' (' + n['attribution'] + ')', text)
        source_notes = {n['id']: n for n in read('source.json')['source_notes']}
        author_notes = [n for n in annotations['notes'] if 'source_note_id' in n]
        self.assertEqual({n['source_note_id'] for n in author_notes}, set(source_notes))
        for n in author_notes:
            original = source_notes[n['source_note_id']]
            self.assertEqual(n['original_marker'], original['marker'])
            self.assertEqual(n['original_anchor'], original['original_anchor'])
            self.assertEqual(n['source_text'], original['German'])
            self.assertIn(n['source_note_id'], n['source_ids'])
            self.assertEqual(n['source_note_target_unit'], mapping[n['source_note_id']]['final_English_unit'])
            self.assertEqual(n['authorship'], original['authorship'])
        path = ROOT / 'tools/render_section_reading.py'
        spec = importlib.util.spec_from_file_location('section_renderer', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.render(P), text)


if __name__ == '__main__':
    unittest.main()
