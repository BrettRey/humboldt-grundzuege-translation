"""Reader annotation must preserve text and remain traceable after journal replay."""
import hashlib
import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from humboldt import database, ingest, queries


def read(path):
    return json.loads((ROOT / path).read_text())


class ReaderNotes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.notes = read('translations/annotated/notes.json')
        cls.record = read('translations/annotated/record.json')
        cls.tables, _ = ingest.load(ROOT)
        cls.versions = {r['id']: r for r in cls.tables['text_version']}
        cls.units = {r['id']: r for r in cls.tables['unit']}
        cls.reading = (ROOT / 'translations/annotated/reading.md').read_text()

    def test_reading_preserves_complete_bodies_and_printed_paragraphs(self):
        clean = re.sub(r'\[\^[\w-]+\]', '', self.reading)
        blocks = {}
        current = None
        for line in clean.split('## Introduction\n', 1)[1].split('## Terminology guide\n', 1)[0].splitlines():
            match = re.match(r'^\*\*(\d+)\*\* (.+)$', line)
            if match:
                current = int(match[1])
                self.assertNotIn(current, blocks)
                blocks[current] = [match[2]]
            elif line.startswith('## '):
                current = None
            elif current is not None and line.strip():
                blocks[current].append(line)
        self.assertEqual(list(blocks), list(range(1, 16)) + [147])
        defaults = {int(r['section']): r['target_id'] for r in read('edition/manifest.json')['reading_defaults']}
        for number, paragraphs in blocks.items():
            self.assertEqual(' '.join(paragraphs), self.versions[defaults[number]]['body'])
            self.assertEqual(len(paragraphs), 2 if number == 7 else 1)
        self.assertEqual(self.record['counts']['source_rendering_blocks'], 107)
        for body in self.record['unchanged_bodies']:
            self.assertEqual(self.versions[body['target_version']]['body_sha256'], body['target_body_sha256'])

    def test_one_note_sequence_authorship_and_exact_current_anchors(self):
        before, definitions = self.reading.split('## Notes\n', 1)
        calls = re.findall(r'\[\^([\w-]+)\]', before)
        defined = re.findall(r'^\[\^([\w-]+)\]: (.+)$', definitions, re.M)
        notes = self.notes['notes']
        self.assertEqual(calls, [n['id'] for n in notes])
        self.assertEqual([x[0] for x in defined], calls)
        self.assertEqual(len(set(calls)), len(calls))
        self.assertEqual([n['display_number'] for n in notes], list(range(1, len(notes) + 1)))
        self.assertEqual({n['authorship'] for n in notes}, {'translator', 'editor1906', 'humboldt'})
        for note, (_, text) in zip(notes, defined):
            self.assertEqual(text, note['text'] + ' (' + note['attribution'] + ')')
            source = self.units[note['source_unit']]
            target = self.units[note['target_unit']]
            self.assertEqual(source['version_id'], note['source_version'])
            self.assertEqual(target['version_id'], note['target_version'])
            version = self.versions[note['target_version']]
            self.assertEqual(version['body_sha256'], note['target_body_sha256'])
            segment = version['body'][target['start']:target['end']]
            offset = note['anchor']['offset_in_rendering']
            self.assertTrue(0 < offset <= len(segment))
            if note['anchor']['after'] != 'complete source rendering block':
                self.assertTrue(segment[:offset].endswith(note['anchor']['after']))
        editor = next(n for n in notes if n['id'] == 'editor-remusat-page')
        self.assertIn('Within Humboldt', editor['original_anchor'])
        self.assertTrue(editor['display_relocation'])

    def test_previous_artifacts_dispositions_and_trace_survive(self):
        for item in self.record['inputs']:
            self.assertEqual(hashlib.sha256((ROOT / item['path']).read_bytes()).hexdigest(), item['sha256'])
        for key in ['policy', 'notes', 'dispositions', 'renderer']:
            item = self.record[key]
            self.assertEqual(hashlib.sha256((ROOT / item['path']).read_bytes()).hexdigest(), item['sha256'])
        dispositions = read('translations/annotated/dispositions.json')['earlier_notes']
        self.assertEqual(len(dispositions), self.record['counts']['earlier_notes_dispositioned'])
        self.assertTrue(all(d['apparatus_retained'] and d['reason'] for d in dispositions))
        note_ids = {n['id'] for n in self.notes['notes']}
        guide_ids = {g['id'] for g in self.notes['term_guide']}
        for d in dispositions:
            self.assertTrue(set(d['footnote_ids']) <= note_ids)
            self.assertTrue(set(d['guide_ids']) <= guide_ids)
        bundle = read('edition/passages/reader-footnotes-v1/records.json')
        self.assertEqual(set(bundle['tables']), {'evidence', 'decision', 'decision_evidence', 'unit_evidence', 'unit_decision'})
        self.assertIn('revision-text-933d4f42-f708-5542-9ca6-a11ee25ecdf5', bundle['requires_versions'])
        self.assertIn('revision-text-5508d194-4f71-5864-ab79-1eb6cac6d1bc', bundle['requires_versions'])
        db = database.connect()
        try:
            database.migrate(db)
            database.insert_records(db, self.tables)
            for key in ['subjugation-scope', 'editor-remusat-page']:
                note = next(n for n in self.notes['notes'] if n['id'] == key)
                trace = queries.trace(db, note['target_unit'])
                encoded = json.dumps(trace, ensure_ascii=False)
                self.assertIn('D031.note:' + key, encoded)
                self.assertIn('EFootnotes.note:' + key, encoded)
                self.assertIn(note['source_unit'], encoded)
        finally:
            db.close()


if __name__ == '__main__':
    unittest.main()
