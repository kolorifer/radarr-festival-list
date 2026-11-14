"""Disabled supervised new-case path: normalized intake -> chat -> unsent draft.

prepare/complete exchange JSON directly with the supervising chat; externally
supplied answers are not generation proof. The distinct captured generation
route remains default-closed, with no notification sender
or approval authority.
"""
import argparse
import hashlib
from contextvars import ContextVar
from contextlib import contextmanager
from pathlib import Path
import time
import copy
import re
import sys

from identity_telegram_digest import readable_case
from .contracts import (MAX_INPUT, MAX_OUTPUT, Refusal, decode, digest, encoded,
                        require, scope, shape, stamp, text, validate_packet, reconcile,
                        VERIFIED_IDENTITY_CHECK, reconcile_verified_identity_check, capture_qualification)
from .controller import INSTRUCTIONS, output_schema, validate_final
from .history import History, selected_current, research_dependency
from .responses_protocol import schema_value


_OFFLINE_COMPLETION = ContextVar('new_case_offline_completion', default=None)
_CAPTURED = ContextVar('locked_captured_case', default=None)
_CONNECTED_COMPLETION = ContextVar('connected_captured_completion', default=None)
_APPROVED_CAPTURE = ContextVar('approved_captured_wrapper_context', default=None)

def admitted(packet, selection, now, *, purpose=None):
    validate_packet(packet)
    scope(selection)
    require(selection == packet['binding'], 'selected_occurrence_changed')
    require(packet['hash_basis'] == 'captured_bytes' and packet['event'] is not None
            and selection['occurrence'] is not None, 'captured_occurrence_required')
    require(purpose in (None, VERIFIED_IDENTITY_CHECK), 'assessment_purpose')
    if purpose == VERIFIED_IDENTITY_CHECK:
        rec = reconcile_verified_identity_check(packet, now)
    else:
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
    if rec.get('assessment_purpose') == VERIFIED_IDENTITY_CHECK:
        data['assessment_purpose'] = VERIFIED_IDENTITY_CHECK
        data['qualifications']['capture_source_support'] = copy.deepcopy(f.get('capture_qualification',
            dict(scope='not_recorded',correlation='not_recorded',source_support='not_recorded')))
        data['facts']['producer_assertion'] = dict(route=f['route'], status=f['outcome']['status'],
            category=f['outcome']['category'], reason=f['outcome']['reason'], independently_approved=False)
        data['qualifications']['producer_identity'] = 'assertion only; independent identity not established'
    return data, supplied


def request_for(packet, rec, now):
    data, _ = projection(packet, rec, now)
    # The request binds the entire local packet (including the exact occurrence),
    # but exposes no operational identifiers or authority-bearing receipt.
    binding = digest(dict(purpose='supervised_new_case_draft_v1', packet=digest(packet), prepared_at=now, data=data))
    request = dict(kind='supervised_new_case_handoff', binding_hash=binding,
                   instructions=INSTRUCTIONS.replace('Request only retained lookups. ', '') + ' No lookups; use only supplied evidence. Missing is not a verified negative.',
                   input=data, output_schema=output_schema(), generation_invoked=False)
    if rec.get('assessment_purpose') == VERIFIED_IDENTITY_CHECK:
        request['instructions'] += ' Independently check the producer assertion; verified_tmdb is not independent approval or evidence of correctness. Do not assume a conflict. Missing support must remain unresolved or blocked. Capture source support is explicitly qualified; outcome_only means no prior release, retained or selected observation, not strong correlation. This describes retained collector observations at capture, not upstream absence or unpersisted/in-flight events.'
    require(len(encoded(request)) <= MAX_INPUT, 'handoff_size')
    return request


def prepare(history, packet, selection, *, require_empty=False, purpose=None):
    """Return the actual minimized chat handoff; no manual input/reply file paths."""
    packet = decode(encoded(packet), MAX_INPUT)
    now = stamp(history.clock())
    rec = admitted(packet, selection, now, purpose=purpose)
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
        prepared = dict(type='new_case_prepared', job=job, at=now, request=request,
                    request_hash=digest(request), reconciliation_hash=digest(rec))
        if purpose is not None: prepared['assessment_purpose'] = purpose
        append(prepared)
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
        'Receipt-correlated model assessment; identity and acquisition still need review.' if provenance['mode']=='receipt_correlated_generation' else
        'Supervised supplied assessment; chat authorship requires external verification.',
        'Assessment: ' + result['status'].replace('_', ' '),
        'Evidence rationale: ' + result['rationale'], 'Uncertainty: ' + result['uncertainty'],
        ('Producer assertion (not independent approval): ' if data.get('assessment_purpose') == VERIFIED_IDENTITY_CHECK else 'Source conflict: ') + f['outcome']['reason'].replace('_', ' '),
        *(['Capture source support: ' + data['qualifications']['capture_source_support']['source_support'].replace('_',' ') +
           '; correlation: ' + data['qualifications']['capture_source_support']['correlation'] + '; retained collector observations at capture, not upstream absence.']
          if data.get('assessment_purpose') == VERIFIED_IDENTITY_CHECK else []),
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
        return _complete_locked(history, events, append, request_hash, answer, provenance)


