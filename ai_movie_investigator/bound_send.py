"""Parent-selected request/accounting binding; production activation stays closed.

The internal path is exercised with injected trusted-parent and recording-sink
fixtures only. It does not enroll authority or establish prices or live access.
"""
from .contracts import decode, digest, encoded, require, shape, scope, stamp
from .history import History
from .responses_protocol import MODEL, parse_response
from .controller import output_schema
from .spending import rational
from .responses_http import FixedResponsesHTTP


def send(*args, **kwargs):
    raise ValueError('responses_real_authorization_unimplemented')


def _send_bound(history, body, *, case, run, parent, credential):
    """Only trusted integration code supplies parent, never movie data. The HTTP boundary is fixed.

    Keep the whole monetary reservation as a conservative debit. A future real
    verifier must prove that this reservation covers all charges; this module
    makes no claim about prices and never estimates or refunds unknown cost.
    """
    require(type(history) is History, 'binding_history')
    scope(case)
    request = decode(body, 65536)
    require(type(body) is bytes and encoded(request) == body, 'binding_body')
    require(request.get('model') == MODEL, 'binding_model')
    selected = dict(run=run, case=case, request_sha256=digest(request))
    # The trusted parent's result is the sole source of project and limits.
    permit = decode(encoded(parent.authorize(selected, body)), 8192)
    shape(permit, 'selection project model expires_at input_limit output_limit maximum_debit currency')
    require(permit['selection'] == selected and permit['model'] == MODEL, 'binding_authority')
    require(isinstance(permit['project'], str) and permit['project'].startswith('proj_'), 'binding_project')
    require(stamp(permit['expires_at']) > history.clock(), 'binding_expired')
    require(type(permit['input_limit']) is int and permit['input_limit'] > 0 and
            type(permit['output_limit']) is int and permit['output_limit'] > 0 and
            request.get('max_output_tokens') == permit['output_limit'], 'binding_tokens')
    require(rational(permit['maximum_debit']) > 0 and permit['currency'] in ('USD', 'TEST-USD'), 'binding_debit')
    # Per-history single attempt survives restart, changed run IDs and permits.
    with history.transaction(write=True) as (events, append):
        require(not events, 'binding_attempt_consumed')
        require(parent.validate(permit, body) is True, 'binding_parent_refused')
        require(history.clock() < permit['expires_at'], 'binding_expired')
        append(dict(type='bound_send_reserved', permit=permit, at=history.clock()))
        append(dict(type='bound_send_attempted', request_sha256=selected['request_sha256'], at=history.clock()))
    # Exact project and permit cross the existing HTTP interface. Its real
    # implementation still independently refuses all production authorization.
    require(history.clock() < permit['expires_at'], 'binding_expired')
    result = FixedResponsesHTTP().post(body, credential=credential, project=permit['project'],
                       authorization=permit, timeout=25)
    require(result.status == 200, 'binding_response_unknown')
    answer, accounting = parse_response(result.body, output_schema(), result.request_id)
    usage = accounting['usage']
    require(usage['input_tokens'] <= permit['input_limit'] and
            usage['output_tokens'] <= permit['output_limit'], 'binding_usage_unknown')
    # The parent authenticates the returned receipt; parser success alone is not
    # evidence that a provider issued it for this request or selected project.
    require(parent.validate_receipt(permit, result, accounting) is True, 'binding_receipt_refused')
    with history.transaction(write=True) as (events, append):
        require(len(events) == 2 and events[0]['permit'] == permit, 'binding_history_changed')
        append(dict(type='bound_send_receipt', request_sha256=selected['request_sha256'],
                    accounting=accounting, retained_debit=permit['maximum_debit'],
                    currency=permit['currency'], at=history.clock()))
    return answer
