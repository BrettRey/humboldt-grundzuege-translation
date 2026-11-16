#!/usr/bin/env python3
"""Render the selected reader notes; preserve the inherited translation bodies."""
import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'translations/annotated/reading.md'


def read(path):
    return json.loads((ROOT / path).read_text())


def passages():
    """Reuse frozen reading inputs, including the declared printed paragraph breaks."""
    result = []
    for folder, section in [('introduction', 'Introduction'), ('part-i-opening', 'Part I')]:
        data = read(f'translations/{folder}/revised.json')
        for p in data['paragraphs']:
            result.append(dict(number=p['number'], section=section,
                               sentences=[(s['source_id'], s['english']) for s in p['sentences']],
                               groups=p['typographic_groups']))
    data = read('translations/difficult-147/revised.json')
    result.append(dict(number=147, section='Separate later pilot',
                       sentences=[('p147:' + s['id'], s['text']) for s in data['sentences']],
                       groups=[list(range(1, len(data['sentences']) + 1))]))
    return result


def render():
    record = read('translations/annotated/notes.json')
    notes = record['notes']
    lines = [
        '# Outlines of the General Type of Language' + ''.join('[^' + n['id'] + ']' for n in notes if n.get('display_at') == 'work_title'),
        '<!-- SUMMARY: Existing translation with selected, attributed footnotes · status: provisional; English and annotation review pending · updated: 2026-11-16 -->',
        '',
        'Wilhelm von Humboldt',
        '',
        '## About this reading',
        '',
        'This selection contains the complete Introduction (numbered passages 1–7), the opening of Part I (8–15), and the separate later pilot 147. Passages 16–146 are not included. The bold numbers follow the 1906 print; they are passage references, not newly invented sections. The printed paragraph breaks are retained, including the two paragraphs within passage 7.',
        '',
        'The provisional source is Albert Leitzmann’s 1906 edition, *Gesammelte Schriften*, volume V, pp. 364–372 and 469–470. Drechsel (2024:155) reports cancellation of the first seven paragraphs; the manuscript marks, their extent and their editorial meaning have not been independently verified. This qualification concerns 1–7 and is not extended to 8–15 or 147. See [the textual-basis record](../../docs/preparation/textual-basis-options.md).',
        '',
        'The English wording is preserved from the existing translations. Footnotes ending **(Humboldt)** translate his own notes; **(1906 Ed.)** identifies the print editor’s apparatus; **(Trans.)** identifies our commentary. One Arabic sequence covers all three. The [short terminology guide](#terminology-guide) explains recurring distinctions. These provisional notes and the English await review; English readability review does not establish fidelity to the German.',
        '',
        'The [note records](../../translations/annotated/notes.json) retain stable IDs, exact source/English anchors and evidence limits. The [annotation report](../../translations/annotated/report.md) links all earlier reading copies, alternatives and audits. The historical source includes evaluative scales and labels for peoples and languages; those claims remain Humboldt’s, with focused qualifications in the notes.',
        '',
    ]
    used = {n['id'] for n in notes if n.get('display_at') == 'work_title'}
    for p in passages():
        if p['number'] == 1:
            lines += ['## Introduction', '']
        elif p['number'] == 8:
            lines += ['## I. Presentation of the American languages in themselves and in their distinctive character', '']
        elif p['number'] == 147:
            lines += ['## Separate later pilot: passage 147', '',
                      'This later passage is included as a separate test of the translation method. It does not follow passage 15 in the source. Its opening refers back to the preceding argument, which is outside this selection.', '']
        sentences = []
        for sid, text in p['sentences']:
            selected = [n for n in notes if n['source_id'] == sid and n.get('display_at') != 'work_title']
            # Descending insertion offsets leave every original character in place.
            for offset in sorted({n['anchor']['offset_in_rendering'] for n in selected}, reverse=True):
                at = [n for n in selected if n['anchor']['offset_in_rendering'] == offset]
                text = text[:offset] + ''.join('[^' + n['id'] + ']' for n in at) + text[offset:]
                used.update(n['id'] for n in at)
            sentences.append(text)
        for i, group in enumerate(p['groups']):
            prefix = '**' + str(p['number']) + '** ' if i == 0 else ''
            lines += [prefix + ' '.join(sentences[n - 1] for n in group), '']
    lines += ['## Terminology guide', '',
              'These are local reading aids. The [full termbase](../../docs/preparation/termbase.md) retains contextual choices, alternatives and source attestations.', '']
    for item in record['term_guide']:
        lines += ['**' + item['term'] + '** (' + ', '.join('*' + g + '*' for g in item['German']) + '). ' + item['text'], '']
    lines += ['## Notes', '']
    for note in notes:
        lines += ['[^' + note['id'] + ']: ' + note['text'] + ' (' + note['attribution'] + ')', '']
    if used != {n['id'] for n in notes}:
        raise ValueError('Unattached note')
    return '\n'.join(lines)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true', help='explicitly replace the generated reading')
    args = parser.parse_args()
    text = render()
    if args.write:
        if OUTPUT.exists() and re.search(r'\{(?:>>|\+\+|--|~~|==)', OUTPUT.read_text()):
            raise SystemExit('Reading contains review markup; preserve and resolve it before regenerating.')
        OUTPUT.write_text(text)
        print('Wrote', OUTPUT.relative_to(ROOT))
    elif not OUTPUT.exists() or OUTPUT.read_text() != text:
        raise SystemExit('Reading differs from its records; inspect differences before using --write.')
    else:
        print('Reading matches its note records and frozen English inputs.')
