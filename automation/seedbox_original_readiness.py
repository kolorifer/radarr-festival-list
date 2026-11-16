"""Local original-message prerequisite. No credentials, GET, model or sender."""
import json,time
from ai_movie_investigator.contracts import require,digest
from identity_triage_intake import normalize

WAIT_REASONS={'original_job_missing','telegram_original_missing','telegram_original_incomplete','telegram_original_not_quiescent'}
REFUSALS=WAIT_REASONS|{'host_listing_source','host_listing_capacity','host_listing_case','host_listing_id','host_listing_url','host_listing_ambiguous_or_missing','telegram_single_original_required','telegram_original_ref','telegram_original_payload_changed','telegram_source_binding','telegram_duplicate_original_ref','telegram_receipt_capacity','host_case_missing','snapshot_selection','original_recovery_changed'}

class OriginalWait(ValueError):
    def __init__(self,view):
        super().__init__(view['reason']);self.view=view


def binding(connection,case_id,metadata,sources,allowed_source,*,assessment=False):
    from automation.seedbox_source_evidence import actor_listing
    require(case_id.startswith('outcome-') and metadata['source']==allowed_source,'host_listing_source')
    jobs=connection.execute('select version,body,state,reason,lease,until from retry_jobs where source=? order by version limit 101',(case_id[8:],)).fetchall()
    require(len(jobs)<=100,'host_listing_capacity');matched=[];messages=[]
    for row in jobs:
        record=normalize(json.loads(row[1])['observation'],sources,'outcome')
        if record.get('reason') or record['metadata']!=metadata:continue
        matched.append(row)
        messages.append(connection.execute('select version,payload,refs,context,terminal,prepared,state,attempts,due,created from retry_messages where version=?',(row[0],)).fetchone())
    # Hash only local material, not polling time. No raw actor data is journaled.
    fingerprint=digest(dict(jobs=[(r[0],r[1],r[2],r[3],r[4] is None,r[5]) for r in matched],
        messages=[None if r is None else (*r[:7],r[7]>0,r[9]) for r in messages]))
    if not matched:
        raise OriginalWait(dict(kind='seedbox_original_readiness_v1',status='waiting',reason='original_job_missing',case_id=case_id,local_sha256=fingerprint))
    require(len(matched)==1,'host_listing_ambiguous_or_missing')
    try:
        selected=actor_listing(connection,case_id,metadata,sources,allowed_source,ready_at=time.time(),assessment=assessment)
    except ValueError as error:
        reason=str(error)
        if reason not in WAIT_REASONS:raise
        # Ambiguity, superseded jobs and failed/consumed edits never become waits.
        require(len(matched)==1,'host_listing_ambiguous_or_missing')
        job=matched[0];message=messages[0]
        require(job[2] in ('pending','leased','done','review') and job[3]!='superseded','original_wait_invalid_lifecycle')
        require(message is None or message[6] in ('waiting','edited'),'original_wait_invalid_lifecycle')
        raise OriginalWait(dict(kind='seedbox_original_readiness_v1',status='waiting',reason=reason,case_id=case_id,local_sha256=fingerprint)) from None
    return selected,dict(kind='seedbox_original_readiness_v1',status='ready',reason='original_receipt_validated' if assessment else 'original_complete_quiescent',case_id=case_id,local_sha256=digest(selected['target']['ownership_pin']) if assessment else fingerprint,target_sha256=digest(selected['target']['ownership_pin']) if assessment else digest(selected['target']),actor_version=selected['actor_version'])


def inspect(queue,config,preparation,*,assessment=False):
    from automation.seedbox_host_io import database,selected_snapshot
    from ai_movie_investigator.snapshot_review import select
    import hashlib
    with queue.locked() as (rows,_):
        claims=[r for r in rows if r['type']=='seedbox_preparation_claimed_v1' and digest(r)==preparation]
        require(len(claims)==1,'host_preparation_missing');claim=claims[0]
        require(rows[0]['configuration_sha256']==digest(config),'host_configuration_changed')
    with database(config['collector_database']) as c:raw,metadata,_=selected_snapshot(c,claim['case_id'],time.time())
    select(raw,hashlib.sha256(raw).hexdigest(),claim['case_id'],claim['version'],now=time.time())
    with database(config['actor_database']) as c:
        try:_,view=binding(c,claim['case_id'],metadata,config['sources'],config['listing_source'],assessment=assessment)
        except OriginalWait as error:view=error.view
    return bind_view(queue,config,preparation,dict(view,purpose="assessment") if assessment else view)


def bind_view(queue,config,preparation,view):
    with queue.locked() as (rows,_):
        claims=[r for r in rows if r['type']=='seedbox_preparation_claimed_v1' and digest(r)==preparation]
        require(len(claims)==1 and rows[0]['configuration_sha256']==digest(config),'host_configuration_changed')
        claim=claims[0];require(view['case_id']==claim['case_id'],'host_listing_case')
    return dict(view,preparation=preparation,version=claim['version'],configuration_sha256=digest(config),actor_database_sha256=digest(config['actor_database']))


