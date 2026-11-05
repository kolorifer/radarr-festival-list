"""One supervised fixed-synthetic command with ephemeral interactive authority.

No automatic enrollment, retry, reset, credential discovery or movie inputs.
Operator evidence pins are correspondence, never live authentication by themselves.
"""
from contextlib import contextmanager
from contextvars import ContextVar
import argparse
import getpass
import hashlib
import os
from pathlib import Path
import sys
import time
import warnings

from .bound_send import HistoricalDiagnosticParent, OperatorContext
from .contracts import Refusal, decode, digest, encoded, require, shape, stamp
from .credit_test import POLICY, PER_REQUEST, CONTEXT_TOKENS, CONTEXT_COVERAGE, INPUT_RATE, OUTPUT_RATE, request, ledger_total, TOTAL
from .history import History, FILENAME, checked
from .responses_http import ExplicitCredential, headers
from .responses_protocol import INTEGRATION_MODEL, OUTPUT_TOKENS
from .responses_transport import ResponsesTransport
from .supervised_authorization import command_authority, diagnostic_scope, diagnostic_phase, observe_phase
from .spending import rational
from .private_files import read_private

_PROMPTED = ContextVar("supervised_prompted_credential", default=None)
ACCOUNT_EVIDENCE_SECONDS = 900


