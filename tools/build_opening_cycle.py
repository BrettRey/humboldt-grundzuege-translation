#!/usr/bin/env python3
"""Build the reviewed-design trial store with this single translation cycle.

Requires the original PDFs and the six sealed cycle inputs. Does not overwrite
an existing database. Run from any directory; no third-party packages needed.
"""
import argparse
import json
from pathlib import Path
import re

import alignment_store as store

ROOT = store.ROOT
CYCLE = ROOT / 'translations/opening-001'
GERMAN = 'grundzuege-001-v1'
FINAL = 'en-revised-v2'


def load(name):
    return json.loads((CYCLE / name).read_text(encoding='utf-8'))


def add_english(db, version_id, records, source_path, source_hash, provenance, *,
                source_version=GERMAN, title='Grundzüge §1 — provisional English',
                locator='English renderings of g:s1–g:s7',
                scope='Complete paragraph, seven source-sentence rendering blocks'):
    body = ' '.join(r['english'] for r in records)
    store.insert(db, 'text_version', dict(
        id=version_id, title=title, language='en', body=body,
        body_sha256=store.sha256(body.encode('utf-8')), source_path=source_path,
        source_sha256=source_hash, locator=locator,
        transcription_status='generated_translation_not_certified', provenance=provenance))
    analysis_id = version_id + ':layout'
    store.insert(db, 'analysis', dict(id=analysis_id, version_id=version_id,
        method='Recorded source-sentence renderings; English sentences split at terminal punctuation; written tokens use the prototype convention.',
        scope=scope, status='proposed', supersedes=None))
    para = version_id + ':p1'
    store.add_unit(db, para, analysis_id, version_id, 'paragraph', '§1', (0, len(body)))
    offset = 0
    for record in records:
        text = record['english']
        block = version_id + ':' + record['id']
        store.add_unit(db, block, analysis_id, version_id, 'rendering', record['id'],
                       (offset, offset + len(text)), para,
                       'Rendering of one German sentence; may contain several English sentences.')
        # No abbreviations occur in these checked inputs. This is a local rule,
        # not a general-purpose English sentence parser.
        for n, match in enumerate(re.finditer(r'[^.!?]+[.!?](?=\s|$)', text), 1):
            a, b = match.span()
            while a < b and text[a].isspace():
                a += 1
            sentence_id = block + f':s{n}'
            store.add_unit(db, sentence_id, analysis_id, version_id, 'sentence',
                           f'English sentence {n} in {record["id"]}', (offset+a, offset+b), block)
            for w, (wa, wb) in enumerate(store.word_spans(text[a:b]), 1):
                store.add_unit(db, sentence_id + f':w{w:03}', analysis_id, version_id,
                               'word', f'written token {w}', (offset+a+wa, offset+a+wb), sentence_id)
        group(db, 'sentence:' + block, version_id,
              [record['id']], [r[0] for r in db.execute(
                  'SELECT id FROM unit WHERE parent_id=? AND kind=? ORDER BY start', (block, 'sentence'))],
              'source_sentence_rendering', 'Proposed rendering, not certified semantic equivalence.',
              left_version=source_version)
        offset += len(text) + 1
    store.insert(db, 'unit_evidence', dict(unit_id=para, evidence_id='E01'))
    store.insert(db, 'unit_decision', dict(unit_id=para, decision_id='D001'))


def group(db, id, right_version, left_ids, right_ids, relation, note, *, left_version=GERMAN):
    store.insert(db, 'alignment', dict(id=id, left_version=left_version,
        right_version=right_version, relation=relation, note=note, status='draft'))
    for side, members in [('left', left_ids), ('right', right_ids)]:
        for unit in members:
            store.insert(db, 'alignment_member', dict(alignment_id=id, side=side, unit_id=unit))
    db.execute("UPDATE alignment SET status='proposed' WHERE id=?", (id,))


