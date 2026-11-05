"""Ephemeral authority for the sole interactive fixed-synthetic command.

No JSON/boolean enrollment at the HTTP boundary. Authority exists only while the
command holds its enrolled root transaction. It is not unattended/movie access.
"""
from contextlib import contextmanager
from contextvars import ContextVar
import os
import time

from .contracts import Refusal, decode, digest, require
from .credit_test import request, ledger_total, CONTEXT_TOKENS, TOTAL
from .history import checked, FILENAME
from .responses_protocol import INTEGRATION_SHUTDOWN

_ACTIVE = ContextVar('supervised_synthetic_authority', default=None)
SEND_AUTHORITY_SECONDS = 60


class _Permit:
    def __repr__(self):
        return 'SupervisedSyntheticPermit(<opaque>)'


class _Session:
    def __init__(self, root, events, enrolled, selected, slot, credit, history, credential):
        self.root,self.events,self.enrolled=root,events,enrolled
        self.selected,self.slot,self.credit,self.history,self.credential=selected,slot,credit,history,credential
        self.run=f'synthetic-integration-{slot}'
        self.issued={}
        from .supervised_credit import require_prompted
        self.started_wall,self.started_monotonic=require_prompted(root,credential)
        self.last_wall=self.started_wall
        self.expired=False
        self.deadline=min(self.started_wall+SEND_AUTHORITY_SECONDS,selected.data['expires_at'],
                          selected.data['credit_expires_at'],INTEGRATION_SHUTDOWN)

    def check_time(self):
        require(not self.expired,'supervised_session_expired')
        wall=time.time();elapsed=time.monotonic()-self.started_monotonic
        require(wall>=self.last_wall and elapsed>=0,'supervised_clock_rollback')
        self.last_wall=wall
        now=max(wall,self.root.clock(),self.started_wall+elapsed)
        if now>=self.deadline:self.expired=True
        require(not self.expired,'supervised_session_expired')
        return now

    def check(self,path,body,credential,project):
        from .supervised_credit import validate_evidence, file_identity
        from .supervised_credit import require_prompted, selection_binding, attempt_pin
        self.root.require_write_transaction(self.events)
        require(self.events[1] is self.enrolled, 'supervised_enrollment_binding')
        require_prompted(self.root,credential)
        now=self.check_time()
        self.selected.revalidate()
        e=self.selected.data
        validate_evidence(e,now)
        require(now<INTEGRATION_SHUTDOWN,'integration_model_retired')
        selection_binding(self.events,self.enrolled,self.selected,self.slot)
        require(self.enrolled.get('project')==project==e['project'],'supervised_enrollment_binding')
        require(credential is self.credential,'supervised_credential_binding')
        for h,pin in ((self.root,self.enrolled['root']),(self.credit,self.enrolled['credit']),
                      (self.history,attempt_pin(self.events,self.enrolled,self.slot))):
            info=h.directory.lstat();checked(info,True)
            require([info.st_dev,info.st_ino]==pin,'supervised_storage_changed')
        require(file_identity(self.credit)==self.enrolled['credit_file'],'supervised_storage_changed')
        require(path=='/v1/responses','supervised_endpoint')
        expected=request(self.run)
        require(type(body) is bytes and body==expected,'supervised_request_binding')
        fingerprint=digest(decode(body))
        reservations=self.credit.read()
        ledger_total(reservations,project,ceiling=reservation_ceiling(self.credit,project,fingerprint))
        selected=[r for r in reservations if r['request_hash']==fingerprint]
        require(len(selected)==1 and selected[0]['reserved_usd']==[3,100],'supervised_reservation_required')
        rows=[r for r in self.events if r.get('slot')==self.slot]
        require(len([r for r in rows if r['type']=='supervised_started'])==1 and
                not any(r['type']=='supervised_completed' for r in rows),'supervised_attempt_consumed')
        require(not any(r['type'] in ('supervised_count_attempted','supervised_count_observed') for r in rows),
                'supervised_attempt_consumed')
        local=self.history.read()
        require(len(local)==2 and local[0]['type']=='bound_send_reserved' and
                local[1]['type']=='bound_send_attempted','supervised_generation_not_reserved')
        permit=local[0]['permit']
        require(permit['selection']['run']==self.run and permit['selection']['request_sha256']==fingerprint and
                permit['project']==project and permit['maximum_debit']==[3,100] and
                permit['input_limit']==CONTEXT_TOKENS,'supervised_generation_binding')
        self.check_time() # Metadata/ledger checks must not outlive prompt authority.


