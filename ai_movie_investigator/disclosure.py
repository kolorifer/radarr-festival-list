"""Strict one-generation disclosure projection. Raw retained data stays local."""
import copy
from .contracts import decode, digest, require, shape
from .controller import INSTRUCTIONS, output_schema
from .responses_protocol import MODEL, OUTPUT_TOKENS
from .contracts import encoded

CATALOGUE_FIELDS = ('id', 'imdb', 'title', 'original_title', 'date', 'type', 'runtime')


def row_view(row):
    # Research dependency verification authenticates the original receipt before
    # this projection is called. No parsing of arbitrary source free text.
    facts = {}
    if row['kind'] == 'catalogue':
        require(row['provenance']['origin'] == 'SIMULATED_catalogue', 'pilot_catalogue_origin')
        prefix = 'Synthetic catalogue details evidence '
        require(row['text'].startswith(prefix), 'pilot_catalogue_shape')
        data = decode(row['text'][len(prefix):], 12000)
        facts = {k: data[k] for k in CATALOGUE_FIELDS if k in data}
    # Source free text is not a typed, approved runtime/edition observation.
    # Keep the source identity, but never expose unsupported claim labels.
    claims = [claim for claim in row['claims'] if row['kind'] != 'source' or claim not in ('runtime', 'edition')]
    return dict(kind=row['kind'], candidate=row['candidate'], claims=claims, facts=facts)


def aliases(run):
    return 'run-' + digest(['pilot-run-v1', run])[:24]


def evidence_alias(run, eid):
    return 'evidence-' + digest(['pilot-evidence-v1', run, eid])[:24]


def project(prompt, *, run, disclosure):
    supplied = [r for answer in prompt['query_results'] for r in answer['rows']]
    require(1 <= len(supplied) <= 5 and len({r['id'] for r in supplied}) == len(supplied),
            'pilot_disclosure_rows')
    require(set(disclosure['rows']) == {r['id'] for r in supplied}, 'pilot_disclosure_selection')
    rows = []
    for row in supplied:
        approval = disclosure['rows'][row['id']]
        shape(approval, 'view original_hash')
        view = row_view(row)
        require(view == approval['view'], 'pilot_undisclosed_evidence')
        if row['kind'] == 'source':
            original = {k: v for k, v in row.items() if k != 'freshness'}
            require(digest(original) == approval['original_hash'], 'pilot_unapproved_source')
        else:
            require(approval['original_hash'] is None, 'pilot_catalogue_approval')
        rows.append(dict(alias=evidence_alias(run, row['id']), **view))
    f = prompt['facts']
    facts = dict(title=f['title'], year=f['year'], imdb=f['imdb'], tmdb=f['tmdb'],
                 asserted_imdb=f['outcome'].get('asserted_imdb'), asserted_tmdb=f['outcome'].get('asserted_tmdb'),
                 contradiction=f['outcome']['reason'])
    require(disclosure['facts'] == facts, 'pilot_undisclosed_facts')
    data = dict(protocol='single-pilot-v1', binding_hash=aliases(run), facts=facts,
                conflicting_ids=prompt['reconciliation']['conflicting_ids'], evidence=rows)
    # Explicit construction is shared by private preview and actual wire body.
    return encoded(dict(model=MODEL, instructions=INSTRUCTIONS,
        service_tier='default', prompt_cache_options=dict(ttl='30m'),
        input=[dict(role='user', content=[dict(type='input_text', text=encoded(data).decode())])],
        tools=[], tool_choice='none', store=False, background=False, stream=False,
        max_output_tokens=OUTPUT_TOKENS, truncation='disabled',
        text=dict(format=dict(type='json_schema', name='retained_investigator_v1', strict=True, schema=output_schema()))))


def restore(reply, *, run, disclosure, binding_hash):
    reply = copy.deepcopy(reply)
    shape(reply, 'binding_hash kind lookups result')
    require(reply['binding_hash'] == aliases(run), 'pilot_run_alias_changed')
    require(reply['kind'] == 'final' and reply['lookups'] == [] and reply['result'] is not None,
            'pilot_one_generation_required')
    mapping = {evidence_alias(run, eid): eid for eid in disclosure['rows']}
    for group in [reply['result']] + reply['result']['alternatives']:
        for citation in group['citations']:
            require(citation['evidence_id'] in mapping, 'pilot_citation_alias_unknown')
            original_id = mapping[citation['evidence_id']]
            require(citation['claim'] in disclosure['rows'][original_id]['view']['claims'],
                    'pilot_citation_claim_not_disclosed')
            citation['evidence_id'] = original_id
    reply['binding_hash'] = binding_hash
    return reply
