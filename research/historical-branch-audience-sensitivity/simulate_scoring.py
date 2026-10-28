"""Research-only Phase B union-universe simulation. Production scoring is untouched."""
import json, math
from pathlib import Path

BACKCATALOG=Path("backcatalog-details.json"); AUDIENCE=Path("audience-ratings.json")
INSTITUTIONAL=Path("sources/phase-b-institutional.json")
OUTPUT=Path("scoring-simulation.json"); QUALIFIERS=Path("simulation-qualifiers.json"); PROMOTED=Path("simulation-promoted.json"); NEW=Path("simulation-phase-b-new.json")

# Existing Phase-A film-level recognition. Values are evidence strength, not additive points.
RECOGNITION={
"tt2543164":(1,"Academy Best Picture nominee"),"tt2024544":(3,"Academy Best Picture winner"),
"tt1454468":(1,"Academy Best Picture nominee"),"tt0993846":(1,"Academy Best Picture nominee"),
"tt2042568":(1,"Cannes Grand Prix"),"tt2400275":(1,"Cannes Jury Prize"),
"tt3808342":(2,"Academy International Feature winner + Cannes Grand Prix"),"tt3508840":(1,"Cannes Best Director"),
"tt0407887":(3,"Academy Best Picture winner"),"tt4034228":(1,"Academy Best Picture nominee"),"tt3464902":(1,"Cannes Jury Prize"),
}

def q(v,x):
 v=sorted(n for n in v if isinstance(n,(int,float))); p=(len(v)-1)*x; lo=math.floor(p); hi=math.ceil(p)
 return v[lo] if lo==hi else v[lo]*(hi-p)+v[hi]*(p-lo)
def prod_base(r): return 5 if r<=25 else 4 if r<=50 else 3 if r<=100 else 2 if r<=250 else 1 if r<=500 else .5