def _complete_locked(history, events, append, request_hash, answer, provenance):
    history.require_write_transaction(events)
    prepared = [e for e in events if e['type'] == 'new_case_prepared' and e['request_hash'] == request_hash]
    require(len(prepared) == 1, 'unknown_handoff')
    p = prepared[0]; job = p['job']
    connected = _CONNECTED_COMPLETION.get()
    started = [e for e in events if e['type']=='new_case_generation_started' and e['job']==job]
    if started:
        held=_CAPTURED.get()
        expected_starts=2 if held is not None and 'continuation' in held.grant['authorization'] else 1
        require(len(started)==expected_starts and connected is not None and connected[0] is history and
                connected[1:3]==(request_hash,digest(answer)), 'captured_completion_unbound')
    else:require(connected is None,'captured_completion_unbound')
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
        rec = admitted(packet, packet['binding'], now, purpose=p.get('assessment_purpose'))
        require(digest(rec) == p['reconciliation_hash'], 'decision_or_evidence_applicability_changed')
        request = request_for(packet, rec, p['at'])
        require(request == p['request'] and digest(request) == request_hash, 'handoff_changed')
        shape(provenance, 'mode chat_reference')
        require(provenance['mode'] in ('simulation', 'supervised_supplied') or
                (connected is not None and not connected[3]['simulated'] and
                 provenance['mode']=='receipt_correlated_generation'), 'assessment_provenance')
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
        if p.get('assessment_purpose') is not None:
            report['assessment_purpose'] = p['assessment_purpose']
            report['producer_assertion'] = data['facts']['producer_assertion']
            report['capture_qualification'] = data['qualifications']['capture_source_support']
        if connected is not None:
            simulated=connected[3]['simulated']
            report.update(connected_transport_invoked=True, receipt_hash=connected[3]['receipt_hash'],
                generation_invoked=not simulated, provenance_verified=not simulated,
                transport_provenance='simulated local fixture; unauthenticated' if simulated else
                    'exact fixed TLS transport response correlated to request and project',
                provider_receipt_correlated=not simulated, provider_verified=False)
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



CAPTURED_CONTRACT = 'captured-final-v1'
CAPTURED_OUTPUT_TOKENS = 25000
CAPTURED_REQUEST_BYTES = 65536
CAPTURED_AUTHORITY_BYTES = 131072


