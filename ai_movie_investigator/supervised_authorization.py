"""Ephemeral authority for the sole interactive supervised command.

No JSON/boolean enrollment at the HTTP boundary. Authority exists only while the
command holds its enrolled root transaction. Historical movie disclosure additionally requires its exact owner grant.
"""
from contextlib import contextmanager
from contextvars import ContextVar
import os
import time

from .contracts import Refusal, decode, digest, require, encoded
from .credit_test import request, ledger_total, CONTEXT_TOKENS, TOTAL
from .history import checked, FILENAME
from .responses_protocol import INTEGRATION_SHUTDOWN

_ACTIVE = ContextVar('supervised_synthetic_authority', default=None)
SEND_AUTHORITY_SECONDS = 60
RESPONSE_OBSERVATION_SECONDS = 120
# In-process integration provenance only. Never read from owner/model JSON, CLI
# or environment and never consulted for authorization. Tests replace I/O and
# must explicitly mark that replacement; the production gate stays closed.
_CAPTURED_SIMULATED_IO = ContextVar('captured_simulated_io', default=None)


@contextmanager
def _simulated_captured_io():
    marker=object()
    token=_CAPTURED_SIMULATED_IO.set(marker)
    try:yield
    finally:_CAPTURED_SIMULATED_IO.reset(token)



def _request_value(session,body):
    from .supervised_credit import request_value
    return request_value(body,captured=hasattr(session,'captured'))


class _Permit:
    def __repr__(self):
        return 'SupervisedSyntheticPermit(<opaque>)'


