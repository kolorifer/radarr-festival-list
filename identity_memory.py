"""Remembered movie candidates require a separate, occurrence-bound owner choice."""
import hashlib
import html
import json
import re
import unicodedata
from datetime import datetime, timezone

import verified_identity_cache as cache
from private_text import redact_text

# Missing/contradictory IDs, authentication failures and malformed pages are not outages.
OUTAGES = {'listing_temporary_http','listing_unavailable','rate_limited','lookup_busy',
           'metadata_api_unavailable','metadata_rate_limited','metadata_lookup_busy'}
CONFLICTS = {'identity_conflict','local_identity_conflict','title_conflict','year_conflict',
             'listing_id_conflict','external_id_conflict','non_movie_identity','ambiguous_id_mapping'}
MOVIE_KEYS = ('title','year','tmdb_id','imdb_id','poster_url','identity_status','identity_reason',
              'identity_year_basis','matched_release_year')


def context(release, indexer):
    if (release.get('type') != 'movie' or release.get('season') or release.get('episode')
            or release.get('protocol') != 'torrent' or indexer.get('identifier') != 'torrentleech'
            or indexer.get('name','TorrentLeech').casefold() != 'torrentleech'):
        raise ValueError('unsupported_context')
    title = release.get('title'); year = release.get('year')
    if not isinstance(title,str) or not 1 <= len(title) <= 250 or type(year) != int or not 1888 <= year <= 2100:
        raise ValueError('invalid_context')
    title = ' '.join(unicodedata.normalize('NFC',title).casefold().split())
    if not title:raise ValueError('invalid_title')
    return ['torrentleech',title,year]


def valid_movie(movie):
    return (isinstance(movie,dict) and movie.get('identity_status') == 'verified_tmdb'
            and type(movie.get('tmdb_id')) == int and movie['tmdb_id'] > 0
            and re.fullmatch(r'tt[0-9]{7,12}',str(movie.get('imdb_id',''))) is not None
            and isinstance(movie.get('title'),str) and bool(movie['title']))


def observe(payload, meta, *, verified_at=None):
    """Learn only independent verified IDs; never reinforce an owner's remembered choice."""
    if not cache.configured_path():return
    data=payload.get('data') or {};release=data.get('release') or {};indexer=data.get('indexer') or {}
    key=context(release,indexer)
    previous=cache.get('remembered_movie',key) or {}
    known=previous.get('movie') or {}
    asserted_conflict=bool(known and any(meta.get(k) is not None and str(meta[k])!=str(known.get(k)) for k in ('imdb_id','tmdb_id')))
    if meta.get('identity_reason') in CONFLICTS or asserted_conflict:
        cache.remember(key,{},conflict=True,verified_at=verified_at)
    elif (valid_movie(meta) and meta.get('identity_source') in ('torrentleech_listing','autobrr_external_ids')
          and not meta.get('identity_title_basis') and not meta.get('identity_choice') and not meta.get('identity_evidence')):
        cache.remember(key,{k:meta[k] for k in MOVIE_KEYS if k in meta},verified_at=verified_at)


def candidate(payload):
    data=payload.get('data') or {};release=data.get('release') or {};indexer=data.get('indexer') or {}
    try:
        value=cache.get('remembered_movie',context(release,indexer))
        if not value or value.get('ambiguous') or not valid_movie(value.get('movie')):return None
        movie=value['movie']
        for supplied,target in (('meta_imdb','imdb_id'),('meta_tmdb','tmdb_id')):
            value_id=release.get(supplied)
            if value_id not in (None,'') and (type(value_id) not in (str,int) or str(value_id)!=str(movie[target])):return None
        return value
    except (ValueError,TypeError,KeyError,AttributeError):return None


def packet(payload, current):
    """A proposal only; the current release remains unresolved until explicit POST."""
    import alternative_grab as alt
    data=payload.get('data') or {};meta=current.get('meta') or {}
    if (payload.get('event')!='action.rejected' or (data.get('action') or {}).get('type')!='RADARR'
            or meta.get('identity_status')!='unresolved' or meta.get('identity_reason') not in OUTAGES):return None
    reasons=(data.get('result') or {}).get('rejections')
    if not alt.quality_only(reasons) and reasons!=['Unknown Movie']:return None
    try:alt.source_reference(data['release'],data['indexer'])
    except (ValueError,TypeError,KeyError):return None
    remembered=candidate(payload)
    if not remembered:return None
    if any(meta.get(k) is not None and str(meta[k])!=str(remembered['movie'].get(k)) for k in ('imdb_id','tmdb_id')):return None
    listing_id=(current.get('review_listing') or {}).get('imdb_id')
    if listing_id and listing_id!=remembered['movie']['imdb_id']:return None
    return {'type':'remembered_movie','candidate':remembered['movie'],'verified_at':remembered['verified_at']}


def binding(payload):
    """Bind confirmation to the original release, action and rejection, including its private URL."""
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def target(action):
    payload=action['original_event']
    if binding(payload)!=action['review']['binding']:raise ValueError('changed_release')
    value=candidate(payload)
    expected=action['review']['candidate']
    if not value or any(value['movie'].get(k)!=expected.get(k) for k in ('imdb_id','tmdb_id')):
        raise ValueError('stale_or_ambiguous_memory')
    return dict(value['movie'],identity_source='owner_remembered_choice')


def reviewed_current(action, get_action):
    movie=action.get('movie') or {};marker=movie.get('identity_memory_choice')
    if not marker:return movie.get('identity_source')!='owner_remembered_choice'
    try:
        review=get_action(marker['review_token'])
        if not review or review.get('kind')!='identity_review' or not review.get('chosen'):return False
        expected=target(review)
        if any(expected.get(k)!=movie.get(k) for k in ('imdb_id','tmdb_id')):return False
        original=review['original_event']['data']
        # Acquisition projections omit different metadata fields. Every retained
        # field must still equal the chosen occurrence's original value.
        for field in ('release','indexer'):
            if not action.get(field) or any(original[field].get(k)!=v for k,v in action[field].items()):return False
        if action.get('kind')=='alternative' and action.get('rejections')!=original['result']['rejections']:return False
        return marker.get('binding')==review['review']['binding']
    except (OSError,ValueError,KeyError,TypeError):return False


def render(action, url=None):
    def esc(value):return html.escape(redact_text(str(value)),quote=True)
    movie=action['review']['candidate']
    date=datetime.fromtimestamp(action['review']['verified_at'],timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    body='<h2>Confirm remembered movie</h2><p>Metadata for this torrent is temporarily unavailable. A previous release was verified as:</p>'
    body+='<h3>'+esc(movie['title'])+' ('+esc(movie['year'])+')</h3>'
    body+='<p>IMDb '+esc(movie['imdb_id'])+' · TMDb '+esc(movie['tmdb_id'])+' · Verified '+esc(date)+'</p>'
    body+='<h3>This release</h3><p>'+esc(action['release']['name'])+'</p>'
    body+='<p>The remembered match does not prove this torrent contains that film or the same cut. Confirm the movie for this release only. This does not approve a download.</p>'
    if action.get('chosen'):
        body+='<p>Identity confirmed for this release. No download started.</p>'
        if url:body+='<a href="'+html.escape(url,quote=True)+'">Continue to separate download confirmation</a>'
        else:body+='<form method="post"><button name="prepare_download" value="yes">Open separate download confirmation</button></form>'
    else:
        body+='<form method="post"><label><input type="checkbox" name="confirm_identity" value="yes" required> This torrent is the movie shown above.</label><button>Confirm movie — no download</button></form>'
    return body
