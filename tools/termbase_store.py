#!/usr/bin/env python3
"""Build/query individual terms, senses and checked source attestations."""
import argparse
import csv
import json
from pathlib import Path
import re
import sqlite3

import alignment_store as store
import preparation_store as preparation
from assemble_termbase import key, sha, slug

ROOT=store.ROOT
DATA=ROOT/'sources/terminology/v2'
CATALOG=DATA/'termbase.json'


def build(db,catalog_path=CATALOG):
    catalog=json.loads(catalog_path.read_text())
    if catalog['issues']:
        raise ValueError('catalog has unresolved validation issues')
    for path,fingerprint in catalog['input_sha256'].items():
        if store.sha256((ROOT/path).read_bytes())!=fingerprint:
            raise ValueError('termbase input changed: '+path)
    source_hashes={}
    for control in catalog.get('controls',[]):
        path=control['source_path']
        if path not in source_hashes:source_hashes[path]=store.sha256((ROOT/path).read_bytes())
        if source_hashes[path]!=control['source_sha256']:raise ValueError('comparative source changed: '+path)
    preparation.build(db)
    with db:
        db.executescript('''
        CREATE TABLE lexeme (
          id TEXT PRIMARY KEY NOT NULL, headword TEXT NOT NULL, query_key TEXT UNIQUE NOT NULL,
          kind TEXT NOT NULL, scope TEXT NOT NULL, domains_json TEXT NOT NULL, roles_json TEXT NOT NULL);
        CREATE TABLE lexeme_form (
          lexeme_id TEXT NOT NULL REFERENCES lexeme(id), form TEXT NOT NULL, query_key TEXT NOT NULL, form_role TEXT NOT NULL,
          PRIMARY KEY(lexeme_id,form));
        CREATE INDEX lexeme_form_lookup ON lexeme_form(query_key);
        CREATE TABLE term_sense (
          id TEXT PRIMARY KEY NOT NULL, lexeme_id TEXT NOT NULL REFERENCES lexeme(id),
          label TEXT NOT NULL, definition TEXT NOT NULL, rule TEXT NOT NULL, caution TEXT NOT NULL,
          decision_id TEXT NOT NULL REFERENCES decision(id));
        CREATE TABLE sense_rendering (
          sense_id TEXT NOT NULL REFERENCES term_sense(id), rank INTEGER NOT NULL, rendering TEXT NOT NULL,
          PRIMARY KEY(sense_id,rank));
        CREATE TABLE term_use (
          id TEXT PRIMARY KEY NOT NULL, sense_id TEXT NOT NULL REFERENCES term_sense(id),
          origin TEXT UNIQUE NOT NULL, label TEXT NOT NULL, definition TEXT NOT NULL,
          rule TEXT NOT NULL, caution TEXT NOT NULL);
        CREATE TABLE sense_attestation (
          id TEXT PRIMARY KEY NOT NULL, sense_id TEXT NOT NULL REFERENCES term_sense(id),
          use_id TEXT NOT NULL REFERENCES term_use(id),
          evidence_id TEXT NOT NULL REFERENCES evidence(id),
          checked_context_unit TEXT NOT NULL REFERENCES unit(id),
          checked_expression_unit TEXT REFERENCES unit(id),
          ocr_context_unit TEXT REFERENCES unit(id), source_page_unit TEXT REFERENCES unit(id),
          printed_page INTEGER NOT NULL, pdf_page INTEGER NOT NULL, scan_leaf INTEGER,
          term_form TEXT, evidence_role TEXT NOT NULL, composite_group TEXT,
          text_layer TEXT NOT NULL, issue TEXT NOT NULL);
        CREATE TABLE term_expression_part (
          attestation_id TEXT NOT NULL REFERENCES sense_attestation(id), rank INTEGER NOT NULL,
          unit_id TEXT NOT NULL REFERENCES unit(id), part_role TEXT NOT NULL,
          PRIMARY KEY(attestation_id,rank));
        CREATE TABLE composite_attestation (
          id TEXT PRIMARY KEY NOT NULL, lexeme_id TEXT NOT NULL REFERENCES lexeme(id),
          sense_id TEXT NOT NULL REFERENCES term_sense(id), joined_form TEXT NOT NULL, method TEXT NOT NULL);
        CREATE TABLE composite_member (
          group_id TEXT NOT NULL REFERENCES composite_attestation(id),
          attestation_id TEXT NOT NULL REFERENCES sense_attestation(id), part_order INTEGER NOT NULL,
          PRIMARY KEY(group_id,part_order));
        CREATE TABLE term_relation (
          lexeme_id TEXT NOT NULL REFERENCES lexeme(id), relation TEXT NOT NULL,
          target_id TEXT REFERENCES lexeme(id), target_label TEXT NOT NULL, reason TEXT NOT NULL);
        CREATE TABLE terminology_candidate (
          id TEXT PRIMARY KEY NOT NULL, form TEXT NOT NULL, occurrences INTEGER NOT NULL,
          pages_json TEXT NOT NULL, header_only INTEGER NOT NULL, reader TEXT NOT NULL,
          disposition TEXT NOT NULL, target_id TEXT REFERENCES lexeme(id), reason TEXT NOT NULL);
        CREATE TABLE terminology_page_review (
          printed_page INTEGER PRIMARY KEY NOT NULL, reader TEXT NOT NULL, metadata_json TEXT NOT NULL);
        CREATE TABLE register_carry_forward (
          old_entry TEXT NOT NULL, old_label TEXT PRIMARY KEY NOT NULL,
          disposition TEXT NOT NULL, target_id TEXT REFERENCES lexeme(id), reason TEXT NOT NULL);
        CREATE TABLE terminology_control (
          id TEXT PRIMARY KEY NOT NULL, metadata_json TEXT NOT NULL);
        CREATE TABLE lexeme_control (
          lexeme_id TEXT NOT NULL REFERENCES lexeme(id), control_id TEXT NOT NULL REFERENCES terminology_control(id),
          relation TEXT NOT NULL, comment TEXT NOT NULL, PRIMARY KEY(lexeme_id,control_id));
        ''')
        for term in catalog['terms']:
            store.insert(db,'lexeme',dict(id=term['id'],headword=term['headword'],query_key=key(term['headword']),kind=term['kind'],scope=term['scope'],domains_json=json.dumps(term['domains'],ensure_ascii=False),roles_json=json.dumps(term['roles'],ensure_ascii=False)))
            for form in term['forms']:
                store.insert(db,'lexeme_form',dict(lexeme_id=term['id'],form=form['form'],query_key=key(form['form']),form_role=form['role']))
            for sense in term['senses']:
                did='D009.'+sense['id']
                store.insert(db,'decision',dict(id=did,question=term['headword']+' — '+sense['label'],resolution=sense['rule']+' Caution: '+sense['caution'],authority='Coordinator synthesis under D008; individually sourced, provisional interpretation',status='provisional'))
                store.insert(db,'term_sense',dict(id=sense['id'],lexeme_id=term['id'],label=sense['label'],definition=sense['definition'],rule=sense['rule'],caution=sense['caution'],decision_id=did))
                for n,rendering in enumerate(sense['renderings'],1):store.insert(db,'sense_rendering',dict(sense_id=sense['id'],rank=n,rendering=rendering))
                for use in sense['uses']:store.insert(db,'term_use',dict(id=use['id'],sense_id=sense['id'],origin=use['origin'],label=use['label'],definition=use['definition'],rule=use['rule'],caution=use['caution']))
        # Selected checked quotations form their own immutable excerpt collection.
        # They never replace the preserved OCR or an existing translation version.
        evs=[(sense,ev) for term in catalog['terms'] for sense in term['senses'] for ev in sense['evidence']]
        body='';locations={}
        for sense,ev in evs:
            if body:body+='\n\n'
            start=len(body);body+=ev['checked_quote'];locations[ev['id']]=(start,len(body))
        version='grundzuege-checked-term-excerpts-v2';analysis='checked-term-excerpt-layout-v2'
        store.insert(db,'text_version',dict(id=version,title='Selected image-checked terminology quotations, with separately identified supplementary sources',language='de',body=body,body_sha256=store.sha256(body.encode()),source_path=str(catalog_path.relative_to(ROOT)),source_sha256=store.sha256(catalog_path.read_bytes()),locator='Individual attestation records give printed/PDF/scan coordinates and source layers',transcription_status='model_image_checked_excerpts',provenance='A collection of separately checked excerpts, not a continuous reading text or certified complete transcription. Original OCR, checked quotations, interpretation and supplementary source layers remain distinct.'))
        store.insert(db,'analysis',dict(id=analysis,version_id=version,method='Quotation boundaries and written-token spans; term expressions separately anchored. Not a grammatical parse.',scope='Individual term/sense evidence only',status='proposed',supersedes=None))
        store.insert(db,'analysis',dict(id='term-ocr-contexts-v2',version_id='grundzuege-search-v1',method='Exact locator windows in uncorrected OCR; the checked reading is in a separate version',scope='Selected main-text evidence windows, not whole-work sense annotation',status='proposed',supersedes=None))
        for sense,ev in evs:
            eid='tb:'+ev['id'];start,end=locations[ev['id']];uid='tbquote:'+ev['id']
            store.add_unit(db,uid,analysis,version,'evidence_context',ev['id'],(start,end),None,'Checked excerpt; source layer and verification provenance are in the attestation.')
            for n,(a,b) in enumerate(store.word_spans(ev['checked_quote']),1):store.add_unit(db,uid+f':w{n:03}',analysis,version,'word',ev['checked_quote'][a:b],(start+a,start+b),uid)
            expression=None;part_units=[]
            for np,part in enumerate(ev['checked_parts'],1):
                a,b=part['span']
                if ev['checked_quote'][a:b]!=part['text']:raise ValueError('expression part does not round-trip: '+ev['id'])
                part_id=uid+(':expression' if ev['evidence_role']=='direct_occurrence' else f':part{np}')
                store.add_unit(db,part_id,analysis,version,'term_expression' if ev['evidence_role']=='direct_occurrence' else 'expression_part',part['text'],(start+a,start+b),uid)
                part_units.append(part_id)
                if ev['evidence_role']=='direct_occurrence':expression=part_id
            ocr_unit=source_page=None
            if ev.get('page_span'):
                page=db.execute('SELECT start,end FROM unit WHERE id=?',(f'whole:p{ev["printed_page"]}',)).fetchone()
                a,b=ev['page_span'];ocr_unit='tbocr:'+ev['id'];source_page=f'whole:p{ev["printed_page"]}'
                store.add_unit(db,ocr_unit,'term-ocr-contexts-v2','grundzuege-search-v1','ocr_locator_window',ev['id'],(page['start']+a,page['start']+b),None,'Uncorrected locator window, not the checked reading.')
                if db.execute('SELECT text FROM unit_text WHERE id=?',(ocr_unit,)).fetchone()[0]!=ev['ocr_quote']:
                    raise ValueError('OCR window does not round-trip: '+ev['id'])
            store.insert(db,'evidence',dict(id=eid,source_path=ev['source_path'],source_sha256=ev['source_sha256'],locator=f"printed{ev['printed_page']}; PDF{ev['pdf_page']}; layer={ev['text_layer']}; reader={ev['reader']}",excerpt=ev['checked_quote'],statement=sense['definition'],quote_status=ev['verification'],claim_status='provisional local interpretation; model-assisted image check, not specialist certification'))
            store.insert(db,'unit_evidence',dict(unit_id=uid,evidence_id=eid))
            for part_id in part_units:store.insert(db,'unit_evidence',dict(unit_id=part_id,evidence_id=eid))
            if expression:store.insert(db,'unit_decision',dict(unit_id=expression,decision_id='D009.'+sense['id']))
            store.insert(db,'decision_evidence',dict(decision_id='D009.'+sense['id'],evidence_id=eid))
            store.insert(db,'sense_attestation',dict(id=ev['id'],sense_id=sense['id'],use_id=ev['use_id'],evidence_id=eid,checked_context_unit=uid,checked_expression_unit=expression,ocr_context_unit=ocr_unit,source_page_unit=source_page,printed_page=ev['printed_page'],pdf_page=ev['pdf_page'],scan_leaf=ev.get('scan_leaf'),term_form=ev.get('term_form'),evidence_role=ev['evidence_role'],composite_group=ev.get('composite_group'),text_layer=ev['text_layer'],issue=ev.get('issue','')+' '+ev.get('selection_note','')))
            for np,part_id in enumerate(part_units,1):store.insert(db,'term_expression_part',dict(attestation_id=ev['id'],rank=np,unit_id=part_id,part_role=ev['evidence_role']))
        for group in catalog['composite_attestations']:
            store.insert(db,'composite_attestation',{k:group[k] for k in ['id','lexeme_id','sense_id','joined_form','method']})
            for member in group['members']:store.insert(db,'composite_member',dict(group_id=group['id'],attestation_id=member['evidence_id'],part_order=member['order']))
        for term in catalog['terms']:
            for rel in term['relations']:store.insert(db,'term_relation',dict(lexeme_id=term['id'],relation=rel['type'],target_id=rel['target_id'],target_label=rel['target_label'],reason=rel['reason']))
        for review in catalog['candidate_reviews']:
            target='lex:'+slug(review['target']) if review.get('target') else None
            store.insert(db,'terminology_candidate',dict(id=review['id'],form=review['form'],occurrences=review['count'],pages_json=json.dumps(review['pages']),header_only=int(review['header_only']),reader=review['reader'],disposition=review['disposition'],target_id=target,reason=review['reason']))
        for review in catalog['page_reviews']:store.insert(db,'terminology_page_review',dict(printed_page=review['page'],reader=review['reader'],metadata_json=json.dumps(review,ensure_ascii=False)))
        for item in catalog['carry_forward']:
            store.insert(db,'register_carry_forward',dict(old_entry=item['old_entry'],old_label=item['old_label'],disposition=item['disposition'],target_id='lex:'+slug(item['target']) if item.get('target') else None,reason=item['reason']))
        for control in catalog.get('controls',[]):store.insert(db,'terminology_control',dict(id=control['id'],metadata_json=json.dumps(control,ensure_ascii=False)))
        for link in catalog.get('control_links',[]):store.insert(db,'lexeme_control',link)
        store.insert(db,'preparation_input',dict(path=str(catalog_path.relative_to(ROOT)),sha256=store.sha256(catalog_path.read_bytes())))
    return report(db)


