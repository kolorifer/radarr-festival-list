"""Research-only scoring simulation. Does not modify production backcatalog scoring."""
import json
import math
from pathlib import Path

BACKCATALOG=Path("backcatalog-details.json"); AUDIENCE=Path("audience-ratings.json"); OUTPUT=Path("scoring-simulation.json"); QUALIFIERS=Path("simulation-qualifiers.json")
RECOGNITION={
"tt2543164":(.50,"Academy Best Picture nominee"),"tt2024544":(1.50,"Academy Best Picture winner"),"tt1454468":(.50,"Academy Best Picture nominee"),"tt0993846":(.50,"Academy Best Picture nominee"),
"tt2042568":(.50,"Cannes Grand Prix"),"tt2758880":(.50,"Cannes Jury Prize"),"tt3808342":(1.00,"Academy Foreign Language Film winner + Cannes Grand Prix"),"tt3508840":(.50,"Cannes Best Director")}
def q(v,x):
 v=sorted(n for n in v if isinstance(n,(int,float))); p=(len(v)-1)*x; lo=math.floor(p); hi=math.ceil(p); return v[lo] if lo==hi else v[lo]*(hi-p)+v[hi]*(p-lo)
def revised(r):
 return 5 if r<=25 else 4 if r<=50 else 3 if r<=100 else 2.5 if r<=150 else 2 if r<=250 else 1 if r<=500 else .5
def prod(r):
 return 5 if r<=25 else 4 if r<=50 else 3 if r<=100 else 2 if r<=250 else 1 if r<=500 else .5
def audience(r,t):
 b=0; s=[]
 for rating,votes,strong,exceptional,floor,median,sw,ew,label in [(r['letterboxd_rating'],r['letterboxd_votes'],t['letterboxd_strong'],t['letterboxd_exceptional'],t['letterboxd_vote_floor'],t['letterboxd_votes_median'],.25,.5,'Letterboxd'),(r['imdb_rating'],r['imdb_votes'],t['imdb_strong'],t['imdb_exceptional'],t['imdb_vote_floor'],t['imdb_votes_median'],.125,.25,'IMDb')]:
  if rating is None or votes is None: continue
  raw=ew if rating>=exceptional else sw if rating>=strong else 0
  conf=1 if votes>=median else .5 if votes>=floor else 0
  if raw*conf: b+=raw*conf; s.append(f"{label} {'exceptional' if raw==ew else 'strong'} x{conf:g} confidence")
 return min(.5,b),s
def main():
 back=json.loads(BACKCATALOG.read_text()); aud=json.loads(AUDIENCE.read_text()); ratings=aud['ratings']; rows=[]
 for c in back['candidates']:
  rr=ratings.get(c['imdb_id'],{}).get('reeldb',{}); im=rr.get('imdb') or {}; lb=rr.get('letterboxd') or {}
  rows.append({'title':c['title'],'year':c['year'],'imdb_id':c['imdb_id'],'rank':c['tspdt_rank'],'production_score':c['score'],'existing_bonus':round(float(c['score'])-prod(c['tspdt_rank']),3),'imdb_rating':im.get('rating'),'imdb_votes':im.get('votes'),'letterboxd_rating':lb.get('rating'),'letterboxd_votes':lb.get('votes')})
 ir=[r['imdb_rating'] for r in rows if r['imdb_rating'] is not None]; iv=[r['imdb_votes'] for r in rows if r['imdb_votes'] is not None]; lr=[r['letterboxd_rating'] for r in rows if r['letterboxd_rating'] is not None]; lv=[r['letterboxd_votes'] for r in rows if r['letterboxd_votes'] is not None]
 t={'imdb_strong':round(q(ir,.75),3),'imdb_exceptional':round(q(ir,.9),3),'letterboxd_strong':round(q(lr,.75),3),'letterboxd_exceptional':round(q(lr,.9),3),'imdb_vote_floor':round(q(iv,.1)),'letterboxd_vote_floor':round(q(lv,.1)),'imdb_votes_median':round(q(iv,.5)),'letterboxd_votes_median':round(q(lv,.5))}
 sim=[]
 for r in rows:
  ab,asig=audience(r,t); rb,rsig=RECOGNITION.get(r['imdb_id'],(0,None)); score=round(revised(r['rank'])+r['existing_bonus']+ab+rb,3); sim.append({**r,'audience_bonus':ab,'audience_signals':asig,'recognition_bonus':rb,'recognition_signal':rsig,'simulated_score':score})
 old={r['imdb_id'] for r in rows if r['production_score']>=3}; new={r['imdb_id'] for r in sim if r['simulated_score']>=3}; promoted=sorted([r for r in sim if r['imdb_id'] in new-old],key=lambda x:(-x['simulated_score'],x['rank'])); near=sorted([r for r in sim if 2.5<=r['simulated_score']<3],key=lambda x:(-x['simulated_score'],x['rank']))
 names={'Arrival','12 Years a Slave','Gravity','The Wolf of Wall Street','La Commune (Paris, 1871)','Inside Llewyn Davis','Son of Saul','The Assassin'}
 out={'mode':'simulation-2-verified-recognition','production_unchanged':True,'thresholds_used':t,'counts':{'production_qualifiers':len(old),'simulated_qualifiers':len(new),'promoted':len(promoted),'demoted':0,'near_below':len(near)},'calibration':sorted([r for r in sim if r['title'] in names],key=lambda x:x['rank']),'promoted':promoted,'near_below':near}
 OUTPUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
 compact=[{'title':r['title'],'year':r['year'],'imdb_id':r['imdb_id'],'rank':r['rank'],'score':r['simulated_score'],'audience_bonus':r['audience_bonus'],'recognition_bonus':r['recognition_bonus'],'recognition_signal':r['recognition_signal']} for r in sorted(sim,key=lambda x:(-x['simulated_score'],x['rank'])) if r['simulated_score']>=3]
 QUALIFIERS.write_text(json.dumps(compact,ensure_ascii=False,separators=(',',':'))+'\n')
 print(json.dumps({'counts':out['counts'],'qualifiers':len(compact)}))
if __name__=='__main__': main()
