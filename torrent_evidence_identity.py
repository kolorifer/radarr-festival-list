"""Conjunctive identification from a checked, ID-less torrent listing.

No film-specific facts, scoring, fuzzy runtime/year tolerance or conflicting-ID
repair. Public structured release dates supplement TMDb only after both IDs agree.
"""
import json
import os
import re
import threading
import time
from collections import OrderedDict
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import URLError, HTTPError
from identity_request_guard import reserve, cooldown
from identity_triage_store import digest
from torrent_research_evidence import validate,MAX_TEXT
import tmdb_resolver as tmdb

FLAG='MOVIE_INTEL_TORRENT_EVIDENCE_ENABLED'
_CACHE=OrderedDict();_LOCK=threading.Lock();_UNTIL=0

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args):return None
urlopen=build_opener(NoRedirect).open


def nfo_facts(evidence):
    text=validate(evidence)['nfo']['text']
    # Image-list truncation is independent; a full-length text cap is inconclusive.
    if not text or len(text)>=MAX_TEXT:return None
    parts=re.split(r'\bVideo(?: #\d+)? ID\s*:',text,maxsplit=1)
    if len(parts)!=2 or not re.search(r'\bGeneral\b',parts[0]):return None
    durations=re.findall(r'\bDuration\s*:\s*(?:(\d{1,2})\s*h\s*)?(\d{1,3})\s*min\b',parts[0])
    if len(durations)!=1:return None
    hours,minutes=durations[0]
    if hours and int(minutes)>=60:return None
    duration=int(hours or 0)*60+int(minutes)
    if not 0<duration<=1440:return None
    tracks=re.split(r'\bAudio(?: #\d+)? ID\s*:',text)
    if len(tracks)!=2:return None  # Multiple/dubbed tracks require review.
    audio=re.split(r'\b(?:Text(?: #\d+)? ID\s*:|Menu\s)',tracks[1],maxsplit=1)[0]
    languages=re.findall(r'\bLanguage\s*:\s*([A-Za-z]+(?:[ -][A-Za-z]+)*?)(?=\s*\(|\s+(?:Default|Forced|Service kind|Title)\s*:|$)',audio)
    if len(languages)!=1:return None
    return {'runtime':duration,'language':languages[0].strip().casefold()}


def release_years(entity,qid,imdb,tmdb_id):
    """Use only non-deprecated value claims with exact matching identity links."""
    item=entity['entities'][qid]
    if item.get('id')!=qid or item.get('type')!='item':return set()
    claims=item['claims']
    def values(prop):
        return [x['mainsnak']['datavalue']['value'] for x in claims.get(prop,[])
                if x.get('rank')!='deprecated' and x.get('mainsnak',{}).get('snaktype')=='value']
    if set(values('P345'))!={imdb} or set(values('P4947'))!={str(tmdb_id)}:return set()
    years=set()
    for value in values('P577'):
        if (isinstance(value,dict) and value.get('precision',0)>=9
                and value.get('calendarmodel')=='http://www.wikidata.org/entity/Q1985727'
                and not value.get('before') and not value.get('after')):
            match=re.fullmatch(r'\+(\d{4})-\d{2}-\d{2}T00:00:00Z',value.get('time',''))
            if match:years.add(match[1])
    return years


def wikidata_years(qid,imdb,tmdb_id):
    global _UNTIL
    if not isinstance(qid,str) or not re.fullmatch(r'Q[1-9][0-9]{0,11}',qid):return set()
    if time.monotonic()<_UNTIL:return set()
    request=Request('https://www.wikidata.org/wiki/Special:EntityData/'+qid+'.json',headers={'Accept':'application/json','User-Agent':'movie-intel/1.0 (release-date verification)'})
    try:
        # Shared metadata retry allowance, not an additional request budget.
        reserve('tmdb')
        with urlopen(request,timeout=5) as response:
            raw=response.read(1_048_577)
            if len(raw)>1_048_576:return set()
        return release_years(json.loads(raw),qid,imdb,tmdb_id)
    except HTTPError as exc:
        if exc.code==429:
            try:delay=max(60,int(exc.headers.get('Retry-After','60')))
            except (ValueError,TypeError):delay=60
            _UNTIL=time.monotonic()+delay;cooldown('tmdb',delay)
        return set()
    except (URLError,TimeoutError,OSError,ValueError,KeyError,TypeError):return set()


