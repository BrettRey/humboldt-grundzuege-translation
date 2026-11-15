#!/usr/bin/env python3
"""One-time, read-only export of old snapshots into durable edition records.

Normal builds never call this script or require either snapshot. Source rows
are preserved literally. Written-token rows and discovery indexes are stored
as deterministic recipes over immutable text versions, then compared again.
"""
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from humboldt.records import atomic_json,canonical,file_hash,word_spans


def snapshot(path):
    db=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
    try:
        names=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        return {name:[dict(r) for r in db.execute('SELECT * FROM '+name)] for name in names}
    finally:db.close()


def recipes_for(rows,all_tables):
    versions={r['id']:r for r in all_tables['text_version']};units={r['id']:r for r in all_tables['unit']}
    index={r['unit_id']:r for r in all_tables['word_index']};pages={p['printed_page']:p for p in json.loads((ROOT/'sources/terminology/search-pages.json').read_text())}
    groups=defaultdict(list)
    for row in rows:
        if row['kind'] in {'word','written_word_candidate'}:groups[row['parent_id']].append(row)
    recipes=[]
    for pid,words in sorted(groups.items()):
        words.sort(key=lambda r:r['start']);parent=units[pid];body=versions[parent['version_id']]['body'];text=body[parent['start']:parent['end']]
        spans=list(word_spans(text));assert len(spans)==len(words),pid
        width=len(re.search(r':w(\d+)$',words[0]['id']).group(1))
        assert width in (3,4)
        assert all(w['id']==pid+':w'+format(n,'0'+str(width)) for n,w in enumerate(words,1))
        assert all((w['start'],w['end'])==(parent['start']+a,parent['start']+b) for w,(a,b) in zip(words,spans))
        if all(w['label']==body[w['start']:w['end']] for w in words):mode='text'
        else:
            assert all(w['label']==f'written token {n}' for n,w in enumerate(words,1));mode='number'
        assert len({w['note'] for w in words})==1
        recipe=dict(parent_id=pid,id_format='{parent}:w{n:0'+str(width)+'}',kind=words[0]['kind'],label_mode=mode,note=words[0]['note'],expected_count=len(words))
        if words[0]['kind']=='written_word_candidate':
            meta=index[words[0]['id']];recipe['index']={k:meta[k] for k in ['printed_page','pdf_page','scan_leaf','extraction']}
            recipe['index'].update(header_end=pages[meta['printed_page']]['header_end'],families=[f['id'] for f in all_tables['term_family']])
        recipes.append(recipe)
    return recipes


