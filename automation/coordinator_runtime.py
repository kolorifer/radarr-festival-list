"""Issue 122's ONE opt-in reporting opportunity, owned by the existing parent.

No CLI, scheduler, executor, arbitrary command, implicit retry or chat bridge.
Only dispatcher's authenticated ordinary poll may call operate(), under its locks.
All failure strings are fixed; exact evidence is retained privately.
"""
import base64
import contextlib
import datetime as dt
import hashlib
import os
from pathlib import Path
import re
import stat
import subprocess
import time
from urllib.parse import quote

from automation import coordinator as c
from automation import coordinator_cycles as cycles
from automation import coordinator_exports as exports
from automation import coordinator_io as io
from automation import coordinator_owner as owner
from automation import coordinator_sources as sources
from automation import coordinator_storage as storage
from automation import coordinator_transport as transport
from automation.supervisor_policy import PolicyError, PRIVATE_REPOSITORY, exact_path, hex_value

REPOSITORY = 'kolorifer/radarr-festival-list'
ISSUE = 122
PHASE = 'issue-122-partial-v1'
PREFIX = 'COORDINATOR_OPERATION: '
JOURNAL = 'finite-reporting-phase-1.json'
CLAIM = 'refs/heads/automation/reporting-operation-issue-122-phase-1'
LIMIT = 65536
# Dependency closure for newly reachable code, including validator-only producer
# dependencies. Deployment copies these reviewed blobs, never the whole main tree.
MANIFEST = tuple('automation/' + name + '.py' for name in (
    'github_worker', 'supervisor_policy', 'terminal_receipt', 'coordinator_storage',
    'coordinator_runtime', 'coordinator_transport', 'coordinator', 'coordinator_io',
    'coordinator_owner', 'coordinator_cycles', 'coordinator_exports', 'coordinator_sources',
    'coordinator_diagnostics', 'coordinator_integration', 'coordinator_outbox', 'coordinator_parent')) + (
        'identity_triage_store.py', 'identity_research_handoff.py',
        'identity_research_provider.py', 'identity_triage_intake.py')


def require(ok, reason='operation_rejected'):
    if not ok:
        raise PolicyError(reason)


def keys(value, names):
    require(isinstance(value, dict) and set(value) == set(names.split()))


def pin(value):
    keys(value, 'repository path commit blob sha256')
    require(value['repository'] == PRIVATE_REPOSITORY)
    exact_path(value['path'])
    require(value['path'].endswith('.json'))
    for field, length in (('commit', 40), ('blob', 40), ('sha256', 64)):
        require(hex_value(value[field], length))
    return value


def fetch(runner, selected, limit=LIMIT):
    """Authenticated immutable regular-tree pin read, with no local staging."""
    pin(selected)
    repository = selected['repository']
    runner.private_repository(repository)
    commit = runner.api('repos/' + repository + '/git/commits/' + selected['commit'])
    require(commit.get('sha') == selected['commit'] and hex_value(commit.get('tree', {}).get('sha'), 40))
    tree_sha = commit['tree']['sha']
    parts = selected['path'].split('/')
    for index, part in enumerate(parts):
        tree = runner.api('repos/' + repository + '/git/trees/' + tree_sha)
        matches = [v for v in tree.get('tree', []) if v.get('path') == part]
        require(tree.get('sha') == tree_sha and tree.get('truncated') is False and len(matches) == 1)
        node = matches[0]
        if index < len(parts) - 1:
            require(node.get('mode') == '040000' and node.get('type') == 'tree' and hex_value(node.get('sha'), 40))
            tree_sha = node['sha']
        else:
            require(node.get('mode') == '100644' and node.get('type') == 'blob'
                    and node.get('sha') == selected['blob'] and type(node.get('size')) is int
                    and 0 <= node['size'] <= limit)
    item = runner.api('repos/' + repository + '/contents/' + quote(selected['path'], safe='/') + '?ref=' + selected['commit'])
    raw = runner.decode_private(item)
    require(item.get('sha') == selected['blob'] and item.get('path') == selected['path']
            and len(raw) == node['size'] and len(raw) <= limit
            and hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == selected['blob']
            and io.digest(raw) == selected['sha256'])
    return raw


def timestamp(value):
    require(isinstance(value, str) and re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ', value))
    return dt.datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=dt.timezone.utc).timestamp()


