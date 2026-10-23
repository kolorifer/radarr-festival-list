"""Bounded shadow refresh. Writes only shadow state; never imports actor actions."""
import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import time
import tempfile
from unittest.mock import patch
from .shadow import scan
from .fresh import result, MAX_NFO
from .scorer import source_titles, title_similarity


def atomic(path, value):
    fd, name = tempfile.mkstemp(prefix=path.name+'.', dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, 'w') as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write('\n')
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)



class Budget:
    """Reserved before I/O and persisted across hourly invocations/restarts."""
    def __init__(self, path, now=time.time):
        self.path, self.now = path, now
        self.data = json.loads(path.read_text()) if path.exists() else {'days': {}, 'cooldowns': {}, 'suspended': []}
        self.used = 0
        self.last_request = 0
    def reserve(self, provider):
        now = self.now(); day = time.strftime('%Y-%m-%d', time.gmtime(now))
        if provider in self.data['suspended'] or self.data['cooldowns'].get(provider, 0) > now:
            raise RuntimeError('provider_paused')
        if self.used >= 10 or self.data['days'].get(day, 0) >= 40:
            raise RuntimeError('shadow_request_budget')
        self.used += 1; self.data['days'][day] = self.data['days'].get(day, 0) + 1
        atomic(self.path, self.data)
        time.sleep(max(0, 1.05-(time.monotonic()-self.last_request)))
        self.last_request = time.monotonic()
    def cooldown(self, provider, seconds=0, auth=False):
        if auth and provider not in self.data['suspended']:
            self.data['suspended'].append(provider)
        self.data['cooldowns'][provider] = self.now() + max(seconds, 60)
        atomic(self.path, self.data)


def exact_release(home, row):
    from identity_triage_store import digest
    with closing(sqlite3.connect((home/'.local/state/movie-identity-triage/inbox.sqlite3').as_uri()+'?mode=ro', uri=True)) as c:
        saved = c.execute('select x.version,x.release,h.material from selection_current x join selection_history h on h.version=x.version where x.case_key=?', (row['case_id'],)).fetchone()
    # The research version hashes an export envelope; the collector version is
    # the stage1_outcome provenance digest inside that envelope, not the same ID.
    with closing(sqlite3.connect((home/'.local/state/movie-identity-research/recurring-v1.sqlite3').as_uri()+'?mode=ro', uri=True)) as c:
        evidence = c.execute('select material from evidence where version=? and case_id=?',
                             (row['version'], row['case_id'])).fetchone()
    provenance = json.loads(evidence[0]).get('provenance', []) if evidence else []
    versions = [p.get('digest') for p in provenance if p.get('source') == 'stage1_outcome']
    if not saved or versions != [saved[0]]:
        raise RuntimeError('occurrence_changed')
    material = json.loads(saved[2]); meta = material['metadata']
    if material['route'] not in ('eligible', 'review_only'):
        raise RuntimeError('case_no_longer_unresolved')
    if meta['source'] != 'torrentleech' or meta['release_key_basis'] != 'external_id' or material['correlation'] != 'strong_source_id':
        raise RuntimeError('source_binding_missing')
    with closing(sqlite3.connect((home/'.apps/autobrr/autobrr.db').as_uri()+'?mode=ro', uri=True)) as c:
        rows = c.execute('select torrent_id,info_url from release where torrent_name=? and year=?', (meta['name'], meta['year'])).fetchall()
    from tracker_metadata import valid_listing_url
    urls = {url for ident, url in rows if digest(['torrentleech', 'torrent', ['external', str(ident)]]) == saved[1]
            and valid_listing_url(url) and url.rsplit('/', 1)[-1] == str(ident)}
    if len(urls) != 1:
        raise RuntimeError('exact_listing_not_retained')
    return dict(meta, info_url=urls.pop()), material['outcome']


def metadata_get(path, params, budget):
    """Only TMDb GETs, bounded response and no redirects/proxy inheritance."""
    import requests
    if not re.fullmatch(r'/search/movie|/movie/[1-9][0-9]*|/find/tt[0-9]{7,10}', path):
        raise RuntimeError('metadata_route_denied')
    budget.reserve('tmdb')
    with requests.Session() as session:
        session.trust_env = False
        with session.get('https://api.themoviedb.org/3'+path, params=params,
                         headers={'Authorization': 'Bearer '+os.environ['TMDB_API_TOKEN']},
                         timeout=(3, 5), allow_redirects=False, stream=True) as response:
            if response.status_code in (401,403):
                budget.cooldown('tmdb', auth=True)
            if response.status_code == 429:
                retry = response.headers.get('Retry-After', '3600')
                budget.cooldown('tmdb', min(int(retry), 86400) if retry.isdigit() else 3600)
            if response.status_code != 200:
                raise RuntimeError('metadata_http_failure')
            raw = bytearray(); deadline = time.monotonic()+15
            for chunk in response.iter_content(1024):
                raw.extend(chunk)
                if len(raw) > 1048576 or time.monotonic() > deadline:
                    raise RuntimeError('metadata_response_limit')
            return json.loads(raw)


