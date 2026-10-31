"""Caller-invoked offline reporting cycles. No transport, scheduler or worker hooks.

All directories are explicit, stable, owner-controlled authority. Owner evidence
must be authenticated/selected by the external owner BEFORE staging its inbox;
this module validates bindings and bytes, not the origin of identical bytes.
"""
import base64
import contextlib
import copy
import fcntl
import os
from pathlib import Path
import re
import stat

from automation import coordinator as c
from automation import coordinator_io as io
from automation import coordinator_sources as sources
from automation import coordinator_exports as exports
from automation import coordinator_diagnostics as diagnostics
from automation.coordinator_integration import PublicParser

VERSION = 2
RECEIPT_VERSION = 1
MAX_CYCLES = 4096
MAX_ACTIVE = 20
MAX_ARCHIVE = 256
MAX_STATE = 4 * 1024 * 1024
MAX_PAYLOAD = 524288
MAX_EVIDENCE = 8 * 1024 * 1024
MAX_RECORD = 12 * 1024 * 1024
RECORD_RESERVE = 65536  # Attempt plus two bounded base64-encoded receipts.
MAX_ACTIVE_BYTES = 128 * 1024 * 1024
MAX_ARCHIVE_BYTES = 256 * 1024 * 1024
MAX_STAGE_BYTES = 64 * 1024 * 1024
LAYOUT = {'version': VERSION, 'component': 'coordinator_cycles'}


def canonical(path):
    value = str(path)
    p = Path(value)
    c.require(p.is_absolute() and p.anchor == '/' and str(p) == value
              and all(x not in ('.', '..') for x in p.parts), 'cycle_root')
    return p


def private(fd, directory=False):
    info = os.fstat(fd)
    c.require((stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
              and info.st_uid == os.getuid() and info.st_mode & 0o077 == 0
              and (directory or info.st_nlink == 1), 'cycle_private')


def read(fd, name, limit=MAX_RECORD):
    # Check permissions and links on every owned/inbox file as well as read bounds.
    target = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
    try:
        private(target)
    finally:
        os.close(target)
    return io.read_from_directory(fd, name, limit, reject_hardlinks=True)


def clear_temporary(fd):
    try:
        info = os.stat('.write', dir_fd=fd, follow_symlinks=False)
    except FileNotFoundError:
        return
    c.require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
              and info.st_mode & 0o077 == 0 and info.st_size <= MAX_RECORD, 'cycle_temporary')
    if info.st_nlink != 1:
        # Recover only our atomic-publication link, never an arbitrary hardlink.
        peers = [name for name in os.listdir(fd) if name != '.write'
                 and (name in ('identity.json', 'state.json', 'current.json', 'collection.json',
                               'independent.json', 'manifest.json')
                      or re.fullmatch('[a-f0-9]{64}\.json', name)
                      or name in {s + '.json' for s in sources.SOURCES})
                 and os.path.samestat(info, os.stat(name, dir_fd=fd, follow_symlinks=False))]
        c.require(info.st_nlink == 2 and len(peers) == 1, 'cycle_temporary_links')
    os.unlink('.write', dir_fd=fd)
    os.fsync(fd)


def write(fd, name, raw, replace=False):
    """Exclusive temporary, atomic install, fixed bounded crash debris."""
    temporary = '.write'
    clear_temporary(fd)
    target = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=fd)
    try:
        with os.fdopen(target, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        if replace:
            try:
                read(fd, name)
            except FileNotFoundError:
                pass
        else:
            try:
                existing = read(fd, name)
            except FileNotFoundError:
                pass
            else:
                c.require(existing == raw, 'cycle_conflict')
                os.fsync(fd)
                return
        if replace:
            os.rename(temporary, name, src_dir_fd=fd, dst_dir_fd=fd)
        else:
            # Temporary hardlink is atomic create-only publication, as in the
            # accepted reader. Never use source links as staging shortcuts.
            os.link(temporary, name, src_dir_fd=fd, dst_dir_fd=fd, follow_symlinks=False)
            os.unlink(temporary, dir_fd=fd)
        os.fsync(fd)
    finally:
        try:
            os.unlink(temporary, dir_fd=fd)
        except FileNotFoundError:
            pass


def child(fd, name):
    target = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
    try:
        private(target, True)
        return target
    except BaseException:
        os.close(target)
        raise


def inventory(fd, count, limit):
    names = os.listdir(fd)
    c.require(len(names) <= count, 'cycle_backpressure')
    total = 0
    for name in names:
        raw = read(fd, name, MAX_RECORD)
        total += len(raw)
    c.require(total <= limit, 'cycle_backpressure')
    return names, total


def disjoint(a, b):
    # Both directions matter: a source may not be inside new owned state either.
    exports._outside_source(a, b)
    exports._outside_source(b, a)


@contextlib.contextmanager
def protected_directory(path, existing, output_parent):
    """Prove a no-follow spelling, allowing only a proven missing descendant.

    A failed open/stat is never evidence of absence or of a particular symlink
    cause. Accessible ancestors also prove that a missing source is outside an
    existing writable root. Caller-owned descriptors remain caller-owned.
    """
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:]:
            try:
                info = os.stat(part, dir_fd=fd, follow_symlinks=False)
            except FileNotFoundError:
                if existing is not None:
                    exports._outside_source(fd, existing)
                else:
                    # Both final names can be absent yet alias on this FS. A
                    # shared immediate parent cannot prove prospective separation.
                    c.require(not os.path.samestat(os.fstat(fd), os.fstat(output_parent)),
                              'cycle_source_separation')
                yield None
                return
            c.require(stat.S_ISDIR(info.st_mode), 'cycle_source_path')
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            previous, fd = fd, next_fd
            os.close(previous)
            c.require(os.path.samestat(info, os.fstat(fd)), 'cycle_source_changed')
        yield fd
    finally:
        os.close(fd)


