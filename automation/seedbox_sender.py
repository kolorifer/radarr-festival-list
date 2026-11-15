"""Exact original-card edit after a durable separately generated review.

Main selects unchanged actor topology/code and sole-writer ownership at activation.
Each edit rechecks that process identity and deployed bytes. It never starts the
actor, republishes an original message or treats a callback as human ingestion.
"""
import ast,hashlib,json,os,sqlite3,stat,time,types
from contextvars import ContextVar
from contextlib import contextmanager
from pathlib import Path
from ai_movie_investigator.contracts import require,digest
from ai_movie_investigator.private_files import private_chain,read_private,safe_acl
from automation.reviewed_telegram_UNISSUED import sender,pinned,read_file

_ACTIVE=ContextVar('seedbox_sender_boundary',default=None)

class _HostBoundary(dict):pass

class _FirstTransactionBusy(Exception):pass


def verified(boundary,plan):
    active=_ACTIVE.get()
    require(active is not None and boundary is active['boundary'] and digest(plan)==active['plan_sha256'],'host_sender_authority')
    active['queue'].history.require_write_transaction(active['rows'])
    require(time.monotonic()<active['deadline'],'host_sender_expired')


def _process(pin):
    from automation.seedbox_process import observe
    # Re-read the selected lifetime and command immediately before delivery.
    # Main's finite topology grant, not this check, supplies sole-writer authority.
    return observe(pin)


def _deployed(pin):
    """Public deployed code: exact selected metadata, not a private-input grant.

    Existing group-readable/writable public files are not chmodded or silently
    treated as private. Their literal metadata and every byte must match main's
    accepted deployment selection, and the actor process may not have restarted.
    """
    path=Path(pin['path']);require(path.is_absolute() and path.resolve(strict=True)==path,'host_actor_path')
    for parent in path.parents:
        info=parent.lstat();require(stat.S_ISDIR(info.st_mode) and info.st_uid in (0,os.getuid()) and not info.st_mode&0o022,'host_actor_ancestor')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        before=os.fstat(fd);fields=('st_dev','st_ino','st_mode','st_uid','st_gid','st_nlink')
        require(stat.S_ISREG(before.st_mode) and before.st_uid==os.getuid() and before.st_nlink==1 and 0<before.st_size<=1048576 and [getattr(before,k) for k in fields]==pin['metadata'],'host_actor_code_metadata')
        raw=b''
        while len(raw)<before.st_size:
            part=os.read(fd,min(65536,before.st_size-len(raw)));require(part,'host_actor_code_changed');raw+=part
        after=os.fstat(fd)
        require(all(getattr(before,k)==getattr(after,k) for k in fields+('st_size','st_mtime_ns','st_ctime_ns')) and os.path.samestat(after,path.lstat()) and hashlib.sha256(raw).hexdigest()==pin['sha256'],'host_actor_code_changed')
        return raw
    finally:os.close(fd)


def actor_directory_scope(pin):
    path=Path(pin['path']);require(path.name=='outcomes.sqlite3','host_actor_database_name')
    allowed={path.name,path.name+'-journal',path.name+'-wal',path.name+'-shm','message-bindings'}
    with private_chain(path.parent) as parent:
        entries=os.listdir(parent);require(set(entries)<=allowed,'host_actor_directory_scope')
        for name in entries:
            info=os.stat(name,dir_fd=parent,follow_symlinks=False)
            if name=='message-bindings':require(stat.S_ISDIR(info.st_mode) and info.st_uid==os.getuid() and stat.S_IMODE(info.st_mode)==0o700,'host_actor_directory_scope')
            else:require(stat.S_ISREG(info.st_mode) and info.st_uid==os.getuid() and info.st_nlink==1 and stat.S_IMODE(info.st_mode)==0o600,'host_actor_directory_scope')


