"""Declarative edition inputs -> reproducible, disposable SQLite projection."""
from collections import defaultdict
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import uuid

from . import database
from .records import atomic_json,canonical,file_hash,fingerprint,parse_json,read_json,sync_directory,validate_shape,within,word_spans,publish_exclusive


def project_root(project):
    root=Path(project).resolve()
    within(root,'edition/manifest.json')
    if not (root/'edition/manifest.json').is_file():raise ValueError('missing edition/manifest.json in '+str(root))
    return root


def schema_root():
    # Package resources are bundled for installed and portable releases.
    return Path(__file__).parent/'record_schemas'


def shape(value,name):
    validate_shape(value,read_json(schema_root()/name))


def _add(tables,table,row):
    tables.setdefault(table,[]).append(row)


def _unit(tables,uid,analysis,version,kind,label,start,end,parent=None,note=''):
    _add(tables,'unit',dict(id=uid,analysis_id=analysis,version_id=version,kind=kind,label=label,start=start,end=end,parent_id=parent,note=note))


def expand(tables,layouts,recipes):
    versions={r['id']:r for r in tables.get('text_version',[])}
    all_recipes=list(recipes)
    for layout in layouts:
        vid=layout['version_id'];version=versions.get(vid)
        if version is None:raise ValueError('layout text version missing: '+vid)
        body=version['body'];aid=layout['analysis_id'];pid=layout['paragraph_id']
        if not any(r['id']==aid for r in tables.get('analysis',[])):
            _add(tables,'analysis',dict(id=aid,version_id=vid,method='Declared source-sentence/rendering blocks and unicode_lmn_v1 words; not a certified parse.',scope=layout.get('label','passage'),status='proposed',supersedes=None))
        _unit(tables,pid,aid,vid,'paragraph',layout.get('label','passage'),0,len(body))
        cursor=0
        for segment in layout['segments']:
            text=segment['text'];uid=segment['id']
            if not text or body[cursor:cursor+len(text)]!=text:raise ValueError('layout omits, reorders or changes body at '+uid)
            _unit(tables,uid,aid,vid,segment.get('kind','sentence'),segment.get('label',uid),cursor,cursor+len(text),pid)
            all_recipes.append(dict(parent_id=uid,id_format='{parent}:w{n:03}',kind='word',label_mode='number',note=''))
            if segment.get('source_units'):
                source=layout.get('source_version')
                if not source:raise ValueError('aligned layout needs source_version')
                gid=segment.get('alignment_id','alignment:'+uid)
                _add(tables,'alignment',dict(id=gid,left_version=source,right_version=vid,relation='source_sentence_rendering',note='Declared provisional correspondence; not certified equivalence.',status='proposed'))
                for side,ids in [('left',segment['source_units']),('right',[uid])]:
                    for item in ids:_add(tables,'alignment_member',dict(alignment_id=gid,side=side,unit_id=item))
            cursor+=len(text)
            if cursor<len(body):
                if body[cursor]!=' ':raise ValueError('layout blocks must be separated by one space: '+uid)
                cursor+=1
        if cursor!=len(body):raise ValueError('layout omits body tail: '+vid)
    units={r['id']:r for r in tables.get('unit',[])}
    families={r['id']:re.compile(r['pattern']) for r in tables.get('term_family',[])}
    for recipe in all_recipes:
        parent=units.get(recipe['parent_id'])
        if parent is None:raise ValueError('word recipe parent missing: '+recipe['parent_id'])
        if recipe['id_format'] not in {'{parent}:w{n:03}','{parent}:w{n:04}'}:raise ValueError('unsupported word ID format')
        body=versions[parent['version_id']]['body'];text=body[parent['start']:parent['end']];count=0
        for n,(a,b) in enumerate(word_spans(text),1):
            count=n;uid=recipe['id_format'].format(parent=parent['id'],n=n);token=text[a:b]
            label=token if recipe['label_mode']=='text' else f'written token {n}'
            _unit(tables,uid,parent['analysis_id'],parent['version_id'],recipe['kind'],label,parent['start']+a,parent['start']+b,parent['id'],recipe.get('note',''))
            if 'index' in recipe:
                index=recipe['index'];zone='header_candidate' if a<index['header_end'] else 'body_or_note';query=token.casefold()
                _add(tables,'word_index',dict(unit_id=uid,query_form=query,printed_page=index['printed_page'],pdf_page=index['pdf_page'],scan_leaf=index['scan_leaf'],zone=zone,extraction=index['extraction']))
                for fid in index.get('families',[]):
                    if fid not in families:raise ValueError('word recipe family missing: '+fid)
                    if families[fid].search(query):_add(tables,'term_occurrence',dict(family_id=fid,unit_id=uid,query_form=query,zone=zone))
        if recipe.get('expected_count') is not None and count!=recipe['expected_count']:raise ValueError('word recipe count changed: '+parent['id'])
    return tables