def build(db):
    record = load('record.json')
    for path, fingerprint in record['input_sha256'].items():
        store.verify_file(path, fingerprint)
    store.build(db)
    candidates = load('candidates.json')['candidates']
    audits, final, decisions = load('audits.json'), load('revised.json'), load('decisions.json')
    source_hash = lambda name: record['input_sha256']['translations/opening-001/' + name]
    with db:
        for candidate in candidates:
            add_english(db, 'en-' + candidate['id'] + '-v1', candidate['sentences'],
                'translations/opening-001/candidates.json', source_hash('candidates.json'),
                candidate['model'] + '; isolated fresh candidate. ' + final['source_status'])
        add_english(db, 'en-synthesis-v1', audits['audited_text']['sentences'],
            'translations/opening-001/audits.json', source_hash('audits.json'),
            'Coordinator synthesis assessed by both audits, superseded by en-revised-v2. ' + final['source_status'])
        add_english(db, FINAL, final['sentences'],
            'translations/opening-001/revised.json', source_hash('revised.json'),
            'Coordinator revision after one model-audit cycle; supersedes en-synthesis-v1. ' + final['source_status'])
        store.insert(db, 'analysis', dict(id='final-clause-links', version_id=FINAL,
            method='Coordinator exact-quote target spans; proposed semantic links, mechanically anchored.',
            scope='All 20 proposed German anchors, including noncontiguous English correspondence',
            status='proposed', supersedes=None))
        final_body = db.execute('SELECT body FROM text_version WHERE id=?', (FINAL,)).fetchone()[0]
        source_annotations = {r['id']: r for r in json.loads(store.PACKET.read_text())['annotations']}
        for row in load('alignments.json')['clauses']:
            source_record = source_annotations[row['source_id']]
            block = db.execute('SELECT start,end FROM unit WHERE id=?', (FINAL+':'+source_record['sentence_id'],)).fetchone()
            targets = []
            for n, quote in enumerate(row['target_quotes'], 1):
                span = store.anchor(final_body, quote, block['start'], block['end'])
                target = 'final:' + row['source_id'] + f':{n}'
                store.add_unit(db, target, 'final-clause-links', FINAL, 'correspondence_span',
                               row['source_id'], span, note=row['note'])
                targets.append(target)
            group(db, 'clause:' + row['source_id'], FINAL, [row['source_id']], targets,
                  'proposed_clause_correspondence', row['note'])
        # A real lexical cluster: two related German compound/forms map to four
        # English words. Members are grouped, not forced into one-to-one links.
        word_id = lambda version, text, source_sentence=None: unique_word(db, version, text, source_sentence)
        group(db, 'lexical:distinctiveness', FINAL,
              [word_id(GERMAN, w) for w in ('Nationaleigenthümlichkeit', 'Eigenthümlichkeiten')],
              [word_id(FINAL, w, sid) for w, sid in
               [('national', 'g:s4'), ('distinctiveness', 'g:s4'), ('distinctive', 'g:s6'), ('traits', 'g:s6')]],
              'related_term_cluster', 'Provisional related renderings; no one-to-one morphology asserted.')
        source = db.execute('SELECT * FROM text_version WHERE id=?', (GERMAN,)).fetchone()
        store.insert(db, 'evidence', dict(id='E-CYCLE-PRINT', source_path=source['source_path'],
            source_sha256=source['source_sha256'], locator=source['locator'], excerpt='',
            statement='Checked printed German supplies the wording for these interpretive choices; interpretation and authorial finality remain open.',
            quote_status='scan_checked_transcription', claim_status='translation_interpretation_provisional'))
        for choice in decisions['choices']:
            store.insert(db, 'decision', dict(id=choice['id'], question=choice['term'],
                resolution=choice['choice'] + '. ' + choice['reason'] + ' Alternatives: ' + '; '.join(choice['alternatives']),
                authority='Coordinator under D002; English review pending. Model judgments are evidence, not approval.', status='provisional'))
            store.insert(db, 'decision_evidence', dict(decision_id=choice['id'], evidence_id='E-CYCLE-PRINT'))
            for source_id in choice['source_ids']:
                for unit in (source_id, FINAL + ':' + source_id):
                    store.insert(db, 'unit_decision', dict(unit_id=unit, decision_id=choice['id']))
                    db.execute('''INSERT INTO unit_evidence VALUES (?, ?)
                        ON CONFLICT(unit_id, evidence_id) DO NOTHING''', (unit, 'E-CYCLE-PRINT'))
        for auditor in audits['audits']:
            for finding in auditor['findings']:
                evidence_id = 'AUDIT:' + auditor['id'] + ':' + finding['id']
                store.insert(db, 'evidence', dict(id=evidence_id,
                    source_path='translations/opening-001/audits.json', source_sha256=source_hash('audits.json'),
                    locator=auditor['model'] + ', ' + finding['id'] + ', pre-revision synthesis',
                    excerpt=finding['english_quote'], statement=finding['finding'],
                    quote_status='exact_source_and_English_anchors_checked',
                    claim_status='model_judgment_on_pre_revision_text'))
                disposition = next(d for d in decisions['audit_dispositions']
                    if d['auditor']==auditor['id'] and d['finding']==finding['id'])
                # Shared findings can support the same decision. The precise
                # disposition is retained in the sealed decisions input.
                store.insert(db, 'decision_evidence', dict(decision_id=disposition['decision_id'], evidence_id=evidence_id))


def unique_word(db, version, text, source_sentence=None):
    sql = "SELECT id FROM unit_text WHERE version_id=? AND kind='word' AND text=?"
    params = [version, text]
    if source_sentence is not None:
        sql += ' AND start >= (SELECT start FROM unit WHERE id=?) AND end <= (SELECT end FROM unit WHERE id=?)'
        params += [version + ':' + source_sentence] * 2
    rows = db.execute(sql, params).fetchall()
    if len(rows) != 1:
        raise ValueError(f'word is missing or ambiguous: {version} {text}')
    return rows[0][0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=Path, default=ROOT / 'tmp/opening-001-cycle.sqlite')
    args = parser.parse_args()
    args.db.parent.mkdir(parents=True, exist_ok=True)
    try:
        with args.db.open('xb'):
            pass
    except FileExistsError:
        parser.error('output exists; choose a fresh --db path')
    db = store.connect(args.db)
    try:
        build(db)
        print(json.dumps(store.summary(db), ensure_ascii=False, indent=2))
    except Exception:
        db.close()
        args.db.unlink()
        raise
    finally:
        db.close()


if __name__ == '__main__':
    main()
