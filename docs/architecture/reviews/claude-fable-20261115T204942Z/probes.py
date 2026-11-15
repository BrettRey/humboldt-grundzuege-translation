"""Bounded reproductions of Fable findings, using temporary synthetic editions."""
from contextlib import closing
from datetime import datetime,timezone
import hashlib,json,shutil,subprocess,sys,tempfile,threading
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request,urlopen
ROOT=Path.cwd();sys.path.insert(0,str(ROOT/'src'))
from humboldt import database,ingest,queries,reader,revisions
from humboldt.records import read_json,file_hash
RUN=Path(__file__).resolve().parent
results={"recorded_at":datetime.now(timezone.utc).isoformat()}

def fixture(base,name):
    p=base/name;shutil.copytree(ROOT/'tests/fixtures/minimal',p);return p

def edit_bundle(project,change):
    path=project/'edition/passages/minimal.json';data=read_json(path);change(data)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    mpath=project/'edition/manifest.json';m=read_json(mpath);m['datasets'][0]['sha256']=file_hash(path);mpath.write_text(json.dumps(m,indent=2)+'\n')

def proposal(project,kind='term_sense',target='fixture:sense',field='rule',value='Synthetic changed rule.'):
    return revisions.propose(project,kind=kind,target_id=target,field=field,value=value,by='Synthetic contributor',reason='Architecture review probe')

def rejected(call):
    try:call()
    except ValueError as e:return {"type":type(e).__name__,"message":str(e)}
    raise AssertionError('Expected rejection did not occur')

