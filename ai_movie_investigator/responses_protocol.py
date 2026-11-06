"""Finite Responses text protocol. Never retain reasoning or remote error bodies."""
import re

from .contracts import Refusal, MAX_OUTPUT, decode, encoded, require

MODEL = 'gpt-6.1-sol'
INTEGRATION_MODEL = 'gpt-5-nano-2025-08-07'
INTEGRATION_RETENTION = 'in_memory'  # Explicit synthetic contract; not zero retention.
INTEGRATION_SHUTDOWN = 1796947200  # 2026-12-11 UTC; no automatic replacement
INPUT_TOKENS = 65536
OUTPUT_TOKENS = 4096


def schema_value(value, schema):
    """Validate just the selected investigator schema, including nested limits."""
    if 'anyOf' in schema:
        from .contracts import Refusal
        for option in schema['anyOf']:
            try:
                schema_value(value, option)
                return
            except Refusal:
                pass
        require(False, 'responses_answer_schema')
    kind = schema['type']
    if isinstance(kind, list):
        require(kind == ['string', 'null'] and (value is None or isinstance(value, str)),
                'responses_answer_schema')
        return
    require({'null': value is None, 'string': isinstance(value, str),
             'integer': type(value) is int, 'array': isinstance(value, list),
             'object': isinstance(value, dict)}[kind], 'responses_answer_schema')
    if 'enum' in schema:
        require(value in schema['enum'], 'responses_answer_schema')
    if kind == 'object':
        require(set(value) == set(schema['required']) == set(schema['properties'])
                and schema['additionalProperties'] is False, 'responses_answer_schema')
        for key, child in value.items():
            schema_value(child, schema['properties'][key])
    if kind == 'array':
        require(len(value) <= schema.get('maxItems', 100), 'responses_answer_schema')
        for child in value:
            schema_value(child, schema['items'])


def response_id(value):
    require(isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,160}', value),
            'responses_identity_invalid')
    return value