# Finite literal codes only; arbitrary exceptions and remote values are excluded.
_SAFE_REASON_GROUPS = {
    'transport_refused': frozenset((
        'responses_observation_profile responses_observation_transition '
        'responses_setup_deadline_exceeded responses_observation_deadline_exceeded '
        'responses_cleanup_failed '
        'responses_body_limit responses_body_truncated responses_credential_invalid responses_deadline '
        'responses_deadline_exceeded responses_dns_failed responses_http_rejected responses_http_shape '
        'responses_network_completion_unknown responses_network_denied responses_path_denied responses_peer_changed '
        'responses_project_invalid responses_request_size responses_timer_busy responses_timer_unavailable '
        'responses_tls_required responses_tls_roots_unavailable simulation_credential_required simulation_response_invalid '
        'simulation_response_missing '
    ).split()),
    'protocol_refused': frozenset((
        'responses_action_or_output_denied responses_answer_count responses_answer_schema responses_cache_or_tier_changed '
        'responses_cache_partition responses_contract_changed responses_identity_invalid responses_model_profile '
        'responses_not_completed responses_output_shape responses_reasoning_shape responses_text_required '
        'responses_unsupported_shape responses_usage_invalid responses_usage_limit responses_usage_required '
    ).split()),
    'binding_refused': frozenset((
        'supervised_observation_binding '
        'binding_attempt_consumed binding_authority binding_body binding_debit '
        'binding_expired binding_history binding_history_changed binding_model '
        'binding_parent_refused binding_project binding_receipt_refused binding_response_unknown '
        'binding_tokens binding_usage_unknown credit_history_missing credit_parent_required '
        'credit_pricing_changed credit_project_changed credit_result_binding credit_scope_or_model_expired '
        'credit_synthetic_input_required credit_synthetic_result integration_model_retired model_transport_disabled '
        'operator_account_unknown operator_authority_stale operator_context_missing operator_context_pin '
        'operator_coverage_above_cap operator_coverage_unknown operator_credential_disclosed operator_credential_echo '
        'operator_credential_route_changed operator_disclosure_changed operator_evidence_missing operator_evidence_pin '
        'operator_evidence_stale operator_evidence_unknown operator_expanded_disclosure_unpinned operator_expanded_observations '
        'operator_historical_qualification operator_history_changed operator_limits_unknown operator_owner_authority_missing '
        'operator_permit_changed operator_pricing_unknown operator_privacy_missing operator_receipt_correlation '
        'operator_receipt_mismatch operator_receipt_unbound operator_request_changed operator_request_policy '
        'operator_route_missing operator_selection_changed responses_authorization_stale responses_bound_mode_conflict '
        'responses_completion_unknown_or_rejected responses_credential_echo_refused responses_credential_in_input responses_deadline '
        'responses_deadline_exceeded responses_decisions_changed responses_history_binding responses_http_rejected '
        'responses_input_protocol responses_pending_request responses_request_already_consumed responses_request_size '
        'responses_reservation_required responses_reserved_input_changed responses_retained_evidence_changed responses_schema_unsupported '
        'responses_selected_input_changed simulation_credential_required supervised_attempt_consumed supervised_clock_rollback '
        'supervised_credential_binding supervised_diagnostic_phase supervised_endpoint supervised_enrollment_binding '
        'supervised_generation_binding supervised_generation_not_reserved supervised_operator_boundary supervised_recovery_binding '
        'supervised_request_binding supervised_reservation_required supervised_session_expired supervised_storage_changed '
        'supervised_wire_binding supervised_wire_consumed '
    ).split()),
    'validation_refused': frozenset((
        'case_id claims credit_budget_changed credit_clock_rollback '
        'credit_count_correlation credit_count_invalid credit_file_identity credit_history_missing '
        'credit_input_bound credit_project credit_request_ceiling credit_request_consumed '
        'credit_total_ceiling decision_evidence decision_evidence_hashes decision_kind '
        'decision_limit decision_revision decision_supersession decision_target '
        'decision_time delivery_id duplicate_decision_id duplicate_evidence_id '
        'event_hash_changed event_mismatch evidence_expiry evidence_kind '
        'evidence_limit facts_schema hash hash_basis '
        'identifier images imdb input_limit '
        'integration_model_retired invalid_json legacy_occurrence_invented legacy_route '
        'outcome_codes outcome_schema packet_version quarantined_outcome '
        'release_fields responses_credential_invalid route schema '
        'size_limit source_basis source_case_mismatch spending_binding_changed '
        'spending_budget_changed spending_case_changed spending_ceiling spending_clock_or_expiry '
        'spending_counter_limit spending_history spending_policy_unknown spending_previous_charge_unknown '
        'spending_rational spending_receipt_changed spending_request_changed spending_request_consumed '
        'spending_request_limit spending_response_consumed spending_send_binding spending_send_consumed '
        'spending_send_missing spending_send_sequence spending_settlement_sequence spending_usage_exceeds_reservation '
        'supervised_attempt_consumed supervised_credential_disclosed supervised_credit_only supervised_enrollment_binding '
        'supervised_enrollment_exists supervised_evidence_changed supervised_evidence_missing supervised_evidence_selection '
        'supervised_evidence_stale supervised_interactive_terminal_required supervised_model_pricing_unknown supervised_not_enrolled '
        'supervised_project supervised_prompt_required supervised_reauthorization_binding supervised_reauthorization_evidence '
        'supervised_reauthorization_state supervised_reauthorization_uncertain supervised_recovery_binding supervised_recovery_evidence '
        'supervised_recovery_state supervised_root_changed supervised_slot supervised_storage_changed '
        'timestamp tmdb trusted_issuers unsafe_text '
        'year '
    ).split()),
    'storage_refused': frozenset((
        'acl_unsupported decision_history_omitted decision_revision_conflict decision_revocation_rollback '
        'history_busy history_capacity history_directory_changed history_file_changed '
        'history_file_identity_changed history_file_missing history_incomplete_tail history_integrity '
        'history_read_only history_schema history_transaction_changed history_transaction_required '
        'history_write_failed immutable_event_conflict invocation_already_consumed invocation_missing '
        'lookup_budget model_call_budget model_reservation_sequence model_send_consumed '
        'model_send_unbound packet_changed parent_changed previous_model_attempt_unknown '
        'research_completion_unbound research_dependency_binding_changed research_dependency_invalid research_dependency_missing '
        'research_derived_input_changed research_detail_not_returned research_input_ambiguous_or_missing research_original_unbound '
        'research_plan_changed research_plan_revoked research_plan_unbound research_receipt_binding_changed '
        'research_receipt_missing_or_ambiguous research_receipt_reservation_unbound research_receipts_incomplete result_immutable '
        'selected_case_superseded storage_acl storage_acl_unsupported supervised_handoff_already_consumed '
        'unknown_job unsafe_history_path unsafe_history_permissions unsafe_packet '
        'unsafe_parent '
    ).split()),
}


def safe_reason(error):
    code=error.args[0] if type(error) is Refusal and len(error.args)==1 and type(error.args[0]) is str else None
    return code if any(code in codes for codes in _SAFE_REASON_GROUPS.values()) else "unexpected_exception"