@contextlib.contextmanager
def store(root, runtime, owner, protected=()):
    root = canonical(root)
    c.identifier(runtime); c.identifier(owner)
    checkout = Path(__file__).resolve().parent.parent
    with io.directory(root.parent) as parent, io.directory(checkout) as checkout_fd:
        private(parent, True)
        exports._outside_source(parent, checkout_fd)
        # Every separation guard runs before mkdir, marker, lock or cleanup.
        # Missing protected descendants are safe only after checking their actual
        # no-follow ancestors; ambiguous/inaccessible roots fail closed.
        with contextlib.ExitStack() as preflight:
            try:
                existing = preflight.enter_context(io.directory(root))
            except FileNotFoundError:
                # Parent is pinned and accessible; verify the final entry alone.
                try:
                    os.stat(root.name, dir_fd=parent, follow_symlinks=False)
                except FileNotFoundError:
                    existing = None
                else:
                    raise
            if existing is not None:
                private(existing, True)
                disjoint(existing, checkout_fd)
            for path in protected:
                with protected_directory(path, existing, parent) as source_fd:
                    if source_fd is not None:
                        exports._outside_source(parent, source_fd)
                        if existing is not None:
                            disjoint(existing, source_fd)
        created = False
        try:
            os.mkdir(root.name, 0o700, dir_fd=parent)
            os.fsync(parent)
            created = True
        except FileExistsError:
            pass
        with io.directory(root) as fd:
            private(fd, True)
            marker = {**LAYOUT, 'runtime': runtime, 'owner': owner}
            if created:
                write(fd, 'identity.json', io.encode(marker))
            else:
                c.require(io.decode(read(fd, 'identity.json')) == marker, 'cycle_unowned_root')
            flags = os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK
            try:
                lock = os.open('lock', flags | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=fd)
            except FileExistsError:
                lock = os.open('lock', flags, dir_fd=fd)
            try:
                private(lock)
                fcntl.flock(lock, fcntl.LOCK_EX)
                clear_temporary(fd)
                handles = {}
                with contextlib.ExitStack() as stack:
                    for name in ('staging', 'active', 'archive', 'handoff'):
                        try:
                            os.mkdir(name, 0o700, dir_fd=fd)
                            os.fsync(fd)
                        except FileExistsError:
                            pass
                        handles[name] = child(fd, name)
                        stack.callback(os.close, handles[name])
                        clear_temporary(handles[name])
                    try:
                        state = io.decode(read(fd, 'state.json', MAX_STATE))
                    except FileNotFoundError:
                        c.require(all(not os.listdir(handle) for handle in handles.values())
                                  and 'current.json' not in os.listdir(fd), 'cycle_state_missing')
                        state = {**marker, 'cycles': {}, 'reports': {}, 'baseline': None,
                                 'current': None, 'collecting': None}
                    validate_state(state)
                    c.require(state['version'] == VERSION and state['component'] == LAYOUT['component']
                              and state['runtime'] == runtime and state['owner'] == owner,
                              'cycle_state')
                    c.require(len(state['cycles']) <= MAX_CYCLES and len(state['reports']) <= MAX_ACTIVE + MAX_ARCHIVE,
                              'cycle_backpressure')
                    yield root, fd, handles, state
            finally:
                os.close(lock)


