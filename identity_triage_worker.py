"""Finite, proposal-only Stage2 runner. No scheduler and no application of proposals."""
import json
import os
from pathlib import Path
import sys
import sqlite3
import time
import unicodedata

from identity_research_provider import Provider, validate_case
from identity_research_store import ResearchStore, Stop
from identity_triage_store import private_path, digest


def normalized(title):
    # Candidate discovery only. Never used by the actor's identity/action gates.
    return ''.join(c for c in unicodedata.normalize('NFKC',title).casefold() if c.isalnum())


def investigate(lease,provider):
    """Evidence-first bounded research; candidates are never accepted identities."""
    item=lease['item'];f=item['facts'];evidence=[];candidates=[];ids=[];found=[];tv=[]
    conflict_review=bool(set(f['contradictions']) & {'title_conflict','year_conflict','identifier_conflict'})
    missing=False
    def get(kind,value):
        result=provider.get(lease,kind,value)
        evidence.append({'method':kind,'query':value,'result':result})
        if result['reason'] not in ('ok','not_found'):
            raise ResearchFailure(result)
        return result.get('data')
    try:
        if f['imdb']:
            found_data=get('find',f['imdb'])
            if found_data:
                found=found_data['movies'];tv=found_data['tv']
                if found_data['tv_other']:tv.append({'type':'tv_episode_or_season'})
            missing=not found
            ids.extend(x['id'] for x in found)
        if f['tmdb']:ids.append(f['tmdb'])
        # Historical IDs remain candidate assertions, never verified crosswalks.
        ids.extend(item['historical_candidates'])
        if not found or conflict_review:
            for title in (f['variants'][:1] if conflict_review else f['variants']):
                movies=get('movie_search',title)
                shows=None if conflict_review else get('tv_search',title)
                if shows:tv.extend(shows['results'])
                if movies:
                    names={normalized(t) for t in f['variants']}
                    matches=[x for x in movies['results'] if normalized(x['title']) in names or (x['original_title'] and normalized(x['original_title']) in names)]
                    if conflict_review:
                        matches.sort(key=lambda x: (not (x.get('date') or '').startswith(str(f['year'])),x['id']))
                    ids.extend(x['id'] for x in matches)
        unique=list(dict.fromkeys(ids))
        for movie_id in unique[:3]:
            data=get('details',movie_id)
            if data:
                conflicts=[];support_gaps=['independent_source_corroboration_missing'] if conflict_review else []
                if f['imdb'] and data['imdb'] and data['imdb']!=f['imdb']:conflicts.append('identifier_conflict')
                if not data['imdb'] and f['imdb']:conflicts.append('missing_crosswalk')
                names={normalized(x) for x in [data['title'],data['original_title']]+data['aliases']+data['translations'] if x}
                if normalized(f['title']) not in names:conflicts.append('title_conflict')
                if not data['date']:support_gaps.append('release_date_missing')
                elif data['date'][:4]!=str(f['year']):conflicts.append('year_conflict')
                if f['director'] and not data['directors']:support_gaps.append('director_missing')
                elif f['director'] and normalized(f['director']) not in {normalized(x) for x in data['directors']}:conflicts.append('director_conflict')
                if f['runtime'] and not data['runtime']:support_gaps.append('runtime_missing')
                elif f['runtime'] and f['runtime']!=data['runtime']:conflicts.append('runtime_conflict')
                candidates.append({'record':data,'contradictions':sorted(set(conflicts)),
                                   'source_contradictions':list(f['contradictions']),'support_gaps':support_gaps,
                                   'confidence':'review_required',
                                   'explanation':'Exact IDs and context are evidence; historical claims and conflicts remain unapproved.'})
        reason='identifier_conflict' if len(found)>1 or any('identifier_conflict' in x['contradictions'] for x in candidates) else 'candidate_review' if candidates else 'tv_only' if tv else 'missing_crosswalk' if missing else 'no_supported_candidate'
        return {'reason':reason,'missing_crosswalk':missing,'candidates':candidates,'competing_movie_ids':unique,
                'detail_limit_reached':len(unique)>3,'tv_observations':tv,'evidence':evidence,
                'original_facts':f,'next_action':'human_review' if candidates else 'await_evidence',
                'runtime_correction':False,'catalog_absence_proven':False,'conflict_investigation':conflict_review}
    except ResearchFailure as exc:
        return {'reason':exc.result['reason'],'retry_after':exc.result.get('retry_after',0),
                'candidates':candidates,'evidence':evidence,'original_facts':f,'runtime_correction':False}
    except Stop as exc:
        return {'reason':str(exc),'candidates':candidates,'evidence':evidence,'original_facts':f,'runtime_correction':False}


