"""Record and build contracts against tiny explicit synthetic fixtures."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from humboldt import database,ingest
from humboldt.records import canonical,read_json,validate_shape

FIXTURE=Path(__file__).resolve().parents[1]/'fixtures/minimal'


class IngestTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'project';shutil.copytree(FIXTURE,self.root)

    def change_bundle(self,change):
        path=self.root/'edition/passages/minimal.json';data=read_json(path);change(data);path.write_text(json.dumps(data)+'\n')
        mpath=self.root/'edition/manifest.json';manifest=read_json(mpath);manifest['datasets'][0]['sha256']=hashlib.sha256(path.read_bytes()).hexdigest();mpath.write_text(json.dumps(manifest))

    def test_rebuild_without_sources_and_same_logical_content(self):
        (self.root/'sources/fixture.txt').unlink()
        first=ingest.build(self.root,self.root/'build/one.sqlite')
        second=ingest.build(self.root,self.root/'build/two.sqlite')
        self.assertEqual(first['logical_digest'],second['logical_digest'])
        db=database.connect(self.root/'build/one.sqlite',readonly=True)
        try:
            self.assertEqual(db.execute('SELECT count(*) FROM alignment').fetchone()[0],2)
            self.assertEqual(db.execute("SELECT text FROM unit_text WHERE id='fixture:source:v1:s1:w002'").fetchone()[0],'beta')
        finally:db.close()
        self.assertEqual(ingest.validate(self.root)['attachments'][0]['status'],'not_in_bundle')

    def test_declared_hash_and_source_body_hash_are_enforced(self):
        p=self.root/'edition/passages/minimal.json';p.write_text(p.read_text()+' ')
        with self.assertRaisesRegex(ValueError,'fingerprint'):ingest.load(self.root)
        # Restore fixture and introduce a declared but internally corrupt text.
        shutil.copy2(FIXTURE/'edition/passages/minimal.json',p)
        self.change_bundle(lambda d:d['tables']['text_version'][0].update(body='changed'))
        with self.assertRaisesRegex(ValueError,'body hash'):ingest.load(self.root)

    def test_schema_versions_and_unknown_tables_fail(self):
        with self.assertRaises(ValueError):validate_shape(True,{'const':1})
        with self.assertRaises(ValueError):validate_shape(0,{'const':False})
        self.change_bundle(lambda d:d.update(schema_version=True))
        with self.assertRaises(ValueError):ingest.load(self.root)
        self.change_bundle(lambda d:d.update(schema_version=99))
        with self.assertRaises(ValueError):ingest.load(self.root)
        self.change_bundle(lambda d:(d.update(schema_version=1),d['tables'].update(arbitrary=[])))
        with self.assertRaisesRegex(ValueError,'unknown property'):ingest.load(self.root)

    def test_invalid_spans_duplicate_ids_and_missing_parents_fail(self):
        self.change_bundle(lambda d:d['tables']['unit'][0].update(end=9999))
        with self.assertRaisesRegex(ValueError,'span'):ingest.load(self.root)
        self.change_bundle(lambda d:d['tables']['unit'][0].update(end=10,parent_id='missing'))
        with self.assertRaisesRegex(ValueError,'parent'):ingest.load(self.root)

    def test_import_is_data_only_and_invalid_import_does_not_publish_manifest(self):
        data=read_json(FIXTURE/'edition/passages/minimal.json')
        # A self-contained additional text needs data and layout, no new Python.
        version=copy.deepcopy(data['tables']['text_version'][0]);version['id']='fixture:addition:v1'
        new=dict(format='humboldt.passage',schema_version=1,id='fixture-addition',tables={'text_version':[version]},layouts=[dict(version_id=version['id'],analysis_id='addition:layout',paragraph_id='addition:p1',label='Additional synthetic fixture',segments=[dict(id='addition:s1',text=version['body'],kind='sentence')])])
        path=Path(self.temp.name)/'addition.json';path.write_text(json.dumps(new));ingest.add_dataset(self.root,path)
        self.assertEqual(ingest.validate(self.root)['datasets'],2)
        before=(self.root/'edition/manifest.json').read_bytes()
        new['id']='invalid-addition';new['layouts'][0]['segments'][0]['text']='omitted';path.write_text(json.dumps(new))
        with self.assertRaises(ValueError):ingest.add_dataset(self.root,path)
        self.assertEqual((self.root/'edition/manifest.json').read_bytes(),before)
        self.assertFalse((self.root/'edition/passages/invalid-addition/records.json').exists())

    def test_confined_paths_and_nonfinite_or_duplicate_json_fail(self):
        mpath=self.root/'edition/manifest.json';manifest=read_json(mpath);manifest['datasets'][0]['path']='../../outside.json';mpath.write_text(json.dumps(manifest))
        with self.assertRaises(ValueError):ingest.load(self.root)
        from humboldt.records import parse_json
        for data in ['{"a":1,"a":2}','{"a":NaN}','{"a":Infinity}']:
            with self.assertRaises(ValueError):parse_json(data)

    def test_journal_directory_symlink_is_not_followed(self):
        outside=Path(self.temp.name)/'outside';outside.mkdir();(self.root/'edition/changes').symlink_to(outside,target_is_directory=True)
        with self.assertRaises(ValueError):ingest.load(self.root)

    def test_journal_bytes_cannot_be_silently_reformatted(self):
        from humboldt.revisions import propose
        event=propose(self.root,kind='term_sense',target_id='fixture:sense',field='rule',
                      value='Synthetic proposal.',by='Fixture reader',reason='Synthetic byte check')
        path=self.root/'edition/proposals'/(event['id']+'.json')
        path.write_text(json.dumps(read_json(path),indent=2))
        with self.assertRaisesRegex(ValueError,'canonical bytes'):ingest.load(self.root)

    def test_published_outputs_never_overwrite_without_explicit_force(self):
        dest=self.root/'build/edition.sqlite';ingest.build(self.root,dest);before=dest.read_bytes()
        with self.assertRaises(ValueError):ingest.build(self.root,dest)
        self.assertEqual(dest.read_bytes(),before)
        with self.assertRaises(ValueError):ingest.build(self.root,self.root/'edition/wrong.sqlite',force=True)

    def test_reading_defaults_reference_existing_versions(self):
        path=self.root/'edition/manifest.json';manifest=read_json(path)
        manifest['reading_defaults']=[dict(section='999',source_id='fixture:source:v1',target_id='fixture:english:v1')]
        # The synthetic target's permanent ID is taken from its actual record.
        bundle=read_json(self.root/'edition/passages/minimal.json')
        manifest['reading_defaults'][0]['target_id']=next(r['id'] for r in bundle['tables']['text_version'] if r['language']=='en')
        path.write_text(json.dumps(manifest));_,meta=ingest.load(self.root)
        self.assertEqual(meta['reading_defaults'],manifest['reading_defaults'])
        manifest['reading_defaults'][0]['target_id']='missing';path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError,'reading default version missing'):ingest.load(self.root)


if __name__=='__main__':unittest.main()