class _Session:
    def __init__(self, root, events, enrolled, selected, slot, credit, history, credential):
        self.root,self.events,self.enrolled=root,events,enrolled
        self.selected,self.slot,self.credit,self.history,self.credential=selected,slot,credit,history,credential
        self.run=f'synthetic-integration-{slot}'
        if slot>=7:
            from .supervised_credit import _standing_attempts
            start=next(s for s,_ in _standing_attempts(events,enrolled) if s['slot']==slot)
            if 'historical' in start:
                self.run=start['historical']['run']
                if start['historical'].get('snapshot_profile') == 'normalized_snapshot_v1':
                    self.snapshot_grant=start['historical']
                    self.snapshot_io_marker=_CAPTURED_SIMULATED_IO.get()
            if 'captured' in start:
                from .new_case import locked_captured
                self.captured=locked_captured(start['captured'])
                self.captured_io_marker=_CAPTURED_SIMULATED_IO.get()
                self.run=start['captured']['run']
        self.issued={}
        self.received=None
        self.captured_receipt=None
        self.snapshot_receipt=None
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
        from .supervised_credit import require_prompted, selection_binding, attempt_pin, expected_request
        self.root.require_write_transaction(self.events)
        if hasattr(self,'captured'):self.captured.validate()
        require(self.events[1] is self.enrolled, 'supervised_enrollment_binding')
        require_prompted(self.root,credential)
        now=self.check_time()
        self.selected.revalidate()
        e=self.selected.data
        validate_evidence(e,now,standing=self.slot>=7)
        require(now<INTEGRATION_SHUTDOWN,'integration_model_retired')
        selection_binding(self.events,self.enrolled,self.selected,self.slot)
        if self.slot>=7:
            from .supervised_credit import _standing_attempts
            grant=next(s for s,_ in _standing_attempts(self.events,self.enrolled) if s['slot']==self.slot).get('historical')
            if grant and 'renewal' in grant:
                from .historical_nano import renewal_history
                renewal_history(self.root,self.events,grant,creating=False)
            if grant and grant.get('snapshot_profile') == 'normalized_snapshot_v1':
                from .snapshot_authorization import active,validate_grant,validate_correction,validate_reassessment
                active().check_root(self.root,self.events,e)
                validate_grant(grant,e['project'])
                if 'correction' in grant:validate_correction(self.root,self.events,grant,creating=False)
                if 'reassessment' in grant:validate_reassessment(self.root,self.events,grant,creating=False)
        require(self.enrolled.get('project')==project==e['project'],'supervised_enrollment_binding')
        require(credential is self.credential,'supervised_credential_binding')
        for h,pin in ((self.root,self.enrolled['root']),(self.credit,self.enrolled['credit']),
                      (self.history,attempt_pin(self.events,self.enrolled,self.slot))):
            info=h.directory.lstat();checked(info,True)
            require([info.st_dev,info.st_ino]==pin,'supervised_storage_changed')
        require(file_identity(self.credit)==self.enrolled['credit_file'],'supervised_storage_changed')
        require(path=='/v1/responses','supervised_endpoint')
        expected=expected_request(self.events,self.enrolled,self.slot)
        require(type(body) is bytes and body==expected,'supervised_request_binding')
        fingerprint=digest(_request_value(self,body))
        reservations=self.credit.read()
        ceiling=reservation_ceiling(self.credit,project,fingerprint)
        if self.slot>=7:
            from .credit_test import retained_total
            require(retained_total(reservations,project)<=ceiling,'credit_total_ceiling')
        else:ledger_total(reservations,project,ceiling=ceiling)
        binding=selected_reservation_binding(self.credit,project,fingerprint)
        selected=[r for r in reservations if all(r.get(k)==v for k,v in binding.items())]
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


    def bind_snapshot_receipt(self,result,answer):
        if not hasattr(self,'snapshot_grant'):return
        from .responses_protocol import parse_response,INTEGRATION_MODEL
        from .supervised_credit import expected_request
        from .snapshot_authorization import active,validate_grant
        active().check_root(self.root,self.events,self.selected.data)
        body=validate_grant(self.snapshot_grant,self.enrolled['project'])
        require(body==expected_request(self.events,self.enrolled,self.slot) and _ACTIVE.get() is self and
                self.snapshot_receipt is None and self.received is result and
                _CAPTURED_SIMULATED_IO.get() is self.snapshot_io_marker, 'snapshot_receipt_unbound')
        wire=decode(body,65536)
        parsed,accounting=parse_response(result.body,wire['text']['format']['schema'],result.request_id,
            expected_model=INTEGRATION_MODEL,http_result=result)
        rows=self.history.read()
        require(parsed==answer and len(rows)==3 and rows[-1]['type']=='bound_send_receipt' and
                rows[-1]['request_sha256']==digest(wire) and rows[-1]['accounting']==accounting and
                result.project==self.enrolled['project'],'snapshot_receipt_unbound')
        self.snapshot_receipt=(answer,digest(rows[-1]))

    def complete_snapshot(self,answer):
        require(_ACTIVE.get() is self and hasattr(self,'snapshot_grant') and self.snapshot_receipt is not None and
                self.snapshot_receipt[0]==answer,'snapshot_receipt_unbound')
        from .snapshot_authorization import report
        return report(self.snapshot_grant,decode(answer),self.history)

    def bind_captured_receipt(self,result,answer):
        if not hasattr(self,'captured'):return
        from .responses_protocol import parse_response,INTEGRATION_MODEL
        from .supervised_credit import expected_request
        self.captured.validate()
        require(_ACTIVE.get() is self and self.captured_receipt is None and self.received is result and
            _CAPTURED_SIMULATED_IO.get() is self.captured_io_marker, 'captured_receipt_unbound')
        body=decode(expected_request(self.events,self.enrolled,self.slot),65536)
        parsed,accounting=parse_response(result.body,body['text']['format']['schema'],result.request_id,
            expected_model=INTEGRATION_MODEL,http_result=result)
        rows=self.history.read()
        require(parsed==answer and len(rows)==3 and rows[-1]['type']=='bound_send_receipt' and
            rows[-1]['request_sha256']==digest(body) and rows[-1]['accounting']==accounting and
            result.project==self.enrolled['project'], 'captured_receipt_unbound')
        self.captured_receipt=(answer,digest(rows[-1]))

    def complete_captured(self,answer):
        require(_ACTIVE.get() is self and hasattr(self,'captured') and self.captured_receipt is not None and
            self.captured_receipt[0]==answer, 'captured_receipt_unbound')
        return self.captured.complete(decode(answer))


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
        session.received=None
        session.captured_receipt=None
        session.snapshot_receipt=None
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


