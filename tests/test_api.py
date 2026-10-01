import json
import os
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from unittest.mock import patch
from app import make_server, sample
from procurement.ai import explain
from procurement.engine import analyze, ValidationError
from procurement.storage import Store

class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.server=make_server(0,cls.temp.name+'/test.sqlite')
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.base=f'http://127.0.0.1:{cls.server.server_address[1]}'
        with urllib.request.urlopen(cls.base+'/api/bootstrap') as r:cls.bootstrap=json.load(r)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join();cls.temp.cleanup()

    def request(self,path,data,token=True,extra=None):
        headers={'Content-Type':'application/json',**(extra or {})}
        if token:headers['X-CSRF-Token']=self.bootstrap['token']
        req=urllib.request.Request(self.base+path,data=json.dumps(data).encode(),headers=headers)
        try:
            with urllib.request.urlopen(req) as r:return r.status,r.read(),r.headers
        except urllib.error.HTTPError as e:return e.code,e.read(),e.headers

    def test_analyze(self):
        status,body,headers=self.request('/api/analyze',sample())
        self.assertEqual(status,200);self.assertIsNotNone(json.loads(body)['winner_id'])
        self.assertEqual(headers['X-Content-Type-Options'],'nosniff')

    def test_csrf_and_origin(self):
        self.assertEqual(self.request('/api/analyze',sample(),token=False)[0],403)
        self.assertEqual(self.request('/api/analyze',sample(),extra={'Origin':'https://evil.example'})[0],403)

    def test_invalid_data(self):
        for data in [{},[],{'quotes':[],'scenario':{}}]:
            self.assertEqual(self.request('/api/analyze',data)[0],400)

    def test_save_load_and_history(self):
        data={**sample(),'title':"O'Brien scenario"}
        status,body,_=self.request('/api/save',data);self.assertEqual(status,201)
        saved=json.loads(body)
        with urllib.request.urlopen(self.base+'/api/history/'+str(saved['id'])) as r:loaded=json.load(r)
        self.assertEqual(loaded['quotes'],data['quotes'])
        with urllib.request.urlopen(self.base+'/api/history') as r:history=json.load(r)
        self.assertTrue(any(row['title']==data['title'] for row in history))

    def test_exports_and_sensitivity(self):
        for kind in ['csv','html','json']:
            status,body,headers=self.request('/api/export',{**sample(),'format':kind})
            self.assertEqual(status,200);self.assertIn('attachment',headers['Content-Disposition']);self.assertGreater(len(body),100)
        self.assertEqual(len(json.loads(self.request('/api/sensitivity',sample())[1])),6)

    def test_secrets_and_database_not_served(self):
        for path in ['/.env','/app.py','/runtime/analyses.sqlite3','/../app.py']:
            with self.assertRaises(urllib.error.HTTPError) as cm:urllib.request.urlopen(self.base+path)
            self.assertEqual(cm.exception.code,404)

class AiTests(unittest.TestCase):
    def setUp(self):
        data=sample();self.result=analyze(data['quotes'],data['scenario'])

    def test_consent_and_config(self):
        with self.assertRaises(ValidationError):explain(self.result,consent=False)
        with patch.dict(os.environ,{},clear=True),self.assertRaises(ValidationError):explain(self.result,consent=True)

    def test_adapter_request_and_response(self):
        import io
        payload={'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':'Evidence-based recommendation.'}]}]}
        with patch.dict(os.environ,{'OPENAI_API_KEY':'test-key','OPENAI_MODEL':'test-model'}),patch('urllib.request.urlopen',return_value=io.BytesIO(json.dumps(payload).encode())) as call:
            response=explain(self.result,'Explain briefly',True)
            sent=json.loads(call.call_args.args[0].data)
            self.assertFalse(sent['store']);self.assertEqual(sent['model'],'test-model')
            self.assertNotIn('test-key',sent['input']);self.assertIn('Evidence-based',response['text'])

    def test_api_failure_is_sanitized(self):
        with patch.dict(os.environ,{'OPENAI_API_KEY':'secret','OPENAI_MODEL':'test-model'}),patch('urllib.request.urlopen',side_effect=urllib.error.URLError('secret')):
            with self.assertRaises(ValidationError) as cm:explain(self.result,consent=True)
            self.assertNotIn('secret',str(cm.exception))

class StorageTests(unittest.TestCase):
    def test_checksum_detects_changes(self):
        with tempfile.TemporaryDirectory() as t:
            s=Store(t+'/db.sqlite');x=s.save('Test',{'hello':'world'})
            with s.connect() as db:db.execute('UPDATE analyses SET payload=? WHERE id=?',('{"hello":"changed"}',x['id']))
            with self.assertRaises(ValueError):s.get(x['id'])

if __name__=='__main__':unittest.main()
