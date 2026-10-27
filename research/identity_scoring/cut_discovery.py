"""Shadow-only discovery of edition claims and sourced runtime comparisons.

No film/edition registry. Claims are untrusted; even a corroborated comparison
never changes an identity decision or creates an acquisition capability.
"""
import hashlib
import json
import re
import time
from urllib.parse import urlencode
from bs4 import BeautifulSoup
from .edition_discovery import PRODUCT, SEARCH, fetch
from .scorer import words, score_candidate, valid_runtime, Policy, source_titles

# Syntax and release-format vocabulary, not a catalog of named film cuts.
NOUN = r'(?:cut|edition|version)'
TECH = re.compile(r'\b(?:\d{3,4}p|uhd|blu[ .-]?ray|b[dr]remux|remux|web[ .-]?(?:dl|rip)|'
                  r'hdtv|dvd(?:rip)?|h[ .]?26[45]|[xh]26[45]|avc|hevc|hdr\d*|dv|'
                  r'[248]k|remaster(?:ed)?|restored|dts|truehd|ddp?|aac|atmos|repack|proper|internal)\b', re.I)
MAX_TEXT = 65536


def norm(value):
    return ' '.join(words(value)).replace('director s', 'directors')


def descriptor(value):
    """Compare claims across cut/version/edition wording; preserve unknown names."""
    value = re.sub(r'\b'+NOUN+r'\b', '', norm(value))
    return ' '.join(w for w in value.split() if w not in ('the', 'a', 'an'))


def labels(text):
    """Return bounded syntactic claims with offsets. Never execute source text."""
    if not isinstance(text, str) or not text or len(text)>MAX_TEXT:
        return []
    text = text.replace('’', "'")
    # Filename punctuation and prose delimiters delimit short noun phrases.
    clean = re.sub(r'[._]', ' ', text)
    found=[]
    for m in re.finditer(r'\b'+NOUN+r'\b', clean, re.I):
        before=clean[max(0,m.start()-100):m.start()]
        if re.search(r'\bformat\s*$',before,re.I):continue
        before=re.split(r'[\n:;!?/|()"“”]|\s[-–—]\s|\b(?:is|was|includes?|contains?|features?|featuring|labeled|labelled|this|with|of|and|or|versus|vs|19\d{2}|20\d{2})\b',before,flags=re.I)[-1]
        tokens=re.findall(r"[^\W_]+(?:'s)?",before,flags=re.U)[-4:]
        if not tokens or any(t.isdigit() for t in tokens):continue
        label=' '.join(tokens+[m[0]]).strip()
        # Negated claims are retained, never used to select a cut.
        negated=bool(re.search(r'\b(?:not|no|without|rather than)\b',clean[max(0,m.start()-100):m.end()],re.I))
        found.append({'label':label,'descriptor':descriptor(label),'negated':negated,'offset':m.start()})
        if len(found)>=16:break
    return found


def extract(release, listing, nfo, candidate):
    """Collect claims; suffix leftovers are leads, not proven cut descriptions."""
    claims=[]; seen=set()
    def add(text, origin, implicit=False):
        for value in labels(text):
            # Do not misread the already identified movie title as a cut claim.
            if any(norm(value['label']) in norm(t) for t in candidate['titles']):continue
            key=(origin,norm(value['label']),value['negated'])
            if key in seen:continue
            seen.add(key);claims.append(dict(value,origin=origin,kind='syntactic_claim'))
        if implicit:
            cleaned=TECH.split(text,1)[0].strip(' ._-[]()')
            cleaned=re.sub(r'[-][A-Za-z0-9]+$','',cleaned).strip()
            if cleaned and len(cleaned)<=80 and 1<=len(cleaned.split())<=6 and not labels(cleaned):
                tokens=words(cleaned)
                if any(t.isalpha() and not re.fullmatch('[ivxlcdm]+',t) for t in tokens):
                    key=(origin,norm(cleaned),False)
                    if key not in seen:
                        seen.add(key)
                        claims.append({'label':cleaned,'descriptor':descriptor(cleaned),'negated':False,
                                       'origin':origin,'kind':'unexplained_label'})
    name=release.get('name','')
    if isinstance(name,str) and len(name)<=1024:
        year=re.search(r'(?<!\d)'+str(release['year'])+r'(?!\d)',name)
        if year:add(name[year.end():].replace('.',' '),'release_suffix',True)
    title=release['title']
    # An explicit AKA separates movie aliases, never an edition prefix. Keep
    # unresolved aliases in ordinary identity comparison, not public cut search.
    title_aliases=source_titles(title)
    for t in candidate['titles'] if len(title_aliases)==1 else []:
        raw=words(title); base=words(t)
        if len(raw)>len(base) and (raw[:len(base)]==base or raw[-len(base):]==base):
            rest=raw[len(base):] if raw[:len(base)]==base else raw[:-len(base)]
            add(' '.join(rest),'title_remainder',True)
    description=listing.get('torrent_evidence',{}).get('description',{}).get('text','')
    add(description,'tracker_description')
    add(nfo,'bound_nfo')
    return claims[:32]


