"""Historical manual workflow; this module cannot call a provider.

Default rehearsal invents a fixture response. Explicit prepare/complete accepts
a separately supplied reply without authenticating its author. Neither path
admits a production case or establishes identity, approval or a real budget.
"""
import argparse
import contextlib
import hashlib
import os
import re
import stat
import sys
import time
from pathlib import Path

from .contracts import Refusal, decode, digest, encoded, hash_id, require, scope, shape, stamp, text
from .controller import output_schema, validate_final
from .disclosure import aliases, project, restore, row_view
from .history import History, checked
from .responses_http import ExplicitCredential, HTTPResult, SimulatedHTTP, SYNTHETIC_CREDENTIAL, SYNTHETIC_PROJECT
from .responses_protocol import parse_response
from .responses_replay import simulated_response
from .responses_transport import real_activation_refusal
from .spending import SimulatedSpending
from automation.coordinator_storage import acl_identity, StorageError
from automation.coordinator_transport import acl as linux_acl


def safe_acl(fd, directory):
    if sys.platform == 'darwin':
        return acl_identity(fd)
    if sys.platform.startswith('linux'):
        linux_acl(fd, directory)
        return 'posix_acl_absent'
    raise Refusal('acl_unsupported')


def identity(info):
    return (info.st_dev, info.st_ino, info.st_uid, info.st_mode)


@contextlib.contextmanager
def private_chain(path):
    # Reuse the existing storage guard's descriptor, owner, mode and ACL
    # principles, without granting coordinator access or changing permissions.
    require(path.is_absolute() and path.resolve(strict=True) == path, 'unsafe_history_path')
    names = path.parts[1:]
    fds, observed = [], []
    try:
        fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        fds.append(fd)
        for index in range(len(names) + 1):
            info = os.fstat(fd)
            require(stat.S_ISDIR(info.st_mode) and info.st_uid in (0, os.getuid()) and
                    not stat.S_IMODE(info.st_mode) & 0o022, 'unsafe_parent')
            if index == len(names):
                checked(info, True)
            observed.append((identity(info), safe_acl(fd, True)))
            if index < len(names):
                child = os.open(names[index], os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                fds.append(child)
                require(identity(os.stat(names[index], dir_fd=fd, follow_symlinks=False)) ==
                        identity(os.fstat(child)), 'parent_changed')
                fd = child
        yield fd
        for index, held in enumerate(fds):
            require((identity(os.fstat(held)), safe_acl(held, True)) == observed[index], 'parent_changed')
            if index:
                require(identity(os.stat(names[index - 1], dir_fd=fds[index - 1], follow_symlinks=False)) ==
                        observed[index][0], 'parent_changed')
    finally:
        for fd in reversed(fds):
            os.close(fd)


def read_private(path, limit=65536):
    path = Path(path)
    with private_chain(path.parent) as dfd:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=dfd)
        try:
            info = os.fstat(fd)
            checked(info)
            require(info.st_size <= limit and
                    identity(os.stat(path.name, dir_fd=dfd, follow_symlinks=False)) == identity(info), 'unsafe_packet')
            file_acl = safe_acl(fd, False)
            data = bytearray()
            while len(data) <= limit:
                part = os.read(fd, min(4096, (limit + 1) - len(data)))
                if not part:
                    break
                data.extend(part)
            after = os.fstat(fd)
            checked(after)
            require(len(data) <= limit and identity(after) == identity(info) and
                    (after.st_size, after.st_mtime_ns, after.st_ctime_ns) ==
                    (info.st_size, info.st_mtime_ns, info.st_ctime_ns) and
                    identity(os.stat(path.name, dir_fd=dfd, follow_symlinks=False)) == identity(info) and
                    safe_acl(fd, False) == file_acl, 'packet_changed')
        finally:
            os.close(fd)
    return bytes(data)



def read_packet(path):
    return parse_packet(read_private(path))


def parse_packet(data):
    p = decode(data, 65536)
    if p.get('kind') == 'historical_retained_case':
        shape(p, 'kind packet retained_case retained_case_sha256')
        require(digest(p['retained_case']) == hash_id(p['retained_case_sha256']), 'retained_case_hash')
        validate_packet(p['packet'], allow_unknown_ids=True)
        return expand_retained(p['packet'], p['retained_case']), hashlib.sha256(bytes(data)).hexdigest()
    require(len(data) <= 16384, 'legacy_packet_size')
    validate_packet(p)
    return p, hashlib.sha256(bytes(data)).hexdigest()