def refusal_category(error):
    # Exact static membership only: never echo an exception, path or input.
    code=error.args[0] if type(error) is Refusal and len(error.args)==1 and type(error.args[0]) is str else None
    groups={
        'evidence_expired_or_invalid_window':('supervised_evidence_stale',),
        'evidence_changed':('supervised_evidence_changed','packet_changed'),
        'session_expired':('supervised_session_expired','binding_expired','operator_authority_stale'),
        'clock_changed':('supervised_clock_rollback',),
        'privacy_or_storage_refused':('unsafe_parent','unsafe_packet','unsafe_history_path','storage_acl',
            'storage_acl_unsupported','acl_unsupported','parent_changed','supervised_storage_changed','supervised_root_changed'),
        'state_or_binding_refused':('supervised_not_enrolled','supervised_enrollment_binding','supervised_attempt_consumed',
            'supervised_enrollment_exists','supervised_reauthorization_state','supervised_reauthorization_binding',
            'supervised_reauthorization_uncertain','supervised_reauthorization_evidence',
            'supervised_recovery_state','supervised_recovery_binding','supervised_recovery_evidence'),
        'credit_limit_refused':('credit_total_ceiling','supervised_credit_only'),
        'interactive_input_refused':('supervised_interactive_terminal_required','supervised_prompt_required'),
        'credential_format_invalid':('responses_credential_invalid',),
        'http_rejected':('responses_http_rejected',),
        'network_outcome_unknown':('responses_network_completion_unknown',),
        'local_deadline_outcome_unknown':('responses_setup_deadline_exceeded','responses_observation_deadline_exceeded'),
        'send_or_response_refused':('supervised_authorization_refused','responses_real_authorization_unimplemented',
            'binding_response_unknown','binding_usage_unknown','binding_receipt_refused'),
    }
    for category,codes in groups.items():
        if code in codes:return category
    for category,codes in _SAFE_REASON_GROUPS.items():
        if code in codes:return category
    if isinstance(error,(EOFError,getpass.GetPassWarning,KeyboardInterrupt)):return 'interactive_input_cancelled'
    if isinstance(error,OSError):return 'io_refused'
    return 'unclassified_refusal'


@contextmanager
def interactive_credential(root):
    credential = prompt_credential()
    marker = _PROMPTED.set((root, credential,time.time(),time.monotonic()))
    try:
        yield credential
    finally:
        _PROMPTED.reset(marker)


def require_prompted(root, credential):
    selected = _PROMPTED.get()
    require(selected is not None and selected[0] is root and selected[1] is credential,
            "supervised_prompt_required")
    return selected[2:]


def file_identity(history):
    p=history.directory / FILENAME
    info=p.lstat(); checked(info)
    return [info.st_dev,info.st_ino]


def enroll(directory, selected=None):
    if selected is not None:
        require(type(selected) is SelectedEvidence,'supervised_evidence_selection')
        selected.revalidate()
        validate_evidence(selected.data,time.time())
    root=History(Path(directory))
    with root.transaction(write=True) as (events,append):
        require(not events, 'supervised_enrollment_exists')
        append(dict(type='supervised_enrollment_started',at=root.clock()))
        for name in ('credit','attempt-1','attempt-2'):
            (root.directory/name).mkdir(mode=0o700)
        credit=History(root.directory/'credit')
        with credit.transaction(write=True):pass
        append(dict(type='supervised_enrolled', root=list(root.identity),
            credit=list(credit.identity),credit_file=file_identity(credit),
            attempts={str(n):list(History(root.directory/f'attempt-{n}').identity) for n in (1,2)},
            evidence_sha256=selected.sha256 if selected else None,
            project=selected.data['project'] if selected else None))


def _read_evidence(path):
    path=Path(path)
    before=path.lstat()
    raw=read_private(path,16384)
    after=path.lstat()
    identity=lambda info:(info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns)
    require(identity(before)==identity(after),'supervised_evidence_changed')
    # Persistent selection binds bytes and dev/inode/size/mtime. ctime is a
    # per-read race check, not proof against same-owner change-and-restore.
    return raw,identity(after)[:4]


_EVIDENCE_READER = object()


class SelectedEvidence:
    __slots__=('path','raw','identity','sha256')
    def __init__(self,path,raw,identity,reader):
        require(reader is _EVIDENCE_READER,'supervised_evidence_selection')
        self.path,self.raw,self.identity=Path(path),raw,identity
        self.sha256=hashlib.sha256(raw).hexdigest()
    @property
    def data(self):return decode(self.raw,16384)
    def revalidate(self):
        raw,identity=_read_evidence(self.path)
        require(raw==self.raw and identity==self.identity,'supervised_evidence_changed')


def read_evidence(path):
    raw,identity=_read_evidence(path)
    decode(raw,16384)
    return SelectedEvidence(path,raw,identity,_EVIDENCE_READER)


def validate_evidence(e,now):
    shape(e,'project account_reference observed_at expires_at credit_expires_at available_usd '
          'billing_reference paid_fallback owner_reference model policy context_window pricing_reference context_reference model_access_reference input_rate cached_input_rate output_rate')
    require(isinstance(e['project'],str) and e['project'].startswith('proj_'),'supervised_project')
    require(stamp(e['observed_at'])<=now<stamp(e['expires_at'])<=stamp(e['credit_expires_at']) and
            e['expires_at']-e['observed_at']<=ACCOUNT_EVIDENCE_SECONDS,'supervised_evidence_stale')
    require(rational(e['available_usd'])>=rational([5,100]) and e['paid_fallback'] is False,
            'supervised_credit_only')
    for name in ('account_reference','billing_reference','owner_reference','pricing_reference','context_reference','model_access_reference'):
        require(isinstance(e[name],str) and 1<=len(e[name])<=300 and e[name]!='unknown','supervised_evidence_missing')
    require(e['model']==INTEGRATION_MODEL and e['policy']==POLICY and type(e['context_window']) is int and
            e['context_window']==CONTEXT_TOKENS and rational(e['input_rate'])==INPUT_RATE and
            rational(e['cached_input_rate'])==INPUT_RATE/10 and rational(e['output_rate'])==OUTPUT_RATE,
            'supervised_model_pricing_unknown')


