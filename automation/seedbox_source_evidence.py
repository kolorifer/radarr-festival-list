"""Exact actor listing linkage and deterministic source/catalogue derivation.

No network or credential access. The host adapter retains original responses and
actual observation clocks. Missing or truncated fields stay missing; they are not
negative film evidence. This module never invents a human provenance review.
"""
import json,re
from ai_movie_investigator.contracts import require
from identity_triage_intake import normalize,safe_text
from tracker_metadata import valid_listing_url,parse_listing


def actor_listing(connection,case_id,metadata,sources,allowed_source):
    from automation.reviewed_telegram_operator import _target
    require(case_id.startswith('outcome-') and metadata['source']==allowed_source,'host_listing_source')
    rows=connection.execute('select version,body from retry_jobs where source=? limit 101',(case_id[8:],)).fetchall()
    require(len(rows)<=100,'host_listing_capacity');matches=[]
    for version,body in rows:
        item=json.loads(body);record=normalize(item['observation'],sources,'outcome')
        if record.get('reason') or record['metadata']!=metadata:continue
        target=_target(connection,version,sources)
        require(target['case_id']==case_id,'host_listing_case')
        release=item['observation']['data']['release'];external=release.get('external_id')
        require(type(external) is str and re.fullmatch(r'[1-9][0-9]{0,19}',external),'host_listing_id')
        url='https://www.torrentleech.org/torrent/'+external
        require(valid_listing_url(url) and ('listing' not in item or item['listing']==url),'host_listing_url')
        # Explicit deterministic derivation from the exact retained actor body:
        # the allowlisted source plus its strong numeric external ID selects
        # this URL. This is not a claim that a URL string was present originally.
        matches.append(dict(url=url,release_name=metadata['name'],target=target,actor_version=version))
    require(len(matches)==1,'host_listing_ambiguous_or_missing')
    return matches[0]


def _one(values):
    values=set(values)
    return next(iter(values)) if len(values)==1 else None


def listing_facts(raw,*,release_name,case_id,version,observed_at,expires_at,revision=1):
    from bs4 import BeautifulSoup
    require(type(raw) is bytes and 0<len(raw)<=1000000,'host_listing_size')
    require(revision in (1,2),'host_listing_revision')
    checked=parse_listing(raw,release_name)
    require(checked['reason'] in ('listing_id_found','listing_id_missing','listing_id_conflict'),'host_listing_not_authenticated')
    soup=BeautifulSoup(raw,'html.parser');section=soup.select_one('.torrent-info-details')
    titles=[];years=[];casts=[];directors=[];minutes=[]
    if section:
        for heading in section.select('h3'):
            value=heading.get_text(' ',strip=True)
            match=re.fullmatch(r'(.+?)\s*\((18[7-9][0-9]|19[0-9]{2}|20[0-9]{2}|2100)\)',value)
            if match:titles.append(safe_text(match[1],256));years.append(int(match[2]))
            elif revision==2 and value:titles.append(safe_text(value,256))
        for node in section.select('.torrent-extra-info p' if revision==2 else '.torrent-extra-info > p'):
            value=node.get_text(' ',strip=True)
            if revision==2:
                year=re.fullmatch(r'Year:\s*(18[7-9][0-9]|19[0-9]{2}|20[0-9]{2}|2100)',value)
                if year:years.append(int(year[1]))
            labels=(('Cast',casts),('Director',directors),('Directors',directors))+((('Stars',casts),) if revision==2 else ())
            for label,out in labels:
                if value.startswith(label+':'):
                    names=[safe_text(x.strip(),128) for x in value[len(label)+1:].split(',') if x.strip()]
                    if revision==2 and label in ('Cast','Stars') and node.select('a'):
                        names=[safe_text(a.get_text(' ',strip=True),128) for a in node.select('a') if a.get_text(' ',strip=True)]
                    if len(names)<=20:out.extend(names)
            m=re.fullmatch(r'(?:Runtime|Duration):\s*([0-9]{1,4})\s*(?:min|minutes)',value)
            if m and 0<int(m[1])<=1440:minutes.append(int(m[1]))
    # Do not truncate NFO duration into a guessed edition measurement.
    nfo_node=soup.select_one('#nfo_text');nfo=nfo_node.get_text('\n',strip=True) if nfo_node else ''
    general=re.findall(r'(?:^|\n)General\s*\n(.*?)(?=\n(?:General|Video|Audio|Text)\b|\Z)',nfo,re.S)
    if revision==2:
        # One section boundary for both duration syntaxes. Preserve v1 exactly.
        general=[];current=None
        for line in nfo.splitlines():
            header=re.match(r'[ \t]*(General|Video|Audio|Text|Subtitles?|Menu|Image|Other)\b',line)
            if header:
                if current is not None:general.append('\n'.join(current))
                current=[] if header[1]=='General' and re.fullmatch(r'[ \t]*General(?:[ \t]*:[^\n]*)?[ \t]*',line) else None
            elif current is not None:current.append(line)
        if current is not None:general.append('\n'.join(current))
    duration_text='\n'.join(general)
    durations=[]
    for h,m,s,ms in re.findall(r'\bDuration\s*:\s*([0-9]{1,2}):([0-9]{2}):([0-9]{2})\.([0-9]{3})\b',duration_text):
        if int(m)<60 and int(s)<60:
            value=((int(h)*60+int(m))*60+int(s))*1000+int(ms)
            if 0<value<=86400000:durations.append(value)
    invalid_alternate=False
    if revision==2:
        durations=[]
        for line in duration_text.splitlines():
            if not re.match(r'[ \t]*Duration\b',line):continue
            match=re.fullmatch(r'[ \t]*Duration[ \t]*:[ \t]*([0-9]{1,2}):([0-9]{2}):([0-9]{2})\.([0-9]{3})[ \t]*',line)
            if match:
                h,m,sec,ms=map(int,match.groups());value=((h*60+m)*60+sec)*1000+ms
                if m<60 and sec<60 and 0<value<=86400000:durations.append(value)
                else:invalid_alternate=True
            else:invalid_alternate=True
        blocks=general
        for block in blocks:
            for line in block.splitlines():
                if not re.match(r'\s*Length\s*:',line):continue
                match=re.fullmatch(r'\s*Length\s*:\s*[0-9]+(?:\.[0-9]+)?\s*(?:B|KiB|MiB|GiB|TiB)\s+for\s+([0-9]{1,2})\s*h\s+([0-9]{1,2})\s*min\s+([0-9]{1,2})\s*s\s+([0-9]{1,4})\s*ms\s*',line)
                if match:
                    h,m,sec,ms=map(int,match.groups());value=((h*60+m)*60+sec)*1000+ms
                    if m<60 and sec<60 and ms<1000 and 0<value<=86400000:durations.append(value)
                    else:invalid_alternate=True
                else:invalid_alternate=True
    duration=None if invalid_alternate else _one(durations)
    return dict(kind='selected_listing_facts_v1',case_id=case_id,version=version,observed_at=observed_at,expires_at=expires_at,
        title=_one(titles),year=_one(years),description_runtime_minutes=_one(minutes),nfo_runtime_milliseconds=duration,
        nfo_runtime_kind='container' if duration is not None else 'unknown' if nfo else 'absent',
        cast=sorted(set(casts)) if len(set(casts))<=20 else [],directors=sorted(set(directors)) if len(set(directors))<=20 else [],
        imdb=checked.get('imdb_id'))


