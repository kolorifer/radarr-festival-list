"""Bounded, inert torrent-page evidence. Never follows links or accepts identities.

Standard-library validation is shared by actor, collector, handoff and worker.
HTML extraction is actor-only and uses its existing exact-listing response.
"""
import hashlib
import re
import unicodedata

MAX_TEXT = 3000
# Public image links only, never tracker capabilities. No query, port, userinfo,
# escapes, fragment or arbitrary fetch endpoint. Unknown hosts remain counted.
IMAGE = re.compile(r'https://i\.ibb\.co/[A-Za-z0-9_-]{1,40}/[A-Za-z0-9_.-]{1,240}\.(?:png|jpg|jpeg|webp)\Z', re.I)
SECRET = re.compile(r'https?://\S+|magnet:\S+|www\.\S+|\b(?:passkey|token|password|authorization|cookie|bearer)\b.*|[A-Za-z0-9_-]{48,}', re.I)


def text(value):
    value = SECRET.sub('[redacted]', value)
    value = ''.join(' ' if unicodedata.category(c).startswith('C') else c for c in value)
    value = re.sub(r'[<>\\?=@]', ' ', value)
    return ' '.join(value.split())[:MAX_TEXT].strip()


def fingerprint(value):
    return hashlib.sha256(value.encode()).hexdigest()


def validate(value):
    if not isinstance(value, dict) or set(value) != {'version','description','nfo','images','unavailable_images','truncated'} or type(value['version']) != int or value['version'] != 1:
        raise ValueError('torrent_evidence_schema')
    for key in ('description','nfo'):
        section=value[key]
        if not isinstance(section,dict) or set(section)!={'text','digest'} or not isinstance(section['text'],str) or text(section['text'])!=section['text'] or section['digest']!=fingerprint(section['text']):
            raise ValueError('torrent_evidence_text')
    if type(value['truncated']) != bool or type(value['unavailable_images']) != int or not 0<=value['unavailable_images']<=10000:
        raise ValueError('torrent_evidence_bounds')
    if not isinstance(value['images'],list) or len(value['images'])>6:raise ValueError('torrent_evidence_images')
    seen=set()
    for image in value['images']:
        if not isinstance(image,dict) or set(image)!={'url','section','review_status'} or image['section'] not in {'nfo_screenshot','nfo_illustration','description_image','screenshot_gallery'} or image['review_status']!='not_visually_reviewed' or not isinstance(image['url'],str) or not IMAGE.fullmatch(image['url']) or image['url'] in seen:
            raise ValueError('torrent_evidence_image')
        seen.add(image['url'])
    return value


def extract(soup):
    """Call only after the page's exact release heading has been verified."""
    from bs4 import NavigableString
    description=soup.select_one('.torrent-info-details')
    nfo=soup.select_one('#nfo_text')
    raw_description=' '.join(x.get_text(' ',strip=True) for x in description.select('h3, .torrent-summary, .torrent-extra-info > p')) if description else ''
    raw_nfo=nfo.get_text(' ',strip=True) if nfo else ''
    result={'version':1,'description':{},'nfo':{},'images':[],'unavailable_images':0,'truncated':False}
    for key,raw in (('description',raw_description),('nfo',raw_nfo)):
        cleaned=text(raw)
        result[key]={'text':cleaned,'digest':fingerprint(cleaned)}
        result['truncated'] |= len(raw)>MAX_TEXT
    seen=set()
    for node,default in ((description,'description_image'),(nfo,'nfo_illustration'),(soup.select_one('.galleryContents'),'screenshot_gallery')):
        if node is None:continue
        section=default
        for child in node.descendants:
            if isinstance(child,NavigableString):
                if default=='nfo_illustration' and re.search(r'\bScreenshots\b',str(child),re.I):section='nfo_screenshot'
                continue
            if child.name!='img':continue
            url=child.get('src','')
            if not isinstance(url,str) or not IMAGE.fullmatch(url):
                result['unavailable_images']+=1;continue
            if url in seen:continue
            seen.add(url)
            if len(result['images'])>=6:result['truncated']=True;continue
            result['images'].append({'url':url,'section':section,'review_status':'not_visually_reviewed'})
    return validate(result)


def assess(value, candidate):
    """Review hints, not a score or identity override. Never treat IDs as proof."""
    validate(value)
    nfo=value['nfo']['text']
    durations=set()
    for hours,minutes in re.findall(r'\bDuration\s*:\s*(\d{1,2})\s*h\s*(\d{1,2})\s*min\b',nfo,re.I):
        if int(minutes)<60 and 0<int(hours)*60+int(minutes)<=1440:durations.add(int(hours)*60+int(minutes))
    for minutes in re.findall(r'\bDuration\s*:\s*(\d{1,4})\s*min\b',nfo,re.I):
        if 0<int(minutes)<=1440:durations.add(int(minutes))
    return {'nfo_runtime_minutes':sorted(durations),
            'catalog_runtime_minutes':candidate.get('runtime'),
            'runtime_comparison':'not_available' if not durations or not candidate.get('runtime') else 'agrees' if durations=={candidate['runtime']} else 'differs_or_ambiguous',
            'screenshots_for_review':sum(x['section'] in {'nfo_screenshot','screenshot_gallery'} for x in value['images']),
            'visual_review':'pending' if value['images'] else 'unavailable',
            'description_independent_of_tracker_id':False,
            'source_claims_verified':False}
