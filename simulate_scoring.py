"""Research-only multi-route qualification simulation. Production scoring is untouched."""
import json, math
from pathlib import Path

BACKCATALOG=Path("backcatalog-details.json"); AUDIENCE=Path("audience-ratings.json")
OUTPUT=Path("scoring-simulation.json"); QUALIFIERS=Path("simulation-qualifiers.json")

# Film-level recognition only; acting/craft awards are excluded.
# Values are evidence strength for the institutional route, not additive score points.
RECOGNITION={
"tt2543164":(1,"Academy Best Picture nominee"),
"tt2024544":(3,"Academy Best Picture winner"),
"tt1454468":(1,"Academy Best Picture nominee"),
"tt0993846":(1,"Academy Best Picture nominee"),
"tt2042568":(1,"Cannes Grand Prix"),
"tt2400275":(1,"Cannes Jury Prize"),
"tt3808342":(2,"Academy International Feature winner + Cannes Grand Prix"),
"tt3508840":(1,"Cannes Best Director"),
"tt0407887":(3,"Academy Best Picture winner"),
"tt4034228":(1,"Academy Best Picture nominee"),
"tt3464902":(1,"Cannes Jury Prize"),
}

CALIBRATION={'Arrival','12 Years a Slave','Gravity','The Wolf of Wall Street','La Commune (Paris, 1871)','Inside Llewyn Davis','Son of Saul','The Assassin','The Departed','Manchester by the Sea','The Lobster','Donnie Darko','Dune','Blade Runner 2049','Midsommar','Her','Ex Machina','Scott Pilgrim vs. the World','Goodbye to Language','Winter Sleep'}

def q(v,x):
 v=sorted(n for n in v if isinstance(n,(int,float))); p=(len(v)-1)*x; lo=math.floor(p); hi=math.ceil(p)
 return v[lo] if lo==hi else v[lo]*(hi-p)+v[hi]*(p-lo)

def prod_base(r): return 5 if r<=25 else 4 if r<=50 else 3 if r<=100 else 2 if r<=250 else 1 if r<=500 else .5

def main():
 back=json.loads(BACKCATALOG.read_text()); aud=json.loads(AUDIENCE.read_text()); ratings=aud['ratings']; rows=[]
 for c in back['candidates']:
  rr=ratings.get(c['imdb_id'],{}).get('reeldb',{}); im=rr.get('imdb') or {}; lb=rr.get('letterboxd') or {}
  rows.append({'title':c['title'],'year':c['year'],'imdb_id':c['imdb_id'],'rank':c['tspdt_rank'],'production_score':c['score'],'existing_bonus':round(float(c['score'])-prod_base(c['tspdt_rank']),3),'imdb_rating':im.get('rating'),'imdb_votes':im.get('votes'),'letterboxd_rating':lb.get('rating'),'letterboxd_votes':lb.get('votes')})
 ir=[r['imdb_rating'] for r in rows if r['imdb_rating'] is not None]; iv=[r['imdb_votes'] for r in rows if r['imdb_votes'] is not None]; lr=[r['letterboxd_rating'] for r in rows if r['letterboxd_rating'] is not None]; lv=[r['letterboxd_votes'] for r in rows if r['letterboxd_votes'] is not None]
 t={'imdb_p75':q(ir,.75),'imdb_p90':q(ir,.9),'imdb_votes_median':q(iv,.5),'letterboxd_p75':q(lr,.75),'letterboxd_p90':q(lr,.9),'letterboxd_votes_median':q(lv,.5)}
 sim=[]
 for r in rows:
  routes=[]; evidence=[]; rank=r['rank']; inst,instsig=RECOGNITION.get(r['imdb_id'],(0,None))
  # Route 1: canon. Top 100 is sufficient; 101-250 needs an independent established signal already in production data.
  canon = rank<=100 or (rank<=250 and r['existing_bonus']>=1)
  if canon: routes.append('canon')
  # Route 2: institutional. A Best Picture winner / equivalent very strong film-level recognition qualifies directly.
  institutional = inst>=3
  if institutional: routes.append('institutional')
  # Audience breadth/strength is evidence, never a standalone route.
  im_strong=r['imdb_rating'] is not None and r['imdb_votes'] is not None and r['imdb_rating']>=t['imdb_p75'] and r['imdb_votes']>=t['imdb_votes_median']
  lb_strong=r['letterboxd_rating'] is not None and r['letterboxd_votes'] is not None and r['letterboxd_rating']>=t['letterboxd_p75'] and r['letterboxd_votes']>=t['letterboxd_votes_median']
  im_exc=r['imdb_rating'] is not None and r['imdb_votes'] is not None and r['imdb_rating']>=t['imdb_p90'] and r['imdb_votes']>=t['imdb_votes_median']
  lb_exc=r['letterboxd_rating'] is not None and r['letterboxd_votes'] is not None and r['letterboxd_rating']>=t['letterboxd_p90'] and r['letterboxd_votes']>=t['letterboxd_votes_median']
  # Route 3: audience-critical convergence. Requires TSPDT critical standing plus broad agreement on both audience systems.
  convergence = rank<=1000 and im_strong and lb_strong and (rank<=500 or im_exc or lb_exc)
  if convergence: routes.append('convergence')
  # Route 4: corroboration. Moderate canon + another independent film-level or broad-audience signal.
  corroboration = (rank<=250 and (inst>=1 or (im_strong and lb_strong))) or (rank<=500 and inst>=2)
  if corroboration and not routes: routes.append('corroboration')
  if instsig: evidence.append(instsig)
  if im_strong: evidence.append('IMDb strong/broad')
  if lb_strong: evidence.append('Letterboxd strong/broad')
  qualified=bool(routes)
  sim.append({**r,'institutional_strength':inst,'institutional_signal':instsig,'imdb_strong_broad':im_strong,'letterboxd_strong_broad':lb_strong,'routes':routes,'qualified':qualified,'evidence':evidence})
 old={r['imdb_id'] for r in rows if r['production_score']>=3}; new={r['imdb_id'] for r in sim if r['qualified']}
 out={'mode':'simulation-4-multi-route','production_unchanged':True,'candidate_universe':'TSPDT-only in phase A; union-universe expansion is next and deliberately separated from route calibration','route_rules':{'canon':'TSPDT top 100 OR top 250 + existing independent major signal','institutional':'very strong film-level recognition (strength 3)','convergence':'TSPDT top 1000 + strong/broad IMDb + strong/broad Letterboxd + (top 500 OR exceptional on either audience system)','corroboration':'TSPDT top 250 + institutional signal or dual strong/broad audience; OR top 500 + strong institutional signal'},'thresholds_used':{k:round(v,3) for k,v in t.items()},'counts':{'production_qualifiers':len(old),'route_qualifiers':len(new),'promoted':len(new-old),'demoted':len(old-new)},'route_counts':{x:sum(x in r['routes'] for r in sim) for x in ['canon','institutional','convergence','corroboration']},'calibration':sorted([r for r in sim if r['title'] in CALIBRATION],key=lambda x:x['rank']),'promoted':sorted([r for r in sim if r['imdb_id'] in new-old],key=lambda x:x['rank']),'demoted':sorted([r for r in sim if r['imdb_id'] in old-new],key=lambda x:x['rank'])}
 OUTPUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
 compact=[{'title':r['title'],'year':r['year'],'imdb_id':r['imdb_id'],'rank':r['rank'],'routes':r['routes'],'evidence':r['evidence']} for r in sim if r['qualified']]
 QUALIFIERS.write_text(json.dumps(compact,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'counts':out['counts'],'route_counts':out['route_counts']}))
if __name__=='__main__': main()