def parse_response(raw, schema, request_id=None, *, expected_model=MODEL, http_result=None):
    from .responses_http import MAX_RESPONSE
    require(expected_model in (MODEL, INTEGRATION_MODEL), 'responses_model_profile')
    envelope_limit,opaque_limit=MAX_RESPONSE,16384
    if http_result is not None:
        from .supervised_authorization import response_limits
        envelope_limit,opaque_limit=response_limits(http_result,raw,request_id,expected_model)
    response = decode(raw, envelope_limit)
    require(isinstance(response,dict) and response.get('object')=='response','responses_object_invalid')
    require(response.get('model')==expected_model,'responses_model_mismatch')
    require(response.get('error') is None,'responses_error_present')
    status=response.get('status')
    if status=='incomplete':
        detail=response.get('incomplete_details')
        reason=detail.get('reason') if type(detail) is dict else None
        if reason=='max_output_tokens':raise Refusal('responses_incomplete_max_output_tokens')
        if reason=='content_filter':raise Refusal('responses_incomplete_content_filter')
        raise Refusal('responses_incomplete_other')
    if status=='failed':raise Refusal('responses_status_failed')
    if status=='cancelled':raise Refusal('responses_status_cancelled')
    if status=='queued':raise Refusal('responses_status_queued')
    if status=='in_progress':raise Refusal('responses_status_in_progress')
    require(status=='completed','responses_status_other')
    require(response.get('incomplete_details') is None,'responses_incomplete_details_present')
    # Project only fields used by this protocol. Additive envelope metadata is
    # bounded by decode(), never evaluated or returned in accounting.
    require(all(response.get(key) is None for key in
            ('conversation', 'previous_response_id', 'prompt')), 'responses_context_changed')
    validate_tool_usage(response.get('tool_usage'))
    rid = response_id(response.get('id'))
    # Require echoes of the selected privacy/foreground/tool/output contract.
    require(isinstance(response.get('text'), dict), 'responses_contract_changed')
    format_value = response['text'].get('format')
    selected_format = dict(type='json_schema', name='retained_investigator_v1', strict=True, schema=schema)
    require(isinstance(format_value, dict) and set(format_value) <= set(selected_format) | {'description'}
            and all(format_value.get(k) == v for k, v in selected_format.items())
            and format_value.get('strict') is True
            and (format_value.get('description') is None or isinstance(format_value['description'], str)),
            'responses_contract_changed')
    require(response.get('store') is False and response.get('background') is False
            and response.get('tools') == [] and response.get('tool_choice') == 'none'
            and response.get('max_output_tokens') == OUTPUT_TOKENS,
            'responses_contract_changed')
    cache = response.get('prompt_cache_options')
    cache_ok = cache is None if expected_model == INTEGRATION_MODEL else (
        isinstance(cache, dict) and set(cache) <= {'ttl', 'mode', 'comparison_response_id'}
        and cache.get('ttl') == '30m' and cache.get('mode', 'implicit') == 'implicit'
        and cache.get('comparison_response_id') is None)
    require(response.get('service_tier') == 'default' and cache_ok and
            response.get('prompt_cache_diagnostics') is None and
            response.get('prompt_cache_retention') ==
            (INTEGRATION_RETENTION if expected_model == INTEGRATION_MODEL else None) and
            response.get('prompt_cache_key') is None, 'responses_cache_or_tier_changed')
    output = response.get('output')
    require(isinstance(output, list) and 1 <= len(output) <= 3, 'responses_output_shape')
    answers = []
    for item in output:
        require(isinstance(item, dict), 'responses_output_shape')
        if item.get('type') == 'reasoning':
            # The current reference documents opaque encrypted_content by
            # default. Validate its data type, then discard it without logging,
            # hashing, retaining, decrypting or forwarding it to the next call.
            opaque = item.get('encrypted_content')
            require(set(item) <= {'id', 'type', 'summary', 'status', 'content', 'encrypted_content'}
                    and item.get('summary') == [] and item.get('content') in (None, [])
                    and (opaque is None or isinstance(opaque, str) and len(opaque) <= opaque_limit)
                    and item.get('status') in (None, 'completed'), 'responses_reasoning_shape')
            response_id(item.get('id'))
            continue
        require({'id', 'type', 'role', 'status', 'content'} <= set(item)
                <= {'id', 'type', 'role', 'status', 'content', 'phase'}
                and item.get('phase') in (None, 'final_answer')
                and item['type'] == 'message' and item['role'] == 'assistant'
                and item['status'] == 'completed', 'responses_action_or_output_denied')
        response_id(item['id'])
        content = item['content']
        require(isinstance(content, list) and len(content) == 1, 'responses_answer_count')
        part = content[0]
        require(isinstance(part, dict) and set(part) <= {'type', 'text', 'annotations', 'logprobs'}
                and part.get('type') == 'output_text' and part.get('annotations') == []
                and part.get('logprobs') in (None, []), 'responses_text_required')
        answer = decode(part.get('text'), MAX_OUTPUT)
        schema_value(answer, schema)
        answers.append(encoded(answer))
    require(len(answers) == 1, 'responses_answer_count')
    usage = validate_usage(response.get('usage'), legacy=expected_model == INTEGRATION_MODEL)
    policy = dict(model=expected_model, service_tier='default')
    if expected_model == MODEL:
        policy['prompt_cache_options'] = dict(ttl='30m')
    else:
        policy['prompt_cache_retention'] = INTEGRATION_RETENTION
    accounting = dict(response_id=rid, model=expected_model, usage=usage, policy=policy)
    if request_id is not None:
        accounting['request_id'] = response_id(request_id)
    return answers[0], accounting


