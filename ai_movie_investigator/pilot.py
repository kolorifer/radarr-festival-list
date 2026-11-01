"""Inspectable one-case OFFLINE plan, never authorization or a real budget."""
from .contracts import (MAX_INPUT, decode, digest, encoded, reconcile, require,
                        stamp, validate_packet)
from .controller import INSTRUCTIONS, RetainedTools, output_schema
from .responses_http import ExplicitCredential, SimulatedHTTP, SYNTHETIC_CREDENTIAL
from .responses_protocol import INPUT_TOKENS, OUTPUT_TOKENS
from .responses_transport import ResponsesTransport, SimulatedAuthorization, real_activation_refusal
from .research import RESEARCH_SECONDS, validate_plan
from .spending import COUNTER, POLICY, PRICING, pair, rational

MISSING_LIVE = (
    'authoritative_real_send_verifier', 'current_unresolved_occurrence_and_full_owner_decisions',
    'sanctioned_api_project_key_and_exact_model_access', 'approved_redacted_payload_and_privacy_terms',
    'confirmed_model_default_tier_30m_cache_and_current_prices', 'reviewed_exact_token_counter',
    'explicit_owner_currency_ceiling_and_billing_conditions', 'exact_installed_shared_provider_ledger_epoch_and_code',
    'validated_source_to_provider_material_correspondence', 'provider_access_and_separate_live_research_grant',
    'exact_private_output_and_receipt_storage_grants', 'one_case_execution_grant_and_expiry',
    'current_shared_model_quota_telemetry',
    'reviewed_host_network_dependency_isolation_and_supported_exact_head_ci',
)


def build_plan(history, original, research_plan, *, selected_job, provenance,
               ceiling, expires_at, output_binding=None, receipt_binding=None):
    """No discovery, account reads, token API or live grant validation.

    Caller-selected hashes are inspectable template entries, never verification
    of external facts. Every missing live fact remains missing unconditionally.
    """
    validate_plan(research_plan, original)
    require(provenance in ('synthetic', 'historical_unverified'), 'pilot_provenance')
    now = stamp(history.clock())
    stamp(expires_at)
    require(now < expires_at <= research_plan['expires_at'], 'pilot_expiry')
    events = history.read()
    selected = next((e for e in events if e['type'] == 'intake' and e['job'] == selected_job), None)
    require(selected is not None, 'pilot_input_unknown')
    packet = validate_packet(selected['packet'])
    require(all(packet[k] == original[k] for k in
                ('binding', 'event', 'facts', 'decisions', 'original_hash', 'hash_basis', 'trusted_issuers')),
            'pilot_occurrence_changed')
    latest = [e for e in events if e['type'] == 'intake' and
              e['packet']['binding']['case_id'] == packet['binding']['case_id']][-1]
    completions = [e for e in events if e['type'] == 'research_complete' and e['job'] == selected_job
                   and e['original_job'] == digest(original) and e['plan_hash'] == digest(research_plan)]
    if packet != original:
        require(bool(completions), 'pilot_research_provenance_missing')
    prompt = dict(protocol='retained-investigator-v1', binding_hash=digest(packet['binding']),
                  binding=packet['binding'], facts=packet['facts'], reconciliation=reconcile(packet, now),
                  evidence_index=[{k: row[k] for k in ('id', 'kind', 'observed_at', 'expires_at')}
                                  for row in RetainedTools(packet, now).rows.values()],
                  query_results=[], instruction=INSTRUCTIONS)
    transport = ResponsesTransport(enabled=True, http=SimulatedHTTP([]),
        credential=ExplicitCredential(SYNTHETIC_CREDENTIAL),
        authorization=SimulatedAuthorization(encoded(packet), now, expires_at), clock=lambda: now)
    payload = decode(transport._body(encoded(prompt), output_schema()), 65536)
    from .contracts import Refusal
    from .history import plan_retired, research_dependency
    blockers = list(MISSING_LIVE)
    dependency = selected.get('research_dependency')
    try:
        if packet != original:
            research_dependency(events, selected_job)
        if plan_retired(events, digest(original), digest(research_plan)):
            require(False, 'research_plan_revoked')
    except Refusal as exc:
        blockers.append(str(exc))
    if packet['binding']['occurrence'] is None or packet['event'] is None:
        blockers.append('historical_occurrence_and_source_currentness_unknown')
    if selected_job != latest['job']:
        blockers.append('selected_input_superseded')
    if reconcile(packet, now)['admission'] != 'eligible':
        blockers.append('selected_case_ineligible')
    if any(e['observed_at'] > now or e['expires_at'] is None or e['expires_at'] <= now
           for e in packet['evidence']):
        blockers.append('evidence_freshness_unverified')
    if ceiling is None:
        blockers.append('no_selected_simulated_ceiling')
    for value in (output_binding, receipt_binding):
        require(value is None or isinstance(value, str) and len(value) == 64 and
                all(c in '0123456789abcdef' for c in value), 'pilot_destination_binding')
    plan = dict(schema=1, kind='offline_pilot_plan_not_authority', provenance=provenance,
        selected_job=selected_job, binding=packet['binding'], input_hash=digest(packet),
        original_hash=packet['original_hash'], original_hash_basis=packet['hash_basis'],
        evidence_hash=digest(packet['evidence']), decision_hash=digest(packet['decisions']),
        evidence=packet['evidence'], decisions=packet['decisions'], research_plan=research_plan,
        research_plan_hash=digest(research_plan), research_receipts=completions[-1]['receipts'] if completions else [],
        research_dependency=dependency,
        source_version=packet['binding']['version'], provider_version=research_plan['provider_version'],
        clocks=dict(original_event=packet['event'], selected_at=now, currentness_checked_at=now,
                    currentness_provenance='synthetic_only' if provenance == 'synthetic' else 'unverified',
                    expires_at=expires_at),
        selected_redacted_model_payload=payload, selected_payload_hash=digest(payload),
        request_policy=POLICY, prewarm=False, diagnostics=False,
        limits=dict(model_calls=2, retained_lookups=5, provider_gets=5, input_bytes=MAX_INPUT,
                    input_tokens=INPUT_TOKENS, output_tokens=OUTPUT_TOKENS, output_bytes=8192,
                    model_stage_seconds=60, model_call_seconds=25, research_stage_seconds=RESEARCH_SECONDS),
        pricing=dict(synthetic=True, reviewed_real_identity=None, test_rates=PRICING),
        counter=dict(synthetic=True, test_identity=COUNTER, reviewed_real_identity=None),
        currency='USD', selected_test_ceiling=None if ceiling is None else pair(rational(ceiling)),
        real_owner_ceiling=None, output_binding=output_binding, receipt_binding=receipt_binding,
        missing_live_facts=blockers, real_readiness=False,
        real_refusal=real_activation_refusal(None))
    require(len(encoded(plan)) <= 131072, 'pilot_size')
    plan['plan_hash'] = digest(plan)
    return decode(encoded(plan), 131072)


