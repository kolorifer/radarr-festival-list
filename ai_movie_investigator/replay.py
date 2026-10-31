"""Nonempty synthetic end-to-end proof. No live transport, providers or services.

Run: python -m ai_movie_investigator.replay --synthetic
All durable writes live under an automatically removed synthetic temporary root.
"""
import argparse
import copy
import json
from pathlib import Path
import tempfile
import uuid

from identity_triage_intake import normalize
from .contracts import captured_outcome, digest
from .codex_transport import FakeTransport
from .controller import investigate
from .history import History
from .review import daily_digest, propose_rule

NOW = 1793444400  # 2026-10-31 11:00 UTC; fixed synthetic fixture clock.


def synthetic_case(number=1):
    raw = json.loads(Path(__file__).with_name('synthetic.json').read_text())
    raw['id'] = str(uuid.UUID(int=number))
    raw['data']['release']['external_id'] = 'synthetic-' + str(number)
    sources = {'synthetic': 'Synthetic Index'}
    normalized = normalize(raw, sources, 'outcome')
    binding = dict(source='synthetic', case_id='outcome-' + normalized['release'],
                   version=digest(['synthetic_version', number]),
                   occurrence=dict(event_id=raw['id'], delivery_id=number))
    candidate = dict(imdb='tt9000127', tmdb=9000127)
    evidence = []
    for eid, kind, claims in [('catalogue-1', 'catalogue', ['title', 'year', 'crosswalk']),
                              ('source-1', 'source', ['source_identity', 'runtime'])]:
        evidence.append(dict(id=eid, kind=kind, scope=copy.deepcopy(binding), observed_at=NOW-100,
                             expires_at=NOW+86400, provenance=dict(origin='synthetic_fixture', digest=digest(eid)),
                             candidate=candidate, text='Synthetic retained ' + kind + ' record for Harbor.',
                             claims=claims, image_references=0))
    return raw, binding, evidence


def owner_decision(binding, kind, *, evidence, chosen=False):
    return dict(id='owner-decision', revision=1, issuer='synthetic_owner',
                provenance=dict(origin='owner_fixture', digest=digest(kind)), decided_at=NOW-50,
                scope=copy.deepcopy(binding), evidence_ids=['source-1'],
                evidence_hashes={'source-1': digest(next(r for r in evidence if r['id'] == 'source-1'))}, kind=kind,
                chosen_target=dict(imdb='tt9000127', tmdb=9000127) if chosen else None,
                supersedes=None, revoked_at=None, expires_at=None)


def packet_for(number=1, kind=None):
    raw, binding, evidence = synthetic_case(number)
    decisions = [owner_decision(binding, kind, evidence=evidence, chosen=kind == 'confirmed_identity')] if kind else []
    return captured_outcome(raw, sources={'synthetic': 'Synthetic Index'}, binding=binding,
                            evidence=evidence, decisions=decisions, trusted_issuers=('synthetic_owner',))


def simulated_replies(packet, *, status='supported_candidate'):
    b = packet['binding']
    binding_hash = digest(b)
    operations = [dict(operation='retained_search', case_id=b['case_id'], version=b['version'],
                       evidence_id=None, kind='catalogue', query='Synthetic'),
                  dict(operation='retained_get', case_id=b['case_id'], version=b['version'],
                       evidence_id='source-1', kind=None, query=None)]
    result = dict(status=status, candidate=dict(imdb='tt9000127', tmdb=9000127) if status == 'supported_candidate' else None,
                  alternatives=[], citations=[dict(evidence_id='catalogue-1', claim='crosswalk'),
                                             dict(evidence_id='source-1', claim='source_identity')],
                  rationale='Retained catalogue crosswalk and source assertion cite the same synthetic candidate.',
                  uncertainty='Source runtime and edition require independent system verification.',
                  next_action='verify_source_runtime_edition')
    return [dict(binding_hash=binding_hash, kind='lookup', lookups=operations, result=None),
            dict(binding_hash=binding_hash, kind='final', lookups=[], result=result)]


def run_synthetic(directory):
    history = History(directory, clock=lambda: NOW)
    packets = [packet_for(1, 'confirmed_identity'), packet_for(2, 'technical_gap'),
               packet_for(3, 'intentionally_skipped'), packet_for(4, 'intentionally_skipped'),
               packet_for(5, 'completed_occurrence')]
    for number in range(6, 12):
        p = packet_for(number)
        shadow = copy.deepcopy(p['evidence'][0])
        shadow.update(id='shadow-success', kind='shadow', claims=['shadow_success'],
                      observed_at=NOW-7*86400, expires_at=NOW-86400,
                      text='Earlier synthetic shadow success retained as dated knowledge.')
        p['evidence'].append(shadow)
        packets.append(p)
    packets.append(packet_for(12))  # Unknown disposition is not novelty.
    raw, binding, evidence = synthetic_case(13)
    raw['data']['release']['meta_tmdb'] = 9000128
    raw['data']['outcome'].update(status='needs_review', reason='identity_conflict', asserted_tmdb=9000127)
    packets.append(captured_outcome(raw, sources={'synthetic': 'Synthetic Index'}, binding=binding,
                                    evidence=evidence, decisions=[], trusted_issuers=('synthetic_owner',)))
    changed = copy.deepcopy(packets[4])
    changed['binding']['occurrence'] = dict(event_id=str(uuid.UUID(int=140)), delivery_id=140)
    changed['binding']['version'] = digest('synthetic_materially_changed_occurrence')
    # Old reviewed decision remains bound to the old occurrence. New evidence
    # is explicitly re-bound and materially changed, not approved by the title.
    for row in changed['evidence']:
        row['scope'] = copy.deepcopy(changed['binding'])
        row['text'] += ' New synthetic edition evidence.'
        row['provenance']['digest'] = digest(row['text'])
    new_raw, _, _ = synthetic_case(5)
    new_raw.update(id=str(uuid.UUID(int=140)), timestamp='2026-10-31T11:00:00+00:00')
    packets.append(captured_outcome(new_raw, sources={'synthetic': 'Synthetic Index'}, binding=changed['binding'],
                                    evidence=changed['evidence'], decisions=changed['decisions'],
                                    trusted_issuers=('synthetic_owner',)))
    results = []
    for index, packet in enumerate(packets):
        job, _ = history.intake(packet)
        status = 'unresolved' if index == 12 else 'supported_candidate'
        result = investigate(history, job, 'synthetic-invocation-' + str(index),
                             FakeTransport(simulated_replies(packet, status=status)))
        results.append(result)
    actual = next(e for e in history.read() if e['type'] == 'result')
    propose_rule(history, failure_pattern='Prior occurrence decisions and dated shadow knowledge must be joined before investigation.',
                 supporting_results=[digest(actual)], positive_tests=['Exact occurrence suppresses repeated owner-skipped work.'],
                 negative_tests=['New delivery never inherits prior occurrence approval.'])
    digest_view = daily_digest(history, selected_date='2026-10-31', timezone='Europe/Warsaw')
    return history, results, digest_view


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--synthetic', action='store_true', required=True)
    parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='ai-investigator-synthetic-') as tmp:
        _, _, review = run_synthetic(Path(tmp).resolve())
        print('SIMULATED OFFLINE PROOF — no real new identification\n' + review['text'])


if __name__ == '__main__':
    main()
