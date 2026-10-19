"""Synthetic approvals and transports only; never contact a real tracker/client."""
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
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
        if url.endswith('/torrents/info'):return Response([{'hash':HASH}] if self.existing or self.added else [])
        if url.endswith('/torrents/add') and self.fail:raise TimeoutError()
        if url.endswith('/torrents/add'):self.added=True
        return Response()

class AlternativeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
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
