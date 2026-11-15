"""Bounded main-reviewed original-card edits; no scheduler, model or credentials.

Main authenticates the exact operator review, remote DB/source pins and single
serial actor topology. A file/hash alone cannot establish those attestations.
The injected edit callback is the existing approved in-memory Telegram sender.
"""
from contextlib import contextmanager
import hashlib
import math
import os
import re
import signal
import stat
import threading
import copy
import json
import time
from pathlib import Path

from identity_triage_store import digest
from identity_triage_intake import safe_text


def require(value,reason):
    if not value:raise ValueError(reason)


def shape(value,keys):
    require(type(value) is dict and set(value)==set(keys.split()),'telegram_shape')


def stamp(value):
    require(type(value) in (int,float) and math.isfinite(value) and 0<value<10**11,'telegram_clock')
    return value


def text(value,limit):
    return safe_text(value,limit)


def _validate_plan(plan,now):
    shape(plan,'kind case_id version review_sha256 report_sha256 receipt_sha256 html_sha256 local_context_sha256 source_url candidate summary text reviewed_at production_approved download_approved')
    require(plan['kind']=='reviewed_original_card_v1' and plan['production_approved'] is False and
        plan['download_approved'] is False and re.fullmatch(r'outcome-[a-f0-9]{64}',plan['case_id']), 'telegram_plan')
    for k in ('version','review_sha256','report_sha256','receipt_sha256','html_sha256','local_context_sha256'):
        require(type(plan[k]) is str and re.fullmatch('[a-f0-9]{64}',plan[k]),'telegram_plan')
    require(stamp(plan['reviewed_at'])<=now and type(plan['text']) is str and
        0<len(plan['text'].encode('utf-16-le'))//2<=900,'telegram_plan')
    from urllib.parse import urlsplit
    u=urlsplit(plan['source_url'])
    require(u.scheme=='https' and bool(u.hostname) and not(u.username or u.password or u.query or u.fragment) and
        len(plan['source_url'])<=256 and not any(ord(c)<32 for c in plan['source_url']) and
        'Source listing: '+plan['source_url'] in plan['text'],'telegram_source_context')
    shape(plan['summary'],'discrepancy evidence uncertainty')
    if plan['candidate'] is not None:
        shape(plan['candidate'],'imdb tmdb')
        require(re.fullmatch(r'tt[0-9]{7,10}',plan['candidate']['imdb']) and
            type(plan['candidate']['tmdb']) is int and plan['candidate']['tmdb']>0,'telegram_candidate_binding')


def prepare(operator,reservation,summary):
    """Main-authored concise synopsis AFTER full review, not a new assessment.

    Returns a private deterministic plan. Local text is never a production
    identity decision, disclosure expansion or download approval.
    """
    from ai_movie_investigator.contracts import text
    shape(summary,'discrepancy evidence uncertainty')
    for k,n in (('discrepancy',160),('evidence',240),('uncertainty',160)):
        text(summary[k],n)
        require('\n' not in summary[k] and '\r' not in summary[k],'telegram_summary_lines')
        # These fields are authored by main, not copied blindly from model output.
        from private_text import redact_text
        require(redact_text(summary[k])==summary[k],'telegram_summary_private')
    with operator.locked() as (root,rows,append):
        reviewed=[r for r in rows if r.get('reservation')==reservation and r['type']=='operator_reviewed_v1']
        pending=[r for r in rows if r.get('reservation')==reservation and r['type']=='operator_pending_review_v1']
        prepared=[r for r in rows if r.get('reservation')==reservation and r['type']=='operator_prepared_v1']
        require(len(reviewed)==len(pending)==len(prepared)==1,'telegram_review_required')
        r,p,g=reviewed[0],pending[0],prepared[0]
        require(r['pending_sha256']==digest(p),'telegram_review_binding')
        completed=[e for e in root if e.get('type')=='supervised_completed' and e.get('slot')==p['slot']]
        require(len(completed)==1 and digest(completed[0])==p['completion_sha256'],'telegram_completion_binding')
        result=completed[0]['historical_report'];projection=g['projection']
        require(digest(result)==p['report_sha256'] and result['provider_receipt_correlated'] is True and
                result['generation_invoked'] is True,'telegram_completion_binding')
        from automation.recurring_snapshot_operator import pin_read
        from ai_movie_investigator.snapshot_private_report import validate_local_context
        from urllib.parse import urlsplit
        local=validate_local_context(pin_read(g['local_context']))
        require(result['local_context_sha256']==g['local_context']['sha256'],'telegram_source_context')
        source_url=local['tracker_url'];url=urlsplit(source_url)
        require(len(source_url)<=256 and not url.query and not url.fragment,'telegram_source_link_private')
        candidate=result['result']['candidate']
        catalogue=projection['catalogue']
        supported=result['result']['status']=='supported_candidate'
        if supported:
            require(candidate=={'imdb':catalogue['imdb'],'tmdb':catalogue['tmdb']},'telegram_candidate_binding')
            heading='Reviewed assessment supports a candidate'
        else:
            require(candidate is None,'telegram_candidate_binding');heading='Reviewed assessment remains unresolved'
        label=(str(catalogue['title'])+' ('+str(catalogue['theatrical_year'])+') — '+str(catalogue['imdb'])) if supported else 'No identity is confirmed.'
        card='\n'.join((heading,label,'Discrepancy: '+summary['discrepancy'],
            'Evidence: '+summary['evidence'],'Uncertainty: '+summary['uncertainty'],
            'Source listing: '+source_url,
            'Review proposal only. Production matching is unchanged. No download is approved.'))
        require(len(card.encode('utf-16-le'))//2<=900,'telegram_card_size')
        plan=dict(kind='reviewed_original_card_v1',case_id=projection['case_id'],version=projection['version'],
            review_sha256=digest(r),report_sha256=digest(result),receipt_sha256=result['receipt_hash'],
            html_sha256=p['html']['sha256'],local_context_sha256=g['local_context']['sha256'],
            source_url=source_url,candidate=candidate,summary=summary,text=card,
            reviewed_at=r['observed_at'],production_approved=False,download_approved=False)
        _validate_plan(plan,stamp(operator.clock()))
        old=[e for e in rows if e.get('review_reservation')==reservation and e['type']=='operator_telegram_prepared_v1']
        if old:
            require(len(old)==1 and old[0]['plan']==plan,'telegram_plan_immutable');return old[0]
        event=dict(type='operator_telegram_prepared_v1',review_reservation=reservation,
                   plan=plan,plan_sha256=digest(plan),at=stamp(operator.clock()))
        append(event);return event


def _schema(c):
    c.execute('create table if not exists reviewed_telegram_edits(message_key text primary key,case_id text unique not null,version text not null,plan_sha256 text not null,target_sha256 text not null,state text not null,receipt text,created real not null)')


def _row(c,version):
    names=('version','payload','refs','context','terminal','prepared','state','attempts','due','created',
           'job_source','job_state','job_reason','job_lease','job_until','job_body')
    row=c.execute('select m.version,m.payload,m.refs,m.context,m.terminal,m.prepared,m.state,m.attempts,m.due,m.created,j.source,j.state,j.reason,j.lease,j.until,j.body from retry_messages m join retry_jobs j on j.version=m.version where m.version=?',(version,)).fetchone()
    require(row is not None,'telegram_original_missing')
    return dict(zip(names,row))


def inspect_target(store,version,sources):
    """Read-only exact original receipt/source discovery; main verifies its origin."""
    with store.tx() as c:return _target(c,version,sources)


def _target(c,version,sources):
    from identity_triage_intake import normalize
    from identity_triage_observer import envelope
    from identity_triage_store import digest as source_digest
    row=_row(c,version)
    require(all(row[k] is not None for k in ('payload','refs','context','prepared','terminal')),'telegram_original_incomplete')
    payload=json.loads(row['payload']);refs=json.loads(row['refs']);context=json.loads(row['context'])
    require(payload.get('_retry_original_event')==1 and len(refs)==1,'telegram_single_original_required')
    ref=refs[0];shape(ref,'chat_id message_id kind')
    require(type(ref['chat_id']) is str and type(ref['message_id']) is int and ref['message_id']>0 and
            ref['kind'] in ('text','caption'),'telegram_original_ref')
    observation=json.loads(row['job_body'])['observation']
    original=normalize(observation,sources,'outcome')
    # The existing receipt serializer omits implementation. Recover ONLY that
    # transport label from the exact retained job after matching every retained
    # normalization input; never infer new movie facts or a title-only key.
    release=payload['data']['release'];job_release=observation['data']['release']
    require(all(release.get(k)==job_release.get(k) for k in
        ('type','protocol','title','year','name','external_id','meta_imdb','meta_tmdb')),'telegram_original_payload_changed')
    bound=copy.deepcopy(payload);bound['data']['release']['implementation']=job_release.get('implementation')
    normalized=normalize(envelope(bound,context,sources),sources,'outcome')
    require(not normalized.get('reason') and not original.get('reason') and
            normalized['metadata']['release_key_basis']=='external_id' and
            original['metadata']['release_key_basis']=='external_id' and
            normalized['release']==original['release']==row['job_source'] and
            source_digest([normalized['release'],normalized['metadata']])==version and
            source_digest([original['release'],original['metadata']])==version,'telegram_source_binding')
    others=c.execute('select version,refs from retry_messages where refs is not null limit 10001').fetchall()
    require(len(others)<=10000,'telegram_receipt_capacity')
    for other,raw in others:
        if other==version:continue
        for r in json.loads(raw):
            require((str(r.get('chat_id')),r.get('message_id'))!=(ref['chat_id'],ref['message_id']),
                    'telegram_duplicate_original_ref')
    return dict(row=row,ref=ref,case_id='outcome-'+normalized['release'],
                row_sha256=digest(row),message_key=digest([ref['chat_id'],ref['message_id']]))


@contextmanager
def _deadline(seconds):
    require(threading.current_thread() is threading.main_thread() and
            hasattr(signal,'setitimer') and signal.getitimer(signal.ITIMER_REAL)==(0.0,0.0),
            'telegram_deadline_unavailable')
    if hasattr(signal,'pthread_sigmask'):
        require(signal.SIGALRM not in signal.pthread_sigmask(signal.SIG_BLOCK,[]),'telegram_deadline_unavailable')
    old=signal.getsignal(signal.SIGALRM)
    def expired(*_):raise TimeoutError('telegram_edit_deadline')
    signal.signal(signal.SIGALRM,expired);signal.setitimer(signal.ITIMER_REAL,seconds)
    try:yield
    finally:
        signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,old)


def _check_spool(store,version,ref):
    # The actor's binding spool is independent of SQLite. Main must additionally
    # verify no producer can publish another binding for THIS acknowledged ref
    # during this operation. Fresh sends receive distinct Telegram message IDs.
    from identity_triage_store import private_path
    spool=store.directory/'message-bindings'
    if not spool.exists():return
    private_path(spool,True)
    paths=[]
    with os.scandir(spool) as entries:
        for entry in entries:
            require(len(paths)<1000,'telegram_spool_capacity');paths.append(Path(entry.path))
    for path in paths:
        private_path(path)
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        try:
            before=os.fstat(fd)
            require(stat.S_ISREG(before.st_mode) and before.st_uid==os.getuid() and
                stat.S_IMODE(before.st_mode)==0o600 and before.st_nlink==1 and 0<before.st_size<=131072,
                'telegram_spool_file')
            raw=os.read(fd,131073);after=os.fstat(fd)
            fields=('st_dev','st_ino','st_size','st_mtime_ns','st_ctime_ns','st_mode','st_nlink')
            require(len(raw)==before.st_size and all(getattr(before,k)==getattr(after,k) for k in fields) and
                os.path.samestat(after,path.lstat()),'telegram_spool_changed')
        finally:os.close(fd)
        item=json.loads(raw)
        require(path.name==item['version']+'.json' and item['version']!=version,'telegram_original_spool_pending')
        for other in json.loads(item['refs']):
            require((str(other.get('chat_id')),other.get('message_id'))!=(ref['chat_id'],ref['message_id']),
                    'telegram_original_spool_pending')


def _boundary_valid(boundary,plan,now):
    shape(boundary,'kind single_serial_pump no_other_edit_writers no_original_binding_republication deployed_revision verified_reference reviewed_plan_sha256 observed_at expires_at')
    require(boundary['kind']=='main_verified_sender_boundary_v1' and boundary['single_serial_pump'] is True and
        boundary['no_other_edit_writers'] is True and boundary['no_original_binding_republication'] is True and
        boundary['reviewed_plan_sha256']==digest(plan) and
        boundary['deployed_revision']=='06d17aafefb5a5161364e4bf6f63667a649e1aa3' and
        now-300<=stamp(boundary['observed_at'])<=now<stamp(boundary['expires_at']) and
        boundary['expires_at']<=boundary['observed_at']+300 and
        boundary['expires_at']-now>=30,'telegram_sender_boundary')
    text(boundary['verified_reference'],512)



def deliver(store,plan,target_pin,sources,boundary,edit,*,clock=time.time):
    """At most ONE exact edit; no resend on restart or uncertain acknowledgement.

    The old actor must have one serial pump and no other edit writer. Its existing
    `edited` row is a callback-return record, not independent human ingestion.
    This external topology/code fact is verified by main, not inferred from DB.
    """
    now=stamp(clock());_boundary_valid(boundary,plan,now)
    _validate_plan(plan,now)
    shape(target_pin,'version row_sha256 ref case_id')
    require(target_pin['case_id']==plan['case_id'],'telegram_case_changed')
    message_key=digest([target_pin['ref']['chat_id'],target_pin['ref']['message_id']]);plan_sha=digest(plan)
    # Commit a permanent no-resend reservation BEFORE external I/O. Separate
    # table survives the old retry_messages eight-day cleanup.
    with _deadline(15),store.tx() as c:
        _schema(c)
        old=c.execute('select plan_sha256,target_sha256,state,receipt from reviewed_telegram_edits where message_key=? or case_id=?',(message_key,plan['case_id'])).fetchall()
        if old:
            require(len(old)==1 and old[0][0]==plan_sha and old[0][1]==digest(target_pin),'telegram_delivery_conflict')
            return dict(status=old[0][2],receipt=json.loads(old[0][3]) if old[0][3] else None,resend=False)
        target=_target(c,target_pin['version'],sources);row=target['row']
        require(target['row_sha256']==target_pin['row_sha256'] and target['ref']==target_pin['ref'] and
                target['case_id']==plan['case_id'],'telegram_target_changed')
        require(row['state']=='edited' and row['attempts']>0 and row['job_state'] in ('done','review') and
                row['job_reason']!='superseded' and row['job_lease'] is None and
                (row['job_until'] is None or type(row['job_until']) in (int,float) and math.isfinite(row['job_until']) and row['job_until']<=now),
                'telegram_original_not_quiescent')
        require(row['created']+8*86400>boundary['expires_at'],'telegram_receipt_expiring')
        _check_spool(store,target_pin['version'],target_pin['ref'])
        now=stamp(clock());_boundary_valid(boundary,plan,now)
        require(row['created']+8*86400>boundary['expires_at'],'telegram_receipt_expiring')
        c.execute('insert into reviewed_telegram_edits values(?,?,?,?,?,"reserved",NULL,?)',
            (message_key,plan['case_id'],target_pin['version'],plan_sha,digest(target_pin),now))
        c.execute('update retry_messages set state="reviewed_reserved" where version=?',(target_pin['version'],))
    try:
        # Holding the existing writer transaction through this one 15-second
        # sender call serializes newer outcomes, cleanup and old pump selection.
        with _deadline(15),store.tx() as c:
            reservation=c.execute('select case_id,version,plan_sha256,target_sha256,state from reviewed_telegram_edits where message_key=?',(message_key,)).fetchone()
            require(reservation==(plan['case_id'],target_pin['version'],plan_sha,digest(target_pin),'reserved'),
                    'telegram_reservation_changed')
            _check_spool(store,target_pin['version'],target_pin['ref'])
            current=_target(c,target_pin['version'],sources);row=current['row']
            require(row['state']=='reviewed_reserved','telegram_reservation_changed')
            row['state']='edited'
            require(digest(row)==target_pin['row_sha256'] and current['ref']==target_pin['ref'],
                    'telegram_target_changed')
            require(clock()+15<boundary['expires_at'],'telegram_sender_boundary')
            edit([target_pin['ref']],dict(text=plan['text'],token=None))
            receipt=dict(kind='reviewed_telegram_sender_ack_v1',message_key=message_key,
                ref=target_pin['ref'],case_id=plan['case_id'],plan_sha256=plan_sha,
                target_sha256=digest(target_pin),acknowledged_at=stamp(clock()),
                acknowledgement='existing_sender_returned',human_ingestion=False)
            c.execute('update reviewed_telegram_edits set state="acknowledged",receipt=? where message_key=?',
                      (json.dumps(receipt,sort_keys=True),message_key))
            c.execute('update retry_messages set state="reviewed_edited" where version=?',(target_pin['version'],))
        return dict(status='acknowledged',receipt=receipt,resend=False)
    except Exception:
        # Never retain exception text: transport exceptions may contain bot URLs.
        try:
            with store.tx() as c:c.execute('update reviewed_telegram_edits set state="uncertain" where message_key=? and state="reserved"',(message_key,))
        except Exception:pass
        return dict(status='uncertain',receipt=None,resend=False)


def record_delivery(operator,reservation,receipt):
    """Main records the exact real sender receipt after independent readback."""
    shape(receipt,'kind message_key ref case_id plan_sha256 target_sha256 acknowledged_at acknowledgement human_ingestion')
    shape(receipt['ref'],'chat_id message_id kind')
    require(receipt['message_key']==digest([receipt['ref']['chat_id'],receipt['ref']['message_id']]) and
        stamp(receipt['acknowledged_at'])<=operator.clock(),'telegram_ack_binding')
    require(receipt.get('kind')=='reviewed_telegram_sender_ack_v1' and
        receipt.get('acknowledgement')=='existing_sender_returned' and receipt.get('human_ingestion') is False,
        'telegram_ack_required')
    with operator.locked() as (_,rows,append):
        plans=[r for r in rows if r['type']=='operator_telegram_prepared_v1' and r.get('review_reservation')==reservation]
        require(len(plans)==1 and plans[0]['plan_sha256']==receipt['plan_sha256'] and
            plans[0]['plan']['case_id']==receipt['case_id'],'telegram_ack_binding')
        old=[r for r in rows if r['type']=='operator_telegram_delivered_v1' and r.get('review_reservation')==reservation]
        if old:
            require(len(old)==1 and old[0]['receipt']==receipt,'telegram_ack_conflict');return old[0]
        event=dict(type='operator_telegram_delivered_v1',review_reservation=reservation,receipt=receipt,
                   at=stamp(operator.clock()))
        append(event);return event