def validate_pilot(plan, history, original):
    """Rebuild all pins from current retained state; assertions cannot activate."""
    require(plan['plan_hash'] == digest({k: v for k, v in plan.items() if k != 'plan_hash'}),
            'pilot_hash_changed')
    rebuilt = build_plan(history, original, plan['research_plan'], selected_job=plan['selected_job'],
        provenance=plan['provenance'], ceiling=plan['selected_test_ceiling'],
        expires_at=plan['clocks']['expires_at'], output_binding=plan['output_binding'],
        receipt_binding=plan['receipt_binding'])
    require(rebuilt == plan, 'pilot_changed_or_stale')
    return 'blocked_for_real_execution'


def readable_plan(plan):
    return '\n'.join((
        'OFFLINE PILOT PLAN — ' + plan['provenance'] + '; no real identification or authority',
        'Selected occurrence: ' + str(plan['binding']),
        'Input and original hashes: ' + plan['input_hash'] + ' ' + plan['original_hash'],
        'Evidence and decision hashes: ' + plan['evidence_hash'] + ' ' + plan['decision_hash'],
        'Source/provider versions (different schemes): ' + plan['source_version'] + ' ' + plan['provider_version'],
        'Fixed research operations: ' + str(plan['research_plan']['operations']),
        'Selected redacted payload hash: ' + plan['selected_payload_hash'],
        'Request: gpt-6.1-sol; service_tier=default; prompt_cache_options.ttl=30m; no prewarm or diagnostics',
        'Clocks: ' + str(plan['clocks']),
        'Limits: ' + str(plan['limits']) + '; separate stages, at most 120 seconds combined',
        'TEST spending only: USD ' + str(plan['selected_test_ceiling']) + '; not a hard real spending cap',
        'Private output and receipt bindings: ' + str((plan['output_binding'], plan['receipt_binding'])),
        'Real readiness: blocked; ' + '; '.join(plan['missing_live_facts']),
        'No download or remembered-identity approval transfers.'))
