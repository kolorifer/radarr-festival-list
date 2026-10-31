"""Fixed issue125 seven-window protocol, invoked only by the existing poll.

No CLI, daemon, worker, provider, refresh or receiving bridge. Local scheduling
records never authenticate an operation; immutable owner selections do that.
"""
import hashlib
import os
from pathlib import Path
import re
import subprocess
import time

from automation import coordinator_runtime as r
from automation import coordinator as c
from automation import coordinator_cycles as cycles
from automation import coordinator_owner as owner
from automation import coordinator_io as io
from automation import coordinator_storage as storage
from automation.supervisor_policy import PolicyError

ISSUE = 125
PHASE = 'issue-125-seven-day-v1'
PREFIX = 'COORDINATOR_TRIAL: '
JOURNAL = 'issue-125-seven-day-v1.json'
CLAIM = 'refs/heads/automation/reporting-operation-issue-125-seven-day-v1'
CHAT = '01a18e6b-d16e-7e80-ab37-381b11891c2f'
MANIFEST = r.MANIFEST + ('automation/coordinator_trial.py',)
require, keys = r.require, r.keys
TERMINAL = ('missed', 'quiet', 'backpressure', 'burned', 'archived')
STATUSES = TERMINAL + ('reserved', 'acquisition_uncertain', 'preparation_uncertain',
                       'handoff_uncertain', 'handoff_ready', 'publication_uncertain', 'published')


class Slot(dict):
    """Keep reused finite-runtime detail lookups out of owner-store inventory."""
    def __missing__(self, key):
        return self['details'][key]

    def get(self, key, default=None):
        return dict.get(self, key, self['details'].get(key, default))


def pin(value):
    keys(value, 'repository path commit tree blob sha256')
    require(r.hex_value(value['tree'], 40))
    return r.pin({k: v for k, v in value.items() if k != 'tree'})


def fetch(runner, selected):
    simple = pin(selected)
    commit = runner.api('repos/' + selected['repository'] + '/git/commits/' + selected['commit'])
    require(commit.get('sha') == selected['commit'] and commit.get('tree', {}).get('sha') == selected['tree'])
    return r.fetch(runner, simple)


def select(comments, issue, repository):
    """Only canonical unedited owner comments; issue prose is never authority."""
    commands = []
    author = issue['user']['login']
    for cm in comments:
        if cm['user']['login'] != author or not re.search(r'(?im)^\s*COORDINATOR_TRIAL\b', cm['body']):
            continue
        require(repository == r.REPOSITORY and issue.get('number') == ISSUE
                and issue.get('url') == f'https://api.github.com/repos/{r.REPOSITORY}/issues/{ISSUE}')
        body = cm['body']
        require(body.startswith(PREFIX) and '\n' not in body and len(body) <= 4096)
        value = io.decode(body[len(PREFIX):])
        require(isinstance(value, dict))
        action = value.get('action')
        keys(value, 'action phase selection' + ('' if action in ('activate', 'stop') else ' slot')
             + (' acknowledgement' if action == 'ack' else ''))
        require(action in ('activate', 'stop', 'reconcile', 'ack') and value['phase'] == PHASE
                and body == PREFIX + io.encode(value).decode())
        pin(value['selection'])
        if action not in ('activate', 'stop'):
            require(type(value['slot']) is int and 1 <= value['slot'] <= 7)
        if action == 'ack':
            pin(value['acknowledgement'])
        r.origin(cm, author)
        commands.append((cm, value))
    if not commands:
        return None
    require(len(commands) <= 32)
    starts = [(cm, v) for cm, v in commands if v['action'] == 'activate']
    require(len(starts) == 1)
    start, command = starts[0]
    for cm, v in commands:
        require(v['selection'] == command['selection'] and cm['id'] >= start['id']
                and r.timestamp(cm['created_at']) >= r.timestamp(start['created_at']))
    for n in range(1, 8):
        acks = [v['acknowledgement'] for cm, v in commands if v.get('slot') == n and v['action'] == 'ack']
        require(not acks or all(v == acks[0] for v in acks))
        require(sum(v.get('slot') == n and v['action'] == 'reconcile' for cm, v in commands) <= 2)
    latest = max(commands, key=lambda item: item[0]['id'])
    return dict(id=latest[0]['id'], start=start, selection=command['selection'], commands=commands)


