"""Fixed synthetic Responses integration profile; no credentials or live authority.

Reuse the existing transport and History. Five-cent cumulative reservations; legacy one-cent debits are retained;
unknown and successful attempts both retain the full debit. Never reset by run.
"""
from fractions import Fraction
from .contracts import decode, digest, encoded, require, stamp, hash_id, shape
from .controller import INSTRUCTIONS, output_schema
from .disclosure import aliases
from .history import History
from .responses_protocol import INTEGRATION_MODEL, INTEGRATION_SHUTDOWN, INPUT_TOKENS, OUTPUT_TOKENS

POLICY = dict(model=INTEGRATION_MODEL, service_tier='default')
# Standard USD/token, verified against official model page 2026-11-05.
INPUT_RATE = Fraction(5, 100000000)
OUTPUT_RATE = Fraction(4, 10000000)
PER_REQUEST = Fraction(3, 100)
CONTEXT_TOKENS = 400000
CONTEXT_COVERAGE = "documented-full-model-context-v1"
TOTAL = Fraction(5, 100)


def request(run):
    data = dict(protocol='single-pilot-v1', binding_hash=aliases(run), conflicting_ids=False,
        facts=dict(title='Synthetic Example', year=2026, imdb=None, tmdb=None,
                   asserted_imdb=None, asserted_tmdb=None, contradiction='synthetic_missing_evidence'),
        evidence=[dict(alias='synthetic-empty-source', kind='source', candidate=None, claims=[], facts={})])
    return encoded(dict(**POLICY, instructions=INSTRUCTIONS,
        input=[dict(role='user', content=[dict(type='input_text', text=encoded(data).decode())])],
        tools=[], tool_choice='none', store=False, background=False, stream=False,
        max_output_tokens=OUTPUT_TOKENS, truncation='disabled',
        text=dict(format=dict(type='json_schema',name='retained_investigator_v1',strict=True,schema=output_schema()))))


def ledger_total(events, project):
    require(all(e['type']=='credit_test_reserved' and e['project']==project and
                e['model']==INTEGRATION_MODEL and type(e['reserved_usd']) is list and
                all(type(v) is int for v in e['reserved_usd']) and e['reserved_usd'] in ([1,100],[3,100])
                for e in events), 'credit_budget_changed')
    total=sum((Fraction(*e['reserved_usd']) for e in events), Fraction(0))
    require(total <= TOTAL, 'credit_total_ceiling')
    return total


def reserve(history, *, project, request_hash, input_bound, now, file_identity, debit=(1,100)):
    require(type(history) is History, 'credit_history_missing')
    require(type(file_identity) in (tuple, list) and len(file_identity) == 2 and
            all(type(v) is int and v >= 0 for v in file_identity), 'credit_file_identity')
    hash_id(request_hash)
    require(isinstance(project, str) and __import__('re').fullmatch(r'proj_[A-Za-z0-9_-]+', project), 'credit_project')
    require(stamp(now) < INTEGRATION_SHUTDOWN, 'integration_model_retired')
    require(tuple(debit) in ((1,100),(3,100)), 'credit_request_ceiling')
    full_context=tuple(debit)==(3,100)
    require(type(input_bound) is int and (input_bound==CONTEXT_TOKENS if full_context else 0<input_bound<=INPUT_TOKENS), 'credit_input_bound')
    maximum = input_bound * INPUT_RATE + OUTPUT_TOKENS * OUTPUT_RATE
    require(maximum <= Fraction(*debit), 'credit_request_ceiling')
    with history.transaction(write=True, file_identity=file_identity) as (events, append):
        retained=ledger_total(events,project)
        require(not any(e['request_hash'] == request_hash for e in events), 'credit_request_consumed')
        require(retained + Fraction(*debit) <= TOTAL, 'credit_total_ceiling')
        require(all(now >= e['at'] for e in events), 'credit_clock_rollback')
        append(dict(type='credit_test_reserved', project=project, model=INTEGRATION_MODEL,
                    request_hash=request_hash, reserved_usd=list(debit), at=now))
    return list(debit)


def count_request(run):
    """All input-bearing fields, including the output schema; no generation."""
    generation = decode(request(run))
    return encoded({key: generation[key] for key in
                    ('model', 'instructions', 'input', 'text', 'tools', 'tool_choice', 'truncation')})


def count_receipt(result, *, run, project):
    """Correlate fixed-transport stamps; not provider-signed billing proof."""
    from .responses_http import HTTPResult
    from .responses_protocol import response_id
    require(type(result) is HTTPResult and result.status == 200 and
            result.project == project and result.path == '/v1/responses/input_tokens' and
            result.request_sha256 == digest(decode(count_request(run))),
            'credit_count_correlation')
    response_id(result.request_id)
    value = decode(result.body, 1024)
    shape(value, 'object input_tokens')
    require(value['object'] == 'response.input_tokens' and type(value['input_tokens']) is int and
            0 < value['input_tokens'] <= INPUT_TOKENS, 'credit_count_invalid')
    return dict(generation_sha256=digest(decode(request(run))), count_sha256=result.request_sha256,
                project=project, model=INTEGRATION_MODEL, input_tokens=value['input_tokens'],
                request_id=result.request_id)