def validate_packet(p, *, allow_unknown_ids=False):
    shape(p, 'kind source_sha256 source_report_sha256 case_id version material_evidence title year asserted_imdb reported_candidate_tmdb reason first_observed last_observed source_generated_at source_acquired_at report_partial reported_movie_search event_id delivery_id captured_bytes currentness decisions identity_approval acquisition_approval')
    require(p['kind'] == 'historical_normalized_projection' and p['captured_bytes'] is False and
            p['event_id'] is None and p['delivery_id'] is None and
            all(p[k] == 'unknown' for k in ('currentness', 'decisions', 'identity_approval', 'acquisition_approval')),
            'normalized_unknowns_required')
    for k in ('source_sha256', 'source_report_sha256', 'version', 'material_evidence'):
        hash_id(p[k])
    scope(dict(source='normalized', case_id=p['case_id'], version=p['version'], occurrence=None))
    text(p['title'], 200)
    require(type(p['year']) is int and 1800 <= p['year'] <= 2100, 'year')
    import re
    require((allow_unknown_ids and p['asserted_imdb'] is None) or
            (isinstance(p['asserted_imdb'], str) and re.fullmatch(r'tt[0-9]{7,10}', p['asserted_imdb'])), 'imdb')
    require((allow_unknown_ids and p['reported_candidate_tmdb'] is None) or
            (type(p['reported_candidate_tmdb']) is int and 0 < p['reported_candidate_tmdb'] < 2**31), 'tmdb')
    text(p['reason'], 100)
    require(stamp(p['first_observed']) <= stamp(p['last_observed']), 'observation_order')
    text(p['source_generated_at'], 64)
    text(p['source_acquired_at'], 64)
    require(p['report_partial'] is True and (p['reported_movie_search'] == 'verified_negative_measurement_time_unknown' or
            allow_unknown_ids and p['reported_movie_search'] == 'not_observed'), 'historical_limits_required')
    return p