def main():
    edition=ROOT/'edition';manifest=edition/'manifest.json'
    if manifest.exists():raise SystemExit('edition already exists; this one-time exporter refuses to overwrite it')
    old_path=ROOT/'tmp/termbase-v2/termbase-final.sqlite';new_path=ROOT/'tmp/difficult-147/pilot.sqlite'
    old=snapshot(old_path);full=snapshot(new_path);delta={}
    for table,rows in full.items():
        old_rows=Counter(canonical(r) for r in old[table]);current=Counter(canonical(r) for r in rows)
        assert not old_rows-current,table
        delta[table]=[json.loads(s) for s,n in (current-old_rows).items() for _ in range(n)]
    recipes=recipes_for(old['unit'],full)
    old['unit']=[r for r in old['unit'] if r['kind'] not in {'word','written_word_candidate'}]
    old['word_index']=[];old['term_occurrence']=[]
    bundles=[]
    groups={
        'text':{'text_version','analysis','unit'},
        'evidence':{'evidence','decision','unit_evidence','unit_decision','decision_evidence','alignment','alignment_member','preparation_input'},
    }
    for name,tables in groups.items():
        bundle=dict(format='humboldt.records',schema_version=1,id='legacy-'+name,tables={t:old[t] for t in sorted(tables) if old[t]})
        if name=='text':bundle['word_recipes']=recipes
        dest=edition/'records'/f'{name}.json';atomic_json(dest,bundle);bundles.append(dest)
    remaining=set(old)-set().union(*groups.values())
    bundle=dict(format='humboldt.records',schema_version=1,id='legacy-terminology',tables={t:old[t] for t in sorted(remaining) if old[t]})
    dest=edition/'records/terminology.json';atomic_json(dest,bundle);bundles.append(dest)
    # The actual representative pilot is declarative: six versions and layouts,
    # with consequential extra rows kept as data. No passage-specific Python.
    versions={r['id']:r for r in delta['text_version']};layouts=[];remove_units=set()
    for vid,version in sorted(versions.items()):
        paras=[r for r in delta['unit'] if r['version_id']==vid and r['kind']=='paragraph'];assert len(paras)==1
        para=paras[0];segments=sorted([r for r in delta['unit'] if r['parent_id']==para['id']],key=lambda r:r['start'])
        assert all(r['kind'] in {'sentence','rendering'} for r in segments)
        layouts.append(dict(version_id=vid,analysis_id=para['analysis_id'],paragraph_id=para['id'],label=para['label'],segments=[dict(id=r['id'],kind=r['kind'],label=r['label'],text=version['body'][r['start']:r['end']]) for r in segments]))
        remove_units.add(para['id']);remove_units.update(r['id'] for r in segments)
    delta['unit']=[r for r in delta['unit'] if r['kind'] not in {'word','written_word_candidate'} and r['id'] not in remove_units]
    passage=dict(format='humboldt.passage',schema_version=1,id='passage-0147',tables={t:rs for t,rs in sorted(delta.items()) if rs},layouts=layouts)
    dest=edition/'passages/0147/records.json';atomic_json(dest,passage);bundles.append(dest)
    # Resource identities are provenance/optional attachments, never build inputs.
    resources={}
    for table in ['text_version','evidence']:
        for r in full[table]:
            path=r['source_path']
            if not Path(path).is_absolute() and '..' not in Path(path).parts:
                previous=resources.get(path)
                if previous and previous['sha256']!=r['source_sha256']:raise ValueError('source identity conflict: '+path)
                resources[path]=dict(path=path,sha256=r['source_sha256'],required=False)
    rows_digest={t:hashlib.sha256(canonical(sorted(rs,key=canonical)).encode()).hexdigest() for t,rs in full.items()}
    baseline=json.loads((ROOT/'translations/difficult-147/baseline.json').read_text())
    for folder in ['translations','tools','tests']:
        for p in (ROOT/folder).glob('**/*'):
            if p.is_file() and '__pycache__' not in p.parts and not any(x in p.parts for x in ['unit','integration']):baseline[str(p.relative_to(ROOT))]=file_hash(p)
    baseline['AGENTS.md']=file_hash(ROOT/'AGENTS.md');baseline['docs/WORKFLOW-REVIEW.md']=file_hash(ROOT/'docs/WORKFLOW-REVIEW.md')
    # The exporter itself is implementation, not a pre-existing frozen artifact.
    baseline.pop('tools/migrate_legacy_snapshot.py',None)
    proof=dict(description='Dated migration evidence only. Paths/hashes below are not normal build prerequisites.',source_snapshot=str(new_path.relative_to(ROOT)),source_sha256=file_hash(new_path),counts={t:len(rs) for t,rs in full.items()},table_logical_sha256=rows_digest,preserved_files=baseline)
    atomic_json(edition/'provenance/legacy-migration.json',proof)
    payload=dict(format='humboldt.edition',schema_version=1,id='humboldt-grundzuege',datasets=[dict(path=str(p.relative_to(edition)),sha256=file_hash(p)) for p in bundles],resources=sorted(resources.values(),key=lambda r:r['path']))
    atomic_json(manifest,payload)
    print(json.dumps(dict(datasets=len(bundles),word_recipes=len(recipes),passage_layouts=len(layouts),resources=len(resources),bytes=sum(p.stat().st_size for p in bundles)),indent=2))


if __name__=='__main__':main()