def report(db):
    result=preparation.report(db)
    for name in ['lexeme','term_sense','term_use','sense_attestation','terminology_candidate','terminology_page_review','register_carry_forward','lexeme_control','term_relation']:
        result[name]=db.execute('SELECT count(*) FROM '+name).fetchone()[0]
    result['candidate_dispositions']=dict(db.execute('SELECT disposition,count(*) FROM terminology_candidate GROUP BY disposition'))
    result['evidence_roles']=dict(db.execute('SELECT evidence_role,count(*) FROM sense_attestation GROUP BY evidence_role'))
    result['composite_attestations']=db.execute('SELECT count(*) FROM composite_attestation').fetchone()[0]
    return result


def query(db,term):
    ids=[r[0] for r in db.execute('SELECT DISTINCT lexeme_id FROM lexeme_form WHERE query_key=?',(key(term),))]
    result=[]
    for tid in ids:
        item=dict(db.execute('SELECT * FROM lexeme WHERE id=?',(tid,)).fetchone())
        item['forms']=[dict(r) for r in db.execute('SELECT form,form_role FROM lexeme_form WHERE lexeme_id=? ORDER BY form',(tid,))]
        item['senses']=[]
        for row in db.execute('SELECT * FROM term_sense WHERE lexeme_id=? ORDER BY id',(tid,)):
            sense=dict(row);sense['renderings']=[r[0] for r in db.execute('SELECT rendering FROM sense_rendering WHERE sense_id=? ORDER BY rank',(row['id'],))]
            sense['uses']=[dict(r) for r in db.execute('SELECT * FROM term_use WHERE sense_id=? ORDER BY id',(row['id'],))]
            sense['attestations']=[dict(r) for r in db.execute('''SELECT a.id,a.checked_context_unit,a.checked_expression_unit,a.ocr_context_unit,a.printed_page,a.pdf_page,a.scan_leaf,a.term_form,a.evidence_role,a.composite_group,a.text_layer,a.issue,e.source_path,e.excerpt,e.quote_status
            FROM sense_attestation a JOIN evidence e ON e.id=a.evidence_id WHERE a.sense_id=? ORDER BY a.printed_page''',(row['id'],))]
            item['senses'].append(sense)
        item['relations']=[dict(r) for r in db.execute('SELECT * FROM term_relation WHERE lexeme_id=?',(tid,))]
        item['composite_attestations']=[dict(r) for r in db.execute('SELECT * FROM composite_attestation WHERE lexeme_id=?',(tid,))]
        item['controls']=[dict(r) for r in db.execute('''SELECT c.metadata_json,l.relation,l.comment FROM lexeme_control l JOIN terminology_control c ON c.id=l.control_id WHERE l.lexeme_id=?''',(tid,))]
        result.append(item)
    return result