class _ApprovedCapture:
    """Exact local wrapper trust, not a provider or owner signature."""
    def __init__(self, path, sha256):
        from .supervised_credit import _read_evidence
        self.path=Path(path);self.sha256=sha256
        raw,self.identity=_read_evidence(self.path,CAPTURED_AUTHORITY_BYTES)
        require(hashlib.sha256(raw).hexdigest()==sha256,'captured_activation_changed')
        self.record=decode(raw,CAPTURED_AUTHORITY_BYTES)
        self.audit = self.record.get('kind') == 'trusted_wrapper_verified_identity_check_v1'
        fields = 'kind owner_scope main_review authority body receipt sources runtime_manifest_sha256 issued_at expires_at'
        shape(self.record, fields + (' capture_grant assessment_purpose' if self.audit else ''))
        require(self.audit or self.record['kind']=='trusted_wrapper_one_captured_case_v1','captured_activation_kind')
        if self.audit: require(self.record['assessment_purpose']==VERIFIED_IDENTITY_CHECK,'assessment_purpose')
        require(raw==encoded(self.record),'captured_activation_canonical')
        self.pins={};self.last_time=stamp(self.record['issued_at'])
        pin_limits = [('owner_scope',32768),('main_review',32768),('authority',CAPTURED_AUTHORITY_BYTES),('body',65536),('receipt',8192)]
        if self.audit: pin_limits.append(('capture_grant',4096))
        for name,limit in pin_limits:
            pin=self.record[name];shape(pin,'path sha256')
            data,identity=_read_evidence(Path(pin['path']),limit)
            require(hashlib.sha256(data).hexdigest()==pin['sha256'],'captured_activation_artifact')
            self.pins[name]=(data,identity,limit)
        self.authority=decode(self.pins['authority'][0],CAPTURED_AUTHORITY_BYTES)
        require(self.pins['authority'][0]==encoded(self.authority),'captured_authority_changed')
        self.receipt=decode(self.pins['receipt'][0],8192)
        shape(self.receipt,'version source channel case_id case_version event_id selection_event delivery_rowid evidence_id source_time received_at grant_sha256 body_sha256 body_bytes privacy api_disclosure_authorized' + (' capture_qualification' if self.audit else ''))
        if self.audit:capture_qualification(self.receipt['capture_qualification'])
        r=self.receipt;body=self.pins['body'][0]
        require(r['version']==1 and r['channel']=='outcome' and r['privacy']=='private_local_raw_observer_body_no_api_disclosure' and r['api_disclosure_authorized'] is False,'captured_receipt_scope')
        require(r['body_sha256']==hashlib.sha256(body).hexdigest() and r['body_bytes']==len(body),'captured_receipt_body')
        if self.audit:
            raw_grant = self.pins['capture_grant'][0]
            g = decode(raw_grant,4096)
            shape(g,'version nonce source channel filter expires_at destination privacy')
            require(hashlib.sha256(raw_grant).hexdigest()==r['grant_sha256'] and g['version']==1 and
                g['source']==r['source'] and g['channel']=='outcome' and
                g['filter']==dict(mode='first_verified_identity_check',category='unknown_movie',status='verified_tmdb',reason='external_id_verified') and
                g['destination']==dict(body='capture-body.json',receipt='capture-receipt.json') and
                g['privacy']==r['privacy'] and stamp(r['received_at'])<stamp(g['expires_at']), 'verified_capture_grant')
        require(self.authority.get('assessment_purpose')==(VERIFIED_IDENTITY_CHECK if self.audit else None),'assessment_purpose')
        self.binding=dict(source=r['source'],case_id=r['case_id'],version=r['case_version'],occurrence=dict(event_id=r['event_id'],delivery_id=r['delivery_rowid']))
        scope(self.binding)
        require(self.authority['case']==self.binding and self.authority['max_calls']==1 and self.authority['maximum_debit_usd']==[3,100],'captured_activation_scope')
        require(self.last_time<stamp(self.record['expires_at'])<=stamp(self.authority['expires_at']),'captured_activation_expiry')
        self.revalidate()

    def revalidate(self):
        from .supervised_credit import _read_evidence
        from .installation import verify_installation
        raw,identity=_read_evidence(self.path,CAPTURED_AUTHORITY_BYTES)
        require(identity==self.identity and hashlib.sha256(raw).hexdigest()==self.sha256 and decode(raw,CAPTURED_AUTHORITY_BYTES)==self.record,'captured_activation_changed')
        now=time.time()
        require(self.last_time<=now<self.record['expires_at'],'captured_activation_expired')
        self.last_time=now
        for name,(raw,identity,limit) in self.pins.items():
            current=_read_evidence(Path(self.record[name]['path']),limit)
            require(current==(raw,identity),'captured_activation_artifact_changed')
        manifest=verify_installation(Path(__file__).resolve().parent.parent)
        require(digest(manifest)==self.record['runtime_manifest_sha256'],'captured_activation_runtime')

    def bind(self,authority,packet=None):
        self.revalidate()
        require(authority==self.authority,'captured_activation_authority')
        if packet is not None:
            from .contracts import captured_outcome
            reconstructed=captured_outcome(self.pins['body'][0],sources=self.record['sources'],binding=self.binding,
                evidence=packet['evidence'],decisions=packet['decisions'],trusted_issuers=packet['trusted_issuers'],
                qualification=self.receipt['capture_qualification'] if self.audit else None)
            require(reconstructed==packet,'captured_activation_packet')
            admitted(packet,self.binding,self.last_time,purpose=VERIFIED_IDENTITY_CHECK if self.audit else None)


@contextmanager
def approved_captured_wrapper(path,sha256):
    """Only for the separately accepted private operational wrapper.

    The caller is the trusted issuer and must independently pin this exact
    main-reviewed record, runtime, invocation and owner scope. A caller-selected
    hash is NOT owner authentication. No ordinary CLI/env option exposes this
    API; arbitrary same-process code is outside this local trust boundary.
    Reading/verifying these local artifacts neither prompts nor sends.
    """
    require(_APPROVED_CAPTURE.get() is None,'captured_activation_nested')
    active=_ApprovedCapture(path,sha256)
    token=_APPROVED_CAPTURE.set(active)
    try:yield
    finally:_APPROVED_CAPTURE.reset(token)


def captured_activation_refusal():
    return None if type(_APPROVED_CAPTURE.get()) is _ApprovedCapture else 'captured_real_activation_unissued'


def require_captured_activation():
    reason = captured_activation_refusal()
    require(reason is None, reason or 'captured_real_activation_unissued')
    active=_APPROVED_CAPTURE.get()
    if active is not None:
        require(type(active) is _ApprovedCapture,'captured_activation_untrusted')
        active.revalidate()


def captured_request(request):
    """Final-only contract retains the original candidate/citation semantics."""
    body = decode(offline_request(request), 65536)
    body['max_output_tokens'] = CAPTURED_OUTPUT_TOKENS
    schema = body['text']['format']['schema']
    schema['properties']['binding_hash']['enum'] = [request['binding_hash']]
    schema['properties']['kind']['enum'] = ['final']
    schema['properties']['lookups']['maxItems'] = 0
    schema['properties']['result'] = schema['properties']['result']['anyOf'][0]
    body['instructions'] += ' Return one final result, never null, with no lookups. Keep rationale and uncertainty each within 600 characters.'
    result=encoded(body)
    require(len(result)<=CAPTURED_REQUEST_BYTES,'handoff_size')
    decode(body['input'][0]['content'][0]['text'],MAX_INPUT)
    return result


