"""Passive eligibility projection in the collector's existing private SQLite inbox.

No providers, research execution, action imports or schema changes to v1 tables.
Projection and intake commit together. Original events and seed history stay intact.
"""
import json
from identity_triage_store import digest

RESEARCH = {'tmdb_mapping_missing', 'no_exact_match', 'listing_id_missing'}
REVIEW = {'retry_exhausted','authentication_unavailable','login_required','disabled','resolver_unconfigured','listing_auth_failure','listing_not_found','listing_redirect','metadata_auth_failure','metadata_record_missing','metadata_redirect','title_conflict', 'year_conflict', 'ambiguous_exact_matches', 'ambiguous_id_mapping',
          'identity_conflict', 'local_identity_conflict', 'external_id_conflict', 'listing_id_conflict', 'listing_mismatch'}
RETRY = {'listing_temporary_http','metadata_rate_limited','metadata_api_unavailable','metadata_lookup_busy','resolver_error',
         'details_unavailable','lookup_busy','rate_limited',
         'listing_http_error','listing_unavailable','unavailable'}
INVALID = {'movie_category_type_conflict','invalid_metadata','invalid_external_id','invalid_movie_identity','non_movie_identity',
           'listing_reference_invalid','listing_id_invalid','listing_content_invalid','listing_limit_exceeded'}


def route(outcome):
    status=outcome['status'];reason=outcome['reason']
    if outcome['category'] in {'quality','existing','not_upgrade'} or status=='skipped_routine':return 'routine'
    if status in {'verified_tmdb','legacy_resolved'}:
        return 'verified' if reason in {'external_id_verified','resolved','verified'} else 'quarantine'
    if reason in RETRY:return 'retry_later'
    if reason in INVALID:return 'quarantine'
    if reason in REVIEW:return 'review_only'
    if reason in RESEARCH and status in {'unresolved','imdb_associated'}:return 'eligible'
    return 'unassessed'


def initialize(c):
    for sql in (
        'CREATE TABLE IF NOT EXISTS selection_schema (version INTEGER PRIMARY KEY CHECK(version=1))',
        'INSERT OR IGNORE INTO selection_schema VALUES (1)',
        'CREATE TABLE IF NOT EXISTS selection_events (id TEXT PRIMARY KEY, release TEXT NOT NULL, evidence TEXT NOT NULL REFERENCES evidence(id), observed REAL NOT NULL, received REAL NOT NULL, outcome TEXT NOT NULL)',
        'CREATE INDEX IF NOT EXISTS selection_release ON selection_events(release,observed)',
        'CREATE TABLE IF NOT EXISTS selection_history (version TEXT PRIMARY KEY, case_key TEXT NOT NULL, evidence TEXT NOT NULL REFERENCES evidence(id), route TEXT NOT NULL, correlation TEXT NOT NULL, material TEXT NOT NULL)',
        'CREATE TABLE IF NOT EXISTS selection_current (case_key TEXT PRIMARY KEY, version TEXT NOT NULL REFERENCES selection_history(version), release TEXT UNIQUE NOT NULL, observed REAL NOT NULL)',
        'CREATE TABLE IF NOT EXISTS selection_counters (name TEXT PRIMARY KEY, value INTEGER NOT NULL)',
    ):c.execute(sql)
    if c.execute('select version from selection_schema').fetchall()!=[(1,)]:raise ValueError('selection_schema')


def count(c,name):
    c.execute('insert into selection_counters values (?,1) on conflict(name) do update set value=value+1',(name,))


def ingest(c,record,channel,evidence,now):
    if not evidence:return
    release=record['release']
    if channel=='outcome' or (channel=='selected' and 'outcome' in record):
        outcome=record['outcome'];observed=record['time']
        if observed is None or observed>now+300:
            outcome={'status':'unresolved','category':'other','reason':'invalid_metadata'}
            observed=now
        key=digest([release,evidence,observed,outcome])
        c.execute('insert or ignore into selection_events values (?,?,?,?,?,?)',
                  (key,release,evidence,observed,now,json.dumps(outcome,sort_keys=True)))
    project(c,release)