def selection_binding(events,enrolled,selected,slot):
    """Resolve one manual renewal without replacing enrollment or old slots."""
    require(enrolled.get('project')==selected.data['project'],'supervised_enrollment_binding')
    if slot in (3,4,5):
        recovery_binding(events,enrolled,selected,slot)
        return
    require(not any(e['type'].startswith('supervised_recovery') for e in events),
            'supervised_attempt_consumed')
    renewals=[e for e in events if e.get('type')=='supervised_reauthorized']
    if not renewals:
        require(enrolled.get('evidence_sha256')==selected.sha256,'supervised_enrollment_binding')
        return
    require(len(renewals)==1 and len(events)>=4 and events[3] is renewals[0],
            'supervised_reauthorization_binding')
    renewal=renewals[0]
    shape(renewal,'type at previous_sha256 evidence_sha256 project expires_at prefix_sha256 permitted_slot')
    require(slot==2 and type(renewal['permitted_slot']) is int and renewal['permitted_slot']==2 and
            renewal['previous_sha256']==enrolled['evidence_sha256'] and
            renewal['evidence_sha256']==selected.sha256 and
            renewal['project']==enrolled['project'] and
            renewal['expires_at']==selected.data['expires_at'] and
            renewal['prefix_sha256']==digest(events[:3]) and
            events[2].get('type')=='supervised_started' and events[2].get('slot')==1 and
            selected.data['observed_at']<=stamp(renewal['at'])<renewal['expires_at'],
            'supervised_reauthorization_binding')


def reauthorize(directory,previous,selected):
    """Append once for unused slot2 only when slot1 provably never reserved."""
    require(type(previous) is SelectedEvidence and type(selected) is SelectedEvidence,
            'supervised_evidence_selection')
    previous.revalidate();selected.revalidate()
    old,new=previous.data,selected.data
    now=time.time()
    validate_evidence(old,stamp(old['observed_at'])) # Retained facts, not fresh authority.
    validate_evidence(new,now)
    require(previous.path!=selected.path and previous.identity[:2]!=selected.identity[:2] and
            previous.sha256!=selected.sha256 and old['project']==new['project'] and
            old['expires_at']<=new['observed_at']<=now,'supervised_reauthorization_evidence')
    root=History(Path(directory))
    with root.transaction(write=True) as (events,append):
        require(len(events)==3 and events[0].get('type')=='supervised_enrollment_started' and
                events[1].get('type')=='supervised_enrolled','supervised_reauthorization_state')
        enrolled=events[1];started=events[2]
        shape(started,'type slot at evidence_hash')
        require(started['type']=='supervised_started' and type(started['slot']) is int and started['slot']==1 and
                started['evidence_hash']==digest(old) and old['observed_at']<=stamp(started['at'])<old['expires_at'],
                'supervised_reauthorization_state')
        require(enrolled['root']==list(root.identity),'supervised_root_changed')
        selection_binding(events,enrolled,previous,1)
        credit=History(root.directory/'credit')
        require(enrolled['credit']==list(credit.identity) and enrolled['credit_file']==file_identity(credit),
                'supervised_storage_changed')
        with credit.transaction(file_identity=enrolled['credit_file']) as (reservations,_):
            require(not reservations,'supervised_reauthorization_uncertain')
            for slot in (1,2):
                attempt=History(root.directory/f'attempt-{slot}')
                require(enrolled['attempts'][str(slot)]==list(attempt.identity),'supervised_storage_changed')
                # Even an empty/unknown journal is outside this precise no-reservation case.
                require(not any(attempt.directory.iterdir()),'supervised_reauthorization_uncertain')
            previous.revalidate();selected.revalidate()
            now=time.time();validate_evidence(new,now)
            root.require_write_transaction(events)
            append(dict(type='supervised_reauthorized',at=now,previous_sha256=previous.sha256,
                evidence_sha256=selected.sha256,project=new['project'],expires_at=new['expires_at'],
                prefix_sha256=digest(events),permitted_slot=2))
    return dict(status='reauthorized_no_api_call',permitted_slot=2)


