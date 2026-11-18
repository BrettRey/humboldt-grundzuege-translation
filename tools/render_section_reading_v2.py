#!/usr/bin/env python3
"""Render a frozen section translation and its projected, version-anchored notes."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))


def render(folder):
    from humboldt.ingest import load
    folder = Path(folder).resolve()
    folder.relative_to(ROOT / 'translations')
    def read(name):
        return json.loads((folder / name).read_text())
    source, final, annotations = read('source.json'), read('revised.json'), read('notes.json')
    tables, _ = load(ROOT)
    evidence = {r['id']: r for r in tables['evidence']}
    prefix = final['annotation_evidence_prefix']
    for collection, kind in [(annotations['notes'], 'note'), (annotations['term_guide'], 'guide')]:
        for item in collection:
            item['text'] = evidence[prefix + kind + ':' + item['id']]['excerpt']
    ancillary = {s['source_id']: s['english'] for s in final['ancillary']}
    reading = final['reading']
    lines = ['# ' + reading['title'], '', reading['byline'], '', '## About this reading', '']
    review_path = folder / 'review.json'
    review = json.loads(review_path.read_text()) if review_path.exists() else {}
    for paragraph in reading['about']:
        if review.get('completed') and paragraph.startswith('**Review:**'):
            paragraph = review['reading_status_text']
        lines += [paragraph, '']
    used = set()

    def with_notes(text, source_id, body_hash):
        notes = [n for n in annotations['notes'] if n['source_id'] == source_id]
        for note in notes:
            if note['target_body_sha256'] != body_hash:
                raise ValueError('Note needs semantic reattachment: ' + note['id'])
            offset = note['anchor']['offset_in_rendering']
            fragment = note['anchor']['after']
            if not 0 <= offset <= len(text) or (fragment != 'complete rendering block' and not text[:offset].endswith(fragment)):
                raise ValueError('Note anchor differs: ' + note['id'])
        for offset in sorted({n['anchor']['offset_in_rendering'] for n in notes}, reverse=True):
            selected = [n for n in notes if n['anchor']['offset_in_rendering'] == offset]
            text = text[:offset] + ''.join('[^' + n['id'] + ']' for n in selected) + text[offset:]
            used.update(n['id'] for n in selected)
        return text

    for paragraph in final['paragraphs']:
        n = paragraph['number']
        for heading in source['headings']:
            if heading['before'] == n:
                level = final['reading']['heading_levels'][heading['id']]
                title = ancillary[heading['id']]
                title_hash = hashlib.sha256(title.encode()).hexdigest()
                lines += ['#' * level + ' ' + with_notes(title, heading['id'], title_hash), '']
        body = ' '.join(s['english'] for s in paragraph['sentences'])
        body_hash = hashlib.sha256(body.encode()).hexdigest()
        texts = [with_notes(s['english'], s['source_id'], body_hash) for s in paragraph['sentences']]
        for i, group in enumerate(paragraph['typographic_groups']):
            lines += [('**' + str(n) + '** ' if i == 0 else '') + ' '.join(texts[k - 1] for k in group), '']
    if used != {x['id'] for x in annotations['notes']}:
        raise ValueError('Unattached note')
    lines += ['## Terminology guide', '', 'These local reading aids follow the [conditional termbase](../../docs/preparation/termbase.md); they do not impose invariant English equivalents on every German occurrence.', '']
    for entry in annotations['term_guide']:
        lines += ['**' + entry['term'] + '** (' + ', '.join('*' + g + '*' for g in entry['German']) + '). ' + entry['text'], '']
    lines += ['## Notes', '']
    for note in annotations['notes']:
        lines += ['[^' + note['id'] + ']: ' + note['text'] + ' (' + note['attribution'] + ')', '']
    return '\n'.join(lines)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    output = args.folder / 'reading.md'
    text = render(args.folder)
    if args.write:
        if output.exists() and re.search(r'\{(?:>>|\+\+|--|~~|==)', output.read_text()):
            raise SystemExit('Preserve and resolve review markup before regenerating.')
        output.write_text(text)
        print('Wrote', output)
    elif not output.exists() or output.read_text() != text:
        raise SystemExit('Reading differs from its frozen text and projected annotations.')
    else:
        print('Reading matches its frozen text and projected annotations.')
