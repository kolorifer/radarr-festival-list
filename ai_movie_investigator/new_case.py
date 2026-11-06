"""Disabled supervised new-case path: normalized intake -> chat -> unsent draft.

No historical contract, model process, provider, notification sender or approval.
prepare/complete exchange JSON directly with the supervising chat. There is no
unattended chat bridge: an externally supplied answer is not generation proof.
"""
import argparse
from contextvars import ContextVar
import copy
import re
import sys

from identity_telegram_digest import readable_case
from .contracts import (MAX_INPUT, MAX_OUTPUT, Refusal, decode, digest, encoded,
                        require, scope, shape, stamp, text, validate_packet, reconcile)
from .controller import INSTRUCTIONS, output_schema, validate_final
from .history import History, selected_current, research_dependency
from .responses_protocol import schema_value


_OFFLINE_COMPLETION = ContextVar('new_case_offline_completion', default=None)

def admitted(packet, selection, now):
    validate_packet(packet)
    scope(selection)
    require(selection == packet['binding'], 'selected_occurrence_changed')
    require(packet['hash_basis'] == 'captured_bytes' and packet['event'] is not None
            and selection['occurrence'] is not None, 'captured_occurrence_required')
    require(packet['facts']['route'] == 'eligible' and
            packet['facts']['outcome']['status'] in ('unresolved', 'needs_review'), 'original_route_not_eligible')
    rec = reconcile(packet, now)
    require(rec['admission'] == 'eligible', 'occurrence_not_eligible')
    return rec


def redactor(packet):
    """Exact long references, token-bound short labels; public numeric facts remain typed."""
    local_ids = [packet['binding']['source'], packet['binding']['case_id'],
                 packet['binding']['version'], packet['original_hash']]
    local_ids.extend(str(v) for v in packet['binding']['occurrence'].values())
    for row in packet['evidence']:
        local_ids.extend((row['id'], row['provenance']['origin'], row['provenance']['digest']))
    for row in packet['decisions']:
        local_ids.extend((row['id'], row['issuer'], row['provenance']['origin'], row['provenance']['digest']))
    patterns = [re.escape(v) if len(v) >= 16 else r'(?<![a-zA-Z0-9])' + re.escape(v) + r'(?![a-zA-Z0-9])'
                for v in sorted(set(local_ids), key=len, reverse=True)]
    pattern = re.compile('|'.join(patterns), re.I)
    def minimized(value):
        return pattern.sub('[local reference]', value)
    return minimized


def projection(packet, rec, now):
    """Operational fields stay local; textual references are conservatively redacted."""
    minimized = redactor(packet)
    rows = []; supplied = {}
    for i, original in enumerate(packet['evidence']):
        if original['scope'] != packet['binding'] or original['observed_at'] > now:
            continue
        row = copy.deepcopy(original)
        # Unstructured source text cannot establish runtime/edition facts.
        if row['kind'] == 'source':
            row['claims'] = [c for c in row['claims'] if c not in ('runtime', 'edition')]
        alias = 'evidence-' + str(i + 1)
        supplied[alias] = row
        rows.append(dict(id=alias, kind=row['kind'], candidate=row['candidate'],
            text=minimized(row['text']), claims=row['claims'], observed_at=row['observed_at'], expires_at=row['expires_at'],
            freshness='stale' if row['expires_at'] is not None and row['expires_at'] <= now else 'dated_retained',
            image_references=row['image_references']))
    f = packet['facts']
    facts = dict(title=minimized(f['title']), year=f['year'], imdb=f['imdb'], tmdb=f['tmdb'],
                 asserted_imdb=f['outcome'].get('asserted_imdb'), asserted_tmdb=f['outcome'].get('asserted_tmdb'),
                 reason=f['outcome']['reason'])
    decisions = [dict(kind=r['decision']['kind'], applicability=r['applicability'],
        decided_at=r['decision']['decided_at'], chosen_target=r['decision']['chosen_target'])
        for r in rec['prior_decisions']]
    qualifications = dict(source_authenticity='caller supplied; not independently verified',
        currentness='selected normalized snapshot only; no live queue check',
        decision_coverage='supplied decisions only; completeness unknown', novelty='unknown',
        missing=['physical source identity verification', 'edition and suitability',
                 'identity approval', 'acquisition approval'],
        withheld_evidence=len(packet['evidence']) - len(rows),
        stale_evidence=[r['id'] for r in rows if r['freshness'] == 'stale'],
        catalogue_evidence='present' if any(r['kind'] == 'catalogue' for r in rows) else 'missing',
        source_evidence='present' if any(r['kind'] == 'source' for r in rows) else 'missing',
        image_analysis='not performed', runtime_edition_claims='untyped source claims withheld')
    data = dict(facts=facts, evidence=rows, decisions=decisions, disposition=rec['disposition'],
                conflicting_ids=rec['conflicting_ids'], qualifications=qualifications)
    return data, supplied


