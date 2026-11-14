"""Parent-selected request/accounting binding; production activation stays closed.

The internal path is exercised with injected trusted-parent and recording-sink
fixtures only. It does not enroll authority or establish prices or live access.
"""
from .contracts import decode, digest, encoded, require, shape, scope, stamp, hash_id, text
from .history import History
from .responses_protocol import MODEL, INTEGRATION_MODEL, INTEGRATION_SHUTDOWN, parse_response
from .controller import output_schema
from .spending import rational
from .responses_http import FixedResponsesHTTP


def send(*args, **kwargs):
    raise ValueError('responses_real_authorization_unimplemented')


def _send_bound(history, body, *, case, run, parent, credential, context_sha256=None):
    """Only trusted integration code supplies parent, never movie data. The HTTP boundary is fixed.

    Keep the whole monetary reservation as a conservative debit. A future real
    verifier must prove that this reservation covers all charges; this module
    makes no claim about prices and never estimates or refunds unknown cost.
    """
    from .supervised_authorization import observe_phase
    observe_phase('request_validation')
    require(type(history) is History, 'binding_history')
    scope(case)
    request = decode(body, 65536)
    require(type(body) is bytes and encoded(request) == body, 'binding_body')
    require(request.get('model') in (MODEL, INTEGRATION_MODEL), 'binding_model')
    selected = dict(run=run, case=case, request_sha256=digest(request))
    if context_sha256 is not None:
        selected['local_context_sha256'] = hash_id(context_sha256)
    if type(parent) is HistoricalDiagnosticParent:
        parent.validate_history(history)
        parent.validate_credential(credential)
    # The trusted parent's result is the sole source of project and limits.
    permit = decode(encoded(parent.authorize(selected, body)), 8192)
    fields = 'selection project model expires_at input_limit output_limit maximum_debit currency'
    if 'authority_context_sha256' in permit:
        hash_id(permit['authority_context_sha256'])
        fields += ' authority_context_sha256'
    shape(permit, fields)
    require(permit['selection'] == selected and permit['model'] == request['model'], 'binding_authority')
    require(isinstance(permit['project'], str) and permit['project'].startswith('proj_'), 'binding_project')
    require(stamp(permit['expires_at']) > history.clock(), 'binding_expired')
    require(type(permit['input_limit']) is int and permit['input_limit'] > 0 and
            type(permit['output_limit']) is int and permit['output_limit'] > 0 and
            request.get('max_output_tokens') == permit['output_limit'], 'binding_tokens')
    require(rational(permit['maximum_debit']) > 0 and permit['currency'] in ('USD', 'TEST-USD'), 'binding_debit')
    # Per-history single attempt survives restart, changed run IDs and permits.
    observe_phase('attempt_recording')
    with history.transaction(write=True) as (events, append):
        require(not events, 'binding_attempt_consumed')
        require(parent.validate(permit, body) is True, 'binding_parent_refused')
        require(history.clock() < permit['expires_at'], 'binding_expired')
        append(dict(type='bound_send_reserved', permit=permit, at=history.clock()))
        append(dict(type='bound_send_attempted', request_sha256=selected['request_sha256'], at=history.clock()))
    # Exact project and permit cross the existing HTTP interface. Its real
    # implementation still independently refuses all production authorization.
    require(history.clock() < permit['expires_at'], 'binding_expired')
    if type(parent) is HistoricalDiagnosticParent:
        observe_phase('credit_reservation')
        parent.reserve_credit_test(permit)
    require(history.clock() < permit['expires_at'], 'binding_expired')
    if request['model'] == INTEGRATION_MODEL:
        require(history.clock() < INTEGRATION_SHUTDOWN, 'integration_model_retired')
    from .supervised_authorization import authorization_for, selected_response_contract
    observe_phase('wire_authorization')
    wire_authority = authorization_for('/v1/responses', body, credential, permit['project'], fallback=permit)
    result = FixedResponsesHTTP().post(body, credential=credential, project=permit['project'],
                       authorization=wire_authority, timeout=25)
    require(result.status == 200, 'binding_response_unknown')
    observe_phase('response_parsing')
    _,selected_schema=selected_response_contract(selected['request_sha256'])
    answer, accounting = parse_response(result.body, selected_schema, result.request_id, expected_model=permit['model'], http_result=result)
    usage = accounting['usage']
    require(usage['input_tokens'] <= permit['input_limit'] and
            usage['output_tokens'] <= permit['output_limit'], 'binding_usage_unknown')
    # The parent authenticates the returned receipt; parser success alone is not
    # evidence that a provider issued it for this request or selected project.
    observe_phase('receipt_validation')
    require(parent.validate_receipt(permit, result, accounting) is True, 'binding_receipt_refused')
    observe_phase('receipt_recording')
    with history.transaction(write=True) as (events, append):
        require(len(events) == 2 and events[0]['permit'] == permit, 'binding_history_changed')
        append(dict(type='bound_send_receipt', request_sha256=selected['request_sha256'],
                    accounting=accounting, retained_debit=permit['maximum_debit'],
                    currency=permit['currency'], at=history.clock()))
    observe_phase('receipt_recorded')
    from .supervised_authorization import bind_captured_receipt,bind_snapshot_receipt
    bind_captured_receipt(result,answer)
    bind_snapshot_receipt(result,answer)
    return answer