def _prepared_locked(history, events, request_hash):
    history.require_write_transaction(events)
    rows = [e for e in events if e['type']=='new_case_prepared' and e['request_hash']==request_hash]
    require(len(rows)==1, 'unknown_handoff')
    p=rows[0]; job=p['job']
    selected_current(events,job); research_dependency(events,job)
    packet=next(e['packet'] for e in events if e['type']=='intake' and e['job']==job)
    now=stamp(history.clock())
    require(now>=p['at'], 'clock_rollback')
    rec=admitted(packet,packet['binding'],now,purpose=p.get('assessment_purpose'))
    require(digest(rec)==p['reconciliation_hash'], 'decision_or_evidence_applicability_changed')
    require(projection(packet,rec,now)[0]==projection(packet,rec,p['at'])[0],
            'decision_or_evidence_applicability_changed')
    request=request_for(packet,rec,p['at'])
    require(request==p['request'] and digest(request)==request_hash, 'handoff_changed')
    return p,packet,captured_request(request),rec


def captured_material_hash(packet, rec, *, prepared_at=None):
    """Conservative root replay identity, not an assessment/citation projection.

    Paired retained and prepared-time usable keys prevent both clock-only
    changes and future-only additions from minting new work. Exact retained
    text is used, not redaction affected by caller reference IDs.
    Evidence clocks/labels/order cannot mint a new opportunity. Actual scoped
    content/claims or effective decisions may change it; occurrence stays bound.
    """
    def unique(rows):
        return [value for _,value in sorted({encoded(row):row for row in rows}.items())]
    evidence=[]
    for row in packet['evidence']:
        if row['scope']!=packet['binding']:continue
        if prepared_at is not None and row['observed_at']>prepared_at:continue
        claims=sorted(c for c in row['claims'] if row['kind']!='source' or c not in ('runtime','edition'))
        evidence.append(dict(kind=row['kind'],candidate=row['candidate'],text=row['text'],
            claims=claims,image_references=row['image_references']))
    decisions=[dict(kind=row['decision']['kind'],applicability=row['applicability'],
        chosen_target=row['decision']['chosen_target']) for row in rec['prior_decisions']]
    case={k:v for k,v in packet['binding'].items() if k!='version'}
    f=packet['facts']
    facts={k:f[k] for k in ('title','year','imdb','tmdb')}
    facts.update(asserted_imdb=f['outcome'].get('asserted_imdb'),
        asserted_tmdb=f['outcome'].get('asserted_tmdb'),reason=f['outcome']['reason'])
    return digest(dict(case=case,capture_event=packet['event'],facts=facts,
        evidence=unique(evidence),decisions=unique(decisions),disposition=rec['disposition'],
        conflicting_ids=rec['conflicting_ids']))


def captured_consent(root, root_events, history, events, request_hash, evidence):
    """Pure exact consent proposal, only under root then selected-case locks."""
    from .supervised_credit import file_identity
    root.require_write_transaction(root_events)
    p,packet,body,rec=_prepared_locked(history,events,request_hash)
    consent = dict(kind='captured_occurrence_generation_v1', response_contract=CAPTURED_CONTRACT,
        root_identity=list(root.identity), root_prefix_sha256=digest(root_events),
        case_directory=str(history.directory), case_identity=list(history.identity),
        case_file_identity=file_identity(history), prepared_hash=digest(p), request_hash=request_hash,
        job=p['job'], case=packet['binding'], material_hash=captured_material_hash(packet,rec),
        disclosure_material_hash=captured_material_hash(packet,rec,prepared_at=p['at']),
        capture_event=packet['event'], reconciliation_hash=p['reconciliation_hash'],
        request=decode(body,65536), request_sha256=digest(decode(body,65536)),
        project=evidence['project'], account_reference=evidence['account_reference'],
        evidence_hash=digest(evidence), maximum_debit_usd=[3,100], max_calls=1,
        issued_at=evidence['observed_at'], expires_at=evidence['expires_at'],
        owner_reference=evidence['owner_reference'],
        source_authenticity='unknown', live_currentness='unknown', decision_coverage='unknown',
        identity_approval=False, acquisition_approval=False, notification_authority=False)
    if p.get('assessment_purpose') is not None: consent['assessment_purpose'] = p['assessment_purpose']
    return consent



