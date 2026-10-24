"""Synthetic approvals and transports only; never contact a real tracker/client."""
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import sqlite3
import unittest
from unittest.mock import patch, Mock
import alternative_grab as alt
import alternative_grab_helper as helper
import pending_actions as actions
from radarr_client import RadarrError

MOVIE={'identity_status':'verified_tmdb','tmdb_id':1480,'imdb_id':'tt0052311','title':'Touch of Evil','year':1958}
CURRENT={'id':39,'tmdbId':1480,'imdbId':'tt0052311','hasFile':True,'monitored':True,'movieFileId':138,'qualityProfileId':2,
         'movieFile':{'id':138,'relativePath':'Existing.mkv','edition':'Theatrical','releaseGroup':'GROUP','size':100,'quality':{'quality':{'name':'Remux-2160p'}}}}
RELEASE={'type':'movie','protocol':'torrent','external_id':123,'title':'Touch of Evil','year':1958,
         'name':'Touch.of.Evil.1958.RECONSTRUCTED.2160p.REMUX-GROUP','download_url':'https://www.torrentleech.org/rss/download/123/SYNTHETIC/release.torrent'}
PAYLOAD={'event':'action.rejected','data':{'action':{'type':'RADARR'},'release':RELEASE,'indexer':{'identifier':'torrentleech'},'result':{'rejections':['Existing file meets cutoff: Remux-2160p []']}}}
ACTION={'kind':'alternative','movie':MOVIE,'release':RELEASE,'indexer':{'identifier':'torrentleech'},'rejections':PAYLOAD['data']['result']['rejections'],'existing':alt.snapshot(CURRENT)}

def encode(value):
    if isinstance(value,int):return b'i'+str(value).encode()+b'e'
    if isinstance(value,bytes):return str(len(value)).encode()+b':'+value
    if isinstance(value,list):return b'l'+b''.join(encode(v) for v in value)+b'e'
    return b'd'+b''.join(encode(k)+encode(v) for k,v in sorted(value.items()))+b'e'
INFO={b'name':b'Fixture.mkv',b'length':10,b'piece length':16384,b'pieces':b'x'*20}
TORRENT=encode({b'info':INFO})
HASH=hashlib.sha1(encode(INFO)).hexdigest()

class Response:
    status_code=200
    text='Ok.'
    def __init__(self,body=None):self.body=body
    def json(self):return self.body
    def iter_content(self,n):yield TORRENT
    def __enter__(self):return self
    def __exit__(self,*args):pass

class Session:
    def __init__(self,existing=False,fail=False):self.calls=[];self.cookies=Mock();self.existing=existing;self.fail=fail;self.added=False
    def request(self,method,url,**kw):
        self.calls.append((method,url,kw))
        if url.endswith('/torrents/info'):return Response([{'hash':HASH,'category':'radarr'}] if self.existing or self.added else [])
        if url.endswith('/torrents/add') and self.fail:raise TimeoutError()
        if url.endswith('/torrents/add'):self.added=True
        return Response()

class AlternativeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        p=patch.object(helper.time,'sleep');self.sleep=p.start();self.addCleanup(p.stop)
        self.cfg={'url':'https://client.invalid/qbit','username':'synthetic','password':'synthetic','category':'radarr','state':self.tmp.name+'/receipts'}
        p=patch.object(alt,'get_movie_by_tmdb',return_value=copy.deepcopy(CURRENT));self.current=p.start();self.addCleanup(p.stop)
        p=patch.object(actions,'STORE_PATH',Path(self.tmp.name)/'actions.json');p.start();self.addCleanup(p.stop)
        p=patch.dict(os.environ,{alt.CONFIG:self.tmp.name+'/config.json'});p.start();self.addCleanup(p.stop)
    def test_positive_and_duplicate_approval(self):
        token=alt.offer(PAYLOAD,MOVIE)
        self.assertEqual(token,alt.offer(PAYLOAD,MOVIE))
        self.assertEqual(actions.get_action(token)['existing'],alt.snapshot(CURRENT))
        alt.validate_action(actions.get_action(token))
    def test_negative_rejection_and_source_gates(self):
        for reason in ['Unknown Movie','Release is not wanted','Quality not allowed','prefix Existing file meets cutoff: Remux-2160p []']:
            p=copy.deepcopy(PAYLOAD);p['data']['result']['rejections'].append(reason)
            self.assertFalse(alt.candidate(p));self.assertIsNone(alt.offer(p,MOVIE))
        for key,value in [('type','tv'),('season',1),('episode',1),('protocol','usenet'),('external_id',124),('download_url','https://evil.invalid/file'),('name','')]:
            p=copy.deepcopy(PAYLOAD);p['data']['release'][key]=value
            self.assertFalse(alt.candidate(p));self.assertIsNone(alt.offer(p,MOVIE))
        for suffix in ['?url=https://evil.invalid','/../file','#fragment']:
            p=copy.deepcopy(PAYLOAD);p['data']['release']['download_url']+=suffix
            self.assertFalse(alt.candidate(p))
    def test_identity_and_existing_file_gates(self):
        for key,value in [('identity_status','unresolved'),('imdb_id','tt0000000'),('tmdb_id','1480')]:
            m={**MOVIE,key:value};self.assertIsNone(alt.offer(PAYLOAD,m))
        for key,value in [('monitored',False),('hasFile',False),('movieFileId',999),('imdbId','tt0000000')]:
            self.current.return_value={**CURRENT,key:value};self.assertIsNone(alt.offer(PAYLOAD,MOVIE))
    def test_changed_snapshot_requires_fresh_approval(self):
        for key,value in [('qualityProfileId',99),('movieFile',dict(CURRENT['movieFile'],size=999))]:
            self.current.return_value={**CURRENT,key:value}
            with self.assertRaises(RadarrError):alt.validate_action(ACTION)
    def test_exact_submission_and_durable_cross_token_replay_block(self):
        s=Session()
        with patch.object(helper,'verify_client'):
            self.assertEqual(helper.submit(ACTION,self.cfg,s),'queued')
            self.assertEqual(helper.submit(ACTION,self.cfg,s),'uncertain')
        adds=[r for r in s.calls if r[1].endswith('/torrents/add')]
        self.assertEqual(len(adds),1);self.assertEqual(adds[0][2]['files']['torrents'][1],TORRENT)
        self.assertEqual(adds[0][2]['data'],{'category':'radarr'})
        self.assertEqual(s.calls[0][1],RELEASE['download_url'])
        self.assertNotIn('password',s.calls[0][2]);self.assertTrue(s.cookies.clear.called)
        self.assertTrue(all(row[2]['allow_redirects'] is False for row in s.calls))
    def test_uncertain_client_result_never_repeats(self):
        s=Session(fail=True)
        with patch.object(helper,'verify_client'):
            self.assertEqual(helper.submit(ACTION,self.cfg,s),'uncertain')
            self.assertEqual(helper.submit(ACTION,self.cfg,s),'uncertain')
        self.assertEqual(sum(r[1].endswith('/torrents/add') for r in s.calls),1)
    def test_existing_hash_not_modified(self):
        s=Session(existing=True)
        self.assertEqual(helper.submit(ACTION,self.cfg,s),'already_present')
        self.assertFalse(any(r[1].endswith('/torrents/add') for r in s.calls))
    def test_source_failure_blocks_transfer(self):
        s=Session();s.request=Mock(side_effect=TimeoutError())
        self.assertEqual(helper.submit(ACTION,self.cfg,s),'refused')
        self.assertEqual(s.request.call_count,1)
    def test_no_subprocess_retries_or_secret_output(self):
        with patch.object(alt.subprocess,'run',side_effect=TimeoutError()) as run:
            self.assertEqual(alt.execute('synthetic'),'uncertain')
            self.assertEqual(run.call_count,1)
    def test_bencode_hash_and_reject_unsafe_payloads(self):
        self.assertEqual(helper.torrent_hash(TORRENT),HASH)
        for info in [{**INFO,b'name':b'../escape'}, {**INFO,b'name.utf-8':b'../escape'},
                     {**INFO,b'attr':b'l'}, {**INFO,b'piece length':0}, {**INFO,b'pieces':b'x'}]:
            with self.assertRaises(ValueError):helper.torrent_hash(encode({b'info':info}))
        for raw in [b'<html>login</html>',TORRENT+b'extra',b'd4:infod1:ai1e1:ai2eee']:
            with self.assertRaises(ValueError):helper.torrent_hash(raw)
    def test_private_config_rejects_public_permissions(self):
        p=Path(self.tmp.name)/'config.json';p.write_text(json.dumps(self.cfg));p.chmod(0o600)
        self.assertEqual(helper.private_config(p),self.cfg)
        p.chmod(0o644)
        with self.assertRaises(ValueError):helper.private_config(p)

    def test_client_route_and_hooks_are_checked(self):
        row={'enable':True,'implementation':'QBittorrent','fields':[{'name':k,'value':v} for k,v in {'host':'client.invalid','port':443,'useSsl':True,'urlBase':'qbit','movieCategory':'radarr'}.items()]}
        s=Mock();s.request.side_effect=[Response({'radarr':{}}),Response({'autorun_enabled':False})]
        with patch.object(helper,'radarr_request',return_value=[row]):helper.verify_client(self.cfg,s)
        s.request.side_effect=[Response({'radarr':{}}),Response({'autorun_enabled':True})]
        with patch.object(helper,'radarr_request',return_value=[row]),self.assertRaises(ValueError):helper.verify_client(self.cfg,s)
        with patch.object(helper,'radarr_request',return_value=[]),self.assertRaises(ValueError):helper.verify_client(self.cfg,s)

    def test_main_rejects_unconfirmed_or_expired_capability(self):
        import io
        for action in [None,dict(ACTION,status='pending'),dict(ACTION,status='needs_review')]:
            output=io.StringIO()
            with patch.object(helper.sys,'stdin',io.StringIO('a'*32)),patch.object(helper.sys,'stdout',output),patch.object(helper,'get_action',return_value=action),patch.object(helper,'submit') as submit:
                helper.main()
                submit.assert_not_called()
            self.assertEqual(json.loads(output.getvalue()),{'status':'refused'})

    def test_original_filename_punctuation_without_path_escape(self):
        release=dict(RELEASE,download_url=RELEASE['download_url'].replace('release.torrent','Release.[2160p].(Remux).torrent'))
        self.assertEqual(alt.source_reference(release,ACTION['indexer'])[0],release['download_url'])
        for filename in ['%2fescape.torrent','%5cescape.torrent','bad%00.torrent']:
            release['download_url']=RELEASE['download_url'].replace('release.torrent',filename)
            with self.assertRaises(ValueError):alt.source_reference(release,ACTION['indexer'])

    def test_custom_format_scores_enable_only_verified_exact_approvals(self):
        for score in ('0','100','-100'):
            payload=copy.deepcopy(PAYLOAD)
            payload['data']['result']['rejections']=['Existing file on disk has a equal or higher Custom Format score: '+score]
            self.assertTrue(alt.candidate(payload))
            token=alt.offer(payload,MOVIE)
            self.assertIsNotNone(token)
            alt.validate_action(actions.get_action(token))
            self.assertIsNone(alt.offer(payload,dict(MOVIE,identity_status='unresolved')))
            payload['data']['result']['rejections'].append('Quality not allowed')
            self.assertFalse(alt.candidate(payload))
            self.assertIsNone(alt.offer(payload,MOVIE))

    def test_custom_format_malformed_or_unrelated_reasons_fail_closed(self):
        prefix='Existing file on disk has a equal or higher Custom Format score: '
        for reason in [prefix+'',prefix+'unknown',prefix+'0 extra',prefix+'1.5',prefix+'01',prefix+'0\n',
                       'Minimum custom format score not met', 'prefix '+prefix+'0']:
            self.assertFalse(alt.quality_only([reason]))

    def receipt(self):
        with sqlite3.connect(Path(self.cfg['state'])/'receipts.sqlite3') as c:
            return c.execute('select state,infohash,detail from receipt').fetchone()

    def test_delayed_visibility_recovers_without_second_add(self):
        s=Session();original=s.request;readbacks=iter([[],[],[{'hash':HASH,'category':'radarr'}]])
        def request(method,url,**kw):
            if s.added and url.endswith('/torrents/info'):
                s.calls.append((method,url,kw));return Response(next(readbacks))
            return original(method,url,**kw)
        s.request=request
        with patch.object(helper,'verify_client'):
            self.assertEqual(helper.submit(ACTION,self.cfg,s),'queued')
        self.assertEqual(sum(x[1].endswith('/torrents/add') for x in s.calls),1)
        self.assertEqual(self.sleep.call_count,2)
        self.assertEqual(self.receipt(),('queued',HASH,'hash_verified'))

    def test_lost_add_acknowledgement_uses_hash_readback_only(self):
        s=Session();original=s.request
        def request(method,url,**kw):
            result=original(method,url,**kw)
            if url.endswith('/torrents/add'):raise TimeoutError('private URL must not be recorded')
            return result
        s.request=request
        with patch.object(helper,'verify_client'):
            self.assertEqual(helper.submit(ACTION,self.cfg,s),'queued')
        self.assertEqual(sum(x[1].endswith('/torrents/add') for x in s.calls),1)
        self.assertEqual(self.receipt(),('queued',HASH,'hash_verified_after_unconfirmed_add'))

    def test_transient_readback_error_recovers(self):
        s=Session();original=s.request;failed=False
        def request(method,url,**kw):
            nonlocal failed
            if s.added and url.endswith('/torrents/info') and not failed:
                failed=True;raise TimeoutError()
            return original(method,url,**kw)
        s.request=request
        with patch.object(helper,'verify_client'):
            self.assertEqual(helper.submit(ACTION,self.cfg,s),'queued')
        self.assertEqual(self.receipt()[0],'queued')

    def test_readback_exhaustion_is_bounded_and_durable(self):
        s=Session();original=s.request;reads=[]
        def request(method,url,**kw):
            if s.added and url.endswith('/torrents/info'):
                reads.append(kw);return Response([])
            return original(method,url,**kw)
        s.request=request
        with patch.object(helper,'verify_client'):
            self.assertEqual(helper.submit(ACTION,self.cfg,s),'uncertain')
            calls=len(s.calls)
            self.assertEqual(helper.submit(ACTION,self.cfg,s),'uncertain')
            self.assertEqual(len(s.calls),calls)
        self.assertEqual(len(reads),5)
        self.assertTrue(all(r['timeout']==(2,3) and not r['allow_redirects'] for r in reads))
        self.assertEqual(self.receipt(),('uncertain',HASH,'hash_not_visible'))

    def test_unrelated_or_wrong_category_hash_never_confirms(self):
        for rows,reason in [([{'hash':'0'*40,'category':'radarr'}],'readback_invalid'),
                            ([{'hash':HASH,'category':'other'}],'category_mismatch'),
                            ([{'hash':HASH,'category':'radarr'}]*2,'readback_invalid'),
                            ({'hash':HASH},'readback_invalid'),(None,'readback_invalid')]:
            with self.subTest(rows=rows):
                s=Mock();s.request.return_value=Response(rows)
                self.assertEqual(helper.confirm_submission(s,self.cfg['url'],HASH),(False,reason))
                self.assertEqual(s.request.call_count,1)

    def test_old_receipt_migration_preserves_replay_barrier(self):
        state=Path(self.cfg['state']);state.mkdir(mode=0o700)
        db=state/'receipts.sqlite3';key=alt.source_reference(RELEASE,ACTION['indexer'])[1]
        with sqlite3.connect(db) as c:
            c.execute('create table receipt(source text primary key,state text,created real)')
            c.execute('insert into receipt values(?,?,?)',(key,'uncertain',123))
        s=Session()
        self.assertEqual(helper.submit(ACTION,self.cfg,s),'uncertain')
        self.assertEqual(s.calls,[])
        self.assertEqual(self.receipt(),('uncertain',None,None))

    def test_submission_hash_is_durable_before_add(self):
        s=Session();original=s.request
        def request(method,url,**kw):
            if url.endswith('/torrents/add'):
                self.assertEqual(self.receipt(),('uncertain',HASH,'submission_started'))
            return original(method,url,**kw)
        s.request=request
        with patch.object(helper,'verify_client'):
            self.assertEqual(helper.submit(ACTION,self.cfg,s),'queued')

    def test_delayed_client_visibility_over_real_local_http(self):
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        import threading
        state={'adds':0,'reads':0}
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                self.rfile.read(int(self.headers.get('Content-Length',0)))
                if self.path.endswith('/torrents/add'):state['adds']+=1
                self.send_response(200);self.end_headers();self.wfile.write(b'Ok.')
            def do_GET(self):
                body=TORRENT
                if self.path.startswith('/api/v2/torrents/info'):
                    state['reads']+=1
                    body=json.dumps([{'hash':HASH,'category':'radarr'}] if state['reads']>=4 else []).encode()
                self.send_response(200);self.end_headers();self.wfile.write(body)
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            base='http://127.0.0.1:'+str(server.server_port)
            cfg=dict(self.cfg,url=base)
            with patch.object(helper,'source_reference',return_value=(base+'/fixture','synthetic-source')),patch.object(helper,'verify_client'):
                self.assertEqual(helper.submit(ACTION,cfg),'queued')
            self.assertEqual(state,{'adds':1,'reads':4})
        finally:
            server.shutdown();server.server_close();thread.join()
