"""Finite Responses text protocol. Never retain reasoning or remote error bodies."""
import re

from .contracts import MAX_OUTPUT, decode, encoded, require

MODEL = 'gpt-6.1-sol'
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


def parse_response(raw, schema, request_id=None):
    from .responses_http import MAX_RESPONSE
    response = decode(raw, MAX_RESPONSE)
    require(isinstance(response, dict) and response.get('object') == 'response'
            and response.get('status') == 'completed' and response.get('model') == MODEL
            and response.get('error') is None and response.get('incomplete_details') is None,
            'responses_not_completed')
    allowed = set(('id object status model error incomplete_details store background tools tool_choice '
                   'max_output_tokens text output usage access_programs created_at completed_at instructions '
                   'metadata parallel_tool_calls temperature top_p conversation max_tool_calls moderation '
                   'output_text previous_response_id prompt prompt_cache_diagnostics prompt_cache_key '
                   'prompt_cache_options prompt_cache_retention reasoning safety_identifier service_tier '
                   'tool_usage top_logprobs truncation user').split())
    require(not set(response) - allowed and all(response.get(key) is None for key in
            ('conversation', 'previous_response_id', 'prompt', 'output_text'))
            and response.get('tool_usage') in (None, {}), 'responses_unsupported_shape')
    rid = response_id(response.get('id'))
    # Require echoes of the selected privacy/foreground/tool/output contract.
    require(isinstance(response.get('text'), dict), 'responses_contract_changed')
    require(response.get('store') is False and response.get('background') is False
            and response.get('tools') == [] and response.get('tool_choice') == 'none'
            and response.get('max_output_tokens') == OUTPUT_TOKENS
            and response.get('text', {}).get('format') ==
            dict(type='json_schema', name='retained_investigator_v1', strict=True, schema=schema),
            'responses_contract_changed')
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
                    and (opaque is None or isinstance(opaque, str) and len(opaque) <= 16384)
                    and item.get('status') in (None, 'completed'), 'responses_reasoning_shape')
            response_id(item.get('id'))
            continue
        require(set(item) == {'id', 'type', 'role', 'status', 'content'}
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
    usage = response.get('usage')
    require(isinstance(usage, dict) and set(usage) == {'input_tokens', 'input_tokens_details',
            'output_tokens', 'output_tokens_details', 'total_tokens'}, 'responses_usage_required')
    for key, ceiling in (('input_tokens', INPUT_TOKENS), ('output_tokens', OUTPUT_TOKENS),
                         ('total_tokens', INPUT_TOKENS + OUTPUT_TOKENS)):
        require(type(usage[key]) is int and 0 <= usage[key] <= ceiling, 'responses_usage_limit')
    require(usage['input_tokens'] > 0 and usage['output_tokens'] > 0
            and usage['total_tokens'] == usage['input_tokens'] + usage['output_tokens'], 'responses_usage_invalid')
    input_details = usage['input_tokens_details']
    require(isinstance(input_details, dict) and set(input_details) == {'cached_tokens', 'cache_write_tokens'},
            'responses_usage_invalid')
    for detail in ('cached_tokens', 'cache_write_tokens'):
        require(type(input_details[detail]) is int and 0 <= input_details[detail] <= usage['input_tokens'],
                'responses_usage_invalid')
    output_details = usage['output_tokens_details']
    require(isinstance(output_details, dict) and set(output_details) == {'reasoning_tokens'}
            and type(output_details['reasoning_tokens']) is int
            and 0 <= output_details['reasoning_tokens'] <= usage['output_tokens'], 'responses_usage_invalid')
    accounting = dict(response_id=rid, model=MODEL, usage=usage)
    if request_id is not None:
        accounting['request_id'] = response_id(request_id)
    return answers[0], accounting