def captured_continuation_consent(root, root_events, history, events, request_hash, evidence,
                                  *, prior_slot, owner_reference):
    """Proposal only: one owner-resumed 401 after an attested credential change."""
    from . import supervised_credit as c
    root.require_write_transaction(root_events); history.require_write_transaction(events)
    attempts=c._standing_attempts(root_events,root_events[1])
    require(attempts and attempts[-1][0]['slot']==prior_slot,'captured_continuation_prior')
    old=attempts[-1][0].get('captured')
    require(old is not None,'captured_continuation_prior')
    terminals=[e for e in root_events if e.get('slot')==prior_slot and e['type']=='supervised_diagnostic']
    require(len(terminals)==1,'captured_continuation_prior')
    authority=captured_consent(root,root_events,history,events,request_hash,evidence)
    require(evidence['owner_reference']==owner_reference,'captured_continuation_owner')
    authority['continuation']=dict(prior_slot=prior_slot,prior_grant_sha256=digest(old),
        prior_attempt_sha256=digest(History(root.directory/f'attempt-{prior_slot}').read()),
        prior_terminal_sha256=digest(terminals[0]),case_prefix_sha256=digest(events),
        material_credential_correction_attested=True,owner_reference=owner_reference)
    _captured_continuation(root,root_events,history,events,authority)
    return authority


def _captured_continuation(root, root_events, history, events, authority, grant=None):
    """Check preserved failure and single-use successor under root then case locks."""
    from . import supervised_credit as c
    root.require_write_transaction(root_events);history.require_write_transaction(events)
    a=authority['continuation']
    shape(a,'prior_slot prior_grant_sha256 prior_attempt_sha256 prior_terminal_sha256 '
          'case_prefix_sha256 material_credential_correction_attested owner_reference')
    require(type(a['prior_slot']) is int and a['prior_slot']>=7 and
        a['material_credential_correction_attested'] is True and
        isinstance(a['owner_reference'],str) and bool(a['owner_reference'].strip()) and
        a['owner_reference']==authority['owner_reference'],'captured_continuation_owner')
    attempts=c._standing_attempts(root_events,root_events[1])
    prior=[s for s,_ in attempts if s['slot']==a['prior_slot']]
    require(len(prior)==1 and 'captured' in prior[0],'captured_continuation_prior')
    old=prior[0]['captured'];oa=old['authorization']
    require('continuation' not in oa and oa['owner_reference']!=a['owner_reference'],
        'captured_continuation_owner')
    terminal=[e for e in root_events if e.get('slot')==a['prior_slot'] and e['type']=='supervised_diagnostic']
    rows=History(root.directory/f"attempt-{a['prior_slot']}").read()
    reservations=History(root.directory/'credit').read()
    retained=[r for r in reservations if r['request_hash']==prior[0]['request_sha256']]
    require(len(retained)==1 and retained[0]['reserved_usd']==[3,100], 'captured_continuation_prior')
    require(len(terminal)==1 and terminal[0]['reason']=='responses_http_401' and
        terminal[0]['phase']=='http_response_received' and terminal[0]['category']=='transport_refused' and
        'cleanup_reason' not in terminal[0] and
        [r['type'] for r in rows]==['bound_send_reserved','bound_send_attempted'] and
        not any(e.get('slot')==a['prior_slot'] and e['type']=='supervised_completed' for e in root_events),
        'captured_continuation_prior')
    require(digest(old)==a['prior_grant_sha256'] and digest(rows)==a['prior_attempt_sha256'] and
        digest(terminal[0])==a['prior_terminal_sha256'],'captured_continuation_changed')
    # Preserve the prepared occurrence, disclosure and clocks, not just a title.
    keys=('root_identity','case_directory','case_identity','case_file_identity','prepared_hash',
          'request_hash','job','case','material_hash','disclosure_material_hash','capture_event',
          'reconciliation_hash','request','request_sha256','project','account_reference','assessment_purpose')
    require(all(authority.get(k)==oa.get(k) for k in keys),'captured_continuation_changed')
    uses=[s for s,_ in attempts if s.get('captured',{}).get('authorization',{}).get('continuation',{}).get('prior_slot')==a['prior_slot']]
    if uses:
        require(len(uses)==1 and grant is not None and uses[0]['captured']==grant and
            uses[0] is attempts[-1][0] and uses[0]['slot']==a['prior_slot']+1 and
            uses[0]['prefix_sha256']==authority['root_prefix_sha256'],'captured_continuation_consumed')
    else:
        require(prior[0] is attempts[-1][0] and digest(root_events)==authority['root_prefix_sha256'],
            'captured_continuation_consumed')
    starts=[e for e in events if e.get('job')==authority['job'] and e['type']=='new_case_generation_started']
    require(starts and starts[0]['grant_sha256']==digest(old),'captured_continuation_changed')
    prefix=events
    if len(starts)==2:
        require(grant is not None and events[-1] is starts[-1] and
            starts[-1]['grant_sha256']==digest(grant),'captured_continuation_consumed')
        prefix=events[:-1]
    else:require(len(starts)==1,'captured_continuation_consumed')
    require(digest(prefix)==a['case_prefix_sha256'],'captured_continuation_changed')
    return digest(old)


