import film_identity as fi
"""Research-only Phase B source builder.
Builds a reproducible union-universe seed from film-level Academy recognition.
Production feeds/scoring are untouched.

Academy input is a static CSV mirror derived from the official Oscars ceremony pages.
Using the mirror avoids oscars.org blocking GitHub-hosted runners while keeping the
research build deterministic. The official Academy database remains the authority.

Identity resolution is deliberately cache-first after the authoritative local TSPDT
catalog. Previously verified identities from the committed Phase-B snapshot are reused
before any live IMDb suggestion lookup. This prevents transient IMDb/network failures
from shrinking the research universe between CI runs.
"""
import csv, io, json, re, unicodedata
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import quote

OUT=Path('sources/phase-b-institutional.json')
BACKCATALOG=Path('backcatalog-details.json')
MIN_FILM_YEAR=2000; MAX_FILM_YEAR=2023
UA={'User-Agent':'Mozilla/5.0 (radarr-festival-list research)'}
ACADEMY_CSV='https://raw.githubusercontent.com/mauraanish/Oscars-Data/main/oscars-data.csv'

def get(url):
    with urlopen(Request(url,headers=UA),timeout=30) as r: return r.read()

def norm(s):
    s=unicodedata.normalize('NFKD',str(s).casefold())
    return re.sub(r'[^a-z0-9]+','', ''.join(c for c in s if not unicodedata.combining(c)))

def canonical_index():
    """Known TSPDT movies are authoritative for title/year -> IMDb identity."""
    if not BACKCATALOG.exists(): return {}
    data=json.loads(BACKCATALOG.read_text(encoding='utf-8'))
    idx={}
    for row in data.get('candidates',[]):
        iid=row.get('imdb_id'); title=row.get('title'); year=row.get('year')
        if not iid or not title or not isinstance(year,int): continue
        idx.setdefault(norm(title),[]).append((iid,title,year))
    return idx

def cached_index(path=None):
    """Previously verified Phase-B identities, keyed by source and resolved titles.

    This is a reproducibility cache, not an independent evidence source. Entries are
    only reused for the same normalized title and approximately the same film year.
    """
    path=path or OUT
    if not path.exists(): return {}
    try: data=json.loads(path.read_text(encoding='utf-8'))
    except (OSError,json.JSONDecodeError): return {}
    idx={}
    for row in data.get('films',[]):
        iid=row.get('imdb_id')
        year=row.get('resolved_year') if isinstance(row.get('resolved_year'),int) else row.get('year')
        if not iid or not isinstance(year,int): continue
        titles=[]
        for field in ('title','resolved_title'):
            value=row.get(field)
            if value and value not in titles: titles.append(value)
        for title in titles:
            idx.setdefault(norm(title),[]).append((iid,row.get('resolved_title') or row.get('title') or title,year))
    return idx

def exact_lookup(title,year,index):
    hits=[x for x in index.get(norm(title),[]) if abs(x[2]-year)<=1]
    # De-duplicate aliases that point to the same verified IMDb identity.
    unique={x[0]:x for x in hits}
    return next(iter(unique.values())) if len(unique)==1 else None

def canonical_lookup(title,year,index):
    return exact_lookup(title,year,index)

def imdb_lookup(title,year):
    """Resolve only plausible movie suggestions; never accept a loose title hit."""
    verified=fi.verified_award(title,year) or fi.verified_identity(title,year)
    if verified:return verified["imdb_id"],verified["title"],verified["year"]
    data=json.loads(get('https://v2.sg.media-imdb.com/suggestion/x/'+quote(title)+'.json'))
    cand=[]
    for x in data.get('d',[]):
        iid=x.get('id',''); y=x.get('y'); t=x.get('l','')
        if not iid.startswith('tt') or not isinstance(y,int) or abs(y-year)>1: continue
        if norm(t)!=norm(title): continue
        # IMDb suggestions commonly expose q/qid as feature/movie. Reject known
        # non-film entity types but tolerate missing type metadata.
        kind=' '.join(str(x.get(k) or '').casefold() for k in ('q','qid'))
        blocked=('tv series','tv mini','episode','podcast','video game','music video','short')
        if any(token in kind for token in blocked): continue
        cand.append((abs(y-year),iid,t,y))
    if not cand:return None
    # Same title/year can still be ambiguous. Prefer the exact film year but do
    # not guess between multiple equally good IDs.
    cand.sort()
    best_distance=cand[0][0]
    best=[x for x in cand if x[0]==best_distance]
    if len(best)!=1:return None
    _,iid,t,y=best[0]; return iid,t,y

