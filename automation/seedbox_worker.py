"""One serial durable event worker; no hourly case limiter or Mac dependency.

Entered only by the hash-verified bootstrap. No auto enrollment/reset, provider
retry, uncertain edit replay, or source refresh. All output is private state.
"""
import ctypes,fcntl,hashlib,json,os,select,struct,time
from pathlib import Path
from contextlib import contextmanager
from ai_movie_investigator.contracts import require,encoded,decode,digest
from ai_movie_investigator.private_files import private_chain,read_private,safe_acl
from ai_movie_investigator.snapshot_authorization import _write_once
from automation.seedbox_assessment_queue import Queue,collector_page,_pending,_source_blocked
from automation.seedbox_host_io import database,selected_snapshot,SourceFailure


@contextmanager
def singleton(queue):
    with private_chain(queue.path) as parent:
        fd=os.open('runner.lock',os.O_RDWR|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
        try:
            s=os.fstat(fd)
            require(s.st_uid==os.getuid() and s.st_nlink==1 and s.st_mode&0o777==0o600,'host_lock_changed');safe_acl(fd,False)
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            yield
            require(os.path.samestat(s,os.stat('runner.lock',dir_fd=parent,follow_symlinks=False)),'host_lock_changed')
        finally:os.close(fd)


class Wake:
    """Linux inotify is a hint; durable cursor drains even after lost wakeups."""
    def __init__(self,parent):
        lib=ctypes.CDLL(None,use_errno=True)
        lib.inotify_init1.argtypes=[ctypes.c_int];lib.inotify_init1.restype=ctypes.c_int
        lib.inotify_add_watch.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_uint32];lib.inotify_add_watch.restype=ctypes.c_int
        self.fd=lib.inotify_init1(os.O_CLOEXEC|os.O_NONBLOCK)
        require(self.fd>=0,'host_watch_unavailable')
        if lib.inotify_add_watch(self.fd,os.fsencode(parent),0x00000008|0x00000002|0x00000100|0x00000080|0x00000400|0x00000800)<0:
            os.close(self.fd);raise ValueError('host_watch_unavailable')
    def wait(self):
        # Bounded reconciliation catches missed notifications and due recovery;
        # this is not an assessment/hour limit. Drain immediately while work exists.
        if select.select([self.fd],[],[],30)[0]:os.read(self.fd,65536)
    def close(self):os.close(self.fd)


def _rows(queue):
    with queue.locked() as (rows,_):return list(rows)


def _record(queue,row):
    with queue.locked() as (_,append):append(row)


def recover_sources(queue,config):
    rows=_rows(queue);now=time.time()
    for preparation in _source_blocked(rows):
        failures=[r for r in rows if r['type']=='seedbox_source_blocked_v1' and r['preparation']==preparation];last=failures[-1]
        if last['owner_action'] or last['retry_not_before'] is None or now<last['retry_not_before']:continue
        starts=sum(r['type']=='seedbox_source_started_v1' and r['preparation']==preparation for r in rows)
        if starts>=config['source_attempt_limit']:continue
        _record(queue,dict(type='seedbox_source_recovery_v1',preparation=preparation,failure_sha256=digest(last),reason='bounded_transient_cooldown_elapsed',at=now))


def reconcile_source_interruptions(queue):
    rows=_rows(queue)
    for r in rows:
        if r['type']!='seedbox_source_started_v1':continue
        later=rows[rows.index(r)+1:]
        if any(x['type']=='seedbox_original_recovery_v1' and digest(r) in x['proof']['source_start_sha256'] for x in later):continue
        if not any(x.get('preparation')==r['preparation'] and x['type'] in ('seedbox_evidence_retained_v1','seedbox_source_blocked_v1') for x in later):
            # A GET may have happened. Retain the interruption; no automatic replay.
            _record(queue,dict(type='seedbox_source_blocked_v1',preparation=r['preparation'],reason='source_interrupted',owner_action=True,retry_not_before=None,provider_request_consumed=False,at=time.time()))