def _freshness_access_fix(access_fix, slot, prefix, owner_reference, expires_at, now):
    from . import supervised_credit as c
    shape(access_fix,'path sha256')
    raw,identity=c._read_evidence(Path(access_fix['path']),32768);fix=decode(raw,32768)
    require(raw==encoded(fix) and digest(fix)==access_fix['sha256'],'captured_freshness_access_fix')
    shape(fix,'kind slot root_prefix_sha256 owner_reference material_access_fix_verified prior_failure issued_at expires_at')
    require(fix['kind']=='captured_slot_access_fix' and fix['slot']==slot and
        fix['root_prefix_sha256']==prefix and fix['material_access_fix_verified'] is True and
        fix['prior_failure']=='keychain_denied' and isinstance(fix['owner_reference'],str) and
        bool(fix['owner_reference'].strip()) and fix['owner_reference'] in owner_reference and
        access_fix['sha256'] in owner_reference and
        stamp(fix['issued_at'])<=now<stamp(fix['expires_at']) and
        fix['expires_at']>=expires_at, 'captured_freshness_access_fix')
    return list(identity)


def _unstarted_freshness(root, root_events, history, events, evidence, access_fix):
    from . import supervised_credit as c
    root.require_write_transaction(root_events);history.require_write_transaction(events)
    _,attempts,credit,_=c._standing_history(root,root_events,root_events[1],History(root.directory/'credit'))
    require(bool(attempts),'captured_freshness_state')
    start,authorized=attempts[-1];old=start.get('captured')
    require(old is not None and 'freshness' not in old['authorization'],'captured_freshness_state')
    slot=start['slot'];now=time.time()
    require([e for e in root_events if e.get('slot')==slot]==[start,authorized] and
        not History(root.directory/f'attempt-{slot}').read() and
        len(credit)==start['credit_count'] and digest(credit)==start['credit_sha256'],
        'captured_freshness_started')
    oa=old['authorization']
    require(now>=start['expires_at'] and now>=oa['expires_at'],'captured_freshness_not_expired')
    require(str(history.directory)==oa['case_directory'],'captured_freshness_changed')
    starts=[e for e in events if e.get('job')==oa['job'] and e['type']=='new_case_generation_started']
    if 'continuation' in oa:
        _captured_continuation(root,root_events,history,events,oa,old)
        require(len(starts)==1,'captured_freshness_started')
    else:require(not starts,'captured_freshness_started')
    require(not any(e.get('job')==oa['job'] and e['type'] in ('invocation','result',
        'new_case_completion_started','new_case_completed','new_case_completion_rejected',
        'new_case_simulated_send_started') for e in events),'captured_freshness_started')
    _freshness_access_fix(access_fix,slot,digest(root_events),evidence['owner_reference'],evidence['expires_at'],now)
    c.validate_evidence(evidence,now,standing=True)
    require(evidence['project']==start['project'] and
        evidence['account_reference']==oa['account_reference'] and
        evidence['observed_at']>=start['expires_at'],'captured_freshness_changed')
    return start,authorized,credit


def captured_freshness_consent(root, root_events, history, events, evidence, access_fix):
    """One exact proposal for an expired, allocated but never-started slot."""
    start,_,credit=_unstarted_freshness(root,root_events,history,events,evidence,access_fix)
    old=start['captured'];oa=old['authorization']
    result=captured_consent(root,root_events,history,events,oa['request_hash'],evidence)
    # The original allocation prefix still identifies this slot; the new
    # freshness prefix identifies the later append, never a new allocation.
    result['root_prefix_sha256']=oa['root_prefix_sha256']
    if 'continuation' in oa:
        result['continuation']=dict(oa['continuation'],owner_reference=evidence['owner_reference'])
    result['freshness']=dict(slot=start['slot'],prior_start_sha256=digest(start),
        prior_grant_sha256=digest(old),root_prefix_sha256=digest(root_events),
        case_prefix_sha256=digest(events),credit_prefix_sha256=digest(credit),access_fix=access_fix,
        access_fix_identity=_freshness_access_fix(access_fix,start['slot'],digest(root_events),
            evidence['owner_reference'],evidence['expires_at'],time.time()))
    return result


