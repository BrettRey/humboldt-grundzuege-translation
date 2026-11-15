#!/usr/bin/env python3
"""Build/query the provisional terminology store; never overwrite a snapshot."""
import argparse
import csv
import json
from pathlib import Path
import re
import sqlite3

import alignment_store as store
import build_terminology_index as index

ROOT = store.ROOT
DATA = ROOT / 'sources/terminology'


def load(name):
    return json.loads((DATA / name).read_text(encoding='utf-8'))


def build(db):
    index.build(db)
    evidence = load('evidence.json')
    register = load('register.json')
    hashes = {}
    # Validate every held source before adding interpretive records.
    for item in evidence:
        path = item['source_path']
        if path not in hashes:
            hashes[path] = store.sha256((ROOT / path).read_bytes())
        if hashes[path] != item['source_sha256']:
            raise ValueError('evidence source changed: ' + path)
        if item.get('record_path'):
            path = item['record_path']
            if path not in hashes:
                hashes[path] = store.sha256((ROOT / path).read_bytes())
            if hashes[path] != item['record_sha256']:
                raise ValueError('reader record changed: ' + path)
    with db:
        db.executescript('''
            CREATE TABLE preparation_input (
                path TEXT PRIMARY KEY NOT NULL, sha256 TEXT NOT NULL);
            CREATE TABLE term_entry (
                id TEXT PRIMARY KEY NOT NULL, decision_id TEXT NOT NULL REFERENCES decision(id),
                forms_json TEXT NOT NULL, candidates_json TEXT NOT NULL,
                rule TEXT NOT NULL, exceptions TEXT NOT NULL, confidence TEXT NOT NULL,
                limitation TEXT NOT NULL);
            CREATE TABLE term_entry_family (
                entry_id TEXT NOT NULL REFERENCES term_entry(id),
                family_id TEXT NOT NULL REFERENCES term_family(id),
                PRIMARY KEY(entry_id, family_id));
            CREATE TABLE term_entry_evidence (
                entry_id TEXT NOT NULL REFERENCES term_entry(id),
                evidence_id TEXT NOT NULL REFERENCES evidence(id),
                PRIMARY KEY(entry_id, evidence_id));
            CREATE TABLE evidence_detail (
                evidence_id TEXT PRIMARY KEY NOT NULL REFERENCES evidence(id),
                metadata_json TEXT NOT NULL);
        ''')
        for name in ('register.json', 'evidence.json', 'preserved-inputs.json',
                     'search-pages.json', 'lexicon-retrieval.json', 'recovered-pages.json',
                     'coverage.json', 'register-audit.json'):
            path = DATA / name
            store.insert(db, 'preparation_input', dict(path=str(path.relative_to(ROOT)), sha256=store.sha256(path.read_bytes())))
        for item in evidence:
            store.insert(db, 'evidence', dict(id=item['id'], source_path=item['source_path'],
                source_sha256=item['source_sha256'], locator=item['locator'], excerpt=item.get('quote', ''),
                statement=item['statement'], quote_status=item['quote_status'], claim_status=item['claim_status']))
            store.insert(db, 'evidence_detail', dict(evidence_id=item['id'], metadata_json=json.dumps(item, ensure_ascii=False)))
            p = item.get('printed_page')
            if item['source_path'] == 'sources/raw/gs-v-1906.pdf' and isinstance(p, int) and 364 <= p <= 473:
                store.insert(db, 'unit_evidence', dict(unit_id=f'whole:p{p}', evidence_id=item['id']))
        for entry in register['entries']:
            did = 'D007.' + entry['id']
            store.insert(db, 'decision', dict(id=did, question='How should ' + ' / '.join(entry['forms']) + ' be rendered?',
                resolution=entry['rule'] + ' Exceptions: ' + entry['exceptions'] + ' Limit: ' + entry['limit'],
                authority='Coordinator under D006; provisional preparation norm, not human fidelity approval', status='provisional'))
            store.insert(db, 'term_entry', dict(id=entry['id'], decision_id=did,
                forms_json=json.dumps(entry['forms'], ensure_ascii=False), candidates_json=json.dumps(entry['candidates'], ensure_ascii=False),
                rule=entry['rule'], exceptions=entry['exceptions'], confidence=entry['confidence'], limitation=entry['limit']))
            for family in entry['families']:
                store.insert(db, 'term_entry_family', dict(entry_id=entry['id'], family_id=family))
            for eid in entry['evidence_ids']:
                store.insert(db, 'term_entry_evidence', dict(entry_id=entry['id'], evidence_id=eid))
                store.insert(db, 'decision_evidence', dict(decision_id=did, evidence_id=eid))
        # Only the already checked German of §§1–2 gets these local decision links.
        # These are provisional lexical links, not whole-work sense coding.
        patterns = {
            'T02': r'^sprachkunde$', 'T05': r'^bau(?:es|e)?$',
            'T06': r'^(?:aus)?bildung$', 'T07': r'eigenthümlich',
            'T09': r'^kräft', 'T17': r'^(?:alphabetischer|schrift|literatur)$',
            'T25': r'^(?:aehnlichkeit|einerleiheit|verschieden|abweichung)',
            'T26': r'^(?:sprachstämme|stämmen|horden|familien|nationen|völker)$',
            'T27': r'^(?:verkehrs?|berührung)$', 'T28': r'^(?:gährung|abschleif)',
            'T29': r'^welttheil', 'T30': r'^(?:wohl|bisweilen|doch|zwar|nun|auch)$',
            'T34': r'^zusammengeflossen$'}
        for row in db.execute("SELECT id,text FROM unit_text WHERE version_id IN ('grundzuege-001-v1','grundzuege-002-v1') AND kind='word'").fetchall():
            for tid, pattern in patterns.items():
                if re.search(pattern, row['text'].casefold()):
                    store.insert(db, 'unit_decision', dict(unit_id=row['id'], decision_id='D007.' + tid))
    return report(db)


