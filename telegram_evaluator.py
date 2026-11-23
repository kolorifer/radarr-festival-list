"""Bounded calls to the seedbox movie evaluator and safe presentation of its replies."""
import http.client
import json
import queue
import re
import socket
import threading
import time

from private_text import redact_text, sanitize


MAX_REPLY = 128 * 1024
EVALUATION_LIMIT_SECONDS = 80
_SLOTS = threading.BoundedSemaphore(16)
_QUEUE = queue.SimpleQueue()
_START_LOCK = threading.Lock()
_THREADS = 0
SECRET_TEXT = re.compile(
    r'(?i)\b(?:authorization|cookie|set-cookie)["\']?\s*[:=]\s*[^\r\n]+'
    r'|\b(?:api[_ -]?key|token|passkey|password|secret)["\']?\s*[:=]\s*(?:"(?:\\.|[^"\\])*"|[^\s,;]+)'
)


def reserve():
    """Reserve a bounded in-process slot without delaying the intake thread."""
    global _THREADS
    if not _SLOTS.acquire(blocking=False):
        return False
    try:
        with _START_LOCK:
            while _THREADS < 2:
                threading.Thread(target=_run,name='telegram-evaluator',daemon=True).start()
                _THREADS += 1
    except (RuntimeError,OSError):
        release()
        return False
    return True


def release():
    _SLOTS.release()


def _run():
    while True:
        name, deliver = _QUEUE.get()
        try:
            try:
                result = evaluation(name)
            except Exception:
                result = 'Evaluator failed before a complete reply was available.'
            deliver(result)
        except Exception:
            # Nothing from exceptions, wire content or private IDs belongs in logs.
            print('telegram_evaluator delivery_failed', flush=True)
        finally:
            release()


def submit(name, deliver):
    """Transfer an already reserved slot to the two actor-local daemon threads."""
    _QUEUE.put((name,deliver))


def _post(path, payload, timeout):
    """Use direct loopback only. No redirects, proxy, automatic retry or credentials."""
    deadline = time.monotonic() + timeout
    connection = http.client.HTTPConnection('127.0.0.1', 40716, timeout=timeout)
    expired = threading.Event()
    alarm = None
    try:
        connection.connect()
        transport = connection.sock

        def interrupt():
            expired.set()
            try:
                transport.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

        alarm = threading.Timer(max(0, deadline-time.monotonic()), interrupt)
        alarm.daemon = True
        alarm.start()
        raw = json.dumps(payload, ensure_ascii=True).encode('ascii')
        connection.request('POST', path, body=raw, headers={'Content-Type':'application/json',
                                                           'Accept':'application/json'})
        with connection.getresponse() as response:
            content = response.read(MAX_REPLY + 1)
            if expired.is_set() or time.monotonic() >= deadline:
                raise TimeoutError
            if len(content) <= MAX_REPLY and response.length not in (None, 0):
                raise http.client.IncompleteRead(content, response.length)
            return response.status, content
    except (OSError, http.client.HTTPException) as error:
        if expired.is_set() or isinstance(error, TimeoutError):
            raise TimeoutError from None
        raise
    finally:
        if alarm is not None:
            alarm.cancel()
        connection.close()


def _safe_text(text):
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]',
                  lambda match: f'\\u{ord(match[0]):04x}', text)
    return redact_text(SECRET_TEXT.sub('[redacted credential]', text)).encode(
        'utf-8', errors='backslashreplace').decode('utf-8')


def _clean_strings(value):
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            label = _safe_text(key)
            unique = label
            number = 1
            while unique in cleaned:
                number += 1
                unique = f'{label} [{number}]'
            cleaned[unique] = _clean_strings(item)
        return cleaned
    if isinstance(value, list):
        return [_clean_strings(item) for item in value]
    return _safe_text(value) if isinstance(value, str) else value


def _pretty(value):
    parts = []
    size = 0
    for part in json.JSONEncoder(ensure_ascii=False, indent=2).iterencode(value):
        size += len(part)
        if size > 4 * MAX_REPLY:
            return json.dumps(value, ensure_ascii=False, separators=(',', ':'))
        parts.append(part)
    return ''.join(parts)


def evaluation(release_name):
    """Return a complete readable result or a bounded explanatory error."""
    try:
        status, raw = _post('/evaluate', {'raw_text':release_name}, EVALUATION_LIMIT_SECONDS)
    except TimeoutError:
        return f'Evaluator timed out after {EVALUATION_LIMIT_SECONDS} seconds.'
    except (OSError, http.client.HTTPException, ValueError):
        return 'Evaluator connection failed.'
    heading = 'Evaluator result' if 200 <= status < 300 else f'Evaluator error (HTTP {status})'
    if len(raw) > MAX_REPLY:
        return f'{heading}: response exceeded the {MAX_REPLY}-byte safety limit.'
    if not raw:
        return f'{heading}: empty response.'
    try:
        body = _pretty(_clean_strings(sanitize(json.loads(raw))))
    except (ValueError, TypeError, RecursionError):
        body = _safe_text(raw.decode('utf-8', errors='replace'))
        if 200 <= status < 300:
            heading = 'Evaluator error (response was not valid JSON)'
    return heading + '\n' + body


def watched_feedback(movie):
    """One best-effort submission of the already approved Radarr identity."""
    tmdb = movie.get('tmdb_id')
    imdb = movie.get('imdb_id')
    title = movie.get('title')
    if (type(tmdb) not in (str,int) or not re.fullmatch(r'[1-9][0-9]{0,9}',str(tmdb))
            or not isinstance(imdb,str) or not re.fullmatch(r'tt[0-9]{7,12}',imdb)
            or not isinstance(title,str) or not title.strip()):
        return 'identity_incomplete'
    try:
        status, _ = _post('/feedback', {
            'imdb_id':imdb, 'tmdb_id':int(tmdb), 'title':title,
            'decision':'watch', 'note':'Grabbed via Telegram',
        }, 4)
        return 'recorded' if 200 <= status < 300 else 'refused'
    except (OSError, http.client.HTTPException, ValueError):
        return 'unavailable'