def proposal(release, listing, nfo, case, facts):
    """Only a uniquely checked movie may lend identity to edition research."""
    source=case['source']; eligible=[]
    if facts.get('filename_count')!=1:return None
    for c in case['candidates']:
        r=score_candidate(source,c);p=r['contributions']
        if r['blocks'] or p['year']!=20 or p['source_id']!=25 or p['language']<=0:continue
        if source.get('nfo_bound') is not True or not valid_runtime(source.get('runtime')):continue
        # Full movie title must match, or be a whole edge of a title with a label.
        raw=words(source['title'])
        titles=[t for t in c['titles'] if words(t)==raw or
                (len(words(t))<len(raw) and (raw[:len(words(t))]==words(t) or raw[-len(words(t)):]==words(t)))]
        if not titles:continue
        title=max(titles,key=lambda t:len(words(t)))
        claims=extract(release,listing,nfo,c)
        mismatch=valid_runtime(c.get('runtime')) and abs(source['runtime']-c['runtime'])>1
        if not claims and not mismatch:continue
        if listing.get('_discovered_editions') and not mismatch:continue
        eligible.append({'title':title,'year':release['year'],'imdb':c['imdb'],'candidate_id':c['id'],
                         'catalog_runtime':c.get('runtime'),'nfo_runtime':source['runtime'],
                         'baseline_score':r['score'],'baseline_runtime_points':p['runtime'],
                         'claims':claims,'trigger':'runtime_disagreement' if mismatch else 'edition_claim'})
    return eligible[0] if len(eligible)==1 else None


def movie_title(value):
    return re.sub(r'\s+(?:3D\s+)?(?:4K\s+)?Blu-ray$|\s+3D$', '', value, flags=re.I)


def search_links(body, request):
    soup=BeautifulSoup(body,'html.parser'); found=[]
    for a in soup.select('a.hoverlink[data-productid][title][href]'):
        m=re.fullmatch(r'(.+) \((\d{4})\)',a['title'])
        if (m and int(m[2])==request['year'] and norm(movie_title(m[1]))==norm(request['title'])
            and PRODUCT.fullmatch(a['href']) and a['href'] not in found):found.append(a['href'])
    # One exact-title/year product. A miss is inconclusive, never exhaustive.
    return found[:100]


def parse_product(body, request, url, now):
    """Accept only bound product-header fields, never reviews or recommendations."""
    soup=BeautifulSoup(body,'html.parser')
    headings=soup.select('h1'); canonical=soup.select_one('link[rel=canonical]')
    if (not PRODUCT.fullmatch(url) or len(headings)!=1 or not canonical or canonical.get('href')!=url
        or norm(movie_title(headings[0].get_text(' ',strip=True)))!=norm(request['title'])):return None
    runtimes=soup.select('#runtime'); subtitles=soup.select('.subheadingtitle'); imdb=soup.select('a#imdb_icon[href]')
    if len(runtimes)!=1 or len(subtitles)!=1 or len(imdb)!=1:return None
    if not re.fullmatch(r'https://(?:www\.)?imdb\.com/title/'+re.escape(request['imdb'])+r'/',imdb[0]['href']):return None
    header=runtimes[0].find_parent('span',class_='subheading')
    if not header:return None
    years=[a.get_text(strip=True) for a in header.select('a[href]') if re.fullmatch(r'https://www\.blu-ray\.com/movies/movies\.php\?year=\d{4}',a['href'])]
    if years!=[str(request['year'])]:return None
    text=header.get_text(' ',strip=True)
    if re.search(r'\b(?:[2-9]\d* Movies|\d{4}-\d{4})\b',text,re.I):return None
    m=re.fullmatch(r'(\d{1,4}) min',runtimes[0].get_text(' ',strip=True))
    if not m or not valid_runtime(int(m[1])):return None
    subtitle=subtitles[0].get_text(' ',strip=True)
    extracted=[v for part in subtitle.split('/') for v in labels(part) if not v['negated']]
    # Multiple named editions in one header cannot bind one runtime to one cut.
    unique={v['descriptor']:v['label'] for v in extracted}
    if len(unique)!=1:return None
    desc,label=next(iter(unique.items()))
    return {'title':request['title'],'year':request['year'],'imdb':request['imdb'],
            'label':label,'descriptor':desc,'runtime':int(m[1]),'source':url,'retrieved':now,
            'digest':hashlib.sha256(body).hexdigest(),'section':'product_header',
            'scope':'first_exact_movie_year_product','multiple_cuts':bool(re.search(r'\b[2-9]\d* Cuts\b',text,re.I))}


