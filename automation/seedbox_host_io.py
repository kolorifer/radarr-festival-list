"""Fixed read-only host sources. No Radarr, downloads, refresh or source writes."""
from contextlib import contextmanager
import hashlib,json,os,sqlite3,stat,time
from pathlib import Path
from ai_movie_investigator.contracts import require,encoded,decode,digest
from ai_movie_investigator.private_files import private_chain,read_private,safe_acl


from contextvars import ContextVar

_COLLECTOR=ContextVar('seedbox_held_collector',default=None)


def _sidecars(path,required=True):
    result={}
    for suffix in ('-wal','-shm'):
        side=path.with_name(path.name+suffix)
        if not required and not side.exists():continue
        s=side.lstat()
        require(stat.S_ISREG(s.st_mode) and s.st_uid==os.getuid() and s.st_nlink==1 and not s.st_mode&0o077,'host_database_sidecar')
        result[suffix]=(s.st_dev,s.st_ino,s.st_uid,s.st_mode,s.st_nlink)
    return result


class _HeldCollector:
    def __init__(self,pin,fd,connection,sidecars):
        self.pin=dict(pin);self.fd=fd;self.connection=connection;self.sidecars=sidecars
    def check(self):
        path=Path(self.pin['path'])
        with private_chain(path.parent):
            info=os.fstat(self.fd);current=path.lstat()
            require(stat.S_ISREG(info.st_mode) and stat.S_IMODE(info.st_mode)==0o600 and info.st_uid==os.getuid() and info.st_nlink==1 and [info.st_dev,info.st_ino]==self.pin['identity'] and os.path.samestat(info,current),'host_database_changed')
            safe_acl(self.fd,False)
            if self.sidecars is not None:require(_sidecars(path,self.pin.get('journal_mode')=='wal')==self.sidecars,'host_database_sidecar_changed')


@contextmanager
def _open_collector(pin):
    path=Path(pin['path'])
    with private_chain(path.parent) as parent:
        # Keep this descriptor until AFTER SQLite closes: closing another fd for
        # the DB inode can release this process's POSIX SQLite locks.
        fd=os.open(path.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
        c=None
        try:
            sidecars=_sidecars(path,pin.get('journal_mode')=='wal')
            held=_HeldCollector(pin,fd,None,sidecars);held.check()
            c=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=.25,isolation_level=None)
            held.connection=c
            deadline=time.monotonic()+20
            c.set_progress_handler(lambda:int(time.monotonic()>=deadline),1000)
            c.execute('pragma query_only=on');c.execute('pragma trusted_schema=off');c.execute('pragma temp_store=memory')
            if 'journal_mode' in pin:require(c.execute('pragma journal_mode').fetchone()[0]==pin['journal_mode'],'host_database_journal_changed')
            c.setlimit(sqlite3.SQLITE_LIMIT_LENGTH,1048576)
            # Establish native WAL/SHM handles, without freezing a data snapshot.
            c.execute('select count(*) from sqlite_schema').fetchone();held.check()
            c.set_progress_handler(None,0)
            yield held
        finally:
            if c is not None:c.close()
            os.close(fd)


@contextmanager
def collector_lifetime(pin):
    """Installed runner holds one read-only connection across native WAL cycles.

    The bootstrap establishes a kernel no-create boundary BEFORE this function.
    Missing/replaced sidecars refuse; they are never manufactured or ignored.
    """
    require(_COLLECTOR.get() is None and pin.get('journal_mode')=='wal','host_collector_lifetime')
    with _open_collector(pin) as held:
        token=_COLLECTOR.set(held)
        try:yield
        finally:_COLLECTOR.reset(token)


@contextmanager
def _transaction(held):
    held.check();c=held.connection
    require(not c.in_transaction,'host_database_nested_transaction')
    deadline=time.monotonic()+20;c.set_progress_handler(lambda:int(time.monotonic()>=deadline),1000)
    try:
        c.execute('BEGIN');yield c
    finally:
        c.rollback();c.set_progress_handler(None,0)
    held.check()


@contextmanager
def database(pin):
    held=_COLLECTOR.get()
    if held is not None and pin['path']==held.pin['path']:
        require(pin==held.pin,'host_database_selection_changed')
        with _transaction(held) as c:yield c
    else:
        if held is not None:
            require(pin['identity']!=held.pin['identity'],'host_database_selection_changed')
            # Check actual identity before an alternate DB descriptor can open
            # and close our collector inode. Private selected paths must not be
            # replaced concurrently; this check is not an atomic pathname lock.
            path=Path(pin['path'])
            with private_chain(path.parent):
                require(not os.path.samestat(path.lstat(),os.fstat(held.fd)),'host_database_selection_changed')
        with _open_collector(pin) as selected:
            with _transaction(selected) as c:yield c


