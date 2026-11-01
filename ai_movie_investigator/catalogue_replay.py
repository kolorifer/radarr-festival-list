"""Nonempty Task6 SIMULATION. No real source, catalogue, model or spending.

python -m ai_movie_investigator.catalogue_replay --synthetic
"""
import argparse
from pathlib import Path
import tempfile

from identity_recurring_store import RecurringStore

from .contracts import digest
from .controller import investigate
from .history import History
from .pilot import build_plan, readable_plan, validate_pilot
from .replay import NOW, packet_for, simulated_replies
from .research import (FixtureConnection, OfflineResearch, SyntheticClock,
                       SyntheticResearch, material_for, select_plan)
from .responses_replay import simulated_response, simulated_transport
from .review import daily_digest
from .spending import SimulatedSpending


def fixture_rows():
    return [dict(kind='movie_search', value='Synthetic Harbor', status=200, fault=None,
                 body=dict(page=1, results=[dict(id=9000127, title='Synthetic Harbor', release_date='2026-01-01')])),
            dict(kind='details', value=9000127, status=200, fault=None,
                 body=dict(id=9000127, title='Synthetic Harbor', release_date='2026-01-01',
                           external_ids=dict(imdb_id='tt9000127')))]


def setup_case(directory, number=1276):
    """Create an original synthetic epoch, never copy/reset an existing ledger."""
    directory = Path(directory)
    state = directory / 'history'
    ledger = directory / 'catalogue'
    state.mkdir(mode=0o700)
    ledger.mkdir(mode=0o700)
    clock = SyntheticClock(NOW)
    history = History(state, clock=clock)
    store = RecurringStore(ledger, clock=clock)
    original = packet_for(number)
    original['evidence'] = [r for r in original['evidence'] if r['kind'] == 'source']
    job, _ = history.intake(original)
    store.admit(material_for(original))
    plan = select_plan(original, [dict(kind='movie_search', value='Synthetic Harbor'),
                                dict(kind='details', value=dict(from_step=0, id=9000127))],
                       issued_at=NOW, expires_at=NOW+120)
    return history, store, clock, original, job, plan


def run_catalogue_synthetic(directory):
    history, store, clock, original, job, selected = setup_case(directory)
    connection = FixtureConnection(fixture_rows())
    broker = OfflineResearch(enabled=True, history=history, store=store, connection=connection,
        authorization=SyntheticResearch(digest(original), digest(selected)), monotonic=clock)
    new_job, packet, receipts = broker.run(job, selected)
    plan = build_plan(history, original, selected, selected_job=new_job, provenance='synthetic',
        ceiling=[1, 1], expires_at=NOW+120,
        output_binding=digest('SIMULATED private result destination'),
        receipt_binding=digest('SIMULATED private receipt destination'))
    validate_pilot(plan, history, original)
    with history.transaction(write=True) as (_, append):
        append(dict(type='pilot_plan', job=new_job, at=clock(), plan_hash=digest(plan), plan=plan))
    replies = simulated_replies(packet)
    for citation in replies[-1]['result']['citations']:
        if citation['evidence_id'] == 'catalogue-1':
            citation['evidence_id'] = 'research-1'
    spending = SimulatedSpending(history, binding=packet['binding'], ceiling=[1, 1], expires_at=NOW+120)
    transport = simulated_transport(packet,
        responses=[simulated_response(r, n) for n, r in enumerate(replies, 1)], spending=spending)
    transport.clock = clock
    result = investigate(history, new_job, 'SIMULATED-catalogue-model', transport, monotonic=clock)
    # Ineligible skip and explicitly retired/revoked plan: zero catalogue sends.
    skipped = packet_for(12761, 'intentionally_skipped')
    skipped_job, _ = history.intake(skipped)
    skipped_result = investigate(history, skipped_job, 'SIMULATED-skipped', simulated_transport(skipped))
    # A conflict is retained and discussed, never promoted into a match.
    conflict = packet_for(12762)
    conflict['facts']['imdb'] = 'tt9000127'
    conflict['facts']['outcome']['asserted_imdb'] = 'tt9000128'
    conflict_job, _ = history.intake(conflict)
    conflict_result = investigate(history, conflict_job, 'SIMULATED-conflict',
        simulated_transport(conflict, responses=[simulated_response(r, n) for n, r in
                            enumerate(simulated_replies(conflict, status='unresolved'), 1)]))
    revoked = packet_for(12763, 'intentionally_skipped')
    revoked['decisions'][0].update(revision=2, revoked_at=NOW-10)
    revoked_job, _ = history.intake(revoked)
    revoked_plan = select_plan(revoked, [dict(kind='movie_search', value='Synthetic Harbor')],
                               issued_at=NOW, expires_at=NOW+120)
    with history.transaction(write=True) as (_, append):
        append(dict(type='research_revoked', at=clock(), job=revoked_job,
                    plan_hash=digest(revoked_plan), reason='SIMULATED supervisor retirement'))
    from .contracts import Refusal
    revoked_wire = FixtureConnection([fixture_rows()[0]])
    try:
        OfflineResearch(enabled=True, history=history, store=store, connection=revoked_wire,
            authorization=SyntheticResearch(digest(revoked), digest(revoked_plan)), monotonic=clock
        ).run(revoked_job, revoked_plan)
    except Refusal as exc:
        revoked_reason = str(exc)
    else:
        raise AssertionError('retired plan performed research')
    review = daily_digest(history, selected_date='2026-10-31', timezone='Europe/Warsaw')
    return dict(history=history, store=store, result=result, review=review, transport=transport,
                plan=plan, plan_text=readable_plan(plan), receipts=receipts, connection=connection,
                skipped=skipped_result, conflict=conflict_result, revoked=revoked_reason,
                revoked_requests=len(revoked_wire.requests))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--synthetic', required=True, action='store_true')
    parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='SIMULATED-catalogue-') as tmp:
        demo = run_catalogue_synthetic(Path(tmp).resolve())
        print('SIMULATED ONLY — no real identification, access or charge\n' +
              demo['review']['text'] + '\n\n' + demo['plan_text'])


if __name__ == '__main__':
    main()
