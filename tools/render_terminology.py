#!/usr/bin/env python3
"""Render the human-readable register and locator index from preparation records."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'sources/terminology'
DOCS = ROOT / 'docs/preparation'


def anchor(eid):
    return eid.replace(':', '-').lower()


def render():
    evidence = json.loads((DATA / 'evidence.json').read_text())
    entries = json.loads((DATA / 'register.json').read_text())['entries']
    text = ['# Shared terminology register',
        '<!-- SUMMARY: Conditional English rendering rules with source evidence; discovery counts are not sense classifications · status: provisional preparation v1 · updated: 2026-11-15 -->',
        '', 'Use these rules by context, bearer and contrast. They are working norms for a provisional research translation, not a certified glossary. ' 
        'The [argument map](argument-map.md) explains their place in the whole work; the [source controls](primary-and-secondary-controls.md) separate primary usage, later scholarship and historical dictionary ranges. ' 
        'Every evidence link gives a source, exact locator and verification status. Structured rules and the full evidence statements remain in ' 
        '[register.json](../../sources/terminology/register.json) and [evidence.json](../../sources/terminology/evidence.json).',
        '', 'The database indexes every written-token candidate on printed 364–473. Family matches are deliberately broad and overlapping; ' 
        'they include header candidates and apparatus and do not assign a sense to every occurrence. The rules below are based on representative contexts, not exhaustive manual sense coding.',
        '', '## Quick navigation', '', '| Entry | German forms | English candidates |', '|---|---|---|']
    for a in entries:
        text.append(f"| [{a['id']}](#{a['id'].lower()}) | {' / '.join(a['forms'])} | {' / '.join(a['candidates'])} |")
    for a in entries:
        refs = ', '.join(f"[{eid.removeprefix('prep:')}](evidence-index.md#{anchor(eid)})" for eid in a['evidence_ids'])
        text += ['', f"<a id=\"{a['id'].lower()}\"></a>", f"## {a['id']} — {' / '.join(a['forms'])}", '',
            '**Candidates:** ' + ' / '.join(a['candidates']) + '.', '', a['rule'], '', '**Exceptions:** ' + a['exceptions'], '',
            '**Limit:** ' + a['limit'], '', '**Evidence:** ' + refs + '.']
    text += ['', '## Audit and use', '',
        'Two readers checked the proposed register against their assigned primary and secondary material. Six findings were accepted: ' 
        'the two metaphor subjects, supplementation by speakers and hearers, the independent-anchor condition for word order, Formalität’s claimed effect, ' 
        'and missing occurrence-specific support for feeling/Geltung and Selbstbedeutung. ' 
        'Corrections and bounded source checks are recorded in [the audit dispositions](../../sources/terminology/register-audit.json). ' 
        'T34 was then added by the coordinator from the already checked opening packet to make the convergence/mixture rule explicit; it was not part of those audits.',
        '', 'Apply a rule only after checking the new source passage. If a local occurrence conflicts, record an exception or a new decision with evidence. ' 
        'Preserve earlier English versions. The [§§1–2 reassessment](reassessment-001-002.md) retains their present wording.']
    (DOCS / 'terminology-register.md').write_text('\n'.join(text) + '\n')
    text = ['# Evidence locator index', '',
        'These identifiers support the register. A checked image context is distinct from a certified complete transcription. ' 
        'OCR-only quotations retain extraction errors. Modern commentary is paraphrased. The [JSON records](../../sources/terminology/evidence.json) hold statements, excerpts, issues, hashes and reader provenance.',
        '', '| ID | Source and locator | Verification |', '|---|---|---|']
    for a in evidence:
        path = a['source_path']; label = Path(path).stem
        url = a.get('url', '../../' + path)
        loc = a['locator'].replace('|', '\\|')
        status = a['verification'].replace('|', '\\|')
        text.append(f"| <a id=\"{anchor(a['id'])}\"></a>{a['id'].removeprefix('prep:')} | [{label}]({url}), {loc} | {status} |")
    (DOCS / 'evidence-index.md').write_text('\n'.join(text) + '\n')


if __name__ == '__main__':
    render()