def request_for(packet, rec, now):
    data, _ = projection(packet, rec, now)
    # The request binds the entire local packet (including the exact occurrence),
    # but exposes no operational identifiers or authority-bearing receipt.
    binding = digest(dict(purpose='supervised_new_case_draft_v1', packet=digest(packet), prepared_at=now, data=data))
    request = dict(kind='supervised_new_case_handoff', binding_hash=binding,
                   instructions=INSTRUCTIONS.replace('Request only retained lookups. ', '') + ' No lookups; use only supplied evidence. Missing is not a verified negative.',
                   input=data, output_schema=output_schema(), generation_invoked=False)
    require(len(encoded(request)) <= MAX_INPUT, 'handoff_size')
    return request


def prepare(history, packet, selection, *, require_empty=False):
    """Return the actual minimized chat handoff; no manual input/reply file paths."""
    packet = decode(encoded(packet), MAX_INPUT)
    now = stamp(history.clock())
    rec = admitted(packet, selection, now)
    def intake_guard(events):
        if require_empty:require(not events,'offline_history_not_empty')
        # Refused research must not supersede a valid selected snapshot.
        candidate = events if any(e['type'] == 'intake' and e['job'] == digest(packet) for e in events) else [
            *events, dict(type='intake', job=digest(packet), packet=packet)]
        research_dependency(candidate, digest(packet))
    job, _ = history.intake(packet, guard=intake_guard)
    require(job == digest(packet), 'freshness_only_not_new_opportunity')
    with history.transaction(write=True) as (events, append):
        selected_current(events, job)
        research_dependency(events, job)
        require(not any(e.get('job') == job and e['type'] in
                       ('new_case_prepared', 'invocation', 'result') for e in events), 'assessment_already_consumed')
        request = request_for(packet, rec, now)
        append(dict(type='new_case_prepared', job=job, at=now, request=request,
                    request_hash=digest(request), reconciliation_hash=digest(rec)))
    return request


def notification(packet, answer, data, provenance):
    """Existing informational digest format, never Digest.tick or a sender."""
    f = packet['facts']; result = answer['result']
    candidates = [('movie', result['candidate']['tmdb'])] if result['candidate'] else []
    has_evidence = bool(data['evidence'])
    current = any(r['freshness'] != 'stale' for r in data['evidence'])
    body = readable_case(data['facts']['title'], f['year'], f['route'], f['outcome']['reason'],
                         'done', {'assessment': True} if has_evidence else {}, current, candidates)
    lines = ['Movie identification update', '', body,
        'SIMULATED assessment; plumbing test only.' if provenance['mode'] == 'simulation' else
        'Supervised supplied assessment; chat authorship requires external verification.',
        'Assessment: ' + result['status'].replace('_', ' '),
        'Evidence rationale: ' + result['rationale'], 'Uncertainty: ' + result['uncertainty'],
        'Source conflict: ' + f['outcome']['reason'].replace('_', ' '),
        'Conflicting IDs: ' + ('present; unresolved' if data['conflicting_ids'] else 'none established in this snapshot'),
        'Prior disposition: ' + data['disposition'].replace('_', ' '),
        'Evidence: catalogue ' + data['qualifications']['catalogue_evidence'] + '; source ' +
        data['qualifications']['source_evidence'] + '; stale ' + str(len(data['qualifications']['stale_evidence'])) +
        '; withheld scope or future rows ' + str(data['qualifications']['withheld_evidence']) + '.',
        'Selected occurrence only. Live currentness, complete decisions and source authenticity are unverified.',
        'Physical source, edition and suitability remain unverified. Images were not analysed.',
        'No correction or download performed. Any proposed identity correction needs your review in the main ChatGPT conversation.',
        'DRAFT ONLY — not sent; no approval buttons or download authority.']
    rendered = redactor(packet)('\n'.join(lines))
    require(len(rendered.encode('utf-8')) <= 4096, 'notification_draft_size')
    return dict(kind='investigator_notification_draft', text=rendered, sent=False,
                acknowledged=False, identity_approval=False, acquisition_approval=False)


