"""Display-only edition claims. Never establishes movie identity or acquisition policy."""
import re

# Editorial sources and runtime caveats: docs/FILM_EDITIONS.md.
FILMS = {
    'tt0052311': {
        'tmdb_id': 1480, 'title': 'Touch of Evil', 'year': 1958,
        'cuts': {'theatrical': '1958 theatrical', 'preview': '1958 preview',
                 'reconstructed': '1998 reconstructed'},
        'context': 'The 1998 reconstruction follows Welles’ memo and changes editing and opening sound. '
                   'Made after his death, it was never personally approved by Welles, despite the “Director’s Cut” label.',
    },
}
_PATTERNS = {
    'theatrical': r'theatrical(?: (?:cut|version|edition))?',
    'directors': r'director(?: ?s)? (?:cut|edition)|dc',
    'extended': r'extended(?: (?:cut|version|edition))?',
    'unrated': r'unrated(?: (?:cut|version|edition))?',
    'final': r'final cut',
    'international': r'international (?:cut|version|edition)',
    'preview': r'preview (?:cut|version|edition)',
    'reconstructed': r'reconstruct(?:ed|ion)(?: (?:cut|version|edition))?',
    'workprint': r'workprint|work print',
}
_LABELS = {'directors': 'Director’s cut', **{key:key.capitalize() for key in _PATTERNS if key!='directors'}}


def _signals(value):
    if not isinstance(value,str) or len(value)>1024:return set()
    text=re.sub(r'[^a-z0-9]+',' ',value.casefold()).strip()
    return {key for key,pattern in _PATTERNS.items() if re.search(r'(?<!\w)(?:'+pattern+r')(?!\w)',text)}


def claim(name, year, edition=None):
    """Only scan the filename suffix after its movie year, excluding release group.

    A dedicated edition field is also a claim, never proof from runtime or bitrate.
    Multiple labels remain explicit ambiguity, not a preferred cut.
    """
    found=set()
    values=edition if isinstance(edition,list) and len(edition)<=16 else [edition]
    for value in values:found |= _signals(value)
    if isinstance(name,str) and len(name)<=1024 and type(year)==int and 1888<=year<=2100:
        match=re.search(r'(?<!\d)'+str(year)+r'(?!\d)',name)
        if match:
            tail=re.sub(r'-(?!(?:cut|version|edition)$)[A-Za-z0-9]+(?:\.[A-Za-z0-9]{2,4})?$','',name[match.end():],flags=re.I)
            found |= _signals(tail)
    return next(iter(found)) if len(found)==1 else 'ambiguous' if found else 'unknown'


def verified_film(meta):
    """Require already verified matching cross-IDs; titles never select facts."""
    if not isinstance(meta,dict) or meta.get('identity_status')!='verified_tmdb':return None
    imdb=meta.get('imdb_id')
    if not isinstance(imdb,str):return None
    film=FILMS.get(imdb)
    if film and type(meta.get('tmdb_id'))==int and meta['tmdb_id']==film['tmdb_id']:return film
    return None


def annotation(release, meta, existing=None):
    """Plain text, fixed labels only. Caller escapes once when rendering HTML."""
    film=verified_film(meta)
    if not film or not isinstance(release,dict) or release.get('type')!='movie':return ''
    def label(key):
        if key=='unknown':return 'Unknown'
        if key=='ambiguous':return 'Conflicting edition claims'
        return film['cuts'].get(key,_LABELS[key])+' (claimed)'
    fields=[]
    for field in ('edition','cut'):
        value=release.get(field)
        if isinstance(value,list) and len(value)<=8:fields.extend(value)
        elif isinstance(value,str):fields.append(value)
    key=claim(release.get('name'),film['year'],fields)
    lines=['🎞 Multiple significant cuts exist',
           'Edition of this release unknown' if key=='unknown' else 'Announced: '+label(key)]
    # Existing facts only accepted after caller verified the same Radarr identity.
    if existing is not None:
        valid=(isinstance(existing,dict) and existing.get('imdbId')==meta['imdb_id']
               and type(existing.get('tmdbId'))==int and existing['tmdbId']==meta['tmdb_id']
               and existing.get('hasFile') is True)
        file=(existing.get('movieFile') or {}) if valid else {}
        if not isinstance(file,dict):file={}
        existing_claim=claim(file.get('relativePath'),film['year'],file.get('edition'))
        lines.append('Existing: '+label(existing_claim))
    lines.append(film['context'])
    return '\n'.join(lines)


def candidate(release):
    """Cheap lookup shortlist only; it never verifies identity or authorizes actions."""
    if not isinstance(release,dict) or release.get('type')!='movie':return False
    title=release.get('title');year=release.get('year')
    if not isinstance(title,str) or len(title)>250 or type(year)!=int:return False
    title=re.sub(r'[^a-z0-9]+','',title.casefold())
    return any(year==film['year'] and title==re.sub(r'[^a-z0-9]+','',film['title'].casefold()) for film in FILMS.values())
