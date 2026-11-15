"""One explicit same-facts delivery observation; never reassess or rewrite clocks."""
import hashlib,math,os,time
from ai_movie_investigator.contracts import require,encoded,decode,digest,hash_id,Refusal
from ai_movie_investigator.private_files import private_chain
from ai_movie_investigator.snapshot_authorization import _write_once
from automation.seedbox_evidence import load,RAW_FIELDS


def _semantic(value):return {k:v for k,v in value.items() if k not in ('observed_at','expires_at')}


def _compare(old,fresh):
    a=old['projection'];b=fresh['projection']
    excluded={'snapshot_sha256','generated_at','listing','catalogue','evidence_expires_at','source_evidence_sha256','catalogue_evidence_sha256'}
    require({k:v for k,v in a.items() if k not in excluded}=={k:v for k,v in b.items() if k not in excluded},'delivery_occurrence_changed')
    require(_semantic(a['listing'])==_semantic(b['listing']) and _semantic(a['catalogue'])==_semantic(b['catalogue']),'delivery_material_facts_changed')
    require(old['local_raw']==fresh['local_raw'] and old['target_pin']==fresh['target_pin'],'delivery_context_target_changed')
    require(b['generated_at']>=a['generated_at'] and all(b[k]['observed_at']>a[k]['observed_at'] for k in ('listing','catalogue')),'delivery_observation_not_new')


def _binding(queue,preparation):
    from automation.seedbox_automated_review import approved_plan
    plan,target=approved_plan(queue,preparation,historical=True)
    with queue.locked() as (rows,_):
        reports=[r for r in rows if r['type']=='seedbox_assessment_pending_review_v1' and r['preparation']==preparation]
        require(len(reports)==1,'delivery_report_missing');record=reports[0]
    old=load(queue,preparation,now=record['at'])
    proof=dict(kind='seedbox_delivery_revalidation_binding_v1',preparation=preparation,plan_sha256=digest(plan),review_sha256=plan['review_sha256'],report_sha256=plan['report_sha256'],old_manifest_sha256=digest(old['manifest']),target_sha256=digest(target),source_url_sha256=digest(decode(old['local_raw'])['tracker_url']),listing_semantic_sha256=digest(_semantic(old['projection']['listing'])),catalogue_semantic_sha256=digest(_semantic(old['projection']['catalogue'])),original_report_at=record['at'],original_evidence_expires_at=old['projection']['evidence_expires_at'],reassessment=False,automatic_retry=False)
    return proof,old


def proposal(queue,preparation):
    hash_id(preparation);proof,_=_binding(queue,preparation)
    with queue.locked() as (rows,_):
        require(not any(r.get('preparation')==preparation and r['type'] in ('seedbox_delivery_revalidation_started_v1','seedbox_sender_started_v1','seedbox_preparation_superseded_v1') for r in rows),'delivery_revalidation_consumed')
    return proof


def revalidate(queue,config,preparation,expected_sha256):
    """Only this explicit command acquires selected sources once. No provider."""
    from automation.seedbox_host_io import database,selected_snapshot,acquire
    from automation.seedbox_circuit import active
    from automation.seedbox_worker import source_paused
    hash_id(expected_sha256);proof=proposal(queue,preparation)
    require(digest(proof)==expected_sha256,'delivery_revalidation_binding')
    _,old=_binding(queue,preparation)
    with queue.locked() as (rows,append):
        require(digest(config)==rows[0]['configuration_sha256'],'host_configuration_changed')
        require(not active(rows) and not source_paused(rows,time.time()),'delivery_circuit_active')
        require(not any(r.get('preparation')==preparation and r['type'] in ('seedbox_delivery_revalidation_started_v1','seedbox_sender_started_v1','seedbox_preparation_superseded_v1') for r in rows),'delivery_revalidation_consumed')
        claims=[r for r in rows if r['type']=='seedbox_preparation_claimed_v1' and digest(r)==preparation]
        require(len(claims)==1,'delivery_preparation_missing');claim=claims[0]
        started=dict(type='seedbox_delivery_revalidation_started_v1',preparation=preparation,proof=proof,proof_sha256=digest(proof),at=time.time());append(started)
    try:
        with database(config['collector_database']) as c:raw,metadata,coverage=selected_snapshot(c,claim['case_id'],time.time())
        bundle=acquire(config,claim,raw,metadata,revalidation=proof)
        bundle['coverage']['global_collector']=coverage
        return _retain(queue,preparation,bundle,started,old)
    except BaseException as error:
        allowed={'delivery_occurrence_changed','delivery_material_facts_changed','delivery_context_target_changed','delivery_observation_not_new','delivery_selected_target_changed','host_correction_source_changed','host_correction_catalogue_changed'}
        from automation.seedbox_host_io import SourceFailure
        reason=error.args[0] if type(error) is Refusal and len(error.args)==1 and error.args[0] in allowed else 'delivery_revalidation_refused'
        if isinstance(error,SourceFailure) and error.reason in ('source_auth_denied','source_configuration_unavailable','source_rate_limited'):reason=error.reason
        cooldown=None
        if reason=='source_rate_limited':
            delay=error.retry_after if error.retry_after is not None else 60
            if type(delay) in (int,float) and math.isfinite(delay) and 0<=delay<10**12:cooldown=time.time()+max(60,delay)
            else:reason='source_configuration_unavailable'
        with queue.locked() as (rows,append):
            append(dict(type='seedbox_delivery_revalidation_failed_v1',preparation=preparation,started_sha256=digest(started),reason=reason,configuration_sha256=rows[0]['configuration_sha256'],retry_not_before=cooldown,automatic_retry=False,at=time.time()))
        raise Refusal(reason) from None


