"""Shadow-only evidence extraction. No actor changes or acquisition capabilities."""
import hashlib
import re
import unicodedata
from .scorer import evaluate

MAX_NFO = 65536


def normalized(value):
    return ''.join(c for c in unicodedata.normalize('NFKC', value).casefold() if c.isalnum())


def nfo_facts(value):
    """Parse the complete bounded NFO, never a truncated display projection."""
    result = {'runtime': None, 'audio_languages': [], 'audio_track_details': [], 'gaps': [], 'characters': len(value)}
    if not value or len(value) > MAX_NFO:
        result['gaps'].append('nfo_absent_or_over_limit')
        return result
    text = ' '.join(value.split())
    # Padding dots are field separators, not part of a field name.
    text = re.sub(r'(?<=\w)\.{2,}(?=\s*:)', ' ', text)
    sections = re.split(r'-{3,}(GENERAL|VIDEO|AUDIO(?:\s*\(#\d+\))?|TEXT|MENU)-{3,}', text, flags=re.I)
    dotted = len(sections)>1
    # Only the container section can supply runtime, never subtitles or audio.
    header = re.split(r'\b(?:Video|Audio|Text)(?: #\d+)?\s+ID\s*:', text, maxsplit=1)[0]
    if dotted:
        general=[sections[i+1] for i in range(1,len(sections),2) if sections[i].upper()=='GENERAL']
        header=general[0] if len(general)==1 else ''
    durations = re.findall(r'\bDuration\s*:\s*(?:(\d{1,2})\s*h\s*)?(\d{1,3})\s*min\b', header)
    if len(durations) == 1:
        hours, minutes = durations[0]
        duration = int(hours or 0) * 60 + int(minutes)
        if 0 < duration <= 1440 and (not hours or int(minutes) < 60):
            result['runtime'] = duration
    if result['runtime'] is None:
        result['gaps'].append('container_runtime_missing_or_ambiguous')
    tracks = re.split(r'\bAudio(?: #\d+)?\s+ID\s*:', text)[1:]
    if dotted:
        tracks=[sections[i+1] for i in range(1,len(sections),2) if sections[i].upper().startswith('AUDIO')]
    labels=r'ID|Format|Codec ID|Duration|Bit rate(?: mode)?|Channel(?:s| layout)?|Sampling rate|Sample rate|Frame rate|Compression mode|Stream size|Title|Language|Default|Forced|Service kind|SUBTITLES|Chapters'
    def field(track, name):
        values=re.findall(r'\b'+name+r'\s*:\s*(.*?)(?=\s+(?:'+labels+r')\s*:|$)',track,flags=re.I)
        return values[0].strip() if len(values)==1 else None
    for index,track in enumerate(tracks,1):
        track = re.split(r'\b(?:Text|Video)(?: #\d+)?\s+ID\s*:|\bMenu\b|\bSUBTITLES\s*:|\bChapters\s*:', track, maxsplit=1, flags=re.I)[0]
        language=field(track,'Language')
        language=language.casefold() if language else None
        if not language or not re.fullmatch(r'[a-z]+(?:[ -][a-z]+)*',language):language=None
        title=field(track,'Title')
        commentary=bool(title and re.search(r'\bcommentary\b',title,re.I))
        result['audio_languages'].append(language)
        result['audio_track_details'].append({'index':index,'language':language,'title':title,
            'role':'commentary' if commentary else 'unspecified',
            'role_basis':'explicit_title' if commentary else 'not_declared',
            'default':field(track,'Default')})
    if not tracks or None in result['audio_languages'] or len(set(result['audio_languages'])) != 1:
        result['gaps'].append('audio_language_missing_or_mixed')
    result['audio_tracks'] = len(tracks)
    filenames = re.findall(r'\bComplete name\s*:\s*(.*?)\s+Format\s*:', header)
    if dotted:
        prefix=sections[0].strip()
        if re.fullmatch(r'.+\.(?:mkv|mp4|avi|m2ts)',prefix,re.I):filenames.append(prefix)
    result['filenames'] = filenames
    movie = re.findall(r'\bMovie name\s*:\s*(.*?)(?=\s+(?:Encoded date|Writing application|Writing library|Duration|Format)\s*:|$)', header)
    result['declared_movie_names'] = movie
    return result


def unique_mapping(mapping, ident):
    return (isinstance(mapping, dict) and isinstance(mapping.get('movie_results'), list)
            and all(isinstance(r, dict) and type(r.get('id')) == int for r in mapping['movie_results'])
            and [r.get('id') for r in mapping['movie_results']] == [ident]
            and all(not mapping.get(k) for k in ('tv_results', 'tv_episode_results', 'tv_season_results', 'person_results')))


