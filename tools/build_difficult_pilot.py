#!/usr/bin/env python3
"""Add the bounded §147 pilot to a fresh cumulative terminology database."""
import argparse
import json
from pathlib import Path
import re

import alignment_store as store
import build_opening_cycle as opening
import termbase_store as termbase

ROOT=store.ROOT
PILOT=ROOT/'translations/difficult-147'
GERMAN='difficult-147-de-v1'


def read(name):
    return json.loads((PILOT/name).read_text(encoding='utf-8'))


def add_version(db,version,language,records,path,title,provenance):
    body=' '.join(r['text'] for r in records)
    store.insert(db,'text_version',dict(id=version,title=title,language=language,body=body,
        body_sha256=store.sha256(body.encode()),source_path=str(path.relative_to(ROOT)),
        source_sha256=store.sha256(path.read_bytes()),locator='GS V, §147, printed469–470 / PDF479–480 / scan leaves483–484',
        transcription_status='coordinator_image_checked' if language=='de' else 'generated_translation_not_certified',provenance=provenance))
    analysis=version+':layout';paragraph=version+':p1'
    store.insert(db,'analysis',dict(id=analysis,version_id=version,method='Whole source-sentence rendering blocks and written-token spans; not a certified parse.',scope='Complete §147',status='proposed',supersedes=None))
    store.add_unit(db,paragraph,analysis,version,'paragraph','§147',(0,len(body)))
    offset=0
    for record in records:
        text=record['text'];uid=version+':'+record['id']
        assert body[offset:offset+len(text)]==text
        store.add_unit(db,uid,analysis,version,'sentence' if language=='de' else 'rendering',record['id'],(offset,offset+len(text)),paragraph)
        for n,(a,b) in enumerate(store.word_spans(text),1):
            store.add_unit(db,uid+f':w{n:03}',analysis,version,'word',f'written token {n}',(offset+a,offset+b),uid)
        if language=='en':
            opening.group(db,'p147:sentence:'+uid,version,[GERMAN+':'+record['id']],[uid],
                'source_sentence_rendering','One rendering block can contain more than one English sentence; semantic correspondence is provisional.',left_version=GERMAN)
        offset+=len(text)+1
    return body


