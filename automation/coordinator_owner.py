"""Finite offline owner commissioning. Transport and authentication stay external.

No request file is authority: every call receives the full owner-selected request.
Only reserve's first successful return grants one external acquisition opportunity.
An interrupted return burns that opportunity. No network or executor is provided.
"""
import contextlib
import copy
import fcntl
import os
from pathlib import Path
import re

from automation import coordinator as c
from automation import coordinator_cycles as cycles
from automation import coordinator_exports as exports
from automation import coordinator_io as io
from automation import coordinator_sources as sources
from automation.coordinator_integration import PublicParser

VERSION = 1
MAX_INTENTS = 20
MAX_INTENT = 16384
MAX_LEDGER = 512 * 1024
MAX_INDEPENDENT = 3 * c.MAX_BYTES
ROOT_FIELDS = ('intake_root', 'cycle_root', 'evidence_root', 'receipt_root')
FIXED_PATHS = tuple(exports.EXPORTS.values())


class OwnerFailure(ValueError):
    def __init__(self, reason):
        self.reason = reason
        super().__init__(reason)


def require(ok, reason):
    if not ok:
        raise OwnerFailure(reason)


def request(base, runtime, owner, cycle_id, now, intake_root, cycle_root,
            evidence_root, receipt_root, parent_output, selector, source_path,
            destination, recipient, expected='absent', evidence_manifest_sha256=None):
    """Explicit caller authority; never load this configuration from staged JSON."""
    for identifier in (runtime, owner, cycle_id, selector, recipient):
        c.identifier(identifier)
    require(owner != recipient, 'owner_distinct_recipient')
    c.stamp(now)
    cycles.destination(destination)
    require(expected == 'absent', 'owner_create_only')
    if evidence_manifest_sha256 is not None:
        sources.hex64(evidence_manifest_sha256)
    # source_path is an exact externally approved selector spelling, never opened
    # here. A later transport must independently prove its canonical remote path.
    remote = cycles.canonical(source_path)
    value = dict(version=VERSION, base=str(base), runtime=runtime, owner=owner,
                 cycle=cycle_id, now=float(now), intake_root=str(intake_root),
                 cycle_root=str(cycle_root), evidence_root=str(evidence_root),
                 receipt_root=str(receipt_root), parent_output=str(parent_output),
                 selector=selector, source_path=str(source_path), paths=list(FIXED_PATHS),
                 destination=copy.deepcopy(destination), recipient=recipient,
                 expected=expected, evidence_manifest_sha256=evidence_manifest_sha256)
    base = cycles.canonical(value['base'])
    # Restrict new sibling names to ASCII lowercase, so missing prospective
    # directories cannot be case/Unicode normalization aliases. Existing paths
    # still undergo descriptor/ancestor identity checks on every entrypoint.
    require(re.fullmatch(r'[a-z][a-z0-9-]{0,63}', base.name), 'owner_path')
    names = []
    require(base != remote and base not in remote.parents and remote not in base.parents,
            'owner_overlap')
    for field in ROOT_FIELDS:
        p = cycles.canonical(value[field])
        require(p.parent == base and re.fullmatch(r'[a-z][a-z0-9-]{0,63}', p.name), 'owner_path')
        names.append(p.name)
    require(len(set(names)) == len(names) and not set(names) & {'identity.json', 'lock'},
            'owner_overlap')
    output = cycles.canonical(value['parent_output'])
    require(re.fullmatch(r'[a-z][a-z0-9-]{0,63}\.json', output.name)
            and output.parent != base.parent and output.parent != base
            and base not in output.parents and output.parent not in base.parents,
            'owner_output_path')
    require(len(io.encode(value)) <= MAX_INTENT // 2, 'owner_request_bound')
    return value


def validate_request(value):
    # Reconstruct through the public validator; extra keys/changed versions fail.
    expected = request(value['base'], value['runtime'], value['owner'], value['cycle'],
                       value['now'], *(value[k] for k in ROOT_FIELDS), value['parent_output'],
                       value['selector'], value['source_path'], value['destination'],
                       value['recipient'], value['expected'], value['evidence_manifest_sha256'])
    require(value == expected, 'owner_request')


def identity(fd):
    cycles.private(fd, True)
    st = os.fstat(fd)
    return [st.st_dev, st.st_ino]


@contextlib.contextmanager
def exact_directory(path):
    """Also refuse changed-case/normalization aliases on permissive filesystems."""
    path = cycles.canonical(path)
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:]:
            require(part in os.listdir(fd), 'owner_path_spelling')
            before = os.stat(part, dir_fd=fd, follow_symlinks=False)
            sub = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = sub
            require(os.path.samestat(before, os.fstat(fd)), 'owner_root_changed')
        yield fd
    finally:
        os.close(fd)