def authenticate(runner, cm, author):
    current = runner.api(f'repos/{r.REPOSITORY}/issues/comments/{cm["id"]}')
    require(r.origin(current, author) == r.origin(cm, author)
            and current.get('issue_url') == f'https://api.github.com/repos/{r.REPOSITORY}/issues/{ISSUE}')
    require(r.timestamp(cm['created_at']) <= time.time() + 300)
    return r.origin(current, author)


def load(runner, selected, author):
    try:
        with owner.exact_directory(runner.state_dir) as fd:
            owner.identity(fd)
            state = io.decode(owner.private_read(fd, JOURNAL, r.LIMIT))
    except FileNotFoundError:
        return None
    keys(state, 'version phase selection origin status windows high_water slots consumed evidence_identity')
    require(type(state['version']) is int and state['version'] == 1 and state['phase'] == PHASE
            and state['selection'] == selected['selection']
            and state['origin'] == r.origin(selected['start'], author)
            and state['status'] in ('claim_uncertain', 'active')
            and isinstance(state['slots'], dict) and set(state['slots']) <= {str(n) for n in range(1, 8)}
            and isinstance(state['consumed'], list) and len(state['consumed']) <= 21
            and len(set(state['consumed'])) == len(state['consumed'])
            and all(type(v) is int and v > 0 for v in state['consumed']))
    c.stamp(state['high_water'])
    windows(state['windows'])
    if state['status'] == 'active':
        require(isinstance(state['evidence_identity'], list) and len(state['evidence_identity']) == 2
                and all(type(v) is int and v >= 0 for v in state['evidence_identity']))
    for n, entry in state['slots'].items():
        keys(entry, 'status request evidence_identity attempt publication acknowledgement claim_confirmed details')
        require(entry['status'] in STATUSES and entry['claim_confirmed'] is True
                and isinstance(entry['details'], dict))
        if entry['request'] is not None:
            owner.validate_request(entry['request'])
            require(entry['request']['runtime'] == PHASE and entry['request']['cycle'] == 'day-' + n
                    and entry['request']['owner'] == author)
        else:
            require(entry['status'] == 'missed')
        if entry['status'] in ('publication_uncertain', 'published', 'archived'):
            require(entry['attempt'] is not None)
        if entry['status'] in ('published', 'archived'):
            require(entry['publication'] is not None)
    return state


def windows(value):
    require(isinstance(value, list) and len(value) == 7)
    for i, window in enumerate(value):
        keys(window, 'slot start end')
        require(type(window['slot']) is int and window['slot'] == i + 1)
        start, end = r.timestamp(window['start']), r.timestamp(window['end'])
        require(window['start'].endswith('T11:30:00Z') and window['end'].endswith('T11:40:00Z')
                and end - start == 600)
        if i:
            require(start - r.timestamp(value[i - 1]['start']) == 86400)


def work(state, selected, now):
    """Misses have no late transport; rollback freezes until the prior clock."""
    if any(command['action'] == 'stop' for cm, command in selected['commands']):
        return None
    if state is None:
        return ('activate', None, None)
    if state['status'] != 'active' or now < state['high_water']:
        return None
    for window in state['windows']:
        n = window['slot']
        if str(n) not in state['slots'] and now >= r.timestamp(window['start']):
            return ('missed' if now >= r.timestamp(window['end']) else 'acquire', n, None)
    for cm, command in selected['commands']:
        if command['action'] in ('activate', 'stop'):
            continue
        entry = state['slots'].get(str(command['slot']))
        if entry is None or entry['status'] not in ('publication_uncertain', 'published'):
            continue
        if command['action'] == 'reconcile':
            if entry['publication'] is None and cm['id'] not in state['consumed']:
                return ('reconcile', command['slot'], (cm, command))
            # A retained observation can finish import with no second readback.
            if (entry['publication'] is None and entry['details'].get('reconciled') == cm['id']
                    and retained_observation(entry, command['slot'])):
                return ('reconcile', command['slot'], (cm, command))
        elif entry['publication'] is not None:
            # The first authentic ack remains the selected origin on replay.
            if cm['id'] not in state['consumed'] or entry['acknowledgement'] is not None:
                return ('ack', command['slot'], (cm, command))
    return None