def build(db):
    record=read('record.json')
    for path,digest in record['input_sha256'].items():store.verify_file(path,digest)
    for path,digest in read('baseline.json').items():store.verify_file(path,digest)
    source=read('source.json');store.verify_file(source['source_path'],source['source_sha256'])
    termbase.build(db)
    with db:
        body=add_version(db,GERMAN,'de',source['sentences'],PILOT/'source.json','Grundzüge §147 — checked German',source['normalization'])
        if body!=source['body']:raise ValueError('source sentence list differs from body')
        for item in read('candidates.json')['candidates']:
            add_version(db,'en147-'+item['id']+'-v1','en',item['sentences'],PILOT/'candidates.json','Grundzüge §147 — independent candidate','Fresh isolated source-only candidate; runtime models: '+', '.join(item['models']))
        for filename in ['synthesis.json','revised.json']:
            data=read(filename)
            add_version(db,data['id'],'en',data['sentences'],PILOT/filename,'Grundzüge §147 — coordinator English',data['status'])
        for s in source['sentences']:
            eid='E147.'+s['id'];page=s['pages']
            store.insert(db,'evidence',dict(id=eid,source_path=source['source_path'],source_sha256=source['source_sha256'],locator='GS V printed'+','.join(map(str,page))+'; '+s['id'],excerpt=s['text'],statement='Coordinator image-checked main text of §147; not manuscript or specialist validation.',quote_status='coordinator_image_checked',claim_status='primary_print_reading'))
            store.insert(db,'unit_evidence',dict(unit_id=GERMAN+':'+s['id'],evidence_id=eid))
        final=read('revised.json');final_id=final['id']
        for anchor in read('alignments.json')['anchors']:
            sentence=anchor['sentence'];left=GERMAN+':'+sentence;right=final_id+':'+sentence
            for version,parent,quote,suffix in [(GERMAN,left,anchor['german'],'de'),(final_id,right,anchor['english'],'en')]:
                unit=db.execute('SELECT * FROM unit_text WHERE id=?',(parent,)).fetchone()
                whole=db.execute('SELECT body FROM text_version WHERE id=?',(version,)).fetchone()[0]
                span=store.anchor(whole,quote,unit['start'],unit['end'])
                store.add_unit(db,'p147:'+anchor['id']+':'+suffix,version+':layout',version,'clause' if suffix=='de' else 'phrase',anchor['label'],span,parent,'Proposed consequential span; not a complete syntactic analysis.')
            opening.group(db,'p147:anchor:'+anchor['id'],final_id,['p147:'+anchor['id']+':de'],['p147:'+anchor['id']+':en'],'consequential_span_rendering',anchor['note'],left_version=GERMAN)
        for decision in read('decisions.json')['decisions']:
            did='D011.'+decision['id'];sentence=decision['sentence']
            store.insert(db,'decision',dict(id=did,question=decision['question'],resolution=decision['resolution'],authority='Coordinator under D010; source-based provisional judgment',status='provisional'))
            for uid in [GERMAN+':'+sentence,final_id+':'+sentence]:store.insert(db,'unit_decision',dict(unit_id=uid,decision_id=did))
            store.insert(db,'decision_evidence',dict(decision_id=did,evidence_id='E147.'+sentence))
        for link in read('term-links.json'):
            parent=db.execute('SELECT * FROM unit_text WHERE id=?',(GERMAN+':'+link['sentence'],)).fetchone()
            start,end=store.anchor(body,link['quote'],parent['start'],parent['end'])
            uid='p147:term:'+link['id'];store.add_unit(db,uid,GERMAN+':layout',GERMAN,'term_occurrence',link['headword'],(start,end),parent['id'],'Local association with a cited provisional termbase rule; not an automatic global sense assignment.')
            sense=db.execute('SELECT decision_id FROM term_sense WHERE id=?',(link['sense_id'],)).fetchone()
            if sense is None:raise ValueError('missing term sense: '+link['sense_id'])
            store.insert(db,'unit_decision',dict(unit_id=uid,decision_id=sense['decision_id']))
        store.insert(db,'evidence',dict(id='E147.audits',source_path='translations/difficult-147/audits.json',source_sha256=store.sha256((PILOT/'audits.json').read_bytes()),locator='One fresh Claude and one fresh Muse audit of the pre-audit synthesis',excerpt=json.dumps(read('audits.json'),ensure_ascii=False),statement='Model audits and coordinator dispositions; not independent source witnesses.',quote_status='model_audit_record',claim_status='provisional_model_judgment'))
        store.insert(db,'unit_evidence',dict(unit_id=final_id+':p1',evidence_id='E147.audits'))
        notes=read('notes.json')
        for key in ['author_note','editor_note']:
            eid='E147.'+key
            store.insert(db,'evidence',dict(id=eid,source_path=source['source_path'],source_sha256=source['source_sha256'],
                locator='GS V printed470 / PDF480 / scan leaf484; '+key,excerpt=notes[key]['source'],statement=notes[key]['English'],
                quote_status='coordinator_print_reading_with_explicit_uncertainty',claim_status='source_note_with_provisional_English'))
            store.insert(db,'unit_evidence',dict(unit_id=final_id+':p1',evidence_id=eid))
    return store.summary(db)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--db',type=Path,required=True);args=p.parse_args()
    args.db.parent.mkdir(parents=True,exist_ok=True)
    try:
        with args.db.open('xb'):pass
    except FileExistsError:p.error('choose a fresh database path')
    db=store.connect(args.db)
    try:print(json.dumps(build(db),indent=2))
    except Exception:
        db.close();args.db.unlink();raise
    finally:db.close()


if __name__=='__main__':main()
