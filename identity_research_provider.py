"""Strict metadata-GET protocol and bounded projections. No arbitrary URL API."""
from contextlib import contextmanager
import signal
from email.utils import parsedate_to_datetime
import http.client
import json
import re
import time
from urllib.parse import urlencode

from identity_triage_store import digest

IMDB = re.compile(r'tt[0-9]{7,10}\Z')
REASONS = {'missing_crosswalk','title_conflict','year_conflict','runtime_conflict','director_conflict','edition_conflict','identifier_conflict','unknown_identity','missing_id','ambiguous_title'}


def clean(value, limit=512):
    if not isinstance(value,str) or not 1 <= len(value) <= limit or any(ord(c)<32 for c in value) or any(x in value.lower() for x in ('http:', 'https:', 'magnet:', '<', '>', 'passkey=', 'token=', 'authorization')):
        raise ValueError('unsafe_text')
    return value


def ident(value):
    if type(value) != int or not 0 < value < 2**31:
        raise ValueError('invalid_id')
    return value


def validate_case(item):
    from identity_research_store import ELIGIBLE
    if not isinstance(item,dict) or set(item)!={'case_id','seed','eligibility','facts','provenance','historical_candidates','observed_at'}:
        raise ValueError('case_schema')
    if not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}',item['case_id']) or type(item['seed'])!=bool or item['eligibility'] not in ELIGIBLE:
        raise ValueError('case_eligibility')
    if item['seed'] != (item['eligibility']=='seed_missing_crosswalk'):
        raise ValueError('seed_eligibility')
    if type(item['observed_at']) not in (int,float) or not 0 < item['observed_at'] < 10**11:
        raise ValueError('observation_time')
    f=item['facts']
    if set(f)-{'torrent_evidence'}!={'title','year','imdb','tmdb','variants','contradictions','director','runtime'}:
        raise ValueError('facts_schema')
    if 'torrent_evidence' in f:
        from torrent_research_evidence import validate
        validate(f['torrent_evidence'])
    clean(f['title'],256)
    if type(f['year'])!=int or not 1870<=f['year']<=2100:
        raise ValueError('invalid_year')
    if f['imdb'] is not None and (not isinstance(f['imdb'],str) or not IMDB.fullmatch(f['imdb'])):
        raise ValueError('invalid_imdb')
    if f['tmdb'] is not None: ident(f['tmdb'])
    if not isinstance(f['variants'],list) or not 1<=len(f['variants'])<=2 or len(set(f['variants'])) != len(f['variants']):
        raise ValueError('variant_budget')
    for title in f['variants']:clean(title,256)
    if not isinstance(f['contradictions'],list) or set(f['contradictions'])-REASONS:
        raise ValueError('contradiction_schema')
    if f['director'] is not None:clean(f['director'],128)
    if f['runtime'] is not None and (type(f['runtime'])!=int or not 1<=f['runtime']<=1440):raise ValueError('invalid_runtime')
    if not isinstance(item['provenance'],list) or not 1<=len(item['provenance'])<=8:raise ValueError('provenance')
    # Source URLs are represented by fixed names and content digests, never followed.
    for p in item['provenance']:
        if set(p)!={'source','digest','observed_at'} or p['source'] not in {'stage1_seed','stage1_outcome','resolver_preflight','issue44_public_evidence','stored_source_assertion'} or not re.fullmatch('[a-f0-9]{64}',p['digest']) or type(p['observed_at']) not in (int,float) or not 0<p['observed_at']<10**11:
            raise ValueError('provenance')
    if not isinstance(item['historical_candidates'],list) or len(item['historical_candidates'])>3:raise ValueError('candidate_budget')
    for value in item['historical_candidates']:ident(value)
    return json.loads(json.dumps(item,allow_nan=False))


def route(kind,value):
    if kind=='find' and isinstance(value,str) and IMDB.fullmatch(value):
        return '/3/find/'+value+'?external_source=imdb_id'
    if kind=='details':
        return '/3/movie/'+str(ident(value))+'?append_to_response=external_ids%2Calternative_titles%2Ctranslations%2Crelease_dates%2Ccredits'
    if kind in ('movie_search','tv_search'):
        return '/3/search/'+('movie' if kind=='movie_search' else 'tv')+'?'+urlencode({'query':clean(value,256),'page':1,'include_adult':'false'})
    raise ValueError('request_not_allowed')


def text_or_none(value,limit=512):
    return clean(value,limit) if value else None


def brief(r,tv=False):
    if not isinstance(r,dict):raise ValueError('record')
    return {'id':ident(r.get('id')),'title':clean(r.get('name' if tv else 'title'),256),
            'original_title':text_or_none(r.get('original_name' if tv else 'original_title'),256),
            'date':text_or_none(r.get('first_air_date' if tv else 'release_date'),20),'type':'tv' if tv else 'movie'}


