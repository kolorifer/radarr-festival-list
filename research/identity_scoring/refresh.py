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
from .fresh import result, MAX_NFO, build_case, unique_mapping
EVIDENCE_REVISION = 2

from .scorer import source_titles, title_similarity, score_candidate, words


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
    def can_start_refresh(self):
        day=time.strftime('%Y-%m-%d',time.gmtime(self.now()))
        return self.data['days'].get(day,0)<40

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
        # Whitespace is presentation, but identity still requires exact source-ID
        # digest, year, canonical URL and the fresh tracker heading check.
        rows = c.execute('select torrent_id,info_url,torrent_name from release where year=? limit 10001', (meta['year'],)).fetchall()
    if len(rows)>10000:raise RuntimeError('source_reference_capacity')
    from tracker_metadata import valid_listing_url
    urls = {url for ident, url, name in rows if ' '.join(name.split()) == ' '.join(meta['name'].split()) and digest(['torrentleech', 'torrent', ['external', str(ident)]]) == saved[1]
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


def targeted_queries(release, listing, nfo, details, mappings):
    """Scope discovery only after independent source facts support a unique ID.

    This is completeness within explicit title/year queries, never a claim that
    every similarly named movie in the catalog has been fetched.
    """
    if len(details)!=1 or len(source_titles(release['title']))!=1:return None
    ident,d=next(iter(details.items()))
    imdb=listing.get('imdb_id')
    if not imdb or not unique_mapping(mappings.get(imdb),ident):return None
    search={'page':1,'total_pages':1,'total_results':1,'results':[{'id':ident}]}
    case,_=build_case(release,listing,nfo,search,details,mappings)
    scored=score_candidate(case['source'],case['candidates'][0])
    points=scored['contributions']
    if (scored['blocks'] or points['title']!=30 or points['year']!=20
        or points['source_id']!=25 or points['runtime']<=0 or points['language']<=0):return None
    original=d.get('original_title')
    if not isinstance(original,str) or not original.strip():return None
    # Validate bounded title before sending it back as a query.
    words(original)
    year=release['year'];date=d.get('release_date') or ''
    primary=int(date[:4]) if date[:4].isdigit() else year
    queries=[(release['title'],year),(original,year),(original,primary)]
    return list(dict.fromkeys(queries))


def local_identity_recheck(release, scored, actor_root):
    """Read actor catalog only. Missing/ambiguous identities do not clear history."""
    from movie_intel import _norm
    from production_scoring import load_catalog
    wanted={_norm(t) for t in source_titles(release['title'])}
    wanted.add(_norm(scored['ranked'][0]['title']))
    hits=[r for r in load_catalog(actor_root).values()
          if str(r.get('year'))==str(release['year'])
          and any(_norm(t) in wanted for t in [r.get('title'),*r.get('aliases',[])] if t)]
    if not hits:return {'status':'missing'}
    ident=scored['ranked'][0]['candidate_id'];imdb=scored['source'].get('imdb')
    agrees=all(r.get('imdb_id')==imdb and r.get('tmdb_id') in (None,ident) for r in hits)
    return {'status':'agrees' if agrees else 'conflict','matched_records':len(hits),
            'imdb':imdb if agrees else None,'tmdb':ident if agrees else None}


def apply_existing_conflict_guard(scored, release, outcome):
    """A resolved title-only conflict may clear; asserted identity conflicts may not."""
    top=scored['ranked'][0]['candidate_id'] if scored.get('ranked') else None
    id_conflict=(any(value and value!=top for value in (outcome.get('asserted_tmdb'),release.get('tmdb')))
                 or any(value and value!=scored.get('source',{}).get('imdb')
                        for value in (outcome.get('asserted_imdb'),release.get('imdb'))))
    title_resolved=(scored.get('alias_resolution')=='complete_candidate_comparison'
                    and scored.get('decision')=='would_identify'
                    and outcome.get('reason')=='title_conflict')
    recheck=scored.get('local_identity_recheck',{})
    local_resolved=(outcome.get('reason')=='local_identity_conflict'
                    and scored.get('decision')=='would_identify'
                    and scored.get('discovery_scope',{}).get('kind')=='verified_id_targeted'
                    and recheck.get('status')=='agrees' and recheck.get('tmdb')==top
                    and recheck.get('imdb')==scored.get('source',{}).get('imdb'))
    if id_conflict or (outcome.get('status')=='needs_review' and not (title_resolved or local_resolved)):
        scored.update(decision='review',selected_id=None)
        if 'existing_identity_conflict_requires_review' not in scored['reasons']:
            scored['reasons'].append('existing_identity_conflict_requires_review')


def refresh_one(home, row, budget, progress=None, checkpoint=lambda: None):
    import tracker_metadata as tracker
    from identity_request_guard import guarded
    from bs4 import BeautifulSoup
    from torrent_research_evidence import SECRET
    release, outcome = exact_release(home, row)
    # Same research version and exact current occurrence are rechecked above on
    # every resume. Completed GETs survive budget exhaustion, for at most24h.
    progress = progress if progress is not None else {}
    now=time.time()
    if progress.get('revision')!=EVIDENCE_REVISION or now-progress.get('started',0)>=86400:
        progress.clear();progress.update(revision=EVIDENCE_REVISION,started=now,metadata={})
        checkpoint()
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
    if 'listing' in progress:
        listing=progress['listing'];captured=progress['captured']
    else:
        with guarded(budget), patch.object(tracker, 'parse_listing', side_effect=parse):
            listing = tracker.lookup_listing(release, {'identifier':'torrentleech'})
        if not captured:
            reason=listing.get('reason')
            allowed={'listing_mismatch','listing_id_invalid','listing_id_conflict','listing_not_found',
                     'listing_redirect','listing_temporary_http','listing_auth_failure','login_required',
                     'rate_limited','authentication_unavailable','listing_unavailable','listing_content_invalid',
                     'listing_limit_exceeded','listing_http_error','listing_reference_invalid','disabled','lookup_busy'}
            raise RuntimeError(reason if reason in allowed else 'listing_refresh_failed')
        progress.update(listing=listing,captured=captured);checkpoint()
    def get(path, params):
        key=json.dumps([path,params],sort_keys=True)
        if key not in progress['metadata']:
            progress['metadata'][key]=metadata_get(path,params,budget)
            checkpoint()
        return progress['metadata'][key]
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
    direct_ids=set(ids); summaries={}; searches=[]; discovery_complete=True; discovery_integrity=True
    details={}; plan=None
    if len(ids)==1 and len(source_titles(release['title']))==1 and unique_mapping(mappings.get(imdb),ids[0]):
        ident=ids[0]
        d=get('/movie/'+str(ident), {'append_to_response':'external_ids,alternative_titles,translations,release_dates','language':'en-US'})
        if type(d.get('id'))!=int or d['id']!=ident:raise RuntimeError('details_id_conflict')
        details[ident]=d
        plan=targeted_queries(release,listing,captured['nfo'],details,mappings)
    scope={'kind':'verified_id_targeted' if plan else 'broad_title',
           'basis':'checked_unique_imdb_title_year_nfo' if plan else 'title_queries',
           'exhaustive_catalog_search':False}
    for title,year in (plan or [(t,None) for t in source_titles(release['title'])]):
        params={'query':title, 'include_adult':'false', 'page':1, 'language':'en-US'}
        if year is not None:params['year']=year
        response=get('/search/movie',params)
        rows=response.get('results', [])
        if not isinstance(rows,list) or len(rows)>20:
            raise RuntimeError('candidate_capacity')
        page_ids=[r.get('id') for r in rows]
        if any(type(i)!=int or not 0<i<2**31 for i in page_ids) or len(set(page_ids))!=len(page_ids):
            raise RuntimeError('invalid_candidates')
        complete=(response.get('page')==1 and response.get('total_pages') in ((1,) if rows else (0,1))
                  and response.get('total_results')==len(rows))
        discovery_integrity &= (response.get('page')==1 and type(response.get('total_pages'))==int
                                and response['total_pages']>=0 and type(response.get('total_results'))==int
                                and response['total_results']>=len(rows)
                                and (response['total_pages']>1 or response['total_results']==len(rows)))
        discovery_complete &= complete
        searches.append({'query':title,**({'year':year} if year is not None else {}),'count':len(rows),'ids':page_ids,'complete':complete})
        for row in rows:
            prior=summaries.get(row['id'])
            if prior and any(prior.get(k)!=row.get(k) for k in ('title','original_title','release_date')):
                discovery_complete=False; discovery_integrity=False
            summaries.setdefault(row['id'],row)
        ids.extend(i for i in page_ids if i not in ids)
    if len(ids)>(61 if plan else 41):raise RuntimeError('candidate_capacity')
    if not ids:raise RuntimeError('candidate_search_empty')
    search={'page':1,'total_pages':1,'total_results':len(ids),
            'results':[summaries.get(i,{'id':i}) for i in ids],
            'alias_search_support':searches,'discovery_complete':discovery_complete,
            'discovery_scope':scope,'discovery_integrity':discovery_integrity}
    def priority(ident):
        row=summaries.get(ident,{})
        names=[n for n in (row.get('title'),row.get('original_title')) if isinstance(n,str) and n]
        similarity=max([title_similarity(alias,name) for alias in source_titles(release['title']) for name in names] or [0])
        year=(row.get('release_date') or '')[:4]==str(release['year'])
        return (ident not in direct_ids,-(30*(2*similarity-1)+(20 if year else -20)),ident)
    provisional,_=build_case(release,listing,captured['nfo'],search,details,mappings)
    from .scorer import evaluate
    ranks=evaluate(provisional)['ranked']
    upper={r['candidate_id']:r['upper_score'] for r in ranks}
    detail_ids=sorted(ids,key=lambda ident:(ident not in direct_ids,-upper.get(ident,100),priority(ident)))[:4]
    for ident in detail_ids:
        if ident in details:continue
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
    # Packaging is investigated only after ordinary candidate discovery, without
    # changing query scope or suppressing rivals. All requests share Budget.
    from .edition_discovery import proposal, discover
    case,facts=build_case(release,listing,captured['nfo'],search,details,mappings,
                          outcome.get('asserted_imdb') or release.get('imdb'))
    request=proposal(case['source'],case['candidates'])
    edition_status=None
    if request and facts.get('filename_count')==1:
        discovery=discover(request,home/'.local/state/identity-scoring-shadow/edition-cache.json',budget)
        edition_status=discovery['status']
        if discovery.get('record'):
            listing['_discovered_editions']=[discovery['record']]
            scored=result(release,listing,captured['nfo'],search,details,mappings,
                          outcome.get('asserted_imdb') or release.get('imdb'))
    if edition_status:scored['edition_discovery_status']=edition_status
    # Cut claims/runtime comparisons are separate audit proposals. Never clear
    # actor identity conflicts or change scorer weights/selection in this pilot.
    from .cut_discovery import proposal as cut_proposal, discover as discover_cut, comparison
    cut_request=cut_proposal(release,listing,captured['nfo'],case,facts)
    if cut_request:
        cut_finding=discover_cut(cut_request,home/'.local/state/identity-scoring-shadow/cut-cache.json',budget)
        scored['edition_investigation']=comparison(cut_request,cut_finding)
    scored['discovery_scope']=scope
    scored['discovery_integrity']=discovery_integrity
    if outcome.get('reason')=='local_identity_conflict' and scored['decision']=='would_identify' and plan:
        try:scored['local_identity_recheck']=local_identity_recheck(release,scored,home/'radarr-festival-list')
        except Exception:scored['local_identity_recheck']={'status':'unavailable'}
    apply_existing_conflict_guard(scored, release, outcome)
    return dict(**scored, candidate_searches=searches, refreshed_at=progress['started'], completed_at=time.time(), evidence_revision=EVIDENCE_REVISION,
                refresh_complete=(edition_status!='edition_budget_deferred' and
                    scored.get('edition_investigation',{}).get('discovery',{}).get('status')!='cut_budget_deferred'),
                listing_reason=listing['reason'],
                full_nfo=captured, description=listing.get('torrent_evidence', {}).get('description', {}),
                screenshots=listing.get('torrent_evidence', {}).get('images', []),
                requests=budget.used)


# Success is reused for this evidence version throughout the bounded pilot;
# its original timestamp/age remains visible. A new occurrence gets a new key.
def complete_entry(entry):
    fresh=entry.get('fresh') or {}
    return (fresh.get('evidence_revision')==EVIDENCE_REVISION or fresh.get('decision')=='would_identify') and fresh.get('refresh_complete',True)


def due_rows(rows, saved, now):
    due=[]
    for row in rows:
        entry=saved.get(row['key'],{})
        if complete_entry(entry):continue
        # A new parser revision gets one prompt reassessment of retained cases.
        if entry.get('attempt_revision')==EVIDENCE_REVISION and now<entry.get('next_attempt',0):continue
        due.append(row)
    def priority(row):
        entry=saved.get(row['key'],{});fresh=entry.get('fresh') or {}
        # Unseen/unresolved work precedes repeat validation of old successes;
        # within each group use oldest attempt to avoid one failing case starving others.
        return (fresh.get('decision')=='would_identify',entry.get('attempted',0),row['observed'])
    return sorted(due,key=priority)


DIAGNOSTICS={'provider_paused','shadow_request_budget','occurrence_changed',
    'case_no_longer_unresolved','source_binding_missing','source_reference_capacity',
    'exact_listing_not_retained','metadata_route_denied','metadata_http_failure',
    'metadata_response_limit','listing_refresh_failed','candidate_capacity_or_empty',
    'invalid_candidates','invalid_mapping','candidate_capacity','details_id_conflict',
    'candidate_search_empty','candidate_search_incomplete','listing_mismatch','listing_id_invalid',
    'listing_id_conflict','listing_not_found','listing_redirect','listing_temporary_http',
    'listing_auth_failure','login_required','rate_limited','authentication_unavailable',
    'listing_unavailable','listing_content_invalid','listing_limit_exceeded','listing_http_error',
    'listing_reference_invalid','disabled','lookup_busy'}


def attempt_refresh(home,row,saved,ledger,budget,now):
    entry=saved.setdefault(row['key'],{})
    # Reserve the attempt before I/O, preserving previous good evidence on failure.
    entry.update(attempted=now,attempt_revision=EVIDENCE_REVISION,next_attempt=now+3600)
    entry.pop('error',None)
    progress=entry.setdefault('progress',{})
    checkpoint=lambda:atomic(ledger,saved)
    checkpoint()
    try:
        fresh=refresh_one(home,row,budget,progress,checkpoint)
        entry['fresh']=fresh
        if fresh.get('refresh_complete',True):entry.pop('progress',None)
    except Exception as exc:
        error=str(exc) if type(exc) is RuntimeError and str(exc) in DIAGNOSTICS else 'refresh_incomplete'
        entry['error']=error
        # Stable evidence/reference failures need no hourly repeat. Temporary
        # errors back off exponentially to one day; budgets don't count as failures.
        if error in {'shadow_request_budget','provider_paused'}:
            if error=='shadow_request_budget' and not budget.can_start_refresh():
                entry['next_attempt']=(int(now)//86400+1)*86400
        else:
            entry['failures']=entry.get('failures',0)+1
            stable={'exact_listing_not_retained','source_binding_missing','occurrence_changed',
                    'case_no_longer_unresolved','listing_mismatch','listing_id_invalid','listing_id_conflict',
                    'listing_not_found','listing_reference_invalid','source_reference_capacity'}
            entry['next_attempt']=now+(86400 if error in stable else min(86400,3600*2**min(entry['failures'],5)))
    entry['requests']=budget.used
    checkpoint()


def project_entry(row,entry,now):
    row.update(refresh_attempted=entry.get('attempted'),refresh_error=entry.get('error'),
               next_attempt=entry.get('next_attempt'))
    fresh=entry.get('fresh')
    if fresh:
        row['retained_snapshot']={k:row.get(k) for k in ('decision','selected_id','ranked','margin','reasons','evidence_gaps')}
        row.update({k:v for k,v in fresh.items() if k not in ('full_nfo','description','screenshots')})
        row['evidence_file']='refresh-state.json'
        row['evidence_age_seconds']=max(0,now-fresh['refreshed_at'])
        row['refresh_status']='fresh' if row['evidence_age_seconds']<=86400 else 'retained_stale'
        row['current_evidence_revision']=fresh.get('evidence_revision')==EVIDENCE_REVISION
    elif entry:row['refresh_status']='incomplete'


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
    eligible=[]
    for row in report['rows']:
        if row['key'] in pilot.get('carryover_keys',[]):row['cohort']='carried_over'
        if row['cohort'] in ('new_during_pilot','carried_over'):eligible.append(row)
    due=due_rows(eligible,saved,now)
    budget=Budget(state/'refresh-budget.json')
    if due and not budget.can_start_refresh():
        report['refresh_deferred']='daily_budget_exhausted'
        report['deferred_cases']=len(due)
    if due and budget.can_start_refresh():
        attempt_refresh(home,due[0],saved,ledger,budget,now)
    for row in eligible:
        project_entry(row,saved.get(row['key'],{}),now)
    report['carried_over']=sum(r['cohort']=='carried_over' for r in eligible)
    report['completed_current_revision']=sum(complete_entry(saved.get(r['key'],{})) and saved[r['key']]['fresh'].get('evidence_revision')==EVIDENCE_REVISION for r in eligible)
    report['reused_prior_successes']=sum(complete_entry(saved.get(r['key'],{})) and saved[r['key']]['fresh'].get('evidence_revision')!=EVIDENCE_REVISION for r in eligible)
    report['scheduler']='unresolved_first_checkpointed_no_repeat_success'
    report['would_identify']=sum(r.get('decision')=='would_identify' for r in report['rows'])
    report['arithmetic_pass']=sum(r.get('arithmetic_pass',False) for r in report['rows'])
    report['fresh_results']=sum(r.get('refresh_status')=='fresh' for r in report['rows'])
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
