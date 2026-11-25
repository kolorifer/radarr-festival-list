"""Bounded calls to the seedbox movie evaluator and safe presentation of its replies."""
import http.client
import json
import queue
import re
import socket
import threading
import time
from typing import NamedTuple

from private_text import redact_text, sanitize


MAX_REPLY = 128 * 1024
EVALUATION_LIMIT_SECONDS = 80
_SLOTS = threading.BoundedSemaphore(16)
_QUEUE = queue.SimpleQueue()
_START_LOCK = threading.Lock()
_THREADS = 0
SECRET_TEXT = re.compile(
    r'(?i)\b(?:authorization|cookie|set-cookie)["\']?\s*[:=]\s*[^\r\n]+'
    r'|\bbearer\s+[A-Za-z0-9._~+/-]{8,}=*'
    r'|\b(?:[a-z][a-z0-9_-]{0,127})?(?:api[_ -]?key|token|passkey|password|secret|credential)s?'
    r'["\']?\s*[:=]\s*(?:"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[^\s,;]+)'
)
SECRET_KEY_ENDINGS = ('apikey','token','passkey','password','secret','credential',
                      'authorization','cookie')
PRIVATE_REFERENCE = re.compile(r'(?i)\b(?:[a-z][a-z0-9+.-]*://|magnet:|www\.)\S+')
ANNOUNCE_LANGUAGES = frozenset("""
    arabic cantonese catalan chinese croatian czech danish dutch english estonian
    finnish french german greek hebrew hindi hungarian icelandic indonesian italian japanese
    korean latvian lithuanian mandarin norwegian persian polish portuguese romanian russian
    serbian slovak slovenian spanish swedish tamil thai turkish ukrainian vietnamese
""".split())


class Evaluation(NamedTuple):
    text: str
    proposal: dict | None = None


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
        request, deliver = _QUEUE.get()
        try:
            try:
                result = evaluation(request)
            except Exception:
                result = Evaluation('Evaluator failed before a complete reply was available.')
            deliver(result)
        except Exception:
            # Nothing from exceptions, wire content or private IDs belongs in logs.
            print('telegram_evaluator delivery_failed', flush=True)
        finally:
            release()


def submit(request, deliver):
    """Transfer an already reserved slot to the two actor-local daemon threads."""
    _QUEUE.put((request,deliver))


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
    text = PRIVATE_REFERENCE.sub('[redacted URL]',text)
    return redact_text(SECRET_TEXT.sub('[redacted credential]', text)).encode(
        'utf-8', errors='backslashreplace').decode('utf-8')


def _source_text(value, limit, *, redact=False):
    if not isinstance(value, str):
        return None
    safe = _safe_text(value)
    if not redact and safe != value:
        return None
    return safe.strip()[:limit] or None


def _imdb(value):
    return value if isinstance(value, str) and re.fullmatch(r'tt[0-9]{7,10}',value) else None


def _tmdb(value):
    return int(value) if type(value) in (str,int) and re.fullmatch(r'[1-9][0-9]{0,9}',str(value)) else None


def _year(value):
    if type(value) in (str,int) and re.fullmatch(r'[0-9]{4}',str(value)) and 1888 <= int(value) <= 2100:
        return int(value)
    return None


def _audio_languages(value, *, announced=False):
    if isinstance(value,str):
        value = re.split(r'[,;/]', value)
    if not isinstance(value,list):
        return []
    return list(dict.fromkeys(
        language.title() for item in value[:32] if (language := _source_text(item,64))
        and (not announced or language.casefold() in ANNOUNCE_LANGUAGES)))[:6]


def _nfo_languages(text):
    # Only read explicit language fields within bounded MediaInfo audio sections.
    sections = re.split(
        r'\b(Audio|Text|Video)(?:\s*#\d+)?\s*(?:ID\s*)?:|\bMenu\s+(?=ID\s*:)',
        text, flags=re.I)
    values = []
    for kind, track in zip(sections[1::2],sections[2::2]):
        if not kind or kind.casefold() != 'audio':
            continue
        languages = re.findall(
            r'\bLanguage\s*:\s*([a-zA-Z]+(?:[ -][a-zA-Z]+)*?)(?=\s*\(|\s+\w[\w /()]*\s*:|$)',track)
        if len(languages) == 1:
            values.append(languages[0])
    return _audio_languages(values,announced=True)


def _source_label(release):
    source = _source_text(release.get('source'),128)
    processing = _source_text(release.get('media_processing'),64)
    if source:
        source = ' '.join(source.replace('.',' ').split())
    if source and processing and not re.search(r'(?<!\w)'+re.escape(processing)+r'(?!\w)', source,re.I):
        return source + ' ' + processing
    return source or processing