def apply_existing_conflict_guard(scored, release, outcome):
    """A resolved title-only conflict may clear; asserted identity conflicts may not."""
    top=scored['ranked'][0]['candidate_id'] if scored.get('ranked') else None
    id_conflict=(any(value and value!=top for value in (outcome.get('asserted_tmdb'),release.get('tmdb')))
                 or any(value and value!=scored.get('source',{}).get('imdb')
                        for value in (outcome.get('asserted_imdb'),release.get('imdb'))))
    title_resolved=(scored.get('alias_resolution')=='complete_candidate_comparison'
                    and scored.get('decision')=='would_identify'
                    and outcome.get('reason')=='title_conflict')
    if id_conflict or (outcome.get('status')=='needs_review' and not title_resolved):
        scored.update(decision='review',selected_id=None)
        if 'existing_identity_conflict_requires_review' not in scored['reasons']:
            scored['reasons'].append('existing_identity_conflict_requires_review')


def refresh_one(home, row, budget):
    import tracker_metadata as tracker
    from identity_request_guard import guarded
    from bs4 import BeautifulSoup
    from torrent_research_evidence import SECRET
    release, outcome = exact_release(home, row)
    captured = {}; original = tracker.parse_listing
    def parse(body, name):
        listing = original(body, name)
        if listing.get('reason') not in ('listing_id_found', 'listing_id_missing'):
            return listing
        soup = BeautifulSoup(body, 'html.parser')
        nfos = soup.select('#nfo_text')
        raw = nfos[0].get_text(' ', strip=True) if len(nfos) == 1 else ''
        # Preserve the complete NFO up to a hard limit; never pass truncated text
        # to the parser. Strip capabilities before saving any source evidence.
        captured['over_limit'] = len(raw) > MAX_NFO
        captured['nfo'] = SECRET.sub('[redacted]', raw) if len(raw) <= MAX_NFO else ''
        captured['nfo_digest'] = hashlib.sha256(raw.encode()).hexdigest()
        return listing
    with guarded(budget), patch.object(tracker, 'parse_listing', side_effect=parse):
        listing = tracker.lookup_listing(release, {'identifier':'torrentleech'})
    if not captured:
        raise RuntimeError('listing_refresh_failed')
    get = lambda path, params: metadata_get(path, params, budget)
    # Search explicit aliases separately, retaining every rival within the cap.
    # A checked IMDb is a candidate even when title queries are empty.
    mappings = {}; imdb = listing.get('imdb_id'); ids = []
    if imdb:
        mapping = get('/find/'+imdb, {'external_source':'imdb_id','language':'en-US'})
        mappings[imdb] = mapping
        for r in mapping.get('movie_results', []):
            ident=r.get('id')
            if type(ident)!=int or not 0<ident<2**31:
                raise RuntimeError('invalid_mapping')
            if ident not in ids:ids.append(ident)
    direct_ids=set(ids); summaries={}; searches=[]; discovery_complete=True
    for title in source_titles(release['title']):
        response=get('/search/movie', {'query':title, 'include_adult':'false', 'page':1, 'language':'en-US'})
        rows=response.get('results', [])
        if not isinstance(rows,list) or len(rows)>20:
            raise RuntimeError('candidate_capacity')
        page_ids=[r.get('id') for r in rows]
        if any(type(i)!=int or not 0<i<2**31 for i in page_ids) or len(set(page_ids))!=len(page_ids):
            raise RuntimeError('invalid_candidates')
        complete=(response.get('page')==1 and response.get('total_pages') in ((1,) if rows else (0,1))
                  and response.get('total_results')==len(rows))
        discovery_complete &= complete
        searches.append({'query':title,'count':len(rows),'ids':page_ids,'complete':complete})
        for row in rows:
            prior=summaries.get(row['id'])
            if prior and any(prior.get(k)!=row.get(k) for k in ('title','original_title','release_date')):
                discovery_complete=False
            summaries.setdefault(row['id'],row)
        ids.extend(i for i in page_ids if i not in ids)
    if len(ids)>41:raise RuntimeError('candidate_capacity')
    if not ids:raise RuntimeError('candidate_search_empty')
    search={'page':1,'total_pages':1,'total_results':len(ids),
            'results':[summaries.get(i,{'id':i}) for i in ids],
            'alias_search_support':searches,'discovery_complete':discovery_complete}
    def priority(ident):
        row=summaries.get(ident,{})
        names=[n for n in (row.get('title'),row.get('original_title')) if isinstance(n,str) and n]
        similarity=max([title_similarity(alias,name) for alias in source_titles(release['title']) for name in names] or [0])
        year=(row.get('release_date') or '')[:4]==str(release['year'])
        return (ident not in direct_ids,-(30*(2*similarity-1)+(20 if year else -20)),ident)
    detail_ids=sorted(ids,key=priority)[:4]
    details = {}
    for ident in detail_ids:
        d = get('/movie/'+str(ident), {'append_to_response':'external_ids,alternative_titles,translations,release_dates','language':'en-US'})
        if type(d.get('id')) != int or d.get('id') != ident:
            raise RuntimeError('details_id_conflict')
        details[ident] = d
    # Crosswalk the provisional leader only. Rival metadata stays visible even
    # without a reverse lookup; no requests are spent pretending it is approved.
    scored = result(release, listing, captured['nfo'], search, details, mappings,
                    outcome.get('asserted_imdb') or release.get('imdb'))
    top=scored['ranked'][0]['candidate_id'] if scored['ranked'] else None
    top_imdb=(details.get(top,{}).get('external_ids') or {}).get('imdb_id')
    if isinstance(top_imdb,str) and re.fullmatch(r'tt[0-9]{7,10}',top_imdb) and top_imdb not in mappings:
        mappings[top_imdb]=get('/find/'+top_imdb,{'external_source':'imdb_id','language':'en-US'})
        scored=result(release, listing, captured['nfo'], search, details, mappings,
                      outcome.get('asserted_imdb') or release.get('imdb'))
    apply_existing_conflict_guard(scored, release, outcome)
    return dict(**scored, candidate_searches=searches, refreshed_at=time.time(), listing_reason=listing['reason'],
                full_nfo=captured, description=listing.get('torrent_evidence', {}).get('description', {}),
                screenshots=listing.get('torrent_evidence', {}).get('images', []),
                requests=budget.used)