def _retain(queue,preparation,bundle,started,old):
    path=queue.path/('delivery-evidence-'+preparation)
    with private_chain(queue.path) as fd:os.mkdir(path.name,0o700,dir_fd=fd)
    with private_chain(path) as fd:
        pins={}
        for key in RAW_FIELDS:
            raw=bundle[key];require(type(raw) is bytes and len(raw)<=1048576,'host_evidence_size')
            _write_once(fd,key+'.bin',raw);pins[key]=dict(sha256=hashlib.sha256(raw).hexdigest(),size=len(raw))
        manifest=dict(kind='seedbox_evidence_bundle_v1',preparation=preparation,files=pins,attestation=bundle['attestation'],target_pin=bundle['target_pin'],coverage=bundle['coverage'],derivation_revision=2)
        _write_once(fd,'manifest.json',encoded(manifest))
    # Compare even before publishing an eligible retained-evidence record.
    projected=dict(bundle['projection'],host_reporting_revision=2)
    _compare(old,dict(projection=projected,local_raw=bundle['local_raw'],target_pin=bundle['target_pin']))
    with queue.locked() as (rows,append):
        require(started in rows and not any(r.get('preparation')==preparation and r['type'] in ('seedbox_delivery_evidence_retained_v1','seedbox_sender_started_v1') for r in rows),'delivery_revalidation_consumed')
        record=dict(type='seedbox_delivery_evidence_retained_v1',preparation=preparation,manifest_sha256=digest(manifest),started_sha256=digest(started),proof_sha256=started['proof_sha256'],at=time.time())
        append(record)
    # Independently rederive originals from retained bytes before success.
    current(queue,preparation)
    return record


def current(queue,preparation,*,expected_plan=None):
    with queue.locked() as (rows,_):
        records=[r for r in rows if r.get('preparation')==preparation and r['type']=='seedbox_delivery_evidence_retained_v1']
        unresolved=any(r.get('preparation')==preparation and r['type'] in ('seedbox_delivery_revalidation_started_v1','seedbox_delivery_revalidation_failed_v1') for r in rows)
    require(records or not unresolved,'delivery_revalidation_incomplete')
    if not records:return load(queue,preparation)
    with queue.locked() as (rows,_):
        starts=[r for r in rows if r.get('preparation')==preparation and r['type']=='seedbox_delivery_revalidation_started_v1']
        require(len(records)==len(starts)==1 and records[0]['started_sha256']==digest(starts[0]) and records[0]['proof_sha256']==starts[0]['proof_sha256']==digest(starts[0]['proof']),'delivery_revalidation_binding')
        require(not any(r.get('preparation')==preparation and r['type']=='seedbox_delivery_revalidation_failed_v1' for r in rows),'delivery_revalidation_refused')
        selected=starts[0]['proof']
    proof,old=_binding(queue,preparation)
    require(proof==selected and (expected_plan is None or proof['plan_sha256']==digest(expected_plan)),'delivery_revalidation_binding')
    fresh=load(queue,preparation,delivery=True);_compare(old,fresh)
    return fresh
