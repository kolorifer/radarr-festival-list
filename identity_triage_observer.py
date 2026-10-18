"""Best-effort bounded outcome hook. Never controls the existing action flow."""
from datetime import datetime, timezone
import http.client
import json
import os
from pathlib import Path
import queue
import re
import threading
import uuid

from identity_triage_intake import CATEGORIES, OUTCOME_STATUSES, REASONS, decode, normalize
from identity_triage_store import private_path

_QUEUE = queue.Queue(maxsize=32)
_LOCK = threading.Lock()
_WORKER = None


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
               'reason': meta.get('identity_reason') if meta.get('identity_reason') in REASONS else 'other'}
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
    return result


def _send(cfg, item):
    connection = http.client.HTTPConnection('127.0.0.1', cfg['port'], timeout=0.5)
    try:
        connection.request('POST', '/v1/outcome', json.dumps(item).encode(),
                           {'Content-Type': 'application/json', 'X-Identity-Intake-Key': cfg['key']})
        response = connection.getresponse()
        if response.status != 200:
            raise ValueError('unavailable')
        response.read(1024)
    finally:
        connection.close()


def _run():
    while True:
        path, item = _QUEUE.get()
        try:
            if os.environ.get('MOVIE_INTEL_TRIAGE_OBSERVER_ENABLED', '0') == '1':
                _send(read_config(path), item)  # current key; queued items cannot bypass revocation
        except Exception:
            print('triage_observer unavailable_delivery_lost', flush=True)
        finally:
            _QUEUE.task_done()


def observe(payload, context):
    global _WORKER
    if os.environ.get('MOVIE_INTEL_TRIAGE_OBSERVER_ENABLED', '0') != '1':
        return
    try:
        path = os.environ['MOVIE_INTEL_TRIAGE_OBSERVER_CONFIG']
        cfg = read_config(path)
        item = envelope(payload, context, cfg['sources'])
        with _LOCK:
            if _WORKER is None or not _WORKER.is_alive():
                _WORKER = threading.Thread(target=_run, daemon=True, name='identity-outcome-observer')
                _WORKER.start()
        _QUEUE.put_nowait((path, item))
    except Exception:
        print('triage_observer unavailable_delivery_lost', flush=True)
