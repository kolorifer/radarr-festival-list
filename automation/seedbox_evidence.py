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
        if bundle.get('derivation_revision')==2:manifest['derivation_revision']=2
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
        revision=manifest.get('derivation_revision',1);require(revision in (1,2),'host_listing_revision')
        derived=listing_facts(raw['source_original'],release_name=local['release_name'],case_id=claim['case_id'],version=claim['version'],observed_at=source['observed_at'],expires_at=source['expires_at'],revision=revision)
        require(derived==source,'host_source_derivation_changed')
        found=json.loads(raw['find_original']);movies=found.get('movie_results')
        require(type(movies) is list and len(movies)==1 and type(movies[0].get('id')) is int and movies[0]['id']==cat['tmdb'],'host_crosswalk_changed')
        derived_cat=catalogue_facts(raw['catalogue_original'],expected_tmdb=cat['tmdb'],expected_imdb=source['imdb'],observed_at=cat['observed_at'],expires_at=cat['expires_at'])
        require(derived_cat==cat,'host_catalogue_derivation_changed')
        att=manifest['attestation']
        require(att['source_original_sha256']==manifest['files']['source_original']['sha256'] and att['catalogue_original_sha256']==manifest['files']['catalogue_original']['sha256'],'host_originals_changed')
        selected=projection(raw['snapshot'],manifest['files']['snapshot']['sha256'],claim['case_id'],claim['version'],raw['source'],raw['catalogue'],att,now=now)
        if revision==2:selected['host_reporting_revision']=2
        if 'correction_of' in claim:
            proof=claim['correction_proposal']
            require(source['observed_at']>proof['parent_source_observed_at'] and cat['observed_at']>proof['parent_catalogue_observed_at'],'host_correction_observation_not_new')
            require(revision==2 and digest(proof)==claim['correction_proposal_sha256'] and digest({k:v for k,v in source.items() if k not in ('observed_at','expires_at')})==proof['corrected_semantic_sha256'] and digest({k:v for k,v in cat.items() if k not in ('observed_at','expires_at')})==proof['catalogue_semantic_sha256'] and digest(manifest['target_pin'])==proof['target_sha256'] and digest(local['tracker_url'])==proof['source_url_sha256'],'host_correction_evidence_changed')
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