def validate_state(state):
    c.keys(state, 'version component runtime owner cycles reports baseline current collecting')
    c.require(type(state['version']) is int and state['version'] == VERSION
              and state['component'] == LAYOUT['component'], 'cycle_schema')
    c.identifier(state['runtime']); c.identifier(state['owner'])
    c.require(isinstance(state['cycles'], dict) and len(state['cycles']) <= MAX_CYCLES
              and isinstance(state['reports'], dict)
              and len(state['reports']) <= MAX_ACTIVE + MAX_ARCHIVE, 'cycle_capacity')
    for cid, entry in state['cycles'].items():
        c.identifier(cid)
        c.keys(entry, 'request status report checkpoints' + (' collection' if 'collection' in entry else ''))
        c.keys(entry['checkpoints'], 'independent collection')
        for digest in entry['checkpoints'].values():
            if digest is not None:
                sources.hex64(digest)
        c.require(entry['status'] in ('collecting', 'quiet', 'prepared', 'backpressure'), 'cycle_status')
        if 'collection' in entry:
            c.require(entry['collection'] in ('collected', 'movie_unavailable', 'interrupted'), 'cycle_collection')
        request = entry['request']
        c.keys(request, 'runtime owner cycle now source_root evidence_root manifest destination recipient')
        c.require(request['runtime'] == state['runtime'] and request['owner'] == state['owner']
                  and request['cycle'] == cid, 'cycle_request')
        c.stamp(request['now']); canonical(request['source_root'])
        if request['evidence_root'] is not None:
            canonical(request['evidence_root'])
        io.relative_path(request['manifest']); destination(request['destination']); c.identifier(request['recipient'])
        if entry['report'] is not None:
            sources.hex64(entry['report'])
            c.require(entry['report'] in state['reports'], 'cycle_report_missing')
    for rid, meta in state['reports'].items():
        sources.hex64(rid)
        c.keys(meta, 'cycle location publication recipient')
        c.require(meta['cycle'] in state['cycles'] and state['cycles'][meta['cycle']]['report'] == rid
                  and meta['location'] in ('active', 'archive')
                  and meta['publication'] in ('pending', 'uncertain', 'verified')
                  and meta['recipient'] in ('pending', 'acknowledged'), 'cycle_report_meta')
    if state['baseline'] is not None:
        sources.hex64(state['baseline'])
    if state['current'] is not None:
        c.keys(state['current'], 'cycle observed_at')
        c.require(state['current']['cycle'] in state['cycles'], 'cycle_current')
        c.stamp(state['current']['observed_at'])
    c.require(state['collecting'] is None or state['collecting'] in state['cycles'], 'cycle_collecting')


def stage_usage(fd):
    total, count = 0, 0
    for name in os.listdir(fd):
        if name in ('movie', 'combined'):
            sub = child(fd, name)
            try:
                if name == 'movie':
                    clear_reader_temporaries(sub)
                clear_temporary(sub)
                for item in os.listdir(sub):
                    total += len(read(sub, item))
                    count += 1
            finally:
                os.close(sub)
        else:
            total += len(read(fd, name))
            count += 1
    c.require(total <= MAX_STAGE_BYTES and count <= 32, 'cycle_staging_bound')
    return total


def save(fd, state):
    validate_state(state)
    raw = io.encode(state)
    c.require(len(raw) <= MAX_STATE, 'cycle_backpressure')
    write(fd, 'state.json', raw, replace=True)


def empty_manifest(reason='missing_entry'):
    return {'version': 2, 'repository': c.REPOSITORY,
            'sources': [{'id': s, 'path': None, 'sha256': None, 'revision': None,
                         'generated_at': None, 'observed_at': None, 'collected_at': None,
                         'max_age_seconds': sources.MAX_AGE[s]} for s in sources.SOURCES],
            'diagnostics': [diagnostics.diagnostic(s, 'acquisition', reason) for s in exports.EXPORTS]}


def pack(raw):
    return base64.b64encode(raw).decode('ascii')


def unpack(raw):
    return base64.b64decode(raw, validate=True)


def evidence_bound(evidence):
    c.require(isinstance(evidence, dict) and len(evidence) <= 16, 'cycle_evidence_count')
    c.require(sum(len(unpack(v)) for v in evidence.values()) <= MAX_EVIDENCE, 'cycle_evidence_bound')
    for name in evidence:
        io.relative_path(name)


def evidence_binding(evidence):
    """Bind captured bytes, including invalid input, independently of claims."""
    evidence_bound(evidence)
    return {name: {'sha256': io.digest(unpack(raw)), 'size': len(unpack(raw))}
            for name, raw in evidence.items()}


def checkpoint(stage, name, anchors):
    try:
        raw = read(stage, name + '.json')
    except FileNotFoundError:
        c.require(anchors[name] is None, 'cycle_checkpoint_missing')
        return None
    c.require(anchors[name] is not None and io.digest(raw) == anchors[name],
              'cycle_checkpoint_binding')
    return io.decode(raw)


