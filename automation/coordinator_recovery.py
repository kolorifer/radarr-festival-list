"""Fixed issue122 sealed collecting-checkpoint recovery. No acquisition interface.

The ordinary parent authenticates both owner comments and immutable selections.
A new selection explicitly attests reviewed code evolution; original pins stay
immutable. This module has no CLI, executor, credentials or reservation route.
"""
import base64
import os
from pathlib import Path
import re
import stat

from automation import coordinator_runtime as r
from automation import coordinator_owner as owner
from automation import coordinator_cycles as cycles
from automation import coordinator_io as io
from automation import coordinator_storage as storage

COMMANDS = 'finite-recovery-commands.json'


def consumed(runner, origin):
    try:
        with owner.exact_directory(runner.state_dir) as fd:
            owner.identity(fd)
            value = io.decode(owner.private_read(fd, COMMANDS, r.LIMIT))
    except FileNotFoundError:
        return False
    r.keys(value, 'version commands')
    r.require(type(value['version']) is int and value['version'] == 1
              and isinstance(value['commands'], list) and len(value['commands']) <= 32)
    return origin in value['commands']


def consume(runner, origin):
    with owner.exact_directory(runner.state_dir) as fd:
        owner.identity(fd)
        try:
            value = io.decode(owner.private_read(fd, COMMANDS, r.LIMIT))
        except FileNotFoundError:
            value = dict(version=1, commands=[])
        r.keys(value, 'version commands')
        r.require(value['version'] == 1 and len(value['commands']) < 32 and origin not in value['commands'])
        value['commands'].append(origin)
        cycles.write(fd, COMMANDS, io.encode(value), replace=True)


MAX_RETAINED = 32 * 1024 * 1024
AUTHORIZATION = 'recovery-authorization.json'
RETAINED = 'recovery-retained.json'
SELECTION = 'recovery-selection.json'


def scheduling_binding(state, selected, author):
    binding = state['recovery']
    r.keys(binding, 'pin origin selection_sha256 authorization_sha256')
    r.pin(binding['pin'])
    r.require(binding['selection_sha256'] == binding['pin']['sha256']
              and r.hex_value(binding['authorization_sha256'], 64))
    recovery = selected.get('recovery')
    r.require(recovery is not None and binding['pin'] == recovery[1]['recovery']
              and binding['origin'] == r.origin(recovery[0], author)
              and selected['command'].get('recovery') == binding['pin'])
    if 'recovery_last_comment' in state:
        last = state['recovery_last_comment']
        r.keys(last, 'id body created_at updated_at author')
        r.require(last['author'] == author and last['id'] >= binding['origin']['id']
                  and last['created_at'] == last['updated_at'])
        command = io.decode(last['body'][len(r.PREFIX):])
        r.require(last['body'] == r.PREFIX + io.encode(command).decode()
                  and command in [dict(action=a, phase=r.PHASE, selection=state['selection'],
                                       recovery=binding['pin']) for a in ('recover', 'continue')])
        r.timestamp(last['created_at'])


def locations(runtime):
    """Only fixed selected local roles; selection cannot supply file paths."""
    req = runtime.req
    seal = 'seal-' + r.c.fingerprint(req) + '.json'
    return {
        'phase': (runtime.evidence_root, {'selection.json', 'authorization.json', 'transport.json'}),
        'adapter': (Path(req['base']), {'identity.json', 'lock', owner.intent_name(req), seal}),
        'intake': (Path(req['intake_root']), {'review-report.json'}),
        'incoming': (Path(req['intake_root']) / 'incoming', {'snapshot.json'}),
        'independent': (Path(req['evidence_root']), {'manifest.json', 'engineering.json', 'parent_status.json'}),
        'receipts': (Path(req['receipt_root']), set()),
        'cycles': (Path(req['cycle_root']), {'identity.json', 'state.json', 'lock'}),
        'active': (Path(req['cycle_root']) / 'active', set()),
        'archive': (Path(req['cycle_root']) / 'archive', set()),
        'handoff': (Path(req['cycle_root']) / 'handoff', set()),
        'stage': (Path(req['cycle_root']) / 'staging', {'independent.json'}),
        'movie': (Path(req['cycle_root']) / 'staging/movie',
                  {'investigations.json', 'research_report.json', 'manifest.json', 'observations.json', 'diagnostics.json'}),
        'combined': (Path(req['cycle_root']) / 'staging/combined',
                     {s + '.json' for s in r.sources.SOURCES} | {'manifest.json'}),
    }


