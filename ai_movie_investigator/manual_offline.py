"""One-case historical projection rehearsal. This module cannot call a provider.

The response is invented, not a model result. This route does not admit a case
into the pilot or establish identity, currentness, approval, or a real budget.
"""
import argparse
import contextlib
import hashlib
import os
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


def read_packet(path):
    path = Path(path)
    with private_chain(path.parent) as dfd:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=dfd)
        try:
            info = os.fstat(fd)
            checked(info)
            require(info.st_size <= 16384 and
                    identity(os.stat(path.name, dir_fd=dfd, follow_symlinks=False)) == identity(info), 'unsafe_packet')
            file_acl = safe_acl(fd, False)
            data = bytearray()
            while len(data) <= 16384:
                part = os.read(fd, min(4096, 16385 - len(data)))
                if not part:
                    break
                data.extend(part)
            after = os.fstat(fd)
            checked(after)
            require(len(data) <= 16384 and identity(after) == identity(info) and
                    (after.st_size, after.st_mtime_ns, after.st_ctime_ns) ==
                    (info.st_size, info.st_mtime_ns, info.st_ctime_ns) and
                    identity(os.stat(path.name, dir_fd=dfd, follow_symlinks=False)) == identity(info) and
                    safe_acl(fd, False) == file_acl, 'packet_changed')
        finally:
            os.close(fd)
    p = decode(bytes(data), 16384)
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
    require(isinstance(p['asserted_imdb'], str) and re.fullmatch(r'tt[0-9]{7,10}', p['asserted_imdb']), 'imdb')
    require(type(p['reported_candidate_tmdb']) is int and 0 < p['reported_candidate_tmdb'] < 2**31, 'tmdb')
    text(p['reason'], 100)
    require(stamp(p['first_observed']) <= stamp(p['last_observed']), 'observation_order')
    text(p['source_generated_at'], 64)
    text(p['source_acquired_at'], 64)
    require(p['report_partial'] is True and p['reported_movie_search'] == 'verified_negative_measurement_time_unknown', 'historical_limits_required')
    return p, hashlib.sha256(bytes(data)).hexdigest()


def rehearse(packet, packet_sha256, directory, *, ceiling, response=None):
    """Construct, simulate and validate once; the supplied response is fixture-only."""
    directory = Path(directory)
    history = History(directory)
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
                report_partial=packet['report_partial'], reported_movie_search=packet['reported_movie_search'],
                facts=dict(title=packet['title'], source_year=packet['year'], asserted_imdb=packet['asserted_imdb'],
                           reported_candidate_tmdb=packet['reported_candidate_tmdb'], reason=packet['reason']),
                unknowns=['original event and delivery IDs', 'captured event bytes', 'currentness',
                          'complete occurrence decisions', 'identity and acquisition approval', 'edition and suitability'],
                qualification='Invented response, not an identification, live authorization, current case or download approval.',
                provenance_limit='Source hashes and facts are packet assertions; this program does not verify retained source files.',
                disclosure_limit='The simulated request contains title, source year, asserted IMDb and reason only; candidate, clocks, partial status and search observation remain local.',
                **outcome)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true', help='Always refused; no live implementation exists')
    parser.add_argument('--input', type=Path)
    parser.add_argument('--output-dir', type=Path, help='Existing owner-only private directory')
    parser.add_argument('--simulated-ceiling-millionths', type=int, default=500000)
    args = parser.parse_args()
    if args.live:
        parser.exit(2, real_activation_refusal(None) + '\n')
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