def commit_checkpoint(stage, name, value, fd, state, entry):
    raw = io.encode(value)
    c.require(len(raw) <= MAX_RECORD, 'cycle_collection_bound')
    write(stage, name + '.json', raw)
    # A crash between file and state commits leaves an unverified checkpoint.
    # Preserve it and reject recovery; never bless mutable bytes after restart.
    entry['checkpoints'][name] = io.digest(raw)
    save(fd, state)


def independent(root, manifest_name, now):
    """Only explicit engineering/parent sources; never discover worker journals."""
    result = {'entries': [], 'evidence': {}, 'outcome': 'not_supplied'}
    if root is None:
        return result
    try:
        with io.directory(root) as fd:
            original_manifest = io.read_from_directory(fd, manifest_name, c.MAX_BYTES, reject_hardlinks=True)
            value = sources.manifest(io.decode(original_manifest), now)
            c.require(all(e['path'] is None for e in value['sources']
                          if e['id'] not in ('engineering', 'parent_status')), 'cycle_optional_sources')
            result['evidence']['independent-manifest.json'] = pack(original_manifest)
            for e in value['sources']:
                if e['id'] not in ('engineering', 'parent_status'):
                    continue
                entry = copy.deepcopy(e)
                if entry['path'] is not None:
                    try:
                        raw = io.read_from_directory(fd, entry['path'], c.MAX_BYTES, reject_hardlinks=True)
                    except sources.FAILURES:
                        # Keep the claimed binding; validator truthfully marks unreadable.
                        entry['path'] = entry['id'] + '.json'
                    else:
                        entry['path'] = entry['id'] + '.json'
                        result['evidence'][entry['path']] = pack(raw)
                result['entries'].append(entry)
            result['outcome'] = 'selected'
    except sources.FAILURES:
        result = {'entries': [], 'evidence': {}, 'outcome': 'unavailable'}
    return result


def clear_reader_temporaries(fd):
    for name in os.listdir(fd):
        if not re.fullmatch(r'\.export-[a-f0-9]{32}', name):
            continue
        info = os.stat(name, dir_fd=fd, follow_symlinks=False)
        c.require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
                  and info.st_mode & 0o077 == 0 and info.st_size <= c.MAX_BYTES, 'cycle_reader_temporary')
        if info.st_nlink != 1:
            peers = [p for p in ('investigations.json', 'research_report.json', 'manifest.json',
                                'observations.json', 'diagnostics.json')
                     if p in os.listdir(fd)
                     and os.path.samestat(info, os.stat(p, dir_fd=fd, follow_symlinks=False))]
            c.require(info.st_nlink == 2 and len(peers) == 1, 'cycle_reader_temporary_links')
        os.unlink(name, dir_fd=fd)
        os.fsync(fd)


def cleanup_stage(fd):
    """Only our reserved slot and declared reader/combined files, never recursion."""
    allowed = {'independent.json', 'collection.json', '.write'}
    for name in os.listdir(fd):
        if name in ('movie', 'combined'):
            sub = child(fd, name)
            try:
                if name == 'movie':
                    clear_reader_temporaries(sub)
                for item in os.listdir(sub):
                    valid = (item in {'manifest.json', 'observations.json', 'diagnostics.json', '.write'}
                             or item in {s + '.json' for s in sources.SOURCES}
                             or re.fullmatch(r'\.export-[a-f0-9]{32}', item))
                    c.require(valid, 'cycle_stage_unowned')
                    read(sub, item, MAX_RECORD)
                    os.unlink(item, dir_fd=sub)
                os.fsync(sub)
            finally:
                os.close(sub)
            os.rmdir(name, dir_fd=fd)
        else:
            c.require(name in allowed, 'cycle_stage_unowned')
            read(fd, name, MAX_RECORD)
            os.unlink(name, dir_fd=fd)
    os.fsync(fd)