def response_observation_window(token,body,credential,project,path):
    from .supervised_credit import expected_request
    """Observation of one bound synthetic response, never extra send authority."""
    session=_ACTIVE.get()
    if session is None:return None
    session.root.require_write_transaction(session.events)
    require(type(token) is _Permit and token in session.issued and
            session.issued[token]==(path,body,credential,project,True) and
            credential is session.credential and path=='/v1/responses' and
            body==expected_request(session.events,session.enrolled,session.slot) and project==session.enrolled['project'],
            'supervised_observation_binding')
    # HTTP just consumed this exact token after full pre-send validation. The
    # existing pre-connect/pre-POST checks still require unexpired authority.
    return RESPONSE_OBSERVATION_SECONDS



def bind_observed_response(token,result,body,credential,project,path):
    """Bind the actual immutable HTTP result in memory; never persist its body."""
    from .responses_http import HTTPResult
    response_observation_window(token,body,credential,project,path)
    session=_ACTIVE.get()
    require(session is not None and session.received is None and type(result) is HTTPResult and
            result.status==200 and result.project==project and result.path==path and
            result.request_sha256==digest(_request_value(session,body)), 'supervised_observation_binding')
    session.received=result


def response_limits(result,raw,request_id,model):
    """No caller flag/model name grants the larger parser envelope."""
    from .responses_http import MAX_RESPONSE,SYNTHETIC_MAX_RESPONSE
    from .responses_protocol import INTEGRATION_MODEL
    session=_ACTIVE.get()
    if session is None or result is None or result is not session.received:
        return MAX_RESPONSE,16384
    session.root.require_write_transaction(session.events)
    require(model==INTEGRATION_MODEL and raw is result.body and request_id==result.request_id,
            'supervised_observation_binding')
    return SYNTHETIC_MAX_RESPONSE,SYNTHETIC_MAX_RESPONSE


def selected_output_limit(request_hash):
    """Larger generation only for the exact root-locked historical headroom grant."""
    from .responses_protocol import OUTPUT_TOKENS
    from .supervised_credit import expected_request, _standing_attempts
    from .historical_nano import OUTPUT_HEADROOM_PURPOSE, FINAL_CONTRACT_PURPOSE, HISTORICAL_OUTPUT_TOKENS
    session=_ACTIVE.get()
    if session is None:return OUTPUT_TOKENS
    session.root.require_write_transaction(session.events)
    body=expected_request(session.events,session.enrolled,session.slot)
    require(request_hash==digest(_request_value(session,body)),'supervised_request_binding')
    if hasattr(session,'captured'):
        from .new_case import CAPTURED_OUTPUT_TOKENS
        session.captured.validate()
        require(decode(body,65536)['max_output_tokens']==CAPTURED_OUTPUT_TOKENS,'supervised_request_binding')
        return CAPTURED_OUTPUT_TOKENS
    if session.slot>=7:
        grant=next(s for s,_ in _standing_attempts(session.events,session.enrolled) if s['slot']==session.slot).get('historical',{})
        if grant.get('snapshot_profile') == 'normalized_snapshot_v1':
            from .snapshot_authorization import validate_grant
            require(validate_grant(grant,session.enrolled['project'])==body and
                    decode(body,65536)['max_output_tokens']==HISTORICAL_OUTPUT_TOKENS,'snapshot_selection_changed')
            return HISTORICAL_OUTPUT_TOKENS
        if grant.get('renewal',{}).get('authorization',{}).get('purpose')in (OUTPUT_HEADROOM_PURPOSE,FINAL_CONTRACT_PURPOSE):
            require(decode(body)['max_output_tokens']==HISTORICAL_OUTPUT_TOKENS,'supervised_request_binding')
            return HISTORICAL_OUTPUT_TOKENS
    return OUTPUT_TOKENS


