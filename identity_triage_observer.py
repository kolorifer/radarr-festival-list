"""Best-effort bounded outcome hook. Never controls the existing action flow."""
from datetime import datetime, timezone
import http.client
import json
import os
from pathlib import Path
import queue
import re
import sqlite3
import threading
import uuid
import time
from collections import Counter
from identity_outcome_outbox import Outbox

from identity_triage_intake import CATEGORIES, OUTCOME_STATUSES, REASONS, decode, normalize
from identity_triage_store import private_path

_QUEUE = queue.Queue(maxsize=32)
_LOCK = threading.Lock()
_WORKER = None
_STATS = Counter()
_STATS_LOCK = threading.Lock()

# The collector permits a two-second writer wait and has a five-second hard
# connection lifetime. Let it finish or close before the observer gives up.
# This is a finite socket-operation timeout, not a total delivery deadline.
DELIVERY_TIMEOUT = 6.0


class CollectorHTTPError(ValueError):
    def __init__(self, status):
        super().__init__('collector_http_status')
        self.status = status if type(status) is int and 100 <= status <= 599 else None


def failure_reason(error):
    """Fixed categories only: never stringify an exception or its arguments."""
    if isinstance(error, CollectorHTTPError):
        return 'http_status'
    if isinstance(error, TimeoutError):
        return 'timeout'
    if isinstance(error, ConnectionRefusedError):
        return 'connection_refused'
    if isinstance(error, (ConnectionResetError, ConnectionAbortedError, BrokenPipeError)):
        return 'connection_lost'
    if isinstance(error, http.client.HTTPException):
        return 'http_protocol'
    if isinstance(error, sqlite3.Error):
        primary = getattr(error, 'sqlite_errorcode', 0) & 255
        return {sqlite3.SQLITE_BUSY:'sqlite_busy', sqlite3.SQLITE_LOCKED:'sqlite_locked',
                sqlite3.SQLITE_FULL:'sqlite_full', sqlite3.SQLITE_IOERR:'sqlite_io',
                sqlite3.SQLITE_READONLY:'sqlite_readonly'}.get(primary, 'sqlite_other')
    if isinstance(error, PermissionError):
        return 'permission'
    if isinstance(error, FileNotFoundError):
        return 'path_missing'
    if isinstance(error, OSError):
        return 'os_other'
    if isinstance(error, ValueError):
        return 'validation'
    if isinstance(error, queue.Full):
        return 'queue_full'
    return 'unexpected'


def read_config(path):
    p = private_path(Path(path))
    private_path(p.parent, True)
    if p.stat().st_size > 8192:
        raise ValueError('configuration')
    cfg = decode(p.read_bytes())
    if (set(cfg) != {'port', 'key', 'sources'} or type(cfg['port']) != int or not 1024 <= cfg['port'] <= 65535
            or not isinstance(cfg['key'], str) or not re.fullmatch('[A-Za-z0-9_-]{43,128}', cfg['key'])
            or not isinstance(cfg['sources'], dict) or not 1 <= len(cfg['sources']) <= 32
            or any(not re.fullmatch('[a-z0-9_-]{1,64}', k) or not isinstance(v, str)
                   or not re.fullmatch('[A-Za-z0-9 ._-]{1,80}', v) for k, v in cfg['sources'].items())):
        raise ValueError('configuration')
    return cfg


def envelope(payload, context, sources):
    data = payload.get('data') or {}
    release = data.get('release') or {}
    meta = context.get('meta') or {}
    status = meta.get('identity_status') or ('legacy_resolved' if meta else 'unresolved')
    if context.get('category') in {'quality', 'existing', 'not_upgrade'}:
        status = 'skipped_routine'
    outcome = {'status': status if status in OUTCOME_STATUSES else 'unresolved',
               'category': context.get('category') if context.get('category') in CATEGORIES else 'other',
               'reason': (context.get('identity_observation') or {}).get('reason',meta.get('identity_reason')) if (context.get('identity_observation') or {}).get('reason',meta.get('identity_reason')) in REASONS else ('resolved' if status=='legacy_resolved' else 'other')}
    for key, value in (('asserted_imdb',(context.get('identity_observation') or {}).get('asserted_imdb',meta.get('imdb_id'))),('asserted_tmdb',(context.get('identity_observation') or {}).get('asserted_tmdb',meta.get('tmdb_id')))):
        if value is not None:outcome[key]=value
    evidence = (context.get('identity_observation') or {}).get('torrent_evidence')
    if evidence is not None:
        from torrent_research_evidence import validate
        outcome['torrent_evidence'] = validate(evidence)
    result = {'version': '1.0', 'event': 'identity.outcome', 'id': str(uuid.uuid4()),
              'timestamp': datetime.now(timezone.utc).isoformat(),
              'data': {'release': {k: release[k] for k in ('type', 'protocol', 'implementation', 'title', 'year', 'name', 'external_id', 'meta_imdb', 'meta_tmdb') if k in release},
                       'indexer': {k: (data.get('indexer') or {}).get(k) for k in ('name', 'identifier')},
                       'outcome': outcome}}
    # Normalize before crossing the observation boundary: no hostile partial text
    # or raw external IDs travel to a second process if quarantine is required.
    checked = normalize(result, sources, 'outcome')
    if checked.get('reason'):
        result['data']['release'] = {'type': 'movie'}
        result['data']['outcome'] = {'status':'unresolved','category':'other','reason':'invalid_metadata'}
    return result