def collect(root, handles, request, fd, state, resume=False):
    stage = handles['staging']
    stage_usage(stage)
    cycle_entry = state['cycles'][request['cycle']]
    saved = checkpoint(stage, 'independent', cycle_entry['checkpoints'])
    bound = checkpoint(stage, 'collection', cycle_entry['checkpoints'])
    if bound is not None:
        c.require(bound['request'] == c.fingerprint(request), 'cycle_collection_identity')
        c.require(evidence_binding(bound['evidence']) == bound['evidence_binding'],
                  'cycle_evidence_binding')
        return bound
    if saved is None:
        saved = independent(request['evidence_root'], request['manifest'], request['now']) if not resume else {
            'entries': [], 'evidence': {}, 'outcome': 'interrupted'}
        commit_checkpoint(stage, 'independent', saved, fd, state, cycle_entry)
    evidence = copy.deepcopy(saved['evidence'])
    value = empty_manifest('io_unknown' if resume else 'missing_entry')
    outcome = 'interrupted' if resume else 'movie_unavailable'
    if not resume:
        try:
            exports.stage_exports(request['source_root'], root / 'staging/movie', request['now'])
            with io.directory(root / 'staging/movie') as movie:
                value = io.decode(read(movie, 'manifest.json'))
                for name in os.listdir(movie):
                    evidence['reader/' + name] = pack(read(movie, name))
                for entry in value['sources']:
                    if entry['path'] is not None:
                        evidence[entry['path']] = pack(read(movie, entry['path']))
            outcome = 'collected'
        except sources.FAILURES as exc:
            reason = diagnostics.acquisition_reason(exc)
            if isinstance(exc, exports.StagingFailure):
                reason = 'io_unknown'
            value = empty_manifest(reason)
            outcome = 'movie_unavailable'
            # No completed reader bundle is asserted. Partial acquired originals
            # remain in our disposable slot until the durable outcome is committed.
            evidence = copy.deepcopy(saved['evidence'])
    # Composition has its own finite evidence budget. A movie staging failure
    # must still preserve the independently checkpointed engineering findings.
    if sum(len(unpack(raw)) for raw in evidence.values()) > MAX_EVIDENCE - 65536:
        evidence = copy.deepcopy(saved['evidence'])
        value = empty_manifest('io_unknown')
        outcome = 'movie_unavailable'
    for entry in saved['entries']:
        value['sources'] = [entry if x['id'] == entry['id'] else x for x in value['sources']]
    # Recovery never reuses partly written combined content. It is disposable;
    # only the durable independent checkpoint and completed collection bind data.
    try:
        os.mkdir('combined', 0o700, dir_fd=stage)
    except FileExistsError:
        c.require(resume, 'cycle_stage_collision')
        sub = child(stage, 'combined')
        try:
            for name in os.listdir(sub):
                c.require(name in {s + '.json' for s in sources.SOURCES} | {'manifest.json', '.write'},
                          'cycle_stage_unowned')
                read(sub, name)
                os.unlink(name, dir_fd=sub)
        finally:
            os.close(sub)
    combined = child(stage, 'combined')
    try:
        for entry in value['sources']:
            name = entry['path']
            if name is not None and name in evidence:
                write(combined, name, unpack(evidence[name]))
        manifest_raw = io.encode(value)
        write(combined, 'manifest.json', manifest_raw)
        evidence['combined-manifest.json'] = pack(manifest_raw)
        report = sources.observations(root / 'staging/combined', 'manifest.json', request['now'])
    finally:
        os.close(combined)
    evidence_bound(evidence)
    result = {'request': c.fingerprint(request), 'report': report, 'evidence': evidence,
              'collection': outcome, 'independent': saved['outcome'],
              'evidence_binding': evidence_binding(evidence)}
    commit_checkpoint(stage, 'collection', result, fd, state, cycle_entry)
    stage_usage(stage)
    return result


def destination(value):
    c.keys(value, 'repository path')
    # Reuse the accepted private destination allowlist without engineering IDs.
    from automation.supervisor_policy import PRIVATE_REPOSITORY, exact_path
    c.require(value['repository'] == PRIVATE_REPOSITORY, 'cycle_destination')
    exact_path(value['path'], destination=True)
    return value


def projection(state, cycle, backpressure=False):
    item = state['cycles'].get(cycle)
    rid = item.get('report') if item else None
    meta = state['reports'].get(rid) if rid else None
    return {'state': 'READY_FOR_REVIEW', 'status': item['status'] if item else 'backpressure',
            'changed': bool(rid), 'report_id': rid, 'backpressure': backpressure,
            'collection': item.get('collection') if item else None,
            'publication': meta['publication'] if meta else None,
            'recipient': meta['recipient'] if meta else None,
            'archived': meta['location'] == 'archive' if meta else False}


