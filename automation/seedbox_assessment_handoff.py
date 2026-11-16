"""One source-only terminal handoff; old model and review records are immutable."""
import json,time,uuid
from ai_movie_investigator.contracts import require,digest,decode
from automation.seedbox_original_ownership import KIND,completed


def anchor(c,case_id):
    rows=c.execute('select x.version,x.observed,h.material,h.evidence from selection_current x join selection_history h on h.version=x.version where x.case_key=?',(case_id,)).fetchall()
    require(len(rows)==1,'handoff_case');version,observed,raw,evidence=rows[0];material=json.loads(raw)
    require(digest([case_id,material])==version,'handoff_case')
    cursor=c.execute('select coalesce(max(rowid),0) from deliveries').fetchone()[0]
    reviews=c.execute('select id from selection_reviews where case_key=? order by id',(case_id,)).fetchall()
    return dict(kind='selected_release_job_anchor_v1',case_id=case_id,version=version,observed_at=observed,material=material,selected_evidence=evidence,delivery_cursor=cursor,reviews_sha256=digest(reviews))


def lineage(c,actor,old,ownership):
    """Prove normal retry outcomes, not an inferred exact original webhook ID."""
    case=old['case_id'];current=anchor(c,case);source=case[8:]
    require(current['material']['metadata']==old['material']['metadata']==ownership['metadata'] and current['material']['correlation']==old['material']['correlation']=='strong_source_id' and (current['material']['route']=='eligible' or (current['material']['route']=='review_only' and current['material']['outcome']['status']=='needs_review' and current['material']['outcome']['reason']=='retry_exhausted')) and current['reviews_sha256']==old['reviews_sha256'],'handoff_material_changed')
    require(current['delivery_cursor']>=old['delivery_cursor'],'handoff_cursor')
    require(c.execute('select 1 from deliveries where rowid=?',(old['delivery_cursor'],)).fetchone() is not None,'handoff_cursor')
    material=lambda x:{k:v for k,v in x.items() if k not in ('status','reason')}
    original=old['material']['outcome']
    require(material(current['material']['outcome'])==material(original),'handoff_material_changed')
    latest=actor.execute('select id,reason,ended,started from retry_attempts where version=? order by started desc limit 2',(ownership['version'],)).fetchall()
    require(latest and latest[0][2] is not None and (len(latest)==1 or latest[0][3]!=latest[1][3]),'handoff_retry_link')
    terminal_event=str(uuid.UUID(latest[0][0]))
    rows=c.execute('select d.rowid,d.channel,d.event_id,d.signature,d.evidence,d.source_time,e.release,e.metadata from deliveries d left join evidence e on e.id=d.evidence where (d.rowid>? or d.event_id=?) and (e.release=? or e.release is null) order by d.rowid limit 10001',(old['delivery_cursor'],terminal_event,source)).fetchall()
    require(len(rows)<=10000,'handoff_capacity');links=[]
    for cursor,channel,event,signature,evidence,observed,release,raw in rows:
        require(channel=='outcome' and release==source and raw is not None,'handoff_new_or_unknown_occurrence')
        meta=json.loads(raw);require(meta==ownership['metadata'],'handoff_material_changed')
        try:attempt=uuid.UUID(event).hex
        except (ValueError,TypeError,AttributeError):raise ValueError('handoff_retry_link') from None
        attempts=actor.execute('select version,started,ended,reason from retry_attempts where id=?',(attempt,)).fetchall()
        require(len(attempts)==1 and attempts[0][0]==ownership['version'] and attempts[0][2] is not None and attempts[0][1]<=observed<=attempts[0][2],'handoff_retry_link')
        events=c.execute('select id,outcome from selection_events where release=? and evidence=? and observed=?',(source,evidence,observed)).fetchall();matches=[]
        for ident,outcome_raw in events:
            outcome=json.loads(outcome_raw)
            require(ident==digest([source,evidence,observed,outcome]),'handoff_selection_link')
            if digest(dict(event_id=event,release=source,metadata=meta,outcome=outcome))==signature:matches.append((ident,outcome))
        require(len(matches)==1,'handoff_selection_link');ident,outcome=matches[0]
        require(material(outcome)==material(original) and outcome['status'] in ('unresolved','needs_review') and outcome['reason'] in (original['reason'],'retry_exhausted') and attempts[0][3]==original['reason'],'handoff_material_changed')
        require(not c.execute('select 1 from conflicts where channel=? and event_id=?',(channel,event)).fetchone(),'handoff_conflict')
        links.append(dict(cursor=cursor,event_id=event,selection_id=ident,attempt_sha256=digest([attempt,*attempts[0]])))
    selected_id=digest([source,current['selected_evidence'],current['observed_at'],current['material']['outcome']])
    terminal=[link for link in links if uuid.UUID(link['event_id']).hex==latest[0][0]]
    require(terminal,'handoff_terminal_outcome_pending')
    require(len(terminal)==1 and terminal[0]==links[-1] and terminal[0]['selection_id']==selected_id,'handoff_retry_link')
    job=actor.execute('select state,reason from retry_jobs where version=?',(ownership['version'],)).fetchone()
    require(job in (('review',latest[0][1]),('done',latest[0][1])),'handoff_retry_link')
    current['delivery_cursor']=max(old['delivery_cursor'],links[-1]['cursor'])
    return dict(kind='same_release_job_retry_progression_v1',old_anchor_sha256=digest(old),current_anchor=current,links=links,
        original_webhook_identity='not_established',original_receipt_sha256=digest(ownership))