def retained_observation(entry, n):
    """Local scheduling hint only; runtime reauthenticates before importing."""
    root = Path(entry['request']['base']).parent / PHASE / ('day-' + str(n))
    try:
        with owner.exact_directory(root) as fd:
            require(owner.identity(fd) == entry['evidence_identity'])
            value = io.decode(owner.private_read(fd, 'publication-observation.json', r.LIMIT))
    except FileNotFoundError:
        return False
    keys(value, 'remote receipt')
    r.pin(value['remote'])
    require(value['receipt']['binding'] == entry['attempt']
            and value['remote']['sha256'] == entry['attempt']['payload_sha256'])
    return True


def pending(runner, selected, author):
    require(selected is not None)
    return work(load(runner, selected, author), selected, time.time()) is not None


def validate(value, runner, author, selected):
    keys(value, 'version repository issue phase reviewed_revision deployed_revision code_sha256 storage staging source '
         'recipient_chat windows requests local_chains producer_identity installed_schedule')
    require(value['producer_identity'] == value['installed_schedule'] == 'unknown'
            and value['recipient_chat'] == CHAT)
    windows(value['windows'])
    require(isinstance(value['requests'], list) and len(value['requests']) == 7)
    first = r.timestamp(value['windows'][0]['start'])
    activated = r.timestamp(selected['start']['created_at'])
    require(0 < first - activated <= 86400)
    seen = set()
    shared = None
    first_request = None
    for n, template in enumerate(value['requests'], 1):
        require(isinstance(template, dict) and 'now' not in template)
        req = dict(template, now=r.timestamp(value['windows'][n - 1]['start']))
        # Reuse the strict source/storage/code/request validators, with an
        # explicit protocol tuple; issue122's default semantics remain intact.
        common = {k: v for k, v in value.items() if k not in (
            'windows', 'requests', 'local_chains', 'producer_identity', 'installed_schedule')}
        common.update(operation='day-' + str(n), request=req, independent=None)
        if n == 1:
            r.validate(common, runner, author, protocol=(ISSUE, PHASE, MANIFEST))
            first_request = template
        else:
            owner.validate_request(req)
            varying = {'cycle', 'intake_root', 'evidence_root', 'receipt_root', 'parent_output', 'destination'}
            require({k: v for k, v in template.items() if k not in varying}
                    == {k: v for k, v in first_request.items() if k not in varying})
            require(req['destination'] == dict(repository=r.PRIVATE_REPOSITORY,
                                               path=f'operations/issue-125/day-{n}.json'))
        require(req['cycle'] == 'day-' + str(n) and req['evidence_manifest_sha256'] is None
                and req['selector'] == 'existing-exports-only' and req['recipient'] == CHAT)
        roots = (req['base'], req['cycle_root'])
        require(shared is None or roots == shared)
        shared = roots
        for field in ('intake_root', 'evidence_root', 'receipt_root', 'parent_output'):
            require(req[field] not in seen)
            seen.add(req[field])
    root = Path(value['storage']['path'])
    require(Path(shared[0]) != root / PHASE)
    # Require the selective installed commit to exist remotely before activation.
    deployed = runner.api(f'repos/{r.REPOSITORY}/git/commits/{value["deployed_revision"]}')
    require(deployed.get('sha') == value['deployed_revision'] and r.hex_value(deployed.get('tree', {}).get('sha'), 40))
    # A selection's hash map is not proof that installed bytes were reviewed.
    # Require every regular runtime blob to be exactly in the reviewed commit,
    # while allowing the selective deployment's surrounding tree to differ.
    for name in MANIFEST:
        raw = io.read_bytes(runner.repo, name, r.transport.LIMIT)
        blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        require(runner.git('ls-tree', value['reviewed_revision'], '--', name)
                == '100644 blob ' + blob + '\t' + name + '\n')
    keys(value['local_chains'], 'storage staging key_parent known_hosts_parent')


