"""Private normalized-observation pairing; byte binding is not source authentication."""
import re
import uuid

from .contracts import decode, hash_id, require, shape, stamp


def project(raw, packet, historical_raw, prepared_at):
    envelope = decode(raw, 32768)
    shape(envelope, 'status case version source_file_size_bound result observer_journal_mode')
    require(envelope['status'] == 'completed' and type(envelope['source_file_size_bound']) is int
            and envelope['source_file_size_bound'] == 33554432
            and envelope['observer_journal_mode'] in ('delete', 'wal'), 'companion_envelope')
    require(envelope['case'] == packet['case_id'] and envelope['version'] == packet['version'], 'companion_binding')
    r = envelope['result']
    shape(r, 'status case_id selection_version route correlation reason decision_history normalized_signature captured_bytes evidence_freshness cross_store_atomic intervening_changes selection_event_digest event_uuid outcome_delivery_rowid review_cursor historical_review_count selection_reviews observer_pending facts event_observed_at collector_observation_started_at collector_observed_at spool_observation_started_at spool_observed_at spool_observation_finished_at collector_recheck_started_at collector_rechecked_at')
    expected = dict(status='ok', case_id=packet['case_id'], selection_version=packet['version'], route='eligible',
        correlation='strong_source_id', reason=packet['reason'], decision_history='incomplete_unknown',
        normalized_signature='source_side_match_only', captured_bytes='not_established',
        evidence_freshness='not_established', cross_store_atomic=False, intervening_changes='not_excluded')
    require(all(type(r[k]) is type(v) and r[k] == v for k, v in expected.items()), 'companion_binding')
    hash_id(r['selection_event_digest'])
    require(type(r['event_uuid']) is str, 'companion_event')
    try:
        require(str(uuid.UUID(r['event_uuid'])) == r['event_uuid'], 'companion_event')
    except ValueError:
        require(False, 'companion_event')
    for key in ('outcome_delivery_rowid', 'review_cursor'):
        require(type(r[key]) is int and r[key] > 0, 'companion_cursor')
    require(r['review_cursor'] >= r['outcome_delivery_rowid'], 'companion_cursor')
    clocks = ('event_observed_at', 'collector_observation_started_at', 'collector_observed_at',
        'spool_observation_started_at', 'spool_observed_at', 'spool_observation_finished_at',
        'collector_recheck_started_at', 'collector_rechecked_at')
    times = [stamp(r[k]) for k in clocks]
    require(all(a <= b for a, b in zip(times, times[1:])) and times[-1] <= prepared_at
            and r['event_observed_at'] == packet['last_observed'], 'companion_clock_binding')
    require(r['observer_pending'] in ('present', 'absent'), 'companion_pending')
    case = decode(historical_raw, 65536)['retained_case']
    source = case['source_identity']
    facts = r['facts']
    shape(facts, 'title title_status source_year metadata_imdb metadata_tmdb outcome_asserted_imdb outcome_asserted_tmdb id_values_are_claims')
    require(facts['id_values_are_claims'] is True and facts['title_status'] == 'available'
            and facts['title'] == packet['title'] and type(facts['source_year']) is int
            and facts['source_year'] == packet['year'], 'companion_facts_binding')
    for key, original in (('metadata_imdb', 'imdb'), ('metadata_tmdb', 'tmdb'),
                          ('outcome_asserted_imdb', 'asserted_imdb'), ('outcome_asserted_tmdb', 'asserted_tmdb')):
        value = facts[key]
        require(value is None or (type(value) is str and re.fullmatch(r'tt[0-9]{7,10}', value) is not None
                if 'imdb' in key else type(value) is int and 0 < value < 2**31), 'companion_identity')
        require(original in source and type(facts[key]) is type(source[original])
                and facts[key] == source[original], 'companion_facts_binding')
    reviews = r['selection_reviews']
    require(type(reviews) is list and type(r['historical_review_count']) is int
            and len(reviews) == r['historical_review_count'] <= 32, 'companion_reviews')
    # Preserve prior decisions with opaque occurrence aliases, never raw event/delivery IDs.
    from .contracts import digest
    projected, seen, occurrences = [], set(), {}
    for review in reviews:
        shape(review, 'id event delivery reviewed imdb tmdb year')
        hash_id(review['id']); hash_id(review['event'])
        require(type(review['delivery']) is int and review['delivery'] > 0
                and stamp(review['reviewed']) <= r['collector_observed_at'], 'companion_reviews')
        require(review['id'] == digest([packet['case_id'], review['event'], review['delivery']])
                and review['id'] not in seen, 'companion_reviews')
        seen.add(review['id'])
        require(not (review['event'] == r['selection_event_digest'] and review['delivery'] == r['review_cursor']),
                'companion_selected_occurrence_reviewed')
        require(type(review['imdb']) is str and re.fullmatch(r'tt[0-9]{7,10}', review['imdb']) is not None
                and type(review['tmdb']) is int and 0 < review['tmdb'] < 2**31
                and type(review['year']) is int and 1888 <= review['year'] <= 2100, 'companion_reviews')
        key = (review['event'], review['delivery'])
        alias = occurrences.setdefault(key, 'prior-occurrence-' + str(len(occurrences) + 1))
        projected.append(dict(occurrence=alias, reviewed_at=review['reviewed'], imdb=review['imdb'],
                              tmdb=review['tmdb'], year=review['year'], selected_occurrence=False))
    return dict(kind='supplied_normalized_source_observation',
        authenticity='external_operator_source_verification_required',
        pairing='same normalized case, version, source facts and underlying event time',
        event_observed_at=r['event_observed_at'], collector_observation_started_at=r['collector_observation_started_at'],
        collector_observed_at=r['collector_observed_at'], collector_rechecked_at=r['collector_rechecked_at'],
        observer_observation_started_at=r['spool_observation_started_at'], observer_observed_at=r['spool_observed_at'],
        observer_observation_finished_at=r['spool_observation_finished_at'],
        observer_pending=r['observer_pending'], observer_journal_mode=envelope['observer_journal_mode'],
        pending_scope='Exact selected event at the observed instant only; not proof of delivery or acknowledgement.',
        prior_reviews=projected, decision_history='incomplete_unknown', currentness='incomplete_unknown',
        underlying_movie_evidence_refreshed=False, physical_identity='not_established',
        captured_bytes='not_established', cross_store_atomic=False, intervening_changes='not_excluded',
        historical_event_delivery_binding='not_established', identity_approval=False, acquisition_approval=False)