def refresh_captured(directory,selected,case_directory,authority_path,authority_sha256,access_fix):
    """Append freshness authority once; never allocate a slot, debit or credential."""
    from . import supervised_credit as c
    require_captured_activation()
    require(type(selected) is c.SelectedEvidence,'supervised_evidence_selection')
    selected.revalidate();root=History(Path(directory));history=History(Path(case_directory))
    require(root.identity!=history.identity,'captured_freshness_changed')
    with root.transaction(write=True) as (events,append):
        with history.transaction(write=True) as (rows,_):
            expected=captured_freshness_consent(root,events,history,rows,selected.data,access_fix)
            raw,identity=c._read_evidence(Path(authority_path),CAPTURED_AUTHORITY_BYTES)
            a=decode(raw,CAPTURED_AUTHORITY_BYTES)
            require(raw==encoded(a) and digest(a)==authority_sha256 and a==expected,'captured_authority_changed')
            grant=dict(authority_path=str(Path(authority_path)),authority_sha256=authority_sha256,
                authority_identity=list(identity),authorization=a,run='captured-'+digest(a),case=a['case'],request=a['request'])
            validate_captured(grant,selected.data['project'])
            start,authorized,credit=_unstarted_freshness(root,events,history,rows,selected.data,access_fix)
            effective=c._credit_grant(events,events[1],start['slot'])
            from .spending import rational,pair
            from .credit_test import retained_total,PER_REQUEST
            ceiling=min(rational(effective['ceiling_usd']),rational(selected.data['available_usd']))
            require(selected.data['account_reference']==effective['account_reference'] and
                selected.data['credit_expires_at']<=effective['credit_expires_at'] and
                time.time()<effective['credit_expires_at'] and
                retained_total(credit,selected.data['project'])+PER_REQUEST<=ceiling,'supervised_standing_credit')
            selected.revalidate();at=time.time();c.validate_evidence(selected.data,at,standing=True)
            row=dict(type='supervised_captured_freshness_authorized',slot=start['slot'],at=at,
                prefix_sha256=digest(events),prior_start_sha256=digest(start),captured=grant,
                evidence_sha256=selected.sha256,evidence=selected.data,ceiling_usd=pair(ceiling))
            c._freshened_start(start,row,events)
            append(row)
    return dict(status='captured_freshness_authorized_no_send',slot=start['slot'],request_sha256=start['request_sha256'])

def validate_captured(grant, project):
    """Validate exact private authority; JSON alone never opens the closed gate."""
    from .supervised_credit import _read_evidence
    require_captured_activation()
    shape(grant,'authority_path authority_sha256 authority_identity authorization run case request')
    raw,identity=_read_evidence(Path(grant['authority_path']),CAPTURED_AUTHORITY_BYTES)
    authority=decode(raw,CAPTURED_AUTHORITY_BYTES)
    require(raw==encoded(authority) and digest(authority)==grant['authority_sha256'] and
        list(identity)==grant['authority_identity'] and authority==grant['authorization'], 'captured_authority_changed')
    require(authority['kind']=='captured_occurrence_generation_v1' and
        authority['response_contract']==CAPTURED_CONTRACT and authority['project']==project and
        authority['max_calls']==1 and
        authority['maximum_debit_usd']==[3,100] and
        authority['case']['occurrence'] is not None and
        authority['request']==grant['request'] and authority['case']==grant['case'] and
        grant['run']=='captured-'+digest(authority) and
        digest(grant['request'])==authority['request_sha256'], 'captured_authority_changed')
    require(stamp(authority['issued_at'])<=time.time()<stamp(authority['expires_at']), 'captured_authority_expired')
    if 'freshness' in authority:
        f=authority['freshness']
        require(_freshness_access_fix(f['access_fix'],f['slot'],f['root_prefix_sha256'],
            authority['owner_reference'],authority['expires_at'],time.time())==f['access_fix_identity'],
            'captured_freshness_access_fix')
    active=_APPROVED_CAPTURE.get()
    if active is not None:active.bind(authority)
    body=encoded(grant['request'])
    require(len(body)<=CAPTURED_REQUEST_BYTES,'handoff_size')
    decode(grant['request']['input'][0]['content'][0]['text'],MAX_INPUT)
    return body


