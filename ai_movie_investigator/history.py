"""Owner-only, bounded append history. No access to any existing service database.

The selected directory must already exist with mode 0700. Locked, no-follow
descriptor access and namespace identity checks guard every read and append.
An incomplete tail fails closed; recovery never replays a model reservation.
"""
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import stat
import time

from .contracts import Refusal, decode, digest, encoded, require, stamp

MAX_HISTORY = 16 * 1024 * 1024
MAX_RECORDS = 10000
FILENAME = 'ai-investigator-v1.jsonl'


def checked(info, directory=False):
    require((stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)) and
            info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) == (0o700 if directory else 0o600)
            and (directory or info.st_nlink == 1), 'unsafe_history_permissions')


class History:
    def __init__(self, directory, clock=time.time):
        self.directory = Path(directory)
        require(self.directory.is_absolute() and self.directory.resolve(strict=True) == self.directory,
                'unsafe_history_path')
        checked(self.directory.lstat(), True)
        self.identity = self.directory.stat().st_dev, self.directory.stat().st_ino
        self.clock = clock

    @contextmanager
    def transaction(self, *, write=False):
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        dfd = os.open(self.directory, flags)
        fd = None
        try:
            ds = os.fstat(dfd)
            checked(ds, True)
            require((ds.st_dev, ds.st_ino) == self.identity, 'history_directory_changed')
            open_flags = (os.O_RDWR | os.O_APPEND) if write else os.O_RDONLY
            try:
                if write:
                    try:
                        fd = os.open(FILENAME, open_flags | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_NONBLOCK,
                                     0o600, dir_fd=dfd)
                    except FileExistsError:
                        fd = os.open(FILENAME, open_flags | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=dfd)
                else:
                    fd = os.open(FILENAME, open_flags | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=dfd)
            except FileNotFoundError:
                if write:
                    raise
                yield [], None
                return
            lock_deadline = time.monotonic() + 2
            while True:
                try:
                    fcntl.flock(fd, (fcntl.LOCK_EX if write else fcntl.LOCK_SH) | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    require(time.monotonic() < lock_deadline, 'history_busy')
                    time.sleep(.01)

            def check():
                require(self.directory.resolve(strict=True) == self.directory, 'history_directory_changed')
                current = self.directory.lstat()
                checked(current, True)
                require((current.st_dev, current.st_ino) == self.identity, 'history_directory_changed')
                s = os.fstat(fd)
                checked(s)
                ns = os.stat(FILENAME, dir_fd=dfd, follow_symlinks=False)
                checked(ns)
                require((s.st_dev, s.st_ino) == (ns.st_dev, ns.st_ino), 'history_file_changed')
                require(s.st_size <= MAX_HISTORY, 'history_capacity')

            check()
            raw = bytearray()
            while True:
                chunk = os.read(fd, min(65536, MAX_HISTORY + 1 - len(raw)))
                if not chunk:
                    break
                raw.extend(chunk)
                require(len(raw) <= MAX_HISTORY, 'history_capacity')
            require(not raw or raw.endswith(b'\n'), 'history_incomplete_tail')
            rows = [decode(bytes(line), 196608) for line in raw.splitlines()]
            require(len(rows) <= MAX_RECORDS, 'history_capacity')
            previous = None
            for index, row in enumerate(rows, 1):
                require(isinstance(row, dict) and set(row) == {'sequence', 'previous', 'event', 'hash'}, 'history_schema')
                require(row['sequence'] == index and row['previous'] == previous
                        and row['hash'] == digest({k: v for k, v in row.items() if k != 'hash'}), 'history_integrity')
                previous = row['hash']
            events = [r['event'] for r in rows]

            def append(event):
                nonlocal previous
                require(write, 'history_read_only')
                check()
                require(len(events) < MAX_RECORDS, 'history_capacity')
                record = dict(sequence=len(events) + 1, previous=previous, event=event)
                record['hash'] = digest(record)
                body = encoded(record) + b'\n'
                require(len(body) <= 196608 and os.fstat(fd).st_size + len(body) <= MAX_HISTORY, 'history_capacity')
                view = memoryview(body)
                while view:
                    n = os.write(fd, view)
                    require(n > 0, 'history_write_failed')
                    view = view[n:]
                os.fsync(fd)
                os.fsync(dfd)
                check()
                events.append(event)
                previous = record['hash']

            yield events, append
        finally:
            if fd is not None:
                os.close(fd)
            os.close(dfd)

    def read(self):
        with self.transaction() as (events, _):
            return events

    def intake(self, packet):
        # Deep-copy before taking the lock so a caller cannot mutate stored input.
        packet = decode(encoded(packet), 49152)
        from .contracts import validate_packet
        validate_packet(packet)
        job = digest(packet)
        now = stamp(self.clock())
        with self.transaction(write=True) as (events, append):
            intakes = [e for e in events if e['type'] == 'intake']
            if any(e['job'] == job for e in intakes):
                return job, 'exact_redelivery'
            for old in intakes:
                p = old['packet']
                if (p['event'] and packet['event'] and p['binding']['source'] == packet['binding']['source']
                        and p['event']['id'] == packet['event']['id']):
                    require(p['event'] == packet['event'], 'immutable_event_conflict')
            same = [e for e in intakes if e['packet']['binding']['case_id'] == packet['binding']['case_id']]
            reason = 'first_captured_outcome'
            if same:
                prior = same[-1]['packet']
                def material(p):
                    p = json.loads(encoded(p))
                    for evidence in p['evidence']:
                        evidence.pop('observed_at')
                        evidence.pop('expires_at')
                    return p
                if material(prior) == material(packet):
                    # A refreshed clock is retained, never a new investigation
                    # opportunity or revival of expired evidence/approval.
                    old_job = same[-1]['job']
                    if not any(e['type'] == 'retained_observation' and e['input_hash'] == job for e in events):
                        append(dict(type='retained_observation', at=now, job=old_job, input_hash=job,
                                    packet=packet, reason='freshness_only_no_new_job'))
                    return old_job, 'freshness_only_no_new_job'
                if prior['binding']['occurrence'] != packet['binding']['occurrence']:
                    reason = 'distinct_delivery'
                elif prior['evidence'] != packet['evidence']:
                    reason = 'retained_evidence_changed'
                elif prior['binding'] != packet['binding']:
                    reason = 'case_version_changed'
                else:
                    reason = 'decision_history_changed'
                # Prevent rollback of an issuer's versioned history or revival
                # of a revoked/superseded decision on an otherwise same scope.
                old_decisions = {d['id']: d for e in same for d in e['packet']['decisions']}
                new_decisions = {d['id']: d for d in packet['decisions']}
                for key, old in old_decisions.items():
                    require(key in new_decisions, 'decision_history_omitted')
                    new = new_decisions[key]
                    require(new['revision'] >= old['revision'] and
                            (new == old or new['revision'] > old['revision']), 'decision_revision_conflict')
                    require(old['revoked_at'] is None or new['revoked_at'] == old['revoked_at'], 'decision_revocation_rollback')
            append(dict(type='intake', at=now, job=job, packet=packet, reason=reason))
            return job, reason

    def start(self, job, invocation, runtime):
        with self.transaction(write=True) as (events, append):
            require(any(e['type'] == 'intake' and e['job'] == job for e in events), 'unknown_job')
            require(not any(e['type'] == 'invocation' and (e['job'] == job or e['invocation'] == invocation)
                            for e in events), 'invocation_already_consumed')
            append(dict(type='invocation', job=job, invocation=invocation, at=stamp(self.clock()), runtime=runtime))

    def record(self, event, *, guard=None):
        with self.transaction(write=True) as (events, append):
            job = event['job']
            require(any(e['type'] == 'invocation' and e['job'] == job for e in events), 'invocation_missing')
            require(not any(e['type'] == 'result' and e['job'] == job for e in events), 'result_immutable')
            if event['type'] == 'model_reserved':
                require(sum(e['type'] == 'model_reserved' and e['job'] == job for e in events) < 2, 'model_call_budget')
            if event['type'] == 'model_reserved' or event['type'] == 'result' and event.get('status') == 'supported_candidate':
                original = next(e for e in events if e['type'] == 'intake' and e['job'] == job)
                current = [e for e in events if e['type'] == 'intake' and
                           e['packet']['binding']['case_id'] == original['packet']['binding']['case_id']][-1]
                require(current['job'] == job, 'selected_case_superseded')
            if event['type'] == 'lookup':
                require(sum(e['type'] == 'lookup' and e['job'] == job for e in events) < 5, 'lookup_budget')
            if guard is not None:
                guard()  # Validate time/policy inside the same currentness lock.
            append(dict(event, at=stamp(self.clock())))