def complete(history, request_hash, answer, provenance):
    """Validate a directly supplied chat answer and persist an unsent draft once.

    A rejected/interrupted completion is consumed. No acquisition, resend or
    generation is attempted; immutable history remains inspectable.
    """
    answer = decode(encoded(answer), MAX_OUTPUT)
    provenance = decode(encoded(provenance), 4096)
    with history.transaction(write=True) as (events, append):
        prepared = [e for e in events if e['type'] == 'new_case_prepared' and e['request_hash'] == request_hash]
        require(len(prepared) == 1, 'unknown_handoff')
        p = prepared[0]; job = p['job']
        simulated = [e for e in events if e['type']=='new_case_simulated_send_started' and e['job']==job]
        simulation_receipt = None
        if simulated:
            token = _OFFLINE_COMPLETION.get()
            receipts = [e for e in events if e['type']=='new_case_simulated_response' and e['job']==job]
            require(len(simulated)==1 and len(receipts)==1 and token is not None and
                    token[0] is history and token[1:]==(request_hash,digest(answer),digest(receipts[0])),
                    'simulated_completion_unbound')
            simulation_receipt = receipts[0]
        require(not any(e['type'] == 'new_case_completion_started' and e['job'] == job for e in events),
                'completion_already_consumed')
        append(dict(type='new_case_completion_started', job=job, at=stamp(history.clock()),
                    reply_hash=digest(answer), provenance=provenance))
        try:
            selected_current(events, job)
            research_dependency(events, job)
            packet = next(e['packet'] for e in events if e['type'] == 'intake' and e['job'] == job)
            now = stamp(history.clock())
            require(now >= p['at'], 'clock_rollback')
            rec = admitted(packet, packet['binding'], now)
            require(digest(rec) == p['reconciliation_hash'], 'decision_or_evidence_applicability_changed')
            request = request_for(packet, rec, p['at'])
            require(request == p['request'] and digest(request) == request_hash, 'handoff_changed')
            shape(provenance, 'mode chat_reference')
            require(provenance['mode'] in ('simulation', 'supervised_supplied'), 'assessment_provenance')
            text(provenance['chat_reference'], 240)
            require(provenance['chat_reference'].strip(), 'assessment_provenance')
            schema_value(answer, output_schema())
            require(answer['binding_hash'] == request['binding_hash'] and answer['kind'] == 'final'
                    and answer['lookups'] == [] and answer['result'] is not None, 'reply_handoff_binding')
            data, supplied = projection(packet, rec, p['at'])
            validate_final(answer['result'], supplied, rec, now)
            data, _ = projection(packet, rec, now)
            draft = notification(packet, answer, data, provenance)
            report = dict(kind='supervised_new_case_review', job=job, binding=packet['binding'],
                request_hash=request_hash, reply_hash=digest(answer), assessment=answer['result'],
                provenance=provenance, provenance_verified=False, generation_invoked=False,
                qualifications=data['qualifications'], draft=draft)
            if simulation_receipt is not None:
                report.update(simulated_transport_invoked=True, simulated_response_hash=digest(simulation_receipt))
            append(dict(type='new_case_completed', job=job, at=now, report=report, report_hash=digest(report)))
            return report
        except (ValueError, TypeError, KeyError, IndexError):
            append(dict(type='new_case_completion_rejected', job=job, at=stamp(history.clock())))
            raise


def offline_request(request):
    """Serialize the existing minimized handoff; this grants no network authority."""
    from .credit_test import POLICY
    from .responses_protocol import OUTPUT_TOKENS
    require(request['kind']=='supervised_new_case_handoff' and request['generation_invoked'] is False,
            'handoff_changed')
    body=encoded(dict(**POLICY,instructions=request['instructions'],
        input=[dict(role='user',content=[dict(type='input_text',text=encoded(dict(
            binding_hash=request['binding_hash'],input=request['input'])).decode())])],
        tools=[],tool_choice='none',store=False,background=False,stream=False,
        max_output_tokens=OUTPUT_TOKENS,truncation='disabled',text=dict(format=dict(
            type='json_schema',name='retained_investigator_v1',strict=True,schema=output_schema()))))
    require(len(body)<=65536,'handoff_size')
    return body


