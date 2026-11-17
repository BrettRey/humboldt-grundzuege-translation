"""Query contracts on synthetic overlapping, bilingual, revision-aware data."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from humboldt import database, queries


def fixture():
    sha = 'a' * 64
    bodies = {'g': 'Die Andeutung stärkt den Verstand. Straße 100%.', 'e': "The indication supports understanding. <script>alert('x')</script>", 'e2': 'The hint aids understanding.'}
    tables = {'text_version': [], 'analysis': [], 'unit': []}
    for key, body in bodies.items():
        tables['text_version'].append(dict(id=key,title='§147 ' + key,language='de' if key=='g' else 'en',body=body,body_sha256=hashlib.sha256(body.encode()).hexdigest(),source_path='sources/fixture.txt',source_sha256=sha,locator='printed 462 / PDF 472',transcription_status='synthetic_not_certified',provenance='synthetic'))
        tables['analysis'].append(dict(id='a-'+key,version_id=key,method='synthetic segmentation',scope='synthetic',status='proposed',supersedes=None))
        for kind,prefix,parent in [('paragraph','p-',None),('sentence','s-','p-'+key)]:
            tables['unit'].append(dict(id=prefix+key,analysis_id='a-'+key,version_id=key,kind=kind,label='§147' if kind=='paragraph' else key+' sentence',start=0,end=len(body),parent_id=parent,note=''))
        word = 'Andeutung' if key=='g' else 'indication' if key=='e' else 'hint'
        start=bodies[key].index(word)
        tables['unit'].append(dict(id='w-'+key,analysis_id='a-'+key,version_id=key,kind='word',label=word,start=start,end=start+len(word),parent_id='s-'+key,note=''))
    tables['unit'] += [dict(id='t-g',analysis_id='a-g',version_id='g',kind='term_expression',label='sibling term annotation',start=4,end=13,parent_id='s-g',note=''),dict(id='o-g',analysis_id='a-g',version_id='g',kind='phrase',label='overlap',start=0,end=8,parent_id='s-g',note='')]
    tables['decision'] = [dict(id=k,question=q,resolution=r,authority='synthetic',status='provisional') for k,q,r in [('d-term',"Term <script>alert('q')</script>",'Preserve indication vs mental supply.'),('d-sentence','Sentence criterion','Keep word order and independent marker distinct.')]]
    tables['unit_decision'] = [dict(unit_id='t-g',decision_id='d-term'),dict(unit_id='s-g',decision_id='d-sentence')]
    tables['evidence'] = [dict(id='ev',source_path='sources/missing.pdf',source_sha256=sha,locator='printed 462 / PDF 472',excerpt='Die Andeutung',statement='Synthetic checked-quote placeholder, not Humboldt evidence.',quote_status='synthetic',claim_status='synthetic')]
    tables['unit_evidence'] = [dict(unit_id='t-g',evidence_id='ev')]
    tables['decision_evidence'] = [dict(decision_id='d-term',evidence_id='ev')]
    tables['lexeme'] = [dict(id=k,headword=h,query_key=h.casefold(),kind='synthetic',scope='synthetic',domains_json='[]',roles_json='[]') for k,h in [('l','Andeutung'),('lv','Verstand'),('la','Auffassen')]]
    tables['lexeme_form'] = [dict(lexeme_id='l',form='Andeutung',query_key='andeutung',form_role='headword')]
    tables['term_sense'] = [dict(id=k,lexeme_id=l,label=label,definition=definition,rule='Keep local contrast.',caution='Do not infer an English word alignment.',decision_id='d-term') for k,l,label,definition in [('sense','l','indication','Indication distinct from completion.'),('sv','lv','faculty','faculty of understanding'),('sa','la','apprehension','contains understanding incidentally')]]
    tables['sense_rendering'] = [dict(sense_id=s,rank=r,rendering=v) for s,r,v in [('sense',1,'indication'),('sv',1,'understanding'),('sa',1,'apprehension'),('sa',2,'understanding')]]
    tables['term_use'] = [dict(id='use',sense_id='sense',origin='synthetic',label='use',definition='Synthetic use.',rule='Local.',caution='')]
    tables['sense_attestation'] = [dict(id='att',sense_id='sense',use_id='use',evidence_id='ev',checked_context_unit='s-g',checked_expression_unit='t-g',ocr_context_unit=None,source_page_unit='p-g',printed_page=462,pdf_page=472,scan_leaf=None,term_form='Andeutung',evidence_role='direct_occurrence',composite_group=None,text_layer='synthetic',issue='')]
    tables['term_expression_part'] = [dict(attestation_id='att',rank=1,unit_id='t-g',part_role='expression')]
    tables['alignment'] = [dict(id='al-'+k,left_version='g',right_version=k,relation='source_sentence_rendering',note='Proposed, no semantic certification.',status='proposed') for k in ('e','e2')]
    tables['alignment_member'] = [dict(alignment_id='al-'+k,side=side,unit_id=unit) for k in ('e','e2') for side,unit in [('left','s-g'),('right','s-'+k)]]
    tables['revision_history'] = [dict(id='rev',proposal_id='proposal',kind='term_sense',target_id='sense',field='rule',old_value_json='"old"',new_value_json='"new"',by_name='Test',reason='Synthetic test',evidence_json='["ev"]',recorded_at='2000-01-01T00:00:00Z',status='accepted',metadata_json='{}')]
    tables['change_impact'] = [dict(revision_id='rev',entity_kind='unit',entity_id='w-g',impact='review',metadata_json='{}')]
    tables['build_metadata'] = [dict(key='resources',value_json=json.dumps([{'path':'sources/fixture.txt','sha256':sha},{'path':'sources/active.html','sha256':sha},{'path':'sources/missing.pdf','sha256':sha}]))]
    return tables


def create_database(path=':memory:', v1=False, data=None):
    db = database.connect(path)
    database.migrate(db, target=1 if v1 else None)
    data=fixture() if data is None else data
    if v1:
        for table in ('revision_history','change_impact','build_metadata'):
            data.pop(table)
    database.insert_records(db,data)
    db.commit()
    return db


class QueryTests(unittest.TestCase):
    def setUp(self):
        self.db=create_database()
        self.addCleanup(self.db.close)

    def test_english_ranking_and_embedded_search(self):
        results=queries.search(self.db,'understanding',2)
        self.assertEqual(results[0]['lexeme_id'],'lv')
        self.assertEqual(results[0]['match_field'],'English rendering')
        self.assertEqual(results[1]['lexeme_id'],'la')
        texts=queries.search(self.db,'supports')
        self.assertEqual(texts[0]['language'],'en')
        self.assertEqual(texts[0]['unit_id'],'s-e')

    def test_literal_unicode_search(self):
        self.assertTrue(queries.search(self.db,'STRASSE'))
        percent=queries.search(self.db,'%')
        self.assertEqual(len(percent),1)
        self.assertIn('100%',percent[0]['snippet'])
        self.assertEqual(queries.search(self.db,'not present'),[])
        with self.assertRaises(ValueError): queries.search(self.db,'x',0)

    def test_word_trace_includes_sibling_and_sentence(self):
        result=queries.trace(self.db,'w-g')
        self.assertEqual({d['id'] for d in result['decisions']},{'d-term','d-sentence'})
        annotations={r['id']:r for r in result['annotations']}
        self.assertEqual(annotations['t-g']['relation'],'exact_span')
        self.assertEqual(annotations['o-g']['relation'],'overlapping_context')
        self.assertEqual(annotations['s-g']['scope'],'context')
        self.assertEqual(result['terms'][0]['scope'],'exact')
        self.assertEqual(queries.trace(self.db,'s-g')['terms'][0]['scope'],'context')
        self.assertEqual(queries.trace(self.db,'o-g')['terms'][0]['scope'],'context')
        self.assertEqual(result['evidence'][0]['id'],'ev')
        self.assertEqual({v['id'] for v in result['alternatives']},{'e','e2'})
        self.assertEqual(result['history']['revisions'][0]['id'],'rev')

    def test_english_trace_links_source_terms_as_context(self):
        result=queries.trace(self.db,'w-e')
        self.assertEqual(result['terms'][0]['scope'],'context')
        self.assertTrue(any(r['id']=='d-term' for r in result['decisions']))
        self.assertTrue(any(v['id']=='e2' for v in result['alternatives']))
        self.assertTrue(all(r['scope']=='context' for r in result['context_links'] if r['relation']=='aligned_context'))

    def test_entity_passage_and_history_are_json_safe(self):
        for result in [queries.sections(self.db),queries.passage(self.db,'§147'),queries.entity(self.db,'lexeme','l'),queries.entity(self.db,'term_sense','sense'),queries.trace(self.db,'w-g'),queries.search(self.db,'indication')]:
            json.dumps(result,ensure_ascii=False,allow_nan=False)
        raw=dict(self.db.execute('SELECT * FROM term_sense WHERE id=?',('sense',)).fetchone())
        self.assertEqual(queries.entity(self.db,'sense','sense')['record'],raw)
        self.assertEqual(queries.passage(self.db,147)['versions'][0]['transcription_status'],'synthetic_not_certified')
        with self.assertRaises(queries.NotFound): queries.trace(self.db,'absent')
        with self.assertRaises(ValueError): queries.entity(self.db,'untrusted SQL','x')

    def test_explicit_passage_metadata_with_generic_source(self):
        from humboldt import render
        data = fixture()
        data['text_version'][0].update(title='Independent passage',language='und')
        next(u for u in data['unit'] if u['id']=='p-g')['label']='Independent paragraph'
        data['build_metadata'].append(dict(key='passages',value_json=json.dumps([dict(id='new-passage',section='999',version_ids=['g','e'])])))
        db = create_database(data=data)
        self.addCleanup(db.close)
        self.assertEqual([s['section'] for s in queries.sections(db)], ['147','999'])
        result = queries.passage(db,'999')
        self.assertEqual({v['id'] for v in result['versions']}, {'g','e'})
        html = render.home(queries.sections(db),result)
        self.assertIn('Source version',html)
        self.assertIn('Die ',html)
        self.assertIn('The ',html)

    def test_old_snapshot_labels_missing_history(self):
        with closing(create_database(v1=True)) as db:
            result=queries.trace(db,'w-g')
            self.assertFalse(result['history']['available'])
            self.assertIn('does not establish',result['history']['note'])

    def test_declared_reading_default_and_explicit_version_choice(self):
        from humboldt import render
        data=fixture()
        next(u for u in data['unit'] if u['id']=='p-g')['label']='§2'
        data['alignment'].append(dict(id='a-span',left_version='g',right_version='e',relation='consequential_span_rendering',note='Synthetic span',status='proposed'))
        data['alignment_member'].extend([dict(alignment_id='a-span',side='left',unit_id='w-g'),dict(alignment_id='a-span',side='right',unit_id='w-e')])
        data['build_metadata'].append(dict(key='reading_defaults',value_json=json.dumps([
            dict(section='147',source_id='g',target_id='e2')
        ])))
        with closing(create_database(data=data)) as db:
            # A legacy copied paragraph label must not override its section title.
            self.assertEqual([s['section'] for s in queries.sections(db)],['147'])
            passage=queries.passage(db,'147')
            default=render.home(queries.sections(db),passage)
            self.assertIn('<option value="e2" selected>',default)
            self.assertIn('[e2]</option>',default)
            chosen=render.home(queries.sections(db),passage,en='e')
            self.assertIn('<option value="e" selected>',chosen)
            self.assertNotIn('<option value="e2" selected>',chosen)
            self.assertLess(chosen.index('Recorded alignment: source_sentence_rendering'),chosen.index('<h2>Additional span alignments</h2>'))

    def test_lettered_passages_sort_and_remain_separately_queryable(self):
        from humboldt import render
        data = fixture()
        # Title, paragraph label and explicit declaration each discover a distinct ID.
        data['text_version'][0]['title'] = 'Grundzüge §62b — source'
        data['text_version'][1]['title'] = 'Unnumbered rendering'
        data['text_version'][2]['title'] = 'Grundzüge §62 — revised'
        next(u for u in data['unit'] if u['id'] == 'p-e')['label'] = '§62a'
        data['build_metadata'].append(dict(key='passages', value_json=json.dumps([
            dict(id='lettered', section='63a', version_ids=['g'])
        ])))
        data['build_metadata'].append(dict(key='reading_defaults', value_json=json.dumps([
            dict(section='62a', target_id='e')
        ])))
        with closing(create_database(data=data)) as db:
            self.assertEqual([v['section'] for v in queries.sections(db)], ['62', '62a', '62b', '63a'])
            passage = queries.passage(db, '§62a')
            self.assertEqual([v['id'] for v in passage['versions']], ['e'])
            self.assertEqual(passage['reading_defaults']['target_id'], 'e')
            self.assertIn('value="62a"', render.home(queries.sections(db), passage))
            self.assertEqual([v['id'] for v in queries.passage(db, '62')['versions']], ['e2'])
            for bad in ['62aa', '62A', '62; DROP TABLE unit', '-62a', '62/a']:
                with self.assertRaises(ValueError):
                    queries.passage(db, bad)

if __name__=='__main__': unittest.main()
