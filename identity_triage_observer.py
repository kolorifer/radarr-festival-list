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


def count(name):
    with _STATS_LOCK:_STATS[name]+=1
    if name in {'queue_full','prepersist_failed','delivery_failed','configuration_failed'}:
        print('triage_observer '+name,flush=True)


def metrics():
    with _STATS_LOCK:
        return dict(_STATS)|{'memory_pending':_QUEUE.qsize(),'prepersist_crash_window':'unknown_on_restart'}


def _run():
    outbox=None;last_report=0
    while True:
        try:
            if os.environ.get('MOVIE_INTEL_TRIAGE_OBSERVER_ENABLED','0')!='1':
                time.sleep(1);continue
            if outbox is None:
                outbox=Outbox(Path.home().resolve()/'.local/state/movie-identity-outcomes')
            try:item=_QUEUE.get(timeout=.25)
            except queue.Empty:item=None
            if item is not None:
                try:outbox.put(item);count('persisted')
                except Exception:
                    count('prepersist_failed')
                    try:_QUEUE.put_nowait(item)
                    except queue.Full:count('queue_full')
                finally:_QUEUE.task_done()
            pending=outbox.next()
            if pending:
                key,item,attempts=pending
                try:
                    cfg=read_config(os.environ['MOVIE_INTEL_TRIAGE_OBSERVER_CONFIG'])
                    if os.environ.get('MOVIE_INTEL_TRIAGE_OBSERVER_ENABLED','0')=='1':
                        _send(cfg,item);outbox.ack(key);count('delivered')
                except Exception:
                    outbox.failed(key,attempts);count('delivery_failed')
            if time.monotonic()-last_report>=60:
                print('triage_observer metrics '+json.dumps({'process':metrics(),'durable':outbox.metrics()},sort_keys=True),flush=True)
                last_report=time.monotonic()
        except Exception:
            count('prepersist_failed');outbox=None;time.sleep(2)


def start():
    global _WORKER
    if os.environ.get('MOVIE_INTEL_TRIAGE_OBSERVER_ENABLED','0')!='1':return
    try:
        read_config(os.environ['MOVIE_INTEL_TRIAGE_OBSERVER_CONFIG'])
        with _LOCK:
            if _WORKER is None or not _WORKER.is_alive():
                _WORKER=threading.Thread(target=_run,daemon=True,name='identity-outcome-observer')
                _WORKER.start()
                print('triage_observer started prepersist_window_uncertain',flush=True)
    except Exception:count('configuration_failed')


def observe(payload,context):
    if os.environ.get('MOVIE_INTEL_TRIAGE_OBSERVER_ENABLED','0')!='1':return
    try:
        cfg=read_config(os.environ['MOVIE_INTEL_TRIAGE_OBSERVER_CONFIG'])
        item=envelope(payload,context,cfg['sources'])
        if _WORKER is None or not _WORKER.is_alive():start()
        _QUEUE.put_nowait(item);count('queued')
    except queue.Full:count('queue_full')
    except Exception:count('configuration_failed')