def origin(comment, expected_owner):
    require(comment.get('user', {}).get('login') == expected_owner
            and type(comment.get('id')) is int and comment['id'] > 0
            and comment.get('created_at') == comment.get('updated_at'))
    timestamp(comment['created_at'])
    return {k: comment[k] for k in ('id', 'body', 'created_at', 'updated_at')} | {'author': expected_owner}


def select(comments, issue, repository):
    """No request => None, with no filesystem/network effects or new capabilities."""
    commands = []
    author = issue['user']['login']
    for comment in comments:
        if comment['user']['login'] != author:
            continue
        body = comment['body']
        if not re.search(r'(?im)^\s*COORDINATOR_OPERATION\b', body):
            continue
        require(repository == REPOSITORY and issue.get('number') == ISSUE
                and issue.get('url') == f'https://api.github.com/repos/{REPOSITORY}/issues/{ISSUE}')
        require(body.startswith(PREFIX) and '\n' not in body and len(body) <= 4096)
        value = io.decode(body[len(PREFIX):])
        action = value.get('action') if isinstance(value, dict) else None
        keys(value, 'action phase selection acknowledgement' if action == 'ack' else 'action phase selection')
        require(action in ('start', 'reconcile', 'ack') and value['phase'] == PHASE
                and body == PREFIX + io.encode(value).decode('ascii'))
        pin(value['selection'])
        if action == 'ack':
            pin(value['acknowledgement'])
        origin(comment, author)
        commands.append((comment, value))
    if not commands:
        return None
    require(len(commands) <= 32)
    starts = [(cm, v) for cm, v in commands if v['action'] == 'start']
    require(len(starts) == 1)
    start, initial = starts[0]
    acknowledgements = []
    for cm, value in commands:
        require(value['selection'] == initial['selection'] and cm['id'] >= start['id']
                and timestamp(cm['created_at']) >= timestamp(start['created_at']))
        if value['action'] == 'ack':
            acknowledgements.append(value['acknowledgement'])
    require(not acknowledgements or all(a == acknowledgements[0] for a in acknowledgements))
    latest, value = max(commands, key=lambda item: item[0]['id'])
    # Retain the FIRST exact acknowledgement origin, including on matching replay.
    ack = next(((cm, v) for cm, v in commands if v['action'] == 'ack'), None)
    return {'id': latest['id'], 'start': start, 'comment': latest, 'command': value, 'ack': ack}


def authenticate(runner, comment, author):
    current = runner.api(f'repos/{REPOSITORY}/issues/comments/{comment["id"]}')
    require(origin(current, author) == origin(comment, author)
            and current.get('issue_url') == f'https://api.github.com/repos/{REPOSITORY}/issues/{ISSUE}')
    return origin(current, author)


def file_identity(value):
    keys(value, 'path dev ino')
    require(storage.canonical(value['path']) and type(value['dev']) is int and value['dev'] >= 0
            and type(value['ino']) is int and value['ino'] > 0)


