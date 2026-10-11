"""Research-only Phase B source builder.
Builds a reproducible union-universe seed from film-level Academy recognition.
Production feeds/scoring are untouched.

Academy input is a static CSV mirror derived from the official Oscars ceremony pages.
Using the mirror avoids oscars.org blocking GitHub-hosted runners while keeping the
research build deterministic. The official Academy database remains the authority.
"""
import csv, io, json, re, unicodedata
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import quote

OUT=Path('sources/phase-b-institutional.json')
MIN_FILM_YEAR=2000; MAX_FILM_YEAR=2023
UA={'User-Agent':'Mozilla/5.0 (radarr-festival-list research)'}
ACADEMY_CSV='https://raw.githubusercontent.com/mauraanish/Oscars-Data/main/oscars-data.csv'

def get(url):
    with urlopen(Request(url,headers=UA),timeout=30) as r: return r.read()

def norm(s):
    s=unicodedata.normalize('NFKD',s.casefold())
    return re.sub(r'[^a-z0-9]+','', ''.join(c for c in s if not unicodedata.combining(c)))

def imdb_lookup(title,year):
    data=json.loads(get('https://v2.sg.media-imdb.com/suggestion/x/'+quote(title)+'.json'))
    cand=[]
    for x in data.get('d',[]):
        iid=x.get('id',''); y=x.get('y'); t=x.get('l','')
        if not iid.startswith('tt') or not isinstance(y,int) or abs(y-year)>1: continue
        score=(0 if norm(t)==norm(title) else 1, abs(y-year))
        cand.append((score,iid,t,y))
    if not cand:return None
    _,iid,t,y=min(cand); return iid,t,y

def academy():
    raw=get(ACADEMY_CSV).decode('utf-8-sig')
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
        ceremony=int(r['year'])
        film_year=ceremony-1
        if not (MIN_FILM_YEAR<=film_year<=MAX_FILM_YEAR): continue
        cat=allowed.get(r['category'])
        title=(r.get('film') or '').strip()
        if not cat or not title: continue
        winner=str(r.get('won','')).strip().lower() in {'1','true','yes'}
        status='winner' if winner else 'nominee'
        key=(norm(title),film_year)
        f=films.setdefault(key,{'title':title,'year':film_year,'signals':[],'institutional_strength':0})
        if cat=='Best Picture': strength=3 if winner else 1
        else: strength=2 if winner else 1
        sig=f'Academy {cat} {status}'
        f['institutional_strength']=max(f['institutional_strength'],strength)
        if sig not in f['signals']: f['signals'].append(sig)
    return list(films.values())

def main():
    films=academy(); resolved=[]; unresolved=[]
    for i,f in enumerate(films,1):
        try: m=imdb_lookup(f['title'],f['year'])
        except Exception as e:
            print('IMDb lookup error',f['title'],e); m=None
        if m:
            iid,title,year=m; f.update(imdb_id=iid,resolved_title=title,resolved_year=year); resolved.append(f)
        else: unresolved.append(f)
        if i%50==0: print('resolved',i,'/',len(films))
    seed={'title':'Nocturnal Animals','year':2016,'imdb_id':'tt4550098','institutional_strength':2,'signals':['Venice Grand Jury Prize']}
    if not any(x['imdb_id']==seed['imdb_id'] for x in resolved): resolved.append(seed)
    resolved.sort(key=lambda x:(x['year'],x['title']))
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({'films':resolved,'unresolved':unresolved,'notes':'Research-only systematic Academy film-level universe (Best Picture; International/Foreign Language; Documentary Feature; Animated Feature) from a static Oscars-derived CSV mirror, plus verified Venice seed. Acting/craft awards excluded.'},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'source_candidates':len(films),'resolved':len(resolved),'unresolved':len(unresolved)}))
if __name__=='__main__': main()