with tempfile.TemporaryDirectory(prefix='humboldt-fable-probes-') as temporary:
    base=Path(temporary)
    p=fixture(base,'row-fingerprint');event=proposal(p);revisions.decide(p,event['id'],accept=False,by='Synthetic editor',reason='Rejected synthetic proposal')
    edit_bundle(p,lambda d:d['tables']['term_sense'][0].update(label='Corrected synthetic label'))
    results['replay_after_unrelated_label_edit']=rejected(lambda:ingest.validate(p))

    p=fixture(base,'text-correction');event=proposal(p,'text_version','fixture:source:v1','body','Alpha theta. Gamma delta.')
    revisions.decide(p,event['id'],accept=True,by='Synthetic editor',reason='Accepted synthetic text correction')
    tables,meta=ingest.load(p);history=tables['revision_history'][0];new_id=json.loads(history['metadata_json'])['new_version_id']
    ingest.build(p,p/'build/edition.sqlite')
    with closing(database.connect(p/'build/edition.sqlite',readonly=True)) as db:
        sections=queries.sections(db);listed={v['id'] for s in sections for v in s['versions']}
        assert new_id not in listed
        assert queries.entity(db,'text_version',new_id)['record']['body']=='Alpha theta. Gamma delta.'
    bundle=dict(format='humboldt.passage',schema_version=1,id='new-revision-apparatus',tables={},layouts=[dict(version_id=new_id,analysis_id='probe:analysis',paragraph_id='probe:paragraph',segments=[dict(id='probe:sentence',text='Alpha theta. Gamma delta.',kind='sentence')])])
    path=base/'apparatus.json';path.write_text(json.dumps(bundle))
    results['corrected_version_apparatus']=dict(version_id=new_id,unit_kinds=sorted({u['kind'] for u in tables['unit'] if u['version_id']==new_id}),visible_in_any_section=False,retrievable_by_id=True,import_rejection=rejected(lambda:ingest.add_dataset(p,path)))

    p=fixture(base,'crlf-form');edit_bundle(p,lambda d:d['tables']['term_sense'][0].update(rule='Line one\nLine two'))
    ingest.build(p,p/'build/edition.sqlite')
    with closing(database.connect(p/'build/edition.sqlite',readonly=True)) as db:target=dict(db.execute("SELECT * FROM term_sense WHERE id='fixture:sense'").fetchone())
    server=reader.make_server(p,p/'build/edition.sqlite');thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        payload=dict(kind='term_sense',target_id='fixture:sense',field='rule',value='Line one\r\nLine two',by='Synthetic reader',reason='CRLF form probe',evidence='[]',target_sha256=revisions.fingerprint(target))
        request=Request(server.reader_url+'proposal',data=urlencode(payload).encode(),headers={'Content-Type':'application/x-www-form-urlencoded'})
        with urlopen(request,timeout=5) as response:draft=json.load(response)
    finally:server.shutdown();server.server_close();thread.join(timeout=2)
    event=revisions.propose(p,kind=draft['kind'],target_id=draft['target_id'],field=draft['field'],value=draft['value'],by=draft['by'],reason=draft['reason'],expected_sha256=draft['target_sha256'])
    revisions.decide(p,event['id'],accept=True,by='Synthetic editor',reason='Accept synthetic newline-only change')
    projected,_=ingest.load(p);rule=projected['term_sense'][0]['rule']
    assert '\r\n' in rule and rule.replace('\r\n','\n')==target['rule']
    results['crlf_form']=dict(http_draft_retains_crlf=True,newline_only_change_accepted=True,lf_paragraphs=len(list(revisions._paragraphs('Alpha.\n\nBeta.'))),crlf_paragraphs=len(list(revisions._paragraphs('Alpha.\r\n\r\nBeta.'))),native_browser_serialization_tested=False)

    p=fixture(base,'clone-a');q=fixture(base,'clone-b');a=proposal(p);b=proposal(q,value='Other synthetic change.')
    shutil.copy2(q/'edition/proposals'/(b['id']+'.json'),p/'edition/proposals'/(b['id']+'.json'))
    results['two_clone_journal_merge']=rejected(lambda:ingest.load(p))

    p=fixture(base,'new-evidence');bundle=read_json(p/'edition/passages/minimal.json');ev=dict(bundle['tables']['evidence'][0]);ev.update(id='probe:new-evidence',statement='Additional synthetic evidence for a review test')
    addition=dict(format='humboldt.passage',schema_version=1,id='synthetic-evidence-addition',tables={'evidence':[ev]})
    path=base/'new-evidence.json';path.write_text(json.dumps(addition));ingest.add_dataset(p,path)
    event=revisions.propose(p,kind='term_sense',target_id='fixture:sense',field='rule',value='Synthetic evidence-supported change.',by='Synthetic contributor',reason='Test imported evidence ID',evidence=[ev['id']])
    results['new_evidence_via_dataset_import']=dict(supported=True,usable_in_proposal=event['evidence']==[ev['id']])

manifest=read_json(ROOT/'edition/manifest.json')
results['live_state']=dict(real_journal_events=len(revisions.read_events(ROOT)),git_head_present=subprocess.run(['git','rev-parse','--verify','HEAD'],cwd=ROOT,capture_output=True).returncode==0,declared_translation_resources=[r['path'] for r in manifest.get('resources',[]) if r['path'].startswith('translations/')],frozen_baseline_release_present=(ROOT/'releases/0.1.0/release.json').is_file(),tracked_digest_record=(ROOT/'docs/architecture/verification.json').is_file())
with closing(database.connect(ROOT/'build/edition.sqlite',readonly=True)) as db:
    records=reader.source_resources(ROOT,db)
    results['live_state']['blocked_existing_translation_attachments']=[r['path'] for r in records if r['path'].startswith('translations/') and (ROOT/r['path']).is_file() and not r['available']]
    results['live_state']['multiline_text_versions']=db.execute("SELECT count(*) FROM text_version WHERE instr(body,char(10))>0").fetchone()[0]
inputs=read_json(RUN/'inputs.json');assert all(file_hash(ROOT/name)==sha for name,sha in inputs['files'].items())
results['reviewed_files_unchanged']=len(inputs['files'])
(RUN/'probes.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(results,ensure_ascii=False,indent=2))
