"""Ephemeral authority for the sole interactive fixed-synthetic command.

No JSON/boolean enrollment at the HTTP boundary. Authority exists only while the
command holds its enrolled root transaction. It is not unattended/movie access.
"""
from contextlib import contextmanager
from contextvars import ContextVar
import os
import time

from .contracts import Refusal, decode, digest, require
from .credit_test import request, count_request
from .history import checked, FILENAME
from .responses_protocol import INTEGRATION_SHUTDOWN

_ACTIVE = ContextVar('supervised_synthetic_authority', default=None)


class _Permit:
    def __repr__(self):
        return 'SupervisedSyntheticPermit(<opaque>)'


class _Session:
    def __init__(self, root, events, enrolled, selected, slot, credit, history, credential):
        self.root,self.events,self.enrolled=root,events,enrolled
        self.selected,self.slot,self.credit,self.history,self.credential=selected,slot,credit,history,credential
        self.run=f'synthetic-integration-{slot}'
        self.issued={}
        self.last_wall=time.time()
        self.started_wall=self.last_wall
        self.started_monotonic=time.monotonic()

    def check(self,path,body,credential,project):
        from .supervised_credit import validate_evidence, file_identity
        from .supervised_credit import require_prompted
        self.root.require_write_transaction(self.events)
        require(self.events[1] is self.enrolled, 'supervised_enrollment_binding')
        require_prompted(self.root,credential)
        wall=time.time()
        require(wall>=self.last_wall, 'supervised_clock_rollback')
        self.last_wall=wall
        now=max(wall,self.root.clock(),self.started_wall+time.monotonic()-self.started_monotonic)
        self.selected.revalidate()
        e=self.selected.data
        validate_evidence(e,now)
        require(now<INTEGRATION_SHUTDOWN,'integration_model_retired')
        require(self.enrolled.get('evidence_sha256')==self.selected.sha256 and
                self.enrolled.get('project')==project==e['project'],'supervised_enrollment_binding')
        require(credential is self.credential,'supervised_credential_binding')
        for h,pin in ((self.root,self.enrolled['root']),(self.credit,self.enrolled['credit']),
                      (self.history,self.enrolled['attempts'][str(self.slot)])):
            info=h.directory.lstat();checked(info,True)
            require([info.st_dev,info.st_ino]==pin,'supervised_storage_changed')
        require(file_identity(self.credit)==self.enrolled['credit_file'],'supervised_storage_changed')
        require(path in ('/v1/responses/input_tokens','/v1/responses'),'supervised_endpoint')
        expected=count_request(self.run) if path.endswith('/input_tokens') else request(self.run)
        require(type(body) is bytes and body==expected,'supervised_request_binding')
        fingerprint=digest(decode(body))
        reservations=self.credit.read()
        require(1<=len(reservations)<=5 and all(r['type']=='credit_test_reserved' and
                r['project']==project and r['reserved_usd']==[1,100] for r in reservations) and
                sum(r['request_hash']==fingerprint for r in reservations)==1,'supervised_reservation_required')
        rows=[r for r in self.events if r.get('slot')==self.slot]
        require(len([r for r in rows if r['type']=='supervised_started'])==1 and
                not any(r['type']=='supervised_completed' for r in rows),'supervised_attempt_consumed')
        attempted=[r for r in rows if r['type']=='supervised_count_attempted']
        require(len(attempted)==1 and attempted[0]['request_hash']==digest(decode(count_request(self.run))),
                'supervised_count_not_reserved')
        counts=[r for r in rows if r['type']=='supervised_count_observed']
        if path.endswith('/input_tokens'):
            require(not counts,'supervised_count_consumed')
        else:
            require(len(counts)==1 and counts[0]['receipt']['generation_sha256']==fingerprint and
                    counts[0]['receipt']['project']==project,'supervised_count_binding')
            local=self.history.read()
            require(len(local)==2 and local[0]['type']=='bound_send_reserved' and
                    local[1]['type']=='bound_send_attempted','supervised_generation_not_reserved')
            permit=local[0]['permit']
            require(permit['selection']['run']==self.run and permit['selection']['request_sha256']==fingerprint and
                    permit['project']==project and permit['maximum_debit']==[1,100] and
                    permit['input_limit']==counts[0]['receipt']['input_tokens'],'supervised_generation_binding')


@contextmanager
def command_authority(root,events,enrolled,selected,slot,credit,history,credential):
    from .supervised_credit import SelectedEvidence, require_prompted
    root.require_write_transaction(events)
    require(len(events)>1 and events[1] is enrolled, "supervised_enrollment_binding")
    require_prompted(root,credential)
    require(type(selected) is SelectedEvidence and _ACTIVE.get() is None,'supervised_operator_boundary')
    selected.revalidate()
    require(enrolled.get('evidence_sha256')==selected.sha256 and enrolled.get('project')==selected.data['project'],
            'supervised_enrollment_binding')
    session=_Session(root,events,enrolled,selected,slot,credit,history,credential)
    marker=_ACTIVE.set(session)
    try:yield
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
