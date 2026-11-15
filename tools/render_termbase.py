#!/usr/bin/env python3
"""Render a navigable Markdown termbase from the validated individual records."""
import json
import os
from pathlib import Path

from assemble_termbase import key, slug

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'sources/terminology/v2'
DOC=ROOT/'docs/preparation'


def group(headword):
    initial=slug(headword)[0]
    if initial<='e':return 'a-e'
    if initial<='k':return 'f-k'
    if initial<='r':return 'l-r'
    return 's-z'


def link(path,from_path):
    return os.path.relpath(ROOT/path,from_path.parent)


def locator(e):
    work='GS V' if e['source_path']=='sources/raw/gs-v-1906.pdf' else 'GS VIII' if 'gs-08' in e['source_path'] else Path(e['source_path']).stem
    return f"{work}:{e['printed_page']} / PDF {e['pdf_page']}"+(f" / scan leaf {e['scan_leaf']}" if e.get('scan_leaf') else '')


def render(catalog_path=DATA/'termbase.json'):
    c=json.loads(catalog_path.read_text());terms=c['terms']
    if c['issues']:raise ValueError('render only a validated catalog')
    (DOC/'v2').mkdir(exist_ok=True)
    main=DOC/'termbase.md'
    senses=sum(len(t['senses']) for t in terms)
    attestations=sum(len(s['evidence']) for t in terms for s in t['senses'])
    lines=['# Humboldt terminology: individual terms and contextual uses', '',
        'This termbase gives separate records for source terms, compounds, phrases and consequential contextual vocabulary. '
        'Observed inflections and spelling variants are listed within a record. Contextual uses are distinguished where the local contribution or contrast changes; '
        'their number is not a claim about a fixed dictionary polysemy. All proposed English remains provisional.', '',
        f'It contains **{len(terms):,} headword records, {senses:,} contextual sense/use groups and {attestations:,} primary evidence records**. '
        'These include contextual vocabulary; several records can cite the same passage. '
        'Supporting translation-policy terms are labelled separately. The earlier 34-group register remains preserved as a historical input.', '',
        '[Coverage and accuracy report](v2/coverage-report.md) · [Store guide](v2/store-guide.md) · '
        '[Structured termbase](../../sources/terminology/v2/termbase.json)', '',
        '## Find a term', '',
        'Use the alphabetical index below or search by headword/observed form in SQLite. '
        'The detailed records give the English choices, local definition, rendering rule, caution, checked quotation and exact source locator. '
        'The source images and original OCR remain unchanged.', '',
        'Some consequential choices to consult first:', '',
        '- [Form](v2/terms-f-k.md#form): what has form, and its local relation to matter or activity.',
        '- [Verstand](v2/terms-s-z.md#verstand) and [Vermögen](v2/terms-s-z.md#vermoegen): faculty, idiom and bearer-conditioned English.',
        '- [Grammatical form](v2/terms-f-k.md#grammatische-form) and [Hinzudenken](v2/terms-f-k.md#hinzudenken): audible indication versus supplying a relation in thought.',
        '- [Satz](v2/terms-s-z.md#satz), [Periode](v2/terms-l-r.md#periode) and [Weltansicht](v2/terms-s-z.md#weltansicht): local units and viewpoints without imported modern equations.', '',
        '| German headword | English candidates across cited uses | Uses |', '|---|---|---|']
    for t in terms:
        renderings=list(dict.fromkeys(r for s in t['senses'] for r in s['renderings']))
        target=f"v2/terms-{group(t['headword'])}.md#{slug(t['headword'])}"
        lines.append(f"| [{t['headword']}]({target}) | {' / '.join(renderings).replace('|',' / ')} | {len(t['senses'])} |")
    lines += ['', '## Reading the evidence', '',
        'Checked wording is kept in a separate excerpt collection from the OCR locator window. '
        'An image check is model-assisted source verification, not independent specialist validation. '
        'Quoted content is an attestation for the specified local interpretation, not evidence that every matching token has that sense.', '',
        'Historical-dictionary entries and primary/secondary parallels are comparative controls. They are attached explicitly where relevant, '
        'rather than copied from an old group onto all its members. A dictionary range does not override Humboldt’s local contrast.', '',
        'A candidate disposition reports why a surface form was included, treated as a variant, or excluded from terminology. '
        'It does not silently remove that word from the searchable source or certify all of its occurrences. '
        'The coverage report gives the selection criteria, reviewed remainder, source issues and audit dispositions.']
    main.write_text('\n'.join(lines)+'\n')
    controls={x['id']:x for x in c.get('controls',[])}
    by_control={}
    for item in c.get('control_links',[]):by_control.setdefault(item['lexeme_id'],[]).append(item)
    for bucket,title in [('a-e','A–E'),('f-k','F–K'),('l-r','L–R'),('s-z','S–Z')]:
        path=DOC/f'v2/terms-{bucket}.md';lines=[f'# Terms {title}', '', '[Back to the term index](../termbase.md)', '']
        for t in terms:
            if group(t['headword'])!=bucket:continue
            lines += [f'<a id="{slug(t["headword"])}"></a>',f"## {t['headword']}", '',
                f"**Scope:** {t['scope']}. **Domains:** {', '.join(t['domains'])}. **Role:** {', '.join(r.replace('_',' ') for r in t['roles'])}.", '',
                ('**Checked/rejoined source forms:** '+', '.join(t['checked_forms'])+'.') if t['checked_forms'] else 'The editorial headword expands an elliptical source expression; its actual parts remain separately anchored below.', '']
            for n,s in enumerate(t['senses'],1):
                lines += [f"### {n}. {s['label']}", '', '**English:** '+' / '.join(s['renderings'])+'.', '',s['definition'], '', '**Rule:** '+s['rule'], '']
                if s['caution']:lines += ['**Caution:** '+s['caution'], '']
                if len(s['uses'])>1:
                    lines+=['**Contextual uses retained within this sense:**', '']
                    for use in s['uses']:
                        ps=sorted({e['printed_page'] for e in s['evidence'] if e['use_id']==use['id']})
                        lines.append('- Printed '+', '.join(map(str,ps))+': '+use['definition']+' '+use['rule'])
                    lines.append('')
                for e in s['evidence']:
                    url=link(e['source_path'],path)+f"#page={e['pdf_page']}"
                    role={'direct_occurrence':'direct occurrence','supporting_context':'supporting context','word_part':'page-divided word fragment','elliptical_expression':'elliptical phrase'}[e['evidence_role']]
                    lines += [f"**Evidence ({role}):** [{locator(e)}]({url}); {e['text_layer'].replace('_',' ')}; {e['verification']}.", '', '> '+e['checked_quote'], '']
                    if e.get('issue'):lines += ['**Reading note:** '+e['issue'], '']
                    if e.get('selection_note'):lines += ['**Linkage note:** '+e['selection_note'], '']
            if t['relations']:
                lines += ['**Relations:** '+ '; '.join((f"[{r['target_label']}](terms-{group(r['target_label'])}.md#{slug(r['target_label'])})" if r.get('target_id') else r['target_label'])+' ('+r['type']+': '+r['reason']+')' for r in t['relations'])+'.', '']
            for item in by_control.get(t['id'],[]):
                control=controls[item['control_id']]
                url=control.get('url') or link(control['source_path'],path)
                lines += [f"**Comparative control:** [{control['locator']}]({url}). {control['statement']} {item['comment']}", '']
        path.write_text('\n'.join(lines)+'\n')


if __name__=='__main__':render()