def deliver_reviewed(queue,config,preparation):
    from automation.seedbox_automated_review import approved_plan
    from automation.reviewed_telegram_operator import deliver
    from identity_triage_store import private_path
    from ai_movie_investigator import private_files as guards
    plan,target=approved_plan(queue,preparation)
    actor_directory_scope(config['actor_database'])
    selected=config['sender'];require(selected['kind']=='main_selected_actor_topology_v1' and selected['revision']=='06d17aafefb5a5161364e4bf6f63667a649e1aa3' and selected['sole_edit_writer'] is True and selected['single_serial_pump'] is True and selected['no_original_binding_republication'] is True,'host_sender_selection')
    require(type(selected['observed_at']) in (int,float) and selected['observed_at']<=time.time()<selected['expires_at']<=config['credit_policy']['expires_at'],'host_topology_expired')
    observed=_process(selected['process'])
    require(set(selected['deployed_files'])=={'identity_triage_store.py','identity_triage_intake.py','identity_outcome_outbox.py','identity_triage_observer.py','retry_telegram.py','torrent_research_evidence.py','movie_intel_service.py','deploy/run.py'},'host_sender_closure')
    actor={name:_deployed(pin) for name,pin in selected['deployed_files'].items()}
    # Reuse only the exact frozen existing transaction method, not actor startup.
    cls=next(n for n in ast.parse(actor['identity_outcome_outbox.py']).body if isinstance(n,ast.ClassDef) and n.name=='Outbox')
    method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='tx')
    namespace=dict(contextmanager=contextmanager,private_path=private_path,sqlite3=sqlite3)
    exec(compile(ast.Module(body=[method],type_ignores=[]),'selected-existing-outbox-transaction','exec'),namespace)
    store=types.SimpleNamespace(path=Path(config['actor_database']['path']))
    store.directory=store.path.parent;pin=config['actor_database']
    transactions=[0]
    @contextmanager
    def checked_tx():
        transactions[0]+=1;entered=False
        with private_chain(store.directory) as parent:
            fd=os.open(store.path.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
            try:
                def check():
                    s=os.fstat(fd);require(stat.S_ISREG(s.st_mode) and s.st_uid==os.getuid() and s.st_nlink==1 and stat.S_IMODE(s.st_mode)==0o600 and [s.st_dev,s.st_ino]==pin['identity'] and os.path.samestat(s,store.path.lstat()),'host_sender_database_changed');safe_acl(fd,False)
                check()
                try:
                    with namespace['tx'](store) as c:
                        entered=True
                        require(c.execute('pragma journal_mode').fetchone()[0]=='delete','host_actor_journal_changed')
                        c.execute('pragma trusted_schema=off')
                        check();yield c;check()
                except sqlite3.OperationalError as error:
                    code=getattr(error,'sqlite_errorcode',None)
                    if transactions[0]==1 and not entered and type(code) is int and code&255 in (sqlite3.SQLITE_BUSY,sqlite3.SQLITE_LOCKED):
                        raise _FirstTransactionBusy() from None
                    raise
            finally:os.close(fd)
    store.tx=checked_tx
    environment=read_private(Path(config['source_configuration']['path']),65536)
    require(hashlib.sha256(environment).hexdigest()==config['source_configuration']['sha256'],'host_sender_environment_changed')
    edit=sender(actor,environment);now=time.time()
    auth_denied=[]
    request=edit.__globals__['_telegram_request']
    def observed_request(*args):
        from urllib.error import HTTPError
        try:return request(*args)
        except HTTPError as error:
            if error.code in (401,403):
                from automation.seedbox_circuit import record
                append(record(rows,'telegram','telegram_auth_denied',preparation))
                auth_denied.append(True)
            raise
    edit.__globals__['_telegram_request']=observed_request
    boundary=_HostBoundary(kind='seedbox_sender_boundary_v1',topology_selection_sha256=digest(selected),topology_issued_at=selected['observed_at'],topology_expires_at=selected['expires_at'],process_checked_at=now,reviewed_plan_sha256=digest(plan),observed_at=now,expires_at=min(now+120,selected['expires_at']))
    require(boundary['expires_at']-now>=30,'host_topology_expired')
    original_edit=edit
    def edit(*args):
        # Recheck immediately under the original DB writer lock. The collector
        # may still advance after this check; no production identity is changed.
        _process(selected['process'])
        for name,pin in selected['deployed_files'].items():require(_deployed(pin)==actor[name],'host_actor_code_changed')
        from automation.seedbox_evidence import load,verify_current
        # Evidence was reconstructed before taking the queue lock. Avoid a
        # nested queue transaction inside this sender callback.
        verify_current(queue,preparation,evidence,configuration_sha256)
        require(time.time()+15<boundary['expires_at'],'host_topology_expired')
        return original_edit(*args)
    from automation.seedbox_evidence import load
    evidence=load(queue,preparation)
    with queue.locked() as (rows,append):
        configuration_sha256=rows[0]['configuration_sha256']
        prior=[r for r in rows if r['type']=='seedbox_sender_started_v1' and r['preparation']==preparation]
        # A crash after reservation never causes a second edit. PR204's receipt
        # can be audited independently; no attempt to resend uncertain delivery.
        deferred={r['sender_start_sha256'] for r in rows if r['type']=='seedbox_sender_pre_send_deferred_v1'}
        if any(digest(r) not in deferred for r in prior):return dict(status='uncertain_or_previously_started',resend=False)
        require(len(prior)<3,'host_sender_pre_send_checks_exhausted')
        previous=[r for r in rows if r['type']=='seedbox_sender_pre_send_deferred_v1' and r['preparation']==preparation]
        require(not previous or now>=previous[-1]['at']+60,'host_sender_pre_send_cooldown')
        started=dict(type='seedbox_sender_started_v1',preparation=preparation,plan_sha256=digest(plan),target_sha256=digest(target),process=observed,at=now)
        append(started)
        marker=_ACTIVE.set(dict(queue=queue,rows=rows,boundary=boundary,plan_sha256=digest(plan),deadline=time.monotonic()+120))
        try:
            result=deliver(store,plan,target,config['sources'],boundary,edit,private_guard=vars(guards),clock=time.time)
            return result
        except _FirstTransactionBusy:
            append(dict(type='seedbox_sender_pre_send_deferred_v1',preparation=preparation,sender_start_sha256=digest(started),reason='first_transaction_busy_before_application_reservation_or_sender',at=time.time()))
            raise ValueError('host_sender_pre_send_busy') from None
        finally:_ACTIVE.reset(marker)
