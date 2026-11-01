"""Read-only private views. Rendering does not deliver, acknowledge or archive."""
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from .contracts import digest, require, text


def case_view(events, job, *, at):
    intake = next((e for e in events if e['type'] == 'intake' and e['job'] == job), None)
    require(intake is not None, 'unknown_job')
    packet = intake['packet']
    rows = [e for e in events if e.get('job') == job]
    results = [e for e in rows if e['type'] == 'result']
    from .contracts import reconcile
    rec = reconcile(packet, at)
    result = results[-1] if results else None
    latest = [e for e in events if e['type'] == 'intake' and
              e['packet']['binding']['case_id'] == packet['binding']['case_id']][-1]
    currentness = ('current selected input' if latest['job'] == job else
                  'historical input; superseded by ' + latest['job'])
    status = result['status'] if result else ('failed_unknown' if any(e['type'] == 'model_reserved' for e in rows)
                                             else 'pending')
    if result is None and any(e['type'] == 'research_started' for e in rows):
        status = ('research_evidence_retained' if any(e['type'] == 'research_complete' and
                  e['original_job'] == job for e in events) else 'research_failed_unknown')
    if result is None and any(e['type'] == 'research_revoked' for e in rows):
        status = 'research_retired'
    lines = [f"{packet['facts']['title']} ({packet['facts']['year']})", f'Case: {job}',
             f"Scope: {packet['binding']}", f"Intake: {intake['reason']}",
             f'Input currentness: {currentness}',
             'Decisions and findings below belong to this input snapshot; later inputs do not rewrite its history.',
             f"Outcome: {status}", f"Prior disposition: {rec['disposition']}",
             'Novelty: unknown; missing history does not establish a new film.',
             'Operational closure: unavailable; identity review and download confirmation remain separate.']
    for prior in rec['prior_decisions']:
        d = prior['decision']
        lines.append(f"Decision {d['id']} revision {d['revision']}: {d['kind']}; {prior['applicability']}; "
                     f"decided {d['decided_at']}; chosen target {d['chosen_target']}; provenance {d['provenance']}")
    if rec['known_identity']:
        lines.append(f"Owner-confirmed film: {rec['known_identity']}; source, runtime and edition still need verification.")
    for evidence in packet['evidence']:
        stale = evidence['expires_at'] is not None and evidence['expires_at'] <= at
        lines.append(f"Evidence {evidence['id']} ({evidence['kind']}): {evidence['text']}; "
                     f"candidate {evidence['candidate']}; claims {evidence['claims']}; "
                     f"observed {evidence['observed_at']}; {'stale dated knowledge' if stale else 'dated retained evidence'}; "
                     f"scope {'matches' if evidence['scope'] == packet['binding'] else 'changed or unbound'}; "
                     f"provenance {evidence['provenance']}; image references {evidence['image_references']} (not image analysis)")
    if result:
        inference = ('not attempted' if result['model_calls'] == 0 else
                     'SIMULATED; not a real identification' if result['runtime']['simulated'] else
                     'real model inference; review proposal only' if result['model_result'] else
                     'real model attempt; completion unknown or rejected')
        lines.extend([f"Result identity: {digest(result)}", f"Reason: {result['reason']}",
                      f"Inference: {inference}",
                      f"Runtime: {result['runtime']}", f"Model calls: {result['model_calls']}; provider GETs: {result['provider_gets']}"])
        mr = result['model_result']
        if mr:
            lines.extend([f"Candidate: {mr['candidate']}; alternatives: {mr['alternatives']}",
                          f"Evidence rationale: {mr['rationale']}", f"Citations: {mr['citations']}",
                          f"Uncertainty: {mr['uncertainty']}", f"Next action: {mr['next_action']}"])
        else:
            lines.append('Next action: review the recorded disposition or activation prerequisite; do not replay an unknown attempt.')
    else:
        lines.append('Next action: inspect pending or unknown state; no inference completion or delivery is established.')
    for e in rows:
        if e['type'] == 'research_revoked':
            lines.append(f"Research plan {e['plan_hash']} retired; no research or model approval follows.")
        if e['type'] == 'research_complete':
            lines.append(f"Catalogue research: {e['simulated_gets']} SIMULATED GETs through shared ledger; "
                         f"plan {e['plan_hash']}; receipts {e['receipts']}; zero live GETs.")
        if e['type'] == 'pilot_plan':
            lines.append(f"Offline pilot plan: {e['plan_hash']}; real readiness blocked; template is not authority.")
        if e['type'] == 'api_response':
            a = e['accounting']
            lines.append(f"API accounting ({'SIMULATED' if a['simulated'] else 'real'}): "
                         f"response {a['response_id']}; request {a.get('request_id', 'not supplied')}; "
                         f"usage {a['usage']}; final billing not verified.")
        if e['type'] == 'lookup':
            a = e['answer']
            lines.append(f"Tool used: {a['operation']}; returned {[r['id'] for r in a['rows']]}; retained replay, zero provider GETs.")
    return '\n'.join(lines)