class _CapturedCase:
    def __init__(self, root, root_events, history, events, append, grant, evidence):
        self.root,self.root_events,self.history,self.events,self.append=root,root_events,history,events,append
        self.grant,self.evidence=grant,evidence
        self.started=False

    def validate(self):
        from .supervised_credit import file_identity
        self.root.require_write_transaction(self.root_events)
        self.history.require_write_transaction(self.events)
        a=self.grant['authorization']
        body=validate_captured(self.grant,self.evidence['project'])
        p,packet,expected,rec=_prepared_locked(self.history,self.events,a['request_hash'])
        require(a.get('assessment_purpose')==p.get('assessment_purpose'),'assessment_purpose')
        active=_APPROVED_CAPTURE.get()
        if active is not None:active.bind(a,packet)
        require(list(self.root.identity)==a['root_identity'] and
            list(self.history.identity)==a['case_identity'] and file_identity(self.history)==a['case_file_identity'] and
            str(self.history.directory)==a['case_directory'] and digest(p)==a['prepared_hash'] and
            p['job']==a['job'] and captured_material_hash(packet,rec)==a['material_hash'] and
            captured_material_hash(packet,rec,prepared_at=p['at'])==a['disclosure_material_hash'] and
            packet['event']==a['capture_event'] and p['reconciliation_hash']==a['reconciliation_hash'] and
            packet['binding']==a['case'] and expected==body and digest(self.evidence)==a['evidence_hash'] and
            self.evidence['account_reference']==a['account_reference'], 'captured_selection_changed')
        require(not any(e.get('job')==p['job'] and e['type'] in ('invocation','result',
            'new_case_completion_started','new_case_simulated_send_started') for e in self.events), 'assessment_already_consumed')
        starts=[e for e in self.events if e.get('job')==p['job'] and e['type']=='new_case_generation_started']
        if 'freshness' in a:
            prefix=self.events[:-1] if self.started else self.events
            require(digest(prefix)==a['freshness']['case_prefix_sha256'], 'captured_freshness_changed')
        if 'continuation' in a:
            _captured_continuation(self.root,self.root_events,self.history,self.events,a,self.grant)
            require(len(starts)==(2 if self.started else 1),'captured_generation_consumed')
        else:
            require((not starts and not self.started) or (self.started and len(starts)==1 and
                starts[0]['grant_sha256']==digest(self.grant)), 'captured_generation_consumed')
        return body

    def start(self):
        self.validate()
        require(not self.started, 'captured_generation_consumed')
        self.append(dict(type='new_case_generation_started',job=self.grant['authorization']['job'],
            at=stamp(self.history.clock()),grant_sha256=digest(self.grant)))
        self.started=True

    def complete(self, answer):
        self.validate()
        require(self.started,'captured_completion_unbound')
        from .supervised_authorization import consume_captured_completion,observe_phase
        proof=consume_captured_completion(self,answer)
        observe_phase('captured_result_validation')
        request_hash=self.grant['authorization']['request_hash']
        marker=_CONNECTED_COMPLETION.set((self.history,request_hash,digest(answer),proof))
        try:
            return _complete_locked(self.history,self.events,self.append,request_hash,answer,
                dict(mode='simulation' if proof['simulated'] else 'receipt_correlated_generation',
                     chat_reference='Connected fake socket fixture; no authenticated provider or delivery' if proof['simulated'] else
                         'Fixed transport request and project correlation; not chat ingestion or delivery'))
        finally:_CONNECTED_COMPLETION.reset(marker)


@contextmanager
def captured_case_lock(root,root_events,grant,evidence):
    """Lock order: root -> case -> short attempt/credit locks. Never reacquire case."""
    require_captured_activation()
    root.require_write_transaction(root_events)
    require(_CAPTURED.get() is None,'captured_lock_required')
    a=grant['authorization']; history=History(Path(a['case_directory']),clock=root.clock)
    require(history.identity!=root.identity,'captured_selection_changed')
    with history.transaction(write=True) as (events,append):
        held=_CapturedCase(root,root_events,history,events,append,grant,evidence)
        held.validate()
        marker=_CAPTURED.set(held)
        try:yield held
        finally:_CAPTURED.reset(marker)


def locked_captured(grant):
    held=_CAPTURED.get()
    require(type(held) is _CapturedCase and held.grant==grant,'captured_lock_required')
    held.validate()
    return held


def authorize_captured(directory,selected,case_directory,request_hash,authority_path,authority_sha256):
    """Dormant exact grant preparation; gate precedes any private read/mutation."""
    from . import supervised_credit as c
    require_captured_activation()
    require(type(selected) is c.SelectedEvidence,'supervised_evidence_selection')
    selected.revalidate();c.validate_evidence(selected.data,time.time(),standing=True)
    root=History(Path(directory)); history=History(Path(case_directory))
    with root.transaction(write=True) as (root_events,root_append):
        require(root.identity!=history.identity,'captured_selection_changed')
        with history.transaction(write=True) as (events,append):
            expected=captured_consent(root,root_events,history,events,request_hash,selected.data)
            raw,identity=c._read_evidence(Path(authority_path),CAPTURED_AUTHORITY_BYTES);a=decode(raw,CAPTURED_AUTHORITY_BYTES)
            if 'continuation' in a:
                expected=captured_continuation_consent(root,root_events,history,events,request_hash,selected.data,
                    prior_slot=a['continuation']['prior_slot'],owner_reference=a['continuation']['owner_reference'])
            require(raw==encoded(a) and digest(a)==authority_sha256 and a==expected,'captured_authority_changed')
            grant=dict(authority_path=str(Path(authority_path)),authority_sha256=authority_sha256,
                authority_identity=list(identity),authorization=a,run='captured-'+digest(a),case=a['case'],request=a['request'])
            validate_captured(grant,selected.data['project'])
            held=_CapturedCase(root,root_events,history,events,append,grant,selected.data);held.validate()
            marker=_CAPTURED.set(held)
            try:slot=c._prepare_next_locked(root,root_events,root_append,selected,create=True,captured=grant)
            finally:_CAPTURED.reset(marker)
    return dict(status='captured_authorized_no_send',slot=slot,request_sha256=a['request_sha256'])

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
