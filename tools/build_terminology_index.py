#!/usr/bin/env python3
"""Create an OCR discovery index, preserving the existing translation store."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sqlite3

import alignment_store as store
import build_paragraph_002 as paragraph

ROOT = store.ROOT
FAMILIES = [
    ('type', 'Typus / Sprachtypus', r'typus|typen|typisch'),
    ('form', 'Form and compounds', r'form|förm|foerm'),
    ('formation', 'Bildung / Ausbildung / Fortbildung', r'^(?!einbild)(?:bild|ausbild|fortbild|weiterbild|gebild|verbild|nachbild)'),
    ('structure', 'Bau / Construction', r'bau|bäu|baeu|constr|konstr|structur|struktur'),
    ('distinctiveness', 'Eigenthümlichkeit / Individualität / Charakter', r'eigenth|eigent|individu|charakter|character'),
    ('mind', 'Geist / Verstand / Gemüth', r'geist|intellect|intellekt|verstand|gemüth|gemuet'),
    ('power', 'Kraft / Vermögen', r'kraft|kräft|kraeft|vermögen|vermoegen'),
    ('activity', 'Thätigkeit / Wirkung / Verfahren', r'thät|thaet|tätig|taetig|wirk|verfahren|process|erzeug'),
    ('perspective', 'Anschauung / Ansicht / Auffassung', r'anschau|ansicht|auffass|wahrnehm|vorstell|einbild'),
    ('thought', 'Gedanke / Denken / Begriff', r'gedank|denk|begriff|idee|vorstell'),
    ('designation', 'Bezeichnung / Bedeutung / Ausdruck', r'bezeich|zeichen|bedeut|ausdruck'),
    ('sound', 'Laut / Ton / Articulation / Schrift', r'laut|ton|tön|toen|articul|artikul|buchstab|alphabet|schrift'),
    ('word', 'Wort / Wurzel / Wörtervorrath', r'wort|wört|woert|wurzel'),
    ('speech', 'Rede / Satz / Periode', r'rede|satz|sätz|saetz|periode'),
    ('grammar', 'Grammatik / Logik / grammatical form', r'gramm|logik|logisch|sprachform|denkform|redeform|hinzudenk'),
    ('relationship', 'Verschiedenheit / Verwandtschaft / Aehnlichkeit', r'verschieden|verwandt|abstamm|ähn|aehn|einerlei|gleich|ungleich'),
    ('community', 'Sprache / Sprachkunde / Volk / Nation', r'volk|völker|voelker|nation|stamm|stämm|staemm|horde|familie|sprache|sprachkund|sprachstudi|mensch'),
    ('contact', 'Verkehr / Berührung / influence / history', r'verkehr|berühr|beruehr|einfluss|gähr|gaehr|gaer|abschleif|geschicht|histor'),
]


def pages():
    text = (ROOT/'sources/grundzuege-ocr.txt').read_text(encoding='utf-8')
    pieces = re.split(r'===== PRINTED PAGE (\d+) \| PDF PAGE (\d+) \| SCAN LEAF (\d+) =====\n', text)
    recovered = {r['printed_page']: r for r in json.loads((ROOT/'sources/terminology/recovered-pages.json').read_text())}
    result = []
    for i in range(1,len(pieces),4):
        printed,pdf,leaf = map(int,pieces[i:i+3])
        if printed>473:
            continue
        raw = recovered.get(printed,{}).get('text',pieces[i+3])
        lines = raw.splitlines()
        first = next((line for line in lines if line.strip()), '')
        # The first nonblank line is only a header candidate, never a certified
        # removal. It stays in the indexed stream with its own zone label.
        header = re.sub(r'\s+',' ',first).strip()
        normalized = re.sub(r'\s+',' ',re.sub(r'(\w)-\s*\n\s*(\w)',r'\1\2',raw)).strip()
        result.append(dict(printed_page=printed,pdf_page=pdf,scan_leaf=leaf,
            text=normalized,header_end=len(header),extraction='recovery-ocr' if printed in recovered else 'embedded-ocr'))
    if [p['printed_page'] for p in result] != list(range(364,474)):
        raise ValueError('main-text page coverage is incomplete')
    return result


def build(db):
    data = pages()
    source = ROOT/'sources/terminology/search-pages.json'
    current = json.loads(source.read_text())
    if current != data:
        raise ValueError('search-pages input differs; regenerate explicitly before building')
    paragraph.build(db)
    with db:
        db.executescript('''CREATE TABLE term_family (id TEXT PRIMARY KEY NOT NULL, label TEXT NOT NULL, pattern TEXT NOT NULL);
            CREATE TABLE term_occurrence (family_id TEXT NOT NULL REFERENCES term_family(id),
                unit_id TEXT NOT NULL REFERENCES unit(id), query_form TEXT NOT NULL, zone TEXT NOT NULL,
                PRIMARY KEY(family_id,unit_id));
            CREATE TABLE word_index (unit_id TEXT PRIMARY KEY NOT NULL REFERENCES unit(id),
                query_form TEXT NOT NULL, printed_page INTEGER NOT NULL, pdf_page INTEGER NOT NULL,
                scan_leaf INTEGER NOT NULL, zone TEXT NOT NULL, extraction TEXT NOT NULL);
            CREATE INDEX word_form_lookup ON word_index(query_form);
            CREATE INDEX family_lookup ON term_occurrence(family_id);''')
        body=''; offsets=[]
        for page in data:
            if body:body+='\n\n'
            start=len(body);body+=page['text'];offsets.append((page,start,len(body)))
        store.insert(db,'text_version',dict(id='grundzuege-search-v1',title='Whole-work OCR discovery text, printed364–473',
            language='de',body=body,body_sha256=store.sha256(body.encode()),source_path=str(source.relative_to(ROOT)),
            source_sha256=store.sha256(source.read_bytes()),locator='Printed364–473; page metadata recorded per unit',
            transcription_status='uncorrected_search_text',provenance='Derived from the preserved embedded OCR plus labelled recovery for printed410; join line-end hyphens and collapse whitespace. Not a checked transcription; includes headings/apparatus.'))
        store.insert(db,'analysis',dict(id='whole-work-search-layout',version_id='grundzuege-search-v1',method='Unicode written-token convention; casefolded lookup forms. Family regexes are discovery aids, not sense coding.',scope='All110 main-text pages; contents excluded',status='proposed',supersedes=None))
        for id,label,pattern in FAMILIES:
            store.insert(db,'term_family',dict(id=id,label=label,pattern=pattern))
        patterns=[(id,re.compile(pattern)) for id,_,pattern in FAMILIES]
        for page,start,end in offsets:
            pid=f'whole:p{page["printed_page"]}'
            store.add_unit(db,pid,'whole-work-search-layout','grundzuege-search-v1','page',str(page['printed_page']),(start,end))
            for n,(a,b) in enumerate(store.word_spans(page['text']),1):
                uid=pid+f':w{n:04}';token=page['text'][a:b];query=token.casefold()
                zone='header_candidate' if a<page['header_end'] else 'body_or_note'
                store.add_unit(db,uid,'whole-work-search-layout','grundzuege-search-v1','written_word_candidate',token,(start+a,start+b),pid,'OCR candidate, not a checked linguistic word.')
                store.insert(db,'word_index',dict(unit_id=uid,query_form=query,printed_page=page['printed_page'],pdf_page=page['pdf_page'],scan_leaf=page['scan_leaf'],zone=zone,extraction=page['extraction']))
                for id,pattern in patterns:
                    if pattern.search(query):store.insert(db,'term_occurrence',dict(family_id=id,unit_id=uid,query_form=query,zone=zone))
    return data


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',type=Path,default=ROOT/'tmp/preparation/terminology.sqlite')
    parser.add_argument('--prepare-input',action='store_true')
    args=parser.parse_args()
    if args.prepare_input:
        (ROOT/'sources/terminology/search-pages.json').write_text(json.dumps(pages(),ensure_ascii=False,indent=2)+'\n')
        return
    args.db.parent.mkdir(parents=True,exist_ok=True)
    try:
        with args.db.open('xb'):pass
    except FileExistsError:parser.error('choose a fresh output path')
    db=store.connect(args.db)
    try:
        build(db)
        report=store.summary(db)
        report['indexed_words']=db.execute('SELECT count(*) FROM word_index').fetchone()[0]
        report['indexed_pages']=db.execute('SELECT count(DISTINCT printed_page) FROM word_index').fetchone()[0]
        report['family_matches']=db.execute('SELECT count(*) FROM term_occurrence').fetchone()[0]
        print(json.dumps(report,indent=2))
    except Exception:
        db.close();args.db.unlink();raise
    finally:db.close()


if __name__=='__main__':main()