@contextmanager
def command_authority(root,events,enrolled,selected,slot,credit,history,credential):
    from .supervised_credit import SelectedEvidence, require_prompted, selection_binding, attempt_pin
    root.require_write_transaction(events)
    require(len(events)>1 and events[1] is enrolled, "supervised_enrollment_binding")
    require_prompted(root,credential)
    require(type(selected) is SelectedEvidence and _ACTIVE.get() is None,'supervised_operator_boundary')
    selected.revalidate()
    selection_binding(events,enrolled,selected,slot)
    session=_Session(root,events,enrolled,selected,slot,credit,history,credential)
    session.check_time()
    marker=_ACTIVE.set(session)
    try:yield session
    finally:
        session.issued.clear()
        _ACTIVE.reset(marker)


def authorization_for(path,body,credential,project,fallback=None):
    session=_ACTIVE.get()
    if session is None:return fallback
    session.check(path,body,credential,project)
    require(not any(row[0]==path for row in session.issued.values()),'supervised_wire_consumed')
    token=_Permit()
    session.issued[token]=(path,body,credential,project,False)
    return token


def refusal(token,*,body=None,credential=None,project=None,path=None,consume=True):
    session=_ACTIVE.get()
    if type(token) is not _Permit or session is None or token not in session.issued:
        return 'responses_real_authorization_unimplemented'
    try:
        old_path,old_body,old_credential,old_project,used=session.issued[token]
        require(path==old_path and body==old_body and credential is old_credential and project==old_project,
                'supervised_wire_binding')
        require(not used if consume else used,'supervised_wire_consumed')
        session.check(path,body,credential,project)
        session.issued[token]=(path,body,credential,project,True)
        return None
    except (Refusal,OSError,ValueError,TypeError,KeyError):
        return 'supervised_authorization_refused'


def reservation_ceiling(history,project,request_hash):
    """Only an active root-locked manual slot3 can exceed the normal five cents."""
    session=_ACTIVE.get()
    if session is None or session.slot!=3:return TOTAL
    from .supervised_credit import recovery_retained, selection_binding, require_prompted, validate_evidence
    session.root.require_write_transaction(session.events)
    require(session.events[1] is session.enrolled and history is session.credit and
            project==session.enrolled['project'] and request_hash==digest(decode(request(session.run))),
            'supervised_recovery_binding')
    require_prompted(session.root,session.credential)
    session.selected.revalidate()
    validate_evidence(session.selected.data,session.check_time())
    selection_binding(session.events,session.enrolled,session.selected,3)
    ceiling=recovery_retained(session.root,session.events,session.enrolled,session.selected,history)
    session.check_time()
    return ceiling


# Diagnostic state has no authority and is never consulted for admission.
_DIAGNOSTIC = ContextVar('supervised_diagnostic', default=None)
_PHASES = frozenset(('preflight slot_started request_validation attempt_recording '
    'credit_reservation wire_authorization http_setup tls_setup dns_lookup socket_connect '
    'tls_handshake http_send http_receive http_response_received http_body_read '
    'http_body_received response_parsing receipt_validation receipt_recording '
    'receipt_recorded completion_recording completed').split())


@contextmanager
def diagnostic_scope():
    state={'phase':'preflight'}
    token=_DIAGNOSTIC.set(state)
    try:yield state
    finally:_DIAGNOSTIC.reset(token)


def observe_phase(phase):
    require(phase in _PHASES,'supervised_diagnostic_phase')
    state=_DIAGNOSTIC.get()
    if state is not None:state['phase']=phase


def diagnostic_phase():
    state=_DIAGNOSTIC.get()
    return state['phase'] if state is not None else None
