"""Manual prepare/complete only. No generation, source lookup or AI authentication.

The operator independently verifies the chat/artifact provenance. Local hashes
bind supplied bytes, not their author. Historical proposals cannot enter pilot.
"""
import hashlib
import os
import re
import time
from pathlib import Path

from .contracts import Refusal, decode, digest, encoded, require, shape, text
from .history import History, FILENAME, checked
from .manual_offline import private_chain, read_private, parse_packet, build_request, safe_acl, identity
from .responses_protocol import schema_value


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def schema():
    def obj(p):
        return dict(type='object', properties=p, required=list(p), additionalProperties=False)
    string = dict(type='string')
    strings = dict(type='array', items=string, maxItems=48)
    return obj(dict(assessment_id=string, input_sha256=string, request_sha256=string,
        kind=dict(type='string', enum=['supervised_historical_assessment']),
        status=dict(type='string', enum=['historical_candidate_proposal', 'unresolved', 'blocked']),
        candidate=dict(anyOf=[obj(dict(imdb=string, tmdb=dict(type='integer'), title=string, year=dict(type='integer'))), dict(type='null')]),
        support=dict(type='array', maxItems=16, items=obj(dict(path=string, value=string))),
        rationale=string, uncertainty=string, contradictions=strings, missing_facts=strings,
        disposition=dict(type='string', enum=['human_review_no_approval'])))


def context(packet, fingerprint, prepared_at):
    binding, _, _, raw = build_request(packet, fingerprint, now=prepared_at)
    aid = digest(dict(binding=binding, input_sha256=fingerprint, prepared_at=prepared_at,
                      purpose='supervised_historical_assessment'))
    request = decode(raw, 65536)
    data = decode(request['input'][0]['content'][0]['text'], 32768)
    data['assessment_id'] = aid
    data['qualifications']['output_limit'] = 'historical proposal or unresolved or blocked; human review, no approval'
    request['input'][0]['content'][0]['text'] = encoded(data).decode()
    request['text']['format']['schema'] = schema()
    # This is a request template for this chat, not an API model invocation.
    raw = encoded(request)
    require(len(raw) <= 65536, 'manual_request_size')
    return dict(assessment_id=aid, binding=binding, input_sha256=fingerprint,
                request_sha256=sha(raw), prepared_at=prepared_at), raw, data


def write_once(dfd, name, raw):
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=dfd)
    try:
        before = os.fstat(fd); checked(before); acl = safe_acl(fd, False)
        with os.fdopen(fd, 'wb', closefd=False) as stream:
            stream.write(raw); stream.flush(); os.fsync(fd)
        after = os.fstat(fd); checked(after)
        require(identity(before) == identity(after) == identity(os.stat(name, dir_fd=dfd, follow_symlinks=False))
                and safe_acl(fd, False) == acl, 'manual_artifact_changed')
        os.fsync(dfd)
    finally:
        os.close(fd)


def prepare(input_path, directory):
    raw = read_private(input_path)
    packet, fingerprint = parse_packet(raw)
    require(packet['kind'] == 'historical_expanded_projection', 'manual_full_input_required')
    selected, request, data = context(packet, fingerprint, time.time())
    directory = Path(directory)
    with private_chain(directory) as dfd:
        history = History(directory)
        with history.transaction(write=True) as (events, append):
            require(not events and set(os.listdir(dfd)) == {FILENAME}, 'manual_directory_consumed')
            append(dict(type='manual_prepare_started', selection=selected))
            for name, body in [('input.json', raw), ('request.json', request),
                               ('model-input.json', encoded(data)), ('selection.json', encoded(selected))]:
                write_once(dfd, name, body)
            append(dict(type='manual_prepared', selection=selected))
    return selected


def constraints(data):
    o = data['historical_observations']
    conflicts = {data['facts']['contradiction']}
    for row in o['candidate_conflicts']:
        conflicts.update(row['contradictions'] or [])
        conflicts.update(row['source_contradictions'] or [])
    missing = set(o['missing_fields']) | {'currentness', 'complete occurrence decisions', 'physical source identity',
        'edition and suitability', 'identity approval', 'acquisition approval'}
    return sorted(conflicts), sorted(missing)


def resolve(data, path):
    require(isinstance(path, str) and len(path) <= 250 and
            path.startswith(('historical_observations/', 'qualifications/', 'facts/')), 'manual_evidence_path')
    value = data
    for key in path.split('/'):
        if isinstance(value, list):
            require(key.isdigit() and str(int(key)) == key and int(key) < len(value), 'manual_evidence_path')
            value = value[int(key)]
        else:
            require(isinstance(value, dict) and key in value, 'manual_evidence_path')
            value = value[key]
    require(len(encoded(value)) <= 2048, 'manual_evidence_size')
    return value