def daily_digest(history, *, selected_date, timezone, previous_result_ids=()):
    """Explicit calendar/timezone and caller-selected comparison, with no receipts."""
    require(isinstance(selected_date, str) and date.fromisoformat(selected_date).isoformat() == selected_date, 'digest_date')
    zone = ZoneInfo(timezone)
    selected = date.fromisoformat(selected_date)
    start = datetime.combine(selected, time.min, zone).timestamp()
    end = datetime.combine(selected + timedelta(days=1), time.min, zone).timestamp()
    events = history.read()
    # Honest historical as-of view: later results cannot fill yesterday's gap.
    events = [e for e in events if e['at'] < end]
    intakes = [e for e in events if e['type'] == 'intake']
    results = [e for e in events if e['type'] == 'result' and start <= e['at'] < end]
    changed = [digest(r) for r in results if digest(r) not in previous_result_ids]
    lines = [f'AI movie investigation review — {selected_date} ({timezone})',
             'Private offline review; rendering is not sending, acknowledgement or archive.',
             f'Changed results: {len(changed)}. Delivery: not attempted. Schedule: inactive; missed runs not measured.']
    if not intakes:
        lines.append('Quiet: no retained cases as of this selected day; live queue and coverage unknown.')
    for intake in intakes:
        lines.extend(['', case_view(events, intake['job'], at=end)])
    proposals = [e for e in events if e['type'] == 'proposal']
    for e in events:
        if e['type'] in ('spending_reserved', 'spending_settled'):
            lines.append(f"SIMULATED spending {e['type']}: request {e['local_request_id']}; "
                         f"USD rational {e['cost']}; no real affordability or final billing established.")
    for p in proposals:
        lines.extend(['', f"Generic-rule proposal {p['proposal_id']}: {p['failure_pattern']}",
                      f"Supporting results: {p['supporting_results']}",
                      f"Positive tests: {p['positive_tests']}; negative tests: {p['negative_tests']}",
                      'Proposal only; production code is never edited automatically.'])
    return dict(text='\n'.join(lines), changed_result_ids=changed,
                selected_date=selected_date, timezone=timezone, sent=False, acknowledged=False, archived=False)


def propose_rule(history, *, failure_pattern, supporting_results, positive_tests, negative_tests):
    """Record a review proposal; this operation has no code-editing capability."""
    text(failure_pattern, 600)
    require(isinstance(supporting_results, list) and 1 <= len(supporting_results) <= 8, 'proposal_support')
    for tests in (positive_tests, negative_tests):
        require(isinstance(tests, list) and 1 <= len(tests) <= 8, 'proposal_tests')
        for suggestion in tests:
            text(suggestion, 200)
    proposal = dict(failure_pattern=failure_pattern, supporting_results=supporting_results,
                    positive_tests=positive_tests, negative_tests=negative_tests)
    proposal_id = digest(proposal)
    with history.transaction(write=True) as (events, append):
        actual = {digest(e) for e in events if e['type'] == 'result'}
        require(set(supporting_results) <= actual, 'proposal_unknown_support')
        if not any(e['type'] == 'proposal' and e['proposal_id'] == proposal_id for e in events):
            append(dict(type='proposal', proposal_id=proposal_id, at=history.clock(), **proposal))
    return proposal_id