def build_case(release, listing, full_nfo, search, details, mappings, asserted_imdb=None):
    facts = nfo_facts(full_nfo)
    checked = listing.get('reason') in ('listing_id_found', 'listing_id_missing')
    conflict = not checked or bool(asserted_imdb and listing.get('imdb_id') and asserted_imdb != listing['imdb_id'])
    # NFO belongs to the exact validated listing. A contradictory embedded filename
    # invalidates binding; absence is recorded, not fabricated as filename proof.
    filename_conflict = len(facts.get('filenames', [])) > 1
    for name in facts.get('filenames', []):
        name = re.sub(r'\.(mkv|mp4|avi|m2ts)$', '', name, flags=re.I)
        filename_conflict |= normalized(name) != normalized(release['name'])
    conflict |= filename_conflict
    source = dict(title=release['title'], year=release['year'], imdb=listing.get('imdb_id'),
                  runtime=facts['runtime'], language=None, checked_listing=checked,
                  conflicting_evidence=conflict, nfo_bound=checked and not filename_conflict)
    # Convert the source audio language using catalog language names, without
    # assuming that source language equals a candidate's original language.
    language_map = {}
    for d in details.values():
        for language in d.get('spoken_languages', []):
            name, code = language.get('english_name'), language.get('iso_639_1')
            if isinstance(name, str) and isinstance(code, str) and re.fullmatch('[a-z]{2,3}', code):
                language_map.setdefault(name.casefold(), set()).add(code)
    langs = facts['audio_languages']
    if langs and None not in langs and len(set(langs)) == 1 and len(language_map.get(langs[0], set())) == 1:
        source['language'] = next(iter(language_map[langs[0]]))
    candidates = []
    for ident, d in details.items():
        names = [d.get('title'), d.get('original_title')]
        names += [x.get('title') for x in d.get('alternative_titles', {}).get('titles', [])]
        names += [x.get('data', {}).get('title') for x in d.get('translations', {}).get('translations', [])]
        dates = [d.get('release_date')]
        dates += [x.get('release_date') for c in d.get('release_dates', {}).get('results', []) for x in c.get('release_dates', [])]
        imdb = (d.get('external_ids') or {}).get('imdb_id')
        if d.get('imdb_id') not in (None, imdb):
            source['conflicting_evidence'] = True
        candidates.append(dict(id=ident, titles=list(dict.fromkeys(n for n in names if n))[:100],
                               years=sorted({int(x[:4]) for x in dates if isinstance(x, str) and x[:4].isdigit()}),
                               runtime=d.get('runtime') or None, language=d.get('original_language'),
                               imdb=imdb, media_type='movie', crosswalk_verified=unique_mapping(mappings.get(imdb), ident)))
    source['alias_search_support'] = search.get('alias_search_support', []) if isinstance(search,dict) else []
    rows = search.get('results', []) if isinstance(search, dict) else []
    ids = [x.get('id') for x in rows]
    complete = (isinstance(search, dict) and search.get('page') == 1 and search.get('total_pages') == 1
                and search.get('total_results') == len(rows) and 0 < len(rows) <= 3
                and len(set(ids)) == len(ids) and set(ids).issubset(details))
    for name in facts.pop('declared_movie_names', []):
        year = re.search(r'\((\d{4})\)\s*$', name)
        if year and int(year[1]) != release['year']:
            source['conflicting_evidence'] = True
        title = re.sub(r'\s*\(\d{4}\)\s*$', '', name)
        if '\ufffd' in title:
            facts['gaps'].append('nfo_movie_name_encoding_damaged')
        elif normalized(title) not in {normalized(t) for c in candidates for t in c['titles']}:
            source['conflicting_evidence'] = True
    case = dict(source=source, candidates=candidates, candidate_set_complete=complete)
    facts['binding'] = 'exact_listing_nfo_element' if source['nfo_bound'] else 'unverified'
    facts['filename_present'] = bool(facts.pop('filenames', []))
    return case, facts


def result(release, listing, full_nfo, search, details, mappings, asserted_imdb=None):
    case, facts = build_case(release, listing, full_nfo, search, details, mappings, asserted_imdb)
    scored = evaluate(case)
    top = scored['ranked'][0] if scored['ranked'] else None
    return dict(**scored, source=case['source'], nfo_facts=facts,
                evidence_digest=hashlib.sha256(full_nfo.encode()).hexdigest(),
                arithmetic_pass=bool(top and top['score'] >= 70 and scored['margin'] >= 15),
                evidence_gaps=facts['gaps'] + ([] if case['source']['language'] else ['source_language_unmapped']))
