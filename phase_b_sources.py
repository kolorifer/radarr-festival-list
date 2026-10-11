"""Research-only Phase B source builder.
Builds a reproducible union-universe seed from film-level Academy recognition.
Production feeds/scoring are untouched.
"""
import json, re, unicodedata
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import quote
from bs4 import BeautifulSoup

OUT=Path('sources/phase-b-institutional.json')
MIN_FILM_YEAR=2000; MAX_FILM_YEAR=2023
UA={'User-Agent':'Mozilla/5.0 (radarr-festival-list research)'}

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
        # Prefer exact normalized title; suggestion service occasionally uses translated titles.
        score=(0 if norm(t)==norm(title) else 1, abs(y-year))
        cand.append((score,iid,t,y))
    if not cand:return None
    _,iid,t,y=min(cand); return iid,t,y

def academy():
    films={}
    # Ceremony N honors mostly N-1 releases. 2001..2024 covers film years 2000..2023.
    for ceremony in range(2001,2025):
        soup=BeautifulSoup(get(f'https://www.oscars.org/oscars/ceremonies/{ceremony}'),'html.parser')
        text='\n'.join(s.strip() for s in soup.stripped_strings)
        # Parse category blocks from visible page text. Only film-level categories are admitted.
        cats=['Best Picture','International Feature Film','Foreign Language Film','Documentary (Feature)','Documentary Feature Film','Animated Feature Film']
        positions=[]
        for cat in cats:
            for m in re.finditer(r'(?m)^'+re.escape(cat)+r'$',text): positions.append((m.start(),cat))
        positions.sort()
        for idx,(pos,cat) in enumerate(positions):
            end=positions[idx+1][0] if idx+1<len(positions) else min(len(text),pos+5000)
            block=text[pos:end]
            # Category appears more than once in navigation/index. Require Winner marker nearby.
            wm=re.search(r'(?m)^Winner$',block)
            if not wm: continue
            lines=[x.strip() for x in block[wm.start():].splitlines() if x.strip()]
            # Expected sequence: Winner, [country for intl], title, credits, Nominees, ...
            entries=[]; status='winner'
            i=1
            while i<len(lines):
                if lines[i]=='Nominees': status='nominee'; i+=1; continue
                if lines[i] in cats or lines[i].startswith('## '): break
                val=lines[i]
                # Identify likely title as line immediately after Winner/Nominees, allowing country line in intl.
                if i==1 or lines[i-1]=='Nominees':
                    title=val
                    if cat in ('International Feature Film','Foreign Language Film') and i+1<len(lines): title=lines[i+1]; i+=1
                    entries.append((title,status))
                i+=1
            film_year=ceremony-1
            for title,status in entries:
                if not (MIN_FILM_YEAR<=film_year<=MAX_FILM_YEAR): continue
                key=(norm(title),film_year)
                f=films.setdefault(key,{'title':title,'year':film_year,'signals':[],'institutional_strength':0})
                if cat=='Best Picture':
                    strength=3 if status=='winner' else 1
                    sig=f'Academy Best Picture {status}'
                else:
                    strength=2 if status=='winner' else 1
                    sig=f'Academy {cat} {status}'
                f['institutional_strength']=max(f['institutional_strength'],strength)
                if sig not in f['signals']: f['signals'].append(sig)
    return list(films.values())

def main():
    films=academy(); resolved=[]; unresolved=[]
    for i,f in enumerate(films,1):
        m=imdb_lookup(f['title'],f['year'])
        if m:
            iid,title,year=m; f.update(imdb_id=iid,resolved_title=title,resolved_year=year); resolved.append(f)
        else: unresolved.append(f)
        if i%50==0: print('resolved',i,'/',len(films))
    # Preserve independently verified Venice seed until Venice source is automated.
    seed={'title':'Nocturnal Animals','year':2016,'imdb_id':'tt4550098','institutional_strength':2,'signals':['Venice Grand Jury Prize']}
    if not any(x['imdb_id']==seed['imdb_id'] for x in resolved): resolved.append(seed)
    resolved.sort(key=lambda x:(x['year'],x['title']))
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({'films':resolved,'unresolved':unresolved,'notes':'Research-only systematic Academy film-level universe (Best Picture; International/Foreign Language; Documentary Feature; Animated Feature), plus verified Venice seed. Acting/craft awards excluded.'},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'resolved':len(resolved),'unresolved':len(unresolved)}))
if __name__=='__main__': main()