class Trial(r.Runtime):
    """Reuse accepted guarded IO/publication components, never issue122 state."""
    def __init__(self, runner, issue, selected, login):
        self.runner, self.issue, self.selected = runner, issue, selected
        self.author = issue['user']['login']
        require(login == self.author and runner.args.github_repo == r.REPOSITORY
                and runner.args.issue == ISSUE and not runner.args.dry_run)
        for fd, path in ((runner.global_lock_fd, runner.dispatch_dir / 'dispatcher.lock'),
                         (runner.lock_fd, runner.state_dir / 'runner.lock')):
            require(fd is not None and os.path.samestat(os.fstat(fd), os.stat(path, follow_symlinks=False)))
        # Refetch current issue/comments under both locks. Latest stop/closed or
        # a superseding engineering task wins before any private input is read.
        current = runner.api(f'repos/{r.REPOSITORY}/issues/{ISSUE}')
        require(current['state'] == 'open' and current['user']['login'] == self.author)
        comments = runner.comments()
        from automation.github_worker import fields, task_number
        trusted = [cm for cm in comments if cm['user']['login'] in (login, self.author)]
        require(not trusted or fields(max(trusted, key=lambda cm: cm['id'])['body']).get('STATE') != 'DONE')
        latest = select(comments, current, r.REPOSITORY)
        require(latest == selected)
        engineering = [cm['id'] for cm in comments if cm['user']['login'] == self.author
                       and task_number(cm['body']) is not None
                       and (fields(cm['body']).get('STATE') == 'READY_FOR_CODEX' or 'GOAL' in fields(cm['body']))]
        require(selected['id'] >= max(engineering, default=0))
        self.start_origin = authenticate(runner, selected['start'], self.author)
        self.pin = selected['selection']
        self.raw_selection = fetch(runner, self.pin)
        self.trial_value = io.decode(self.raw_selection)
        require(self.raw_selection == io.encode(self.trial_value))
        validate(self.trial_value, runner, self.author, selected)
        self.journal = load(runner, selected, self.author)
        if self.journal:
            require(self.journal['windows'] == self.trial_value['windows'])
            require(self.journal['selection'] == self.pin)
        self.job = work(self.journal, selected, time.time())
        self.value = self.trial_value
        self.state = None
        self.evidence_root = Path(self.value['storage']['path']) / PHASE
        self.recovery = None
        self.evidence = {}

    def save(self, create=False):
        raw = io.encode(self.journal)
        require(len(raw) <= r.LIMIT)
        with owner.exact_directory(self.runner.state_dir) as fd:
            owner.identity(fd)
            if create:
                r.exports._write_new(fd, JOURNAL, raw)
            else:
                cycles.write(fd, JOURNAL, raw, replace=True)

    def authority(self):
        """Fresh stop/supersession checks at external-effect boundaries."""
        current = self.runner.api(f'repos/{r.REPOSITORY}/issues/{ISSUE}')
        require(current['state'] == 'open' and current['user']['login'] == self.author)
        comments = self.runner.comments()
        from automation.github_worker import fields, task_number
        trusted = [cm for cm in comments if cm['user']['login'] == self.author]
        require(not trusted or fields(max(trusted, key=lambda cm: cm['id'])['body']).get('STATE') != 'DONE')
        latest = select(comments, current, r.REPOSITORY)
        require(latest == self.selected and not any(v['action'] == 'stop' for cm, v in latest['commands']))
        require(not any(cm['id'] > latest['id'] and task_number(cm['body']) is not None
                        and (fields(cm['body']).get('STATE') == 'READY_FOR_CODEX' or 'GOAL' in fields(cm['body']))
                        for cm in trusted))
        authenticate(self.runner, self.selected['start'], self.author)

    def guards(self):
        super().guards()
        v = self.trial_value
        paths = dict(storage=v['storage']['path'], staging=v['staging']['path'],
                     key_parent=str(Path(v['source']['key']['path']).parent),
                     known_hosts_parent=str(Path(v['source']['known_hosts']['path']).parent))
        for name, path in paths.items():
            grant = storage.Grant(dict(version=1, path=path, expected='unused'), self.pin, [], lambda _: None)
            grant.home = storage.pwd.getpwuid(os.geteuid()).pw_dir
            with grant.chain(path, guard=True) as (_, observed):
                require(observed == v['local_chains'][name])

    def verify(self):
        for grant in self.grants:
            grant.verify()
        if self.journal and self.journal['evidence_identity'] is not None:
            root = Path(self.trial_value['storage']['path']) / PHASE
            with owner.exact_directory(root) as fd:
                require(owner.identity(fd) == self.journal['evidence_identity'])
        if self.state and self.state['evidence_identity'] is not None:
            with owner.exact_directory(self.evidence_root) as fd:
                require(owner.identity(fd) == self.state['evidence_identity'])

    def persist(self, **changes):
        # Reused publication fields remain bounded inside the slot's details.
        for name, value in changes.items():
            if name in self.state:
                self.state[name] = value
            else:
                self.state['details'][name] = value
        self.journal['slots'][str(self.number)] = self.state
        self.journal['high_water'] = max(self.journal['high_water'], time.time())
        self.save()

    def activate(self):
        self.authority()
        now = time.time()
        require(0 <= now - r.timestamp(self.selected['start']['created_at']) <= 3600
                and now < r.timestamp(self.value['windows'][0]['start']))
        parent = Path(self.value['storage']['path'])
        base = Path(self.value['requests'][0]['base'])
        with owner.exact_directory(parent) as fd:
            require(not owner.exists(fd, base.name) and not owner.exists(fd, PHASE))
        with owner.exact_directory(self.value['staging']['path']) as fd:
            require(all(not owner.exists(fd, Path(req['parent_output']).name) for req in self.value['requests']))
        self.journal = dict(version=1, phase=PHASE, selection=self.pin, origin=self.start_origin,
                            status='claim_uncertain', windows=self.value['windows'], high_water=now,
                            slots={}, consumed=[], evidence_identity=None)
        # Uncertain claim cannot be replayed/adopted. No new engineering claim.
        self.save(create=True)
        claim = self.runner.api(f'repos/{r.REPOSITORY}/git/refs', ref=CLAIM, sha=self.value['reviewed_revision'])
        require(claim.get('ref') == CLAIM and claim.get('object', {}).get('sha') == self.value['reviewed_revision'])
        self.verify()
        with owner.exact_directory(parent) as fd:
            os.mkdir(PHASE, 0o700, dir_fd=fd)
            os.fsync(fd)
        with owner.exact_directory(parent / PHASE) as fd:
            self.journal['evidence_identity'] = owner.identity(fd)
        self.evidence_root = parent / PHASE
        self.record('selection.json', self.value)
        self.record('authorization.json', dict(origin=self.start_origin, selection=self.pin, claim=claim))
        self.journal['status'] = 'active'
        self.save()

    def slot(self, n, missed=False):
        self.number = n
        template = self.trial_value['requests'][n - 1]
        self.req = dict(template, now=time.time())
        self.value = dict(self.trial_value, operation='day-' + str(n), request=self.req)
        self.evidence_root = Path(self.value['storage']['path']) / PHASE / ('day-' + str(n))
        self.state = self.journal['slots'].get(str(n))
        if self.state is None:
            self.state = Slot(status='missed' if missed else 'reserved', request=None if missed else self.req,
                              evidence_identity=None, attempt=None, publication=None, acknowledgement=None,
                              claim_confirmed=True, details={})
            # Durable per-window consumption BEFORE reserve or transport. Any
            # uncertain reservation/preparation is terminal to the scheduler.
            self.persist()
            if missed:
                return
            self.verify()
            with owner.exact_directory(self.evidence_root.parent) as fd:
                os.mkdir(self.evidence_root.name, 0o700, dir_fd=fd)
                os.fsync(fd)
            with owner.exact_directory(self.evidence_root) as fd:
                self.persist(evidence_identity=owner.identity(fd))
            self.record('reservation.json', dict(selection=self.pin, slot=n,
                        window=self.value['windows'][n - 1], request=self.req, observed_at=self.req['now']))
            with self.credentials():
                self.in_window()
                reservation = owner.reserve(self.req)
                require(reservation['acquisition_grant'] is True)
                self.persist(status='acquisition_uncertain', reservation=reservation)
                self.credential_check()
                self.in_window()
                self.acquire_prepare()
        else:
            self.state = Slot(self.state)
            self.req = self.state['request']
            require(self.req is not None and {k: v for k, v in self.req.items() if k != 'now'} == template)
            self.value['request'] = self.req
            self.verify()

    def in_window(self):
        self.authority()
        window = self.trial_value['windows'][self.number - 1]
        require(r.timestamp(window['start']) <= time.time() < r.timestamp(window['end']))

    def publish(self):
        self.authority()
        super().publish()

    def finish_preparation(self, prepared):
        self.record('preparation.json', prepared)
        if prepared['status'] in ('quiet', 'backpressure'):
            self.persist(status=prepared['status'])
        else:
            super().finish_preparation(prepared)

    def acknowledge(self, cm, command):
        self.authority()
        selected_origin = authenticate(self.runner, cm, self.author)
        if cm['id'] not in self.journal['consumed']:
            self.journal['consumed'].append(cm['id'])
            self.persist()
        selected_pin = command['acknowledgement']
        ack = io.decode(fetch(self.runner, selected_pin))
        keys(ack, 'version phase slot selection binding recipient_chat ingestion_reference observed_at publication')
        require(type(ack['version']) is int and ack['version'] == 1 and ack['phase'] == PHASE
                and type(ack['slot']) is int and ack['slot'] == self.number and ack['selection'] == self.pin
                and ack['binding'] == self.state['attempt'] and ack['publication'] == self.state['publication']
                and ack['recipient_chat'] == CHAT)
        c.identifier(ack['ingestion_reference']); c.stamp(ack['observed_at'])
        require(self.state['details']['publication_observed_at'] <= ack['observed_at'] <= r.timestamp(cm['created_at'])
                and r.timestamp(cm['created_at']) <= time.time() + 300)
        evidence = dict(origin=selected_origin, pin=selected_pin, selection=ack)
        require(self.state['acknowledgement'] is None or self.state['acknowledgement'] == evidence)
        self.record('acknowledgement.json', evidence)
        self.persist(acknowledgement=evidence)
        receipt = dict(version=1, kind='recipient', owner=self.author, issuer=CHAT,
                       binding=self.state['attempt'], observed_at=ack['observed_at'], reference=ack['ingestion_reference'])
        self.install_receipt('recipient', receipt)
        owner.receipt(self.req, 'recipient', 'recipient')
        result = owner.archive(self.req)
        require(result['archived'] is True)
        self.record('archive.json', result)
        self.persist(status='archived')

    def run(self):
        if self.job is None:
            return
        self.guards()
        action, n, command = self.job
        if action == 'activate':
            with self.credentials():
                self.activate()
            return
        self.verify()
        phase_root = Path(self.trial_value['storage']['path']) / PHASE
        with owner.exact_directory(phase_root) as fd:
            require(owner.private_read(fd, 'selection.json', r.LIMIT) == self.raw_selection)
            authorization = io.decode(owner.private_read(fd, 'authorization.json', r.LIMIT))
        keys(authorization, 'origin selection claim')
        require(authorization['origin'] == self.start_origin and authorization['selection'] == self.pin
                and authorization['claim'].get('ref') == CLAIM
                and authorization['claim'].get('object', {}).get('sha') == self.value['reviewed_revision'])
        claim = self.runner.api(f'repos/{r.REPOSITORY}/git/ref/' + CLAIM.removeprefix('refs/'))
        require(claim.get('ref') == CLAIM and claim.get('object', {}).get('sha') == self.value['reviewed_revision'])
        if action in ('acquire', 'missed'):
            self.slot(n, missed=action == 'missed')
            return
        cm, cmd = command
        authenticate(self.runner, cm, self.author)
        self.slot(n)
        if action == 'reconcile':
            if cm['id'] not in self.journal['consumed']:
                self.journal['consumed'].append(cm['id'])
                self.persist(reconciled=cm['id'])
            self.reconcile()
        else:
            self.acknowledge(cm, cmd)


def operate(runner, issue, selected, login):
    try:
        Trial(runner, issue, selected, login).run()
    except (OSError, ValueError, PolicyError, KeyError, TypeError, AttributeError,
            RecursionError, subprocess.SubprocessError):
        raise PolicyError('seven_day_reporting_needs_owner_review') from None
