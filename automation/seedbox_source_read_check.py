"""One selected source observation. No queue, database, or retained output."""
import hashlib
import re
import time

from ai_movie_investigator.contracts import decode, digest, hash_id, require, shape, stamp
from identity_triage_intake import normalize
from torrent_research_evidence import validate as validate_torrent_evidence


SELECTION_LIMIT = 65536


def select(raw, expected_sha256, config, configuration_sha256, now):
    """Check both records from the exact externally verified selection."""
    require(hashlib.sha256(raw).hexdigest() == hash_id(expected_sha256), 'selection_pin')
    selection = decode(raw, SELECTION_LIMIT)
    shape(selection, 'kind configuration_sha256 excluded_case_id paused_at collector_observed_at '
          'selected_at expires_at collector_version collector_material actor_version actor_observation '
          'expected_listing_imdb')
    require(selection['kind'] == 'seedbox_source_read_selection_v1'
            and hash_id(selection['configuration_sha256']) == configuration_sha256, 'selection_configuration')
    paused, observed, selected, expires = (
        stamp(selection[field]) for field in ('paused_at', 'collector_observed_at', 'selected_at', 'expires_at'))
    require(paused < observed <= selected <= now < expires <= selected + 300, 'selection_time')

    event = selection['actor_observation']
    actor = normalize(event, config['sources'], 'outcome')
    require(not actor.get('reason'), 'actor_record_refused')
    case_id = 'outcome-' + hash_id(actor['release'])
    excluded = selection['excluded_case_id']
    require(type(excluded) is str and excluded.startswith('outcome-'), 'selection_excluded_case')
    hash_id(excluded[8:])
    require(case_id != excluded, 'selection_excluded_case')
    material = selection['collector_material']
    require(digest([case_id, material]) == hash_id(selection['collector_version'])
            and digest([actor['release'], actor['metadata']]) == hash_id(selection['actor_version'])
            and actor['metadata'] == material['metadata']
            and actor['metadata']['source'] == config['listing_source']
            and material['route'] == 'eligible' and material['correlation'] == 'strong_source_id',
            'selection_binding')
    validate_torrent_evidence(material['outcome']['torrent_evidence'])
    external = event['data']['release']['external_id']
    imdb = selection['expected_listing_imdb']
    require(type(external) is str and re.fullmatch(r'[1-9][0-9]{0,19}', external)
            and type(imdb) is str and re.fullmatch(r'tt[0-9]{7,12}', imdb), 'selection_listing')
    return dict(case_id=case_id, version=selection['collector_version'],
                url='https://www.torrentleech.org/torrent/' + external,
                release_name=actor['metadata']['name'], imdb=imdb, expires_at=expires)


def observe(config, selected, stage, *, clock=time.time):
    from automation.seedbox_host_io import _get, _source_inputs
    from automation.seedbox_source_evidence import catalogue_facts, listing_facts, missing_movie_facts
    from tracker_metadata import parse_listing

    env, cookies = _source_inputs(config, stage)

    def get(label, url, **auth):
        stage(label)
        started = clock()
        require(started < selected['expires_at'], 'selection_expired')
        raw, observed = _get(url, **auth)
        require(started <= observed <= clock() < selected['expires_at'], 'source_observation_time')
        return raw, observed

    page, observed = get('listing_get', selected['url'], cookies=cookies)
    stage('listing_heading_id')
    listing = parse_listing(page, selected['release_name'])
    require(listing['reason'] == 'listing_id_found', listing['reason'])
    require(listing['imdb_id'] == selected['imdb'], 'listing_expected_imdb_mismatch')
    stage('listing_facts')
    facts = listing_facts(page, release_name=selected['release_name'],
                          case_id=selected['case_id'], version=selected['version'],
                          observed_at=observed, expires_at=observed + 900, revision=2)
    require(facts['imdb'] == selected['imdb'], 'listing_facts_imdb_mismatch')

    imdb = selected['imdb']
    found, found_at = get('catalogue_find',
                          'https://api.themoviedb.org/3/find/' + imdb + '?external_source=imdb_id',
                          token=env['TMDB_API_TOKEN'])
    result = decode(found, 1048576)
    require(type(result) is dict and result.get('success', True) is True
            and 'status_code' not in result, 'catalogue_lookup_refused')
    movies = result.get('movie_results')
    require(type(movies) is list and len(movies) <= 1, 'catalogue_lookup_refused')
    if not movies:
        missing_movie_facts(found, requested_imdb=imdb, observed_at=found_at, expires_at=found_at + 900)
        return 'authenticated_no_movie_mapping'
    require(type(movies[0]) is dict and type(movies[0].get('id')) is int
            and 0 < movies[0]['id'] < 2**31, 'catalogue_lookup_refused')
    tmdb = movies[0]['id']
    detail, detail_at = get('catalogue_detail',
                            f'https://api.themoviedb.org/3/movie/{tmdb}?append_to_response=credits,release_dates',
                            token=env['TMDB_API_TOKEN'])
    catalogue_facts(detail, expected_tmdb=tmdb, expected_imdb=imdb,
                    observed_at=detail_at, expires_at=detail_at + 900)
    return 'authenticated_crosswalk'