def validate_usage(usage, *, legacy=False):
    """Exact mandatory usage; writes partition by the selected cache lifetime."""
    require(isinstance(usage, dict) and set(usage) == {'input_tokens', 'input_tokens_details',
            'output_tokens', 'output_tokens_details', 'total_tokens'}, 'responses_usage_required')
    input_ceiling = 400000 if legacy else INPUT_TOKENS
    for key, ceiling in (('input_tokens', input_ceiling), ('output_tokens', OUTPUT_TOKENS),
                         ('total_tokens', input_ceiling + OUTPUT_TOKENS)):
        require(type(usage[key]) is int and 0 <= usage[key] <= ceiling, 'responses_usage_limit')
    require(usage['input_tokens'] > 0 and usage['output_tokens'] > 0
            and usage['total_tokens'] == usage['input_tokens'] + usage['output_tokens'], 'responses_usage_invalid')
    input_details = usage['input_tokens_details']
    require(isinstance(input_details, dict) and {'cached_tokens'} <= set(input_details)
            <= {'cached_tokens', 'cache_write_tokens', 'cache_write_tokens_details'}, 'responses_usage_invalid')
    if legacy:
        require(type(input_details['cached_tokens']) is int and
                0 <= input_details['cached_tokens'] <= usage['input_tokens'], 'responses_usage_invalid')
        writes = input_details.get('cache_write_tokens', 0)
        require(type(writes) is int and writes == 0, 'responses_cache_partition')
        partition = input_details.get('cache_write_tokens_details')
        require(partition is None or zero_counts(partition, {'ttl_30m_tokens', 'ttl_12h_tokens'}),
                'responses_cache_partition')
        output_details = usage['output_tokens_details']
        require(isinstance(output_details, dict) and set(output_details) == {'reasoning_tokens'} and
                type(output_details['reasoning_tokens']) is int and
                0 <= output_details['reasoning_tokens'] <= usage['output_tokens'], 'responses_usage_invalid')
        return dict(usage, input_tokens_details={'cached_tokens': input_details['cached_tokens']})
    require('cache_write_tokens' in input_details, 'responses_usage_invalid')
    for detail in ('cached_tokens', 'cache_write_tokens'):
        require(type(input_details[detail]) is int and 0 <= input_details[detail] <= usage['input_tokens'],
                'responses_usage_invalid')
    # Cached and separately billed cache-write tokens partition the input;
    # accepting both individually must not leave a negative ordinary remainder.
    require(input_details['cached_tokens'] + input_details['cache_write_tokens'] <= usage['input_tokens'],
            'responses_usage_invalid')
    writes = input_details.get('cache_write_tokens_details')
    if writes is None and input_details['cache_write_tokens'] == 0:
        writes = {'ttl_30m_tokens': 0, 'ttl_12h_tokens': 0}
    require(isinstance(writes, dict) and set(writes) == {'ttl_30m_tokens', 'ttl_12h_tokens'} and
            all(type(v) is int and v >= 0 for v in writes.values()) and
            writes['ttl_12h_tokens'] == 0 and
            writes['ttl_30m_tokens'] == input_details['cache_write_tokens'], 'responses_cache_partition')
    output_details = usage['output_tokens_details']
    require(isinstance(output_details, dict) and set(output_details) == {'reasoning_tokens'}
            and type(output_details['reasoning_tokens']) is int
            and 0 <= output_details['reasoning_tokens'] <= usage['output_tokens'], 'responses_usage_invalid')
    return dict(usage, input_tokens_details=dict(input_details, cache_write_tokens_details=writes))


def zero_counts(value, keys):
    return (isinstance(value, dict) and set(value) == keys
            and all(type(v) is int and v == 0 for v in value.values()))


def validate_tool_usage(value):
    """Known zero billing counters are metadata, never permission for a tool."""
    if value is None:
        return
    require(isinstance(value, dict) and set(value) <= {'image_gen', 'web_search'},
            'responses_tool_usage_denied')
    if 'web_search' in value:
        require(zero_counts(value['web_search'], {'num_requests'}), 'responses_tool_usage_denied')
    if 'image_gen' not in value:
        return
    image = value['image_gen']
    required = {'input_tokens', 'output_tokens', 'total_tokens', 'input_tokens_details'}
    optional = {'cached_tokens', 'cached_tokens_details', 'output_tokens_details'}
    require(isinstance(image, dict) and required <= set(image) <= required | optional,
            'responses_tool_usage_denied')
    require(all(type(image[k]) is int and image[k] == 0 for k in
                ('input_tokens', 'output_tokens', 'total_tokens')) and
            zero_counts(image['input_tokens_details'], {'image_tokens', 'text_tokens'}),
            'responses_tool_usage_denied')
    require(image.get('cached_tokens') is None or
            type(image['cached_tokens']) is int and image['cached_tokens'] == 0,
            'responses_tool_usage_denied')
    for key, keys in (('cached_tokens_details', {'cached_image_tokens', 'cached_text_tokens'}),
                      ('output_tokens_details', {'image_tokens', 'text_tokens'})):
        require(image.get(key) is None or zero_counts(image[key], keys), 'responses_tool_usage_denied')
