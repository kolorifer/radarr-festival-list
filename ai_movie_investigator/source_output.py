"""Independent fixed-shape validation of sanitized exact-case output.

No filesystem, SSH, production source, transport, acknowledgement or publication.
These checks supplement, never replace, source, child and preflight guards.
"""
import math
import re
import uuid
from . import source_case as core

_FAILURES = frozenset(('already_reviewed', 'case_changed', 'case_missing', 'clock_invalid',
    'deadline_exceeded', 'delivery_ambiguous', 'delivery_conflict', 'delivery_cursor_unknown',
    'delivery_signature_mismatch', 'event_ambiguous', 'event_invalid', 'event_missing',
    'evidence_invalid', 'input_invalid', 'invalid_json', 'limits_unavailable',
    'material_invalid', 'not_eligible', 'observer_invalid', 'query_failed',
    'review_invalid', 'disclosure_mismatch', 'selection_invalid', 'schema_invalid', 'schema_changed',
    'too_many_rows', 'version_changed', 'child_failure'))
_FIXED = {'status':'ok',
          'route':'eligible', 'correlation':'strong_source_id', 'reason':'title_conflict',
          'decision_history':'incomplete_unknown', 'normalized_signature':'source_side_match_only',
          'captured_bytes':'not_established', 'evidence_freshness':'not_established',
          'cross_store_atomic':False, 'intervening_changes':'not_excluded'}
_TIMES = ('event_observed_at', 'collector_observation_started_at', 'collector_observed_at',
          'spool_observation_started_at', 'spool_observed_at', 'spool_observation_finished_at',
          'collector_recheck_started_at', 'collector_rechecked_at')
_EXTRA = {'selection_event_digest', 'event_uuid', 'outcome_delivery_rowid', 'review_cursor',
          'historical_review_count', 'selection_reviews', 'observer_pending', 'facts', 'case_id', 'selection_version'} | set(_TIMES)


def _need(condition):
    if not condition:
        raise ValueError('invalid_sanitized_result')


def validate(result, requested_uuid, selector):
    """Validate the already buffered result and exact probe binding or refuse."""
    core.validate_selector(selector)
    _need(type(result) is dict)
    if result.get('status') == 'refused':
        _need(set(result) == {'status', 'code'} and result['code'] in _FAILURES)
        return result
    _need(set(result) == set(_FIXED) | _EXTRA)
    _need(result['case_id'] == selector['case_id'] and result['selection_version'] == selector['version'])
    for key, value in _FIXED.items():
        _need(type(result[key]) is type(value) and result[key] == value)
    _need(type(requested_uuid) is str and len(requested_uuid) == 36)
    try: _need(str(uuid.UUID(requested_uuid)) == requested_uuid)
    except (ValueError, TypeError, AttributeError): raise ValueError('invalid_sanitized_result') from None
    _need(result['event_uuid'] == requested_uuid)
    _need(type(result['selection_event_digest']) is str and
          re.fullmatch(r'[0-9a-f]{64}', result['selection_event_digest']) is not None)
    for key in ('outcome_delivery_rowid', 'review_cursor'):
        _need(type(result[key]) is int and result[key] > 0)
    _need(result['review_cursor'] >= result['outcome_delivery_rowid'])
    _need(result['observer_pending'] in ('present', 'absent') and type(result['observer_pending']) is str)
    facts = result['facts']
    _need(type(facts) is dict and set(facts) == {'title', 'title_status', 'source_year',
        'metadata_imdb', 'metadata_tmdb', 'outcome_asserted_imdb', 'outcome_asserted_tmdb',
        'id_values_are_claims'} and facts['id_values_are_claims'] is True)
    _need(facts['title_status'] in ('available', 'not_established', 'withheld_unsafe'))
    if facts['title_status'] == 'available':
        title = facts['title']
        _need(type(title) is str and title == selector['title'])
    else:
        _need(facts['title'] is None)
    year = facts['source_year']
    _need(year is None or type(year) is int and 1888 <= year <= 2100)
    for key in ('metadata_imdb', 'outcome_asserted_imdb'):
        value = facts[key]
        _need(value is None or type(value) is str and re.fullmatch(r'tt[0-9]{7,10}', value) is not None)
    for key in ('metadata_tmdb', 'outcome_asserted_tmdb'):
        value = facts[key]
        _need(value is None or type(value) is int and 0 < value < 2**31)
    for key in _TIMES:
        value = result[key]
        _need(type(value) in (int, float) and math.isfinite(value) and 0 < value < 10**11)
    _need(result['event_observed_at'] <= result['collector_observation_started_at'])
    sequence = _TIMES[1:]
    _need(all(result[a] <= result[b] for a, b in zip(sequence, sequence[1:])))
    reviews = result['selection_reviews']
    _need(type(reviews) is list and type(result['historical_review_count']) is int and
          len(reviews) == result['historical_review_count'] and len(reviews) <= 32)
    for review in reviews:
        _need(type(review) is dict and set(review) == {'id','event','delivery','reviewed','imdb','tmdb','year'})
        for key in ('id','event'):
            _need(type(review[key]) is str and re.fullmatch(r'[0-9a-f]{64}', review[key]) is not None)
        _need(type(review['delivery']) is int and review['delivery'] > 0 and
              type(review['reviewed']) in (int, float) and math.isfinite(review['reviewed']) and
              0 < review['reviewed'] <= result['collector_observed_at'])
        _need(type(review['imdb']) is str and re.fullmatch(r'tt[0-9]{7,10}', review['imdb']) is not None)
        _need(type(review['tmdb']) is int and 0 < review['tmdb'] < 2**31 and
              type(review['year']) is int and 1888 <= review['year'] <= 2100)
        _need(review['id'] == core.digest([selector['case_id'], review['event'], review['delivery']]))
        _need(not (review['event'] == result['selection_event_digest'] and
                   review['delivery'] == result['review_cursor']))
    return result