def selected_snapshot(c,case_id,now):
    """One explicitly selected case, preserving global coverage as incomplete.

    Avoid the old global 100-eligible export ceiling without truncating a queue.
    Full source event history remains separately retained by the durable cursor.
    """
    from identity_selection import metrics,CONFLICT_RESEARCH
    rows=c.execute('select x.version,x.observed,(select min(s.observed) from selection_events s where s.release=x.release),h.material from selection_current x join selection_history h on h.version=x.version where x.case_key=?',(case_id,)).fetchall()
    require(len(rows)==1,'host_case_missing');version,observed,first,raw=rows[0];material=json.loads(raw);m=material['metadata'];o=material['outcome']
    case=dict(case_id=case_id,version=version,observed_at=observed,first_observed_at=first,title=m['title'],year=m['year'],route=material['route'],reason=o['reason'],correlation=material['correlation'],original_type=m.get('original_type','movie'),source_identity=dict(imdb=m['imdb'],tmdb=m['tmdb'],asserted_imdb=o.get('asserted_imdb'),asserted_tmdb=o.get('asserted_tmdb')))
    items=[]
    if case['route']=='eligible':
        contradictions=([o['reason'] if o['reason'] in ('title_conflict','year_conflict') else 'identifier_conflict'] if o['reason'] in CONFLICT_RESEARCH else ['missing_crosswalk'] if o['reason']=='tmdb_mapping_missing' else ['unknown_identity'])
        facts=dict(title=m['title'],year=m['year'],imdb=o.get('asserted_imdb') or m['imdb'],tmdb=o.get('asserted_tmdb') or m['tmdb'],variants=[m['title']],contradictions=contradictions,director=None,runtime=None)
        if 'torrent_evidence' in o:facts['torrent_evidence']=o['torrent_evidence']
        items=[dict(case_id=case_id,seed=False,eligibility='explicit_unresolved',facts=facts,provenance=[dict(source='stage1_outcome',digest=version,observed_at=observed)],historical_candidates=[],observed_at=observed)]
    coverage=metrics(c);global_coverage=dict(coverage)
    snapshot=encoded(dict(kind='seedbox_selected_snapshot_v1',selected_case_id=case_id,version=1,generated_at=now,coverage=coverage,cases=[case],items=items))
    return snapshot,m,global_coverage


def _configuration(pin):
    from deploy.run import read_environment
    raw=read_private(Path(pin['path']),65536);require(hashlib.sha256(raw).hexdigest()==pin['sha256'],'host_configuration_changed')
    class Text:
        def read_text(self,*a,**kw):return raw.decode()
        def stat(self):return Path(pin['path']).stat()
    values=read_environment(Text())
    # No exporting into os.environ and no returning unrelated production keys.
    selected={k:values.get(k) for k in ('TMDB_API_TOKEN','MOVIE_INTEL_TL_COOKIE_FILE','MOVIE_INTEL_TL_METADATA_ENABLED')}
    values.clear();return selected


class SourceFailure(ValueError):
    """Finite safe audit facts; never include URLs, credentials or response text.

    No retry permission is implied. The runner must persist this outcome and
    enforce bounded retry/cooldown policy before another source read.
    """
    def __init__(self, reason, *, retry_after=None):
        super().__init__(reason)
        self.reason=reason
        self.retry_after=retry_after
        self.owner_action=reason not in ('source_rate_limited','source_temporary','source_deadline')