def read_file(path, limit):
    with owner.exact_directory(path.parent) as parent:
        owner.identity(parent)
        r.require(storage.exact_entry(parent, path.name))
        before = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        try:
            cycles.private(fd)
            r.require(stat.S_IMODE(before.st_mode) == 0o600 and os.path.samestat(before, os.fstat(fd)))
            acl = storage.acl_identity(fd)
            raw = owner.private_read(parent, path.name, limit)
            after = os.fstat(fd)
            meta = lambda st: [getattr(st, f) for f in (
                'st_dev', 'st_ino', 'st_uid', 'st_gid', 'st_mode', 'st_size', 'st_mtime_ns', 'st_ctime_ns', 'st_nlink')]
            r.require(meta(before) == meta(after) and storage.acl_identity(fd) == acl
                      and os.path.samestat(after, os.stat(path.name, dir_fd=parent, follow_symlinks=False)))
            return dict(metadata=meta(after), acl=acl, sha256=io.digest(raw)), raw
        finally:
            os.close(fd)


def capture(runtime):
    """Read-only, bounded fixed tree; no core store/cleanup or source-path read."""
    dirs, files, contents, total = {}, {}, {}, 0
    for role, (path, allowed) in locations(runtime).items():
        if role in ('movie', 'combined'):
            with owner.exact_directory(path.parent) as parent:
                owner.identity(parent)
                if not owner.exists(parent, path.name):
                    r.require(path.name not in os.listdir(parent))
                    continue
        with owner.exact_directory(path) as fd:
            ident = owner.identity(fd)
            r.require(stat.S_IMODE(os.fstat(fd).st_mode) == 0o700)
            dirs[role] = dict(identity=ident, acl=storage.acl_identity(fd))
            names = owner.bounded_names(fd, 24, 'recovery_entries')
            children = {'adapter': {Path(runtime.req[k]).name for k in owner.ROOT_FIELDS},
                        'intake': {'incoming'}, 'cycles': {'active', 'archive', 'handoff', 'staging'},
                        'stage': {'movie', 'combined'}}.get(role, set())
            for name in names:
                if name in children:
                    continue
                # Native reader's known exclusive temp is retained too;
                # hardlinked/unknown debris fails closed before core cleanup.
                r.require(name in allowed or (role == 'movie' and re.fullmatch(r'\.export-[a-f0-9]{32}', name)))
                record, raw = read_file(path / name, cycles.MAX_RECORD)
                key = role + '/' + name
                files[key], contents[key] = record, base64.b64encode(raw).decode('ascii')
                total += len(raw)
                r.require(total <= MAX_RETAINED and len(files) <= 48)
    record, raw = read_file(runtime.runner.state_dir / r.JOURNAL, r.LIMIT)
    files['parent/journal'], contents['parent/journal'] = record, base64.b64encode(raw).decode('ascii')
    return dict(directories=dirs, files=files), contents