def run():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--actor-code', required=True)
    args=parser.parse_args()
    os.umask(0o077)
    home=Path.home().resolve(); state=home/'.local/state/identity-scoring-shadow'
    pilot=json.loads((state/'pilot.json').read_text()); now=time.time()
    if now>=pilot['until']:
        return
    import sys
    sys.path.append(args.actor_code)
    from deploy.run import read_environment
    env=read_environment(home/'.config/movie-intel/environment')
    for key in ('TMDB_API_TOKEN','MOVIE_INTEL_TL_COOKIE_FILE','MOVIE_INTEL_TL_METADATA_ENABLED'):
        os.environ[key]=env.get(key,'')
    databases=[home/'.local/state/movie-identity-research'/n for n in ('recurring-v1.sqlite3','research.sqlite3')]
    report=scan(databases,pilot['started'],pilot['until'])
    ledger=state/'refresh-state.json'
    saved=json.loads(ledger.read_text()) if ledger.exists() else {}
    # One case per run; unsuccessful evidence can retry next hour, successful
    # refreshes are reused for at most24h. Old pilot baseline is never refetched.
    eligible=[r for r in report['rows'] if r['cohort']=='new_during_pilot']
    due=[r for r in eligible if now-saved.get(r['key'],{}).get('attempted',0)>=
         (86400 if saved.get(r['key'],{}).get('fresh') else 3600)]
    due.sort(key=lambda r:saved.get(r['key'],{}).get('attempted',0))
    if due:
        row=due[0]; entry={'attempted':now}; saved[row['key']]=entry
        atomic(ledger,saved)  # A process kill cannot create an unlimited retry loop.
        budget=Budget(state/'refresh-budget.json')
        try:
            entry['fresh']=refresh_one(home,row,budget)
        except Exception as exc:
            # Only our fixed diagnostic vocabulary may leave this boundary.
            allowed = {'provider_paused','shadow_request_budget','occurrence_changed',
                       'case_no_longer_unresolved','source_binding_missing',
                       'exact_listing_not_retained','metadata_route_denied','metadata_http_failure',
                       'metadata_response_limit','listing_refresh_failed','candidate_capacity_or_empty',
                       'invalid_candidates','invalid_mapping','candidate_capacity','details_id_conflict',
                       'candidate_search_empty','candidate_search_incomplete'}
            entry['error'] = str(exc) if type(exc) is RuntimeError and str(exc) in allowed else 'refresh_incomplete'
        entry['requests']=budget.used
        atomic(ledger,saved)
    for row in eligible:
        entry=saved.get(row['key'],{}); fresh=entry.get('fresh')
        row['refresh_attempted']=entry.get('attempted'); row['refresh_error']=entry.get('error')
        if fresh and now-fresh['refreshed_at']<=86400:
            row['retained_snapshot']={k:row.get(k) for k in ('decision','selected_id','ranked','margin','reasons','evidence_gaps')}
            row.update({k:v for k,v in fresh.items() if k not in ('full_nfo','description','screenshots')})
            row['evidence_file']='refresh-state.json'
        elif entry:
            row['refresh_status']='not_fresh'
    report['would_identify']=sum(r.get('decision')=='would_identify' for r in report['rows'])
    report['arithmetic_pass']=sum(r.get('arithmetic_pass',False) for r in report['rows'])
    report['fresh_results']=sum('refreshed_at' in r for r in report['rows'])
    report['collection_mode']='bounded_fresh_shadow'
    atomic(state/'report.json',report)


def main():
    import fcntl
    os.umask(0o077)
    state=Path.home().resolve()/'.local/state/identity-scoring-shadow'
    with (state/'.refresh.lock').open('a') as lock:
        try:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            return
        run()


if __name__=='__main__':
    main()