def main():
 back=json.loads(BACKCATALOG.read_text()); aud=json.loads(AUDIENCE.read_text()); ratings=aud['ratings']; rows=[]
 for c in back['candidates']:
  rr=ratings.get(c['imdb_id'],{}).get('reeldb',{}); im=rr.get('imdb') or {}; lb=rr.get('letterboxd') or {}
  rows.append({'title':c['title'],'year':c['year'],'imdb_id':c['imdb_id'],'rank':c['tspdt_rank'],'production_score':c['score'],'existing_bonus':round(float(c['score'])-prod_base(c['tspdt_rank']),3),'imdb_rating':im.get('rating'),'imdb_votes':im.get('votes'),'letterboxd_rating':lb.get('rating'),'letterboxd_votes':lb.get('votes'),'candidate_sources':['TSPDT']})
 # Thresholds stay frozen from the original TSPDT audience population so universe expansion cannot move the goalposts.
 ir=[r['imdb_rating'] for r in rows if r['imdb_rating'] is not None]; iv=[r['imdb_votes'] for r in rows if r['imdb_votes'] is not None]; lr=[r['letterboxd_rating'] for r in rows if r['letterboxd_rating'] is not None]; lv=[r['letterboxd_votes'] for r in rows if r['letterboxd_votes'] is not None]
 t={'imdb_p75':q(ir,.75),'imdb_p90':q(ir,.9),'imdb_votes_median':q(iv,.5),'letterboxd_p75':q(lr,.75),'letterboxd_p90':q(lr,.9),'letterboxd_votes_median':q(lv,.5)}
 byid={r['imdb_id']:r for r in rows}
 external=json.loads(INSTITUTIONAL.read_text())['films']
 for f in external:
  if f['imdb_id'] in byid:
   byid[f['imdb_id']]['candidate_sources'].append('institutional')
  else:
   rr=ratings.get(f['imdb_id'],{}).get('reeldb',{}); im=rr.get('imdb') or {}; lb=rr.get('letterboxd') or {}
   row={'title':f['title'],'year':f['year'],'imdb_id':f['imdb_id'],'rank':None,'production_score':0,'existing_bonus':0,'imdb_rating':im.get('rating'),'imdb_votes':im.get('votes'),'letterboxd_rating':lb.get('rating'),'letterboxd_votes':lb.get('votes'),'candidate_sources':['institutional']}
   rows.append(row); byid[f['imdb_id']]=row
 extmap={f['imdb_id']:(f['institutional_strength'],' + '.join(f['signals'])) for f in external}
 sim=[]
 for r in rows:
  routes=[]; evidence=[]; rank=r['rank']; inst,instsig=extmap.get(r['imdb_id'],RECOGNITION.get(r['imdb_id'],(0,None)))
  canon = rank is not None and (rank<=100 or (rank<=250 and r['existing_bonus']>=1))
  if canon: routes.append('canon')
  institutional = inst>=3
  if institutional: routes.append('institutional')
  im_strong=r['imdb_rating'] is not None and r['imdb_votes'] is not None and r['imdb_rating']>=t['imdb_p75'] and r['imdb_votes']>=t['imdb_votes_median']
  lb_strong=r['letterboxd_rating'] is not None and r['letterboxd_votes'] is not None and r['letterboxd_rating']>=t['letterboxd_p75'] and r['letterboxd_votes']>=t['letterboxd_votes_median']
  im_exc=r['imdb_rating'] is not None and r['imdb_votes'] is not None and r['imdb_rating']>=t['imdb_p90'] and r['imdb_votes']>=t['imdb_votes_median']
  lb_exc=r['letterboxd_rating'] is not None and r['letterboxd_votes'] is not None and r['letterboxd_rating']>=t['letterboxd_p90'] and r['letterboxd_votes']>=t['letterboxd_votes_median']
  if rank is not None:
   convergence=im_strong and lb_strong and (rank<=500 or im_exc or lb_exc)
   corroboration=(rank<=250 and (inst>=1 or (im_strong and lb_strong))) or (rank<=500 and inst>=2)
  else:
   # Outside TSPDT, audience never qualifies by itself. It must corroborate independent institutional evidence.
   convergence=inst>=1 and im_strong and lb_strong and (im_exc or lb_exc)
   corroboration=inst>=2 and (im_strong or lb_strong)
  if convergence: routes.append('convergence')
  if corroboration and not routes: routes.append('corroboration')
  if instsig: evidence.append(instsig)
  if im_strong: evidence.append('IMDb strong/broad')
  if lb_strong: evidence.append('Letterboxd strong/broad')
  sim.append({**r,'institutional_strength':inst,'institutional_signal':instsig,'imdb_strong_broad':im_strong,'letterboxd_strong_broad':lb_strong,'routes':routes,'qualified':bool(routes),'evidence':evidence})
 old={r['imdb_id'] for r in rows if r['production_score']>=3}; new={r['imdb_id'] for r in sim if r['qualified']}
 promoted=sorted([r for r in sim if r['imdb_id'] in new-old],key=lambda x:(x['rank'] is None,x['rank'] or 99999,x['title']))
 phaseb=sorted([r for r in sim if r['rank'] is None],key=lambda x:x['title'])
 out={'mode':'simulation-4b-union-universe','production_unchanged':True,'candidate_universe':'TSPDT union independently verified film-level institutional sources (Phase B seed)','threshold_policy':'Audience thresholds frozen from TSPDT population before union expansion','thresholds_used':{k:round(v,3) for k,v in t.items()},'counts':{'candidate_universe':len(rows),'tspdt_candidates':sum(r['rank'] is not None for r in rows),'outside_tspdt_candidates':len(phaseb),'production_qualifiers':len(old),'route_qualifiers':len(new),'promoted':len(new-old),'outside_tspdt_qualifiers':sum(r['qualified'] for r in phaseb)},'route_counts':{x:sum(x in r['routes'] for r in sim) for x in ['canon','institutional','convergence','corroboration']},'phase_b_new':phaseb,'promoted':promoted}
 OUTPUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
 compact=[{'title':r['title'],'year':r['year'],'imdb_id':r['imdb_id'],'rank':r['rank'],'sources':r['candidate_sources'],'routes':r['routes'],'evidence':r['evidence']} for r in sim if r['qualified']]
 QUALIFIERS.write_text(json.dumps(compact,ensure_ascii=False,indent=2)+'\n')
 PROMOTED.write_text(json.dumps([{'title':r['title'],'year':r['year'],'imdb_id':r['imdb_id'],'rank':r['rank'],'routes':r['routes'],'evidence':r['evidence']} for r in promoted],ensure_ascii=False,indent=2)+'\n')
 NEW.write_text(json.dumps([{'title':r['title'],'year':r['year'],'imdb_id':r['imdb_id'],'qualified':r['qualified'],'routes':r['routes'],'evidence':r['evidence'],'imdb_rating':r['imdb_rating'],'imdb_votes':r['imdb_votes'],'letterboxd_rating':r['letterboxd_rating'],'letterboxd_votes':r['letterboxd_votes']} for r in phaseb],ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(out['counts']))
if __name__=='__main__': main()
