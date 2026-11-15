"""Real loopback HTTP tests: escaped content, sources and write-free drafts."""
from contextlib import closing
import hashlib
import http.client
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_queries import create_database
from humboldt import database, reader, revisions


class ReaderTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project=Path(self.tmp.name)
        (self.project/'sources').mkdir()
        (self.project/'sources/fixture.txt').write_text('Synthetic attachment',encoding='utf-8')
        (self.project/'sources/active.html').write_text('<script>alert(1)</script>',encoding='utf-8')
        (self.project/'private.txt').write_text('PRIVATE',encoding='utf-8')
        (self.project/'sources/unlisted.txt').write_text('UNLISTED',encoding='utf-8')
        (self.project/'sources/escape.txt').symlink_to(self.project/'private.txt')
        self.dbpath=self.project/'edition.sqlite'
        create_database(self.dbpath).close()
        self.server=reader.make_server(self.project,self.dbpath)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.addCleanup(self.close_server)
        self.base=self.server.reader_url.rstrip('/')

    def close_server(self):
        self.server.shutdown();self.server.server_close();self.thread.join(timeout=2)

    def get(self,path):
        with urlopen(self.base+path,timeout=5) as response:
            return response.read().decode(),response.headers

    def test_health_search_trace_and_passage(self):
        body,_=self.get('/api/health')
        self.assertTrue(json.loads(body)['read_only'])
        for path in ['/api/search?q=understanding','/api/trace?id=w-g','/api/passage?section=147','/api/entity?kind=sense&id=sense']:
            body,headers=self.get(path)
            self.assertIn('application/json',headers['Content-Type'])
            json.loads(body)
        with self.assertRaises(HTTPError) as caught:self.get('/api/trace?id=absent')
        self.assertEqual(caught.exception.code,404)
        self.assertIn('No unit',caught.exception.read().decode());caught.exception.close()

    def test_html_is_escaped_and_sources_missing_labelled(self):
        for path in ['/','/trace?id=w-g','/entity?kind=decision&id=d-term','/entity?kind=term_sense&id=sense','/search?q=%3Cscript%3E','/propose?kind=decision&id=d-term&field=resolution']:
            body,headers=self.get(path)
            self.assertNotIn('<script>',body)
            self.assertNotIn("alert('q')</script>",body)
            self.assertIn("default-src 'none'",headers['Content-Security-Policy'])
        body,_=self.get('/')
        self.assertIn('&lt;script&gt;',body)
        self.assertIn('Attachment not included',body)
        self.assertIn('synthetic_not_certified',body)
        body,_=self.get('/trace?id=w-g')
        self.assertIn('d-term',body);self.assertIn('d-sentence',body)

    def test_source_allowlist_and_path_safety(self):
        body,headers=self.get('/source?'+urlencode({'path':'sources/fixture.txt'}))
        self.assertEqual(body,'Synthetic attachment')
        body,headers=self.get('/source?'+urlencode({'path':'sources/active.html'}))
        self.assertIn('text/plain',headers['Content-Type'])
        self.assertEqual(headers['Content-Disposition'],'attachment')
        for name in ['../private.txt','/etc/passwd','sources/../private.txt','sources\\fixture.txt','sources/escape.txt','sources/unlisted.txt','sources/%2e%2e/private.txt']:
            with self.assertRaises(HTTPError) as caught:self.get('/source?'+urlencode({'path':name}))
            self.assertIn(caught.exception.code,(403,404));caught.exception.close()
        with self.assertRaises(HTTPError) as caught:self.get('/source?path=sources/missing.pdf')
        self.assertEqual(caught.exception.code,404);caught.exception.close()

    def test_loopback_host_enforced(self):
        for host in ['0.0.0.0','192.0.2.1','example.com']:
            with self.assertRaises(reader.ReaderError):reader.make_server(self.project,self.dbpath,host=host)
        connection=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=5)
        connection.request('GET','/api/health',headers={'Host':'evil.example:'+str(self.server.server_port)})
        response=connection.getresponse()
        self.assertEqual(response.status,403);response.read();connection.close()

    def test_missing_build_explicit(self):
        with self.assertRaisesRegex(FileNotFoundError,'Build the edition first'):
            reader.make_server(self.project,'absent.sqlite')

    def test_draft_download_fingerprints_raw_row_without_writes(self):
        with closing(database.connect(self.dbpath,readonly=True)) as db:
            row=dict(db.execute("SELECT * FROM term_sense WHERE id='sense'").fetchone())
        before=hashlib.sha256(self.dbpath.read_bytes()).hexdigest()
        files_before={str(p.relative_to(self.project)) for p in self.project.rglob('*')}
        draft=dict(kind='term_sense',target_id='sense',field='rule',value='Revised local contrast.',by='Test reader',reason='Synthetic review.',evidence='["ev"]',target_sha256=revisions.fingerprint(row))
        request=Request(self.base+'/proposal',data=urlencode(draft).encode(),headers={'Content-Type':'application/x-www-form-urlencoded'})
        with urlopen(request,timeout=5) as response:
            result=json.load(response)
            self.assertIn('attachment',response.headers['Content-Disposition'])
        self.assertEqual(result['target_sha256'],revisions.fingerprint(row))
        self.assertEqual(result['evidence'],['ev'])
        self.assertNotIn('id',result);self.assertNotIn('at',result)
        self.assertEqual(hashlib.sha256(self.dbpath.read_bytes()).hexdigest(),before)
        self.assertEqual({str(p.relative_to(self.project)) for p in self.project.rglob('*')},files_before)
        draft['target_sha256']='0'*64
        with self.assertRaises(HTTPError) as caught:urlopen(Request(self.base+'/proposal',data=urlencode(draft).encode(),headers={'Content-Type':'application/x-www-form-urlencoded'}),timeout=5)
        self.assertEqual(caught.exception.code,409);caught.exception.close()
        draft['field']='body'
        with self.assertRaises(HTTPError) as caught:urlopen(Request(self.base+'/proposal',data=urlencode(draft).encode(),headers={'Content-Type':'application/x-www-form-urlencoded'}),timeout=5)
        self.assertEqual(caught.exception.code,400);caught.exception.close()

if __name__=='__main__':unittest.main()
