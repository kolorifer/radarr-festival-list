"""OFFLINE experiment. Pure functions; no runtime, provider or action imports.

Scores are proposed evidence points, NOT calibrated probabilities. Missing
attributes score zero with fixed weights (never renormalized). Gate results are
reported separately from arithmetic, so conflicting source IDs cannot be bought
out by many weak matches. Inputs must be provenance-checked by the caller.
"""
from dataclasses import dataclass, field
import math
import re
import unicodedata

WEIGHTS = {'title':30.0, 'year':20.0, 'runtime':15.0, 'language':10.0, 'source_id':25.0}

@dataclass(frozen=True)
class Policy:
    weights: dict = field(default_factory=lambda:dict(WEIGHTS))
    threshold: float = 70.0
    margin: float = 15.0
    runtime_scale: float = .10

    def __post_init__(self):
        if set(self.weights)!=set(WEIGHTS) or any(not finite(x) or x<0 for x in self.weights.values()) or not math.isclose(sum(self.weights.values()),100):
            raise ValueError('weights_must_sum_to_100')
        if not finite(self.threshold) or not 0<=self.threshold<=100 or not finite(self.margin) or not 0<self.margin<=100 or not finite(self.runtime_scale) or not 0<self.runtime_scale<=1:
            raise ValueError('policy_bounds')


def finite(value):
    return type(value) in (int,float) and math.isfinite(value)


def words(value):
    if not isinstance(value,str) or not value.strip() or len(value)>256:raise ValueError('bounded_title')
    return re.findall(r'[^\W_]+',unicodedata.normalize('NFC',value).casefold().replace('&','and'))


def source_titles(value):
    """Only an explicit, bounded AKA pair; never guess punctuation as aliases."""
    words(value)
    parts=re.split(r'\s+(?:aka|a\.k\.a\.)\s+', value, flags=re.I)
    return parts if len(parts)==2 and all(p.strip() for p in parts) else [value]


def title_similarity(left,right):
    a,b=words(left),words(right)
    # Preserve the existing protection against fuzzy changes to sequel numbers.
    numbers=lambda ws:[x for x in ws if any(c.isdigit() for c in x) or re.fullmatch(r'[ivxlcdm]+',x)]
    if numbers(a)!=numbers(b):return 0.0
    a,b=''.join(a),''.join(b)
    if not a or not b:raise ValueError('empty_title')
    row=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        new=[i]
        for j,y in enumerate(b,1):new.append(min(new[-1]+1,row[j]+1,row[j-1]+(x!=y)))
        row=new
    return 1-row[-1]/max(len(a),len(b))


def valid_year(y):
    return type(y)==int and 1888<=y<=2100


def valid_runtime(r):
    return finite(r) and 0<r<=1440