def retained(queue,preparation):
    from automation.seedbox_evidence import load
    with queue.locked() as (rows,_):
        reports=[r for r in rows if r['type']=='seedbox_assessment_pending_review_v1' and r['preparation']==preparation]
        require(len(reports)==1,'handoff_report')
    return load(queue,preparation,now=reports[0]['at'])


def observe(queue,config,preparation):
    from automation.seedbox_host_io import database
    old=retained(queue,preparation);ownership=old['target_pin']
    require(ownership.get('kind')==KIND,'handoff_ownership')
    with database(config['actor_database']) as actor:
        target=completed(actor,ownership,config)
        with database(config['collector_database']) as c:proof=lineage(c,actor,old['manifest']['assessment_anchor'],ownership)
    return dict(kind='seedbox_terminal_handoff_v1',preparation=preparation,old_manifest_sha256=digest(old['manifest']),ownership_sha256=digest(ownership),target=target,lineage=proof,configuration_sha256=digest(config))


def before_delivery(queue,config,preparation):
    """Quiet local waiting, then at most one exact source reobservation."""
    from automation.seedbox_original_readiness import WAIT_REASONS
    from automation.seedbox_delivery_evidence import revalidate,proposal,current
    old=retained(queue,preparation)
    if old['target_pin'].get('kind')!=KIND:return True
    try:proof=observe(queue,config,preparation)
    except ValueError as error:
        if str(error) not in WAIT_REASONS|{'handoff_terminal_outcome_pending'}:raise
        # Only finite reason is retained. No model, source or sender reservation.
        with queue.locked() as (rows,append):
            waits=[r for r in rows if r['type']=='seedbox_terminal_wait_v1' and r['preparation']==preparation]
            if not waits or waits[-1]['reason']!=str(error):append(dict(type='seedbox_terminal_wait_v1',preparation=preparation,reason=str(error),at=time.time()))
        return False
    with queue.locked() as (rows,_):
        attempts=[r for r in rows if r['type']=='seedbox_delivery_revalidation_started_v1' and r['preparation']==preparation]
    if attempts:
        current(queue,preparation);return True
    p=old['projection'];a=proof['lineage']['current_anchor']
    if a['version']==p['version'] and a['observed_at']==p['observed_at'] and time.time()+180<min(p['evidence_expires_at'],p['generated_at']+3600):return True
    selected=proposal(queue,preparation,handoff=proof)
    revalidate(queue,config,preparation,digest(selected),handoff=proof)
    return True


def verify_collector(c,proof):
    """Final collector check under sender lock; never reopen its actor inode."""
    selected=proof['lineage'];expected=selected['current_anchor'];actual=anchor(c,expected['case_id'])
    cursors=c.execute('select d.rowid from deliveries d left join evidence e on e.id=d.evidence where d.rowid>? and (e.release=? or e.release is null) order by d.rowid limit 10001',(expected['delivery_cursor'],expected['case_id'][8:])).fetchall()
    require(not cursors,'handoff_new_or_unknown_occurrence')
    actual['delivery_cursor']=expected['delivery_cursor']
    require(actual==expected,'handoff_changed')
