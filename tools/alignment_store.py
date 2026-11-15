#!/usr/bin/env python3
"""Disposable linked-text demonstration; Python standard library only.

Offsets count Unicode code points, with half-open [start, end) ranges.
No normalization is performed. Hashes cover exact UTF-8 bytes.
"""

import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / 'sources/annotations/opening-001.json'
SCHEMA = Path(__file__).with_name('alignment-schema.sql')


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def connect(path=':memory:'):
    db = sqlite3.connect(path, uri=str(path).startswith('file:'))
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys = ON')
    return db


def verify_file(relative_path, expected_hash):
    path = ROOT / relative_path
    actual = sha256(path.read_bytes())
    if actual != expected_hash:
        raise ValueError(f'source fingerprint mismatch: {relative_path}')


def anchor(body, quote, start=0, end=None):
    """Locate one exact occurrence within the requested window; never guess."""
    end = len(body) if end is None else end
    if not quote or not 0 <= start <= end <= len(body):
        raise ValueError('invalid quote or anchor window')
    first = body.find(quote, start, end)
    if first < 0 or body.find(quote, first + 1, end) >= 0:
        raise ValueError(f'quote is missing or ambiguous: {quote[:60]!r}')
    return first, first + len(quote)


def word_spans(body):
    """Written tokens: letters/marks/numbers, with internal hyphens/apostrophes.

    This convention is not a linguistic word analysis. Punctuation is omitted.
    Combining marks remain in their written token; offsets remain code points.
    """
    def constituent(char):
        return unicodedata.category(char)[0] in 'LMN'

    i = 0
    while i < len(body):
        if not constituent(body[i]):
            i += 1
            continue
        start = i
        i += 1
        while i < len(body):
            if constituent(body[i]):
                i += 1
            elif body[i] in "-'’" and i + 1 < len(body) and constituent(body[i + 1]):
                i += 2
            else:
                break
        yield start, i


def insert(db, table, record):
    # Table/column identifiers are internal constants or trusted packet keys.
    keys = list(record)
    db.execute(f'INSERT INTO {table} ({",".join(keys)}) VALUES ({",".join("?" for _ in keys)})',
               [record[key] for key in keys])


def add_unit(db, id, analysis_id, version_id, kind, label, span, parent_id=None, note=''):
    insert(db, 'unit', dict(id=id, analysis_id=analysis_id, version_id=version_id,
                           kind=kind, label=label, start=span[0], end=span[1],
                           parent_id=parent_id, note=note))


def build(db, packet_path=PACKET, *, initialize_schema=True):
    packet = json.loads(Path(packet_path).read_text(encoding='utf-8'))
    # Check all original files and exact text before creating anything.
    for version in packet['versions']:
        verify_file(version['source_path'], version['source_sha256'])
        if sha256(version['body'].encode('utf-8')) != version['body_sha256']:
            raise ValueError(f'body fingerprint mismatch: {version["id"]}')
    for evidence in packet['evidence']:
        verify_file(evidence['source_path'], evidence['source_sha256'])
    if initialize_schema:
        db.executescript(SCHEMA.read_text(encoding='utf-8'))
    with db:
        for version in packet['versions']:
            insert(db, 'text_version', version)
        for analysis in packet['analyses']:
            insert(db, 'analysis', analysis)
        for layout in packet['layouts']:
            version_id, analysis_id = layout['version_id'], layout['analysis_id']
            body = db.execute('SELECT body FROM text_version WHERE id=?', (version_id,)).fetchone()[0]
            para_id = f'{analysis_id}:p1'
            add_unit(db, para_id, analysis_id, version_id, layout['container_kind'],
                     layout['container_label'], (0, len(body)))
            previous_end = 0
            for sentence in layout['sentences']:
                span = anchor(body, sentence['quote'])
                if span[0] < previous_end or body[previous_end:span[0]].strip():
                    raise ValueError('sentences overlap, reorder, or omit source text')
                previous_end = span[1]
                add_unit(db, sentence['id'], analysis_id, version_id, 'sentence',
                         sentence['id'], span, para_id)
                for n, (a, b) in enumerate(word_spans(sentence['quote']), 1):
                    add_unit(db, f'{sentence["id"]}:w{n:03}', analysis_id, version_id,
                             'word', f'written token {n}', (span[0] + a, span[0] + b), sentence['id'])
            if body[previous_end:].strip():
                raise ValueError('sentence list omits source text at end')
        for annotation in packet['annotations']:
            sentence = db.execute('SELECT * FROM unit_text WHERE id=?', (annotation['sentence_id'],)).fetchone()
            body = db.execute('SELECT body FROM text_version WHERE id=?', (sentence['version_id'],)).fetchone()[0]
            span = anchor(body, annotation['quote'], sentence['start'], sentence['end'])
            add_unit(db, annotation['id'], annotation['analysis_id'], sentence['version_id'],
                     annotation['kind'], annotation['label'], span,
                     annotation['parent_id'], annotation['note'])
        for table in ('evidence', 'decision'):
            for record in packet[table]:
                insert(db, table, record)
        for table in ('unit_evidence', 'unit_decision', 'decision_evidence'):
            for record in packet[table]:
                insert(db, table, record)
        for group in packet['alignments']:
            insert(db, 'alignment', {key: value for key, value in group.items() if key != 'members'})
            for member in group['members']:
                insert(db, 'alignment_member', dict(alignment_id=group['id'], **member))
            db.execute("UPDATE alignment SET status='proposed' WHERE id=?", (group['id'],))
    return packet