class ResearchFailure(Exception):
    def __init__(self,result):self.result=result


def read_config(path):
    p=private_path(path)
    if p.stat().st_size>8192:raise ValueError('config_size')
    config=json.loads(p.read_text())
    if set(config) not in ({'enabled','tmdb_token'},{'enabled','tmdb_token','mode'}) or type(config['enabled'])!=bool or not isinstance(config['tmdb_token'],str):
        raise ValueError('config_schema')
    if config.get('mode','pilot') not in ('pilot','recurring'):raise ValueError('config_mode')
    return config


def read_manifest(path):
    p=private_path(path)
    if p.stat().st_size>65536:raise ValueError('manifest_size')
    items=json.loads(p.read_text())
    if not isinstance(items,list) or not 1<=len(items)<=14:raise ValueError('manifest_count')
    return [validate_case(item) for item in items]


def main():
    os.umask(0o077)
    home=Path.home().resolve();config=home/'.config/movie-identity-research/config.json';state=home/'.local/state/movie-identity-research'
    # Fixed paths and no bypass CLI. Disabled startup performs no TLS or HTTP.
    connection=None;store=None;run=None
    try:
        cfg=read_config(config)
        if not cfg['enabled']:
            print('research disabled',flush=True);return 0
        from identity_research_sandbox import confine,preconnect
        try:connection=preconnect()
        except OSError:
            if cfg.get('mode')!='recurring':raise
        abi=confine(connection,config,state)
        recurring=cfg.get('mode')=='recurring'
        snapshot=None
        if recurring:
            from identity_recurring_store import RecurringStore
            from identity_research_handoff import validate_snapshot
            p=private_path(state/'incoming/snapshot.json')
            if p.stat().st_size>1_048_576:raise ValueError('snapshot_size')
            snapshot=validate_snapshot(json.loads(p.read_text()),time.time())
            store=RecurringStore(state);items=snapshot['items']
        else:
            store=ResearchStore(state);items=read_manifest(state/'input.json')
        for item in items:store.admit(item)
        if recurring:store.reconcile(items)
        if recurring and connection is None:
            from identity_investigation_report import write_report
            write_report(state,snapshot,store)
            print('research provider_unavailable queued_cases_preserved',flush=True)
            return 1
        run=store.start()
        class SwitchProvider(Provider):
            def get(self,lease,kind,value):
                if not read_config(config)['enabled']:raise Stop('run_inactive')
                return super().get(lease,kind,value)
        provider=SwitchProvider(store,run,connection,cfg['tmdb_token'])
        print('research sandbox_verified abi='+str(abi),flush=True)
        while True:
            if recurring:time.sleep(1.05)
            try:lease=store.lease(run)
            except Stop:break
            if not lease:break
            result=investigate(lease,provider)
            store.finish(lease,result)
            if result['reason'] in {'auth_failure','rate_limited','transport_failure','request_budget','provider_cooldown','provider_suspended','run_inactive'}:break
        store.end(run)
        if recurring:
            from identity_investigation_report import write_report
            print('research changed_cases='+str(write_report(state,snapshot,store)),flush=True)
        print('research summary '+json.dumps(store.summary(),sort_keys=True),flush=True)
        return 0
    except (ValueError,OSError,sqlite3.Error,Stop):
        # Never stringify exception objects: paths, payloads and tokens are private.
        print('research stopped_safe',flush=True)
        return 1
    finally:
        if connection:connection.close()


if __name__=='__main__':
    raise SystemExit(main())
