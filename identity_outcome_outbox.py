"""Private observer retry spool; contains only already sanitized observations.

Admission into this spool is asynchronous: the pre-persist memory window is lossy
and counted separately. Once committed, delivery is at least once until collector ACK.
"""
from contextlib import contextmanager
import json
import sqlite3
import re
import time
from identity_triage_store import create_private, private_directory, private_path


class Outbox:
    def __init__(self,directory):
        self.directory=private_directory(directory);self.path=self.directory/'outcomes.sqlite3'
        try:create_private(self.path)
        except FileExistsError:pass
        with self.tx() as c:
            c.execute('create table if not exists pending(id TEXT PRIMARY KEY,body TEXT NOT NULL,created REAL NOT NULL,attempts INTEGER NOT NULL DEFAULT 0,due REAL NOT NULL)')
            c.execute('create table if not exists counters(name TEXT PRIMARY KEY,value INTEGER NOT NULL)')

    @contextmanager
    def tx(self):
        private_path(self.directory,True);private_path(self.path)
        c=sqlite3.connect(self.path.as_uri()+'?mode=rw',uri=True,timeout=.1,isolation_level=None)
        try:
            c.execute('pragma synchronous=FULL');c.execute('BEGIN IMMEDIATE');yield c;c.commit()
        finally:c.close()

    @staticmethod
    def count(c,key):
        c.execute('insert into counters values (?,1) on conflict(name) do update set value=value+1',(key,))

    def put(self,item):
        from identity_triage_intake import normalize
        if set(item)!={'version','event','id','timestamp','data'} or set(item['data'])!={'release','indexer','outcome'}:
            raise ValueError('outbox_shape')
        data=item['data'];indexer=data['indexer'];release=data['release']
        if set(indexer)!={'identifier','name'} or not re.fullmatch('[a-z0-9_-]{1,64}',indexer['identifier']) or not re.fullmatch('[A-Za-z0-9 ._-]{1,80}',indexer['name']):
            raise ValueError('outbox_source')
        if set(release)-{'type','protocol','implementation','title','year','name','external_id','meta_imdb','meta_tmdb'}:
            raise ValueError('outbox_fields')
        checked=normalize(item,{indexer['identifier']:indexer['name']},'outcome')
        if checked.get('reason'):
            if release!={'type':'movie'} or data['outcome']!={'status':'unresolved','category':'other','reason':'invalid_metadata'}:
                raise ValueError('outbox_quarantine')
        body=json.dumps(item,sort_keys=True)
        if len(body.encode())>65536:raise ValueError('outcome_size')
        with self.tx() as c:
            if c.execute('select count(*) from pending').fetchone()[0]>=10000:raise ValueError('outbox_capacity')
            cursor=c.execute('insert or ignore into pending values (?,?,?,0,?)',(item['id'],body,time.time(),time.time()))
            if cursor.rowcount:self.count(c,'persisted')

    def next(self,now=None):
        with self.tx() as c:
            row=c.execute('select id,body,attempts from pending where due<=? order by created,id limit 1',(time.time() if now is None else now,)).fetchone()
            return (row[0],json.loads(row[1]),row[2]) if row else None

    def ack(self,key):
        with self.tx() as c:
            if c.execute('delete from pending where id=?',(key,)).rowcount:self.count(c,'delivered')

    def failed(self,key,attempts):
        with self.tx() as c:
            c.execute('update pending set attempts=attempts+1,due=? where id=?',(time.time()+min(300,2**min(attempts+1,8)),key))
            self.count(c,'delivery_failures')

    def metrics(self):
        with self.tx() as c:
            return dict(c.execute('select name,value from counters'))|{'pending':c.execute('select count(*) from pending').fetchone()[0]}