def recovery_binding(events,enrolled,selected,slot=3):
    """One explicit local extension; neither a new enrollment nor a refund."""
    require(type(slot) is int and slot in (3,4,5),'supervised_slot')
    index={3:5,4:8,5:12}[slot]
    kind='supervised_recovery' if slot==3 else 'supervised_continuation'
    require(len(events)>=index+2 and events[index]['type']==kind+'_started' and
            events[index+1]['type']==kind+'_authorized','supervised_recovery_binding')
    start,grant=events[index:index+2]
    shape(start,'type at prefix_sha256 evidence_sha256 project expires_at previous_sha256 '
                'credit_sha256 attempt_sha256 request_sha256 permitted_slot cumulative_usd')
    shape(grant,'type at start_sha256 attempt')
    require(start['prefix_sha256']==digest(events[:index]) and grant['start_sha256']==digest(start) and
            start['evidence_sha256']==selected.sha256 and start['project']==enrolled['project'] and
            start['expires_at']==selected.data['expires_at'] and
            start['previous_sha256']==events[{3:3,4:5,5:8}[slot]]['evidence_sha256'] and
            type(start['permitted_slot']) is int and start['permitted_slot']==slot and
            start['cumulative_usd']==[{3:6,4:9,5:12}[slot],100] and
            start['request_sha256']==digest(decode(request(f'synthetic-integration-{slot}'))) and
            selected.data['observed_at']<=stamp(start['at'])<=stamp(grant['at'])<start['expires_at'] and
            all(e['type'] in ('supervised_started','supervised_completed','supervised_diagnostic') and e.get('slot')==slot
                for e in events[index+2:]),'supervised_recovery_binding')
    require(rational(selected.data['available_usd'])>=rational([{3:6,4:9,5:12}[slot],100]),'supervised_credit_only')
    return start,grant


def attempt_pin(events,enrolled,slot):
    if slot in (3,4,5):return events[{3:6,4:9,5:13}[slot]]['attempt']
    return enrolled['attempts'][str(slot)]


def recovery_retained(root,events,enrolled,selected,credit,slot=3):
    """Recheck the retained debit/attempt before admission and each wire check."""
    start,_=recovery_binding(events,enrolled,selected,slot)
    require(enrolled['root']==list(root.identity) and enrolled['credit']==list(credit.identity) and
            enrolled['credit_file']==file_identity(credit),'supervised_storage_changed')
    for previous_slot in range(1,slot):
        old=History(root.directory/f'attempt-{previous_slot}')
        require(list(old.identity)==attempt_pin(events,enrolled,previous_slot),'supervised_storage_changed')
        if previous_slot==1:require(not any(old.directory.iterdir()),'supervised_recovery_state')
        else:
            pin=events[{2:5,3:8,4:12}[previous_slot]]['attempt_sha256']
            require(digest(old.read())==pin,'supervised_recovery_state')
    reservations=credit.read()
    retained_count={3:1,4:2,5:3}[slot]
    require(len(reservations) in (retained_count,retained_count+1) and
            digest(reservations[:retained_count])==start['credit_sha256'],
            'supervised_recovery_state')
    if len(reservations)==retained_count+1:
        require(reservations[-1]['request_hash']==start['request_sha256'] and
                reservations[-1]['reserved_usd']==[3,100],'supervised_recovery_state')
    return rational([{3:6,4:9,5:12}[slot],100])


