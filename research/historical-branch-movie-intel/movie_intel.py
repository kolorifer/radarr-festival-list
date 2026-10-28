"""Local lookup core for enriched autobrr notifications."""
import json,re
from pathlib import Path
ROOT=Path(__file__).parent

def _load(path,default):
 try:return json.loads((ROOT/path).read_text())
 except (OSError,json.JSONDecodeError):return default

def _norm(s):return re.sub(r'[^a-z0-9]+','',str(s).lower())

def build_index():
 audience=_load('audience-ratings.json',{}).get('ratings',{})
 qualifiers={x['imdb_id']:x for x in _load('simulation-qualifiers.json',[]) if x.get('imdb_id')}
 institutional={x['imdb_id']:x for x in _load('sources/phase-b-institutional.json',{}).get('films',[]) if x.get('imdb_id')}
 candidates={x['imdb_id']:x for x in _load('backcatalog-details.json',{}).get('candidates',[]) if x.get('imdb_id')}
 ids=set(audience)|set(qualifiers)|set(institutional)|set(candidates)
 out={}
 for iid in ids:
  c=candidates.get(iid,{}) ; inst=institutional.get(iid,{}) ; q=qualifiers.get(iid,{})
  title=c.get('title') or inst.get('title') or q.get('title'); year=c.get('year') or inst.get('year') or q.get('year')
  rr=(audience.get(iid) or {}).get('reeldb') or {}
  out[iid]={'imdb_id':iid,'title':title,'year':year,'tspdt_rank':c.get('tspdt_rank'),'imdb':rr.get('imdb') or {},'letterboxd':rr.get('letterboxd') or {},'institutional_signals':inst.get('signals',[]),'institutional_strength':inst.get('institutional_strength',0),'qualified':bool(q),'routes':q.get('routes',[]),'evidence':q.get('evidence',[])}
 return out

def find_local(title,year,index=None):
 index=index or build_index(); key=_norm(title); hits=[]
 for row in index.values():
  if row.get('title') and _norm(row['title'])==key and (not year or str(row.get('year'))==str(year)):hits.append(row)
 return hits[0] if len(hits)==1 else None

def rejection_class(rejections):
 text=' '.join(rejections or []).lower()
 if 'unknown movie' in text:return 'unknown_movie'
 if 'quality' in text:return 'quality'
 if 'upgrade' in text:return 'not_upgrade'
 if 'existing' in text or 'already' in text:return 'existing'
 return 'other'