class Selection:
    def __init__(self, runtime):
        self.runtime = runtime
        comment, command = runtime.selected['recovery']
        self.origin = r.authenticate(runtime.runner, comment, runtime.author)
        self.pin = command['recovery']
        self.raw = r.fetch(runtime.runner, self.pin)
        self.value = io.decode(self.raw)
        v = self.value
        r.keys(v, 'version phase operation original_selection original_start request_sha256 code checkpoint')
        r.keys(v['code'], 'reviewed_revision deployed_revision code_sha256')
        r.keys(v['checkpoint'], 'directories files')
        r.require(type(v['version']) is int and v['version'] == 1 and v['phase'] == r.PHASE
                  and v['operation'] == runtime.value['operation'] == 'partial-1'
                  and v['original_selection'] == runtime.pin
                  and io.encode(v['original_start']) == io.encode(runtime.start_origin)
                  and v['request_sha256'] == r.c.fingerprint(runtime.value['request'])
                  and comment['id'] > runtime.selected['start']['id']
                  and r.timestamp(comment['created_at']) >= r.timestamp(runtime.selected['start']['created_at'])
                  and runtime.value['independent'] is not None
                  and self.raw == io.encode(v))

    def initial_boundary(self):
        rt, v = self.runtime, self.value
        state, req = rt.state, rt.req
        r.require(state['status'] == 'preparation_uncertain' and state['claim_confirmed'] is True
                  and state['attempt'] is state['publication'] is state['acknowledgement'] is None
                  and set(state) == set(('version selection selection_sha256 start request status claim_confirmed '
                                         'evidence_identity attempt publication acknowledgement reservation').split()))
        claim = rt.runner.api(f'repos/{r.REPOSITORY}/git/ref/heads/automation/reporting-operation-issue-122-phase-1')
        r.require(claim.get('ref') == r.CLAIM and claim.get('object', {}).get('sha') == rt.value['reviewed_revision'])
        checkpoint, contents = capture(rt)
        r.require(io.encode(checkpoint) == io.encode(v['checkpoint']))
        phase = rt.evidence_root
        with owner.exact_directory(phase) as fd:
            r.require(owner.private_read(fd, 'selection.json', r.LIMIT) == rt.raw_selection)
            auth = io.decode(owner.private_read(fd, 'authorization.json', r.LIMIT))
            r.keys(auth, 'pin start claim storage')
            r.require(auth['pin'] == rt.pin and auth['start'] == rt.start_origin and auth['claim'] == claim
                      and auth['storage'] == [g.baseline for g in rt.grants])
            tr = io.decode(owner.private_read(fd, 'transport.json', cycles.MAX_RECORD))
            r.keys(tr, 'complete returncode stdout stderr acquired_at')
            r.require(tr['complete'] is True and type(tr['returncode']) is int and tr['returncode'] == 0)
            r.c.stamp(tr['acquired_at'])
            r.require(tr['acquired_at'] >= req['now'])
            stdout = base64.b64decode(tr['stdout'], validate=True)
            r.require(len(stdout) <= r.transport.OUTPUT_LIMIT)
            envelope = io.decode(stdout)
            r.keys(envelope, 'version files')
            r.require(type(envelope['version']) is int and envelope['version'] == 1
                      and set(envelope['files']) == set(owner.FIXED_PATHS))
            r.require(len(base64.b64decode(tr['stderr'], validate=True)) <= r.transport.ERROR_LIMIT)
        with owner.owner_store(req) as (fd, ledger):
            intent = owner.bound_intent(req, fd, ledger)
            r.require(io.encode(state['reservation']) == io.encode(dict(state='READY_FOR_REVIEW', status='reserved',
                      acquisition_grant=True, intent_sha256=intent['sha256'])))
            owner.verified_seal(req, fd)
            status = owner.inspect_locked(req)
            r.require(status['status'] == 'collecting' and status['report_id'] is None)
        with owner.exact_directory(req['cycle_root']) as fd:
            cycle_state = io.decode(owner.private_read(fd, 'state.json', cycles.MAX_STATE))
        entry = cycle_state['cycles'][req['cycle']]
        r.require(cycle_state['collecting'] == req['cycle'] and cycle_state['reports'] == {}
                  and cycle_state['baseline'] is cycle_state['current'] is None
                  and set(cycle_state['cycles']) == {req['cycle']}
                  and entry['checkpoints']['collection'] is None
                  and r.hex_value(entry['checkpoints']['independent'], 64))
        saved = base64.b64decode(contents['stage/independent.json'], validate=True)
        r.require(io.digest(saved) == entry['checkpoints']['independent'])
        expected = cycles.independent(req['evidence_root'], 'manifest.json', req['now'])
        r.require(io.decode(saved) == expected and expected['outcome'] == 'selected')
        # Both original exports must still match the successful retained read.
        for path, item in envelope['files'].items():
            r.keys(item, 'status metadata sha256 bytes')
            raw = base64.b64decode(item['bytes'], validate=True)
            meta = item['metadata']
            r.require(isinstance(meta, list) and len(meta) == 9
                      and all(type(n) is int and n >= 0 for n in meta)
                      and meta[2:4] == [rt.value['source']['uid'], rt.value['source']['gid']]
                      and meta[4] == stat.S_IFREG | 0o600 and meta[8] == 1
                      and len(raw) == meta[5] and len(raw) <= r.transport.LIMIT)
            r.require(item['status'] == 'read' and item['sha256'] == io.digest(raw)
                      and base64.b64decode(contents[('incoming/' if '/' in path else 'intake/') + Path(path).name], validate=True) == raw)
        with owner.exact_directory(Path(req['parent_output']).parent) as fd:
            r.require(not owner.exists(fd, Path(req['parent_output']).name))
        # Recheck read-only inventory immediately before retaining authorization.
        r.require(capture(rt)[0] == checkpoint)
        return contents

    def authorization(self):
        rt = self.runtime
        return dict(origin=self.origin, pin=self.pin, selection_sha256=io.digest(self.raw),
                    original_selection=rt.pin, original_start=rt.start_origin,
                    request_sha256=r.c.fingerprint(rt.req), code=self.value['code'],
                    checkpoint=self.value['checkpoint'])

    def authorize(self):
        rt = self.runtime
        expected = self.authorization()
        binding = dict(pin=self.pin, origin=self.origin, selection_sha256=io.digest(self.raw),
                       authorization_sha256=r.c.fingerprint(expected))
        if 'recovery' not in rt.state:
            r.require(rt.selected['command']['action'] == 'recover')
            # A crash between evidence files and the parent binding is ambiguous;
            # never adopt unanchored state or re-run its effects.
            contents = self.initial_boundary()
            rt.record(SELECTION, self.value)
            rt.record(RETAINED, contents)
            rt.record(AUTHORIZATION, expected)
            rt.persist(recovery=binding)
        else:
            r.require(rt.state['recovery'] == binding)
            with owner.exact_directory(rt.evidence_root) as fd:
                r.require(owner.private_read(fd, SELECTION, r.LIMIT) == self.raw
                          and io.decode(owner.private_read(fd, AUTHORIZATION, r.LIMIT)) == expected)
                retained = io.decode(owner.private_read(fd, RETAINED, 2 * MAX_RETAINED))
            r.require(set(retained) == set(self.value['checkpoint']['files']))
            for name, raw in retained.items():
                r.require(io.digest(base64.b64decode(raw, validate=True)) == self.value['checkpoint']['files'][name]['sha256'])
            # Original durable evidence stays immutable even after disposable
            # cycle staging is reclaimed. No source/credential path is opened.
            paths = locations(rt)
            for role, selected in self.value['checkpoint']['directories'].items():
                if role not in ('movie', 'combined'):
                    with owner.exact_directory(paths[role][0]) as fd:
                        r.require(owner.identity(fd) == selected['identity']
                                  and stat.S_IMODE(os.fstat(fd).st_mode) == 0o700
                                  and storage.acl_identity(fd) == selected['acl'])
            for name, record in self.value['checkpoint']['files'].items():
                role, file = name.split('/', 1)
                if role in ('phase', 'adapter', 'intake', 'incoming', 'independent'):
                    r.require(read_file(paths[role][0] / file, cycles.MAX_RECORD)[0] == record)
            with owner.owner_store(rt.req) as (fd, ledger):
                owner.bound_intent(rt.req, fd, ledger)
                owner.verified_seal(rt.req, fd)

    def run(self):
        rt = self.runtime
        r.require(rt.selected['command']['action'] in ('recover', 'continue'))
        r.require(rt.state.get('recovery_last_comment') != rt.command_origin)
        # The command is consumed before any accepted preparation/handoff call.
        # Only a newer explicit matching continuation can inspect interrupted work.
        rt.persist(recovery_last_comment=rt.command_origin)
        status = rt.state['status']
        if status == 'preparation_uncertain':
            prepared = owner.prepare(rt.req)  # existing collecting => resume=True
            r.require(prepared['status'] == 'prepared')
            rt.persist(status='handoff_uncertain')
            status = 'handoff_uncertain'
        if status == 'handoff_uncertain':
            # Accepted semantics never grant a second handoff. Recover a lost
            # return ONLY if its exact output was already durably exposed.
            with owner.owner_store(rt.req) as (fd, ledger):
                owner.bound_intent(rt.req, fd, ledger)
                inspected = owner.inspect_locked(rt.req)
                r.require(inspected['status'] == 'prepared')
            rid = inspected['report_id']
            with owner.exact_directory(Path(rt.req['cycle_root']) / 'active') as fd:
                record = io.decode(owner.private_read(fd, rid + '.json', cycles.MAX_RECORD))
            if record['attempt'] is None:
                handoff = owner.handoff(rt.req)
                r.require(handoff['may_attempt'] is True)
                binding = cycles.binding_for(r.PHASE, rt.req['cycle'], rid, rt.req, handoff['sha256'])
            else:
                binding = cycles.binding_for(r.PHASE, rt.req['cycle'], rid, rt.req, record['sha256'])
                r.require(record['attempt'] == binding)
                path = Path(rt.req['parent_output'])
                with owner.exact_directory(path.parent) as fd:
                    raw = owner.private_read(fd, path.name, cycles.MAX_PAYLOAD)
                r.require(raw == record['payload'].encode() and io.digest(raw) == binding['payload_sha256'])
                with owner.exact_directory(Path(rt.req['cycle_root']) / 'handoff') as fd:
                    r.require(owner.private_read(fd, rid + '.json', cycles.MAX_PAYLOAD) == raw)
            rt.persist(attempt=binding, status='handoff_ready')
        r.require(rt.state['status'] == 'handoff_ready')
        rt.publish()  # existing durable at-most-one PUT and immutable readback