def _check_versions(tables):
    versions={r['id']:r for r in tables.get('text_version',[])}
    if len(versions)!=len(tables.get('text_version',[])):raise ValueError('duplicate text version ID')
    for version in versions.values():
        if not isinstance(version['body'],str) or not version['body'] or '\0' in version['body']:raise ValueError('empty/invalid text body: '+version['id'])
        import hashlib
        if hashlib.sha256(version['body'].encode()).hexdigest()!=version['body_sha256']:raise ValueError('body hash mismatch: '+version['id'])
    return versions


def _check(tables):
    versions=_check_versions(tables)
    units={u['id']:u for u in tables.get('unit',[])}
    if len(units)!=len(tables.get('unit',[])):raise ValueError('duplicate unit ID')
    for u in units.values():
        if u['version_id'] not in versions:raise ValueError('unit text version missing: '+u['id'])
        body=versions[u['version_id']]['body']
        if any(not isinstance(u[x],int) or isinstance(u[x],bool) for x in ('start','end')) or not 0<=u['start']<u['end']<=len(body):raise ValueError('invalid unit span: '+u['id'])
        if u['parent_id']:
            parent=units.get(u['parent_id'])
            if parent is None or parent['analysis_id']!=u['analysis_id'] or parent['version_id']!=u['version_id'] or not parent['start']<=u['start']<u['end']<=parent['end']:raise ValueError('invalid unit parent: '+u['id'])
    for table,rows in tables.items():
        for row in rows:
            if 'id' in row and (not isinstance(row['id'],str) or not row['id']):raise ValueError('invalid ID: '+table)
    return tables