# An explicit trusted integration input, not an authentication mechanism. The
# operator must pin independently checked originals before constructing this.
# Movie/model data cannot enroll evidence. Production still refuses all sends.
from dataclasses import dataclass, field
from .responses_http import ExplicitCredential, HTTPResult
from .responses_protocol import INPUT_TOKENS, OUTPUT_TOKENS, response_id
from .spending import POLICY, pair
from .pilot_account import COVERAGE


@dataclass(frozen=True)
class OperatorContext:
    record_json: bytes = field(repr=False)
    record_sha256: str
    evidence_pins: tuple
    disclosure_json: bytes = field(default=None, repr=False)


class HistoricalDiagnosticParent:
    """Validate a selected operator evidence bundle for one historical request.

    Pins prove correspondence, not authenticity. Trusted integration supplies
    the context and credential object after independently checking originals.
    No flags, environment discovery, credential reads or external calls occur.
    Fixture contexts exercise this code but cannot open the production gate.
    """
    def __init__(self, context, *, history, credential=None, credit_history=None):
        require(type(context) is OperatorContext and type(history) is History, 'operator_context_missing')
        self.context, self.history, self._credential = context, history, credential
        self._body = self._permit_bytes = None
        self.credit_history = credit_history

    def _record(self):
        import hashlib
        c = self.context
        require(type(c.record_json) is bytes and
                hashlib.sha256(c.record_json).hexdigest() == hash_id(c.record_sha256), 'operator_context_pin')
        r = decode(c.record_json, 32768)
        integration = r.get('mode') in ('synthetic_api_integration','historical_nano_manual','captured_nano_dormant')
        shape(r, 'mode selection project model issued_at expires_at history_identity currency ceiling output_limit evidence' +
              (' credit_history_identity credit_history_file_identity' if integration else ''))
        require(r['mode'] in ('historical_manual_diagnostic', 'synthetic_api_integration','historical_nano_manual','captured_nano_dormant') and type(self._credential) is ExplicitCredential,
                'operator_route_missing')
        require(bool(self._credential.value), 'operator_route_missing')
        require(r['history_identity'] == list(self.history.identity), 'operator_history_changed')
        now = self.history.clock()
        require(stamp(r['issued_at']) <= now < stamp(r['expires_at']), 'operator_authority_stale')
        require(r['model'] == (INTEGRATION_MODEL if integration else MODEL) and isinstance(r['project'], str) and
                __import__('re').fullmatch(r'proj_[A-Za-z0-9_-]+', r['project']), 'operator_account_unknown')
        output_limit=OUTPUT_TOKENS
        if r['mode'] in ('historical_nano_manual','captured_nano_dormant'):
            from .supervised_authorization import selected_output_limit
            output_limit=selected_output_limit(r['selection']['request_sha256'])
        require(r['currency'] in ('USD', 'TEST-USD') and rational(r['ceiling']) > 0 and
                type(r['output_limit']) is int and r['output_limit'] == output_limit, 'operator_limits_unknown')
        if integration:
            require(type(self.credit_history) is History and self.credit_history is not self.history and
                    self.credit_history.identity != self.history.identity and
                    list(self.credit_history.identity) == r['credit_history_identity'], 'credit_history_missing')
            require(rational(r['ceiling']) <= rational([3,100]) and now < INTEGRATION_SHUTDOWN and
                    r['expires_at'] <= INTEGRATION_SHUTDOWN, 'credit_scope_or_model_expired')
        roles = {'owner', 'privacy', 'account', 'credential_route', 'coverage', 'pricing'}
        require(type(r['evidence']) is dict and set(r['evidence']) == roles and
                type(c.evidence_pins) is tuple and len(c.evidence_pins) == len(roles), 'operator_evidence_missing')
        pins = dict(c.evidence_pins)
        require(set(pins) == roles, 'operator_evidence_missing')
        binding = digest({k: v for k, v in r.items() if k != 'evidence'})
        for role, e in r['evidence'].items():
            shape(e, 'binding_hash issuer reference observed_at expires_at facts')
            require(digest(e) == hash_id(pins[role]) and e['binding_hash'] == binding,
                    'operator_evidence_pin')
            require(isinstance(e['issuer'], str) and e['issuer'] not in ('', 'unknown') and
                    isinstance(e['reference'], str) and e['reference'] not in ('', 'unknown'), 'operator_evidence_unknown')
            require(stamp(e['observed_at']) <= now < stamp(e['expires_at']) and
                    r['expires_at'] <= e['expires_at'], 'operator_evidence_stale')
        return r

    def validate_credential(self, credential):
        require(credential is self._credential and type(credential) is ExplicitCredential,
                'operator_credential_route_changed')
        return True

    def validate_history(self, history):
        require(history is self.history, 'operator_history_changed')
        return True

    def _permit(self, selected, body):
        r = self._record()
        integration = r['mode'] in ('synthetic_api_integration','historical_nano_manual','captured_nano_dormant')
        from .credit_test import POLICY as CREDIT_POLICY, request as credit_request, CONTEXT_TOKENS, CONTEXT_COVERAGE
        policy = CREDIT_POLICY if integration else POLICY
        shape(selected, 'run case request_sha256 local_context_sha256')
        scope(selected['case'])
        require(selected == r['selection'] and
                (selected['case']['occurrence'] is not None if r['mode']=='captured_nano_dormant' else selected['case']['occurrence'] is None),
                'operator_selection_changed')
        hash_id(selected['local_context_sha256'])
        request = decode(body, 65536)
        require(encoded(request) == body and digest(request) == selected['request_sha256'], 'operator_request_changed')
        require(self._credential.value.encode() not in body and
                self._credential.value.encode() not in self.context.record_json, 'operator_credential_disclosed')
        from .controller import INSTRUCTIONS
        instructions,schema=INSTRUCTIONS,output_schema()
        if r['mode'] in ('historical_nano_manual','captured_nano_dormant'):
            from .supervised_authorization import selected_response_contract
            instructions,schema=selected_response_contract(selected['request_sha256'])
        require(request.get('instructions') == instructions and request.get('model') == r['model'] and
                request.get('text') == dict(format=dict(type='json_schema', name='retained_investigator_v1',
                    strict=True, schema=schema)) and
                all(request.get(k) == v for k, v in policy.items()) and
                request.get('tools') == [] and request.get('tool_choice') == 'none' and
                request.get('store') is False and request.get('background') is False and
                request.get('stream') is False and request.get('truncation') == 'disabled' and
                request.get('max_output_tokens') == r['output_limit'], 'operator_request_policy')
        shape(request, 'model instructions service_tier input tools tool_choice store background stream max_output_tokens truncation text' +
              (' prompt_cache_retention' if integration else ' prompt_cache_options'))
        require(type(request['input']) is list and len(request['input']) == 1, 'operator_disclosure_changed')
        message = request['input'][0]
        shape(message, 'role content')
        require(message['role'] == 'user' and type(message['content']) is list and len(message['content']) == 1,
                'operator_disclosure_changed')
        part = message['content'][0]
        shape(part, 'type text')
        require(part['type'] == 'input_text', 'operator_disclosure_changed')
        from .contracts import MAX_INPUT
        data = decode(part['text'], MAX_INPUT if r['mode']=='captured_nano_dormant' else 32768)
        from .supervised_authorization import selected_snapshot_request
        is_snapshot = r['mode']=='historical_nano_manual' and selected_snapshot_request(selected,body)
        if r['mode']=='captured_nano_dormant':
            from .supervised_authorization import selected_captured_request
            selected_captured_request(selected,body)
            require(self.context.disclosure_json==encoded(data),'operator_expanded_disclosure_unpinned')
            expanded=True
        elif is_snapshot:
            require(self.context.disclosure_json==encoded(data),'operator_expanded_disclosure_unpinned')
            expanded=True
        else:
            expanded = 'historical_observations' in data or 'qualifications' in data
            shape(data, 'protocol binding_hash facts conflicting_ids evidence' +
                  (' historical_observations qualifications' if expanded else ''))
            if r['mode']=='historical_nano_manual':require(expanded,'operator_historical_qualification')
            if r['mode']=='synthetic_api_integration':
                require(body == credit_request(selected['run']), 'credit_synthetic_input_required')
            if expanded:
                # Independently selected exact minimized disclosure, never a model-
                # supplied expansion. Original input pin and complete request remain
                # bound by the trusted operator record and privacy evidence.
                require(type(self.context.disclosure_json) is bytes and
                        self.context.disclosure_json == encoded(data), 'operator_expanded_disclosure_unpinned')
                q = data['qualifications']
                require(isinstance(q, dict) and q.get('historical') is True and
                        q.get('captured_bytes') is False and q.get('authenticated_provider_receipt') is False and
                        q.get('physical_source_verified') is False and
                        q.get('identity_approval') == q.get('acquisition_approval') == 'unknown' and
                        q.get('currentness') == q.get('decisions') == 'unknown', 'operator_historical_qualification')
                require(isinstance(data['historical_observations'], dict), 'operator_expanded_observations')
            from .disclosure import aliases
            require(data['protocol'] == 'single-pilot-v1' and data['binding_hash'] == aliases(selected['run']),
                    'operator_disclosure_changed')
            f = data['facts']
            shape(f, 'title year imdb tmdb asserted_imdb asserted_tmdb contradiction')
            text(f['title'], 200); text(f['contradiction'], 100)
            require(type(f['year']) is int and 1800 <= f['year'] <= 2100 and
                    f['imdb'] is None and f['tmdb'] is None and f['asserted_tmdb'] is None and
                    (f['asserted_imdb'] is None or isinstance(f['asserted_imdb'], str) and
                     __import__('re').fullmatch(r'tt[0-9]{7,10}', f['asserted_imdb'])), 'operator_disclosure_changed')
            require(type(data['evidence']) is list and 1 <= len(data['evidence']) <= 5, 'operator_disclosure_changed')
            for row in data['evidence']:
                shape(row, 'alias kind candidate claims facts')
                require(row['kind'] == 'source' and row['candidate'] is None and row['claims'] == [] and row['facts'] == {},
                        'operator_disclosure_changed')
        facts = {role: e['facts'] for role, e in r['evidence'].items()}
        require(facts['owner'] == dict(operation=r['mode'], max_calls=1, currency=r['currency'], ceiling=r['ceiling']),
                'operator_owner_authority_missing')
        privacy = dict(request_sha256=selected['request_sha256'], store=False, tools=[])
        if expanded:
            privacy['disclosure_sha256'] = digest(data)
        require(facts['privacy'] == privacy,
                'operator_privacy_missing')
        require(facts['account'] == dict(project=r['project'], model=r['model'], policy=policy), 'operator_account_unknown')
        route = facts['credential_route']
        shape(route, 'project injection_route')
        require(route['project'] == r['project'] and isinstance(route['injection_route'], str) and
                route['injection_route'] not in ('', 'unknown'), 'operator_route_missing')
        coverage = facts['coverage']
        shape(coverage, 'request_sha256 policy coverage counter_identity input_upper_bound')
        require(coverage['request_sha256'] == selected['request_sha256'] and coverage['policy'] == policy and
                coverage['coverage'] == (CONTEXT_COVERAGE if integration and r['ceiling']==[3,100] else COVERAGE) and isinstance(coverage['counter_identity'], str) and
                coverage['counter_identity'] not in ('', 'unknown') and type(coverage['input_upper_bound']) is int and
                (coverage['input_upper_bound']==CONTEXT_TOKENS if integration and r['ceiling']==[3,100] else 0<coverage['input_upper_bound']<=INPUT_TOKENS), 'operator_coverage_unknown')
        pricing = facts['pricing']
        shape(pricing, 'policy currency input cache_read cache_write output ancillary_maximum')
        require(pricing['policy'] == policy and pricing['currency'] == r['currency'], 'operator_pricing_unknown')
        rates = {k: rational(pricing[k]) for k in ('input', 'cache_read', 'cache_write', 'output', 'ancillary_maximum')}
        maximum = coverage['input_upper_bound'] * max(rates[k] for k in ('input', 'cache_read', 'cache_write'))
        maximum += r['output_limit'] * rates['output'] + rates['ancillary_maximum']
        require(0 < maximum <= rational(r['ceiling']), 'operator_coverage_above_cap')
        if integration:
            from .credit_test import INPUT_RATE, OUTPUT_RATE, PER_REQUEST
            require(rates['input'] == INPUT_RATE and rates['cache_read'] == INPUT_RATE / 10 and
                    rates['cache_write'] == 0 and rates['output'] == OUTPUT_RATE and
                    rates['ancillary_maximum'] == 0 and rational(r['ceiling']) in (rational([1,100]), PER_REQUEST),
                    'credit_pricing_changed')
            maximum = rational(r['ceiling'])  # Full selected debit survives every outcome.

        return dict(selection=selected, project=r['project'], model=r['model'], expires_at=r['expires_at'],
                    input_limit=coverage['input_upper_bound'], output_limit=r['output_limit'],
                    maximum_debit=pair(maximum), currency=r['currency'], authority_context_sha256=self.context.record_sha256)

    def reserve_credit_test(self, permit):
        if permit['model'] != INTEGRATION_MODEL:
            return
        r = self._record()
        require(permit['project'] == r['project'], 'credit_project_changed')
        from .credit_test import reserve
        reserve(self.credit_history, project=permit['project'],
                request_hash=permit['selection']['request_sha256'],
                input_bound=permit['input_limit'], now=self.history.clock(),
                file_identity=r['credit_history_file_identity'], debit=permit['maximum_debit'])

    def authorize(self, selected, body):
        permit = self._permit(selected, body)
        self._body, self._permit_bytes = bytes(body), encoded(permit)
        return permit

    def validate(self, permit, body):
        require(encoded(permit) == self._permit_bytes and body == self._body and
                permit == self._permit(permit['selection'], body), 'operator_permit_changed')
        return True

    def validate_receipt(self, permit, result, accounting):
        require(self._body is not None and encoded(permit) == self._permit_bytes and
                type(result) is HTTPResult and result.status == 200, 'operator_receipt_unbound')
        require(result.request_sha256 == permit['selection']['request_sha256'] and
                result.project == permit['project'], 'operator_receipt_correlation')
        response_id(result.request_id)
        require(self._credential.value.encode() not in result.body and
                self._credential.value not in result.request_id, 'operator_credential_echo')
        _, parsed = parse_response(result.body, decode(self._body,65536)['text']['format']['schema'], result.request_id, expected_model=permit['model'], http_result=result)
        require(parsed == accounting and parsed['model'] == permit['model'] and
                parsed['usage']['input_tokens'] <= permit['input_limit'] and
                parsed['usage']['output_tokens'] <= permit['output_limit'], 'operator_receipt_mismatch')
        # Correlation comes from the fixed TLS transport, not a provider signature
        # or independent billing attestation. Never accept model-supplied stamps.
        # Retain the entire verified worst-case debit; no price estimate/refund
        # is inferred from a response or from historical budget metadata.
        return True
