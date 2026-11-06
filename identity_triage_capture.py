"""Default-off, one server-lifetime private capture. No provider or action access."""
import hashlib
import json
import math
import os
import secrets
import stat
import threading
import time

from identity_triage_intake import decode, safe_text
from identity_triage_store import digest

GRANT = 'capture-grant.json'
RESERVATION = 'capture-reservation.json'
BODY = 'capture-body.json'
RECEIPT = 'capture-receipt.json'


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode()


def check(st, directory=False):
    if (st.st_uid != os.getuid() or stat.S_IMODE(st.st_mode) != (0o700 if directory else 0o600)
            or not (stat.S_ISDIR(st.st_mode) if directory else stat.S_ISREG(st.st_mode))
            or (not directory and st.st_nlink != 1)):
        raise ValueError('capture_private_path')


def read_at(parent, name, limit):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    try:
        before = os.fstat(fd); check(before)
        if not 0 < before.st_size <= limit:
            raise ValueError('capture_size')
        raw = os.read(fd, limit + 1)
        after = os.fstat(fd)
        fields = ('st_dev', 'st_ino', 'st_mode', 'st_uid', 'st_gid', 'st_nlink',
                  'st_size', 'st_mtime_ns', 'st_ctime_ns')
        if any(getattr(before, k) != getattr(after, k) for k in fields) or len(raw) != before.st_size:
            raise ValueError('capture_changed')
        return raw
    finally:
        close_capture(fd)


def close_capture(fd):
    try:
        os.close(fd)
    except OSError:
        pass  # Never retry an ambiguous close; ordinary intake is independent.


def write_at(parent, name, raw):
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
    try:
        check(os.fstat(fd))
        with os.fdopen(fd, 'wb', closefd=False) as stream:
            stream.write(raw); stream.flush(); os.fsync(fd)
    finally:
        close_capture(fd)
    os.fsync(parent)


def strict_envelope(raw, record):
    """V1 deliberately excludes torrent evidence and any unrecognized raw field."""
    e = decode(raw)
    if set(e) != {'version', 'event', 'id', 'timestamp', 'data'}:
        return False
    d = e['data']
    if not isinstance(d, dict) or set(d) != {'release', 'indexer', 'outcome'}:
        return False
    if (not isinstance(d['release'], dict) or set(d['release']) - {
            'type', 'protocol', 'implementation', 'title', 'year', 'name',
            'external_id', 'meta_imdb', 'meta_tmdb'} or not isinstance(d['indexer'], dict)
            or set(d['indexer']) != {'identifier', 'name'} or not isinstance(d['outcome'], dict)
            or set(d['outcome']) - {'status', 'category', 'reason', 'asserted_imdb', 'asserted_tmdb'}):
        return False
    # Reject recognized capability syntax; this is not proof that text has no secrets.
    def validate(value):
        if isinstance(value, dict):
            for v in value.values(): validate(v)
        elif isinstance(value, str): safe_text(value, 500)
        elif value is not None and type(value) not in (int, bool):
            raise ValueError('capture_raw_type')
    # UUID/timestamp have their own validated grammar; timestamp contains '+'.
    validate(d)
    return (e['id'] == record['event_id'] and d['outcome'] == record['outcome']
            and e['version'] == '1.0' and e['event'] == 'identity.outcome')


