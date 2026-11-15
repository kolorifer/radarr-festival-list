"""Immutable host evidence, rederived at the provider boundary.

Only capture() acquires sources. Loading never fetches, refreshes or repairs them.
Original bytes (including the IMDb crosswalk) and observation clocks are retained.
"""
import hashlib,json,os,time
from pathlib import Path
from ai_movie_investigator.contracts import require,encoded,decode,digest,hash_id
from ai_movie_investigator.private_files import private_chain,read_private
from ai_movie_investigator.snapshot_authorization import _write_once

RAW_FIELDS=('source_original','catalogue_original','find_original','snapshot','source','catalogue','local_raw')

def capture(queue,config,preparation):
    from automation.seedbox_host_io import database,selected_snapshot,acquire
    with queue.locked() as (rows,_):
        claims=[r for r in rows if r['type']=='seedbox_preparation_claimed_v1' and digest(r)==preparation]
        require(len(claims)==1,'host_preparation_missing');claim=claims[0]
        require(not any(r.get('preparation')==preparation and r['type'] in ('seedbox_evidence_retained_v1','seedbox_provider_started_v1','seedbox_preparation_superseded_v1') for r in rows),'host_evidence_consumed')
    with database(config['collector_database']) as c:
        raw,metadata,coverage=selected_snapshot(c,claim['case_id'],time.time())
    bundle=acquire(config,claim,raw,metadata)
    bundle['coverage']['global_collector']=coverage
    return _retain(queue,preparation,bundle)


def _retain(queue,preparation,bundle):
    hash_id(preparation)
    path=queue.path/('evidence-'+preparation)
    # Existing/interrupted outputs are not overwritten or silently reacquired.
    with private_chain(queue.path) as parent:
        os.mkdir(path.name,0o700,dir_fd=parent)
    with private_chain(path) as fd:
        pins={}
        for key in RAW_FIELDS:
            raw=bundle[key];require(type(raw) is bytes and len(raw)<=1048576,'host_evidence_size')
            _write_once(fd,key+'.bin',raw);pins[key]=dict(sha256=hashlib.sha256(raw).hexdigest(),size=len(raw))
        manifest=dict(kind='seedbox_evidence_bundle_v1',preparation=preparation,files=pins,
            attestation=bundle['attestation'],target_pin=bundle['target_pin'],coverage=bundle['coverage'])
        _write_once(fd,'manifest.json',encoded(manifest))
    with queue.locked() as (rows,append):
        require(not any(r.get('preparation')==preparation and r['type'] in ('seedbox_evidence_retained_v1','seedbox_provider_started_v1','seedbox_preparation_superseded_v1') for r in rows),'host_evidence_consumed')
        append(dict(type='seedbox_evidence_retained_v1',preparation=preparation,manifest_sha256=digest(manifest),at=time.time()))
    return load(queue,preparation)


def load(queue,preparation,*,now=None):
    from automation.seedbox_source_evidence import listing_facts,catalogue_facts
    from ai_movie_investigator.snapshot_private_report import validate_local_context
    from ai_movie_investigator.snapshot_review import projection
    hash_id(preparation);now=time.time() if now is None else now
    with queue.locked() as (rows,_):
        records=[r for r in rows if r['type']=='seedbox_evidence_retained_v1' and r['preparation']==preparation]
        claims=[r for r in rows if r['type']=='seedbox_preparation_claimed_v1' and digest(r)==preparation]
        require(len(records)==len(claims)==1,'host_evidence_missing');record=records[0];claim=claims[0]
    path=queue.path/('evidence-'+preparation)
    with private_chain(path):
        manifest=decode(read_private(path/'manifest.json',65536),65536)
        require(digest(manifest)==record['manifest_sha256'] and manifest['preparation']==preparation and set(manifest['files'])==set(RAW_FIELDS),'host_evidence_changed')
        raw={}
        for key,pin in manifest['files'].items():
            value=read_private(path/(key+'.bin'),1048576)
            require(len(value)==pin['size'] and hashlib.sha256(value).hexdigest()==pin['sha256'],'host_evidence_changed');raw[key]=value
        local=validate_local_context(raw['local_raw']);source=decode(raw['source'],65536);cat=decode(raw['catalogue'],65536)
        derived=listing_facts(raw['source_original'],release_name=local['release_name'],case_id=claim['case_id'],version=claim['version'],observed_at=source['observed_at'],expires_at=source['expires_at'])
        require(derived==source,'host_source_derivation_changed')
        found=json.loads(raw['find_original']);movies=found.get('movie_results')
        require(type(movies) is list and len(movies)==1 and type(movies[0].get('id')) is int and movies[0]['id']==cat['tmdb'],'host_crosswalk_changed')
        derived_cat=catalogue_facts(raw['catalogue_original'],expected_tmdb=cat['tmdb'],expected_imdb=source['imdb'],observed_at=cat['observed_at'],expires_at=cat['expires_at'])
        require(derived_cat==cat,'host_catalogue_derivation_changed')
        att=manifest['attestation']
        require(att['source_original_sha256']==manifest['files']['source_original']['sha256'] and att['catalogue_original_sha256']==manifest['files']['catalogue_original']['sha256'],'host_originals_changed')
        selected=projection(raw['snapshot'],manifest['files']['snapshot']['sha256'],claim['case_id'],claim['version'],raw['source'],raw['catalogue'],att,now=now)
        require(manifest['target_pin']['case_id']==claim['case_id'],'host_target_changed')
        return dict(snapshot_raw=raw['snapshot'],projection=selected,local_raw=raw['local_raw'],target_pin=manifest['target_pin'],evidence_sha256=record['manifest_sha256'],manifest=manifest)


def verify_current(queue,preparation,evidence,configuration_sha256):
    """Last read-only collector check; no claim of freezing its future updates."""
    from automation.seedbox_host_io import database,selected_snapshot
    from ai_movie_investigator.snapshot_review import select
    config=decode(read_private(queue.path/'configuration.json',131072),131072)
    require(digest(config)==configuration_sha256,'host_configuration_changed')
    p=evidence['projection'];old=decode(evidence['snapshot_raw'],1048576)['cases'][0]
    with database(config['collector_database']) as c:
        raw,_,_=selected_snapshot(c,p['case_id'],time.time())
        case,_,_=select(raw,hashlib.sha256(raw).hexdigest(),p['case_id'],p['version'],now=time.time())
        require(case['observed_at']==old['observed_at'],'host_current_occurrence_changed')
    return time.time()


def persist_report(queue,preparation):
    from ai_movie_investigator.snapshot_private_report import render
    with queue.locked() as (rows,_):
        matches=[r for r in rows if r['type']=='seedbox_assessment_pending_review_v1' and r['preparation']==preparation]
        require(len(matches)==1,'host_report_missing');record=matches[0]
    # Historical rendering only. This grants no fresh source/provider/send right.
    evidence=load(queue,preparation,now=record['at']);report=record['report']
    html=render(report,digest(report),evidence['projection'],evidence['local_raw'],report['local_context_sha256']).encode()
    require(hashlib.sha256(html).hexdigest()==record['html_sha256'],'host_report_changed')
    path=queue.path/('report-'+preparation+'.html')
    with private_chain(queue.path) as fd:
        try:_write_once(fd,path.name,html)
        except FileExistsError:require(read_private(path,1048576)==html,'host_report_changed')
    return path
