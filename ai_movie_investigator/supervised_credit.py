"""Supervised synthetic and separately consented historical Nano commands.

No automatic enrollment, retry, reset or credential discovery. Historical inputs
require their own exact disclosure grant; synthetic authority is insufficient.
Operator evidence pins are correspondence, never live authentication by themselves.
"""
from contextlib import contextmanager, ExitStack
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
from .contracts import Refusal, decode, digest, encoded, require, shape, stamp, hash_id, MAX_INPUT, MAX_OUTPUT
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
    'captured_refused': frozenset(('verified_identity_check_scope assessment_purpose verified_capture_grant verified_capture_qualification captured_real_activation_unissued captured_authority_changed captured_authority_expired captured_selection_changed captured_generation_consumed captured_completion_unbound captured_lock_required captured_route_required captured_pending_grant captured_receipt_unbound').split()),
    'keychain_refused': frozenset(('keychain_platform keychain_project keychain_missing keychain_interaction_required keychain_denied keychain_unavailable keychain_data_invalid keychain_process_required keychain_lookup_timeout keychain_lookup_busy keychain_framework_unavailable keychain_interaction_get_failed keychain_interaction_disable_failed keychain_interaction_restore_failed keychain_query_build_failed keychain_query_failed keychain_release_failed keychain_not_available keychain_parameter_invalid keychain_entitlement_missing').split()),
    'historical_report_refused': frozenset(('pilot_run_alias_changed pilot_one_generation_required pilot_citation_alias_unknown pilot_citation_claim_not_disclosed model_status next_action alternative_limit citation_limit unsupported_citation unsupported_claim unsupported_candidate candidate_status alternative_evidence_missing candidate_evidence_missing conflicting_ids_require_review owner_target_conflict stale_candidate_support insufficient_candidate_support normalized_identity_not_established').split()),
    'historical_refused': frozenset(('historical_expanded_required historical_disclosure_size historical_disclosure_changed historical_owner_confirmation_required historical_receipt_missing historical_route_required historical_pending_grant historical_assessment_consumed historical_renewal_changed historical_renewal_authority historical_renewal_expired historical_renewal_prior historical_renewal_consumed').split()),
    'standing_credit_refused': frozenset(('supervised_standing_missing supervised_standing_binding '
        'supervised_standing_interrupted supervised_standing_history supervised_standing_credit').split()),
    'evidence_changed': frozenset((
        'supervised_evidence_changed_read_device supervised_evidence_changed_read_inode '
        'supervised_evidence_changed_read_size supervised_evidence_changed_read_mtime '
        'supervised_evidence_changed_read_ctime supervised_evidence_changed_selected_bytes '
        'supervised_evidence_changed_selected_device supervised_evidence_changed_selected_inode '
        'supervised_evidence_changed_selected_size supervised_evidence_changed_selected_mtime '
    ).split()),
    'send_or_response_refused': frozenset((
        'supervised_authorization_io_error supervised_authorization_type_error '
        'supervised_authorization_key_error supervised_authorization_value_error '
    ).split()),
    'transport_refused': frozenset((
        'responses_observation_profile responses_observation_transition '
        'responses_setup_deadline_exceeded responses_observation_deadline_exceeded '
        'responses_cleanup_failed '
        'responses_length_duplicate responses_length_invalid responses_framing_conflict '
        'responses_transfer_encoding_invalid responses_declared_body_limit responses_observed_body_limit '
        'responses_body_limit responses_body_truncated responses_credential_invalid responses_deadline '
        'responses_deadline_exceeded responses_dns_failed responses_http_rejected responses_http_shape '
        'responses_http_400 responses_http_401 responses_http_403 responses_http_404 responses_http_408 '
        'responses_http_409 responses_http_422 responses_http_429 responses_http_5xx responses_http_other '
        'responses_network_completion_unknown responses_network_denied responses_path_denied responses_peer_changed '
        'responses_project_invalid responses_request_size responses_timer_busy responses_timer_unavailable '
        'responses_tls_required responses_tls_roots_unavailable simulation_credential_required simulation_response_invalid '
        'simulation_response_missing '
    ).split()),
    'protocol_refused': frozenset((
        'responses_action_or_output_denied responses_answer_count responses_answer_schema responses_cache_or_tier_changed '
        'responses_cache_partition responses_contract_changed responses_identity_invalid responses_model_profile '
        'responses_not_completed responses_object_invalid responses_model_mismatch responses_error_present responses_incomplete_max_output_tokens responses_incomplete_content_filter responses_incomplete_other responses_status_failed responses_status_cancelled responses_status_queued responses_status_in_progress responses_status_other responses_incomplete_details_present responses_output_shape responses_reasoning_shape responses_text_required '
        'responses_context_changed responses_tool_usage_denied responses_unsupported_shape responses_usage_invalid responses_usage_limit responses_usage_required '
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
        'offline_fixture_required offline_history_not_empty offline_assessment_disabled offline_transport_required simulated_completion_unbound simulated_response_unbound '
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


@contextmanager
def keychain_credential(root,project):
    from .keychain_credential import credential as retrieve
    credential=retrieve(project)
    marker=_PROMPTED.set((root,credential,time.time(),time.monotonic()))
    try:yield credential
    finally:_PROMPTED.reset(marker)


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


def _read_evidence(path, limit=16384):
    path=Path(path)
    before=path.lstat()
    raw=read_private(path,limit)
    after=path.lstat()
    identity=lambda info:(info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns)
    before_identity,after_identity=identity(before),identity(after)
    for old,new,reason in zip(before_identity,after_identity,(
            'supervised_evidence_changed_read_device','supervised_evidence_changed_read_inode',
            'supervised_evidence_changed_read_size','supervised_evidence_changed_read_mtime',
            'supervised_evidence_changed_read_ctime')):
        require(old==new,reason)
    # Persistent selection binds bytes and dev/inode/size/mtime. ctime is a
    # per-read race check, not proof against same-owner change-and-restore.
    return raw,after_identity[:4]


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
        require(raw==self.raw,'supervised_evidence_changed_selected_bytes')
        if identity!=self.identity:
            for old,new,reason in zip(self.identity,identity,(
                    'supervised_evidence_changed_selected_device','supervised_evidence_changed_selected_inode',
                    'supervised_evidence_changed_selected_size','supervised_evidence_changed_selected_mtime')):
                require(old==new,reason)
            # Preserve exact tuple equality even for a malformed selection.
            require(False,'supervised_evidence_changed')



def read_evidence(path):
    raw,identity=_read_evidence(path)
    decode(raw,16384)
    return SelectedEvidence(path,raw,identity,_EVIDENCE_READER)


def validate_evidence(e,now,*,standing=False):
    shape(e,'project account_reference observed_at expires_at credit_expires_at available_usd '
          'billing_reference paid_fallback owner_reference model policy context_window pricing_reference context_reference model_access_reference input_rate cached_input_rate output_rate'+(' credit_kind' if standing else ''))
    if standing:require(e['credit_kind']=='promotional','supervised_standing_credit')
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
    if slot>=7:
        standing_binding(events,enrolled,selected,slot)
        return
    if slot in (3,4,5,6):
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
    require(type(slot) is int and slot in (3,4,5,6),'supervised_slot')
    index={3:5,4:8,5:12,6:16}[slot]
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
            start['previous_sha256']==events[{3:3,4:5,5:8,6:12}[slot]]['evidence_sha256'] and
            type(start['permitted_slot']) is int and start['permitted_slot']==slot and
            start['cumulative_usd']==[{3:6,4:9,5:12,6:15}[slot],100] and
            start['request_sha256']==digest(decode(request(f'synthetic-integration-{slot}'))) and
            selected.data['observed_at']<=stamp(start['at'])<=stamp(grant['at'])<start['expires_at'] and
            all(e['type'] in ('supervised_started','supervised_completed','supervised_diagnostic') and e.get('slot')==slot
                for e in events[index+2:]),'supervised_recovery_binding')
    require(rational(selected.data['available_usd'])>=rational([{3:6,4:9,5:12,6:15}[slot],100]),'supervised_credit_only')
    return start,grant


def attempt_pin(events,enrolled,slot):
    if slot>=7:
        matches=[g for start,g in _standing_attempts(events,enrolled) if start['slot']==slot]
        require(len(matches)==1,'supervised_standing_binding')
        return matches[0]['attempt']
    if slot in (3,4,5,6):return events[{3:6,4:9,5:13,6:17}[slot]]['attempt']
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
            pin=events[{2:5,3:8,4:12,5:16}[previous_slot]]['attempt_sha256']
            require(digest(old.read())==pin,'supervised_recovery_state')
    reservations=credit.read()
    retained_count={3:1,4:2,5:3,6:4}[slot]
    require(len(reservations) in (retained_count,retained_count+1) and
            digest(reservations[:retained_count])==start['credit_sha256'],
            'supervised_recovery_state')
    if len(reservations)==retained_count+1:
        require(reservations[-1]['request_hash']==start['request_sha256'] and
                reservations[-1]['reserved_usd']==[3,100],'supervised_recovery_state')
    return rational([{3:6,4:9,5:12,6:15}[slot],100])


def recover_once(directory,previous,selected,*,slot=3):
    """Manual, append-only slots3/4/5/6 for their individually fixed retained shapes.

    A failure after the start append is terminal. Never recreate or repair it.
    This command has no credential, HTTP or automatic run path.
    """
    require(type(slot) is int and slot in (3,4,5,6),'supervised_slot')
    prior_count={3:1,4:2,5:3,6:4}[slot]
    cap=[{3:6,4:9,5:12,6:15}[slot],100]
    index={3:5,4:8,5:12,6:16}[slot]
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
        if slot in (4,5,6):expected+=['supervised_recovery_started','supervised_recovery_authorized','supervised_started']
        if slot in (5,6):expected+=['supervised_continuation_started','supervised_continuation_authorized','supervised_started','supervised_diagnostic']
        if slot==6:expected+=['supervised_continuation_started','supervised_continuation_authorized','supervised_started','supervised_diagnostic']
        require(len(events)==index and [e['type'] for e in events]==expected,'supervised_recovery_state')
        enrolled=events[1]
        selection_binding(events,enrolled,previous,slot-1)
        started=events[index-2 if slot in (5,6) else index-1]
        shape(started,'type slot at evidence_hash')
        require(type(started['slot']) is int and started['slot']==slot-1 and
                started['evidence_hash']==digest(old) and
                old['observed_at']<=stamp(started['at'])<old['expires_at'], 'supervised_recovery_state')
        if slot in (5,6):
            terminal=events[index-1]
            shape(terminal,'type slot at phase reason category')
            require(type(terminal['slot']) is int and terminal['slot']==slot-1 and
                    terminal['phase']=={5:'http_receive',6:'http_response_received'}[slot] and
                    terminal['reason']=={5:'responses_network_completion_unknown',6:'responses_body_limit'}[slot] and
                    terminal['category']=={5:'network_outcome_unknown',6:'transport_refused'}[slot] and
                    stamp(terminal['at'])>=stamp(started['at']), 'supervised_recovery_state')
        credit=History(root.directory/'credit')
        require(enrolled['root']==list(root.identity) and enrolled['credit']==list(credit.identity) and
                enrolled['credit_file']==file_identity(credit),'supervised_storage_changed')
        if slot in (4,5,6):
            recovery_retained(root,events,enrolled,previous,credit,slot-1)
        for previous_slot in range(1,slot):
            attempt=History(root.directory/f'attempt-{previous_slot}')
            require(list(attempt.identity)==attempt_pin(events,enrolled,previous_slot),'supervised_storage_changed')
            if previous_slot==1:require(not any(attempt.directory.iterdir()),'supervised_recovery_state')
        with credit.transaction(file_identity=enrolled['credit_file']) as (reservations,_), \
             attempt.transaction() as (prior,_):
            fingerprint=digest(decode(request(f'synthetic-integration-{slot-1}')))
            require(len(reservations)==prior_count and
                    ledger_total(reservations,new['project'],ceiling=TOTAL if slot==3 else rational([{4:6,5:9,6:12}[slot],100]))==PER_REQUEST*prior_count and
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


def request_value(body, *, captured=False):
    """Captured request parsing has its own bound, never the answer allowance."""
    from .contracts import MAX_OUTPUT
    if captured:
        from .new_case import CAPTURED_REQUEST_BYTES
        return decode(body,CAPTURED_REQUEST_BYTES)
    return decode(body,MAX_OUTPUT)


def operator_context(e,history,credit,enrollment,run,case,now,*,expires_at=None,historical=None,keychain=False,captured=None):
    grant=historical or captured
    body=encoded(grant['request']) if grant else request(run)
    wire=request_value(body,captured=bool(captured))
    disclosure=(decode(grant['request']['input'][0]['content'][0]['text'],
        MAX_INPUT if captured else MAX_OUTPUT) if grant else None)
    selection=dict(run=run,case=case,request_sha256=digest(wire),
                   local_context_sha256=digest(e))
    r=dict(mode='captured_nano_dormant' if captured else 'historical_nano_manual' if historical else 'synthetic_api_integration',selection=selection,project=e['project'],model=INTEGRATION_MODEL,
        issued_at=now,expires_at=min(e['expires_at'],expires_at) if expires_at is not None else e['expires_at'],history_identity=list(history.identity),currency='USD',
        ceiling=[3,100],output_limit=wire['max_output_tokens'],credit_history_identity=enrollment['credit'],
        credit_history_file_identity=enrollment['credit_file'])
    facts=dict(owner=dict(operation=r['mode'],max_calls=1,currency='USD',ceiling=[3,100]),
        privacy=dict(request_sha256=selection['request_sha256'],store=False,tools=[]),
        account=dict(project=e['project'],model=INTEGRATION_MODEL,policy=POLICY),
        credential_route=dict(project=e['project'],injection_route='fixed-project-keychain-memory-only' if keychain else 'local-no-echo-memory-only'),
        coverage=dict(request_sha256=selection['request_sha256'],policy=POLICY,coverage=CONTEXT_COVERAGE,
            counter_identity=e['context_reference'],input_upper_bound=CONTEXT_TOKENS),
        pricing=dict(policy=POLICY,currency='USD',input=[5,100000000],cache_read=[5,1000000000],
            cache_write=[0,1],output=[4,10000000],ancillary_maximum=[0,1]))
    if grant:facts['privacy']['disclosure_sha256']=digest(disclosure)
    binding=digest(r)
    r['evidence']={role:dict(binding_hash=binding,issuer='supervised-operator',
        reference=digest(e),observed_at=e['observed_at'],expires_at=e['expires_at'],facts=value)
        for role,value in facts.items()}
    raw=encoded(r)
    return OperatorContext(raw,hashlib.sha256(raw).hexdigest(),tuple((k,digest(v)) for k,v in r['evidence'].items()),
        encoded(disclosure) if grant else None),selection


_LAST_DIAGNOSTIC = ContextVar('supervised_last_diagnostic',default=None)


def run(directory,selected,slot,*,clock=time.time,historical=False,keychain=False,captured=False):
    _LAST_DIAGNOSTIC.set(None)
    with diagnostic_scope():
        try:return _run(directory,selected,slot,clock=clock,historical=historical,keychain=keychain,captured=captured)
        except (Exception,KeyboardInterrupt) as error:
            if _LAST_DIAGNOSTIC.get() is None:
                _LAST_DIAGNOSTIC.set(safe_diagnostic(error))
            raise


def safe_diagnostic(error):
    result=dict(phase=diagnostic_phase() or 'preflight',reason=safe_reason(error),category=refusal_category(error))
    cleanup=getattr(error,'keychain_cleanup_reason',None)
    if cleanup in ('keychain_release_failed','keychain_interaction_restore_failed'):result['cleanup_reason']=cleanup
    return result


def _run(directory,selected,slot,*,clock=time.time,historical=False,keychain=False,captured=False):
    if captured:
        from .new_case import require_captured_activation
        require_captured_activation()
        require(not historical and slot is not None,'captured_route_required')
    next_attempt=slot is None
    require(next_attempt or (type(slot) is int and slot>=1),'supervised_slot')
    require(type(selected) is SelectedEvidence,'supervised_evidence_selection')
    selected.revalidate()
    evidence=selected.data
    validate_evidence(evidence,max(clock(),time.time()),standing=next_attempt or slot>=7) # Before prompt, journal mutation or HTTP.
    root=History(Path(directory),clock=clock)
    with root.transaction(write=True) as (events,append), ExitStack() as case_locks:
        require(len(events)>=2 and events[0]['type']=='supervised_enrollment_started' and
                events[1]['type']=='supervised_enrolled','supervised_not_enrolled')
        enrolled=events[1]
        require(enrolled['root']==list(root.identity),'supervised_root_changed')
        if next_attempt:
            slot=_prepare_next_locked(root,events,append,selected,create=False)
            credit=History(root.directory/'credit')
        else:
            selection_binding(events,enrolled,selected,slot)
            require(not any(e.get('slot')==slot and (slot<7 or e.get('type') not in
                    ('supervised_standing_attempt_started','supervised_standing_attempt_authorized'))
                    for e in events),'supervised_attempt_consumed')
            credit=History(root.directory/'credit',clock=clock)
            history=History(root.directory/f'attempt-{slot}',clock=clock)
            require(enrolled['credit']==list(credit.identity) and enrolled['credit_file']==file_identity(credit) and
                    attempt_pin(events,enrolled,slot)==list(history.identity),'supervised_storage_changed')
            ceiling=(standing_retained(root,events,enrolled,selected,credit,slot) if slot>=7 else
                     recovery_retained(root,events,enrolled,selected,credit,slot) if slot in (3,4,5,6) else TOTAL)
            with credit.transaction(file_identity=enrolled['credit_file']) as (old,_):
                from .credit_test import retained_total
                require(retained_total(old,evidence['project'])+PER_REQUEST<=ceiling,'credit_total_ceiling')
            require(not history.read(),'supervised_attempt_consumed')
        historical_grant=None; captured_grant=None; captured_case=None
        if slot>=7 and not next_attempt:
            start,_=standing_binding(events,enrolled,selected,slot)
            historical_grant=start.get('historical');captured_grant=start.get('captured')
            if historical_grant and 'renewal' in historical_grant:
                from .historical_nano import renewal_history
                renewal_history(root,events,historical_grant,creating=False)
        require(bool(historical_grant)==historical,'historical_route_required')
        require(bool(captured_grant)==captured,'captured_route_required')
        if captured_grant:
            from .new_case import captured_case_lock
            captured_case=case_locks.enter_context(captured_case_lock(root,events,captured_grant,evidence))
        run_id=historical_grant['run'] if historical_grant else f'synthetic-integration-{slot}'
        case=dict(source='synthetic-credit-integration',case_id='outcome-'+digest('synthetic-example'),
                  version=digest(decode(request(run_id))),occurrence=None)
        if historical_grant:case=historical_grant['case']
        if captured_grant:run_id=captured_grant['run'];case=captured_grant['case']
        with (keychain_credential(root,evidence['project']) if keychain else interactive_credential(root)) as credential:
            # Validate format without serializing or storing the resulting headers.
            headers(credential,evidence['project'])
            # Conservative typo/identifier filter, not authentication. Keep the
            # root lock held; no slot/debit is consumed by invalid input.
            require(credential.value.startswith('sk-'),'responses_credential_invalid')
            if next_attempt:
                require(slot==_prepare_next_locked(root,events,append,selected,create=True),'supervised_standing_binding')
                history=History(root.directory/f'attempt-{slot}')
            if captured_case:captured_case.start()
            append(dict(type='supervised_started',slot=slot,at=clock(),evidence_hash=digest(evidence)))
            observe_phase('slot_started')
            try:
                validate_evidence(evidence,max(clock(),time.time()),standing=slot>=7)
                body=expected_request(events,enrolled,slot)
                require(credential.value.encode() not in body and credential.value.encode() not in encoded(evidence),
                        'supervised_credential_disclosed')
                with command_authority(root,events,enrolled,selected,slot,credit,history,credential) as authority:
                    context,selection=operator_context(evidence,history,credit,enrolled,run_id,case,clock(),
                        expires_at=authority.deadline,historical=historical_grant,keychain=keychain,captured=captured_grant)
                    parent=HistoricalDiagnosticParent(context,history=history,credit_history=credit,credential=credential)
                    if historical_grant or captured_grant:
                        from .bound_send import _send_bound
                        answer=_send_bound(history,body,run=run_id,case=case,parent=parent,credential=credential,
                                           context_sha256=selection['local_context_sha256'])
                        if captured_grant:
                            captured_report=authority.complete_captured(answer)
                        else:
                            from .historical_nano import report
                            historical_report=report(historical_grant,decode(answer),history)
                    else:
                        answer=ResponsesTransport(enabled=True,credential=credential,clock=clock).complete_credit_test(
                            history=history,run=run_id,case=case,context_sha256=selection['local_context_sha256'],parent=parent)
                    observe_phase('completion_recording')
                    append(dict(type='supervised_completed',slot=slot,at=clock(),answer=decode(answer),
                                request_hash=selection['request_sha256'],reserved_usd=[3,100],
                                **({'historical_report':historical_report} if historical_grant else
                                   {'captured_report':captured_report} if captured_grant else {})))
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



# Standing promotional authority is append-only and applies only to future
# manually started synthetic attempts. Historical requests are never rebuilt.
def _standing_base(events,enrolled):
    require(len(events)>=21 and events[20].get('type')=='supervised_standing_authorized',
            'supervised_standing_missing')
    grant=events[20]
    shape(grant,'type at project account_reference policy ceiling_usd credit_expires_at evidence_sha256 prefix_sha256 credit_sha256 attempts')
    require(grant['prefix_sha256']==digest(events[:20]) and grant['project']==enrolled['project'] and
            grant['policy']==POLICY and rational(grant['ceiling_usd'])>=PER_REQUEST and
            stamp(grant['at'])<stamp(grant['credit_expires_at']), 'supervised_standing_binding')
    return grant


def _promotional_renewal(events,enrolled):
    """Validate one successor grant without rewriting the original authority."""
    base=_standing_base(events,enrolled)
    matches=[(i,r) for i,r in enumerate(events) if r.get('type')=='supervised_promotional_renewed']
    require(len(matches)<=1,'supervised_standing_binding')
    if not matches:return None
    index,row=matches[0]
    shape(row,'type at project account_reference policy original_grant_sha256 prefix_sha256 credit_sha256 credit_count next_slot ceiling_usd credit_expires_at evidence_sha256 evidence')
    e=row['evidence'];validate_evidence(e,stamp(row['at']),standing=True)
    require(index>=21 and row['prefix_sha256']==digest(events[:index]) and
            row['original_grant_sha256']==digest(base) and row['project']==base['project']==e['project'] and
            row['account_reference']==base['account_reference']==e['account_reference'] and row['policy']==POLICY and
            row['credit_expires_at']==e['credit_expires_at']>base['credit_expires_at'] and
            base['credit_expires_at']<=row['at'] and row['ceiling_usd']==e['available_usd'] and
            type(row['next_slot']) is int and row['next_slot']>=7 and
            type(row['credit_count']) is int and row['credit_count']>=5,
            'supervised_standing_credit')
    hash_id(row['evidence_sha256'])
    return row


def _credit_grant(events,enrolled,slot):
    renewal=_promotional_renewal(events,enrolled)
    return renewal if renewal and slot>=renewal['next_slot'] else _standing_base(events,enrolled)


def renew_promotional(directory,selected):
    """Append a verified same-account successor; never reset, allocate or send."""
    require(type(selected) is SelectedEvidence,'supervised_evidence_selection')
    selected.revalidate();e=selected.data;validate_evidence(e,time.time(),standing=True)
    root=History(Path(directory))
    with root.transaction(write=True) as (events,append):
        enrolled=events[1];credit=History(root.directory/'credit')
        base,attempts,reservations,total=_standing_history(root,events,enrolled,credit)
        require(_promotional_renewal(events,enrolled) is None,'supervised_standing_binding')
        require(not attempts or any(r.get('type') in ('supervised_completed','supervised_diagnostic') and r.get('slot')==attempts[-1][0]['slot'] for r in events),
                'supervised_standing_interrupted')
        selected.revalidate();now=time.time();validate_evidence(e,now,standing=True)
        require(e['project']==base['project'] and e['account_reference']==base['account_reference'] and
                base['credit_expires_at']<=now<e['credit_expires_at'] and
                e['credit_expires_at']>base['credit_expires_at'] and total+PER_REQUEST<=rational(e['available_usd']),
                'supervised_standing_credit')
        row=dict(type='supervised_promotional_renewed',at=now,project=e['project'],account_reference=e['account_reference'],
            policy=POLICY,original_grant_sha256=digest(base),prefix_sha256=digest(events),credit_sha256=digest(reservations),
            credit_count=len(reservations),next_slot=7+len(attempts),ceiling_usd=e['available_usd'],
            credit_expires_at=e['credit_expires_at'],evidence_sha256=selected.sha256,evidence=e)
        _promotional_renewal([*events,row],enrolled)
        append(row)
    return dict(status='promotional_renewed_no_api_call',next_slot=row['next_slot'],prior_reservations_retained=True)


def _standing_attempts(events,enrolled):
    _standing_base(events,enrolled)
    result=[];index=21;slot=7;renewal=_promotional_renewal(events,enrolled)
    while index<len(events):
        start=events[index]
        if start.get('type')=='supervised_promotional_renewed':
            require(start is renewal and start['next_slot']==slot,'supervised_standing_binding')
            index+=1;continue
        shape(start,'type at slot project policy prefix_sha256 evidence_sha256 evidence_hash expires_at request_sha256 '
                    'credit_sha256 credit_count previous_attempt_sha256 ceiling_usd'+(' historical' if 'historical' in start else '')+(' captured' if 'captured' in start else '')+(' promotional_renewal_sha256' if 'promotional_renewal_sha256' in start else ''))
        effective=_credit_grant(events,enrolled,slot)
        require(start.get('promotional_renewal_sha256')==(digest(effective) if effective.get('type')=='supervised_promotional_renewed' else None),'supervised_standing_binding')
        require(not ('historical' in start and 'captured' in start),'captured_route_required')
        require(start['type']=='supervised_standing_attempt_started' and type(start['slot']) is int and
                start['slot']==slot and start['prefix_sha256']==digest(events[:index]) and
                start['project']==enrolled['project'] and start['policy']==POLICY,
                'supervised_standing_binding')
        require(index+1<len(events),'supervised_standing_interrupted')
        granted=events[index+1];shape(granted,'type at slot start_sha256 attempt')
        require(granted['type']=='supervised_standing_attempt_authorized' and granted['slot']==slot and
                granted['start_sha256']==digest(start) and stamp(start['at'])<=stamp(granted['at'])<stamp(start['expires_at']),
                'supervised_standing_binding')
        index+=2
        if index<len(events) and events[index]['type']=='supervised_started':
            row=events[index];shape(row,'type slot at evidence_hash')
            require(row['slot']==slot and row['evidence_hash']==start['evidence_hash'] and
                    stamp(granted['at'])<=stamp(row['at'])<start['expires_at'],'supervised_standing_binding')
            index+=1
            if index<len(events) and events[index]['type'] in ('supervised_completed','supervised_diagnostic'):
                row=events[index]
                require(row['slot']==slot and stamp(row['at'])>=events[index-1]['at'],'supervised_standing_binding')
                if row['type']=='supervised_completed':
                    require(row['request_hash']==start['request_sha256'] and row['reserved_usd']==[3,100],
                            'supervised_standing_binding')
                index+=1
        result.append((start,granted));slot+=1
    return result


def _standing_history(root,events,enrolled,credit):
    from .credit_test import retained_total
    grant=_standing_base(events,enrolled);attempts=_standing_attempts(events,enrolled)
    require(enrolled['root']==list(root.identity) and enrolled['credit']==list(credit.identity) and
            enrolled['credit_file']==file_identity(credit),'supervised_storage_changed')
    require(set(grant['attempts'])==set(map(str,range(1,7))),'supervised_standing_binding')
    for number,pin in grant['attempts'].items():
        h=History(root.directory/f'attempt-{number}')
        require(list(h.identity)==pin['identity'] and digest(h.read())==pin['sha256'],'supervised_standing_history')
    for i,(start,authorized) in enumerate(attempts):
        h=History(root.directory/f"attempt-{start['slot']}")
        require(list(h.identity)==authorized['attempt'],'supervised_storage_changed')
        rows=h.read()
        require(not rows or any(e.get('type')=='supervised_started' and e.get('slot')==start['slot'] for e in events),
                'supervised_standing_history')
        if i+1<len(attempts):
            require(digest(rows)==attempts[i+1][0]['previous_attempt_sha256'],'supervised_standing_history')
        require(len(rows)<=3 and [r['type'] for r in rows]==
                ['bound_send_reserved','bound_send_attempted','bound_send_receipt'][:len(rows)],
                'supervised_standing_history')
        if rows:
            permit=rows[0]['permit']
            require(permit['selection']['run']==(start['historical']['run'] if 'historical' in start else start['captured']['run'] if 'captured' in start else f"synthetic-integration-{start['slot']}") and
                    permit['selection']['request_sha256']==start['request_sha256'] and
                    permit['project']==enrolled['project'] and permit['model']==INTEGRATION_MODEL and
                    permit['maximum_debit']==[3,100],'supervised_standing_history')
        if len(rows)>1:require(rows[1]['request_sha256']==start['request_sha256'],'supervised_standing_history')
    reservations=credit.read();total=retained_total(reservations,enrolled['project'])
    renewal=_promotional_renewal(events,enrolled)
    if renewal:
        count=renewal['credit_count']
        require(len(reservations)>=count and digest(reservations[:count])==renewal['credit_sha256'],'supervised_standing_history')
    require(len(reservations)>=5 and digest(reservations[:5])==grant['credit_sha256'],'supervised_standing_history')
    if attempts:
        require(attempts[0][0]['previous_attempt_sha256']==grant['attempts']['6']['sha256'],'supervised_standing_history')
    known={start['request_sha256'] for start,_ in attempts}
    require(all(r['request_hash'] in known and r['reserved_usd']==[3,100] for r in reservations[5:]) and
            len({r['request_hash'] for r in reservations})==len(reservations),'supervised_standing_history')
    if attempts:
        start=attempts[-1][0];n=start['credit_count']
        require(type(n) is int and n>=5 and len(reservations) in (n,n+1) and
                digest(reservations[:n])==start['credit_sha256'],'supervised_standing_history')
        if len(reservations)==n+1:
            require(reservations[-1]['request_hash']==start['request_sha256'],'supervised_standing_history')
    return grant,attempts,reservations,total


def expected_request(events,enrolled,slot):
    if slot>=7:
        matches=[s for s,_ in _standing_attempts(events,enrolled) if s['slot']==slot]
        require(len(matches)==1,'supervised_standing_binding')
        if 'captured' in matches[0]:
            from .new_case import validate_captured
            return validate_captured(matches[0]['captured'],enrolled['project'])
        if 'historical' in matches[0]:
            from .historical_nano import validate
            return validate(matches[0]['historical'],enrolled['project'])
    return request(f'synthetic-integration-{slot}')


def standing_binding(events,enrolled,selected,slot):
    grant=_standing_base(events,enrolled);attempts=_standing_attempts(events,enrolled)
    require(attempts and slot==attempts[-1][0]['slot'],'supervised_standing_binding')
    start,authorized=attempts[-1]
    e=selected.data
    require(start['evidence_sha256']==selected.sha256 and start['evidence_hash']==digest(e) and
            start['expires_at']==e['expires_at'] and start['project']==e['project']==grant['project'] and
            start['request_sha256']==digest(request_value(expected_request(events,enrolled,slot),captured='captured' in start)) and
            e['observed_at']<=start['at']<e['expires_at'],'supervised_standing_binding')
    return start,authorized


def standing_retained(root,events,enrolled,selected,credit,slot):
    selected.revalidate();e=selected.data;validate_evidence(e,time.time(),standing=True)
    grant,_,_,total=_standing_history(root,events,enrolled,credit)
    start,_=standing_binding(events,enrolled,selected,slot)
    grant=_credit_grant(events,enrolled,slot)
    ceiling=min(rational(grant['ceiling_usd']),rational(e['available_usd']))
    require(e['account_reference']==grant['account_reference'] and e['credit_expires_at']<=grant['credit_expires_at'] and time.time()<grant['credit_expires_at'] and
            rational(start['ceiling_usd'])==ceiling and total<=ceiling,'supervised_standing_credit')
    return ceiling


def authorize_standing(directory,selected):
    """Append authority on the same closed six-attempt history; never send."""
    require(type(selected) is SelectedEvidence,'supervised_evidence_selection')
    selected.revalidate();e=selected.data;validate_evidence(e,time.time(),standing=True)
    root=History(Path(directory))
    with root.transaction(write=True) as (events,append):
        expected=['supervised_enrollment_started','supervised_enrolled','supervised_started',
                  'supervised_reauthorized','supervised_started','supervised_recovery_started',
                  'supervised_recovery_authorized','supervised_started']
        expected+=['supervised_continuation_started','supervised_continuation_authorized','supervised_started','supervised_diagnostic']*3
        require([r['type'] for r in events]==expected,'supervised_standing_history')
        enrolled=events[1]
        require([r['slot'] for r in events if r['type']=='supervised_started']==list(range(1,7)) and
                [r['slot'] for r in events if r['type']=='supervised_diagnostic']==[4,5,6], 'supervised_standing_history')
        require(enrolled['root']==list(root.identity) and enrolled['project']==e['project'],'supervised_enrollment_binding')
        credit=History(root.directory/'credit')
        require(enrolled['credit']==list(credit.identity) and enrolled['credit_file']==file_identity(credit),'supervised_storage_changed')
        reservations=credit.read()
        require(len(reservations)==5 and all(r['reserved_usd']==[3,100] for r in reservations) and
                ledger_total(reservations,e['project'],ceiling=rational([15,100]))==rational([15,100]),
                'supervised_standing_history')
        pins={}
        for slot in range(1,7):
            h=History(root.directory/f'attempt-{slot}');rows=h.read()
            require(list(h.identity)==attempt_pin(events,enrolled,slot),'supervised_storage_changed')
            if slot==1:require(not rows and not any(h.directory.iterdir()),'supervised_standing_history')
            else:
                require(len(rows)==2 and rows[0]['type']=='bound_send_reserved' and rows[1]['type']=='bound_send_attempted',
                        'supervised_standing_history')
                permit=rows[0]['permit'];old_hash=reservations[slot-2]['request_hash']
                require(permit['selection']['run']==f'synthetic-integration-{slot}' and
                        permit['selection']['request_sha256']==rows[1]['request_sha256']==old_hash and
                        permit['project']==e['project'] and permit['model']==INTEGRATION_MODEL and
                        permit['maximum_debit']==[3,100] and permit['input_limit']==CONTEXT_TOKENS and
                        permit['output_limit']==OUTPUT_TOKENS,'supervised_standing_history')
                if slot>=3:
                    index={3:5,4:8,5:12,6:16}[slot];old=events[index];authorized=events[index+1]
                    require(old['prefix_sha256']==digest(events[:index]) and authorized['start_sha256']==digest(old) and
                            old['request_sha256']==old_hash and old['credit_sha256']==digest(reservations[:slot-2]) and
                            old['attempt_sha256']==pins[str(slot-1)]['sha256'],'supervised_standing_history')
            pins[str(slot)]=dict(identity=list(h.identity),sha256=digest(rows))
        selected.revalidate();now=time.time();validate_evidence(e,now,standing=True)
        require(rational(e['available_usd'])>=rational([18,100]),'supervised_standing_credit')
        append(dict(type='supervised_standing_authorized',at=now,project=e['project'],account_reference=e['account_reference'],policy=POLICY,
            ceiling_usd=e['available_usd'],credit_expires_at=e['credit_expires_at'],evidence_sha256=selected.sha256,
            prefix_sha256=digest(events),credit_sha256=digest(reservations),attempts=pins))
    return dict(status='standing_authorized_no_api_call',per_request_usd=[3,100],ceiling_usd=e['available_usd'])


def _prepare_next_locked(root,events,append,selected,*,create,historical=None,captured=None):
    root.require_write_transaction(events)
    require(not (historical and captured),'captured_route_required')
    if captured:
        from .new_case import locked_captured
        held=locked_captured(captured)
        require(held.root is root and held.root_events is events and
                captured['authorization']['root_prefix_sha256']==digest(events),'captured_authority_changed')
    e=selected.data
    require(len(events)>=21,'supervised_standing_missing');enrolled=events[1]
    credit=History(root.directory/'credit')
    grant,attempts,reservations,total=_standing_history(root,events,enrolled,credit)
    grant=_credit_grant(events,enrolled,7+len(attempts))
    require(e['project']==grant['project'] and e['account_reference']==grant['account_reference'] and e['credit_expires_at']<=grant['credit_expires_at'] and
            time.time()<grant['credit_expires_at'],'supervised_standing_credit')
    ceiling=min(rational(grant['ceiling_usd']),rational(e['available_usd']))
    require(total+PER_REQUEST<=ceiling,'supervised_standing_credit')
    if attempts and 'historical' in attempts[-1][0]:
        require(any(e.get('type')=='supervised_started' and e.get('slot')==attempts[-1][0]['slot'] for e in events),'historical_pending_grant')
    if attempts and 'captured' in attempts[-1][0]:
        require(any(e.get('type')=='supervised_started' and e.get('slot')==attempts[-1][0]['slot'] for e in events),'captured_pending_grant')
    if captured:
        authority=captured['authorization']
        for old,_ in attempts:
            if 'captured' not in old:continue
            prior=old['captured']['authorization']
            require(all(k in prior for k in ('material_hash','disclosure_material_hash','capture_event')),'captured_authority_changed')
            require(prior['material_hash']!=authority['material_hash'] and
                prior['disclosure_material_hash']!=authority['disclosure_material_hash'],'captured_generation_consumed')
            if (prior['case']['source']==authority['case']['source'] and
                    prior['capture_event']['id']==authority['capture_event']['id']):
                require(prior['capture_event']==authority['capture_event'] and
                    prior['case']['case_id']==authority['case']['case_id'],'captured_selection_changed')
    if historical:
        if 'renewal' in historical:
            from .historical_nano import renewal_history
            renewal_history(root,events,historical,creating=True)
        else:
            require(not any(s.get('historical',{}).get('fingerprint')==historical['fingerprint'] for s,_ in attempts),'historical_assessment_consumed')
    slot=7+len(attempts);target=root.directory/f'attempt-{slot}'
    require(not os.path.lexists(target),'supervised_standing_history')
    prior=digest(History(root.directory/f'attempt-{slot-1}').read())
    selected.revalidate();now=time.time();validate_evidence(e,now,standing=True)
    from .spending import pair
    start=dict(type='supervised_standing_attempt_started',at=now,slot=slot,project=e['project'],policy=POLICY,
        prefix_sha256=digest(events),evidence_sha256=selected.sha256,evidence_hash=digest(e),expires_at=e['expires_at'],
        request_sha256=digest(decode(request(f'synthetic-integration-{slot}'))),credit_sha256=digest(reservations),
        credit_count=len(reservations),previous_attempt_sha256=prior,ceiling_usd=pair(ceiling))
    if grant.get('type')=='supervised_promotional_renewed':start['promotional_renewal_sha256']=digest(grant)
    if historical:
        start['historical']=historical
        start['request_sha256']=digest(historical['request'])
    if captured:
        start['captured']=captured
        start['request_sha256']=digest(captured['request'])
    if not create:return slot
    append(start);target.mkdir(mode=0o700);attempt=History(target)
    append(dict(type='supervised_standing_attempt_authorized',at=time.time(),slot=slot,start_sha256=digest(start),
                attempt=list(attempt.identity)))
    return slot


def prepare_next(directory,selected):
    """Allocate a distinct attempt; partial preparation refuses without repair."""
    require(type(selected) is SelectedEvidence,'supervised_evidence_selection')
    selected.revalidate();validate_evidence(selected.data,time.time(),standing=True)
    root=History(Path(directory))
    with root.transaction(write=True) as (events,append):
        return _prepare_next_locked(root,events,append,selected,create=True)


def run_next(directory,selected):
    require(sys.stdin.isatty() and sys.stderr.isatty(),'supervised_interactive_terminal_required')
    return run(directory,selected,None)


def check_keychain(directory,selected):
    """One-shot credential availability/format only; shared lock, no send authority."""
    require(type(selected) is SelectedEvidence,'supervised_evidence_selection')
    selected.revalidate();e=selected.data;validate_evidence(e,time.time(),standing=True)
    root=History(Path(directory))
    with root.transaction() as (events,_):
        require(len(events)>=21,'supervised_standing_missing')
        grant,attempts,_,total=_standing_history(root,events,events[1],History(root.directory/'credit'))
        grant=_credit_grant(events,events[1],7+len(attempts))
        require(e['project']==grant['project'] and e['account_reference']==grant['account_reference'] and
            time.time()<grant['credit_expires_at'] and e['credit_expires_at']<=grant['credit_expires_at'] and
            total+PER_REQUEST<=min(rational(grant['ceiling_usd']),rational(e['available_usd'])),'supervised_standing_credit')
        selected.revalidate()
        from .keychain_credential import credential
        value=credential(e['project'])
        headers(value,e['project'])
    return dict(status='credential_available_format_only_no_api_call')


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
    continuation.add_argument('--slot',type=int,choices=(4,5,6),default=4)
    standing=sub.add_parser('authorize-standing');standing.add_argument('--evidence',required=True,type=Path)
    renewal=sub.add_parser('renew-promotional');renewal.add_argument('--evidence',required=True,type=Path)
    next_send=sub.add_parser('run-next');next_send.add_argument('--evidence',required=True,type=Path)
    k=sub.add_parser('check-keychain');k.add_argument('--evidence',required=True,type=Path)
    k=sub.add_parser('run-next-keychain');k.add_argument('--evidence',required=True,type=Path)
    k=sub.add_parser('run-historical-keychain');k.add_argument('--evidence',required=True,type=Path);k.add_argument('--slot',required=True,type=int)
    r=sub.add_parser('authorize-historical-renewal');r.add_argument('--evidence',required=True,type=Path);r.add_argument('--authorization',required=True,type=Path);r.add_argument('--authorization-sha256',required=True)
    h=sub.add_parser('authorize-historical');h.add_argument('--evidence',required=True,type=Path);h.add_argument('--input',required=True,type=Path)
    h=sub.add_parser('run-historical');h.add_argument('--evidence',required=True,type=Path);h.add_argument('--slot',required=True,type=int)
    h=sub.add_parser('authorize-captured');h.add_argument('--evidence',required=True,type=Path);h.add_argument('--case-history',required=True,type=Path);h.add_argument('--request-hash',required=True);h.add_argument('--authorization',required=True,type=Path);h.add_argument('--authorization-sha256',required=True)
    h=sub.add_parser('run-captured-keychain');h.add_argument('--evidence',required=True,type=Path);h.add_argument('--slot',required=True,type=int)
    send=sub.add_parser('run');send.add_argument('--evidence',required=True,type=Path)
    send.add_argument('--slot',required=True,type=int,choices=(1,2,3,4,5,6))
    args=parser.parse_args(argv)
    _LAST_DIAGNOSTIC.set(None)
    try:
        if args.action in ('authorize-captured','run-captured-keychain'):
            from .new_case import require_captured_activation,authorize_captured
            require_captured_activation() # Before evidence, case, authority, credential or ledger access.
            selected=read_evidence(args.evidence)
            if args.action=='authorize-captured':
                result=authorize_captured(args.state,selected,args.case_history,args.request_hash,args.authorization,args.authorization_sha256)
            else:result=run(args.state,selected,args.slot,captured=True,keychain=True)
        elif args.action=='enroll':
            selected=read_evidence(args.evidence)
            enroll(args.state,selected);result=dict(status='enrolled_no_api_call')
        elif args.action=='reauthorize':
            previous=read_evidence(args.previous_evidence);selected=read_evidence(args.evidence)
            result=reauthorize(args.state,previous,selected)
        elif args.action=='recover-once':
            result=recover_once(args.state,read_evidence(args.previous_evidence),read_evidence(args.evidence))
        elif args.action=='continue-once':
            result=recover_once(args.state,read_evidence(args.previous_evidence),read_evidence(args.evidence),slot=args.slot)
        elif args.action=='renew-promotional':result=renew_promotional(args.state,read_evidence(args.evidence))
        elif args.action=='authorize-standing':result=authorize_standing(args.state,read_evidence(args.evidence))
        elif args.action=='authorize-historical-renewal':
            from .historical_nano import authorize_renewal
            result=authorize_renewal(args.state,read_evidence(args.evidence),args.authorization,args.authorization_sha256)
        elif args.action=='authorize-historical':
            from .historical_nano import authorize
            result=authorize(args.state,read_evidence(args.evidence),args.input)
        elif args.action=='run-historical':result=run(args.state,read_evidence(args.evidence),args.slot,historical=True)
        elif args.action=='run-next':result=run_next(args.state,read_evidence(args.evidence))
        elif args.action=='check-keychain':result=check_keychain(args.state,read_evidence(args.evidence))
        elif args.action=='run-next-keychain':result=run(args.state,read_evidence(args.evidence),None,keychain=True)
        elif args.action=='run-historical-keychain':result=run(args.state,read_evidence(args.evidence),args.slot,historical=True,keychain=True)
        else:result=run(args.state,read_evidence(args.evidence),args.slot)
        print(encoded(result).decode());return 0
    except (Exception,KeyboardInterrupt) as error:
        # Never print raw exceptions, remote bodies, credentials or a traceback.
        diagnostic=_LAST_DIAGNOSTIC.get() or safe_diagnostic(error)
        print('Supervised synthetic command refused: category='+refusal_category(error)+
              '; action='+args.action+'; '+('request status unconfirmed' if args.action in ('run','run-next','run-historical','run-next-keychain','run-historical-keychain','run-captured-keychain') else 'no API request')+
              '; phase='+diagnostic['phase']+'; reason='+diagnostic['reason']+
              ('; cleanup_reason='+diagnostic['cleanup_reason'] if 'cleanup_reason' in diagnostic else '')+
              '. Retain state; do not retry automatically.',file=sys.stderr)
        return 1


if __name__=='__main__':
    # -m executes this file as __main__; authority imports the canonical module.
    # Use its classes and prompt ContextVar throughout the executable command.
    from ai_movie_investigator.supervised_credit import main as canonical_main
    from ai_movie_investigator.keychain_credential import one_shot_process
    with one_shot_process():
        raise SystemExit(canonical_main())