def validate(value, runner, author):
    keys(value, 'version repository issue phase operation reviewed_revision deployed_revision code_sha256 storage staging source request recipient_chat independent')
    require(type(value['version']) is int and value['version'] == 1 and value['repository'] == REPOSITORY
            and type(value['issue']) is int and value['issue'] == ISSUE and value['phase'] == PHASE)
    c.identifier(value['operation']); c.identifier(value['recipient_chat'])
    require(value['deployed_revision'] == runner.runner_revision and hex_value(runner.runner_revision, 40))
    require(hex_value(value['reviewed_revision'], 40))
    reviewed = runner.api(f'repos/{REPOSITORY}/git/commits/{value["reviewed_revision"]}')
    require(reviewed.get('sha') == value['reviewed_revision'] and hex_value(reviewed.get('tree', {}).get('sha'), 40))
    hashes = value['code_sha256']
    require(isinstance(hashes, dict) and set(hashes) == set(MANIFEST))
    code_root = Path(__file__).resolve().parent.parent
    require(runner.repo == code_root and runner.git('rev-parse', 'HEAD').strip() == value['deployed_revision']
            and runner.git('status', '--porcelain', '--', *MANIFEST) == '')
    for name in MANIFEST:
        require(hex_value(hashes[name], 64) and io.digest(io.read_bytes(code_root, name, transport.LIMIT)) == hashes[name])
    enclosing = storage.selection(io.encode(value['storage']))
    require(isinstance(enclosing['expected'], dict))  # REUSE ONLY; never mkdir/repair.
    file_identity(value['staging'])
    req = value['request']
    require(isinstance(req, dict) and type(req.get('version')) is int and req['version'] == owner.VERSION)
    owner.validate_request(req)
    require(req['owner'] == author and req['cycle'] == value['operation'] and req['runtime'] == PHASE
            and req['recipient'] != author and value['recipient_chat'] != author
            and Path(req['base']).parent == Path(enclosing['path'])
            and Path(req['parent_output']).parent == Path(value['staging']['path']))
    require(req['destination']['path'] == f'operations/issue-122/{value["operation"]}.json')
    src = value['source']
    keys(src, 'host port account key known_hosts root uid gid ancestors')
    require(isinstance(src['host'], str) and re.fullmatch(r'[a-z0-9][a-z0-9.-]{0,252}', src['host'])
            and not src['host'].endswith('.') and '..' not in src['host']
            and type(src['port']) is int and 1 <= src['port'] <= 65535
            and isinstance(src['account'], str) and re.fullmatch(r'[a-z_][a-z0-9_-]{0,31}', src['account'])
            and type(src['uid']) is int and src['uid'] > 0
            and type(src['gid']) is int and src['gid'] >= 0 and storage.canonical(src['root'])
            and src['root'] == req['source_path'])
    for field in ('key', 'known_hosts'):
        file_identity(src[field])
    ancestors = src['ancestors']
    require(isinstance(ancestors, list) and len(ancestors) == len(src['root'].split('/'))
            and all(isinstance(a, list) and len(a) == 5
                    and all(type(n) is int and n >= 0 for n in a)
                    and a[1] > 0 and stat.S_ISDIR(a[4]) and not a[4] & 0o022
                    and a[2] in (0, src['uid']) for a in ancestors)
            and ancestors[-1][2:4] == [src['uid'], src['gid']]
            and stat.S_IMODE(ancestors[-1][4]) == 0o700)
    independent = value['independent']
    evidence = {}
    if independent is None:
        require(req['evidence_manifest_sha256'] is None)
    else:
        keys(independent, 'manifest engineering parent_status')
        for name, selected in independent.items():
            if selected is not None:
                evidence['manifest.json' if name == 'manifest' else name + '.json'] = fetch(runner, selected, sources.c.MAX_BYTES)
        require('manifest.json' in evidence and io.digest(evidence['manifest.json']) == req['evidence_manifest_sha256'])
        manifest = sources.manifest(io.decode(evidence['manifest.json']), req['now'])
        for entry in manifest['sources']:
            name = entry['id'] + '.json'
            if entry['id'] not in ('engineering', 'parent_status'):
                require(entry['path'] is None)
            else:
                require(entry['path'] == (name if name in evidence else None))
                if name in evidence:
                    require(io.digest(evidence[name]) == entry['sha256'])
    return evidence


def safe_write(root, name, raw):
    with owner.exact_directory(root) as fd:
        owner.identity(fd)
        if owner.exists(fd, name):
            require(owner.private_read(fd, name, max(len(raw), LIMIT)) == raw)
        else:
            exports._write_new(fd, name, raw)