def candidate(details,title,year,facts,get=tmdb._get,dates=wikidata_years):
    ident=details.get('id');ext=details.get('external_ids') or {};imdb=ext.get('imdb_id')
    if type(ident)!=int or not tmdb.valid_tmdb_id(ident) or not tmdb.valid_imdb_id(imdb):return None
    names=[details.get('title'),details.get('original_title')]
    names += [x.get('title') for x in details.get('alternative_titles',{}).get('titles',[])]
    names += [x.get('data',{}).get('title') for x in details.get('translations',{}).get('translations',[])]
    if not tmdb._identity_title(title) or tmdb._identity_title(title) not in {tmdb._identity_title(x) for x in names if isinstance(x,str)}:return None
    if type(details.get('runtime'))!=int or details['runtime']!=facts['runtime']:return None
    language=details.get('original_language')
    languages={x.get('english_name','').casefold() for x in details.get('spoken_languages',[]) if x.get('iso_639_1')==language}
    if facts['language'] not in languages:return None
    mapping=get('/find/'+imdb,{'external_source':'imdb_id','language':'en-US'})
    if not isinstance(mapping,dict) or any(mapping.get(x) for x in ('tv_results','tv_episode_results','tv_season_results','person_results')):raise ValueError('mapping_inconclusive')
    movies=mapping.get('movie_results')
    if not isinstance(movies,list) or len(movies)!=1 or movies[0].get('id')!=ident:raise ValueError('mapping_conflict')
    years={tmdb._year(details.get('release_date'))}
    years.update(tmdb._year(d.get('release_date')) for c in details.get('release_dates',{}).get('results',[]) for d in c.get('release_dates',[]))
    basis='tmdb_release_dates'
    if str(year) not in years:
        if str(year) not in dates(ext.get('wikidata_id'),imdb,ident):raise ValueError('year_inconclusive')
        basis='wikidata_crosslinked_release_dates'
    result=tmdb._compact(details)
    result.update(identity_status='verified_tmdb',identity_reason='external_id_verified',identity_source='torrent_evidence',
                  identity_title_basis='documented_alias_and_nfo',identity_year_basis=basis,matched_release_year=str(year))
    return result


def resolve(release,indexer,listing,get=None,dates=None):
    if os.environ.get(FLAG)!='1':return None
    if (not listing or listing.get('reason')!='listing_id_missing' or listing.get('imdb_id')
            or str(indexer.get('identifier') or indexer.get('name') or '').casefold()!='torrentleech'
            or release.get('meta_imdb') not in (None,'') or release.get('meta_tmdb') not in (None,'')):return None
    from tracker_metadata import valid_listing_url
    if not valid_listing_url(release.get('info_url')) or not isinstance(release.get('name'),str):return None
    if type(release.get('year'))!=int or not 1888<=release['year']<=2100:return None
    try:facts=nfo_facts(listing['torrent_evidence'])
    except (ValueError,KeyError,TypeError):return None
    if not facts:return None
    source=digest([release.get('info_url'),release.get('name'),release.get('title'),release['year'],listing['torrent_evidence']])
    if not _LOCK.acquire(blocking=False):return None
    try:
        now=time.monotonic();cached=_CACHE.get(source)
        if cached and cached[0]>now:return dict(cached[1]) if cached[1] else None
        provider=get or tmdb._get;dates=dates or wikidata_years
        def get(path,params):
            if time.monotonic()-now>20:raise ValueError('evidence_deadline')
            return provider(path,params)
        result=None
        try:
            search=get('/search/movie',{'query':release['title'],'include_adult':'false','language':'en-US','page':1})
            if not isinstance(search,dict) or search.get('page')!=1 or search.get('total_pages')!=1:raise ValueError('incomplete_search')
            rows=search.get('results')
            if not isinstance(rows,list) or not 1<=len(rows)<=3 or search.get('total_results')!=len(rows):raise ValueError('search_capacity')
            ids=[x.get('id') for x in rows]
            if any(type(x)!=int or not tmdb.valid_tmdb_id(x) for x in ids) or len(set(ids))!=len(ids):raise ValueError('invalid_search')
            matches=[]
            for ident in ids:
                details=get('/movie/'+str(ident),{'append_to_response':'external_ids,alternative_titles,translations,release_dates','language':'en-US'})
                if not isinstance(details,dict) or details.get('id')!=ident:raise ValueError('incomplete_details')
                match=candidate(details,release['title'],release['year'],facts,get,dates)
                if match:matches.append(match)
            if len(matches)==1:result=dict(matches[0],identity_evidence={'source':source})
        except (ValueError,KeyError,TypeError,AttributeError):pass
        _CACHE[source]=(now+(900 if result else 60),result)
        _CACHE.move_to_end(source)
        while len(_CACHE)>256:_CACHE.popitem(last=False)
        return dict(result) if result else None
    finally:_LOCK.release()