def cycle(root, runtime, owner, cycle_id, now, source_root, intended_destination,
          recipient, evidence_root=None, manifest='manifest.json'):
    """One acquisition at most per identity. Same full request is idempotent."""
    c.identifier(cycle_id); c.identifier(recipient); c.stamp(now)
    now = float(now)
    destination(intended_destination); io.relative_path(manifest)
    source_root = canonical(source_root)
    evidence_root = canonical(evidence_root) if evidence_root is not None else None
    root = canonical(root)
    # Reject lexical overlap first; store then proves actual path/identity
    # separation before writes. Safely separated file acquisition can be partial.
    for protected in (source_root, evidence_root):
        if protected is not None:
            c.require(root != protected and root not in protected.parents and protected not in root.parents,
                      'cycle_overlap')
    request = {'runtime': runtime, 'owner': owner, 'cycle': cycle_id, 'now': now,
               'source_root': str(source_root), 'evidence_root': str(evidence_root) if evidence_root else None,
               'manifest': manifest, 'destination': copy.deepcopy(intended_destination), 'recipient': recipient}
    with store(root, runtime, owner, tuple(p for p in (source_root, evidence_root) if p is not None)) as (
            root, fd, handles, state):
        old = state['cycles'].get(cycle_id)
        if old is not None:
            c.require(old['request'] == request, 'cycle_reuse')
            if old['status'] != 'collecting':
                if old['report'] is not None:
                    load_record(handles, state, old['report'])
                # Finish cleanup left after an atomic outcome commit.
                if state['collecting'] == cycle_id:
                    cleanup_stage(handles['staging'])
                    state['collecting'] = None
                    save(fd, state)
                return projection(state, cycle_id, old['status'] == 'backpressure')
        else:
            if state['collecting'] is not None:
                # Resolve an interrupted identity explicitly, never silently replace it.
                return projection(state, cycle_id, True)
            active_names, _ = inventory(handles['active'], MAX_ACTIVE + 1, MAX_ACTIVE_BYTES + MAX_RECORD)
            if len(state['cycles']) >= MAX_CYCLES or len(active_names) >= MAX_ACTIVE:
                return projection(state, cycle_id, True)
            c.require(not os.listdir(handles['staging']), 'cycle_stage_unowned')
            state['cycles'][cycle_id] = {'request': request, 'status': 'collecting', 'report': None,
                                         'checkpoints': {'independent': None, 'collection': None}}
            state['collecting'] = cycle_id
            if len(io.encode(state)) + 4096 > MAX_STATE:
                del state['cycles'][cycle_id]
                state['collecting'] = None
                return projection(state, cycle_id, True)
            save(fd, state)  # Intent is durable BEFORE touching any source.
        collected = collect(root, handles, request, fd, state, resume=old is not None)
        material = c.fingerprint(sources.material_report(collected['report']))
        changed = state['baseline'] != material
        rid = None
        status = 'quiet'
        if changed:
            payload = io.encode({'version': VERSION, 'comparison_version': 2,
                                 'identity': {'runtime': runtime, 'cycle': cycle_id},
                                 'observed_at': now, 'report': collected['report'],
                                 'evidence_binding': collected['evidence_binding']})
            rid = c.fingerprint({'runtime': runtime, 'cycle': cycle_id, 'sha256': io.digest(payload)})
            record = {'version': VERSION, 'runtime': runtime, 'cycle': cycle_id, 'id': rid,
                      'payload': payload.decode(), 'sha256': io.digest(payload),
                      'evidence': collected['evidence'], 'material': material,
                      'attempt': None, 'publication_receipt': None, 'recipient_receipt': None}
            raw = io.encode(record)
            names, total = inventory(handles['active'], MAX_ACTIVE + 1, MAX_ACTIVE_BYTES + MAX_RECORD)
            existing = rid + '.json' in names
            if len(payload) > MAX_PAYLOAD or len(raw) + RECORD_RESERVE > MAX_RECORD or (
                    not existing and (len(names) >= MAX_ACTIVE or total + len(raw)
                                      + (len(names) + 1) * RECORD_RESERVE > MAX_ACTIVE_BYTES)):
                status, rid = 'backpressure', None
            else:
                write(handles['active'], rid + '.json', raw)
                state['reports'][rid] = {'cycle': cycle_id, 'location': 'active',
                                         'publication': 'pending', 'recipient': 'pending'}
                state['baseline'] = material
                status = 'prepared'
        # Current observation is separate from the immutable original report.
        current = {'cycle': cycle_id, 'observed_at': now, 'collection': collected['collection'],
                   'report': collected['report']}
        if len(io.encode(current)) > MAX_PAYLOAD:
            c.require(status == 'backpressure', 'cycle_current_bound')
            current.update(report=None, reason='observation_too_large')
        write(fd, 'current.json', io.encode(current), replace=True)
        state['current'] = {'cycle': cycle_id, 'observed_at': now}
        state['cycles'][cycle_id].update(status=status, report=rid, collection=collected['collection'])
        save(fd, state)  # Outcome/payload/baseline durable before reclaiming staging.
        cleanup_stage(handles['staging'])
        state['collecting'] = None
        save(fd, state)
        return projection(state, cycle_id, status == 'backpressure')


