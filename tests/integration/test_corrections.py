"""Complete authoring paths from the architecture review, on synthetic data."""
from contextlib import closing
import copy
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from urllib.parse import urlencode
from urllib.request import Request,urlopen

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from humboldt import database,ingest,queries,reader,render,revisions as rev
from humboldt.records import file_hash,read_json,record_id


class CorrectionWorkflows(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'project'
        shutil.copytree(ROOT/'tests/fixtures/minimal',self.root)

    def amend_base(self,change):
        path=self.root/'edition/passages/minimal.json';bundle=read_json(path);change(bundle)
        path.write_text(json.dumps(bundle,ensure_ascii=False)+'\n')
        path=self.root/'edition/manifest.json';manifest=read_json(path)
        manifest['datasets'][0]['sha256']=file_hash(self.root/'edition/passages/minimal.json')
        path.write_text(json.dumps(manifest)+'\n')

    def propose(self,*,kind='term_sense',target='fixture:sense',field='rule',value='Synthetic changed rule.'):
        return rev.propose(self.root,kind=kind,target_id=target,field=field,value=value,by='Synthetic reader',reason='Synthetic correction test')

    def decide(self,p,accept=True):
        return rev.decide(self.root,p['id'],accept=accept,by='Synthetic editor',reason='Explicit synthetic disposition')

    def server(self):
        path=self.root/'build/edition.sqlite';ingest.build(self.root,path)
        server=reader.make_server(self.root,path)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        def close():server.shutdown();server.server_close();thread.join(timeout=2)
        self.addCleanup(close);return server

    def test_corrected_version_accepts_reviewed_apparatus_and_later_amendments(self):
        old='fixture:source:v1'
        p=self.propose(kind='text_version',target=old,field='body',value='Alpha theta. Gamma delta.')
        self.decide(p);tables,_=ingest.load(self.root)
        new=json.loads(tables['revision_history'][0]['metadata_json'])['new_version_id']
        bundle=dict(format='humboldt.passage',schema_version=1,id='reviewed-apparatus',section='999',requires_versions=[new],
                    tables={'alignment':[dict(id='reviewed:alignment',left_version=new,right_version='fixture:english:v1',relation='source_sentence_rendering',status='proposed',note='Synthetic reviewed correspondence')],
                            'alignment_member':[dict(alignment_id='reviewed:alignment',side='left',unit_id='reviewed:s1'),dict(alignment_id='reviewed:alignment',side='right',unit_id='fixture:english:v1:s1')]},
                    layouts=[dict(version_id=new,analysis_id='reviewed:analysis',paragraph_id='reviewed:p',segments=[dict(id='reviewed:s1',text='Alpha theta.',kind='sentence'),dict(id='reviewed:s2',text='Gamma delta.',kind='sentence')])])
        path=Path(self.temp.name)/'apparatus.json';path.write_text(json.dumps(bundle));ingest.add_dataset(self.root,path)
        self.decide(self.propose(kind='alignment',target='reviewed:alignment',field='note',value='Synthetic amended correspondence note.'))
        self.decide(self.propose(kind='text_version',target=new,field='transcription_status',value='synthetic_explicit_recheck'))
        # Metadata amendments must not incorrectly mark a text as superseded.
        self.propose(kind='text_version',target=new,field='body',value='Alpha revised. Gamma delta.')
        ingest.build(self.root,self.root/'build/edition.sqlite')
        with closing(database.connect(self.root/'build/edition.sqlite',readonly=True)) as db:
            passage=queries.passage(db,'999');versions={v['id']:v for v in passage['versions']}
            self.assertIn(new,versions);self.assertEqual([b['id'] for b in versions[new]['blocks']],['reviewed:s1','reviewed:s2'])
            self.assertEqual(versions[old]['body'],'Alpha beta. Gamma delta.')
            self.assertEqual(versions[new]['transcription_status'],'synthetic_explicit_recheck')
            self.assertEqual(queries.entity(db,'alignment','reviewed:alignment')['record']['note'],'Synthetic amended correspondence note.')
            self.assertIn(new,render.entity_view(queries.entity(db,'text_version',old)))
            self.assertEqual(queries.entity(db,'text_version',new)['predecessor_id'],old)
        # Exercise the fixed lifecycle in the portable product as well as the
        # checkout: no original PDFs, old builders or sibling tmp databases.
        shutil.copytree(ROOT/'src',self.root/'src',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        for name in ('humboldt','pyproject.toml'):shutil.copy2(ROOT/name,self.root/name)
        from humboldt.release import create
        package=Path(self.temp.name)/'corrected-release'
        create(self.root,self.root/'build/edition.sqlite',package)
        process=subprocess.run([sys.executable,'humboldt','passage','999'],cwd=package,capture_output=True,text=True)
        self.assertEqual(process.returncode,0,process.stderr)
        versions={v['id']:v for v in json.loads(process.stdout)['versions']}
        self.assertEqual([b['id'] for b in versions[new]['blocks']],['reviewed:s1','reviewed:s2'])

    def test_section_inheritance_does_not_require_new_apparatus_or_section_title(self):
        p=self.propose(kind='text_version',target='fixture:source:v1',field='body',value='Alpha theta. Gamma delta.')
        self.decide(p);tables,meta=ingest.load(self.root)
        new=json.loads(tables['revision_history'][0]['metadata_json'])['new_version_id']
        self.assertIn(new,meta['passages'][0]['version_ids'])

    def test_unrelated_base_metadata_changes_preserve_recorded_decisions_with_context_warning(self):
        p=self.propose();self.decide(p)
        self.amend_base(lambda b:b['tables']['term_sense'][0].update(label='Synthetic corrected label'))
        tables,_=ingest.load(self.root)
        row=tables['term_sense'][0];self.assertEqual(row['rule'],'Synthetic changed rule.')
        self.assertEqual(row['label'],'Synthetic corrected label')
        metadata=json.loads(tables['revision_history'][0]['metadata_json'])
        self.assertTrue(metadata['context_changed_since_proposal'])
        self.assertEqual(metadata['original_target_snapshot'],p['target_snapshot'])
        self.assertTrue(any(r['impact']=='proposal_context_review_required' for r in tables['change_impact']))

    def test_pending_proposal_with_changed_context_can_be_rejected_but_not_accepted(self):
        p=self.propose()
        self.amend_base(lambda b:b['tables']['term_sense'][0].update(label='Synthetic corrected label'))
        ingest.validate(self.root)
        with self.assertRaises(rev.RevisionConflict):self.decide(p)
        self.decide(p,False);ingest.validate(self.root)

    def test_changed_original_target_value_is_not_silently_rebased(self):
        p=self.propose()
        self.amend_base(lambda b:b['tables']['term_sense'][0].update(rule='Unjournaled synthetic rule'))
        with self.assertRaisesRegex(rev.RevisionConflict,p['id']):ingest.load(self.root)

    def test_journal_metadata_change_keeps_pending_acceptance_guard(self):
        p=self.propose()
        self.decide(self.propose(field='label',value='Synthetic journaled label'))
        with self.assertRaises(rev.RevisionConflict):self.decide(p)
        self.decide(p,False);tables,_=ingest.load(self.root)
        self.assertEqual(tables['term_sense'][0]['label'],'Synthetic journaled label')
        self.assertEqual(tables['term_sense'][0]['rule'],'Synthetic original rule.')

    def test_crlf_http_draft_is_normalized_and_noop_is_rejected(self):
        self.amend_base(lambda b:b['tables']['term_sense'][0].update(rule='Line one\nLine two'))
        server=self.server()
        with closing(database.connect(self.root/'build/edition.sqlite',readonly=True)) as db:
            target=dict(db.execute("SELECT * FROM term_sense WHERE id='fixture:sense'").fetchone())
        fields=dict(kind='term_sense',target_id='fixture:sense',field='rule',value='Line one\r\nLine two',by='Synthetic reader',reason='Line one\r\nLine two',evidence='[]',target_sha256=rev.fingerprint(target))
        request=Request(server.reader_url+'proposal',data=urlencode(fields).encode(),headers={'Content-Type':'application/x-www-form-urlencoded'})
        with urlopen(request,timeout=5) as response:draft=json.load(response)
        self.assertEqual(draft['value'],target['rule']);self.assertNotIn('\r',draft['reason'])
        with self.assertRaisesRegex(rev.RevisionError,'no change'):self.propose(value=draft['value'])
        self.assertEqual(rev.read_events(self.root),[])

    def test_text_authoring_normalizes_lines_and_historical_crlf_spans_remain_valid(self):
        p=self.propose(kind='text_version',target='fixture:source:v1',field='body',value='Alpha theta.\r\n\r\nGamma delta.')
        self.assertEqual(p['value'],'Alpha theta.\n\nGamma delta.');self.decide(p)
        tables,_=ingest.load(self.root)
        new=json.loads(tables['revision_history'][0]['metadata_json'])['new_version_id']
        paragraphs=[u for u in tables['unit'] if u['version_id']==new and u['kind']=='paragraph']
        self.assertEqual(len(paragraphs),2)
        body='Alpha.\r\n\r\nBeta.'
        self.assertEqual([body[a:b] for a,b in rev._paragraphs(body)],['Alpha.','Beta.'])

    def test_composite_rendering_and_form_amendments_preserve_history(self):
        tables,_=ingest.load(self.root)
        rendering=tables['sense_rendering'][0];rid=record_id('sense_rendering',rendering)
        p=self.propose(kind='sense_rendering',target=json.dumps(json.loads(rid),indent=2),field='rendering',value='synthetic concept')
        self.assertEqual(p['target_id'],rid);self.decide(p)
        form=tables['lexeme_form'][0];fid=record_id('lexeme_form',form)
        self.decide(self.propose(kind='lexeme_form',target=fid,field='form',value='SyntheticBeta'))
        ingest.build(self.root,self.root/'build/edition.sqlite')
        with closing(database.connect(self.root/'build/edition.sqlite',readonly=True)) as db:
            entry=queries.entity(db,'sense_rendering',rid)
            self.assertEqual(entry['record']['rendering'],'synthetic concept')
            self.assertIn('Revise rendering',render.entity_view(entry))
            key=json.dumps(dict(lexeme_id=form['lexeme_id'],form='SyntheticBeta'))
            entry=queries.entity(db,'lexeme_form',key);self.assertEqual(entry['record']['query_key'],'syntheticbeta')
            self.assertTrue(entry['history']['revisions'])
            self.assertTrue(queries.search(db,'synthetic concept'))

    def test_invalid_accepted_record_amendment_is_refused_before_publication(self):
        tables,_=ingest.load(self.root);row=tables['alignment_member'][0]
        p=self.propose(kind='alignment_member',target=record_id('alignment_member',row),field='unit_id',value='missing:unit')
        with self.assertRaises((ValueError,sqlite3.DatabaseError)):self.decide(p)
        self.assertEqual(len(rev.read_events(self.root)),1)
        ingest.validate(self.root)

    def test_declared_translation_attachment_can_be_read_without_widening_allowlist(self):
        folder=self.root/'translations';folder.mkdir();(folder/'fixture.json').write_text('{"synthetic":true}')
        (folder/'unlisted.json').write_text('not declared')
        path=self.root/'edition/manifest.json';manifest=read_json(path)
        manifest['resources'].append(dict(path='translations/fixture.json',sha256=file_hash(folder/'fixture.json'),required=False));path.write_text(json.dumps(manifest))
        server=self.server()
        with urlopen(server.reader_url+'source?'+urlencode({'path':'translations/fixture.json'}),timeout=5) as response:
            self.assertEqual(response.read(),b'{"synthetic":true}')
            self.assertEqual(response.headers['Content-Disposition'],'attachment')
        from urllib.error import HTTPError
        with self.assertRaises(HTTPError) as caught:urlopen(server.reader_url+'source?'+urlencode({'path':'translations/unlisted.json'}),timeout=5)
        caught.exception.close()

    def test_missing_dependency_import_is_not_published(self):
        before=(self.root/'edition/manifest.json').read_bytes()
        bundle=dict(format='humboldt.passage',schema_version=1,id='unresolved',tables={},requires_versions=['missing:version'])
        path=Path(self.temp.name)/'missing.json';path.write_text(json.dumps(bundle))
        with self.assertRaisesRegex(ValueError,'requires_versions'):ingest.add_dataset(self.root,path)
        self.assertEqual((self.root/'edition/manifest.json').read_bytes(),before)

    def test_baseline_comparison_distinguishes_frozen_base_from_new_approved_content(self):
        initial=ingest.validate(self.root)['logical_digest']
        reference=Path(self.temp.name)/'baseline.json'
        record=dict(format='humboldt.baseline',schema_version=1,manifest=read_json(self.root/'edition/manifest.json'),logical_digest=initial)
        reference.write_text(json.dumps(record))
        self.decide(self.propose())
        self.assertTrue(ingest.verify(self.root,reference)['matches'])
        release=dict(format='humboldt.release',schema_version=1,logical_digest=initial)
        reference.write_text(json.dumps(release))
        with self.assertRaisesRegex(ValueError,'differs'):ingest.verify(self.root,reference)
        release['logical_digest']=ingest.validate(self.root)['logical_digest'];reference.write_text(json.dumps(release))
        self.assertTrue(ingest.verify(self.root,reference)['matches'])
        release['schema_version']=True;reference.write_text(json.dumps(release))
        with self.assertRaisesRegex(ValueError,'version 1'):ingest.verify(self.root,reference)


if __name__=='__main__':unittest.main()
