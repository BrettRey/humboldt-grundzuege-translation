"""Portable reader/editor workflows, without historical builders or PDF inputs."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from humboldt import database,ingest
from humboldt.records import canonical,read_json

FIXTURE=ROOT/'tests/fixtures/minimal'


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'project';shutil.copytree(FIXTURE,self.root)

    def command(self,*args,ok=True):
        result=subprocess.run([sys.executable,str(ROOT/'humboldt'),'--project',str(self.root),*args],capture_output=True,text=True)
        if ok:self.assertEqual(result.returncode,0,result.stderr)
        else:self.assertNotEqual(result.returncode,0)
        return result

    def test_cli_propose_accept_reject_and_old_reading(self):
        self.command('build')
        results=json.loads(self.command('search','term').stdout);self.assertTrue(results)
        p=json.loads(self.command('propose','--kind','term_sense','--id','fixture:sense','--field','rule','--value','Synthetic revised rule.','--by','Fixture contributor','--reason','Synthetic workflow check','--evidence','fixture:evidence').stdout)
        self.command('decide',p['id'],'--accept','--by','Fixture editor','--reason','Synthetic acceptance, not scholarly review')
        self.command('build','--force')
        db=database.connect(self.root/'build/edition.sqlite',readonly=True)
        try:
            self.assertEqual(db.execute("SELECT rule FROM term_sense WHERE id='fixture:sense'").fetchone()[0],'Synthetic revised rule.')
            history=db.execute('SELECT * FROM revision_history').fetchone();self.assertIn('Synthetic original rule.',history['old_value_json'])
            self.assertGreater(db.execute('SELECT count(*) FROM change_impact').fetchone()[0],0)
        finally:db.close()
        # Base data stays untouched; rejecting a subsequent proposal is explicit.
        self.assertEqual(read_json(self.root/'edition/passages/minimal.json')['tables']['term_sense'][0]['rule'],'Synthetic original rule.')
        p2=json.loads(self.command('propose','--kind','decision','--id','fixture:rule','--field','resolution','--value','Synthetic discarded alternative.','--by','Fixture contributor','--reason','Synthetic alternative').stdout)
        self.command('decide',p2['id'],'--reject','--by','Fixture editor','--reason','Synthetic rejection')
        self.command('build','--force')
        db=database.connect(self.root/'build/edition.sqlite',readonly=True)
        try:self.assertEqual(db.execute("SELECT resolution FROM decision WHERE id='fixture:rule'").fetchone()[0],'Synthetic original rule.')
        finally:db.close()

    def test_text_correction_creates_version_and_stale_proposal_fails(self):
        p=json.loads(self.command('propose','--kind','text_version','--id','fixture:source:v1','--field','body','--value','Alpha changed. Gamma delta.','--by','Fixture contributor','--reason','Synthetic text correction').stdout)
        stale=json.loads(self.command('propose','--kind','text_version','--id','fixture:source:v1','--field','body','--value','Alpha other. Gamma delta.','--by','Fixture contributor','--reason','Synthetic conflicting alternative').stdout)
        self.command('decide',p['id'],'--accept','--by','Fixture editor','--reason','Synthetic acceptance')
        self.command('decide',stale['id'],'--accept','--by','Fixture editor','--reason','Must fail as stale',ok=False)
        self.command('build')
        db=database.connect(self.root/'build/edition.sqlite',readonly=True)
        try:
            old=db.execute("SELECT body FROM text_version WHERE id='fixture:source:v1'").fetchone()[0];self.assertEqual(old,'Alpha beta. Gamma delta.')
            rows=db.execute("SELECT id,body,transcription_status FROM text_version WHERE body='Alpha changed. Gamma delta.'").fetchall();self.assertEqual(len(rows),1)
            self.assertNotEqual(rows[0]['id'],'fixture:source:v1')
            self.assertGreater(db.execute('SELECT count(*) FROM change_impact').fetchone()[0],0)
        finally:db.close()

    def test_edition_ids_survive_record_reordering(self):
        first=ingest.build(self.root,self.root/'build/first.sqlite')
        path=self.root/'edition/passages/minimal.json';data=read_json(path)
        for rows in data['tables'].values():rows.reverse()
        data['layouts'].reverse();path.write_text(json.dumps(data))
        manifest=self.root/'edition/manifest.json';meta=read_json(manifest);meta['datasets'][0]['sha256']=hashlib.sha256(path.read_bytes()).hexdigest();manifest.write_text(json.dumps(meta))
        second=ingest.build(self.root,self.root/'build/second.sqlite');self.assertEqual(first['logical_digest'],second['logical_digest'])

    def test_downloaded_proposal_checks_observed_target_and_records_attribution(self):
        from humboldt.revisions import fingerprint
        tables,_=ingest.load(self.root)
        target=next(r for r in tables['term_sense'] if r['id']=='fixture:sense')
        draft=dict(format='humboldt.proposal-draft',schema_version=1,
                   kind='term_sense',target_id=target['id'],field='rule',
                   value='Synthetic downloaded correction.',by='Fixture reader',
                   reason='Synthetic draft round trip',evidence=['fixture:evidence'],
                   target_sha256='0'*64)
        path=Path(self.temp.name)/'draft.json';path.write_text(json.dumps(draft))
        self.command('import-proposal',str(path),ok=False)
        self.assertEqual(json.loads(self.command('history').stdout),[])
        draft['target_sha256']=fingerprint(target);path.write_text(json.dumps(draft))
        proposal=json.loads(self.command('import-proposal',str(path)).stdout)
        self.assertEqual(proposal['by'],'Fixture reader')
        self.command('decide',proposal['id'],'--accept','--by','Fixture editor','--reason','Synthetic accepted draft')
        events=json.loads(self.command('history','--id',target['id']).stdout)
        self.assertEqual([e['by'] for e in events],['Fixture reader','Fixture editor'])

    def test_pending_journal_change_prevents_releasing_stale_build(self):
        self.command('build')
        self.command('propose','--kind','term_sense','--id','fixture:sense',
                     '--field','rule','--value','Synthetic pending change.',
                     '--by','Fixture reader','--reason','Synthetic pending proposal')
        output=Path(self.temp.name)/'stale-release'
        result=self.command('release','--output',str(output),ok=False)
        self.assertIn('inputs or journal changed',result.stderr)
        self.assertFalse(output.exists())

    def test_release_runs_without_developer_checkout_or_raw_sources(self):
        # Code and durable data are sufficient; no sibling tools or tmp database.
        isolated=Path(self.temp.name)/'isolated';shutil.copytree(self.root,isolated)
        shutil.copytree(ROOT/'src',isolated/'src',ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copy2(ROOT/'humboldt',isolated/'humboldt');shutil.copy2(ROOT/'pyproject.toml',isolated/'pyproject.toml')
        for name in ('LICENSE','LICENSE-CONTENT','NOTICE.md','CITATION.cff'):
            if (ROOT/name).is_file():shutil.copy2(ROOT/name,isolated/name)
        (isolated/'examples').mkdir();shutil.copy2(FIXTURE/'edition/passages/minimal.json',isolated/'examples/minimal-passage.json')
        shutil.rmtree(isolated/'sources')
        for args in [('validate',),('build',),('search','term'),('trace','fixture:source:v1:s1:w002')]:
            r=subprocess.run([sys.executable,'humboldt',*args],cwd=isolated,capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr)
        release=Path(self.temp.name)/'release'
        r=subprocess.run([sys.executable,'humboldt','release','--output',str(release)],cwd=isolated,capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr)
        r=subprocess.run([sys.executable,'humboldt','validate'],cwd=release,capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr)
        self.assertFalse((release/'tmp').exists());self.assertFalse((release/'tools').exists())
        self.assertTrue((release/'examples/minimal-passage.json').is_file())
        self.assertEqual((release/'LICENSE').read_bytes(),(ROOT/'LICENSE').read_bytes())
        manifest=read_json(release/'release.json')
        for name,digest in manifest['files'].items():self.assertEqual(hashlib.sha256((release/name).read_bytes()).hexdigest(),digest,name)


if __name__=='__main__':unittest.main()