def assess_offline(history,packet,selection,frame,*,enabled=False):
    """One simulated transport invocation, never model generation or live authority.

    A static response frame exercises the actual serializer/framing/parser. Its
    receipt proves only local fixture correlation. No supplied-answer fallback
    may finish an uncertain simulated invocation, and prepare forbids replay.
    """
    from .responses_http import SimulatedHTTP,ExplicitCredential,SYNTHETIC_CREDENTIAL,SYNTHETIC_PROJECT,PATH
    from .responses_protocol import parse_response,INTEGRATION_MODEL
    require(enabled is True,'offline_assessment_disabled')
    require(type(frame) is bytes and len(frame)<=40960,'offline_transport_required')
    packet=decode(encoded(packet),MAX_INPUT)
    admitted(packet,selection,stamp(history.clock()))
    # Finite invented fixture only; this is not a generic offline movie runner.
    from .replay import synthetic_case
    from .contracts import captured_outcome
    raw,binding,evidence=synthetic_case(165)
    fixture=captured_outcome(encoded(raw),sources={'synthetic':'Synthetic Index'},binding=binding,
        evidence=evidence,decisions=[],trusted_issuers=['synthetic_owner'])
    require(packet==fixture,'offline_fixture_required')
    http=SimulatedHTTP([frame])
    request=prepare(history,packet,selection,require_empty=True);request_hash=digest(request);job=digest(packet)
    body=offline_request(request)
    with history.transaction(write=True) as (events,append):
        selected_current(events,job);research_dependency(events,job)
        require(not any(e.get('job')==job and e['type'] in ('new_case_completion_started',
            'new_case_completed','new_case_completion_rejected','new_case_simulated_send_started')
            for e in events),'completion_already_consumed')
        append(dict(type='new_case_simulated_send_started',job=job,at=stamp(history.clock()),
                    request_hash=request_hash,wire_hash=digest(decode(body)),simulated=True))
    result=http.post(body,credential=ExplicitCredential(SYNTHETIC_CREDENTIAL),project=SYNTHETIC_PROJECT,timeout=25)
    require(http.framed_result is result and result.status==200 and result.request_sha256==digest(decode(body)) and
            result.project==SYNTHETIC_PROJECT and result.path==PATH,'simulated_response_unbound')
    answer,accounting=parse_response(result.body,output_schema(),result.request_id,expected_model=INTEGRATION_MODEL)
    answer=decode(answer,MAX_OUTPUT)
    receipt=dict(type='new_case_simulated_response',job=job,at=stamp(history.clock()),
        request_hash=request_hash,wire_hash=digest(decode(body)),reply_hash=digest(answer),
        accounting=accounting,simulated=True,provider_verified=False,request_count=len(http.requests))
    with history.transaction(write=True) as (events,append):
        selected_current(events,job);research_dependency(events,job)
        append(receipt)
    marker=_OFFLINE_COMPLETION.set((history,request_hash,digest(answer),digest(receipt)))
    try:
        return complete(history,request_hash,answer,dict(mode='simulation',chat_reference='Offline framed transport fixture; no real generation'))
    finally:_OFFLINE_COMPLETION.reset(marker)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('prepare', 'complete'))
    parser.add_argument('--history-dir', required=True)
    args = parser.parse_args()
    try:
        data = decode(sys.stdin.buffer.read(MAX_INPUT + 1), MAX_INPUT)
        history = History(args.history_dir)
        if args.operation == 'prepare':
            shape(data, 'packet selection')
            output = prepare(history, data['packet'], data['selection'])
        else:
            shape(data, 'request_hash answer provenance')
            output = complete(history, data['request_hash'], data['answer'], data['provenance'])
        sys.stdout.buffer.write(encoded(output) + b'\n')
    except (OSError, ValueError, TypeError, KeyError, IndexError):
        parser.exit(2, 'New-case workflow refused; inspect private history. No notification sent.\n')


if __name__ == '__main__':
    main()