def _get(url,*,token=None,cookies=None):
    import requests,re
    from ai_movie_investigator.responses_http import total_deadline
    from tracker_metadata import _backoff
    listing=re.fullmatch(r'https://www\.torrentleech\.org/torrent/[1-9][0-9]{0,19}',url)
    catalogue=re.fullmatch(r'https://api\.themoviedb\.org/3/(?:find/tt[0-9]{7,12}\?external_source=imdb_id|movie/[1-9][0-9]*\?append_to_response=credits,release_dates)',url)
    require(bool(listing) != bool(catalogue),'host_source_origin')
    require((listing and cookies and token is None) or (catalogue and token and cookies is None),'host_source_credentials')
    try:
        # Existing absolute main-thread timer covers DNS, headers and slow
        # trickles, not just completed chunks. Byte-sized decoded reads also
        # bound how much work occurs between explicit deadline checks.
        with total_deadline(15) as check, requests.Session() as session:
            session.trust_env=False
            headers={'Accept':'application/json' if catalogue else 'text/html','Accept-Encoding':'identity','User-Agent':'movie-assessment/1'}
            if token:headers['Authorization']='Bearer '+token
            if cookies:
                for key,value in cookies.items():session.cookies.set(key,value,domain='www.torrentleech.org',path='/')
            with session.get(url,headers=headers,allow_redirects=False,stream=True,timeout=(3,5)) as response:
                status=response.status_code
                if status in (401,403):raise SourceFailure('source_auth_denied')
                if status==429:raise SourceFailure('source_rate_limited',retry_after=_backoff(response.headers.get('Retry-After')))
                if status==404:raise SourceFailure('source_missing')
                if 300<=status<400:raise SourceFailure('source_redirect')
                if status>=500:raise SourceFailure('source_temporary',retry_after=_backoff(response.headers.get('Retry-After')))
                if status!=200:raise SourceFailure('source_http_refused')
                if response.headers.get('Content-Encoding','identity').lower() not in ('','identity'):raise SourceFailure('source_content_invalid')
                expected='application/json' if catalogue else 'text/html'
                if expected not in response.headers.get('Content-Type','').lower():raise SourceFailure('source_content_invalid')
                data=bytearray()
                for chunk in response.iter_content(1):
                    check()
                    data.extend(chunk)
                    if len(data)>1000000:raise SourceFailure('source_size_bound')
                check()
                return bytes(data),time.time()
    except SourceFailure:raise
    except __import__('ai_movie_investigator.contracts',fromlist=['Refusal']).Refusal as error:
        if str(error)=='responses_deadline_exceeded':raise SourceFailure('source_deadline',retry_after=60) from None
        raise
    except (TimeoutError,requests.Timeout):raise SourceFailure('source_deadline',retry_after=60) from None
    except requests.RequestException:raise SourceFailure('source_temporary',retry_after=60) from None


