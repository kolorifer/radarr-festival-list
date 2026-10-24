"""Restricted stdin-capability helper; credentials stay in owner-only configuration.

No public listener or arbitrary downloader commands. Receipts are durable before
submission and bind source identity across capability expiry/recreation.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import sys
import time
import requests
from alternative_grab import CONFIG, source_reference, validate_action
from pending_actions import get_action
from radarr_client import _request as radarr_request


def private_config(path):
    if not Path(path).is_absolute():raise ValueError("config")
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(fd) as f:
        s=os.fstat(f.fileno())
        if not stat.S_ISREG(s.st_mode) or s.st_uid!=os.getuid() or s.st_mode&0o077 or s.st_size>16384:raise ValueError('config')
        cfg=json.load(f)
    from urllib.parse import urlsplit
    u=urlsplit(cfg['url'])
    if u.scheme!='https' or not u.hostname or u.username or u.password or u.query or u.fragment:raise ValueError('client')
    if set(cfg)!={'url','username','password','category','state'} or cfg['category']!='radarr':raise ValueError('config')
    if not Path(cfg['state']).is_absolute():raise ValueError('state')
    if not all(isinstance(cfg[k],str) and cfg[k] for k in ('username','password')):raise ValueError('credentials')
    return cfg


def torrent_hash(data):
    """Bounded canonical bencode parser retaining the exact original info bytes."""
    if not isinstance(data,bytes) or not 1<=len(data)<=4_000_000:raise ValueError('torrent')
    pos=0;info=None;nodes=0
    def parse(depth=0):
        nonlocal pos,info,nodes
        nodes+=1
        if depth>32 or nodes>100000 or pos>=len(data):raise ValueError('torrent')
        start=pos;ch=data[pos:pos+1]
        if ch==b'i':
            end=data.index(b'e',pos);raw=data[pos+1:end]
            if not re.fullmatch(rb'(?:0|-?[1-9][0-9]*)',raw) or len(raw)>20:raise ValueError('integer')
            pos=end+1;return int(raw)
        if ch in (b'd',b'l'):
            pos+=1;out={} if ch==b'd' else [];previous=None
            while pos<len(data) and data[pos:pos+1]!=b'e':
                if ch==b'd':
                    key=parse(depth+1)
                    if not isinstance(key,bytes) or previous is not None and key<=previous:raise ValueError('dictionary')
                    previous=key;begin=pos;value=parse(depth+1);out[key]=value
                    if depth==0 and key==b'info':info=data[begin:pos]
                else:out.append(parse(depth+1))
            if pos>=len(data):raise ValueError('truncated')
            pos+=1;return out
        end=data.index(b':',pos);raw=data[pos:end]
        if not re.fullmatch(rb'(?:0|[1-9][0-9]*)',raw) or len(raw)>8:raise ValueError('length')
        size=int(raw);pos=end+1
        if pos+size>len(data):raise ValueError('truncated')
        value=data[pos:pos+size];pos+=size;return value
    root=parse()
    if pos!=len(data) or not isinstance(root,dict) or not isinstance(root.get(b'info'),dict) or info is None:raise ValueError('torrent')
    obj=root[b'info']
    if not isinstance(obj.get(b'pieces'),bytes) or len(obj[b'pieces'])%20 or not obj[b'pieces']:raise ValueError('v1_required')
    def safe(part):
        return isinstance(part,bytes) and part not in (b'',b'.',b'..') and not any(c in part for c in (b'/',b'\\',b'\x00'))
    if not safe(obj.get(b'name')) or b'name.utf-8' in obj and not safe(obj[b'name.utf-8']):raise ValueError('unsafe_name')
    if b'attr' in obj or b'symlink path' in obj:raise ValueError('symlink')
    if type(obj.get(b'piece length')) is not int or obj[b'piece length']<=0:raise ValueError('pieces')
    if b'files' in obj:
        if not isinstance(obj[b'files'],list) or not obj[b'files']:raise ValueError('files')
        for f in obj[b'files']:
            if not isinstance(f,dict) or not isinstance(f.get(b'path'),list) or not f[b'path'] or not all(safe(p) for p in f[b'path']) or b'attr' in f or b'symlink path' in f:raise ValueError('unsafe_path')
            if b'path.utf-8' in f and (not isinstance(f[b'path.utf-8'],list) or not f[b'path.utf-8'] or not all(safe(p) for p in f[b'path.utf-8'])):raise ValueError('unsafe_path')
            if type(f.get(b'length')) is not int or f[b'length']<0:raise ValueError('length')
        if b'length' in obj:raise ValueError('length')
    elif type(obj.get(b'length')) is not int or obj[b'length']<0:raise ValueError('length')
    return hashlib.sha1(info).hexdigest()


def request(session,method,url,**kw):
    r=session.request(method,url,timeout=(5,15),allow_redirects=False,**kw)
    if r.status_code!=200:raise ValueError('http')
    return r


def verify_client(cfg,session):
    rows=[r for r in radarr_request('/downloadclient') if r.get('enable') and r.get('implementation')=='QBittorrent']
    if len(rows)!=1:raise ValueError('client_route')
    fields={f['name']:f.get('value') for f in rows[0]['fields']}
    host=fields['host'];port=fields.get('port')
    url='https://'+host+((':'+str(port)) if port and port!=443 else '')+'/'+str(fields.get('urlBase') or '').strip('/')
    if not fields.get('useSsl') or url.rstrip('/')!=cfg['url'].rstrip('/') or fields.get('movieCategory')!='radarr':raise ValueError('client_route')
    base=cfg['url'].rstrip('/')
    cats=request(session,'GET',base+'/api/v2/torrents/categories').json()
    prefs=request(session,'GET',base+'/api/v2/app/preferences').json()
    if not isinstance(cats,dict) or 'radarr' not in cats or not isinstance(prefs,dict):raise ValueError('client')
    if prefs.get('autorun_enabled') or prefs.get('autorun_on_torrent_added_enabled'):raise ValueError('hooks')


def open_receipts(db):
    """Add private diagnostics without discarding any existing replay barrier."""
    c=sqlite3.connect(db,timeout=5)
    os.chmod(db,0o600)
    c.execute('create table if not exists receipt(source text primary key,state text,created real)')
    c.execute('create table if not exists receipt_detail(source text primary key,infohash text,detail text,updated real)')
    c.commit()
    return c


def record_detail(c,key,detail,infohash=None):
    # A separate table keeps the original three-column receipt compatible with rollback.
    c.execute('insert into receipt_detail(source,infohash,detail,updated) values(?,?,?,?) '
              'on conflict(source) do update set infohash=coalesce(excluded.infohash,receipt_detail.infohash), '
              'detail=excluded.detail,updated=excluded.updated', (key,infohash,detail,time.time()))


def confirm_submission(session,base,infohash):
    """Only GETs: qBittorrent can acknowledge before its torrent is visible.

    Also resolves a lost add acknowledgement if the exact hash is visible.
    Nothing here can retry the add, fetch the source, or change a transfer.
    """
    detail='hash_not_visible'
    for delay in (0,0.25,0.5,1,2):
        if delay:time.sleep(delay)
        try:
            r=session.request('GET',base+'/api/v2/torrents/info',
                              params={'hashes':infohash},timeout=(2,3),allow_redirects=False)
            if r.status_code!=200:
                detail='readback_http_error';continue
            rows=r.json()
        except Exception:
            detail='readback_unavailable';continue
        if rows==[]:
            detail='hash_not_visible';continue
        if (not isinstance(rows,list) or len(rows)!=1 or not isinstance(rows[0],dict)
                or not isinstance(rows[0].get('hash'),str)
                or rows[0]['hash'].lower()!=infohash):
            return False,'readback_invalid'
        if rows[0].get('category')!='radarr':return False,'category_mismatch'
        return True,'hash_verified'
    return False,detail


def submit(action,cfg,session=None):
    validate_action(action)
    url,key=source_reference(action['release'],action['indexer'])
    state=Path(cfg['state']);state.mkdir(mode=0o700,parents=True,exist_ok=True)
    if state.is_symlink() or state.stat().st_mode&0o077:raise ValueError('state')
    db=state/'receipts.sqlite3'
    if db.is_symlink():raise ValueError('state')
    c=open_receipts(db)
    try:
        with c:c.execute('insert into receipt(source,state,created) values(?,?,?)',(key,'uncertain',time.time()))
    except sqlite3.IntegrityError:
        c.close();return 'uncertain' # never retry an older capability under another token
    sent=False;stage='source_fetch'
    try:
        s=session or requests.Session();s.trust_env=False
        # Fetch only the bound source URL; no redirects, fallback searches or substitutions.
        with request(s,'GET',url,stream=True) as r:
            chunks=[];total=0;started=time.monotonic()
            for chunk in r.iter_content(65536):
                total+=len(chunk)
                if total>4_000_000 or time.monotonic()-started>20:raise ValueError('torrent_limit')
                chunks.append(chunk)
        stage='torrent_validation'
        data=b''.join(chunks);infohash=torrent_hash(data)
        with c:record_detail(c,key,'torrent_validated',infohash)
        base=cfg['url'].rstrip('/')
        # Never send tracker session state to the client or client credentials to the tracker.
        s.cookies.clear()
        stage='client_login'
        r=request(s,'POST',base+'/api/v2/auth/login',data={'username':cfg['username'],'password':cfg['password']})
        if r.text.strip()!='Ok.':raise ValueError('auth')
        stage='existing_hash_check'
        rows=request(s,'GET',base+'/api/v2/torrents/info',params={'hashes':infohash}).json()
        if not isinstance(rows,list):raise ValueError('client')
        if any(not isinstance(row,dict) or row.get('hash','').lower()!=infohash for row in rows):raise ValueError('hash')
        if rows:
            status='already_present';detail='existing_hash_verified' # do not recategorize or mutate an existing transfer
        else:
            stage='submission_preflight'
            validate_action(action) # movie/file/profile may have changed during source fetch
            verify_client(cfg,s)
            # Commit the hash and stage before the only add call. A process timeout
            # still leaves evidence for operator reconciliation, never permission to retry.
            with c:record_detail(c,key,'submission_started')
            sent=True;stage='submission'
            acknowledged=False
            try:
                r=request(s,'POST',base+'/api/v2/torrents/add',files={'torrents':('release.torrent',data,'application/x-bittorrent')},data={'category':'radarr'})
                acknowledged=r.text.strip()=='Ok.'
            except Exception:
                pass # the client may already have accepted it; read only from here
            with c:record_detail(c,key,'add_acknowledged' if acknowledged else 'add_unconfirmed')
            confirmed,detail=confirm_submission(s,base,infohash)
            status='queued' if confirmed else 'uncertain'
            if confirmed and not acknowledged:detail='hash_verified_after_unconfirmed_add'
        with c:
            c.execute('update receipt set state=? where source=?',(status,key))
            record_detail(c,key,detail)
        return status
    except Exception:
        status='uncertain' if sent else 'refused'
        with c:
            c.execute('update receipt set state=? where source=?',(status,key))
            record_detail(c,key,stage+'_failed')
        return status
    finally:c.close()


def main():
    os.umask(0o077)
    try:
        token=sys.stdin.read(129)
        if not re.fullmatch(r'[A-Za-z0-9_-]{20,128}',token):raise ValueError('capability')
        action=get_action(token)
        if not action or action.get('status')!='executing' or action.get('kind')!='alternative':raise ValueError('capability')
        status=submit(action,private_config(os.environ[CONFIG]))
    except Exception:status='refused'
    print(json.dumps({'status':status}))

if __name__=='__main__':main()