def load(project,*,changes=True,_manifest=None,_blobs=None):
    root=project_root(project);edition=root/'edition';manifest=_manifest if _manifest is not None else read_json(edition/'manifest.json');shape(manifest,'edition.schema.json')
    tables=defaultdict(list);layouts=[];recipes=[];inputs=[];dataset_ids=set();paths=set();passages=[];dependent=[]
    for item in manifest['datasets']:
        if item['path'] in paths:raise ValueError('duplicate dataset path: '+item['path'])
        paths.add(item['path']);path=within(edition,item['path'])
        raw=(_blobs or {}).get(item['path'])
        if raw is None:raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=item['sha256']:raise ValueError('dataset fingerprint mismatch: '+item['path'])
        bundle=parse_json(raw);shape(bundle,'bundle.schema.json')
        if bundle['id'] in dataset_ids:raise ValueError('duplicate dataset ID: '+bundle['id'])
        dataset_ids.add(bundle['id']);inputs.append(dict(path=item['path'],sha256=item['sha256']))
        if bundle['format']=='humboldt.passage' and bundle.get('section'):
            passages.append(dict(id=bundle['id'],section=bundle['section'],version_ids=list(dict.fromkeys([r['id'] for r in bundle['tables'].get('text_version',[])]+[r['version_id'] for r in bundle.get('layouts',[])]))))
        if bundle.get('requires_versions'):
            dependent.append(bundle)
            continue
        for table,rows in bundle['tables'].items():tables[table].extend(rows)
        layouts.extend(bundle.get('layouts',[]));recipes.extend(bundle.get('word_recipes',[]))
    _check_versions(tables)
    tables=expand(dict(tables),layouts,recipes);_check(tables)
    def materialize(projected):
        # Dependencies are explicit. A reviewed apparatus can become available
        # between two events, so later proposals may amend its records too.
        while True:
            known={r['id'] for r in projected.get('text_version',[])}
            ready=[b for b in dependent if set(b['requires_versions'])<=known]
            if not ready:return
            for bundle in ready:
                for table,rows in bundle['tables'].items():projected.setdefault(table,[]).extend(copy.deepcopy(rows))
                _check_versions(projected)
                expand(projected,bundle.get('layouts',[]),bundle.get('word_recipes',[]))
                dependent.remove(bundle)
            _check(projected)
    events=[];journal=[]
    if changes:
        for folder in ['proposals','changes']:
            directory=within(edition,folder)
            if (edition/folder).is_symlink():raise ValueError('journal directory symlinks are not accepted')
            for path in sorted(directory.glob('*.json')):
                if path.is_symlink():raise ValueError('journal symlinks are not accepted')
                within(edition,str(path.relative_to(edition)))
                raw=path.read_bytes();event=parse_json(raw)
                if raw!=(canonical(event)+'\n').encode('utf-8'):raise ValueError('journal event must use canonical bytes: '+path.name)
                if event.get('id')!=path.stem or event.get('event_type')!=('proposal' if folder=='proposals' else 'decision'):raise ValueError('journal filename/type does not match event: '+path.name)
                events.append(event);journal.append(dict(path=str(path.relative_to(edition)),sha256=hashlib.sha256(raw).hexdigest()))
        if events:
            from .revisions import apply
            tables,history=apply(tables,events,materialize=materialize)
            for name in ('revision_history','change_impact'):
                tables[name]=history.get(name,[])
            _check(tables)
    materialize(tables)
    if dependent:raise ValueError('unresolved dataset requires_versions: '+', '.join(b['id'] for b in dependent))
    # A new text inherits its predecessor's logical passage membership, not its
    # verification status or semantic alignments. This works without § titles.
    for row in tables.get('revision_history',[]):
        if row['status']=='accepted' and row['kind']=='text_version' and row['field']=='body':
            info=json.loads(row['metadata_json']);previous=info.get('previous_version_id');new=info.get('new_version_id')
            for passage in passages:
                if previous in passage['version_ids'] and new not in passage['version_ids']:passage['version_ids'].append(new)
    defaults=manifest.get('reading_defaults',[]);sections=set();versions={r['id']:r for r in tables['text_version']}
    for choice in defaults:
        if choice['section'] in sections:raise ValueError('duplicate reading default section')
        sections.add(choice['section'])
        for field in ('source_id','target_id'):
            if field in choice and choice[field] not in versions:raise ValueError('reading default version missing: '+choice[field])
    metadata=dict(edition_id=manifest['id'],record_schema_version=manifest['schema_version'],inputs=inputs,journal=journal,resources=manifest.get('resources',[]),dataset_ids=sorted(dataset_ids),passages=passages,reading_defaults=defaults,input_digest=fingerprint(dict(manifest=manifest,journal=journal)))
    return tables,metadata


def _populate(db,project,*,changes=True,_manifest=None,_blobs=None):
    tables,meta=load(project,changes=changes,_manifest=_manifest,_blobs=_blobs)
    database.migrate(db)
    database.insert_records(db,tables)
    for key,value in meta.items():db.execute('INSERT INTO build_metadata(key,value_json) VALUES (?,?)',(key,canonical(value)))
    db.commit()
    result=database.report(db)
    if result.get('foreign_key_errors') or result.get('integrity')!='ok':raise ValueError('database integrity failed: '+canonical(result))
    return meta


def build(project,output,*,changes=True,force=False):
    from .revisions import project_lock
    with project_lock(project):
        return _build(project,output,changes=changes,force=force)