def trace(db,unit_id):
    """Distinguish an exact checked expression from an OCR context association."""
    unit=db.execute('SELECT * FROM unit_text WHERE id=?',(unit_id,)).fetchone()
    if unit is None:return None
    rows=db.execute('''SELECT DISTINCT l.headword,s.id AS sense_id,s.label,a.id AS attestation_id,
      a.evidence_role,a.printed_page,a.pdf_page,e.excerpt
      FROM term_expression_part p JOIN unit x ON x.id=p.unit_id
      JOIN sense_attestation a ON a.id=p.attestation_id JOIN term_sense s ON s.id=a.sense_id
      JOIN lexeme l ON l.id=s.lexeme_id JOIN evidence e ON e.id=a.evidence_id
      WHERE x.version_id=? AND x.start<=? AND x.end>=?''',(unit['version_id'],unit['start'],unit['end'])).fetchall()
    relation='checked expression or explicitly typed expression part'
    if not rows and unit['version_id']=='grundzuege-search-v1':
        rows=db.execute('''SELECT l.headword,s.id AS sense_id,s.label,a.id AS attestation_id,
          a.evidence_role,a.printed_page,a.pdf_page,e.excerpt
          FROM sense_attestation a JOIN unit x ON x.id=a.ocr_context_unit
          JOIN term_sense s ON s.id=a.sense_id JOIN lexeme l ON l.id=s.lexeme_id
          JOIN evidence e ON e.id=a.evidence_id WHERE x.start<=? AND x.end>=?''',(unit['start'],unit['end'])).fetchall()
        relation='OCR locator-window association; not a sense assignment to this token'
    return dict(unit=dict(unit),relation=relation,matches=[dict(r) for r in rows])