def marker(req, parent):
    return dict(version=VERSION, component='coordinator_owner', runtime=req['runtime'],
                owner=req['owner'], base=req['base'], cycle_root=req['cycle_root'],
                parent=identity(parent))


def intent_name(req):
    return 'intent-' + c.fingerprint(req['cycle']) + '.json'


def exists(fd, name):
    try:
        os.stat(name, dir_fd=fd, follow_symlinks=False)
        return True
    except FileNotFoundError:
        return False


def bounded_names(fd, limit, reason):
    names = []
    with os.scandir(fd) as entries:
        for entry in entries:
            require(len(names) < limit, reason)
            names.append(entry.name)
    return names


@contextlib.contextmanager
def owner_store(req, create=False):
    """No-follow guards precede every private write. No adoption or cleanup."""
    validate_request(req)
    base = cycles.canonical(req['base'])
    checkout = Path(__file__).resolve().parent.parent
    with contextlib.ExitStack() as stack:
        parent = stack.enter_context(exact_directory(base.parent))
        identity(parent)
        checkout_fd = stack.enter_context(io.directory(checkout))
        exports._outside_source(parent, checkout_fd)
        output = Path(req['parent_output'])
        output_parent = stack.enter_context(exact_directory(output.parent))
        identity(output_parent)
        cycles.disjoint(output_parent, checkout_fd)
        exports._outside_source(parent, output_parent)
        was_present = exists(parent, base.name)
        if was_present:
            fd = stack.enter_context(exact_directory(base))
            identity(fd)
            cycles.disjoint(fd, checkout_fd)
            cycles.disjoint(fd, output_parent)
            require(io.decode(cycles.read(fd, 'identity.json', MAX_INTENT)) == marker(req, parent),
                    'owner_identity')
        else:
            require(create, 'owner_missing')
            require(not exists(output_parent, output.name), 'owner_output_exists')
            os.mkdir(base.name, 0o700, dir_fd=parent)  # exclusive initializer
            os.fsync(parent)
            fd = stack.enter_context(io.directory(base))
            identity(fd)
            exports._write_new(fd, 'identity.json', io.encode(marker(req, parent)))
            lock = os.open('lock', os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                           0o600, dir_fd=fd)
            try:
                os.fsync(fd)
            finally:
                os.close(lock)
        lock = os.open('lock', os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        stack.callback(os.close, lock)
        cycles.private(lock)
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise OwnerFailure('owner_busy') from None
        # Unknown/debris entries are never deleted or adopted. Bound the ledger
        # before reading bodies; validate all immutable requests and root claims.
        names = bounded_names(fd, 2 + MAX_INTENTS * 8 + 1, 'owner_backpressure')
        ledger, total, claimed = {}, 0, {'identity.json', 'lock'}
        for name in names:
            if not re.fullmatch(r'intent-[a-f0-9]{64}\.json', name):
                continue
            raw = cycles.read(fd, name, MAX_INTENT)
            total += len(raw)
            entry = io.decode(raw)
            c.keys(entry, 'request sha256 roots')
            validate_request(entry['request'])
            old = entry['request']
            require(entry['sha256'] == c.fingerprint(dict(request=old, roots=entry['roots']))
                    and name == intent_name(old)
                    and marker(old, parent) == marker(req, parent), 'owner_intent_binding')
            require(set(entry['roots']) == set(ROOT_FIELDS) | {'output_parent'}, 'owner_intent_binding')
            ledger[name] = entry
            claimed.add(name)
            for field in ROOT_FIELDS:
                claimed.add(Path(old[field]).name)
            claimed.add('seal-' + c.fingerprint(old) + '.json')
        require(len(ledger) <= MAX_INTENTS and total <= MAX_LEDGER, 'owner_backpressure')
        require(set(names) <= claimed, 'owner_unanchored')
        for entry in ledger.values():
            for field in ROOT_FIELDS:
                with exact_directory(entry['request'][field]) as selected:
                    require(identity(selected) == entry['roots'][field], 'owner_root_changed')
        if ledger:
            with io.directory(req['cycle_root']) as selected:
                require(io.decode(cycles.read(selected, 'identity.json')) == {
                    **cycles.LAYOUT, 'runtime': req['runtime'], 'owner': req['owner']}, 'owner_cycle_identity')
                cycles.validate_state(io.decode(cycles.read(selected, 'state.json', cycles.MAX_STATE)))
        # Prove existing roots by descriptor identity, including against checkout.
        # Only the accepted cycle component may initialize/use cycle_root.
        opened = []
        for field in ROOT_FIELDS:
            p = Path(req[field])
            if exists(fd, p.name):
                sub = stack.enter_context(exact_directory(p))
                identity(sub)
                cycles.disjoint(sub, checkout_fd)
                for other in opened:
                    cycles.disjoint(sub, other)
                opened.append(sub)
        yield fd, ledger


def bound_intent(req, fd, ledger):
    entry = ledger.get(intent_name(req))
    require(entry is not None and entry['request'] == req, 'owner_intent_conflict')
    for field in ROOT_FIELDS:
        pinned = entry['roots'][field]
        with io.directory(req[field]) as root:
            require(identity(root) == pinned, 'owner_root_changed')
    with exact_directory(Path(req['parent_output']).parent) as selected:
        require(identity(selected) == entry['roots']['output_parent'], 'owner_root_changed')
    return entry


def reserve(req):
    """Durable one-shot intent BEFORE any externally authorized transport.

    Return grant=True only to the initializer. Never retry transport on replay,
    including lost stdout, interrupted initialization, or uncertain source reads.
    """
    with owner_store(req, create=True) as (fd, ledger):
        if intent_name(req) in ledger:
            entry = bound_intent(req, fd, ledger)
            return dict(state='READY_FOR_REVIEW', status='reserved', acquisition_grant=False,
                        intent_sha256=entry['sha256'])
        require(len(ledger) < MAX_INTENTS, 'owner_backpressure')
        # Reject reuse of any root/output from a previous acquisition. cycle_root
        # alone is shared to retain accepted material comparison across cycles.
        used = {old['request'][field] for old in ledger.values()
                for field in ROOT_FIELDS + ('parent_output',) if field != 'cycle_root'}
        for field in ROOT_FIELDS:
            if field == 'cycle_root':
                continue
            require(req[field] not in used and not exists(fd, Path(req[field]).name),
                    'owner_root_exists')
        with exact_directory(Path(req['parent_output']).parent) as output_parent:
            require(req['parent_output'] not in used
                    and not exists(output_parent, Path(req['parent_output']).name), 'owner_output_exists')
            output_identity = identity(output_parent)
        require(sum(len(io.encode(v)) for v in ledger.values()) + MAX_INTENT <= MAX_LEDGER,
                'owner_backpressure')
        if ledger:
            with io.directory(req['cycle_root']) as root:
                state = io.decode(cycles.read(root, 'state.json', cycles.MAX_STATE))
                active = cycles.child(root, 'active')
                try:
                    names, total = cycles.inventory(active, cycles.MAX_ACTIVE, cycles.MAX_ACTIVE_BYTES)
                finally:
                    os.close(active)
                require(state['collecting'] is None and len(state['cycles']) < cycles.MAX_CYCLES
                        and len(names) < cycles.MAX_ACTIVE
                        and total + cycles.MAX_RECORD + cycles.RECORD_RESERVE <= cycles.MAX_ACTIVE_BYTES
                        and len(io.encode(state)) + MAX_INTENT <= cycles.MAX_STATE, 'owner_backpressure')
        roots = {'output_parent': output_identity}
        # Directory creation itself grants no transport. A crash before the
        # immutable intent leaves unanchored directories and fails closed.
        for field in ROOT_FIELDS:
            if field == 'cycle_root':
                continue
            os.mkdir(Path(req[field]).name, 0o700, dir_fd=fd)
            with io.directory(req[field]) as sub:
                roots[field] = identity(sub)
        os.fsync(fd)
        # Own a fresh accepted format-2 store, never adopt a preexisting root.
        with cycles.store(req['cycle_root'], req['runtime'], req['owner'],
                          tuple(Path(req[k]) for k in ROOT_FIELDS if k != 'cycle_root')) as (
                              _, cycle_fd, _, state):
            cycles.save(cycle_fd, state)
            roots['cycle_root'] = identity(cycle_fd)
        with io.directory(req['intake_root']) as intake:
            os.mkdir('incoming', 0o700, dir_fd=intake)
            os.fsync(intake)
        entry = dict(request=copy.deepcopy(req), roots=roots)
        entry['sha256'] = c.fingerprint(entry)
        exports._write_new(fd, intent_name(req), io.encode(entry))
        return dict(state='READY_FOR_REVIEW', status='reserved', acquisition_grant=True,
                    intent_sha256=entry['sha256'])


def fixed_tree(root, permitted, limit, total_limit):
    """Exact regular private files, bounded descriptor reads and actual hashes.

    Does not parse/rewrite JSON or alter embedded generation/observation clocks.
    Missing fixed files are retained as missing, never synthesized.
    """
    result, total = {}, 0
    with io.directory(root) as fd:
        identity(fd)
        top = {p.split('/')[0] for p in permitted}
        require(set(bounded_names(fd, len(top), 'owner_intake_entries')) <= top, 'owner_intake_entries')
        for name in sorted(top):
            children = [p.split('/', 1)[1] for p in permitted if p.startswith(name + '/')]
            if children and exists(fd, name):
                sub = cycles.child(fd, name)
                try:
                    require(set(bounded_names(sub, len(children), 'owner_intake_entries')) <= set(children),
                            'owner_intake_entries')
                finally:
                    os.close(sub)
        for path in permitted:
            try:
                # Check private mode through the same pinned parent directory as
                # the stable read (the accepted read also checks metadata/links).
                parts = path.split('/')
                with contextlib.ExitStack() as stack:
                    parent = fd
                    if len(parts) == 2:
                        parent = cycles.child(fd, parts[0])
                        stack.callback(os.close, parent)
                    raw = private_read(parent, parts[-1], limit)
            except FileNotFoundError:
                result[path] = None
                continue
            total += len(raw)
            require(total <= total_limit, 'owner_backpressure')
            result[path] = dict(size=len(raw), sha256=io.digest(raw))
    return result


def private_read(parent, name, limit):
    """Check private ownership and stable metadata on the actual read descriptor."""
    target = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    try:
        cycles.private(target)
        before = os.fstat(target)
        require(before.st_size <= limit, 'owner_backpressure')
        chunks, left = [], limit + 1
        while left:
            raw = os.read(target, min(left, 65536))
            if not raw:
                break
            chunks.append(raw)
            left -= len(raw)
        after = os.fstat(target)
        fields = ('st_dev', 'st_ino', 'st_size', 'st_mode', 'st_uid', 'st_mtime_ns', 'st_ctime_ns', 'st_nlink')
        require(all(getattr(before, k) == getattr(after, k) for k in fields)
                and os.path.samestat(after, os.stat(name, dir_fd=parent, follow_symlinks=False)),
                'owner_input_changed')
        raw = b''.join(chunks)
        require(len(raw) <= limit and len(raw) == after.st_size, 'owner_input_changed')
        return raw
    finally:
        os.close(target)


def capture(req):
    movie = fixed_tree(req['intake_root'], FIXED_PATHS, exports.LIMIT, 2 * exports.LIMIT)
    independent = fixed_tree(req['evidence_root'],
                             ('manifest.json', 'engineering.json', 'parent_status.json'),
                             c.MAX_BYTES, MAX_INDEPENDENT)
    pin = req['evidence_manifest_sha256']
    require((pin is None and all(v is None for v in independent.values()))
            or (pin is not None and independent['manifest.json'] is not None
                and independent['manifest.json']['sha256'] == pin), 'owner_manifest_selection')
    if pin is not None:
        with io.directory(req['evidence_root']) as fd:
            manifest = sources.manifest(io.decode(cycles.read(fd, 'manifest.json', c.MAX_BYTES)), req['now'])
        for entry in manifest['sources']:
            if entry['id'] in ('engineering', 'parent_status'):
                require(entry['path'] in (None, entry['id'] + '.json'), 'owner_manifest_paths')
            else:
                require(entry['path'] is None, 'owner_manifest_paths')
    return dict(request_sha256=c.fingerprint(req), movie=movie, independent=independent)


def seal(req):
    """Owner declares external acquisition complete, even if exports are missing.

    No transport retry, callback, freshness substitution or implicit receipt import.
    The first seal anchors original bytes. Interrupted/unanchored writes reject.
    """
    with owner_store(req) as (fd, ledger):
        bound_intent(req, fd, ledger)
        value = capture(req)
        name = 'seal-' + c.fingerprint(req) + '.json'
        raw = io.encode(value)
        if exists(fd, name):
            require(cycles.read(fd, name, MAX_INTENT) == raw, 'owner_intake_changed')
        else:
            exports._write_new(fd, name, raw)
        return dict(state='READY_FOR_REVIEW', status='sealed')


def verified_seal(req, fd):
    raw = cycles.read(fd, 'seal-' + c.fingerprint(req) + '.json', MAX_INTENT)
    require(io.decode(raw) == capture(req), 'owner_intake_changed')


def prepare(req):
    with owner_store(req) as (fd, ledger):
        bound_intent(req, fd, ledger)
        verified_seal(req, fd)
        # The supplied observation clock and paths remain exactly the reserved
        # request, even when transport/staging completed much later.
        result = cycles.cycle(req['cycle_root'], req['runtime'], req['owner'], req['cycle'],
                              req['now'], req['intake_root'], req['destination'], req['recipient'],
                              req['evidence_root'] if req['evidence_manifest_sha256'] else None)
        verified_seal(req, fd)
        return result


def inspect_locked(req):
    """Read-only accepted ledger/record validation; does not call store()."""
    with io.directory(req['cycle_root']) as fd, contextlib.ExitStack() as stack:
        require(io.decode(cycles.read(fd, 'identity.json')) == {
            **cycles.LAYOUT, 'runtime': req['runtime'], 'owner': req['owner']}, 'owner_cycle_identity')
        state = io.decode(cycles.read(fd, 'state.json', cycles.MAX_STATE))
        cycles.validate_state(state)
        entry = state['cycles'].get(req['cycle'])
        if entry is None:
            return dict(state='READY_FOR_REVIEW', status='reserved', report_id=None)
        expected = dict(runtime=req['runtime'], owner=req['owner'], cycle=req['cycle'], now=req['now'],
                        source_root=req['intake_root'], destination=req['destination'],
                        recipient=req['recipient'], manifest='manifest.json',
                        evidence_root=req['evidence_root'] if req['evidence_manifest_sha256'] else None)
        require(entry['request'] == expected, 'owner_cycle_request')
        handles = {}
        for name in ('active', 'archive'):
            handles[name] = cycles.child(fd, name)
            stack.callback(os.close, handles[name])
        if entry['report']:
            cycles.load_record(handles, state, entry['report'])
        return cycles.projection(state, req['cycle'])


def inspect(req):
    with owner_store(req) as (fd, ledger):
        bound_intent(req, fd, ledger)
        return inspect_locked(req)


def handoff(req):
    with owner_store(req) as (fd, ledger):
        bound_intent(req, fd, ledger)
        verified_seal(req, fd)
        status = inspect_locked(req)
        require(status['status'] == 'prepared', 'owner_not_prepared')
        output_path = Path(req['parent_output'])
        output = output_path.name
        # Never rewrite even identical preexisting output, nor grant a resend.
        with exact_directory(output_path.parent) as output_parent:
            require(not exists(output_parent, output), 'owner_output_exists')
        rid = status['report_id']
        result = cycles.handoff(req['cycle_root'], req['runtime'], req['owner'], rid)
        require(result['may_attempt'], 'owner_publication_uncertain')
        # Accepted handoff has committed uncertain BEFORE payload exposure here.
        with io.directory(Path(req['cycle_root']) / 'handoff') as selected:
            raw = cycles.read(selected, rid + '.json', cycles.MAX_PAYLOAD)
        require(io.digest(raw) == result['sha256'], 'owner_handoff_binding')
        with exact_directory(output_path.parent) as output_parent:
            require(identity(output_parent) == ledger[intent_name(req)]['roots']['output_parent'],
                    'owner_root_changed')
            exports._write_new(output_parent, output, raw)
            require(cycles.read(output_parent, output, cycles.MAX_PAYLOAD) == raw, 'owner_handoff_binding')
        return result


def receipt(req, kind, evidence_id):
    """Explicit external owner's authenticated selection, NOT authentication.

    Before invoking, caller must authenticate actual publication readback OR
    distinct genuine system ingestion. Private files/JSON never establish origin.
    Selection is never inferred from intake, prepare, status, or another receipt.
    """
    require(kind in ('publication', 'recipient') and evidence_id == kind, 'owner_receipt_selection')
    with owner_store(req) as (fd, ledger):
        bound_intent(req, fd, ledger)
        files = fixed_tree(req['receipt_root'], ('publication.json', 'publication.payload', 'recipient.json'),
                           cycles.MAX_PAYLOAD, cycles.MAX_PAYLOAD + 32768)
        require(all(value is None or value['size'] <= 16384 for name, value in files.items()
                    if name.endswith('.json')), 'owner_backpressure')
        with io.directory(req['receipt_root']) as inbox:
            cycles.read(inbox, evidence_id + '.json', 16384)
        rid = inspect_locked(req)['report_id']
        require(rid is not None, 'owner_not_prepared')
        return cycles.import_receipt(req['cycle_root'], req['runtime'], req['owner'], rid,
                                     kind, req['receipt_root'], evidence_id)


def archive(req):
    with owner_store(req) as (fd, ledger):
        bound_intent(req, fd, ledger)
        rid = inspect_locked(req)['report_id']
        require(rid is not None, 'owner_not_prepared')
        return cycles.archive(req['cycle_root'], req['runtime'], req['owner'], rid)


def main(argv=None):
    parser = PublicParser(description=__doc__)
    parser.add_argument('command', choices=('reserve', 'seal', 'prepare', 'handoff', 'inspect', 'receipt', 'archive'))
    for field in ('base', 'runtime', 'owner', 'cycle-id', 'intake-root', 'cycle-root', 'evidence-root',
                  'receipt-root', 'parent-output', 'selector', 'source-path', 'destination-repository',
                  'destination-path', 'recipient', 'expected'):
        parser.add_argument('--' + field, required=True)
    parser.add_argument('--now', type=float, required=True)
    parser.add_argument('--evidence-manifest-sha256')
    parser.add_argument('--kind', choices=('publication', 'recipient'))
    parser.add_argument('--evidence-id')
    args = parser.parse_args(argv)
    try:
        req = request(args.base, args.runtime, args.owner, args.cycle_id, args.now,
                      args.intake_root, args.cycle_root, args.evidence_root, args.receipt_root,
                      args.parent_output, args.selector, args.source_path,
                      dict(repository=args.destination_repository, path=args.destination_path),
                      args.recipient, args.expected, args.evidence_manifest_sha256)
        if args.command == 'receipt':
            result = receipt(req, args.kind, args.evidence_id)
        else:
            require(args.kind is None and args.evidence_id is None, 'owner_receipt_selection')
            result = globals()[args.command](req)
        print(io.encode(result).decode())
        return 0
    except OwnerFailure as exc:
        print(io.encode(dict(state='NEEDS_USER', reason=exc.reason)).decode())
        return 1
    except sources.FAILURES + (KeyError, TypeError):
        print('{"state":"NEEDS_USER","reason":"invalid_or_unavailable_input"}')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
