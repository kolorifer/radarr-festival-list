"""Retired persistent decisions: audit and revocation support only.

No film names/IDs or automatic approval rules. Research cannot write this ledger.
An identity approval is not an acquisition approval.
"""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import sqlite3
import time
import uuid
from identity_triage_store import private_path, private_directory, create_private, digest
from identity_triage_intake import safe_text

REASONS={'title_conflict','year_conflict'}
HEX=re.compile('[a-f0-9]{64}\\Z')
IMDB=re.compile('tt[0-9]{7,10}\\Z')


def directory():return Path.home().resolve()/'.local/state/movie-identity-reviews'


def binding(release,indexer,listing,reason):
    from tracker_metadata import valid_listing_url
    from torrent_research_evidence import validate
    if reason not in REASONS or listing.get('reason')!='listing_id_found':raise ValueError('review_source')
    if indexer.get('identifier')!='torrentleech' or str(indexer.get('name','')).casefold()!='torrentleech':raise ValueError('review_source')
    if release.get('meta_imdb') not in (None,'') or release.get('meta_tmdb') not in (None,''):raise ValueError('review_native_assertion')
    url=release.get('info_url');external=release.get('external_id')
    if not valid_listing_url(url) or not isinstance(external,str) or external!=url.rsplit('/',1)[1]:raise ValueError('review_release')
    if not isinstance(listing.get('imdb_id'),str) or not IMDB.fullmatch(listing['imdb_id']):raise ValueError('review_id')
    evidence=validate(listing['torrent_evidence'])
    if not evidence['nfo']['text'] and not evidence['description']['text']:raise ValueError('review_evidence')
    title=safe_text(release.get('title'),250);name=safe_text(release.get('name'),512);year=release.get('year')
    if type(year)!=int or not 1888<=year<=2100:raise ValueError('review_year')
    evidence_digest=digest(evidence)
    return {'source_key':digest(['torrentleech',external,name,title,year,listing['imdb_id'],reason,evidence_digest]),
            'evidence_digest':evidence_digest,'source_imdb':listing['imdb_id'],'reason':reason}


def validate_decision(value):
    if not isinstance(value,dict) or set(value)!={'source_key','evidence_digest','source_imdb','reason','target_imdb','target_tmdb','review_note'}:raise ValueError('review_schema')
    for key in ('source_key','evidence_digest'):
        if not isinstance(value[key],str) or not HEX.fullmatch(value[key]):raise ValueError('review_digest')
    for key in ('source_imdb','target_imdb'):
        if not isinstance(value[key],str) or not IMDB.fullmatch(value[key]):raise ValueError('review_id')
    if value['source_imdb']==value['target_imdb'] or value['reason'] not in REASONS:raise ValueError('review_scope')
    if type(value['target_tmdb'])!=int or not 0<value['target_tmdb']<2**31:raise ValueError('review_id')
    safe_text(value['review_note'],512)
    return value


@contextmanager
def connection(root=None,write=False):
    root=Path(root) if root is not None else directory();path=root/'decisions.sqlite3'
    if write:
        private_directory(root)
        try:create_private(path)
        except FileExistsError:pass
    private_path(root,True);private_path(path)
    c=sqlite3.connect(path.as_uri()+('?mode=rw' if write else '?mode=ro'),uri=True,timeout=1)
    try:
        if write:
            c.execute('PRAGMA synchronous=FULL')
            c.execute('CREATE TABLE IF NOT EXISTS decisions (id TEXT PRIMARY KEY, source_key TEXT NOT NULL, created REAL NOT NULL, record TEXT NOT NULL)')
            c.execute('CREATE TABLE IF NOT EXISTS revocations (decision TEXT PRIMARY KEY REFERENCES decisions(id), created REAL NOT NULL, note TEXT NOT NULL)')
            c.commit();c.execute('BEGIN IMMEDIATE')
        yield c
        if write:c.commit()
    finally:c.close()


def approve(value,root=None):
    raise ValueError('persistent_reviews_retired')


def revoke(decision,note,root=None):
    safe_text(note,512)
    with connection(root,True) as c:
        if not c.execute('SELECT 1 FROM decisions WHERE id=?',(decision,)).fetchone():raise ValueError('review_not_found')
        c.execute('INSERT INTO revocations VALUES (?,?,?)',(decision,time.time(),note))


def lookup(*args,**kwargs):
    return None  # Persistent decisions are historical audit data only.


def apply(*args,**kwargs):
    # Historical ledger is audit-only. No approval may affect identification.
    return None


def main():
    import argparse
    p=argparse.ArgumentParser(description='Record an explicitly authorized source identity decision; never acquire media.')
    sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('approve');a.add_argument('--input',required=True)
    r=sub.add_parser('revoke');r.add_argument('--decision',required=True);r.add_argument('--note',required=True)
    args=p.parse_args();os.umask(0o077)
    try:
        if args.command=='approve':
            path=private_path(Path(args.input))
            if path.stat().st_size>8192:raise ValueError('review_input_size')
            print(json.dumps({'decision_id':approve(json.loads(path.read_text())),'status':'approved_identity_only'}))
        else:
            revoke(args.decision,args.note);print(json.dumps({'status':'revoked'}))
    except (ValueError,OSError,sqlite3.Error):
        print('review decision refused');return 1
    return 0

if __name__=='__main__':raise SystemExit(main())