def recover_once(directory,previous,selected,*,slot=3):
    """Manual, append-only slots3/4/5 for their individually fixed retained shapes.

    A failure after the start append is terminal. Never recreate or repair it.
    This command has no credential, HTTP or automatic run path.
    """
    require(type(slot) is int and slot in (3,4,5),'supervised_slot')
    prior_count={3:1,4:2,5:3}[slot]
    cap=[{3:6,4:9,5:12}[slot],100]
    index={3:5,4:8,5:12}[slot]
    kind='supervised_recovery' if slot==3 else 'supervised_continuation'
    require(type(previous) is SelectedEvidence and type(selected) is SelectedEvidence,
            'supervised_evidence_selection')
    previous.revalidate();selected.revalidate()
    old,new=previous.data,selected.data
    validate_evidence(old,stamp(old['observed_at']))
    validate_evidence(new,time.time())
    require(previous.path!=selected.path and previous.identity[:2]!=selected.identity[:2] and
            previous.sha256!=selected.sha256 and old['project']==new['project'] and
            old['expires_at']<=new['observed_at'] and rational(new['available_usd'])>=rational(cap),
            'supervised_recovery_evidence')
    root=History(Path(directory))
    with root.transaction(write=True) as (events,append):
        expected=[
            'supervised_enrollment_started','supervised_enrolled','supervised_started',
            'supervised_reauthorized','supervised_started']
        if slot in (4,5):expected+=['supervised_recovery_started','supervised_recovery_authorized','supervised_started']
        if slot==5:expected+=['supervised_continuation_started','supervised_continuation_authorized','supervised_started','supervised_diagnostic']
        require(len(events)==index and [e['type'] for e in events]==expected,'supervised_recovery_state')
        enrolled=events[1]
        selection_binding(events,enrolled,previous,slot-1)
        started=events[10 if slot==5 else index-1]
        shape(started,'type slot at evidence_hash')
        require(type(started['slot']) is int and started['slot']==slot-1 and
                started['evidence_hash']==digest(old) and
                old['observed_at']<=stamp(started['at'])<old['expires_at'], 'supervised_recovery_state')
        if slot==5:
            terminal=events[11]
            shape(terminal,'type slot at phase reason category')
            require(type(terminal['slot']) is int and terminal['slot']==4 and
                    terminal['phase']=='http_receive' and
                    terminal['reason']=='responses_network_completion_unknown' and
                    terminal['category']=='network_outcome_unknown' and
                    stamp(terminal['at'])>=stamp(started['at']), 'supervised_recovery_state')
        credit=History(root.directory/'credit')
        require(enrolled['root']==list(root.identity) and enrolled['credit']==list(credit.identity) and
                enrolled['credit_file']==file_identity(credit),'supervised_storage_changed')
        if slot in (4,5):
            recovery_retained(root,events,enrolled,previous,credit,slot-1)
        for previous_slot in range(1,slot):
            attempt=History(root.directory/f'attempt-{previous_slot}')
            require(list(attempt.identity)==attempt_pin(events,enrolled,previous_slot),'supervised_storage_changed')
            if previous_slot==1:require(not any(attempt.directory.iterdir()),'supervised_recovery_state')
        with credit.transaction(file_identity=enrolled['credit_file']) as (reservations,_), \
             attempt.transaction() as (prior,_):
            fingerprint=digest(decode(request(f'synthetic-integration-{slot-1}')))
            require(len(reservations)==prior_count and
                    ledger_total(reservations,new['project'],ceiling=TOTAL if slot==3 else rational([{4:6,5:9}[slot],100]))==PER_REQUEST*prior_count and
                    reservations[-1]['request_hash']==fingerprint,'supervised_recovery_state')
            require(len(prior)==2 and prior[0]['type']=='bound_send_reserved' and
                    prior[1]['type']=='bound_send_attempted' and
                    prior[1]['request_sha256']==fingerprint,'supervised_recovery_state')
            permit=prior[0]['permit']
            require(permit['selection']['run']==f'synthetic-integration-{slot-1}' and
                    permit['selection']['request_sha256']==fingerprint and
                    permit['selection']['local_context_sha256']==digest(old) and
                    permit['project']==new['project'] and permit['model']==INTEGRATION_MODEL and
                    permit['maximum_debit']==[3,100] and permit['input_limit']==CONTEXT_TOKENS and
                    permit['output_limit']==OUTPUT_TOKENS,'supervised_recovery_state')
            # Refuse preexisting files/directories, including broken symlinks.
            target=root.directory/f'attempt-{slot}'
            require(not os.path.lexists(target),'supervised_recovery_state')
            previous.revalidate();selected.revalidate()
            now=time.time();validate_evidence(new,now)
            root.require_write_transaction(events)
            start=dict(type=kind+'_started',at=now,prefix_sha256=digest(events),
                evidence_sha256=selected.sha256,project=new['project'],expires_at=new['expires_at'],
                previous_sha256=previous.sha256,credit_sha256=digest(reservations),attempt_sha256=digest(prior),
                request_sha256=digest(decode(request(f'synthetic-integration-{slot}'))),
                permitted_slot=slot,cumulative_usd=cap)
            append(start)
            target.mkdir(mode=0o700)
            new_attempt=History(target)
            append(dict(type=kind+'_authorized',at=time.time(),
                        start_sha256=digest(start),attempt=list(new_attempt.identity)))
    return dict(status='recovery_authorized_no_api_call',permitted_slot=slot,cumulative_usd=cap)


def prompt_credential():
    require(sys.stdin.isatty() and sys.stderr.isatty(),'supervised_interactive_terminal_required')
    # getpass falls back to echoed input if terminal setup fails; forbid that.
    with warnings.catch_warnings():
        warnings.simplefilter('error',getpass.GetPassWarning)
        value=getpass.getpass('Secret API key (not Tracking ID or project ID; hidden): ')
    return ExplicitCredential(value)