def report(db):
    result = store.summary(db)
    for key, sql in {
        'indexed_pages': 'SELECT count(DISTINCT printed_page) FROM word_index',
        'written_token_candidates': 'SELECT count(*) FROM word_index',
        'family_matches': 'SELECT count(*) FROM term_occurrence',
        'register_entries': 'SELECT count(*) FROM term_entry',
        'preparation_evidence': "SELECT count(*) FROM evidence WHERE id LIKE 'prep:%'",
        'entry_evidence_links': 'SELECT count(*) FROM term_entry_evidence',
        'local_term_links': "SELECT count(*) FROM unit_decision WHERE decision_id LIKE 'D007.%'",
    }.items():
        result[key] = db.execute(sql).fetchone()[0]
    return result


def concordance(db, path):
    with path.open('x', encoding='utf-8', newline='') as out:
        writer = csv.writer(out)
        writer.writerow(['family', 'token', 'printed_page', 'pdf_page', 'scan_leaf', 'zone', 'extraction', 'unit_id'])
        writer.writerows(db.execute('''SELECT t.family_id,u.text,w.printed_page,w.pdf_page,w.scan_leaf,w.zone,w.extraction,w.unit_id
            FROM term_occurrence t JOIN word_index w USING(unit_id) JOIN unit_text u ON u.id=w.unit_id
            ORDER BY w.printed_page,u.start,t.family_id'''))


def query(db, word=None, family=None, term=None, limit=20):
    if term:
        item = db.execute('SELECT * FROM term_entry WHERE id=?', (term,)).fetchone()
        if item is None:
            return []
        item = dict(item)
        item['evidence'] = [dict(r) for r in db.execute('''SELECT e.id,e.source_path,e.locator,e.statement,e.quote_status
            FROM term_entry_evidence t JOIN evidence e ON e.id=t.evidence_id WHERE t.entry_id=? ORDER BY e.id''', (term,))]
        return item
    column = 'w.query_form' if word is not None else 't.family_id'
    value = word.casefold() if word is not None else family
    return [dict(r) for r in db.execute(f'''SELECT DISTINCT u.id,u.text,w.printed_page,w.pdf_page,w.scan_leaf,w.zone,w.extraction,
        substr(v.body,max(1,u.start-75),u.end-u.start+150) AS context
        FROM word_index w JOIN unit_text u ON u.id=w.unit_id JOIN text_version v ON v.id=u.version_id
        LEFT JOIN term_occurrence t ON t.unit_id=w.unit_id WHERE {column}=?
        ORDER BY w.printed_page,u.start LIMIT ?''', (value, limit))]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    b = sub.add_parser('build'); b.add_argument('--db', type=Path, required=True)
    b.add_argument('--concordance', type=Path)
    q = sub.add_parser('query'); q.add_argument('--db', type=Path, required=True)
    group = q.add_mutually_exclusive_group(required=True)
    group.add_argument('--word'); group.add_argument('--family'); group.add_argument('--term')
    q.add_argument('--limit', type=int, default=20)
    args = parser.parse_args()
    if args.action == 'query':
        with sqlite3.connect(args.db.resolve().as_uri() + '?mode=ro', uri=True) as db:
            db.row_factory = sqlite3.Row
            print(json.dumps(query(db, args.word, args.family, args.term, args.limit), ensure_ascii=False, indent=2))
        return
    if args.concordance and args.concordance.exists():
        parser.error('choose a fresh concordance path')
    args.db.parent.mkdir(parents=True, exist_ok=True)
    try:
        with args.db.open('xb'):
            pass
    except FileExistsError:
        parser.error('choose a fresh database path')
    db = store.connect(args.db)
    try:
        result = build(db)
        if args.concordance:
            concordance(db, args.concordance)
        print(json.dumps(result, indent=2))
    except Exception:
        db.close(); args.db.unlink(); raise
    finally:
        db.close()


if __name__ == '__main__':
    main()