def _build(project,output,*,changes=True,force=False):
    root=project_root(project);output=Path(output).resolve();output.parent.mkdir(parents=True,exist_ok=True)
    # Never permit a typo to overwrite authoritative inputs, code or historical artifacts.
    if output==root or output.is_relative_to(root) and output.parts[len(root.parts)] not in {'build'}:raise ValueError('project build output must be under build/; external fresh output paths are also allowed')
    if output.exists() and not force:raise ValueError('output exists; choose a fresh path or use --force for build/ output')
    if output.exists() and not output.is_relative_to(root/'build'):raise ValueError('force replacement is confined to project build/')
    fd,temp=tempfile.mkstemp(prefix='.'+output.name+'.',suffix='.sqlite',dir=output.parent);os.close(fd);temporary=Path(temp)
    db=database.connect(temporary)
    try:
        _populate(db,root,changes=changes)
        digest=database.logical_digest(db)
        db.execute('INSERT INTO build_metadata(key,value_json) VALUES (?,?)',('logical_digest',canonical(digest)));db.commit()
        database.seal(db);db.commit();report=database.report(db)
        db.close();db=None
        if output.exists() and not force:raise ValueError('output appeared during build; refusing replacement')
        if force:os.replace(temporary,output)
        else:publish_exclusive(temporary,output);temporary.unlink()
        sync_directory(output.parent)
        return dict(report,logical_digest=digest,output=str(output))
    finally:
        if db is not None:db.close()
        if temporary.exists():temporary.unlink()


def validate(project,*,sources=False):
    root=project_root(project);db=database.connect()
    try:
        meta=_populate(db,root);report=database.report(db);report['logical_digest']=database.logical_digest(db)
    finally:db.close()
    attachments=[]
    for resource in meta['resources']:
        path=within(root,resource['path']);state='available' if path.is_file() else 'not_in_bundle'
        if sources and path.is_file() and file_hash(path)!=resource['sha256']:raise ValueError('source attachment fingerprint mismatch: '+resource['path'])
        attachments.append(dict(path=resource['path'],status=state,checked=bool(sources and path.is_file())))
    return dict(report,edition_id=meta['edition_id'],input_digest=meta['input_digest'],datasets=len(meta['inputs']),attachments=attachments)


def verify(project,reference):
    """Compare an explicit immutable baseline, without freezing future edits."""
    root=project_root(project);baseline=read_json(reference)
    if not isinstance(baseline,dict) or type(baseline.get('schema_version')) is not int or baseline['schema_version']!=1:
        raise ValueError('reference must be a version 1 baseline/release object')
    if baseline.get('format')=='humboldt.baseline':
        db=database.connect()
        try:
            _populate(db,root,changes=False,_manifest=baseline['manifest'])
            actual=database.logical_digest(db)
        finally:db.close()
        scope='immutable base records named in the baseline manifest; current journal and added datasets are separate'
    elif baseline.get('format')=='humboldt.release':
        actual=validate(root)['logical_digest'];scope='current complete edition against the selected release'
    else:raise ValueError('reference must be a humboldt.baseline or humboldt.release record')
    if actual!=baseline['logical_digest']:raise ValueError('logical content differs from selected baseline; investigate or choose the correct approved reference for intentional changes')
    return dict(matches=True,logical_digest=actual,reference=str(reference),scope=scope)


def add_dataset(project,source):
    root=project_root(project);bundle=read_json(source);shape(bundle,'bundle.schema.json')
    if bundle['format']!='humboldt.passage':raise ValueError('import expects a humboldt.passage dataset')
    from .revisions import project_lock
    with project_lock(root):
        manifest_path=root/'edition/manifest.json';manifest=read_json(manifest_path)
        safe_id=re.sub(r'[^A-Za-z0-9_-]','-',bundle['id'])
        if safe_id!=bundle['id']:raise ValueError('passage dataset ID must use letters/numbers/_/-')
        relative='passages/'+safe_id+'/records.json';dest=within(root/'edition',relative)
        if dest.exists():raise ValueError('dataset already exists: '+bundle['id'])
        raw=(json.dumps(bundle,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n').encode('utf-8')
        manifest['datasets'].append(dict(path=relative,sha256=hashlib.sha256(raw).hexdigest()))
        candidate=database.connect()
        try:_populate(candidate,root,_manifest=manifest,_blobs={relative:raw})
        finally:candidate.close()
        # Publish only after validation. An interruption between these two
        # publications can leave an unreferenced file, never an invalid manifest.
        atomic_json(dest,bundle,replace=False)
        atomic_json(manifest_path,manifest)
    return dict(id=bundle['id'],path=relative)