def expand_retained(packet, case):
    """Typed offline projection of one retained case; hashes are not authenticity."""
    validate_packet(packet, allow_unknown_ids=True)
    require(isinstance(case, dict) and len(encoded(case)) <= 49152, 'retained_case_size')
    require(all(case.get(k) == packet[k] for k in ('case_id', 'version', 'title', 'year', 'reason')),
            'retained_case_binding')
    require(case.get('first_observed_at') == packet['first_observed'] and
            case.get('observed_at') == packet['last_observed'], 'retained_occurrence_clock_binding')
    source_identity = case.get('source_identity', {})
    require(type(source_identity) is dict and 'asserted_imdb' in source_identity
            and source_identity['asserted_imdb'] == packet['asserted_imdb'], 'retained_case_binding')
    result = case.get('proposal', {}).get('result', {})
    original = result.get('original_facts', {})
    require(original.get('title') == packet['title'] and original.get('year') == packet['year']
            and 'imdb' in original and original['imdb'] == packet['asserted_imdb'], 'retained_original_binding')
    if packet['asserted_imdb'] is None or packet['reported_candidate_tmdb'] is None:
        # This narrow route cannot silently discard other supplied identity bindings.
        require(all(source_identity.get(k) is None for k in ('imdb', 'tmdb', 'asserted_tmdb'))
                and all(original.get(k) is None for k in ('tmdb', 'asserted_imdb', 'asserted_tmdb')),
                'retained_unprojected_identity')
    missing = [key for key in ('asserted_imdb', 'reported_candidate_tmdb') if packet[key] is None]

    def value(obj, key, path, check):
        v = obj.get(key)
        if v is None:
            missing.append(path + '.' + key)
            return None
        require(check(v), 'retained_field_invalid')
        return v

    def string(v):
        text(v, 200)
        return True

    def strings(v):
        return type(v) is list and len(v) <= 40 and all(string(x) for x in v)

    observations = []
    rows = result.get('evidence', [])
    require(type(rows) is list and len(rows) <= 12, 'retained_evidence_limit')
    seen = set()
    for e in rows:
        method = e.get('method')
        if method not in ('find', 'details', 'movie_search'):
            missing.append('unsupported_evidence_method')
            continue
        require(method not in seen, 'retained_duplicate_method')
        seen.add(method)
        r = e.get('result', {})
        observed = value(r, 'observed_at', method, lambda x: stamp(x) >= 0)
        expires = value(r, 'expires_at', method, lambda x: stamp(x) >= 0)
        require(observed is None or expires is None or expires > observed, 'retained_clock_order')
        reason = value(r, 'reason', method, string)
        data = r.get('data', {})
        require(type(data) is dict, 'retained_data')
        query = e.get('query')
        if method == 'find':
            require(packet['asserted_imdb'] is not None and query == packet['asserted_imdb'], 'retained_find_binding')
            movies = value(data, 'movies', method, lambda x: type(x) is list and len(x) <= 5)
            selected = None if movies is None else [catalogue(m, missing, 'find.movie') for m in movies]
            detail = dict(movies=selected)
        elif method == 'details':
            require(packet['asserted_imdb'] is not None and packet['reported_candidate_tmdb'] is not None
                    and type(query) is int and type(data.get('id')) is int
                    and query == packet['reported_candidate_tmdb'] and data.get('id') == query
                    and data.get('imdb') == packet['asserted_imdb'], 'retained_details_binding')
            detail = catalogue(data, missing, 'details', full=True)
        else:
            require(query == packet['title'], 'retained_search_binding')
            hits = value(data, 'results', method, lambda x: type(x) is list and len(x) <= 5)
            detail = dict(results=None if hits is None else [catalogue(m, missing, 'search.movie') for m in hits])
        observations.append(dict(method=method, query=query, reason=reason,
                                 observed_at=observed, expires_at=expires, data=detail))
    missing.extend('evidence.' + m for m in ('find', 'details', 'movie_search') if m not in seen)
    torrent = original.get('torrent_evidence', {})
    require(type(torrent) is dict, 'retained_torrent')
    desc = torrent.get('description', {}).get('text')
    description = dict(year=None, runtime_minutes=None, cast=None, independent_of_tracker_id=None)
    if desc is not None:
        require(type(desc) is str and len(desc) <= 4096, 'retained_description_size')
        y = re.search(r'\bYear:\s*(\d{4})\b', desc)
        duration = re.search(r'\bDuration:\s*(\d{1,3})\s*min\b', desc)
        cast = re.search(r'\bStars:\s*(.*)$', desc)
        names = [x.strip() for x in cast[1].split(',')] if cast else []
        catalogue_names = {name for obs in observations if obs['method'] == 'details'
                           for name in (obs['data'].get('cast') or [])}
        # A free-text tail is never itself a name allowlist. Only exact names
        # already present in the selected structured catalogue can be projected.
        bound_cast = names if 0 < len(names) <= 12 and all(n in catalogue_names for n in names) else None
        if bound_cast is None: missing.append('description.cast_unparsed_or_not_catalogue_bound')
        description.update(year=int(y[1]) if y else None, runtime_minutes=int(duration[1]) if duration else None,
                           cast=bound_cast)
    candidates = result.get('candidates', [])
    require(type(candidates) is list and len(candidates) <= 5, 'retained_candidate_limit')
    conflicts = []
    for c in candidates:
        cr = c.get('record', {})
        cid = value(cr, 'id', 'candidate', lambda x: type(x) is int and 0 < x < 2**31)
        conflicts.append(dict(id=cid, contradictions=value(c, 'contradictions', 'candidate', strings),
                              source_contradictions=value(c, 'source_contradictions', 'candidate', strings)))
    reviews = [c.get('source_review', {}) for c in candidates if c.get('record', {}).get('id') == packet['reported_candidate_tmdb']]
    require(len(reviews) <= 1, 'retained_candidate_ambiguous')
    if reviews:
        description['independent_of_tracker_id'] = value(reviews[0], 'description_independent_of_tracker_id',
                                                         'source_review', lambda x: type(x) is bool)
    for k, v in description.items():
        if v is None: missing.append('description.' + k)
    nfo = torrent.get('nfo', {}).get('text')
    durations = []
    if nfo is not None:
        require(type(nfo) is str and len(nfo) <= 16384, 'retained_nfo_size')
        # Preserve track labels; never reduce a subtitle duration to film runtime.
        sections = re.split(r'\b(Video|Audio|Text) ID\s*:\s*\d+\s*', nfo)
        for i in range(0, len(sections), 2):
            label = 'container' if i == 0 else {'Video':'video','Audio':'audio','Text':'subtitle'}[sections[i-1]]
            for h, m in re.findall(r'\bDuration\s*:\s*(\d{1,2}) h (\d{1,2}) min\b', sections[i]):
                durations.append(dict(stream=label, minutes=int(h)*60+int(m)))
        require(len(durations) <= 16, 'retained_stream_limit')
    for label in ('container', 'video', 'audio', 'subtitle'):
        if not any(d['stream'] == label for d in durations): missing.append('nfo.duration.' + label)
    for k in ('truncated', 'unavailable_images'):
        if k not in torrent: missing.append('torrent.' + k)
    require(type(torrent.get('truncated')) in (bool, type(None)) and
            (torrent.get('unavailable_images') is None or type(torrent['unavailable_images']) is int
             and 0 <= torrent['unavailable_images'] <= 100), 'retained_source_qualification')
    crosswalk = result.get('missing_crosswalk')
    require(type(crosswalk) in (bool, type(None)), 'retained_crosswalk')
    if crosswalk is None: missing.append('missing_crosswalk')
    expanded = dict(packet, kind='historical_expanded_projection', retained_case_sha256=digest(case),
                    observations=dict(catalogue=observations, candidate_conflicts=conflicts, description=description, stream_durations=durations,
                      missing_crosswalk=crosswalk, source_truncated=torrent.get('truncated'),
                      unavailable_images=torrent.get('unavailable_images'), missing_fields=sorted(set(missing)),
                      omitted_fields=['raw NFO and description text', 'images and URLs', 'catalogue aliases and translations',
                                      'original source identifiers and private bindings']))
    # Absence is not a negative search result; preserve full-input bytes when all methods exist.
    absent = {method: 'not_observed' for method in ('find', 'details', 'movie_search') if method not in seen}
    if absent:
        expanded['observations']['missing_observations'] = absent
    if 'movie_search' in absent:
        expanded['reported_movie_search'] = 'not_observed'
    require(len(encoded(expanded)) <= 16384, 'expanded_packet_size')
    return expanded