class Runtime:
    def __init__(self, runner, issue, selected, login):
        self.runner, self.issue, self.selected = runner, issue, selected
        self.author = issue['user']['login']
        require(login == self.author and runner.args.github_repo == REPOSITORY and runner.args.issue == ISSUE
                and runner.global_lock_fd is not None and runner.lock_fd is not None and not runner.args.dry_run)
        for fd, path in ((runner.global_lock_fd, runner.dispatch_dir / 'dispatcher.lock'),
                         (runner.lock_fd, runner.state_dir / 'runner.lock')):
            require(os.path.samestat(os.fstat(fd), os.stat(path, follow_symlinks=False)))
        self.start_origin = authenticate(runner, selected['start'], self.author)
        self.command_origin = authenticate(runner, selected['comment'], self.author)
        self.pin = selected['command']['selection']
        self.raw_selection = fetch(runner, self.pin)
        self.value = io.decode(self.raw_selection)
        self.evidence = validate(self.value, runner, self.author)
        self.req = self.value['request']
        self.evidence_root = Path(self.value['storage']['path']) / 'finite-phase-1'
        require(Path(self.req['base']) != self.evidence_root)
        self.state = None

    def persist(self, **changes):
        self.state.update(changes)
        raw = io.encode(self.state)
        require(len(raw) <= LIMIT)
        with owner.exact_directory(self.runner.state_dir) as fd:
            owner.identity(fd)
            cycles.write(fd, JOURNAL, raw, replace=True)

    def guards(self):
        protected = [self.runner.repo, self.runner.dispatch_dir]
        # Both commissioned root and staging are explicitly selected existing
        # private directories; all ancestors get the accepted ACL/owner guards.
        self.grants = []
        for field, path, expected in (
                ('storage', self.value['storage']['path'], self.value['storage']['expected']),
                ('staging', self.value['staging']['path'], {k: self.value['staging'][k] for k in ('dev', 'ino')})):
            others = protected + [Path(self.value['staging']['path'] if field == 'storage' else self.value['storage']['path'])]
            grant = storage.Grant({'version': 1, 'path': path, 'expected': expected}, self.pin, others, lambda _: None)
            # Grant's constructor derives home only for its fixed suffix. The
            # separately selected staging/SSH parents use the same OS-account
            # owner rules, never a home sliced from an arbitrary path length.
            grant.home = storage.pwd.getpwuid(os.geteuid()).pw_dir
            # Read-only guard: never call Grant.prepare (which can create).
            with grant.chain(path, guard=True) as (_, observed):
                grant.separation(observed)
                require(observed[-1]['identity'][:2] == [expected['dev'], expected['ino']])
                grant.baseline = observed
            self.grants.append(grant)
        # No selected key file may overlap writable state or public/Git state.
        for field in ('key', 'known_hosts'):
            path = Path(self.value['source'][field]['path'])
            for root in protected + [Path(self.value['storage']['path']), Path(self.value['staging']['path'])]:
                require(root != path and root not in path.parents and path not in root.parents)

    def verify(self):
        for grant in self.grants:
            grant.verify()
        if self.state.get('evidence_identity'):
            with owner.exact_directory(self.evidence_root) as fd:
                require(owner.identity(fd) == self.state['evidence_identity'])

    def load(self):
        with owner.exact_directory(self.runner.state_dir) as fd:
            owner.identity(fd)
            try:
                raw = owner.private_read(fd, JOURNAL, LIMIT)
            except FileNotFoundError:
                return False
        self.state = io.decode(raw)
        require(self.state['version'] == 1 and self.state['selection'] == self.pin
                and self.state['start'] == self.start_origin
                and self.state['selection_sha256'] == io.digest(self.raw_selection)
                and self.state['request'] == self.req)
        return True

    def record(self, name, value):
        self.verify()
        safe_write(self.evidence_root, name, io.encode(value))

    def claim_and_start(self):
        now = time.time()
        require(0 <= now - timestamp(self.selected['start']['created_at']) <= 3600
                and 0 <= now - self.req['now'] <= 300)
        self.state = dict(version=1, selection=self.pin, selection_sha256=io.digest(self.raw_selection),
                          start=self.start_origin, request=self.req, status='claim_uncertain',
                          claim_confirmed=False, evidence_identity=None, attempt=None,
                          publication=None, acknowledgement=None)
        # Exclusive durable local consumption precedes the cross-host claim.
        with owner.exact_directory(self.runner.state_dir) as fd:
            owner.identity(fd)
            exports._write_new(fd, JOURNAL, io.encode(self.state))
        claim = self.runner.api(f'repos/{REPOSITORY}/git/refs', ref=CLAIM, sha=self.value['reviewed_revision'])
        require(claim.get('ref') == CLAIM and claim.get('object', {}).get('sha') == self.value['reviewed_revision'])
        self.persist(claim_confirmed=True, status='reserved')
        self.verify()
        with owner.exact_directory(self.evidence_root.parent) as fd:
            os.mkdir(self.evidence_root.name, 0o700, dir_fd=fd)
            os.fsync(fd)
        with owner.exact_directory(self.evidence_root) as fd:
            self.persist(evidence_identity=owner.identity(fd))
        safe_write(self.evidence_root, 'selection.json', self.raw_selection)
        self.record('authorization.json', {'pin': self.pin, 'start': self.start_origin, 'claim': claim,
                                           'storage': [g.baseline for g in self.grants]})
        reservation = owner.reserve(self.req)
        require(reservation['acquisition_grant'] is True)
        self.persist(status='acquisition_uncertain', reservation=reservation)
        # Keys stay in this parent process and its one SSH process; never a child
        # worker, helper request or environment. Exact private FDs avoid link races.
        with contextlib.ExitStack() as stack:
            descriptors, held_files = [], []
            for field in ('key', 'known_hosts'):
                pin_file = self.value['source'][field]
                path = Path(pin_file['path'])
                grant = storage.Grant({'version': 1, 'path': str(path.parent), 'expected': 'unused'},
                                      self.pin, [], lambda _: None)
                grant.home = storage.pwd.getpwuid(os.geteuid()).pw_dir
                parent, _ = stack.enter_context(grant.chain(path.parent, guard=True))
                require(storage.exact_entry(parent, path.name))
                fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
                stack.callback(os.close, fd)
                cycles.private(fd)
                st = os.fstat(fd)
                require([st.st_dev, st.st_ino] == [pin_file['dev'], pin_file['ino']]
                        and stat.S_IMODE(st.st_mode) == 0o600 and st.st_size <= LIMIT)
                storage.acl_identity(fd)
                descriptors.append(fd)
                held_files.append((fd, parent, path.name, transport.metadata(fd), storage.acl_identity(fd)))
            helper = io.read_bytes(self.runner.repo, 'automation/coordinator_transport.py', LIMIT)
            require(io.digest(helper) == self.value['code_sha256']['automation/coordinator_transport.py'])
            result = transport.acquire(self.value['source'], *descriptors, helper,
                                       lock_fds=self.runner.inherited_locks())
            self.record('transport.json', {'complete': result['complete'], 'returncode': result['returncode'],
                        'stdout': base64.b64encode(result['stdout']).decode(),
                        'stderr': base64.b64encode(result['stderr']).decode(), 'acquired_at': time.time()})
            for fd, parent, name, before, before_acl in held_files:
                require(transport.metadata(fd) == before and storage.acl_identity(fd) == before_acl
                        and storage.exact_entry(parent, name)
                        and os.path.samestat(os.fstat(fd), os.stat(name, dir_fd=parent, follow_symlinks=False)))
        # A failed/uncertain transport burns the opportunity but can still produce
        # an honest unavailable report with independently pinned engineering facts.
        files = {}
        if result['complete'] and result['returncode'] == 0:
            try:
                envelope = io.decode(result['stdout'])
                keys(envelope, 'version files')
                require(type(envelope['version']) is int and envelope['version'] == 1
                        and set(envelope['files']) == set(owner.FIXED_PATHS))
                for path, value in envelope['files'].items():
                    require(value['status'] in ('read', 'missing', 'oversized'))
                    keys(value, {'read': 'status metadata sha256 bytes', 'missing': 'status',
                                 'oversized': 'status metadata'}[value['status']])
                    if value['status'] != 'missing':
                        meta = value['metadata']
                        require(isinstance(meta, list) and len(meta) == 9
                                and all(type(n) is int and n >= 0 for n in meta)
                                and meta[2:4] == [self.value['source']['uid'], self.value['source']['gid']]
                                and meta[4] == stat.S_IFREG|0o600 and meta[8] == 1)
                    if value['status'] == 'read':
                        raw = base64.b64decode(value['bytes'], validate=True)
                        require(len(raw) <= transport.LIMIT and len(raw) == meta[5] and io.digest(raw) == value['sha256'])
                        files[path] = raw
            except (ValueError, KeyError, TypeError, PolicyError):
                files = {}
        self.verify()
        for path, raw in files.items():
            dest = Path(self.req['intake_root']) / path
            safe_write(dest.parent, dest.name, raw)
        for name, raw in self.evidence.items():
            safe_write(self.req['evidence_root'], name, raw)
        owner.seal(self.req)
        self.persist(status='preparation_uncertain')
        prepared = owner.prepare(self.req)
        require(prepared['status'] == 'prepared')
        self.persist(status='handoff_uncertain')
        handoff = owner.handoff(self.req)
        require(handoff['may_attempt'] is True)
        binding = cycles.binding_for(self.req['runtime'], self.req['cycle'], handoff['report_id'],
                                     self.req, handoff['sha256'])
        self.persist(attempt=binding, status='handoff_ready')
        self.publish()

    def payload(self):
        path = Path(self.req['parent_output'])
        with owner.exact_directory(path.parent) as fd:
            raw = owner.private_read(fd, path.name, cycles.MAX_PAYLOAD)
        require(self.state['attempt'] is not None and io.digest(raw) == self.state['attempt']['payload_sha256'])
        return raw

    def remote_read(self):
        destination = self.req['destination']
        self.runner.private_repository(destination['repository'])
        endpoint = 'repos/' + destination['repository'] + '/contents/' + quote(destination['path'], safe='/')
        try:
            return self.runner.api(endpoint + '?ref=main')
        except subprocess.CalledProcessError as exc:
            require('HTTP 404' in (exc.stderr or ''), 'operation_readback_unavailable')
            return None

    def publish(self):
        require(self.state['status'] == 'handoff_ready' and self.state['claim_confirmed'])
        self.verify()
        content = self.payload()
        require(self.remote_read() is None, 'operation_destination_exists')
        # No response, 404, exception or restart may grant another PUT.
        self.persist(status='publication_uncertain', write_attempted_at=time.time())
        destination = self.req['destination']
        endpoint = 'repos/' + destination['repository'] + '/contents/' + quote(destination['path'], safe='/')
        response = self.runner.run(['gh', 'api', endpoint, '--method', 'PUT', '--input', '-'],
                                  input=io.encode({'message': 'Retain finite coordinator report', 'branch': 'main',
                                                   'content': base64.b64encode(content).decode()}).decode())
        response = io.decode(response)
        commit = response.get('commit', {}).get('sha')
        blob = response.get('content', {}).get('sha')
        require(hex_value(commit, 40) and hex_value(blob, 40))
        self.persist(remote_write={'commit': commit, 'blob': blob})
        self.reconcile()

    def reconcile(self):
        require(self.state['claim_confirmed'] and self.state['status'] in ('publication_uncertain', 'published', 'archived'))
        if self.state['publication'] is not None:
            return  # Retained authenticated readback; no mutable-main dependency.
        self.verify()
        content = self.payload()
        try:
            with owner.exact_directory(self.evidence_root) as fd:
                observation = io.decode(owner.private_read(fd, 'publication-observation.json', LIMIT))
        except FileNotFoundError:
            item = self.remote_read()
            require(item is not None and item.get('path') == self.req['destination']['path']
                    and self.runner.decode_private(item) == content, 'operation_readback_unavailable')
            blob = hashlib.sha1(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest()
            require(item['sha'] == blob)
            # A known PUT response selects its exact commit; ambiguity pins the
            # authenticated observed main commit, never issues another write.
            commit = (self.state['remote_write']['commit'] if self.state.get('remote_write') else
                      self.runner.api('repos/' + PRIVATE_REPOSITORY + '/commits/main').get('sha'))
            require(hex_value(commit, 40))
            remote_pin = dict(repository=PRIVATE_REPOSITORY, path=self.req['destination']['path'],
                              commit=commit, blob=blob, sha256=io.digest(content))
            require(fetch(self.runner, remote_pin, cycles.MAX_PAYLOAD) == content)
            if self.state.get('remote_write'):
                require(self.state['remote_write']['blob'] == blob)
            receipt = dict(version=1, kind='publication', owner=self.author, issuer=self.author,
                           binding=self.state['attempt'], observed_at=time.time(),
                           reference='publication-' + c.fingerprint(remote_pin))
            observation = {'remote': remote_pin, 'receipt': receipt}
            self.record('publication-observation.json', observation)
        remote_pin, receipt = observation['remote'], observation['receipt']
        require(remote_pin['path'] == self.req['destination']['path']
                and remote_pin['sha256'] == io.digest(content) and receipt['binding'] == self.state['attempt']
                and receipt['reference'] == 'publication-' + c.fingerprint(remote_pin)
                and fetch(self.runner, remote_pin, cycles.MAX_PAYLOAD) == content)
        self.install_receipt('publication', receipt, content)
        with owner.exact_directory(self.req['receipt_root']) as fd:
            retained = io.decode(owner.private_read(fd, 'publication.json', 16384))
        self.record('publication.json', {'binding': self.state['attempt'], 'remote': remote_pin,
                                        'observed_at': retained['observed_at'], 'receipt': retained})
        owner.receipt(self.req, 'publication', 'publication')
        self.persist(publication=remote_pin, publication_observed_at=retained['observed_at'], status='published')

    def install_receipt(self, kind, receipt, payload=None):
        root = self.req['receipt_root']
        if payload is not None:
            safe_write(root, kind + '.payload', payload)
        safe_write(root, kind + '.json', io.encode(receipt))

    def acknowledge(self):
        require(self.selected['ack'] is not None and self.state['publication'] is not None)
        comment, command = self.selected['ack']
        selected_origin = authenticate(self.runner, comment, self.author)
        selected_pin = command['acknowledgement']
        ack = io.decode(fetch(self.runner, selected_pin))
        keys(ack, 'version phase operation selection binding recipient_chat ingestion_reference observed_at publication')
        require(type(ack['version']) is int and ack['version'] == 1 and ack['phase'] == PHASE
                and ack['operation'] == self.value['operation'] and ack['selection'] == self.pin
                and ack['binding'] == self.state['attempt'] and ack['recipient_chat'] == self.value['recipient_chat']
                and ack['publication'] == self.state['publication'])
        c.identifier(ack['ingestion_reference']); c.stamp(ack['observed_at'])
        require(self.state['publication_observed_at'] <= ack['observed_at'] <= timestamp(comment['created_at']) + 300
                and timestamp(comment['created_at']) <= time.time() + 300)
        evidence = {'origin': selected_origin, 'pin': selected_pin, 'selection': ack}
        if self.state['acknowledgement'] is not None:
            require(self.state['acknowledgement'] == evidence)
        else:
            # Persist authenticated owner selection before constructing accepted
            # recipient receipt; worker JSON and engineering receipts cannot enter.
            self.record('acknowledgement.json', evidence)
            self.persist(acknowledgement=evidence)
        receipt = dict(version=1, kind='recipient', owner=self.author, issuer=self.req['recipient'],
                       binding=self.state['attempt'], observed_at=ack['observed_at'],
                       reference=ack['ingestion_reference'])
        self.install_receipt('recipient', receipt)
        owner.receipt(self.req, 'recipient', 'recipient')
        result = owner.archive(self.req)
        require(result['archived'] is True)
        self.record('archive.json', result)
        self.persist(status='archived')

    def run(self):
        self.guards()
        existing = self.load()
        action = self.selected['command']['action']
        if not existing:
            require(action == 'start')
            # A fresh phase never adopts an old adapter/evidence tree, even if
            # it happens to carry accepted same-shaped markers or requests.
            with owner.exact_directory(Path(self.req['base']).parent) as fd:
                require(not owner.exists(fd, Path(self.req['base']).name)
                        and not owner.exists(fd, self.evidence_root.name))
            output = Path(self.req['parent_output'])
            with owner.exact_directory(output.parent) as fd:
                require(not owner.exists(fd, output.name))
            self.claim_and_start()
        elif action == 'start':
            return  # Never continue uncertain work from an ordinary repeated poll.
        else:
            self.verify()
            require(self.state['claim_confirmed'])
            if self.state['status'] == 'archived':
                if action == 'ack':
                    require(self.selected['ack'][1]['acknowledgement'] == self.state['acknowledgement']['pin'])
                return
            # Each selected continuation is consumed too. Matching completed
            # ack/archive replay can finish idempotently after an interruption.
            if action == 'reconcile':
                if self.state.get('reconciled_comment') == self.command_origin:
                    return
                self.persist(reconciled_comment=self.command_origin)
                self.reconcile()
            else:
                # Ack cannot implicitly reconcile a publication. Authenticate
                # and validate the entire selected ack before any receipt write.
                require(self.state['publication'] is not None)
                self.acknowledge()


def operate(runner, issue, selected, login):
    """Only fixed public failure/result codes; no private exception text escapes."""
    try:
        Runtime(runner, issue, selected, login).run()
    except (OSError, ValueError, PolicyError, KeyError, TypeError, AttributeError,
            RecursionError, subprocess.SubprocessError):
        raise PolicyError('finite_reporting_needs_owner_review') from None
