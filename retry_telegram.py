"""Private original-message receipts and durable, bounded retry-status edits.

No provider lookups or download operations. Transport/action preparation are
injected by the actor; receipt ownership never comes from webhook fields.
"""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import tempfile
import threading
import time
from identity_triage_store import digest
from identity_triage_intake import normalize
from identity_triage_observer import envelope

_LOCAL=threading.local()
_BIND_LOCK=threading.Lock()

@contextmanager
def capture():
    previous=getattr(_LOCAL,'receipts',None);receipts=[];_LOCAL.receipts=receipts
    try:yield receipts
    finally:_LOCAL.receipts=previous


def receipt(method, body, response):
    refs=getattr(_LOCAL,'receipts',None)
    if refs is None or method not in ('sendMessage','sendPhoto'):return
    result=response.get('result') or {}
    if not isinstance(result,dict) or not isinstance(result.get('chat'),dict):return
    ident=result.get('message_id')
    if type(ident)!=int or ident<=0:return
    chat=(result.get('chat') or {}).get('id')
    if chat is None or str(chat)!=str(body.get('chat_id')):return
    refs.append({'chat_id':str(chat),'message_id':ident,'kind':'caption' if method=='sendPhoto' else 'text'})


def schema(c):
    c.execute('create table if not exists retry_messages(version text primary key,payload text,refs text,context text,terminal text,prepared text,state text not null default "waiting",attempts integer not null default 0,due real not null default 0,created real not null)')


def completed(c,version,context,terminal,now):
    # Written in the same transaction as the retry outcome, including expiry.
    kept={k:context[k] for k in ('meta','category','review_listing') if k in context} if context else {}
    raw=json.dumps(kept)
    if len(raw.encode())>262144:raw='{}'
    c.execute('insert into retry_messages(version,context,terminal,created) values(?,?,?,?) on conflict(version) do update set context=excluded.context,terminal=excluded.terminal',
              (version,raw,terminal,now))


def binding(payload,context,refs,sources):
    from identity_retry import TEMPORARY
    meta=context.get('meta') or {}
    if meta.get('identity_reason') not in TEMPORARY or not refs:return False
    if len(refs)>8 or len({r['chat_id'] for r in refs})!=1:return False
    observed=envelope(payload,context,sources);r=normalize(observed,sources,'outcome')
    if r.get('reason'):return False
    version=digest([r['release'],r['metadata']])
    REVIEW_RELEASE_KEYS=("protocol","timestamp","publishDate","publish_date","name","title","year","size","seeders","leechers",
                         "download_url","downloadUrl","magnet_uri","magnetUrl","magnet_url","info_url","infoUrl","link","external_id")
    data=payload['data']
    saved={'_retry_original_event':1,'event':payload.get('event'),'timestamp':payload.get('timestamp'),'data':{
        'release':{k:v for k,v in data['release'].items() if k in (*REVIEW_RELEASE_KEYS,'type','meta_imdb','meta_tmdb','season','episode','resolution','source','group','edition','cut')},
        'indexer':{k:v for k,v in data['indexer'].items() if k in ('name','protocol','identifier')},
        'action':{'type':(data.get('action') or {}).get('type')},
        'result':{'rejections':(data.get('result') or {}).get('rejections',[])}}}
    raw=json.dumps(saved)
    if len(raw.encode())>65536:return False
    return {'version':version,'payload':raw,'refs':json.dumps(refs),'created':time.time()}


def save_binding(store,item):
    with store.tx() as c:
        c.execute('delete from retry_messages where created<?',(store.clock()-8*86400,))
        if c.execute('select count(*) from retry_messages').fetchone()[0]>=10000:return False
        c.execute('insert into retry_messages(version,payload,refs,created) values(?,?,?,?) on conflict(version) do update set payload=coalesce(retry_messages.payload,excluded.payload),refs=coalesce(retry_messages.refs,excluded.refs)',
                  (item['version'],item['payload'],item['refs'],item['created']))
    return True


def bind(store,payload,context,refs,sources):
    item=binding(payload,context,refs,sources)
    if not item:return False
    item['created']=store.clock()
    return save_binding(store,item)


def queue_binding(directory,payload,context,refs,sources):
    """Retain the acknowledged message before any contended SQLite transaction.

    Atomic, owner-only spool; first receipt wins. The actor worker drains it
    without sending messages, fetching metadata or creating approvals here.
    """
    item=binding(payload,context,refs,sources)
    if not item:return False
    from identity_triage_store import private_directory
    directory=private_directory(Path(directory))
    spool=private_directory(directory/'message-bindings')
    if len(list(spool.iterdir()))>=1000:raise ValueError('binding_capacity')
    target=spool/(item['version']+'.json')
    raw=json.dumps(item).encode()
    if len(raw)>131072:raise ValueError('binding_size')
    fd,tmp=tempfile.mkstemp(dir=spool,prefix='.binding-')
    try:
        with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
        with _BIND_LOCK:
            if not target.exists():os.replace(tmp,target)
        dfd=os.open(spool,os.O_RDONLY)
        try:os.fsync(dfd)
        finally:os.close(dfd)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
    return True


def flush_binding(store):
    from identity_triage_store import private_path
    spool=store.directory/'message-bindings'
    if not spool.exists():return
    private_path(spool,True)
    for path in sorted(spool.glob('*.json'))[:1]:
        private_path(path)
        if path.stat().st_size>131072:raise ValueError('binding_size')
        item=json.loads(path.read_text())
        if set(item)!={'version','payload','refs','created'} or path.stem!=item['version']:raise ValueError('binding_shape')
        if item['created']<store.clock()-8*86400 or save_binding(store,item):path.unlink()


def pump(store,prepare,edit):
    """One edit batch per tick, five attempts maximum; no sends or re-resolution."""
    flush_binding(store)
    now=store.clock()
    with store.tx() as c:
        c.execute('delete from retry_messages where created<?',(now-8*86400,))
        row=c.execute('select m.version,m.payload,m.refs,m.context,m.terminal,m.prepared,m.attempts from retry_messages m join retry_jobs j on j.version=m.version where m.state="waiting" and m.payload is not null and m.refs is not null and m.context is not null and m.due<=? and j.state in ("done","review") and j.reason!="superseded" order by m.created limit 1',(now,)).fetchone()
    if not row:return False
    version,payload,refs,context,terminal,prepared,attempts=row
    try:
        if not prepared:
            original=json.loads(payload)
            if original.get('_retry_original_event')!=1:terminal='original_event_unavailable'
            prepared=json.dumps(prepare(original,json.loads(context),terminal))
            with store.tx() as c:c.execute('update retry_messages set prepared=? where version=?',(prepared,version))
        edit(json.loads(refs),json.loads(prepared))
    except Exception:
        with store.tx() as c:c.execute('update retry_messages set attempts=attempts+1,due=?,state=? where version=?',
            (now+min(3600,60*2**attempts),'failed' if attempts>=4 else 'waiting',version))
        print('identity_retry message_edit_deferred',flush=True)
        return True
    with store.tx() as c:c.execute('update retry_messages set state="edited",attempts=attempts+1 where version=?',(version,))
    return True