def operator_context(e,history,credit,enrollment,run,case,now,*,expires_at=None):
    selection=dict(run=run,case=case,request_sha256=digest(decode(request(run))),
                   local_context_sha256=digest(e))
    r=dict(mode='synthetic_api_integration',selection=selection,project=e['project'],model=INTEGRATION_MODEL,
        issued_at=now,expires_at=min(e['expires_at'],expires_at) if expires_at is not None else e['expires_at'],history_identity=list(history.identity),currency='USD',
        ceiling=[3,100],output_limit=OUTPUT_TOKENS,credit_history_identity=enrollment['credit'],
        credit_history_file_identity=enrollment['credit_file'])
    facts=dict(owner=dict(operation=r['mode'],max_calls=1,currency='USD',ceiling=[3,100]),
        privacy=dict(request_sha256=selection['request_sha256'],store=False,tools=[]),
        account=dict(project=e['project'],model=INTEGRATION_MODEL,policy=POLICY),
        credential_route=dict(project=e['project'],injection_route='local-no-echo-memory-only'),
        coverage=dict(request_sha256=selection['request_sha256'],policy=POLICY,coverage=CONTEXT_COVERAGE,
            counter_identity=e['context_reference'],input_upper_bound=CONTEXT_TOKENS),
        pricing=dict(policy=POLICY,currency='USD',input=[5,100000000],cache_read=[5,1000000000],
            cache_write=[0,1],output=[4,10000000],ancillary_maximum=[0,1]))
    binding=digest(r)
    r['evidence']={role:dict(binding_hash=binding,issuer='supervised-operator',
        reference=digest(e),observed_at=e['observed_at'],expires_at=e['expires_at'],facts=value)
        for role,value in facts.items()}
    raw=encoded(r)
    return OperatorContext(raw,hashlib.sha256(raw).hexdigest(),tuple((k,digest(v)) for k,v in r['evidence'].items())),selection


_LAST_DIAGNOSTIC = ContextVar('supervised_last_diagnostic',default=None)


def run(directory,selected,slot,*,clock=time.time):
    _LAST_DIAGNOSTIC.set(None)
    with diagnostic_scope():
        try:return _run(directory,selected,slot,clock=clock)
        except (Exception,KeyboardInterrupt) as error:
            if _LAST_DIAGNOSTIC.get() is None:
                _LAST_DIAGNOSTIC.set(safe_diagnostic(error))
            raise


def safe_diagnostic(error):
    return dict(phase=diagnostic_phase() or 'preflight',reason=safe_reason(error),
                category=refusal_category(error))


def _run(directory,selected,slot,*,clock=time.time):
    require(type(slot) is int and slot in (1,2,3,4,5),'supervised_slot')
    require(type(selected) is SelectedEvidence,'supervised_evidence_selection')
    selected.revalidate()
    evidence=selected.data
    validate_evidence(evidence,max(clock(),time.time())) # Before prompt, journal mutation or HTTP.
    root=History(Path(directory),clock=clock)
    with root.transaction(write=True) as (events,append):
        require(len(events)>=2 and events[0]['type']=='supervised_enrollment_started' and
                events[1]['type']=='supervised_enrolled','supervised_not_enrolled')
        enrolled=events[1]
        require(enrolled['root']==list(root.identity),'supervised_root_changed')
        selection_binding(events,enrolled,selected,slot)
        require(not any(e.get('slot')==slot for e in events),'supervised_attempt_consumed')
        credit=History(root.directory/'credit',clock=clock)
        history=History(root.directory/f'attempt-{slot}',clock=clock)
        require(enrolled['credit']==list(credit.identity) and enrolled['credit_file']==file_identity(credit) and
                attempt_pin(events,enrolled,slot)==list(history.identity),'supervised_storage_changed')
        ceiling=recovery_retained(root,events,enrolled,selected,credit,slot) if slot in (3,4,5) else TOTAL
        with credit.transaction(file_identity=enrolled['credit_file']) as (old,_):
            require(ledger_total(old,evidence['project'],ceiling=ceiling)+PER_REQUEST<=ceiling,'credit_total_ceiling')
        require(not history.read(),'supervised_attempt_consumed')
        run_id=f'synthetic-integration-{slot}'
        case=dict(source='synthetic-credit-integration',case_id='outcome-'+digest('synthetic-example'),
                  version=digest(decode(request(run_id))),occurrence=None)
        with interactive_credential(root) as credential:
            # Validate format without serializing or storing the resulting headers.
            headers(credential,evidence['project'])
            # Conservative typo/identifier filter, not authentication. Keep the
            # root lock held; no slot/debit is consumed by invalid input.
            require(credential.value.startswith('sk-'),'responses_credential_invalid')
            append(dict(type='supervised_started',slot=slot,at=clock(),evidence_hash=digest(evidence)))
            observe_phase('slot_started')
            try:
                validate_evidence(evidence,max(clock(),time.time()))
                body=request(run_id)
                require(credential.value.encode() not in body and credential.value.encode() not in encoded(evidence),
                        'supervised_credential_disclosed')
                with command_authority(root,events,enrolled,selected,slot,credit,history,credential) as authority:
                    context,selection=operator_context(evidence,history,credit,enrolled,run_id,case,clock(),
                        expires_at=authority.deadline)
                    parent=HistoricalDiagnosticParent(context,history=history,credit_history=credit,credential=credential)
                    answer=ResponsesTransport(enabled=True,credential=credential,clock=clock).complete_credit_test(
                        history=history,run=run_id,case=case,context_sha256=selection['local_context_sha256'],parent=parent)
                    observe_phase('completion_recording')
                    append(dict(type='supervised_completed',slot=slot,at=clock(),answer=decode(answer),
                                request_hash=selection['request_sha256'],reserved_usd=[3,100]))
                    observe_phase('completed')
                    return dict(status='completed',slot=slot,request_hash=selection['request_sha256'],
                                input_upper_bound=CONTEXT_TOKENS,reserved_usd=[3,100])
            except (Exception,KeyboardInterrupt) as error:
                diagnostic=safe_diagnostic(error)
                _LAST_DIAGNOSTIC.set(diagnostic)
                # Diagnostics cannot clear a consumed slot or mask its failure.
                # A partial failed append remains a corrupt, fail-closed history.
                if diagnostic_phase() is not None:
                    try:
                        append(dict(type='supervised_diagnostic',slot=slot,at=clock(),**diagnostic))
                    except BaseException:
                        pass
                raise