def _send(cfg, item):
    connection = http.client.HTTPConnection('127.0.0.1', cfg['port'], timeout=DELIVERY_TIMEOUT)
    try:
        connection.request('POST', '/v1/outcome', json.dumps(item).encode(),
                           {'Content-Type': 'application/json', 'X-Identity-Intake-Key': cfg['key']})
        response = connection.getresponse()
        if response.status != 200:
            raise CollectorHTTPError(response.status)
        response.read(1024)
    finally:
        connection.close()


def count(name, *, error=None, stage=None, started=None, http_status=None):
    with _STATS_LOCK:_STATS[name]+=1
    if name in {'queue_full','prepersist_failed','delivery_failed','configuration_failed'}:
        message = 'triage_observer ' + name
        if error is not None:
            stages = {'configuration','send','ack','retry_state','initialize','persist',
                      'poll','metrics','projection','enqueue'}
            stage = stage if stage in stages else 'unknown'
            # Bound timing output and allow only a numeric HTTP status. No URL,
            # UUID, release, header, response body, path or exception text.
            elapsed_ms = min(60_000, max(0, int((time.monotonic()-started)*1000))) if started is not None else 0
            if isinstance(error, CollectorHTTPError):
                http_status = error.status
            status = str(http_status) if type(http_status) is int and 100 <= http_status <= 599 else 'none'
            message += f' stage={stage} reason={failure_reason(error)} http_status={status} elapsed_ms={elapsed_ms}'
        print(message,flush=True)


def metrics():
    with _STATS_LOCK:
        return dict(_STATS)|{'memory_pending':_QUEUE.qsize(),'prepersist_crash_window':'unknown_on_restart'}


def _deliver_pending(outbox, pending):
    key, item, attempts = pending
    started = time.monotonic()
    stage, status = 'configuration', None
    try:
        cfg = read_config(os.environ['MOVIE_INTEL_TRIAGE_OBSERVER_CONFIG'])
        if os.environ.get('MOVIE_INTEL_TRIAGE_OBSERVER_ENABLED','0') == '1':
            stage = 'send'
            _send(cfg, item)
            stage, status = 'ack', 200
            outbox.ack(key)
            count('delivered')
    except Exception as exc:
        # Preserve the original failure even if recording retry state also fails.
        count('delivery_failed', error=exc, stage=stage, started=started, http_status=status)
        outbox.failed(key, attempts)


def _run():
    outbox=None;last_report=0
    while True:
        started = time.monotonic()
        stage = 'initialize'
        try:
            if os.environ.get('MOVIE_INTEL_TRIAGE_OBSERVER_ENABLED','0')!='1':
                time.sleep(1);continue
            if outbox is None:
                outbox=Outbox(Path.home().resolve()/'.local/state/movie-identity-outcomes')
            try:item=_QUEUE.get(timeout=.25)
            except queue.Empty:item=None
            if item is not None:
                try:outbox.put(item);count('persisted')
                except Exception as exc:
                    count('prepersist_failed', error=exc, stage='persist', started=started)
                    try:_QUEUE.put_nowait(item)
                    except queue.Full:count('queue_full')
                finally:_QUEUE.task_done()
            stage = 'poll'
            pending=outbox.next()
            if pending:
                stage = 'retry_state'  # Only retry bookkeeping escapes the helper.
                _deliver_pending(outbox, pending)
            stage = 'metrics'
            if time.monotonic()-last_report>=60:
                print('triage_observer metrics '+json.dumps({'process':metrics(),'durable':outbox.metrics()},sort_keys=True),flush=True)
                last_report=time.monotonic()
        except Exception as exc:
            count('prepersist_failed', error=exc, stage=stage, started=started)
            outbox=None;time.sleep(2)


def start():
    global _WORKER
    if os.environ.get('MOVIE_INTEL_TRIAGE_OBSERVER_ENABLED','0')!='1':return
    started = time.monotonic()
    try:
        read_config(os.environ['MOVIE_INTEL_TRIAGE_OBSERVER_CONFIG'])
        with _LOCK:
            if _WORKER is None or not _WORKER.is_alive():
                _WORKER=threading.Thread(target=_run,daemon=True,name='identity-outcome-observer')
                _WORKER.start()
                print('triage_observer started prepersist_window_uncertain',flush=True)
    except Exception as exc:count('configuration_failed', error=exc, stage='configuration', started=started)


def observe(payload,context):
    if os.environ.get('MOVIE_INTEL_TRIAGE_OBSERVER_ENABLED','0')!='1':return
    started = time.monotonic()
    stage = 'configuration'
    try:
        cfg=read_config(os.environ['MOVIE_INTEL_TRIAGE_OBSERVER_CONFIG'])
        stage = 'projection'
        item=envelope(payload,context,cfg['sources'])
        if _WORKER is None or not _WORKER.is_alive():start()
        stage = 'enqueue'
        _QUEUE.put_nowait(item);count('queued')
    except queue.Full as exc:count('queue_full', error=exc, stage=stage, started=started)
    except Exception as exc:count('configuration_failed', error=exc, stage=stage, started=started)