def binding_for(runtime, cycle_id, rid, request, payload_sha256):
    binding = {'runtime': runtime, 'cycle': cycle_id, 'report': rid,
               'destination': request['destination'], 'recipient': request['recipient'],
               'payload_sha256': payload_sha256}
    binding['attempt'] = c.fingerprint({'version': VERSION, 'binding': binding})
    return binding


def load_record(handles, state, rid):
    sources.hex64(rid)
    meta = state['reports'][rid]
    where = 'archive' if meta['location'] == 'archive' else 'active'
    raw = read(handles[where], rid + '.json')
    value = io.decode(raw)
    c.keys(value, 'version runtime cycle id payload sha256 evidence material attempt publication_receipt recipient_receipt')
    payload = value['payload'].encode()
    decoded = io.decode(payload)
    request = state['cycles'][meta['cycle']]['request']
    c.keys(decoded, 'version comparison_version identity observed_at report evidence_binding')
    c.require(type(decoded['version']) is int and decoded['version'] == VERSION, 'cycle_schema')
    c.require(evidence_binding(value['evidence']) == decoded['evidence_binding'], 'cycle_evidence_binding')
    c.require(type(value['version']) is int and value['version'] == VERSION
              and len(payload) <= MAX_PAYLOAD and len(raw) <= MAX_RECORD
              and decoded['identity'] == {'runtime': state['runtime'], 'cycle': meta['cycle']}
              and decoded['observed_at'] == request['now']
              and decoded['comparison_version'] == 2
              and value['material'] == c.fingerprint(sources.material_report(decoded['report'])), 'cycle_record')
    if value['attempt'] is not None:
        expected = binding_for(state['runtime'], meta['cycle'], rid, request, value['sha256'])
        c.require(value['attempt'] == expected, 'cycle_attempt')
    for kind in ('publication', 'recipient'):
        retained = value[kind + '_receipt']
        if retained is not None:
            c.require(value['attempt'] is not None, 'cycle_receipt_unbound')
            receipt = io.decode(unpack(retained))
            c.keys(receipt, 'version kind owner issuer binding observed_at reference')
            c.require(receipt['version'] == RECEIPT_VERSION and receipt['kind'] == kind
                      and receipt['owner'] == state['owner']
                      and receipt['issuer'] == (state['owner'] if kind == 'publication' else request['recipient'])
                      and receipt['binding'] == value['attempt'], 'cycle_receipt_binding')
            c.stamp(receipt['observed_at']); c.identifier(receipt['reference'])
            c.require(receipt['observed_at'] >= request['now'], 'cycle_receipt_time')
    c.require(value['id'] == rid and value['runtime'] == state['runtime']
              and value['cycle'] == meta['cycle'] and io.digest(payload) == value['sha256']
              and rid == c.fingerprint({'runtime': state['runtime'], 'cycle': meta['cycle'],
                                       'sha256': value['sha256']}), 'cycle_record')
    evidence_bound(value['evidence'])
    return value


def handoff(root, runtime, owner, rid):
    """Persist uncertain BEFORE exposing a single owner publication opportunity.

    A replay returns may_attempt=False even if the handoff file was never exposed.
    Readback reconciliation is the only way out of an ambiguous attempt.
    """
    with store(root, runtime, owner) as (_, fd, handles, state):
        value = load_record(handles, state, rid)
        meta = state['reports'][rid]
        request = state['cycles'][meta['cycle']]['request']
        first = value['attempt'] is None
        if first:
            binding = binding_for(runtime, meta['cycle'], rid, request, value['sha256'])
            value['attempt'] = binding
            write(handles['active'], rid + '.json', io.encode(value), replace=True)
        if meta['location'] != 'archive':
            if meta['publication'] == 'pending':
                meta['publication'] = 'uncertain'
            save(fd, state)
            write(handles['handoff'], rid + '.json', value['payload'].encode())
        return {**projection(state, meta['cycle']), 'may_attempt': first,
                'attempt_id': value['attempt']['attempt'], 'sha256': value['sha256']}


