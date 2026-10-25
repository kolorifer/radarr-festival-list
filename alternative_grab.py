"""Exact-release alternative approvals. No search, movie creation or settings writes."""
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit, unquote
from radarr_client import RadarrError, get_movie_by_tmdb
from pending_actions import create_action, get_action

CONFIG='MOVIE_INTEL_ALTERNATIVE_GRAB_CONFIG'
QUALITY=r'(?:Remux|Bluray|WEBDL|WEBRip|HDTV)-(?:720|1080|2160)p'
REASONS=[re.compile(p) for p in (
    r'Existing file meets cutoff: '+QUALITY+r' \[\]',
    r'Existing file on disk is of equal or higher preference: '+QUALITY+r' v[1-9][0-9]*',
    r'Existing file and the Quality profile does not allow upgrades',
    r'Existing file on disk has a equal or higher Custom Format score: -?(?:0|[1-9][0-9]{0,9})',
)]


def quality_only(reasons):
    return (isinstance(reasons,list) and 0<len(reasons)<=8 and
            all(isinstance(r,str) and any(p.fullmatch(r) for p in REASONS) for r in reasons))


def source_reference(release,indexer):
    if not isinstance(release,dict) or not isinstance(indexer,dict):raise ValueError('invalid_source')
    if indexer.get('identifier')!='torrentleech' or release.get('protocol')!='torrent':raise ValueError('unsupported_source')
    if release.get('type')!='movie' or release.get('season') or release.get('episode'):raise ValueError('not_movie')
    source=str(release.get('external_id',''))
    if not re.fullmatch(r'[1-9][0-9]{0,19}',source):raise ValueError('missing_source_id')
    url=release.get('download_url')
    if not isinstance(url,str) or len(url)>2048:raise ValueError('missing_reference')
    match=re.fullmatch(r'https://www\.torrentleech\.org/rss/download/'+source+r'/[A-Za-z0-9_-]+/([^/\\?#\x00-\x1f\x7f]{1,1500}\.torrent)',url)
    if not match or not re.fullmatch(r'[^/\\?#\x00-\x1f\x7f]{1,1500}\.torrent',unquote(match[1])):raise ValueError('invalid_reference')
    if not isinstance(release.get('name'),str) or not 1<=len(release['name'])<=1024:raise ValueError('invalid_name')
    return url,hashlib.sha256(('torrentleech:'+source).encode()).hexdigest()


def existing_movie(movie):
    if (not isinstance(movie,dict) or movie.get('identity_status')!='verified_tmdb'
        or type(movie.get('tmdb_id'))!=int or not re.fullmatch(r'tt[0-9]{7,10}',str(movie.get('imdb_id','')))):
        raise RadarrError('Movie identity is not verified')
    current=get_movie_by_tmdb(movie['tmdb_id'])
    if (not current or current.get('tmdbId')!=movie['tmdb_id'] or current.get('imdbId')!=movie['imdb_id']
        or current.get('hasFile') is not True or not current.get('movieFileId') or not current.get('monitored')):
        raise RadarrError('The same monitored movie and existing file could not be verified')
    file=current.get('movieFile')
    if not isinstance(file,dict) or file.get('id')!=current['movieFileId']:raise RadarrError('Existing file is unavailable')
    return current


def snapshot(current):
    f=current['movieFile'];q=f.get('quality') or {}
    return {'movie_id':current['id'],'file_id':current['movieFileId'],'quality_profile':current.get('qualityProfileId'),
            'name':f.get('relativePath'),'edition':f.get('edition'),'group':f.get('releaseGroup'),
            'size':f.get('size'),'quality':q}


def validate_action(action):
    if action.get('kind')!='alternative' or not quality_only(action.get('rejections')):raise ValueError('ineligible')
    import identity_memory
    if not identity_memory.reviewed_current(action,get_action):raise ValueError('identity_choice_unavailable')
    source_reference(action['release'],action['indexer'])
    current=existing_movie(action['movie'])
    if snapshot(current)!=action.get('existing'):raise RadarrError('Existing movie/file changed; wait for a fresh announcement')
    return current


def offer(payload,meta):
    if not os.environ.get(CONFIG):return None
    data=payload.get('data') or {};reasons=(data.get('result') or {}).get('rejections')
    if payload.get('event')!='action.rejected' or (data.get('action') or {}).get('type')!='RADARR' or not quality_only(reasons):return None
    try:
        release=data['release'];indexer=data['indexer'];source_reference(release,indexer)
        current=existing_movie(meta)
        keys=('type','protocol','external_id','name','title','year','size','resolution','source','group','edition','cut','download_url','info_url')
        movie={k:meta.get(k) for k in ('tmdb_id','imdb_id','identity_status','title','year','identity_source','identity_title_basis')}
        if meta.get('identity_memory_choice'):
            movie.update(identity_source=meta.get('identity_source'),identity_memory_choice=meta['identity_memory_choice'])
        return create_action({'kind':'alternative','movie':movie,'release':{k:release[k] for k in keys if k in release},
                              'indexer':{'identifier':'torrentleech'},'rejections':reasons,'existing':snapshot(current)})
    except (KeyError,ValueError,TypeError,OSError,RadarrError):return None


def execute(token):
    # Only a capability crosses the process interface; no generic URL or client command.
    try:
        run=subprocess.run([sys.executable,str(Path(__file__).with_name('alternative_grab_helper.py'))],
                           input=token,text=True,capture_output=True,timeout=75,check=False)
        result=json.loads(run.stdout)
        if result.get('status') not in ('queued','already_present','refused','uncertain'):raise ValueError()
        return result['status']
    except (OSError,ValueError,subprocess.TimeoutExpired):return 'uncertain'


def candidate(payload):
    if not os.environ.get(CONFIG) or payload.get('event')!='action.rejected':return False
    data=payload.get('data') or {}
    if (data.get('action') or {}).get('type')!='RADARR' or not quality_only((data.get('result') or {}).get('rejections')):return False
    try:source_reference(data.get('release'),data.get('indexer'));return True
    except (ValueError,TypeError):return False