def score_candidate(source,candidate,policy=None):
    policy=policy or Policy()
    titles=candidate.get('titles',[])
    if not isinstance(titles,list) or not 1<=len(titles)<=100:raise ValueError('titles')
    aliases=source_titles(source['title'])
    similarities=[max(title_similarity(a,t) for a in aliases) for t in titles]
    similarity=max(similarities)
    years=candidate.get('years',[])
    if not isinstance(years,list) or len(years)>100 or any(not valid_year(y) for y in years):raise ValueError('years')
    sy=source.get('year')
    if sy is not None and not valid_year(sy):raise ValueError('source_year')
    features={'title':2*similarity-1,'year':0.0,'runtime':0.0,'language':0.0,'source_id':0.0}
    observed=['title'];blocks=[]
    # An arbitrary second name cannot lend its score to an unrelated release.
    sequel=lambda value:[w for w in words(value) if any(c.isdigit() for c in w) or re.fullmatch(r'[ivxlcdm]+',w)]
    if len(aliases)>1 and sequel(aliases[0])!=sequel(aliases[1]):
        blocks.append('source_alias_sequel_conflict')
    catalog_aliases=[any(words(a)==words(t) for t in titles) for a in aliases]
    support=source.get('alias_search_support',[])
    # Search agreement is supporting evidence, not independent proof. Require
    # a documented alias, year and checked unique tracker-ID crosswalk as well.
    search_agrees=(isinstance(support,list) and len(support)==len(aliases)
                   and all(isinstance(r,dict) and r.get('query')==a
                           and r.get('ids')==[candidate['id']] and r.get('count')==1
                           for a,r in zip(aliases,support)))
    corroborated=(search_agrees and any(catalog_aliases) and sy in years
                  and source.get('checked_listing') is True
                  and source.get('imdb') is not None and source.get('imdb')==candidate.get('imdb')
                  and candidate.get('crosswalk_verified') is True)
    if len(aliases)>1 and not all(catalog_aliases) and not corroborated:
        blocks.append('source_alias_not_corroborated')
    if sy is not None and years:
        features['year']=1.0 if sy in years else -1.0;observed.append('year')
    sr,cr=source.get('runtime'),candidate.get('runtime')
    for value in (sr,cr):
        if value is not None and not valid_runtime(value):raise ValueError('runtime')
    if sr is not None and cr is not None:
        features['runtime']=max(-1.0,1-abs(sr-cr)/cr/policy.runtime_scale);observed.append('runtime')
    sl,cl=source.get('language'),candidate.get('language')
    for value in (sl,cl):
        if value is not None and (not isinstance(value,str) or not re.fullmatch('[a-z]{2,3}',value)):raise ValueError('language')
    if sl is not None and cl is not None:
        features['language']=1.0 if sl==cl else -1.0;observed.append('language')
    si,ci=source.get('imdb'),candidate.get('imdb')
    for value in (si,ci):
        if value is not None and (not isinstance(value,str) or not re.fullmatch(r'tt[0-9]{7,10}',value)):raise ValueError('imdb')
    if si is not None and ci is not None:
        features['source_id']=1.0 if si==ci else -1.0;observed.append('source_id')
        if si!=ci:blocks.append('tracker_id_conflict')
    if type(candidate.get('id'))!=int or not 0<candidate['id']<2**31:raise ValueError('candidate_id')
    if candidate.get('media_type')!='movie':blocks.append('not_movie')
    if candidate.get('crosswalk_verified') is not True or ci is None:blocks.append('crosswalk_unverified')
    if source.get('checked_listing') is not True:blocks.append('source_not_checked')
    if source.get('conflicting_evidence') is not False:blocks.append('source_conflict_or_unknown')
    if (sr is not None or sl is not None) and source.get('nfo_bound') is not True:blocks.append('nfo_not_bound_to_release')
    contributions={k:policy.weights[k]*v for k,v in features.items()}
    # Missing rival facts must not create a falsely large winning margin.
    comparable={'title':True,'year':sy is not None,'runtime':sr is not None,'language':sl is not None,'source_id':si is not None}
    upper=sum(contributions.values())+sum(policy.weights[k] for k in comparable if comparable[k] and k not in observed)
    return {'upper_score':upper,'candidate_id':candidate['id'],'title':titles[0], 'score':sum(contributions.values()),
            'contributions':contributions,'observed_attributes':observed,'title_similarity':similarity,
            'matched_title':titles[similarities.index(similarity)],'blocks':blocks}


def evaluate(case,policy=None):
    policy=policy or Policy();candidates=case.get('candidates')
    if not isinstance(candidates,list) or len(candidates)>100:raise ValueError('candidate_capacity')
    ranked=[score_candidate(case['source'],c,policy) for c in candidates]
    if len({r['candidate_id'] for r in ranked})!=len(ranked):raise ValueError('duplicate_candidate')
    ranked.sort(key=lambda r:(-r['score'],r['candidate_id']))
    if not ranked:return {'decision':'review','selected_id':None,'ranked':[],'margin':None,'reasons':['no_candidates']}
    top=ranked[0];margin=top['score']-max([r['upper_score'] for r in ranked[1:]] or [0])
    reasons=list(top['blocks'])
    if case.get('candidate_set_complete') is not True:reasons.append('candidate_set_incomplete')
    if top['score']<policy.threshold:reasons.append('score_below_threshold')
    if margin<policy.margin:reasons.append('insufficient_margin')
    accepted=not reasons
    return {'decision':'would_identify' if accepted else 'review','selected_id':top['candidate_id'] if accepted else None,
            'ranked':ranked,'margin':margin,'reasons':reasons}