def import_receipt(root, runtime, owner, rid, kind, owner_evidence_root, evidence_id):
    """Offline trusted-owner inbox boundary; see COORDINATOR_CYCLES.md.

    The owner authenticates origin and selects exact files BEFORE calling this.
    No success flag, hash pin, source prose or engineering terminal is accepted.
    Files: <evidence_id>.json and (publication only) <evidence_id>.payload.
    """
    c.require(kind in ('publication', 'recipient'), 'cycle_receipt_kind')
    c.identifier(evidence_id)
    inbox = canonical(owner_evidence_root)
    with store(root, runtime, owner) as (_, fd, handles, state):
        value = load_record(handles, state, rid)
        c.require(value['attempt'] is not None, 'cycle_unbound_receipt')
        with io.directory(inbox) as selected:
            private(selected, True)
            disjoint(fd, selected)
            raw = read(selected, evidence_id + '.json', 16384)
            receipt = io.decode(raw)
            c.keys(receipt, 'version kind owner issuer binding observed_at reference')
            c.require(type(receipt['version']) is int and receipt['version'] == RECEIPT_VERSION
                      and receipt['kind'] == kind and receipt['owner'] == owner
                      and receipt['binding'] == value['attempt']
                      and receipt['issuer'] == (owner if kind == 'publication'
                                                else value['attempt']['recipient']), 'cycle_receipt_binding')
            c.stamp(receipt['observed_at']); c.identifier(receipt['reference'])
            c.require(receipt['observed_at'] >= state['cycles'][value['cycle']]['request']['now'],
                      'cycle_receipt_time')
            if kind == 'publication':
                c.require(read(selected, evidence_id + '.payload', MAX_PAYLOAD) == value['payload'].encode(),
                          'cycle_readback')
        field = kind + '_receipt'
        if value[field] is not None:
            c.require(value[field] == pack(raw), 'cycle_receipt_conflict')
        else:
            c.require(state['reports'][rid]['location'] == 'active', 'cycle_archive_conflict')
            value[field] = pack(raw)
            write(handles['active'], rid + '.json', io.encode(value), replace=True)
        meta = state['reports'][rid]
        meta[kind] = 'verified' if kind == 'publication' else 'acknowledged'
        save(fd, state)
        return projection(state, value['cycle'])


def archive(root, runtime, owner, rid):
    """Copy/verify/fsync exact complete record BEFORE freeing active evidence."""
    with store(root, runtime, owner) as (_, fd, handles, state):
        value = load_record(handles, state, rid)
        c.require(value['publication_receipt'] is not None and value['recipient_receipt'] is not None,
                  'cycle_archive_incomplete')
        raw = io.encode(value)
        names, total = inventory(handles['archive'], MAX_ARCHIVE + 1, MAX_ARCHIVE_BYTES + MAX_RECORD)
        name = rid + '.json'
        if name not in names and (len(names) >= MAX_ARCHIVE or total + len(raw) > MAX_ARCHIVE_BYTES):
            return projection(state, value['cycle'], True)
        write(handles['archive'], name, raw)
        c.require(read(handles['archive'], name) == raw, 'cycle_archive_verification')
        # Verification includes exact original source bytes carried in the record.
        archived = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=handles['archive'])
        try:
            private(archived)
            os.fsync(archived)
        finally:
            os.close(archived)
        os.fsync(handles['archive'])
        state['reports'][rid].update(location='archive', publication='verified', recipient='acknowledged')
        save(fd, state)
        for location, expected in (('active', raw), ('handoff', value['payload'].encode())):
            try:
                retained = read(handles[location], name)
            except FileNotFoundError:
                continue
            c.require(retained == expected, 'cycle_archive_conflict')
            os.unlink(name, dir_fd=handles[location])
            os.fsync(handles[location])
        return projection(state, value['cycle'])


def main(argv=None):
    parser = PublicParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for command in ('cycle', 'handoff', 'receipt', 'archive'):
        item = sub.add_parser(command)
        for field in ('root', 'runtime', 'owner'):
            item.add_argument('--' + field, required=True)
        if command == 'cycle':
            item.add_argument('--cycle-id', required=True)
            item.add_argument('--now', required=True, type=float)
            item.add_argument('--source-root', required=True)
            item.add_argument('--destination-repository', required=True)
            item.add_argument('--destination-path', required=True)
            item.add_argument('--recipient', required=True)
            item.add_argument('--evidence-root')
            item.add_argument('--manifest', default='manifest.json')
        else:
            item.add_argument('--id', required=True)
        if command == 'receipt':
            item.add_argument('--kind', required=True, choices=('publication', 'recipient'))
            item.add_argument('--owner-evidence-root', required=True)
            item.add_argument('--evidence-id', required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'cycle':
            result = cycle(args.root, args.runtime, args.owner, args.cycle_id, args.now,
                           args.source_root, {'repository': args.destination_repository,
                                              'path': args.destination_path}, args.recipient,
                           args.evidence_root, args.manifest)
        elif args.command == 'handoff':
            result = handoff(args.root, args.runtime, args.owner, args.id)
        elif args.command == 'archive':
            result = archive(args.root, args.runtime, args.owner, args.id)
        else:
            result = import_receipt(args.root, args.runtime, args.owner, args.id, args.kind,
                                    args.owner_evidence_root, args.evidence_id)
        print(io.encode(result).decode())
        return 0
    except sources.FAILURES:
        print('{"state":"NEEDS_USER","reason":"invalid_or_unavailable_input"}')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