def project(c,release):
    events=c.execute('select s.evidence,s.observed,s.outcome,e.metadata from selection_events s join evidence e on e.id=s.evidence where s.release=? order by s.observed desc,s.id limit 1',(release,)).fetchall()
    if not events:return
    evidence,observed,encoded,metadata=events[0];outcome=json.loads(encoded);meta=json.loads(metadata)
    decision=route(outcome)
    if outcome['reason']=='tmdb_mapping_missing' and not (outcome.get('asserted_imdb') or meta['imdb']):
        decision='quarantine'
    observations=c.execute('select distinct e.metadata from evidence e join deliveries d on d.evidence=e.id where e.release=? and d.channel in ("release_new","retained","selected")',(release,)).fetchall()
    if meta['release_key_basis']!='external_id':correlation='uncertain_name_only'
    elif not observations:correlation='outcome_only'
    else:
        exact=[]
        for (raw,) in observations:
            other=json.loads(raw)
            exact.append(all(other[k]==meta[k] for k in ('source','name','title_key','year')) and
                         all(not other[k] or not meta[k] or other[k]==meta[k] for k in ('imdb','tmdb')))
        correlation='strong_source_id' if all(exact) else 'context_conflict'
    if c.execute('select 1 from selection_events where release=? and observed=? and (outcome!=? or evidence!=?) limit 1', (release,observed,encoded,evidence)).fetchone():
        decision='quarantine';correlation='simultaneous_conflict'
    if any(meta[k] and outcome.get('asserted_'+k) and meta[k]!=outcome['asserted_'+k] for k in ('imdb','tmdb')):
        decision='quarantine';correlation='identifier_conflict'
    seed=c.execute('select e.metadata from seeds s join evidence e on e.id=s.evidence where e.release=?',(release,)).fetchone()
    # Never overwrite/reimport the four richer, previously reviewed pilot inputs.
    if seed:
        original=json.loads(seed[0])
        changed=any(original.get(k)!=meta.get(k) for k in ('title_key','year','imdb','tmdb'))
        decision='review_only' if changed else 'existing_seed'
    status=decision
    if decision in ('eligible','review_only') and correlation!='strong_source_id':status='unmatched'
    if correlation in ('context_conflict','simultaneous_conflict','identifier_conflict') and decision!='existing_seed':status='quarantine'
    key='outcome-'+release
    material={'metadata':meta,'outcome':outcome,'route':status,'underlying_route':decision,'correlation':correlation}
    version=digest([key,material])
    previous=c.execute('select version from selection_current where case_key=?',(key,)).fetchone()
    inserted=c.execute('insert or ignore into selection_history values (?,?,?,?,?,?)',(version,key,evidence,status,correlation,json.dumps(material,sort_keys=True)))
    c.execute('insert into selection_current values (?,?,?,?) on conflict(case_key) do update set version=excluded.version,observed=excluded.observed',(key,version,release,observed))
    if inserted.rowcount and status=='eligible':count(c,'new_eligible_versions')
    if not previous or previous[0]!=version:
        count(c,'changed_versions')
    else:count(c,'duplicate_projection')


def metrics(c):
    states=dict(c.execute('select h.route,count(*) from selection_current x join selection_history h on h.version=x.version group by h.route'))
    correlations=dict(c.execute('select h.correlation,count(*) from selection_current x join selection_history h on h.version=x.version group by h.correlation'))
    observed=c.execute('select count(distinct e.release) from evidence e join deliveries d on d.evidence=e.id where d.channel in ("release_new","retained","selected")').fetchone()[0]
    unassessed=c.execute('select count(distinct e.release) from evidence e join deliveries d on d.evidence=e.id where d.channel in ("release_new","retained","selected") and not exists(select 1 from selection_events s where s.release=e.release)').fetchone()[0]
    legacy=c.execute('select count(*) from outcomes o where not exists(select 1 from selection_events s where s.evidence=o.evidence)').fetchone()[0]
    return {'source_releases_observed':observed,'source_releases_without_outcome':unassessed,
            'outcome_events':c.execute('select count(*) from selection_events').fetchone()[0],
            'assessed_release_cases':sum(states.values()),'routes':states,'correlation':correlations,
            'existing_unresolved_seeds':c.execute('select count(*) from seeds').fetchone()[0],
            'legacy_outcome_rows_without_chronology':legacy,
            'counters':dict(c.execute('select name,value from selection_counters')),
            'researching':0,'automatic_research_enabled':False,'coverage':'incomplete'}


def export(c,limit=100):
    """Narrow private export for future approved research. Never touches its closed ledger."""
    if type(limit)!=int or not 1<=limit<=100:raise ValueError('export_limit')
    result=[]
    for key,version,observed,raw in c.execute('select x.case_key,x.version,x.observed,h.material from selection_current x join selection_history h on h.version=x.version where h.route="eligible" order by x.observed,x.case_key limit ?',(limit,)):
        r=json.loads(raw);m=r['metadata'];o=r['outcome']
        result.append({'case_id':key,'seed':False,'eligibility':'explicit_unresolved',
                       'facts':{'title':m['title'],'year':m['year'],'imdb':o.get('asserted_imdb') or m['imdb'],
                                'tmdb':o.get('asserted_tmdb') or m['tmdb'],'variants':[m['title']],
                                'contradictions':['missing_crosswalk'] if o['reason']=='tmdb_mapping_missing' else ['unknown_identity'],
                                'director':None,'runtime':None},
                       'provenance':[{'source':'stage1_outcome','digest':version,'observed_at':observed}],
                       'historical_candidates':[],'observed_at':observed})
    return result


def snapshot(c,now):
    """Complete bounded operator projection; overflow fails closed, never silently drops."""
    counts=metrics(c)
    if counts['assessed_release_cases']>1000 or counts['routes'].get('eligible',0)>100:
        raise ValueError('selection_export_capacity')
    cases=[]
    for key,version,observed,first,raw in c.execute('select x.case_key,x.version,x.observed,(select min(s.observed) from selection_events s where s.release=x.release),h.material from selection_current x join selection_history h on h.version=x.version order by x.case_key'):
        r=json.loads(raw);m=r['metadata']
        cases.append({'case_id':key,'version':version,'observed_at':observed,
                      'title':m['title'],'year':m['year'],'route':r['route'],'first_observed_at':first,
                      'reason':r['outcome']['reason'],'correlation':r['correlation'],
                      'original_type':m.get('original_type','movie'),
                      'source_identity':{'imdb':m['imdb'],'tmdb':m['tmdb'],
                                         'asserted_imdb':r['outcome'].get('asserted_imdb'),
                                         'asserted_tmdb':r['outcome'].get('asserted_tmdb')}})
    return {'version':1,'generated_at':now,'coverage':counts,'cases':cases,'items':export(c,100)}