def projection(kind,data,expected=None):
    if not isinstance(data,dict):raise ValueError('response_object')
    def rows(name,maximum=20):
        result=data.get(name,[])
        if not isinstance(result,list) or len(result)>maximum:raise ValueError('response_rows')
        return result
    if kind=='find':
        return {'movies':[brief(x) for x in rows('movie_results')],
                'tv':[brief(x,True) for x in rows('tv_results')],
                'tv_other':bool(rows('tv_episode_results') or rows('tv_season_results'))}
    if kind.endswith('_search'):
        if data.get('page')!=1:raise ValueError('search_page')
        return {'results':[brief(x,kind=='tv_search') for x in rows('results')]}
    b=brief(data)
    if b['id']!=expected:raise ValueError('detail_id_conflict')
    external=data.get('external_ids',{}).get('imdb_id')
    if external is not None and (not isinstance(external,str) or not IMDB.fullmatch(external)):raise ValueError('external_id')
    runtime=data.get('runtime')
    if runtime is not None and (type(runtime)!=int or not 0<=runtime<=1440):raise ValueError('runtime')
    directors=[clean(x['name'],128) for x in data.get('credits',{}).get('crew',[]) if x.get('job')=='Director']
    if len(directors)>20:raise ValueError('directors')
    aliases=[clean(x['title'],256) for x in data.get('alternative_titles',{}).get('titles',[])][:100]
    translations=[clean(x['data']['title'],256) for x in data.get('translations',{}).get('translations',[]) if x.get('data',{}).get('title')][:100]
    dates=[clean(d['release_date'],40) for x in data.get('release_dates',{}).get('results',[]) for d in x.get('release_dates',[])][:100]
    cast=[clean(x['name'],128) for x in data.get('credits',{}).get('cast',[])[:8]]
    language=text_or_none(data.get('original_language'),20)
    return b|{'cast':cast,'original_language':language,'imdb':external,'runtime':runtime,'directors':directors,'aliases':aliases,'translations':translations,'dates':dates}


def retry_after(value,now):
    try:
        if value and re.fullmatch('[0-9]{1,9}',value):return int(value)
        return max(0,parsedate_to_datetime(value).timestamp()-now) if value else 0
    except (ValueError,TypeError,OverflowError):return 0


@contextmanager
def request_deadline():
    # The installed worker is single-threaded. Total response lifetime, including
    # a slow trickle, is bounded independently of socket idle timeout.
    def expired(signum, frame):
        raise TimeoutError('metadata_deadline')
    previous = signal.signal(signal.SIGALRM, expired)
    timer = signal.setitimer(signal.ITIMER_REAL, 10)
    if timer[0] or timer[1]:
        signal.setitimer(signal.ITIMER_REAL, *timer)
        signal.signal(signal.SIGALRM, previous)
        raise ValueError('nested_deadline')
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def strict_json(body):
    def pairs(items):
        result = {}
        for k, v in items:
            if k in result: raise ValueError('duplicate_json_key')
            result[k] = v
        return result
    def constant(value): raise ValueError('invalid_json_constant')
    return json.loads(body, object_pairs_hook=pairs, parse_constant=constant)


class Provider:
    def __init__(self,store,run,connection,token,clock=time.time,sleep=time.sleep):
        if not isinstance(token,str) or not re.fullmatch(r'[A-Za-z0-9_.-]{20,4096}',token):raise ValueError('credential_format')
        self.store=store;self.run=run;self.connection=connection;self.token=token;self.clock=clock;self.sleep=sleep
        self.cache_hits=0

    def get(self,lease,kind,value):
        path=route(kind,value);key=digest([kind,value])
        # All calls, including failures, share the same persisted per-provider gate.
        self.sleep(1.05)
        request,cached=self.store.reserve(self.run,lease['token'],key)
        if cached:
            self.cache_hits+=1
            return cached
        result={'reason':'transport_failure','observed_at':self.clock()}
        try:
            with request_deadline():
                self.connection.request('GET',path,headers={'Authorization':'Bearer '+self.token,'Accept':'application/json'})
                response=self.connection.getresponse()
                status=response.status
                if status in (401,403):result['reason']='auth_failure'
                elif status==429:result.update(reason='rate_limited',retry_after=retry_after(response.getheader('Retry-After'),self.clock()))
                elif status==404:result['reason']='not_found'
                elif 300<=status<400:result['reason']='redirect_denied'
                elif status!=200:result['reason']='http_failure'
                else:
                    content_type=response.getheader('Content-Type','').split(';')[0].strip().lower()
                    length=response.getheader('Content-Length')
                    if length and (not length.isdigit() or int(length)>1_048_576):
                        result['reason']='response_too_large';self.connection.close()
                    elif content_type!='application/json':result['reason']='malformed_response';self.connection.close()
                    else:
                        body=response.read(1_048_577)
                        if len(body)>1_048_576:result['reason']='response_too_large';self.connection.close()
                        else:
                            if self.token.encode() in body:raise ValueError('credential_echo')
                            parsed=strict_json(body)
                            result.update(reason='ok',data=projection(kind,parsed,value),expires_at=self.clock()+86400)
                if status!=200:
                    # No following redirects, parsing error bodies or reusing a dirty socket.
                    self.connection.close()
        except (OSError,http.client.HTTPException):
            self.connection.close()
        except (ValueError,TypeError,KeyError,AttributeError,RecursionError):
            result['reason']='malformed_response';self.connection.close()
        self.store.record(request,key,result)
        return result
