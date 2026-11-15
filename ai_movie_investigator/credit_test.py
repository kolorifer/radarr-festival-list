"""Fixed synthetic Responses integration profile; no credentials or live authority.

Reuse the existing transport and History. Five-cent cumulative reservations; legacy one-cent debits are retained;
unknown and successful attempts both retain the full debit. Never reset by run.
"""
from fractions import Fraction
from .contracts import decode, digest, encoded, require, stamp, hash_id, shape
from .controller import INSTRUCTIONS, output_schema
from .disclosure import aliases
from .history import History
from .responses_protocol import INTEGRATION_MODEL, INTEGRATION_RETENTION, INTEGRATION_SHUTDOWN, INPUT_TOKENS, OUTPUT_TOKENS

POLICY = dict(model=INTEGRATION_MODEL, service_tier='default', prompt_cache_retention=INTEGRATION_RETENTION)
# Standard USD/token, verified against official model page 2026-11-05.
INPUT_RATE = Fraction(5, 100000000)
OUTPUT_RATE = Fraction(4, 10000000)
PER_REQUEST = Fraction(3, 100)
CONTEXT_TOKENS = 400000
CONTEXT_COVERAGE = "documented-full-model-context-v1"
TOTAL = Fraction(5, 100)

# Purpose-specific Mini v9 profile; legacy constants above remain immutable.
MINI_MODEL='gpt-5-mini-2025-08-07'
MINI_POLICY=dict(model=MINI_MODEL,service_tier='default',prompt_cache_retention='in_memory')
MINI_INPUT_RATE=Fraction(25,100000000)
MINI_OUTPUT_RATE=Fraction(2,1000000)
MINI_DEBIT=Fraction(15,100)
MINI_PROFILE=dict(kind='film_weighing_mini_v9',model=MINI_MODEL,policy=MINI_POLICY,
    context_window=400000,output_limit=25000,input_rate=[25,100000000],cached_input_rate=[25,1000000000],
    output_rate=[2,1000000],reserved_usd=[15,100],paid_fallback=False)


def is_mini(grant):
    return isinstance(grant,dict) and ((grant.get('contract_version')=='film_weighing_v9' and (('weighing_reassessment' in grant) != ('first_assessment' in grant))) or (grant.get('contract_version') in ('film_assessment_v10','film_quality_v11','film_identity_v12') and 'assessment' in grant))


def profile(grant=None):
    return (MINI_MODEL,MINI_POLICY,MINI_INPUT_RATE,MINI_OUTPUT_RATE,MINI_DEBIT) if is_mini(grant) else (INTEGRATION_MODEL,POLICY,INPUT_RATE,OUTPUT_RATE,PER_REQUEST)


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


def retained_total(events, project):
    """Pure ledger validation/sum; this grants no spending authority."""
    require(all(e['type']=='credit_test_reserved' and e['project']==project and
                type(e['reserved_usd']) is list and
                all(type(v) is int for v in e['reserved_usd']) and ((e['model']==INTEGRATION_MODEL and e['reserved_usd'] in ([1,100],[3,100])) or (e['model']==MINI_MODEL and e['reserved_usd']==[15,100] and e.get('model_profile')=='film_weighing_mini_v9'))
                for e in events), 'credit_budget_changed')
    total=sum((Fraction(*e['reserved_usd']) for e in events), Fraction(0))
    return total


def ledger_total(events, project, *, ceiling=TOTAL):
    require(ceiling in (TOTAL, Fraction(6,100), Fraction(9,100), Fraction(12,100), Fraction(15,100)), 'credit_total_ceiling')
    total=retained_total(events,project)
    require(total <= ceiling, 'credit_total_ceiling')
    return total


def reserve(history, *, project, request_hash, input_bound, now, file_identity, debit=(1,100)):
    require(type(history) is History, 'credit_history_missing')
    require(type(file_identity) in (tuple, list) and len(file_identity) == 2 and
            all(type(v) is int and v >= 0 for v in file_identity), 'credit_file_identity')
    hash_id(request_hash)
    require(isinstance(project, str) and __import__('re').fullmatch(r'proj_[A-Za-z0-9_-]+', project), 'credit_project')
    require(stamp(now) < INTEGRATION_SHUTDOWN, 'integration_model_retired')
    from .supervised_authorization import selected_mini_profile
    mini=selected_mini_profile(request_hash)
    require(tuple(debit) in (((15,100),) if mini else ((1,100),(3,100))), 'credit_request_ceiling')
    full_context=mini or tuple(debit)==(3,100)
    require(type(input_bound) is int and (input_bound==CONTEXT_TOKENS if full_context else 0<input_bound<=INPUT_TOKENS), 'credit_input_bound')
    from .supervised_authorization import selected_output_limit
    output_limit=selected_output_limit(request_hash)
    maximum = input_bound * (MINI_INPUT_RATE if mini else INPUT_RATE) + output_limit * (MINI_OUTPUT_RATE if mini else OUTPUT_RATE)
    require(maximum <= Fraction(*debit), 'credit_request_ceiling')
    from .supervised_authorization import reservation_ceiling, selected_reservation_binding
    binding=selected_reservation_binding(history,project,request_hash)
    ceiling=reservation_ceiling(history,project,request_hash)
    with history.transaction(write=True, file_identity=file_identity) as (events, append):
        retained=retained_total(events,project)
        require(not any(e['request_hash'] == binding['request_hash'] for e in events), 'credit_request_consumed')
        require(retained + Fraction(*debit) <= ceiling, 'credit_total_ceiling')
        require(all(now >= e['at'] for e in events), 'credit_clock_rollback')
        append(dict(type='credit_test_reserved', project=project, model=MINI_MODEL if mini else INTEGRATION_MODEL,
                    **({'model_profile':'film_weighing_mini_v9'} if mini else {}), **binding, reserved_usd=list(debit), at=now))
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