class Capture:
    def __init__(self, directory):
        self.directory = directory
        self.lock = threading.Lock()
        self.burned = False
        self.nonce = None
        self.initialized = False
        self.unavailable = False
        self.phase = 'disabled'

    def _initialize(self):
        if self.initialized:
            return
        self.initialized = True
        try:
            self.nonce = secrets.token_hex(32)
            self.phase = 'ready'
        except Exception:
            self.unavailable = True
            self.phase = 'nonce_unavailable'

    def context(self):
        with self.lock:
            self._initialize()
            return {'capture_nonce': self.nonce, 'capture_consumed': self.burned,
                    'capture_ready': not self.unavailable and not self.burned,
                    'capture_phase': self.phase, 'capture_phase_volatile': True,
                    'capture_grant_validation': 'not_checked_by_health'}

    def prepare(self, c, record, evidence, delivery, raw, cfg, now, validate_config):
        """Called only for a new accepted delivery inside its ingest transaction."""
        if not cfg.get('capture_prepare', False) or not cfg.get('capture_grant_sha256'):
            return None
        with self.lock:
            self._initialize()
            if self.burned or self.unavailable or self.nonce is None:
                return None
            parent = None
            transferred = False
            try:
                if record.get('reason') or not strict_envelope(raw, record):
                    return None
                parent = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
                check(os.fstat(parent), True)
                grant_raw = read_at(parent, GRANT, 4096)
                if hashlib.sha256(grant_raw).hexdigest() != cfg['capture_grant_sha256']:
                    return None
                g = decode(grant_raw)
                if set(g) != {'version', 'nonce', 'source', 'channel', 'filter', 'expires_at',
                              'destination', 'privacy'}:
                    return None
                f = g['filter']; expires = g['expires_at']
                if (g['version'] != 1 or g['nonce'] != self.nonce or g['channel'] != 'outcome'
                        or g['source'] != record['metadata']['source']
                        or g['destination'] != {'body': BODY, 'receipt': RECEIPT}
                        or g['privacy'] != 'private_local_raw_observer_body_no_api_disclosure'
                        or type(expires) not in (int, float) or not math.isfinite(expires)
                        or not now < expires <= now + 3600
                        or not isinstance(f, dict)):
                    return None
                mode = f.get('mode')
                if (mode not in ('first_matching', 'exact_external_id')
                        or set(f) != ({'mode', 'status', 'reason', 'external_id'}
                                      if mode == 'exact_external_id' else {'mode', 'status', 'reason'})):
                    return None
                envelope = decode(raw)
                o = record['outcome']
                if (mode == 'exact_external_id' and (f['external_id'] != envelope['data']['release'].get('external_id')
                        or not isinstance(f['external_id'], str) or not f['external_id'])
                        or f['status'] != o['status'] or f['reason'] != o['reason']
                        or o['status'] not in ('unresolved', 'needs_review')):
                    return None
                observed = record['time']
                if observed is None or observed > now + 300:
                    return None
                event = digest([record['release'], evidence, observed, o])
                latest = c.execute('select id from selection_events where release=? order by observed desc,id limit 1',
                                   (record['release'],)).fetchone()
                row = c.execute('select h.case_key,h.version,h.evidence,h.route,h.correlation,h.material '
                                'from selection_current s join selection_history h on h.version=s.version where s.release=?',
                                (record['release'],)).fetchone()
                if (latest != (event,) or not row or row[2] != evidence or row[3:5] != ('eligible', 'strong_source_id')):
                    return None
                material = json.loads(row[5])
                if material['metadata'] != record['metadata'] or material['outcome'] != o:
                    return None
                receipt = {'version': 1, 'source': g['source'], 'channel': 'outcome',
                           'case_id': row[0], 'case_version': row[1], 'event_id': record['event_id'],
                           'selection_event': event, 'delivery_rowid': delivery, 'evidence_id': evidence,
                           'source_time': observed, 'received_at': now, 'grant_sha256': cfg['capture_grant_sha256'],
                           'body_sha256': hashlib.sha256(raw).hexdigest(), 'body_bytes': len(raw),
                           'privacy': g['privacy'], 'api_disclosure_authorized': False}
                # Burn before ANY durable reservation attempt; never reset, even
                # when reservation/commit/fsync fails. Restart invalidates nonce.
                if not time.time() < expires or not validate_config():
                    return None
                self.burned = True
                self.phase = 'reserving'
                write_at(parent, RESERVATION, encoded(receipt))
                self.phase = 'reserved'
                transferred = True
                return (parent, raw, receipt)
            except Exception:
                self.unavailable = True
                self.phase = 'reservation_failed' if self.burned else 'validation_failed'
                return None  # Capture-only failure must not change ordinary ACK.
            finally:
                if parent is not None and not transferred:
                    close_capture(parent)

    def finish(self, ticket):
        if ticket is None:
            return
        parent, raw, receipt = ticket
        try:
            self.phase = 'writing_body'
            write_at(parent, BODY, raw)
            self.phase = 'writing_receipt'
            write_at(parent, RECEIPT, encoded(receipt))
            self.phase = 'complete'
        except Exception:
            self.phase = 'partial'  # Partial artifacts are terminal; never select a replacement.
        finally:
            close_capture(parent)

    def abandon(self, ticket):
        if ticket is not None:
            self.phase = 'commit_failed_or_interrupted'
            close_capture(ticket[0])