def export(db,path):
    with path.open('x',encoding='utf-8',newline='') as f:
        out=csv.writer(f);out.writerow(['term','sense','definition','English_candidates','rule','caution','primary_pages'])
        for term in db.execute('SELECT id,headword FROM lexeme ORDER BY query_key'):
            for sense in db.execute('SELECT * FROM term_sense WHERE lexeme_id=? ORDER BY id',(term['id'],)):
                renderings=' / '.join(r[0] for r in db.execute('SELECT rendering FROM sense_rendering WHERE sense_id=? ORDER BY rank',(sense['id'],)))
                pages='; '.join(str(r[0]) for r in db.execute('SELECT DISTINCT printed_page FROM sense_attestation WHERE sense_id=? ORDER BY printed_page',(sense['id'],)))
                out.writerow([term['headword'],sense['label'],sense['definition'],renderings,sense['rule'],sense['caution'],pages])


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='action',required=True)
    b=sub.add_parser('build');b.add_argument('--db',type=Path,required=True);b.add_argument('--csv',type=Path)
    q=sub.add_parser('query');q.add_argument('--db',type=Path,required=True);q.add_argument('--term',required=True)
    t=sub.add_parser('trace');t.add_argument('--db',type=Path,required=True);t.add_argument('--unit',required=True)
    a=parser.parse_args()
    if a.action in {'query','trace'}:
        with sqlite3.connect(a.db.resolve().as_uri()+'?mode=ro',uri=True) as db:
            db.row_factory=sqlite3.Row;print(json.dumps(query(db,a.term) if a.action=='query' else trace(db,a.unit),ensure_ascii=False,indent=2))
        return
    if a.csv and a.csv.exists():parser.error('choose a fresh CSV path')
    a.db.parent.mkdir(parents=True,exist_ok=True)
    try:
        with a.db.open('xb'):pass
    except FileExistsError:parser.error('choose a fresh database path')
    db=store.connect(a.db)
    try:
        result=build(db)
        if a.csv:export(db,a.csv)
        print(json.dumps(result,indent=2))
    except Exception:
        db.close();a.db.unlink();raise
    finally:db.close()


if __name__=='__main__':main()