def catalogue(data, missing, path, full=False):
    require(type(data) is dict, 'retained_catalogue')
    keys = ('id', 'title', 'original_title', 'date', 'type')
    if full: keys += ('imdb', 'runtime', 'directors', 'cast', 'dates')
    out = {}
    for k in keys:
        v = data.get(k)
        if v is None: missing.append(path + '.' + k)
        elif k in ('id', 'runtime'):
            require(type(v) is int and 0 < v < (2**31 if k == 'id' else 1000), 'retained_catalogue_number')
        elif k in ('directors', 'cast', 'dates'):
            require(type(v) is list and len(v) <= 40, 'retained_catalogue_list')
            for item in v: text(item, 200)
        else: text(v, 200)
        out[k] = v
    return out


def build_request(packet, packet_sha256, *, now=None):
    """Offline-only request preview and rehearsal; never a live disclosure grant."""
    binding = dict(source='normalized', case_id=packet['case_id'], version=packet['version'], occurrence=None)
    run = digest(dict(packet_sha256=packet_sha256, purpose='offline_rehearsal'))
    # This describes a local projection, never an authenticated source receipt.
    row = dict(id='normalized_projection', kind='source', candidate=None, claims=[])
    facts = dict(title=packet['title'], year=packet['year'], imdb=None, tmdb=None,
                 asserted_imdb=packet['asserted_imdb'], asserted_tmdb=None,
                 contradiction=packet['reason'])
    disclosure = dict(facts=facts, rows={row['id']: dict(view=row_view(row), original_hash=digest(row))})
    prompt = dict(facts=dict(title=facts['title'], year=facts['year'], imdb=None, tmdb=None,
                             outcome=dict(asserted_imdb=facts['asserted_imdb'], asserted_tmdb=None,
                                          reason=facts['contradiction'])),
                  reconciliation=dict(conflicting_ids=None), query_results=[dict(rows=[row])])
    body = project(prompt, run=run, disclosure=disclosure)
    if packet['kind'] == 'historical_expanded_projection':
        wire = decode(body, 65536)
        data = decode(wire['input'][0]['content'][0]['text'], 32768)
        observations = decode(encoded(packet['observations']), 16384)
        instant = time.time() if now is None else stamp(now)
        for row in observations['catalogue']:
            row['expiry_status'] = ('unknown' if row['observed_at'] is None or row['expires_at'] is None else
                                    'future_observation_unverified' if row['observed_at'] > instant else
                                    'expired' if row['expires_at'] <= instant else 'unexpired_at_construction')
        data['historical_observations'] = observations
        data['qualifications'] = dict(assessment_at=instant, historical=True, authenticated_provider_receipt=False,
            report_partial=packet['report_partial'], currentness=packet['currentness'], decisions=packet['decisions'],
            identity_approval=packet['identity_approval'], acquisition_approval=packet['acquisition_approval'],
            captured_bytes=False, physical_source_verified=False, first_observed=packet['first_observed'],
            last_observed=packet['last_observed'], source_generated_at=packet['source_generated_at'],
            source_acquired_at=packet['source_acquired_at'], output_limit='unresolved or blocked only; historical proposal in rationale')
        wire['input'][0]['content'][0]['text'] = encoded(data).decode()
        body = encoded(wire)
        require(len(body) <= 65536, 'expanded_request_size')
    return binding, run, disclosure, body