def selected_response_contract(request_hash):
    from .controller import INSTRUCTIONS,output_schema
    session=_ACTIVE.get()
    if session is None:return INSTRUCTIONS,output_schema()
    from .supervised_credit import expected_request,_standing_attempts
    from .historical_nano import FINAL_CONTRACT_VERSION,final_contract
    session.root.require_write_transaction(session.events)
    body=expected_request(session.events,session.enrolled,session.slot)
    require(request_hash==digest(_request_value(session,body)),'supervised_request_binding')
    if hasattr(session,'captured'):
        session.captured.validate()
        selected=decode(body,65536)
        return selected['instructions'],selected['text']['format']['schema']
    if session.slot>=7:
        grant=next(s for s,_ in _standing_attempts(session.events,session.enrolled) if s['slot']==session.slot).get('historical',{})
        if grant.get('snapshot_profile') == 'normalized_snapshot_v1':
            from .snapshot_authorization import validate_grant
            selected=decode(validate_grant(grant,session.enrolled['project']),65536)
            return selected['instructions'],selected['text']['format']['schema']
        if grant.get('response_contract')==FINAL_CONTRACT_VERSION:return final_contract(grant['run'])
    return INSTRUCTIONS,output_schema()



def selected_snapshot_request(selected,body):
    """Match only the live trusted-main snapshot grant under the root lock."""
    session=_ACTIVE.get()
    if session is None or session.slot < 7:
        return False
    from .supervised_credit import _standing_attempts
    session.root.require_write_transaction(session.events)
    start=next(s for s,_ in _standing_attempts(session.events,session.enrolled) if s['slot']==session.slot)
    grant=start.get('historical',{})
    if grant.get('snapshot_profile') != 'normalized_snapshot_v1':
        return False
    from .snapshot_authorization import active,validate_grant
    active().check_root(session.root,session.events,session.selected.data)
    require(validate_grant(grant,session.enrolled['project'])==body and selected['run']==grant['run'] and
            selected['case']==grant['case'] and selected['request_sha256']==digest(decode(body,65536)),
            'snapshot_selection_changed')
    return True


def selected_captured_request(selected,body):
    session=_ACTIVE.get()
    require(session is not None and hasattr(session,'captured'), 'captured_lock_required')
    expected=session.captured.validate()
    require(body==expected and selected['run']==session.run and
        selected['case']==session.captured.grant['case'], 'captured_selection_changed')
    return True


def consume_captured_completion(held,answer):
    session=_ACTIVE.get()
    require(session is not None and getattr(session,'captured',None) is held and
        session.captured_receipt is not None and session.captured_receipt[0]==encoded(answer),
        'captured_receipt_unbound')
    require(_CAPTURED_SIMULATED_IO.get() is session.captured_io_marker, 'captured_receipt_unbound')
    proof=dict(receipt_hash=session.captured_receipt[1],simulated=session.captured_io_marker is not None)
    session.captured_receipt=None # consumed even if validation/draft persistence fails
    return proof


def consume_snapshot_completion(grant,answer):
    session=_ACTIVE.get()
    require(session is not None and getattr(session,'snapshot_grant',None)==grant and
            session.snapshot_receipt is not None and session.snapshot_receipt[0]==encoded(answer) and
            _CAPTURED_SIMULATED_IO.get() is session.snapshot_io_marker,'snapshot_receipt_unbound')
    proof=dict(receipt_hash=session.snapshot_receipt[1],simulated=session.snapshot_io_marker is not None)
    session.snapshot_receipt=None
    return proof