def acquire(config,claim,snapshot_raw,metadata,*,revalidation=None):
    """Fixed exact listing + exact IMDb catalogue crosswalk. No title search."""
    from automation.seedbox_source_evidence import actor_listing,listing_facts,catalogue_facts
    from ai_movie_investigator.snapshot_review import projection,select
    from bs4 import BeautifulSoup
    import re
    now=time.time();snapshot_sha=hashlib.sha256(snapshot_raw).hexdigest();select(snapshot_raw,snapshot_sha,claim['case_id'],claim['version'],now=now)
    with database(config['actor_database']) as actor:binding=actor_listing(actor,claim['case_id'],metadata,config['sources'],config['listing_source'])
    if revalidation is not None:
        target=dict(version=binding['actor_version'],row_sha256=binding['target']['row_sha256'],ref=binding['target']['ref'],case_id=claim['case_id'])
        require(digest(binding['url'])==revalidation['source_url_sha256'] and digest(target)==revalidation['target_sha256'],'delivery_selected_target_changed')
    proof=claim.get('correction_proposal')
    if proof is not None:
        target=dict(version=binding['actor_version'],row_sha256=binding['target']['row_sha256'],ref=binding['target']['ref'],case_id=claim['case_id'])
        require(digest(proof)==claim['correction_proposal_sha256'] and digest(binding['url'])==proof['source_url_sha256'] and digest(target)==proof['target_sha256'],'host_correction_source_target_changed')
    try:
        env=_configuration(config['source_configuration']);require(env['TMDB_API_TOKEN'] and env['MOVIE_INTEL_TL_COOKIE_FILE'] and env['MOVIE_INTEL_TL_METADATA_ENABLED']=='1','host_source_configuration')
        # Main selects canonical spelling and pins the existing cookie file. The
        # configured alias must resolve to that exact selection, never another file.
        cookie_pin=config['cookie_file'];cookie_path=Path(cookie_pin['path'])
        require(Path(env['MOVIE_INTEL_TL_COOKIE_FILE']).resolve(strict=True)==cookie_path,'host_cookie_selection')
        cookies_raw=read_private(cookie_path,16384);require(hashlib.sha256(cookies_raw).hexdigest()==cookie_pin['sha256'],'host_cookie_changed')
        cookies=json.loads(cookies_raw);require(type(cookies) is dict and cookies and all(type(k) is str and re.fullmatch(r'[A-Za-z0-9_-]{1,100}',k) and type(v) is str and 0<len(v)<=8192 and all(33<=ord(ch)<=126 and ch not in ';,' for ch in v) for k,v in cookies.items()),'host_cookie_format')
    except (OSError,ValueError,KeyError):raise SourceFailure('source_configuration_unavailable') from None
    raw,observed=_get(binding['url'],cookies=cookies)
    from tracker_metadata import parse_listing
    if parse_listing(raw,binding['release_name'])['reason']=='login_required':raise SourceFailure('source_auth_denied')
    facts=listing_facts(raw,release_name=binding['release_name'],case_id=claim['case_id'],version=claim['version'],observed_at=observed,expires_at=observed+900,revision=2)
    if proof is not None:require(facts['observed_at']>proof['parent_source_observed_at'],'host_correction_observation_not_new')
    if proof is not None:require(digest({k:v for k,v in facts.items() if k not in ('observed_at','expires_at')})==proof['corrected_semantic_sha256'],'host_correction_source_changed')
    if revalidation is not None:require(digest({k:v for k,v in facts.items() if k not in ('observed_at','expires_at')})==revalidation['listing_semantic_sha256'],'delivery_material_facts_changed')
    require(facts['imdb'] is not None,'host_listing_crosswalk_needed')
    found,found_at=_get('https://api.themoviedb.org/3/find/'+facts['imdb']+'?external_source=imdb_id',token=env['TMDB_API_TOKEN'])
    movies=json.loads(found).get('movie_results');require(type(movies) is list and len(movies)==1 and type(movies[0].get('id')) is int and movies[0]['id']>0,'host_catalogue_ambiguous')
    tmdb=movies[0]['id'];cat_raw,cat_at=_get('https://api.themoviedb.org/3/movie/'+str(tmdb)+'?append_to_response=credits,release_dates',token=env['TMDB_API_TOKEN'])
    catalogue=catalogue_facts(cat_raw,expected_tmdb=tmdb,expected_imdb=facts['imdb'],observed_at=cat_at,expires_at=cat_at+900)
    if proof is not None:require(catalogue['observed_at']>proof['parent_catalogue_observed_at'],'host_correction_observation_not_new')
    if proof is not None:require(digest({k:v for k,v in catalogue.items() if k not in ('observed_at','expires_at')})==proof['catalogue_semantic_sha256'],'host_correction_catalogue_changed')
    if revalidation is not None:require(digest({k:v for k,v in catalogue.items() if k not in ('observed_at','expires_at')})==revalidation['catalogue_semantic_sha256'],'delivery_material_facts_changed')
    source_raw=encoded(facts);catalogue_raw=encoded(catalogue);h=lambda b:hashlib.sha256(b).hexdigest()
    att=dict(kind='host_authenticated_normalized_case_v1',snapshot_sha256=snapshot_sha,case_id=claim['case_id'],version=claim['version'],source_sha256=h(source_raw),catalogue_sha256=h(catalogue_raw),source_original_sha256=h(raw),catalogue_original_sha256=h(cat_raw),source_linkage_verified=True,catalogue_crosswalk_verified=True,observed_at=time.time(),expires_at=max(observed,cat_at)+900)
    projected=projection(snapshot_raw,snapshot_sha,claim['case_id'],claim['version'],source_raw,catalogue_raw,att,now=time.time())
    soup=BeautifulSoup(raw,'html.parser');node=soup.select_one('#nfo_text');nfo=node.get_text('\n',strip=True) if node else ''
    local=encoded(dict(tracker_url=binding['url'],release_name=binding['release_name'],nfo_text=nfo[:16384]))
    return dict(derivation_revision=2,projection=projected,local_raw=local,source_original=raw,catalogue_original=cat_raw,find_original=found,snapshot=snapshot_raw,source=source_raw,catalogue=catalogue_raw,attestation=att,target_pin=dict(version=binding['actor_version'],row_sha256=binding['target']['row_sha256'],ref=binding['target']['ref'],case_id=claim['case_id']),coverage=dict(nfo_truncated=len(nfo)>16384,cast_truncated=len(json.loads(cat_raw).get('credits',{}).get('cast',[]))>20,source_original_observed_at=observed,catalogue_original_observed_at=cat_at))
