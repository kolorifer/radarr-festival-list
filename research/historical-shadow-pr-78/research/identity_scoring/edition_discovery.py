"""Bounded public packaging discovery; no credentials, actor actions or arbitrary URLs."""
import hashlib
import json
import re
import time
from urllib.parse import urlencode
from bs4 import BeautifulSoup
from .scorer import words, score_candidate

PRODUCT=re.compile(r'https://www\.blu-ray\.com/movies/[A-Za-z0-9-]+/[1-9][0-9]*/')
SEARCH='https://www.blu-ray.com/search/'


def proposal(source, candidates):
    found=[]
    raw=words(source['title'])
    for c in candidates:
        scored=score_candidate(source,c);p=scored['contributions']
        if scored['blocks'] or p['title']==30 or p['year']!=20 or p['source_id']!=25 or p['runtime']<=0 or p['language']!=10:continue
        for title in c['titles']:
            tokens=words(title)
            if len(tokens)>=len(raw) or not any(t.isalpha() for t in tokens):continue
            rest=raw[len(tokens):] if raw[:len(tokens)]==tokens else raw[:-len(tokens)] if raw[-len(tokens):]==tokens else []
            # Never strip a bare sequel number or an excessively long phrase.
            if not 1<=len(rest)<=6 or not any(t.isalpha() for t in rest):continue
            if all(t.isdigit() or re.fullmatch(r'[ivxlcdm]+',t) for t in rest):continue
            if set(rest)&set(tokens):continue
            found.append({'label':' '.join(rest),'title':title,'year':source['year']})
    unique={json.dumps(x,sort_keys=True):x for x in found}
    return next(iter(unique.values())) if len(unique)==1 else None


def search_links(body,label,year):
    soup=BeautifulSoup(body,'html.parser'); links=[]
    for a in soup.select('a.hoverlink[data-productid][title][href]'):
        match=re.fullmatch(r'(.+) \((\d{4})-(\d{4})\)',a['title'])
        if (match and words(match[1])==words(label) and int(match[2])<=year<=int(match[3])
            and PRODUCT.fullmatch(a['href']) and a['href'] not in links):links.append(a['href'])
    return links[:1]  # Membership evidence, not an exhaustive edition search.


def parse_product(body,label,url,now):
    soup=BeautifulSoup(body,'html.parser'); headings=soup.select('h1')
    canonical=soup.select_one('link[rel=canonical]')
    if len(headings)!=1 or not canonical or canonical.get('href')!=url:return None
    heading=re.sub(r'\s+Blu-ray$','',headings[0].get_text(' ',strip=True))
    if words(heading)!=words(label):return None
    # Only per-member disc metadata. Reviews/recommendations never establish membership.
    members=[]
    for a in soup.select('#longsubs > b > a[href]'):
        title=a.get_text(' ',strip=True)
        if PRODUCT.fullmatch(a['href']) and title and len(title)<=256:
            members.append({'title':title})
    if not 2<=len(members)<=100:return None
    return {'label':label,'source':url,'retrieved':now,'members':members,
            'digest':hashlib.sha256(body).hexdigest(),'section':'longsubs','scope':'first_exact_collection_result'}


def fetch(url,budget):
    import requests
    if url!=SEARCH and not (url.startswith(SEARCH+'?') or PRODUCT.fullmatch(url)):
        raise ValueError('edition_url_denied')
    budget.reserve('edition')
    with requests.Session() as session:
        session.trust_env=False
        with session.get(url,headers={'User-Agent':'Mozilla/5.0'},timeout=(3,5),allow_redirects=False,stream=True) as response:
            if response.status_code in (401,403):budget.cooldown('edition',auth=True)
            if response.status_code==429:budget.cooldown('edition',3600)
            if response.status_code!=200:raise RuntimeError('edition_http_failure')
            raw=bytearray();deadline=time.monotonic()+15
            for chunk in response.iter_content(4096):
                raw.extend(chunk)
                if len(raw)>1048576 or time.monotonic()>deadline:raise RuntimeError('edition_response_limit')
            return bytes(raw)


def discover(request,path,budget,now=None):
    from .refresh import atomic
    now=time.time() if now is None else now
    key=hashlib.sha256(json.dumps(request,sort_keys=True).encode()).hexdigest()
    cache={}
    if path.exists() and path.stat().st_size<=2097152:
        try:cache=json.loads(path.read_text())
        except (ValueError,OSError):pass
    if not isinstance(cache,dict):cache={}
    cache={k:v for k,v in cache.items() if isinstance(v,dict) and isinstance(v.get('expires'),(int,float)) and v['expires']>now}
    if key in cache:return cache[key]
    # Reserve room for the complete two-GET lookup, never enlarge shared limits.
    day=time.strftime('%Y-%m-%d',time.gmtime(budget.now()))
    if budget.used>8 or budget.data['days'].get(day,0)>38:return {'status':'edition_budget_deferred'}
    record=None;status='edition_evidence_inconclusive'
    query=urlencode({'quicksearch':1,'quicksearch_country':'US','quicksearch_keyword':request['label'],'section':'bluraymovies'})
    try:
        urls=search_links(fetch(SEARCH+'?'+query,budget),request['label'],request['year'])
        if urls:record=parse_product(fetch(urls[0],budget),request['label'],urls[0],now)
        if record and any(words(m['title'])==words(request['title']) for m in record['members']):status='edition_membership_found'
        else:record=None
    except Exception:
        status='edition_source_unavailable'
    item={'status':status,'record':record,'expires':now+(7*86400 if record else 86400),'checked':now}
    if len(cache)>=100:cache.pop(min(cache,key=lambda k:cache[k].get('checked',0)))
    cache[key]=item;atomic(path,cache)
    return item