def load_key(queue,config):
    from automation.seedbox_credit_policy import permit
    from automation.seedbox_encrypted_credential import credential
    rows=_rows(queue)
    permit(config['credit_policy'],[dict(request_sha256=r['request_sha256'],reserved_usd=r['reserved_usd']) for r in rows if r['type']=='seedbox_provider_started_v1'],now=time.time())
    receipt=decode(read_private(Path(config['credential']['path']).parent/'provision-reserved.json'))
    require(receipt['project']==config['credit_policy']['project'] and receipt['policy_sha256']==digest(config['credit_policy']),'host_credential_provision_changed')
    from datetime import datetime,timezone
    expiry=datetime.strptime(receipt['not_after'],'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc).timestamp()
    require(time.time()<expiry<=config['credit_policy']['expires_at'],'host_credential_expired')
    return credential(config['credential'],project=config['credit_policy']['project'])


def source_paused(rows,now):
    return any(r['type'] in ('seedbox_source_blocked_v1','seedbox_delivery_revalidation_failed_v1') and r['reason']=='source_rate_limited' and now<r['retry_not_before'] for r in rows)


def step(queue,config):
    from automation.seedbox_evidence import capture
    from automation.seedbox_encrypted_credential import credential
    from ai_movie_investigator.seedbox_authorization import execute as assess
    from automation.seedbox_automated_review import execute as review
    from automation.seedbox_sender import deliver_reviewed
    from automation.seedbox_circuit import active,record
    rows=_rows(queue)
    if active(rows):return False
    pages=[r for r in rows if r['type']=='seedbox_queue_page_v1']
    cursor=pages[-1]['page']['through'] if pages else rows[0]['initial_cursor']
    try:
        with database(config['collector_database']) as c:page=collector_page(c,cursor)
    except Exception:
        _record(queue,record(rows,'source','shared_source_configuration_or_access'));return False
    queue.ingest(page,collector_identity=config['collector_identity'])
    recover_sources(queue,config)
    rows=_rows(queue)
    # Existing prepared/report/review records resume only the next unsent stage.
    candidates=[r for r in rows if r['type']=='seedbox_preparation_claimed_v1']
    for claim in candidates:
        preparation=digest(claim)
        operation=[r['type'] for r in rows if r.get('preparation')==preparation and r['type'] in ('seedbox_operation_blocked_v1','seedbox_operation_recovery_v1','seedbox_original_recovery_v1','seedbox_review_correction_completed_v1','seedbox_delivery_evidence_retained_v1','seedbox_delivery_revalidation_failed_v1')]
        if operation and operation[-1] in ('seedbox_operation_blocked_v1','seedbox_delivery_revalidation_failed_v1'):continue
        if any(r.get('preparation')==preparation and r['type'] in ('seedbox_preparation_superseded_v1','seedbox_delivery_terminal_v1') for r in rows):continue
        if preparation in _source_blocked(rows):continue
        deferrals=[r for r in rows if r['type']=='seedbox_sender_pre_send_deferred_v1' and r['preparation']==preparation]
        # The durable deferral itself enforces the count and cooldown.
        if deferrals and (len(deferrals)>=3 or time.time()<deferrals[-1]['at']+60):continue
        attempts=[r for r in rows if r.get('preparation')==preparation and r['type']=='seedbox_provider_started_v1']
        reports=[r for r in rows if r.get('preparation')==preparation and r['type']=='seedbox_assessment_pending_review_v1']
        reviews=[r for r in rows if r.get('preparation')==preparation and r['type'] in ('seedbox_automated_review_completed_v1','seedbox_review_correction_completed_v1')]
        if any(r['stage']=='assessment' for r in attempts) and not reports:continue
        if any(r['stage']=='review' for r in attempts) and not reviews:continue
        phase='source_local'
        try:
            if not any(r.get('preparation')==preparation and r['type']=='seedbox_evidence_retained_v1' for r in rows):
                if source_paused(rows,time.time()):continue
                with database(config['collector_database']) as c:raw,_,_=selected_snapshot(c,claim['case_id'],time.time())
                queue.refresh_preparations(raw,now=time.time())
                if any(r.get('preparation')==preparation and r['type']=='seedbox_preparation_superseded_v1' for r in _rows(queue)):return True
                from automation.seedbox_original_readiness import ready,OriginalWait,bind_view,transition
                if not ready(queue,config,preparation):continue
                phase='source_acquisition'
                try:capture(queue,config,preparation)
                except OriginalWait as error:
                    # The repeated local binding refused BEFORE the source marker
                    # and credentials/GET, even if the earlier precheck was ready.
                    transition(queue,preparation,bind_view(queue,config,preparation,error.view))
                    return False
                except SourceFailure as error:
                    queue.record_source_failure(preparation,reason=error.reason,retry_after=error.retry_after,now=time.time())
                    return True
                except ValueError as error:
                    reasons={'host_listing_crosswalk_needed','host_listing_ambiguous_or_missing','host_catalogue_ambiguous','host_listing_not_authenticated','telegram_original_missing'}
                    if str(error) in reasons:queue.record_source_failure(preparation,reason=str(error),retry_after=None,now=time.time());return True
                    raise
            if not reports:
                phase='credential'
                key=load_key(queue,config)
                phase='assessment'
                assess(queue,preparation,policy=config['credit_policy'],credential=key);del key
                return True
            if not reviews:
                phase='credential'
                key=load_key(queue,config)
                phase='review'
                review(queue,preparation,policy=config['credit_policy'],credential=key);del key
                return True
            if reviews[0]['answer']['verdict']!='approve':
                _record(queue,dict(type='seedbox_delivery_terminal_v1',preparation=preparation,status='review_rejected',at=time.time()));return True
            phase='delivery'
            result=deliver_reviewed(queue,config,preparation)
            _record(queue,dict(type='seedbox_delivery_terminal_v1',preparation=preparation,result=result,at=time.time()));return True
        except Exception as error:
            if phase=='delivery' and str(error)=='host_sender_pre_send_busy':
                current=_rows(queue)
                deferred={r['sender_start_sha256'] for r in current if r['type']=='seedbox_sender_pre_send_deferred_v1'}
                if not any(r['type']=='seedbox_sender_started_v1' and r['preparation']==preparation and digest(r) not in deferred for r in current):
                    count=sum(r['type']=='seedbox_sender_pre_send_deferred_v1' and r['preparation']==preparation for r in current)
                    _record(queue,dict(type='seedbox_delivery_wait_v1',preparation=preparation,reason='first_sqlite_transaction_busy_proven_unsent',checks=count,next_check_at=time.time()+60 if count<3 else None,status='bounded_local_recheck' if count<3 else 'operator_inspection_needed',at=time.time()))
                    return True
            if phase=='credential':
                reason=str(error)
                if reason in ('host_credit_exhausted','host_credit_expired'):_record(queue,record(_rows(queue),'provider',reason,preparation))
                else:_record(queue,record(_rows(queue),'credential','host_credential_unavailable',preparation))
            elif phase in ('source_local','source_acquisition') and (isinstance(error,PermissionError) or str(error).startswith(('host_configuration','host_cookie','host_source_configuration','unsafe_'))):
                _record(queue,record(_rows(queue),'source','shared_source_configuration_or_access',preparation))
            elif phase=='delivery' and str(error)!='host_sender_pre_send_busy' and (isinstance(error,PermissionError) or str(error).startswith(('host_actor_','host_sender_','host_topology_','selected_bot_configuration','unsafe_'))):
                _record(queue,record(_rows(queue),'telegram','shared_sender_configuration_or_access',preparation))
            from ai_movie_investigator.seedbox_authorization import diagnostic
            if phase=='review':
                from automation.seedbox_automated_review import diagnostic
            if phase in ('source_local','source_acquisition'):
                from automation.seedbox_original_readiness import diagnostic as source_diagnostic
                detail=source_diagnostic(error,phase)
            else:detail=diagnostic(error)
            _record(queue,dict(type='seedbox_operation_blocked_v1',preparation=preparation,diagnostic=detail,at=time.time()))
            return True
    if source_paused(_rows(queue),time.time()):return bool(page['events'])
    # Discover the next eligible occurrence without a full-export eligible cap.
    for event in _pending(_rows(queue)):
        with database(config['collector_database']) as c:raw,_,_=selected_snapshot(c,event['case_id'],time.time())
        queue.refresh_preparations(raw,now=time.time())
        if queue.reserve(raw,now=time.time()).get('reservation'):return True
    return bool(page['events'])


def run(config,configuration_sha256):
    require(config['kind']=='seedbox_event_worker_v1' and type(config['source_attempt_limit']) is int and 1<=config['source_attempt_limit']<=3,'host_configuration')
    queue=Queue(config['state']);rows=_rows(queue)
    require(rows[0]['configuration_sha256']==configuration_sha256 and rows[0]['policy_sha256']==digest(config['credit_policy']) and rows[0]['collector_identity']==config['collector_identity'],'host_configuration_changed')
    require(len(rows[0]['prior_consumed_cases'])==7 and config['credit_policy']['prior_reserved_usd'] in ([21,10],[210,100]),'host_legacy_cutover')
    with singleton(queue):
        reconcile_source_interruptions(queue)
        wake=Wake(Path(config['collector_database']['path']).parent)
        try:
            while True:
                if not step(queue,config):wake.wait()
        finally:wake.close()
