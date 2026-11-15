"""Generated transition checks against an independent, tiny editorial model.

These are executable invariants, not a formal proof of Python or SQLite.
"""
import copy
from datetime import datetime,timedelta,timezone
import errno
import hashlib
import json
from pathlib import Path
import random
import sys
import unittest
from unittest.mock import patch
import uuid

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from humboldt import database,ingest,revisions as rev
from humboldt.records import read_json,publish_exclusive


def digest(row):
    wire=json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n'
    return hashlib.sha256(wire.encode()).hexdigest()


def event(seed,sequence,kind):
    return dict(format='humboldt.revision_event',schema_version=2,event_type=kind,
                id=str(uuid.uuid5(uuid.NAMESPACE_OID,f'model:{seed}:{sequence}')),
                sequence=sequence,recorded_at=(datetime(2026,1,1,tzinfo=timezone.utc)+timedelta(seconds=sequence)).isoformat(),
                by='Synthetic model author',reason='Generated transition check',evidence=[])


class JournalModel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base,_=ingest.load(ROOT/'tests/fixtures/minimal')

    def test_generated_sequences_match_model_and_reject_stale_acceptance(self):
        # Independent state: one current row and a set of observed proposals.
        # No database, locks, revisions._check or revisions._project_one here.
        for seed in range(40):
            rng=random.Random(seed);expected=copy.deepcopy(self.base['term_sense'][0]);original=copy.deepcopy(self.base)
            events=[];pending=[];accepted=0
            for turn in range(30):
                if not pending or rng.random()<0.6:
                    field=rng.choice(['label','rule','caution'])
                    p=event(seed,len(events)+1,'proposal')
                    p.update(kind='term_sense',target_id=expected['id'],field=field,value=f'{seed}:{turn}: synthetic {field}',old_value=expected[field],target_sha256=digest(expected),target_snapshot=copy.deepcopy(expected))
                    pending.append(p);events.append(p)
                else:
                    p=pending.pop(rng.randrange(len(pending)))
                    d=event(seed,len(events)+1,'decision');d.update(proposal_id=p['id'],accept=rng.choice([True,False]))
                    fresh=expected==p['target_snapshot']
                    if d['accept'] and not fresh:
                        with self.assertRaises(rev.RevisionConflict):rev.apply(self.base,events+[d])
                        d['accept']=False
                    events.append(d)
                    if d['accept']:expected[p['field']]=p['value'];accepted+=1
            projected,history=rev.apply(self.base,events)
            self.assertEqual(projected['term_sense'][0],expected)
            self.assertEqual(sum(r['status']=='accepted' for r in history['revision_history']),accepted)
            shuffled=copy.deepcopy(events);rng.shuffle(shuffled)
            self.assertEqual(rev.apply(self.base,shuffled),(projected,history))
            self.assertEqual(self.base,original)

    def test_generated_text_revisions_preserve_every_previous_body_and_link(self):
        base=copy.deepcopy(self.base);events=[];current=base['text_version'][0];bodies={current['id']:current['body']}
        for n in range(12):
            p=event(100,len(events)+1,'proposal')
            p.update(kind='text_version',target_id=current['id'],field='body',value=f'α {n}.\n\nSynthetic café {n}.',old_value=current['body'],target_sha256=digest(current),target_snapshot=copy.deepcopy(current))
            d=event(100,len(events)+2,'decision');d.update(proposal_id=p['id'],accept=True);events.extend([p,d])
            projected,history=rev.apply(base,events)
            versions={v['id']:v for v in projected['text_version']}
            self.assertTrue(all(versions[key]['body']==body for key,body in bodies.items()))
            new=json.loads(history['revision_history'][-1]['metadata_json'])['new_version_id']
            current=versions[new];bodies[new]=current['body']
            self.assertEqual(projected.get('unit_evidence'),base.get('unit_evidence'))
            self.assertEqual(projected.get('alignment'),base.get('alignment'))
            self.assertTrue(all(not json.loads(r['metadata_json']).get('automatic_reattachment',False) for r in history['change_impact']))

    def test_json_table_columns_and_packaged_sql_remain_in_sync(self):
        schema=read_json(ROOT/'src/humboldt/record_schemas/bundle.schema.json')['properties']['tables']['properties']
        db=database.connect()
        try:
            database.migrate(db,1)
            tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}-{'schema_migration'}
            self.assertEqual(set(schema),tables)
            for table in tables:
                columns={r[1] for r in db.execute('PRAGMA table_info("'+table+'")')}
                self.assertEqual(set(schema[table]['items']['properties']),columns,table)
        finally:db.close()

    def test_unsupported_filesystem_fails_safely_with_actionable_guidance(self):
        with patch('humboldt.records.os.link',side_effect=OSError(errno.EOPNOTSUPP,'unsupported')):
            with self.assertRaisesRegex(ValueError,'hard links'):
                publish_exclusive('unused-temp','unused-destination')

    def test_format_two_requires_honest_snapshot_and_rejects_unknown_versions(self):
        row=copy.deepcopy(self.base['term_sense'][0]);p=event(900,1,'proposal')
        p.update(kind='term_sense',target_id=row['id'],field='rule',value='Synthetic new rule',old_value=row['rule'],target_sha256=digest(row),target_snapshot=row)
        for change in ('snapshot','version','boolean','key'):
            with self.subTest(change):
                bad=copy.deepcopy(p)
                if change=='snapshot':bad['target_snapshot']['label']='Tampered context'
                elif change=='version':bad['schema_version']=3
                elif change=='boolean':bad['schema_version']=True
                else:
                    bad['target_snapshot']['id']='incorrect:target'
                    bad['target_sha256']=digest(bad['target_snapshot'])
                with self.assertRaises(rev.RevisionError):rev.apply(self.base,[bad])


if __name__=='__main__':unittest.main()