def trace_word(db, unit_id):
    word = db.execute("SELECT * FROM unit_text WHERE id=? AND kind='word'", (unit_id,)).fetchone()
    if word is None:
        raise ValueError(f'not a word unit: {unit_id}')
    ancestors = db.execute('''WITH RECURSIVE chain(id, parent_id, kind, text) AS (
        SELECT id, parent_id, kind, text FROM unit_text WHERE id=?
        UNION ALL
        SELECT p.id, p.parent_id, p.kind, p.text FROM unit_text p JOIN chain c ON p.id=c.parent_id
    ) SELECT * FROM chain''', (unit_id,)).fetchall()
    ids = [row['id'] for row in ancestors]
    placeholders = ','.join('?' for _ in ids)
    evidence = db.execute(f'''SELECT DISTINCT e.* FROM evidence e JOIN unit_evidence l
        ON e.id=l.evidence_id WHERE l.unit_id IN ({placeholders}) ORDER BY e.id''', ids).fetchall()
    decisions = db.execute(f'''SELECT DISTINCT d.* FROM decision d JOIN unit_decision l
        ON d.id=l.decision_id WHERE l.unit_id IN ({placeholders}) ORDER BY d.id''', ids).fetchall()
    annotations = db.execute('''SELECT id, analysis_id, kind, label, text, note FROM unit_text
        WHERE version_id=? AND analysis_id != ? AND start<=? AND end>=? ORDER BY analysis_id, start, end DESC''',
        (word['version_id'], word['analysis_id'], word['start'], word['end'])).fetchall()
    return dict(word=dict(word), ancestry=[dict(r) for r in ancestors],
                evidence=[dict(r) for r in evidence], decisions=[dict(r) for r in decisions],
                containing_annotations=[dict(r) for r in annotations])


def summary(db):
    tables = ('text_version', 'analysis', 'unit', 'evidence', 'decision', 'alignment')
    return dict(counts={table: db.execute(f'SELECT count(*) FROM {table}').fetchone()[0] for table in tables},
                integrity=db.execute('PRAGMA integrity_check').fetchone()[0],
                foreign_key_errors=[tuple(r) for r in db.execute('PRAGMA foreign_key_check')])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('build', 'demo'))
    parser.add_argument('--db', type=Path, default=ROOT / 'tmp/alignment-prototype.sqlite')
    args = parser.parse_args()
    if args.command == 'build':
        args.db.parent.mkdir(parents=True, exist_ok=True)
        # Do not silently replace even the disposable prototype.
        try:
            with args.db.open('xb'):
                pass
        except FileExistsError:
            parser.error('output already exists; choose a fresh --db path')
        db = connect(args.db)
        try:
            build(db)
            print(json.dumps(summary(db), ensure_ascii=False, indent=2))
        except Exception:
            db.close()
            args.db.unlink()
            raise
        finally:
            db.close()
    else:
        if not args.db.is_file():
            parser.error('database is missing; run build first')
        with connect(f'file:{args.db}?mode=ro') as db:
            word = db.execute("SELECT id FROM unit_text WHERE version_id='grundzuege-001-v1' AND kind='word' AND text='Sprachkunde'").fetchone()
            result = dict(summary=summary(db), trace=trace_word(db, word[0]),
                          alignment=[dict(r) for r in db.execute('''SELECT a.id, a.relation, a.status,
                              m.side, u.id AS unit_id, u.text FROM alignment a JOIN alignment_member m
                              ON m.alignment_id=a.id JOIN unit_text u ON u.id=m.unit_id
                              ORDER BY a.id, m.side, u.start''')])
            print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