def correction_proposal(queue,preparation):
    """Offline material-change proof only; never a retry or fresh observation.

    Old receipts are verified against old derivation before calculating v2 facts.
    A distinct reviewed execution binding is still required for any reassessment.
    """
    from automation.seedbox_source_evidence import listing_facts
    from automation.seedbox_automated_review import build
    with queue.locked() as (rows,_):
        reports=[r for r in rows if r['type']=='seedbox_assessment_pending_review_v1' and r['preparation']==preparation]
        reviews=[r for r in rows if r['type']=='seedbox_automated_review_completed_v1' and r['preparation']==preparation]
        attempts=[r for r in rows if r['type']=='seedbox_provider_started_v1' and r['preparation']==preparation]
        require(len(reports)==len(reviews)==1 and len(attempts)==2,'host_correction_completed_pair_required')
        require(not any(r.get('preparation')==preparation and r['type'] in ('seedbox_assessment_uncertain_or_refused_v1','seedbox_review_uncertain_or_refused_v1') for r in rows),'host_correction_uncertain_parent')
        claims=[r for r in rows if r['type']=='seedbox_preparation_claimed_v1' and digest(r)==preparation]
        require(len(claims)==1 and 'correction_of' not in claims[0] and claims[0]['case_id'] not in rows[0]['prior_consumed_cases'],'host_correction_parent')
        case_preps={digest(r) for r in rows if r['type']=='seedbox_preparation_claimed_v1' and r['case_id']==claims[0]['case_id']}
        require(not any(r['type']=='seedbox_sender_started_v1' and r['preparation'] in case_preps for r in rows),'host_correction_send_exists')
    # assessment() retains exact old request/card semantics and verifies report.
    # Use the retained observation clock for historical derivation, not freshness.
    evidence=load(queue,preparation,now=reports[0]['at']);manifest=evidence['manifest']
    require(manifest.get('derivation_revision',1)==1,'host_correction_old_revision')
    path=queue.path/('evidence-'+preparation)
    raw=read_private(path/'source_original.bin',1048576);old=decode(read_private(path/'source.bin',1048576))
    require(hashlib.sha256(raw).hexdigest()==manifest['files']['source_original']['sha256'] and old==evidence['projection']['listing'],'host_correction_original_changed')
    local=decode(evidence['local_raw']);new=listing_facts(raw,release_name=local['release_name'],case_id=old['case_id'],version=old['version'],observed_at=old['observed_at'],expires_at=old['expires_at'],revision=2)
    changed=[k for k in ('title','year','cast','directors','imdb','description_runtime_minutes','nfo_runtime_milliseconds') if old[k]!=new[k]]
    require(changed,'host_correction_no_material_change')
    from ai_movie_investigator.snapshot_review import build_film_prose,validate_film_prose
    from ai_movie_investigator.snapshot_private_report import render
    report=reports[0]['report'];projection=evidence['projection'];built=build_film_prose(projection)
    require(report['request_sha256']==digest(built['request']) and report['receipt_hash']==digest(report['receipt']) and report['retained_reply_hash']==digest(reports[0]['answer']) and report['projection_sha256']==digest(projection),'host_correction_old_report_changed')
    require(validate_film_prose(projection,built,reports[0]['answer'],now=reports[0]['at'])==report['result'],'host_correction_old_report_changed')
    html=render(report,digest(report),projection,evidence['local_raw'],report['local_context_sha256']).encode()
    require(hashlib.sha256(html).hexdigest()==reports[0]['html_sha256'],'host_correction_old_report_changed')
    from automation.seedbox_automated_review import proposal
    card=proposal(report,projection,evidence['local_raw'],evidence['target_pin'],reports[0]['html_sha256']);request,bindings=build(report,projection,card)
    review=reviews[0]
    require(review['answer']['verdict']=='reject' and review['review_kind']=='separate_automated_generation' and review['personal_main_review'] is False,'host_correction_rejected_review_required')
    from ai_movie_investigator.responses_protocol import schema_value
    schema_value(review['answer'],request['text']['format']['schema'])
    require(review['card']==card and review['report_sha256']==digest(report) and review['receipt_sha256']==digest(review['receipt']) and review['receipt']['request_sha256']==digest(request) and all(review['answer'][k]==v for k,v in bindings.items()),'host_correction_old_review_changed')
    for stage,entry,request_hash in (('assessment',reports[0],report['request_sha256']),('review',review,digest(request))):
        selected=[a for a in attempts if a['stage']==stage]
        require(len(selected)==1 and digest(selected[0])==entry['attempt_sha256'] and selected[0]['request_sha256']==request_hash,'host_correction_old_attempt_changed')
        expected_evidence=evidence['evidence_sha256'] if stage=='assessment' else bindings['evidence_sha256']
        require(selected[0]['evidence_sha256']==expected_evidence and selected[0]['review_of']==(None if stage=='assessment' else digest(report)) and selected[0]['reserved_usd']==(report['receipt'] if stage=='assessment' else review['receipt'])['reserved_usd'],'host_correction_old_attempt_changed')
    return dict(kind='seedbox_material_extraction_correction_v2',preparation=preparation,old_manifest_sha256=digest(manifest),original_sha256=manifest['files']['source_original']['sha256'],old_source_sha256=digest(old),corrected_source_sha256=digest(new),changed_fields=changed,corrected_source=new,parent_source_observed_at=old['observed_at'],parent_catalogue_observed_at=projection['catalogue']['observed_at'],corrected_semantic_sha256=digest({k:v for k,v in new.items() if k not in ('observed_at','expires_at')}),catalogue_semantic_sha256=digest({k:v for k,v in projection['catalogue'].items() if k not in ('observed_at','expires_at')}),source_url_sha256=digest(local['tracker_url']),target_sha256=digest(evidence['target_pin']),old_report_sha256=digest(report),old_review_sha256=digest(review),consumed_attempts=[digest(a) for a in attempts],observation_clock_unchanged=True,historical_only=True,provider_execution_authorized=False,reassessment='requires_distinct_reviewed_binding_and_freshness_policy_no_replay')


def record_correction(queue,preparation):
    proposal=correction_proposal(queue,preparation)
    with queue.locked() as (rows,append):
        old=[r for r in rows if r['type']=='seedbox_extraction_correction_proposed_v2' and r['preparation']==preparation]
        if old:
            require(len(old)==1 and old[0]['proposal']==proposal,'host_correction_conflict');return old[0]
        record=dict(type='seedbox_extraction_correction_proposed_v2',preparation=preparation,proposal=proposal,proposal_sha256=digest(proposal),at=time.time())
        append(record);return record


def authorize_correction(queue,preparation,proposal_sha256):
    """Explicit one-case operator command; atomically append a distinct claim.

    Fresh capture/currentness and a distinct request remain mandatory. The old
    preparation cannot be retried; this command never performs external I/O.
    """
    proposal=correction_proposal(queue,preparation)
    require(digest(proposal)==proposal_sha256,'host_correction_proposal_pin')
    with queue.locked() as (rows,append):
        old=[r for r in rows if r['type']=='seedbox_preparation_claimed_v1' and digest(r)==preparation]
        require(len(old)==1,'host_correction_parent')
        require(not any(r['type']=='seedbox_preparation_claimed_v1' and r.get('correction_of')==preparation for r in rows),'host_correction_consumed')
        require(not any(r['type']=='seedbox_sender_started_v1' and r['preparation']==preparation for r in rows),'host_correction_send_exists')
        claim=dict(old[0],correction_of=preparation,correction_proposal=proposal,correction_proposal_sha256=proposal_sha256,at=time.time())
        append(claim)
        return dict(preparation=digest(claim),correction_of=preparation,proposal_sha256=proposal_sha256,fresh_capture_required=True)