def transition(queue,preparation,view):
    with queue.locked() as (rows,append):
        prior=[r for r in rows if r['type']=='seedbox_original_readiness_v1' and r['preparation']==preparation]
        if prior and prior[-1]['view']==view:return False
        # A clock alone cannot turn an unchanged waiting row into permission.
        if prior and prior[-1]['view']['status']=='waiting' and view['status']=='ready' and prior[-1]['view'].get('purpose')==view.get('purpose') and prior[-1]['view']['local_sha256']==view['local_sha256']:return False
        append(dict(type='seedbox_original_readiness_v1',preparation=preparation,view=view,at=time.time()))
    return True


def ready(queue,config,preparation,*,assessment=False):
    with queue.locked() as (rows,_):
        recovered=[r for r in rows if r['type']=='seedbox_original_recovery_v1' and r['preparation']==preparation]
    if recovered and recovered[-1]['proof']['kind']=='seedbox_original_recovery_proposal_v1':assessment=False
    view=inspect(queue,config,preparation,assessment=assessment)
    if recovered:require(view==recovered[-1]['proof']['view'],'original_recovery_changed')
    transition(queue,preparation,view)
    if view['status']!='ready':return False
    with queue.locked() as (rows,_):last=[r for r in rows if r['type']=='seedbox_original_readiness_v1' and r['preparation']==preparation][-1]
    return last['view']['status']=='ready'


def diagnostic(error,phase):
    reason=str(error)
    return dict(kind='seedbox_source_diagnostic_v1',phase=phase,reason=reason if reason in REFUSALS|{'original_wait_invalid_lifecycle','host_configuration_changed'} else 'source_unclassified')


def recovery_proposal(queue,config,preparation,*,assessment=False):
    """Explicit one-new-observation authority; never proves old GET absence."""
    import os
    from ai_movie_investigator.private_files import private_chain
    from automation.seedbox_circuit import active
    view=inspect(queue,config,preparation,assessment=assessment)
    require(view['status']=='ready','original_recovery_not_ready')
    with queue.locked() as (rows,_):
        require(not active(rows),'original_recovery_circuit')
        require(view['case_id'] not in rows[0]['prior_consumed_cases'],'original_recovery_consumed')
        claims=[r for r in rows if r['type']=='seedbox_preparation_claimed_v1' and r['case_id']==view['case_id']]
        related={digest(r) for r in claims}
        require(not any((r.get('preparation') in related or r.get('case_id')==view['case_id']) and r['type'] in ('seedbox_provider_started_v1','seedbox_sender_started_v1','seedbox_evidence_retained_v1','seedbox_delivery_terminal_v1','seedbox_original_recovery_v1') for r in rows),'original_recovery_consumed')
        require(not any(r.get('preparation')==preparation and r['type']=='seedbox_preparation_superseded_v1' for r in rows),'original_recovery_superseded')
        blocked=[r for r in rows if r.get('preparation')==preparation and r['type']=='seedbox_operation_blocked_v1']
        require(len(blocked)==1,'original_recovery_block')
        detail=blocked[0]['diagnostic']
        require(detail.get('reason') in WAIT_REASONS or detail.get('reason')=='unexpected_exception','original_recovery_reason')
        starts=[r for r in rows if r.get('preparation')==preparation and r['type']=='seedbox_source_started_v1']
        require(len(starts)<config['source_attempt_limit'],'original_recovery_source_cap')
        failures=[r for r in rows if r.get('preparation')==preparation and r['type']=='seedbox_source_blocked_v1']
        require(all(r['reason']=='source_interrupted' for r in failures),'original_recovery_source_failure')
        with private_chain(queue.path) as parent:
            for prep in related:
                try:os.stat('evidence-'+prep,dir_fd=parent,follow_symlinks=False)
                except FileNotFoundError:pass
                else:raise ValueError('original_recovery_evidence_exists')
        return dict(kind='seedbox_assessment_original_recovery_v1' if assessment else 'seedbox_original_recovery_proposal_v1',preparation=preparation,view=view,
            history_sha256=digest(rows),blocked_sha256=digest(blocked[0]),source_start_sha256=[digest(r) for r in starts],
            source_failure_sha256=[digest(r) for r in failures],historical_source_outcome='unknown',
            authorization='one_new_source_observation',provider_or_sender_consumed=False)


def recover(queue,config,preparation,proposal_sha256,*,assessment=False):
    proof=recovery_proposal(queue,config,preparation,assessment=assessment)
    require(digest(proof)==proposal_sha256,'original_recovery_changed')
    # Caller holds the ordinary singleton. Recompute current local proof again;
    # capture still rechecks it before the future source marker/credential/GET.
    require(recovery_proposal(queue,config,preparation,assessment=assessment)==proof,'original_recovery_changed')
    with queue.locked() as (rows,append):
        require(not any(r.get('preparation')==preparation and r['type']=='seedbox_original_recovery_v1' for r in rows),'original_recovery_consumed')
        require(digest(rows)==proof['history_sha256'],'original_recovery_changed')
        event=dict(type='seedbox_original_recovery_v1',preparation=preparation,proof=proof,proof_sha256=digest(proof),at=time.time())
        append(event)
    return event