def evaluation_request(release, indexer, listing=None, *, original=None):
    """Project only observed release facts. Existing listing evidence adds no fetch."""
    from source_identity_guard import nfo_runtime
    from torrent_research_evidence import MAX_TEXT, validate

    name = release.get('name')
    if not isinstance(name,str) or len(name)>4096 or not _source_text(name,4096):
        return None
    info = dict((original or {}).get('torrent_info', {}))
    listing = listing or {}
    evidence = listing.get('torrent_evidence')
    try:
        evidence = validate(evidence)
    except (TypeError,ValueError):
        evidence = None

    runtime = release.get('runtime_minutes')
    if type(runtime) is not int or not 1 <= runtime <= 1440:
        runtime = info.get('runtime_minutes')
        minutes = nfo_runtime(listing) if evidence else None
        if minutes is not None and minutes >= 1:
            runtime = round(minutes)
    nfo = evidence['nfo']['text'] if evidence else release.get('nfo_text')
    audio = (_nfo_languages(nfo) if isinstance(nfo,str) and len(nfo) < MAX_TEXT else []) or (
        _audio_languages(release.get('audio_languages'),announced=True)
        or _audio_languages(release.get('language'),announced=True) or info.get('audio_languages'))
    size = release.get('size')
    freeleech = release.get('freeleech')
    if type(freeleech) is not bool:
        freeleech = listing.get('freeleech')
    imdb = _imdb(release.get('meta_imdb'))
    listing_imdb = _imdb(listing.get('imdb_id'))

    fields = {
        'indexer': _source_text(indexer.get('name'),128) or _source_text(indexer.get('identifier'),128),
        'category': _source_text(release.get('category'),128),
        'imdb_id': imdb or listing_imdb,
        'tmdb_id': _tmdb(release.get('meta_tmdb')),
        'runtime_minutes': runtime,
        'audio_languages': audio,
        'resolution': _source_text(release.get('resolution'),128),
        'source': _source_label(release),
        'size_gb': size / 10**9 if type(size) is int and 0 < size < 2**63 else None,
        'freeleech': freeleech if type(freeleech) is bool else None,
        'description': _source_text(evidence['description']['text'] if evidence else release.get('description'),
                                    3000, redact=True),
        'nfo_text': _source_text(nfo,3000,redact=True),
    }
    info.update({key: value for key, value in fields.items() if value is not None})
    if imdb and listing_imdb and imdb != listing_imdb:
        # The evaluator accepts a single tracker IMDb. Do not select a side.
        info.pop('imdb_id',None)
    title = _source_text(release.get('title'),250)
    year = _year(release.get('year'))
    request = {'raw_text':name}
    if title:
        request['hint_title'] = title
    if year:
        request['hint_year'] = year
    if info:
        request['torrent_info'] = info
    if info or title or year:
        # The evaluator's early cache can omit newly supplied evidence and hints.
        request['force_refresh'] = True
    return request


def _proposal(value):
    if not isinstance(value,dict):
        return None
    title = _source_text(value.get('canonical_title'),250)
    year = _year(value.get('year'))
    confidence = value.get('match_confidence')
    if not title or not year or confidence not in ('high','medium','low'):
        return None
    return {'title':title, 'year':year, 'confidence':confidence,
            'imdb_id':_imdb(value.get('imdb_id')), 'tmdb_id':_tmdb(value.get('tmdb_id')),
            'reason':_source_text(value.get('disambiguation_note'),500,redact=True)}


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
            normalized = re.sub(r'[^a-z0-9]','',key.casefold()).removesuffix('s')
            cleaned[unique] = ('[redacted]' if normalized.endswith(SECRET_KEY_ENDINGS)
                               else _clean_strings(item))
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


def evaluation(request):
    """Return a complete readable result or a bounded explanatory error."""
    try:
        status, raw = _post('/evaluate', request, EVALUATION_LIMIT_SECONDS)
    except TimeoutError:
        return Evaluation(f'Evaluator timed out after {EVALUATION_LIMIT_SECONDS} seconds.')
    except (OSError, http.client.HTTPException, ValueError):
        return Evaluation('Evaluator connection failed.')
    heading = 'Evaluator result' if 200 <= status < 300 else f'Evaluator error (HTTP {status})'
    if len(raw) > MAX_REPLY:
        return Evaluation(f'{heading}: response exceeded the {MAX_REPLY}-byte safety limit.')
    if not raw:
        return Evaluation(f'{heading}: empty response.')
    proposal = None
    try:
        parsed = _clean_strings(sanitize(json.loads(raw)))
        body = _pretty(parsed)
        if 200 <= status < 300 and isinstance(parsed,dict):
            proposal = _proposal(parsed.get('identification'))
    except (ValueError, TypeError, RecursionError):
        body = _safe_text(raw.decode('utf-8', errors='replace'))
        if 200 <= status < 300:
            heading = 'Evaluator error (response was not valid JSON)'
    return Evaluation(heading + '\n' + body, proposal)


def watched_feedback(movie, *, decision='watch', note='Grabbed via Telegram', require_saved_ack=False):
    """One best-effort submission of the already approved Radarr identity."""
    tmdb = movie.get('tmdb_id')
    imdb = movie.get('imdb_id')
    title = movie.get('title')
    if (type(tmdb) not in (str,int) or not re.fullmatch(r'[1-9][0-9]{0,9}',str(tmdb))
            or not isinstance(imdb,str) or not re.fullmatch(r'tt[0-9]{7,12}',imdb)
            or not isinstance(title,str) or not title.strip()):
        return 'identity_incomplete'
    try:
        status, raw = _post('/feedback', {
            'imdb_id':imdb, 'tmdb_id':int(tmdb), 'title':title,
            'decision':decision, 'note':note,
        }, 4)
        if require_saved_ack and 200 <= status < 300:
            if status != 200 or len(raw) > MAX_REPLY:
                return 'unconfirmed'
            try:
                ack = json.loads(raw)
            except (ValueError, RecursionError):
                return 'unconfirmed'
            if (not isinstance(ack,dict) or ack.get('status') != 'saved'
                    or ack.get('decision') != decision
                    or type(ack.get('total_feedback')) is not int or ack['total_feedback'] < 1):
                return 'unconfirmed'
        return 'recorded' if 200 <= status < 300 else 'refused'
    except (OSError, http.client.HTTPException, ValueError):
        return 'unavailable'