def discover(request, path, budget, now=None):
    """Two public GETs maximum, shared budget and bounded persistent cache."""
    from .refresh import atomic
    now=time.time() if now is None else now
    identity={k:request[k] for k in ('title','year','imdb')}
    key=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
    cache={}
    if path.exists() and path.stat().st_size<=2097152:
        try:cache=json.loads(path.read_text())
        except (ValueError,OSError):pass
    if not isinstance(cache,dict):cache={}
    cache={k:v for k,v in cache.items() if isinstance(v,dict) and type(v.get('expires')) in (int,float) and v['expires']>now}
    if key in cache:return dict(cache[key],cache_hit=True)
    day=time.strftime('%Y-%m-%d',time.gmtime(budget.now()))
    if budget.used>8 or budget.data['days'].get(day,0)>38:return {'status':'cut_budget_deferred','record':None}
    record=None;status='cut_evidence_inconclusive'; count=0
    query=urlencode({'quicksearch':1,'quicksearch_country':'US','quicksearch_keyword':request['title'],'section':'bluraymovies'})
    try:
        urls=search_links(fetch(SEARCH+'?'+query,budget),request);count=len(urls)
        if urls:record=parse_product(fetch(urls[0],budget),request,urls[0],now)
        if record:status='cut_evidence_found'
    except Exception:status='cut_source_unavailable'
    item={'status':status,'record':record,'products_found':count,'products_examined':int(count>0),
          'search_exhaustive':False,'checked':now,'expires':now+(604800 if record else 86400)}
    if len(cache)>=100:cache.pop(min(cache,key=lambda k:cache[k].get('checked',0)))
    cache[key]=item;atomic(path,cache)
    return dict(item,cache_hit=False)


def comparison(request, discovery):
    """An explained runtime is an annotated proposal; existing gates stay intact."""
    record=discovery.get('record'); reasons=[]
    output={'trigger':request['trigger'],'claims':request['claims'],'candidate_id':request['candidate_id'],
            'nfo_runtime':request['nfo_runtime'],'catalog_runtime':request['catalog_runtime'],
            'discovery':discovery,'decision':'review','reasons':reasons}
    if not record:reasons.append(discovery['status']);return output
    if (record.get('imdb')!=request['imdb'] or record.get('year')!=request['year']
        or norm(record.get('title','unknown'))!=norm(request['title'])):
        reasons.append('cut_identity_conflict');return output
    claims=request['claims'];desc=record['descriptor'].split()
    def agrees(claim):
        tokens=claim['descriptor'].split()
        return bool(tokens) and (tokens==desc or (len(tokens)<len(desc) and desc[-len(tokens):]==tokens))
    # Descriptions may mention other cuts; retain ambiguity rather than silently
    # preferring the convenient claim. Unknown qualifiers are not thrown away.
    if any(c['negated'] or not agrees(c) for c in claims):reasons.append('edition_claims_conflict')
    if not valid_runtime(record.get('runtime')) or abs(request['nfo_runtime']-record['runtime'])>1:
        reasons.append('edition_runtime_mismatch')
    if not reasons:
        output['decision']='would_explain_runtime'
        policy=Policy()
        points=policy.weights['runtime']*max(-1.0,1-abs(request['nfo_runtime']-record['runtime'])/record['runtime']/policy.runtime_scale)
        output['comparison']={'baseline_score':request['baseline_score'],
            'baseline_runtime_points':request['baseline_runtime_points'],
            'edition_runtime_points':points,
            'candidate_score_with_edition_runtime':request['baseline_score']-request['baseline_runtime_points']+points,
            'changes_identity_decision':False}

    return output
