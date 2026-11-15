#!/usr/bin/env python3
"""Build a fresh cumulative §1–§2 trial store from sealed inputs."""
import argparse
import json
from pathlib import Path

import alignment_store as store
import build_opening_cycle as opening

CYCLE = store.ROOT / 'translations/paragraph-002'
PACKET = store.ROOT / 'sources/annotations/paragraph-002.json'
GERMAN = 'grundzuege-002-v1'
FINAL = 'en2-revised-v2'


def load(name):
    return json.loads((CYCLE / name).read_text(encoding='utf-8'))


def build(db):
    record = load('record.json')
    for path, fingerprint in record['input_sha256'].items():
        store.verify_file(path, fingerprint)
    opening.build(db)
    store.build(db, PACKET, initialize_schema=False)
    audits, final, decisions = load('audits.json'), load('revised.json'), load('decisions.json')
    source_hash = lambda name: record['input_sha256']['translations/paragraph-002/' + name]
    with db:
        versions = [('en2-' + c['id'] + '-v1', c['sentences'], 'candidates.json',
                     c['model'] + '; fresh isolated candidate.') for c in load('candidates.json')['candidates']]
        versions += [('en2-synthesis-v1', audits['audited_text']['sentences'], 'audits.json',
                      'Coordinator pre-audit synthesis; superseded by en2-revised-v2.'),
                     (FINAL, final['sentences'], 'revised.json',
                      'Coordinator revision after one audit cycle; supersedes en2-synthesis-v1.')]
        for version_id, sentences, filename, provenance in versions:
            opening.add_english(db, version_id, sentences,
                'translations/paragraph-002/' + filename, source_hash(filename),
                provenance + ' ' + final['source_status'], source_version=GERMAN,
                title='Grundzüge §2 — provisional English',
                locator='English renderings of g2:s1–g2:s3',
                scope='Complete §2, three source-sentence rendering blocks')
        store.insert(db, 'analysis', dict(id='p2-final-clause-links', version_id=FINAL,
            method='Coordinator proposed semantic correspondences, exact target spans checked.',
            scope='All 11 proposed source anchors', status='proposed', supersedes=None))
        body = db.execute('SELECT body FROM text_version WHERE id=?', (FINAL,)).fetchone()[0]
        source_anchors = {a['id']: a for a in json.loads(PACKET.read_text())['annotations']}
        for row in load('alignments.json')['clauses']:
            source = source_anchors[row['source_id']]
            block = db.execute('SELECT start,end FROM unit WHERE id=?', (FINAL+':'+source['sentence_id'],)).fetchone()
            targets = []
            for n, quote in enumerate(row['target_quotes'], 1):
                target = 'p2-final:' + row['source_id'] + f':{n}'
                store.add_unit(db, target, 'p2-final-clause-links', FINAL, 'correspondence_span',
                    row['source_id'], store.anchor(body, quote, block['start'], block['end']), note=row['note'])
                targets.append(target)
            opening.group(db, 'clause:'+row['source_id'], FINAL, [row['source_id']], targets,
                'proposed_clause_correspondence', row['note'], left_version=GERMAN)
        for lex in load('alignments.json')['lexical_groups']:
            left = [word(db, GERMAN, w['sentence_id'], w['text']) for w in lex['source']]
            right = [word(db, FINAL, w['sentence_id'], w['text']) for w in lex['target']]
            opening.group(db, lex['id'], FINAL, left, right, 'related_term_cluster', lex['note'], left_version=GERMAN)
        for choice in decisions['choices']:
            store.insert(db, 'decision', dict(id=choice['id'], question=choice['term'],
                resolution=choice['choice']+'. '+choice['reason']+' Alternatives: '+'; '.join(choice['alternatives']),
                authority='Coordinator under D004; provisional source interpretation; English review pending.', status='provisional'))
            store.insert(db, 'decision_evidence', dict(decision_id=choice['id'], evidence_id='E-P2-PRINT'))
            for sid in choice['source_ids']:
                for uid in (sid, FINAL+':'+sid):
                    store.insert(db, 'unit_decision', dict(unit_id=uid, decision_id=choice['id']))
                    db.execute('''INSERT INTO unit_evidence VALUES (?,?)
                        ON CONFLICT(unit_id,evidence_id) DO NOTHING''', (uid, 'E-P2-PRINT'))
        for auditor in audits['audits']:
            for finding in auditor['findings']:
                evidence_id = 'P2-AUDIT:'+auditor['id']+':'+finding['id']
                store.insert(db, 'evidence', dict(id=evidence_id,
                    source_path='translations/paragraph-002/audits.json', source_sha256=source_hash('audits.json'),
                    locator=auditor['model']+', '+finding['id']+', pre-revision synthesis',
                    excerpt=finding['english_quote'], statement=finding['finding'],
                    quote_status='exact_source_and_English_anchors_checked',
                    claim_status='model_judgment_on_pre_revision_text'))
                disposition = next(d for d in decisions['audit_dispositions']
                    if d['auditor']==auditor['id'] and d['finding']==finding['id'])
                store.insert(db, 'decision_evidence', dict(decision_id=disposition['decision_id'], evidence_id=evidence_id))


def word(db, version, sentence, text):
    uid = sentence if version==GERMAN else version+':'+sentence
    block = db.execute('SELECT start,end FROM unit WHERE id=?', (uid,)).fetchone()
    rows = db.execute("SELECT id FROM unit_text WHERE version_id=? AND kind='word' AND text=? AND start>=? AND end<=?",
                      (version,text,block['start'],block['end'])).fetchall()
    if len(rows)!=1:
        raise ValueError(f'word is missing or ambiguous: {version} {sentence} {text}')
    return rows[0][0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=Path, default=store.ROOT/'tmp/paragraph-002-cycle.sqlite')
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
        print(json.dumps(store.summary(db),ensure_ascii=False,indent=2))
    except Exception:
        db.close()
        args.db.unlink()
        raise
    finally:
        db.close()


if __name__=='__main__':
    main()