class _SafeParser(argparse.ArgumentParser):
    def error(self,message):
        self.exit(2,'Supervised synthetic command refused: category=invalid_arguments; action=unknown. '
                  'Retain state; do not retry automatically.\n')


def main(argv=None):
    parser=_SafeParser(description=__doc__)
    parser.add_argument('--state',required=True,type=Path)
    sub=parser.add_subparsers(dest='action',required=True)
    registration=sub.add_parser('enroll');registration.add_argument('--evidence',required=True,type=Path)
    renewal=sub.add_parser('reauthorize')
    renewal.add_argument('--previous-evidence',required=True,type=Path)
    renewal.add_argument('--evidence',required=True,type=Path)
    recovery=sub.add_parser('recover-once')
    recovery.add_argument('--previous-evidence',required=True,type=Path)
    recovery.add_argument('--evidence',required=True,type=Path)
    continuation=sub.add_parser('continue-once')
    continuation.add_argument('--previous-evidence',required=True,type=Path)
    continuation.add_argument('--evidence',required=True,type=Path)
    continuation.add_argument('--slot',type=int,choices=(4,5),default=4)
    send=sub.add_parser('run');send.add_argument('--evidence',required=True,type=Path)
    send.add_argument('--slot',required=True,type=int,choices=(1,2,3,4,5))
    args=parser.parse_args(argv)
    _LAST_DIAGNOSTIC.set(None)
    try:
        if args.action=='enroll':
            selected=read_evidence(args.evidence)
            enroll(args.state,selected);result=dict(status='enrolled_no_api_call')
        elif args.action=='reauthorize':
            previous=read_evidence(args.previous_evidence);selected=read_evidence(args.evidence)
            result=reauthorize(args.state,previous,selected)
        elif args.action=='recover-once':
            result=recover_once(args.state,read_evidence(args.previous_evidence),read_evidence(args.evidence))
        elif args.action=='continue-once':
            result=recover_once(args.state,read_evidence(args.previous_evidence),read_evidence(args.evidence),slot=args.slot)
        else:result=run(args.state,read_evidence(args.evidence),args.slot)
        print(encoded(result).decode());return 0
    except (Exception,KeyboardInterrupt) as error:
        # Never print raw exceptions, remote bodies, credentials or a traceback.
        diagnostic=_LAST_DIAGNOSTIC.get() or safe_diagnostic(error)
        print('Supervised synthetic command refused: category='+refusal_category(error)+
              '; action='+args.action+'; '+('request status unconfirmed' if args.action=='run' else 'no API request')+
              '; phase='+diagnostic['phase']+'; reason='+diagnostic['reason']+
              '. Retain state; do not retry automatically.',file=sys.stderr)
        return 1


if __name__=='__main__':
    # -m executes this file as __main__; authority imports the canonical module.
    # Use its classes and prompt ContextVar throughout the executable command.
    from ai_movie_investigator.supervised_credit import main as canonical_main
    raise SystemExit(canonical_main())