def academy():
    # The historical mirror contains mixed legacy bytes. latin-1 maps every byte
    # deterministically; title normalization plus IMDb resolution handles accents.
    raw=get(ACADEMY_CSV).decode('latin-1')
    rows=list(csv.DictReader(io.StringIO(raw)))
    films={}
    allowed={
        'Best Picture':'Best Picture',
        'Animated Feature Film':'Animated Feature Film',
        'International Feature Film':'International Feature Film',
        'Foreign Language Film':'International Feature Film',
        'Documentary (Feature)':'Documentary Feature Film',
        'Documentary Feature Film':'Documentary Feature Film',
    }
    for r in rows:
        try: ceremony=int(r['year'])
        except (TypeError,ValueError): continue
        film_year=ceremony-1
        if not (MIN_FILM_YEAR<=film_year<=MAX_FILM_YEAR): continue
        cat=allowed.get(r['category'])
        title=(r.get('film') or '').strip()
        if not cat or not title: continue
        winner=str(r.get('won','')).strip().lower() in {'1','true','yes'}
        status='winner' if winner else 'nominee'
        key=(norm(title),film_year)
        f=films.setdefault(key,{'title':title,'year':film_year,'signals':[],'institutional_strength':0})
        strength=(3 if winner else 1) if cat=='Best Picture' else (2 if winner else 1)
        sig=f'Academy {cat} {status}'
        f['institutional_strength']=max(f['institutional_strength'],strength)
        if sig not in f['signals']: f['signals'].append(sig)
    return list(films.values())

def main():
    films=academy(); resolved=[]; unresolved=[]
    known=canonical_index(); cached=cached_index()
    resolution_counts={'canonical':0,'cached':0,'live_imdb':0,'unresolved':0}
    for i,f in enumerate(films,1):
        m=canonical_lookup(f['title'],f['year'],known)
        resolution='canonical' if m else None
        if not m:
            m=exact_lookup(f['title'],f['year'],cached)
            if m: resolution='cached'
        if not m:
            try: m=imdb_lookup(f['title'],f['year'])
            except Exception as e:
                print('IMDb lookup error',f['title'],type(e).__name__); m=None
            if m: resolution='live_imdb'
        if m:
            iid,title,year=m
            if MIN_FILM_YEAR<=year<=MAX_FILM_YEAR:
                f.update(imdb_id=iid,resolved_title=title,resolved_year=year); resolved.append(f)
                resolution_counts[resolution]+=1
            else:
                unresolved.append(f); resolution_counts['unresolved']+=1
        else:
            unresolved.append(f); resolution_counts['unresolved']+=1
        if i%50==0: print('resolved',i,'/',len(films))
    seed={'title':'Nocturnal Animals','year':2016,'imdb_id':'tt4550098','institutional_strength':2,'signals':['Venice Grand Jury Prize']}
    if not any(x['imdb_id']==seed['imdb_id'] for x in resolved): resolved.append(seed)
    resolved.sort(key=lambda x:(x['year'],x['title']))
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({
        'films':resolved,
        'unresolved':unresolved,
        'resolution_counts':resolution_counts,
        'notes':'Research-only systematic Academy film-level universe (Best Picture; International/Foreign Language; Documentary Feature; Animated Feature) from a static Oscars-derived CSV mirror, plus verified Venice seed. Acting/craft awards excluded. Existing TSPDT IDs are preferred, then previously verified Phase-B identities are reused, and only unresolved identities use exact-title IMDb suggestions.'
    },ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'source_candidates':len(films),'resolved':len(resolved),'unresolved':len(unresolved),'resolution_counts':resolution_counts}))
if __name__=='__main__': main()