def bind_snapshot_receipt(result,answer):
    session=_ACTIVE.get()
    if session is not None:session.bind_snapshot_receipt(result,answer)


def bind_captured_receipt(result,answer):
    session=_ACTIVE.get()
    if session is not None:session.bind_captured_receipt(result,answer)


def response_output_limit(result):
    from .responses_protocol import OUTPUT_TOKENS
    session=_ACTIVE.get()
    if session is None or result is None or result is not session.received:return OUTPUT_TOKENS
    return selected_output_limit(result.request_sha256)


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
    except Refusal as error:
        # Preserve only existing literal diagnostic codes. Unknown/subclassed
        # refusals stay generic; exception text never crosses this boundary.
        from .supervised_credit import safe_reason
        reason=safe_reason(error)
        return reason if reason!='unexpected_exception' else 'supervised_authorization_refused'
    except OSError:
        return 'supervised_authorization_io_error'
    except TypeError:
        return 'supervised_authorization_type_error'
    except KeyError:
        return 'supervised_authorization_key_error'
    except ValueError:
        return 'supervised_authorization_value_error'



def selected_reservation_binding(history,project,request_hash):
    session=_ACTIVE.get()
    if session is None or not hasattr(session,'captured') or not any(k in session.captured.grant['authorization'] for k in ('continuation','completion_correction','prose_correction')):
        return dict(request_hash=request_hash)
    from .supervised_credit import _standing_attempts,reservation_binding
    session.captured.validate()
    require(history is session.credit and project==session.enrolled['project'],'supervised_recovery_binding')
    start=next(s for s,_ in _standing_attempts(session.events,session.enrolled) if s['slot']==session.slot)
    require(start['captured']==session.captured.grant and start['request_sha256']==request_hash,'supervised_request_binding')
    return reservation_binding(start)

def reservation_ceiling(history,project,request_hash):
    """Only a root-locked selected manual session can exceed the normal five cents."""
    session=_ACTIVE.get()
    if session is not None and session.slot>=7:
        from .supervised_credit import standing_retained,require_prompted,expected_request
        session.root.require_write_transaction(session.events)
        require(history is session.credit and project==session.enrolled['project'] and
                request_hash==digest(_request_value(session,expected_request(session.events,session.enrolled,session.slot))),'supervised_recovery_binding')
        require_prompted(session.root,session.credential)
        ceiling=standing_retained(session.root,session.events,session.enrolled,session.selected,history,session.slot)
        session.check_time()
        return ceiling
    if session is None or session.slot not in (3,4,5,6):return TOTAL
    from .supervised_credit import recovery_retained, selection_binding, require_prompted, validate_evidence
    session.root.require_write_transaction(session.events)
    require(session.events[1] is session.enrolled and history is session.credit and
            project==session.enrolled['project'] and request_hash==digest(decode(request(session.run))),
            'supervised_recovery_binding')
    require_prompted(session.root,session.credential)
    session.selected.revalidate()
    validate_evidence(session.selected.data,session.check_time())
    selection_binding(session.events,session.enrolled,session.selected,session.slot)
    ceiling=recovery_retained(session.root,session.events,session.enrolled,session.selected,history,session.slot)
    session.check_time()
    return ceiling


# Diagnostic state has no authority and is never consulted for admission.
_DIAGNOSTIC = ContextVar('supervised_diagnostic', default=None)
_PHASES = frozenset(('preflight slot_started request_validation attempt_recording '
    'credit_reservation wire_authorization http_setup tls_setup dns_lookup socket_connect '
    'tls_handshake http_send http_receive http_response_received http_body_read '
    'http_body_received response_parsing receipt_validation receipt_recording '
    'receipt_recorded captured_result_validation historical_alias_validation historical_result_validation historical_report_preparation completion_recording completed').split())


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