def validate_answer(answer, selected, data):
    schema_value(answer, schema())
    for k in ('assessment_id', 'input_sha256', 'request_sha256'):
        require(answer[k] == selected[k], 'manual_reply_binding')
    text(answer['rationale'], 1600); text(answer['uncertainty'], 1600)
    require(answer['rationale'].strip() and answer['uncertainty'].strip(), 'manual_reasoning_missing')
    conflicts, missing = constraints(data)
    require(answer['contradictions'] == conflicts and answer['missing_facts'] == missing, 'manual_qualifications_missing')
    paths = set()
    for claim in answer['support']:
        require(claim['path'] not in paths and claim['value'] == encoded(resolve(data, claim['path'])).decode(),
                'manual_evidence_claim_mismatch')
        paths.add(claim['path'])
    candidate = answer['candidate']
    require((candidate is not None) == (answer['status'] == 'historical_candidate_proposal'), 'manual_candidate_status')
    if candidate is not None:
        rows = data['historical_observations']['catalogue']
        found = [(i, r) for i, r in enumerate(rows) if r['method'] == 'find']
        details = [(i, r) for i, r in enumerate(rows) if r['method'] == 'details']
        require(len(found) == len(details) == 1, 'manual_crosswalk_missing')
        fi, f = found[0]; di, d = details[0]; record = d['data']
        require(f['reason'] == d['reason'] == 'ok' and f['observed_at'] is not None and d['observed_at'] is not None
                and f['observed_at'] <= selected['prepared_at'] and d['observed_at'] <= selected['prepared_at'],
                'manual_catalogue_observation_unknown')
        require(isinstance(record['date'], str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', record['date']), 'manual_catalogue_date')
        require(candidate == dict(imdb=record['imdb'], tmdb=record['id'], title=record['title'], year=int(record['date'][:4]))
                and candidate['imdb'] == f['query'] and
                any(m['id'] == candidate['tmdb'] for m in (f['data']['movies'] or [])), 'manual_candidate_unsupported')
        require({f'historical_observations/catalogue/{fi}/data/movies',
                 f'historical_observations/catalogue/{di}/data/imdb',
                 f'historical_observations/catalogue/{di}/data/id',
                 f'historical_observations/catalogue/{di}/data/title',
                 f'historical_observations/catalogue/{di}/data/date'} <= paths, 'manual_candidate_citations_missing')
    require(bool(paths), 'manual_evidence_missing')
    return answer


def complete(directory, reply_path, provenance_path):
    reply = read_private(reply_path, 16384)
    provenance_raw = read_private(provenance_path, 4096)
    directory = Path(directory)
    with private_chain(directory) as dfd:
        history = History(directory)
        with history.transaction(write=True) as (events, append):
            require(len(events) == 2 and events[0]['type'] == 'manual_prepare_started'
                    and events[1]['type'] == 'manual_prepared' and events[0]['selection'] == events[1]['selection'],
                    'manual_completion_consumed_or_unprepared')
            selected = events[1]['selection']
            raw = read_private(directory / 'input.json')
            packet, fingerprint = parse_packet(raw)
            expected, request, data = context(packet, fingerprint, selected['prepared_at'])
            require(expected == selected and read_private(directory / 'request.json') == request
                    and read_private(directory / 'model-input.json') == encoded(data)
                    and read_private(directory / 'selection.json') == encoded(selected), 'manual_prepared_changed')
            # Reserve before writing supplied originals or validating. An interrupted
            # or rejected completion cannot be retried with changed bytes.
            append(dict(type='manual_completion_started', reply_sha256=sha(reply), provenance_sha256=sha(provenance_raw)))
            write_once(dfd, 'reply.json', reply)
            write_once(dfd, 'provenance.json', provenance_raw)
            try:
                answer = validate_answer(decode(reply, 16384), selected, data)
                provenance = decode(provenance_raw, 4096)
                shape(provenance, 'chat_id source_reference reply_sha256')
                require(isinstance(provenance['chat_id'], str) and
                        re.fullmatch(r'[a-f0-9-]{36}', provenance['chat_id']), 'manual_provenance_shape')
                text(provenance['source_reference'], 400)
                require(provenance['reply_sha256'] == sha(reply), 'manual_provenance_binding')
            except (Refusal, TypeError, KeyError, IndexError, ValueError):
                append(dict(type='manual_completion_rejected', reply_sha256=sha(reply)))
                raise
            report = dict(kind='validated_supervised_historical_review', selection=selected, assessment=answer,
                reply_sha256=sha(reply), provenance=provenance, provenance_status='external_chat_verification_required',
                qualifications=data['qualifications'], observations=data['historical_observations'],
                simulation=None, software_generated_answer=None, isolated_context=None,
                completion_invoked_generation=False,
                provider_receipt=None, token_bill=None, identity_approval=False, acquisition_approval=False,
                scope='Local byte binding and structured evidence validation only. Retained-case self-hash and source hashes are caller assertions, not archive provenance, source authenticity or current-fact proof. Semantic reasoning, chat authorship, simulation status and context isolation require independent external review. Null provider receipt and token bill mean not recorded, not independently proved absent.')
            body = encoded(report)
            write_once(dfd, 'review-report.json', body)
            append(dict(type='manual_completed', reply_sha256=sha(reply), report_sha256=sha(body)))
    return report