def catalogue_facts(raw,*,expected_tmdb,expected_imdb,observed_at,expires_at):
    require(type(raw) is bytes and 0<len(raw)<=1048576,'host_catalogue_size')
    value=json.loads(raw)
    require(type(value) is dict and type(expected_tmdb) is int and 0<expected_tmdb<2**31 and type(value.get('id')) is int and value['id']==expected_tmdb and type(expected_imdb) is str and re.fullmatch(r'tt[0-9]{7,12}',expected_imdb) and value.get('imdb_id')==expected_imdb,'host_catalogue_crosswalk')
    credits=value.get('credits',{});dates=value.get('release_dates',{});theatrical=[];festival=[]
    require(type(credits) is dict and type(dates) is dict,'host_catalogue_shape')
    for region in dates.get('results',[]):
        for release in region.get('release_dates',[]):
            date=release.get('release_date','')
            if type(date) is not str or not re.match(r'(18[7-9][0-9]|19[0-9]{2}|20[0-9]{2}|2100)-[0-9]{2}-[0-9]{2}T',date):continue
            if release.get('type') in (2,3):theatrical.append(int(date[:4]))
            # Type1 is a premiere, not proof of a festival release.
            # Preserve its raw record without relabelling it as a festival.
    cast=credits.get('cast',[]);crew=credits.get('crew',[])
    require(type(cast) is list and type(crew) is list,'host_catalogue_people')
    # Only ordered first20 credits are retained. This is coverage, not an
    # assertion that other cast are absent; source adapter records truncation.
    actors=[safe_text(x['name'],128) for x in sorted(cast,key=lambda x:x.get('order',1000000))[:20]]
    directors=[safe_text(x['name'],128) for x in crew if x.get('job')=='Director']
    require(len(directors)<=20,'host_catalogue_people')
    runtime=value.get('runtime');require(runtime is None or type(runtime) is int and 0<=runtime<=1440,'host_catalogue_runtime')
    return dict(kind='catalogue_facts_v1',observed_at=observed_at,expires_at=expires_at,title=safe_text(value['title'],256),
        theatrical_year=_one(theatrical),festival_years=sorted(set(festival))[:20],runtime_minutes=runtime or None,
        cast=actors,directors=directors,imdb=expected_imdb,tmdb=expected_tmdb)