def rehearse(packet, packet_sha256, directory, *, ceiling, response=None):
    """Construct, simulate and validate once; the supplied response is fixture-only."""
    directory = Path(directory)
    history = History(directory)
    binding, run, disclosure, body = build_request(packet, packet_sha256)
    reservation = dict(local_request_id='SIMULATED-' + run[:24], request_hash=digest(decode(body, 65536)))
    spending = SimulatedSpending(history, binding=binding, ceiling=ceiling, expires_at=4102444800)
    spending.reserve(body, reservation, binding)
    spending.before_send(body, reservation)
    invented = dict(binding_hash=aliases(run), kind='final', lookups=[], result=dict(
        status='unresolved', candidate=None, alternatives=[], citations=[],
        rationale='The retained title and year require human review.',
        uncertainty='Historical normalized facts do not establish identity or currentness.',
        next_action='obtain_retained_evidence'))
    fixture = simulated_response(invented, 1) if response is None else response
    http = SimulatedHTTP([fixture])
    try:
        res = http.post(body, credential=ExplicitCredential(SYNTHETIC_CREDENTIAL), project=SYNTHETIC_PROJECT, timeout=1)
        require(type(res) is HTTPResult and res.status == 200, 'simulated_http_failure')
        answer, accounting = parse_response(res.body, output_schema(), request_id=res.request_id)
        accounting.update(local_request_id=reservation['local_request_id'], request_hash=reservation['request_hash'])
        spending.settle(reservation, accounting)
        restored = restore(decode(answer), run=run, disclosure=disclosure, binding_hash=digest(binding))
        result = validate_final(restored['result'], {}, dict(conflicting_ids=True, known_identity=None), time.time())
        require(result['status'] != 'supported_candidate' and not result['alternatives'], 'normalized_identity_not_established')
        outcome = dict(state='validated_simulated_response', result=result, simulated_accounting='settled')
    except (Refusal, ValueError, TypeError):
        # No retry: a response or its accounting may be unknown. The history keeps
        # any unsettled simulated reservation across restart.
        outcome = dict(state='simulated_response_or_validation_failed', result=None,
                       simulated_accounting='see_private_history_no_retry')
    return dict(kind='offline_manual_diagnostic', simulation=True, live_provider_called=False,
                input_kind=packet['kind'], input_sha256=packet_sha256,
                source_sha256=packet['source_sha256'], source_report_sha256=packet['source_report_sha256'],
                case_id=packet['case_id'], version=packet['version'], material_evidence=packet['material_evidence'],
                first_observed=packet['first_observed'], last_observed=packet['last_observed'],
                source_generated_at=packet['source_generated_at'], source_acquired_at=packet['source_acquired_at'],
                report_partial=packet['report_partial'],
                reported_movie_search=('see_dated_constructed_request' if packet['kind'] == 'historical_expanded_projection'
                                       else packet['reported_movie_search']),
                facts=dict(title=packet['title'], source_year=packet['year'], asserted_imdb=packet['asserted_imdb'],
                           reported_candidate_tmdb=packet['reported_candidate_tmdb'], reason=packet['reason']),
                unknowns=['original event and delivery IDs', 'captured event bytes', 'currentness',
                          'complete occurrence decisions', 'identity and acquisition approval', 'edition and suitability'],
                qualification='Invented response, not an identification, live authorization, current case or download approval.',
                provenance_limit='Source hashes and facts are packet assertions; this program does not verify retained source files.',
                disclosure_limit=('Expanded typed historical observations; raw text and private bindings remain local.'
                                  if packet['kind'] == 'historical_expanded_projection' else
                                  'Reduced legacy request: title, source year, asserted IMDb and reason only; incomplete evidence.'),
                constructed_request=decode(body, 65536),
                request_sha256=hashlib.sha256(body).hexdigest(),
                **outcome)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true', help='Always refused; no live implementation exists')
    parser.add_argument('--prepare', action='store_true', help='Freeze a supervised historical request; no generation')
    parser.add_argument('--complete', action='store_true', help='Validate one externally supplied supervised reply')
    parser.add_argument('--reply', type=Path)
    parser.add_argument('--provenance', type=Path)
    parser.add_argument('--input', type=Path)
    parser.add_argument('--selector', type=Path, help='Explicit case/version/title selector for prepare with a selected companion')
    parser.add_argument('--companion', type=Path, help='Optional private normalized observation, prepare only')
    parser.add_argument('--output-dir', type=Path, help='Existing owner-only private directory')
    parser.add_argument('--simulated-ceiling-millionths', type=int, default=500000)
    args = parser.parse_args()
    if args.live:
        parser.exit(2, real_activation_refusal(None) + '\n')
    if args.selector is not None and (not args.prepare or args.complete or args.companion is None):
        parser.error('--selector requires --prepare and --companion')
    if args.companion is not None and (not args.prepare or args.complete):
        parser.error('--companion requires --prepare only')
    if args.prepare or args.complete:
        from .manual_supervised import prepare, complete
        from .source_case import Refused as SourceRefused
        if args.prepare == args.complete or args.output_dir is None:
            parser.error('Select exactly one manual operation and an output directory')
        try:
            if args.prepare:
                if args.input is None: parser.error('--prepare requires --input')
                prepare(args.input, args.output_dir, companion_path=args.companion, selector_path=args.selector)
            else:
                if args.reply is None or args.provenance is None: parser.error('--complete requires --reply and --provenance')
                complete(args.output_dir, args.reply, args.provenance)
            print('Supervised manual ' + ('prepared' if args.prepare else 'validated') + '; no generation or approval.')
        except (Refusal, SourceRefused, StorageError, OSError, ValueError, TypeError, KeyError, IndexError) as exc:
            parser.exit(2, 'Supervised manual refused: ' + (str(exc) if isinstance(exc, Refusal) else 'local_input_or_storage_error') + '\n')
        return
    if args.input is None or args.output_dir is None:
        parser.error('--input and --output-dir are required')
    try:
        p, sha = read_packet(args.input)
        with private_chain(args.output_dir) as dfd:
            with os.scandir(dfd) as entries:
                require(next(entries, None) is None, 'rehearsal_directory_not_empty')
            # Exclusive creation is intentionally before any simulated send.
            fd = os.open('report.json', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=dfd)
            try:
                before = os.fstat(fd)
                checked(before)
                file_acl = safe_acl(fd, False)
                require(identity(os.stat('report.json', dir_fd=dfd, follow_symlinks=False)) == identity(before),
                        'report_changed')
                result = rehearse(p, sha, args.output_dir, ceiling=[args.simulated_ceiling_millionths, 1000000])
                body = encoded(result) + b'\n'
                while body:
                    written = os.write(fd, body)
                    require(written > 0, 'report_write_failed')
                    body = body[written:]
                os.fsync(fd)
                checked(os.fstat(fd))
                require(identity(os.fstat(fd)) == identity(before) and safe_acl(fd, False) == file_acl and
                        identity(os.stat('report.json', dir_fd=dfd, follow_symlinks=False)) == identity(before),
                        'report_changed')
                os.fsync(dfd)
            finally:
                os.close(fd)
        print('Offline simulation: ' + result['state'] + '; see private report.json. No provider was contacted.')
    except (Refusal, StorageError, OSError, ValueError) as exc:
        parser.exit(2, 'Offline rehearsal refused: ' + (str(exc) if isinstance(exc, Refusal) else 'local_input_or_storage_error') + '\n')


if __name__ == '__main__':
    main()
