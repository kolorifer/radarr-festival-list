"""Optional inactive Responses adapter; real activation verification is absent.

No key discovery or requests at construction/preflight. No caller booleans,
profile hashes or simulated grants can satisfy real account/privacy/budget
checks. Adding a real authorizer is a separately reviewed engineering change.
"""
from dataclasses import dataclass, field
import time
import uuid

from .contracts import (MAX_INPUT, Refusal, decode, digest, encoded, require,
                        shape, stamp, validate_packet)
from .controller import INSTRUCTIONS, RetainedTools, output_schema
from .responses_http import (ExplicitCredential, FixedResponsesHTTP, SimulatedHTTP,
                             SYNTHETIC_CREDENTIAL, SYNTHETIC_PROJECT)
from .responses_protocol import INPUT_TOKENS, MODEL, OUTPUT_TOKENS, parse_response


@dataclass(frozen=True)
class SimulatedAuthorization:
    """Exact synthetic input and finite time grant. Never a live authorization."""
    packet_json: bytes = field(repr=False)
    issued_at: float
    expires_at: float


def real_activation_refusal(authorization):
    # Deliberately no registered external verifier. A future implementation must
    # authoritatively verify account/project/key/model access, privacy/billing,
    # pricing + durable monetary/token reservation, input/decision/currentness
    # pins, storage/destination grants and stable mandatory network controls.
    # Do not accept a caller's assertions as evidence of those external facts.
    return 'responses_real_authorization_unimplemented'


class ResponsesTransport:
    def __init__(self, *, enabled=False, http=None, credential=None, authorization=None,
                 clock=time.time, monotonic=time.monotonic, spending=None):
        self.enabled = enabled
        self.http = FixedResponsesHTTP() if http is None else http
        self.credential = credential
        self.authorization = authorization
        self.clock = clock
        self.monotonic = monotonic
        self.pending = None
        self.last_accounting = None
        self.used = set()
        self.spending = spending

    def identity(self):
        return dict(transport='openai_responses', model=MODEL, client='fixed_https_v1',
                    simulated=type(self.http) is SimulatedHTTP)

    def audit_identity(self):
        return dict(live_access_verified=False, live_isolation_verified=False,
                    authorization='simulated_only' if type(self.http) is SimulatedHTTP else 'unimplemented')

    def preflight(self):
        # No network, credential discovery, quota probe, metadata or auth reads.
        if self.enabled is not True:
            return 'model_transport_disabled'
        if type(self.http) is not SimulatedHTTP:
            return real_activation_refusal(self.authorization)
        if type(self.authorization) is not SimulatedAuthorization:
            return 'responses_simulation_authorization_missing'
        if self.spending is not None:
            from .spending import SimulatedSpending
            if type(self.spending) is not SimulatedSpending:
                return 'responses_spending_implementation_unknown'
        try:
            now = stamp(self.clock())
            require(stamp(self.authorization.issued_at) <= now < stamp(self.authorization.expires_at)
                    and self.authorization.expires_at - self.authorization.issued_at <= 300,
                    'responses_authorization_stale')
            require(type(self.credential) is ExplicitCredential
                    and self.credential.value == SYNTHETIC_CREDENTIAL, 'simulation_credential_required')
        except (Refusal, TypeError, ValueError):
            return 'responses_simulation_prerequisite_invalid'
        return None

    def _body(self, payload, schema):
        refusal = self.preflight()
        require(refusal is None, refusal or 'responses_denied')
        require(schema == output_schema(), 'responses_schema_unsupported')
        prompt = decode(payload, MAX_INPUT)
        shape(prompt, 'protocol binding_hash binding facts reconciliation evidence_index query_results instruction')
        require(prompt['protocol'] == 'retained-investigator-v1' and prompt['instruction'] == INSTRUCTIONS,
                'responses_input_protocol')
        packet = validate_packet(decode(self.authorization.packet_json, MAX_INPUT))
        require(prompt['binding'] == packet['binding'] and prompt['binding_hash'] == digest(packet['binding'])
                and prompt['facts'] == packet['facts'], 'responses_selected_input_changed')
        from .contracts import reconcile
        require(prompt['reconciliation'] == reconcile(packet, self.clock()), 'responses_decisions_changed')
        tools = RetainedTools(packet, self.clock)
        expected = [{k: r[k] for k in ('id', 'kind', 'observed_at', 'expires_at')} for r in tools.rows.values()]
        require(prompt['evidence_index'] == expected and isinstance(prompt['query_results'], list)
                and len(prompt['query_results']) <= 5, 'responses_selected_input_changed')
        for answer in prompt['query_results']:
            require(isinstance(answer, dict) and 'operation' in answer
                    and tools.lookup(answer['operation']) == answer, 'responses_retained_evidence_changed')
        # Drop instruction from the untrusted user data and use the trusted
        # fixed string as the API instruction. No ambient conversation is read.
        del prompt['instruction']
        body = encoded(dict(model=MODEL, instructions=INSTRUCTIONS,
                            service_tier='default', prompt_cache_options=dict(ttl='30m'),
                            input=[dict(role='user', content=[dict(type='input_text', text=encoded(prompt).decode())])],
                            tools=[], tool_choice='none', store=False, background=False, stream=False,
                            max_output_tokens=OUTPUT_TOKENS, truncation='disabled',
                            text=dict(format=dict(type='json_schema', name='retained_investigator_v1',
                                                  strict=True, schema=schema))))
        require(len(body) <= 65536, 'responses_request_size')
        require(self.credential.value.encode() not in body, 'responses_credential_in_input')
        return body

    def prepare(self, payload, *, schema):
        """Build before durable controller reservation; no HTTP side effect."""
        require(self.pending is None, 'responses_pending_request')
        body = self._body(payload, schema)
        fingerprint = digest(decode(body, 65536))
        require(fingerprint not in self.used, 'responses_request_already_consumed')
        reservation = dict(local_request_id='simulated-' + uuid.uuid4().hex,
                           request_hash=fingerprint, request_bytes=len(body),
                           input_token_ceiling=INPUT_TOKENS, output_token_ceiling=OUTPUT_TOKENS,
                           monetary_reservation='unverified_no_live_send', simulated=True)
        if self.spending is not None:
            reservation['monetary_reservation'] = self.spending.reserve(
                body, reservation, decode(self.authorization.packet_json, MAX_INPUT)['binding'])
        self.pending = (body, reservation, digest(decode(payload, MAX_INPUT)))
        return dict(reservation)

    def complete(self, payload, *, schema, timeout):
        self.last_accounting = None
        require(type(timeout) in (int, float) and 0 < timeout <= 25, 'responses_deadline')
        started = self.monotonic()
        require(self.pending is not None, 'responses_reservation_required')
        body, reservation, prompt_hash = self.pending
        # Consume before any fallible action; no same-object replay on timeout.
        self.pending = None
        self.used.add(reservation['request_hash'])
        require(prompt_hash == digest(decode(payload, MAX_INPUT)) and body == self._body(payload, schema),
                'responses_reserved_input_changed')
        remaining = timeout - (self.monotonic() - started)
        require(remaining > 0, 'responses_deadline_exceeded')
        try:
            if self.spending is not None:
                self.spending.before_send(body, reservation)
                remaining = timeout - (self.monotonic() - started)
                require(remaining > 0, 'responses_deadline_exceeded')
            result = self.http.post(body, credential=self.credential, project=SYNTHETIC_PROJECT, timeout=remaining)
            require(self.monotonic() - started < timeout, 'responses_deadline_exceeded')
            require(result.status == 200, 'responses_http_rejected')
            require(type(result.body) is bytes and self.credential.value.encode() not in result.body
                    and (result.request_id is None or isinstance(result.request_id, str)
                         and self.credential.value not in result.request_id),
                    'responses_credential_echo_refused')
            answer, accounting = parse_response(result.body, schema, result.request_id)
            require(self.credential.value.encode() not in answer and
                    self.credential.value.encode() not in encoded(accounting),
                    'responses_credential_echo_refused')
            require(self.monotonic() - started < timeout, 'responses_deadline_exceeded')
            bound = dict(accounting, local_request_id=reservation['local_request_id'],
                         request_hash=reservation['request_hash'], simulated=True)
            if self.spending is not None:
                self.spending.settle(reservation, bound)
            self.last_accounting = bound
            return answer
        except Refusal:
            raise
        except (OSError, ValueError, TypeError, KeyError, AttributeError):
            raise Refusal('responses_completion_unknown_or_rejected') from None

    def completion_accounting(self):
        return self.last_accounting
