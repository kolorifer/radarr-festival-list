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
    valid_support=(isinstance(support,list) and len(support)==len(aliases)
                   and all(isinstance(r,dict) and r.get('query')==a and r.get('complete',True) is True
                           and isinstance(r.get('ids'),list) and r.get('count')==len(r['ids'])
                           and all(type(i)==int for i in r['ids']) for a,r in zip(aliases,support)))
    search_agrees=valid_support and set.intersection(*(set(r['ids']) for r in support))=={candidate['id']}
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
    audio=source.get('audio_language_codes')
    if audio is not None:
        if not isinstance(audio,list) or any(not isinstance(x,str) or not re.fullmatch('[a-z]{2,3}',x) for x in audio):raise ValueError('audio_languages')
        if cl is not None:
            features['language']=1.0 if cl in audio else 0.0;observed.append('language')
    elif sl is not None and cl is not None:
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
    if (sr is not None or sl is not None or bool(audio)) and source.get('nfo_bound') is not True:blocks.append('nfo_not_bound_to_release')
    edition=source.get('edition_evidence')
    edition_applied=False
    # Packaging evidence cannot bypass any identity, alias or provenance guard.
    if (isinstance(edition,dict) and edition.get('candidate_id')==candidate['id']
        and edition.get('source') and edition.get('retrieved') and not blocks
        and source.get('nfo_bound') is True and len(aliases)==1
        and features['year']==1 and features['runtime']>0 and features['language']==1
        and features['source_id']==1
        and edition.get('movie_title') in titles
        and words(source['title']) in (words(edition['label'])+words(edition['movie_title']),
                                       words(edition['movie_title'])+words(edition['label']))):
        features['title']=1.0; edition_applied=True
    contributions={k:policy.weights[k]*v for k,v in features.items()}
    # Missing rival facts must not create a falsely large winning margin.
    comparable={'title':True,'year':sy is not None,'runtime':sr is not None,'language':sl is not None or bool(audio),'source_id':si is not None}
    upper=sum(contributions.values())+sum(policy.weights[k] for k in comparable if comparable[k] and k not in observed)
    if candidate.get('evidence_status')=='search_only':
        upper=sum(policy.weights.values()) # Missing aliases/dates/details cannot prove a rival irrelevant.
    return {**({'evidence_status':'search_only'} if candidate.get('evidence_status')=='search_only' else {}),'upper_score':upper,'candidate_id':candidate['id'],'title':titles[0], 'score':sum(contributions.values()),
            'contributions':contributions,'observed_attributes':observed,'title_similarity':similarity,
            'matched_title':edition['movie_title'] if edition_applied else titles[similarities.index(similarity)],
            **({'edition_resolution':edition} if edition_applied else {}),'blocks':blocks}


def resolve_alias_comparison(source, ranked, complete, policy=None):
    """Resolve only an alias gate, using a complete, strongly evidenced comparison.

    Also accepts retained ranked evidence for offline shadow re-evaluation. Never
    clears ID, sequel, provenance, NFO or source-conflict blocks.
    """
    policy=policy or Policy()
    if complete is not True or not ranked:return False
    top=ranked[0]; aliases=source_titles(source['title'])
    support=source.get('alias_search_support',[])
    if len(aliases)!=2 or not isinstance(support,list) or len(support)!=2:return False
    ids={r['candidate_id'] for r in ranked}
    if len(ids)!=len(ranked):return False
    for alias,row in zip(aliases,support):
        if (not isinstance(row,dict) or row.get('query')!=alias or row.get('complete') is not True
            or not isinstance(row.get('ids'),list) or row.get('count')!=len(row['ids'])
            or any(type(i)!=int for i in row['ids']) or len(set(row['ids']))!=len(row['ids'])
            or not set(row['ids'])<=ids or top['candidate_id'] not in row['ids']):return False
    if top['blocks']!=['source_alias_not_corroborated']:return False
    if source.get('checked_listing') is not True or source.get('conflicting_evidence') is not False or source.get('nfo_bound') is not True:return False
    if any(r.get('evidence_status')=='search_only' or set(r['observed_attributes'])!=set(policy.weights) for r in ranked):return False
    points=top['contributions']
    if any(points[k]!=policy.weights[k] for k in ('title','year','source_id')) or points['runtime']<=0 or points['language']<=0:return False
    margin=top['score']-max([r['upper_score'] for r in ranked[1:]] or [0])
    if top['score']<policy.threshold or margin<policy.margin:return False
    top['blocks'].remove('source_alias_not_corroborated')
    return True


def bound_identity_rivals(source, ranked, complete, policy=None):
    """Conditional bounds from a unique checked ID, not title-summary guesses.

    Unknown aliases/years can still earn their full weights. Only the identity
    weight is unavailable to a different ID under the verified unique crosswalk.
    """
    policy=policy or Policy()
    ident=source.get('unique_tracker_movie_id')
    if type(ident)!=int or not ranked:return None
    top=ranked[0];points=top['contributions']
    if (top['candidate_id']!=ident or top['blocks']
        or source.get('checked_listing') is not True
        or source.get('conflicting_evidence') is not False or source.get('nfo_bound') is not True
        or any(points[k]!=policy.weights[k] for k in ('title','year','source_id'))
        or points['runtime']<=0 or points['language']<=0):return None
    # A known second record asserting the same IMDb contradicts uniqueness.
    if any(r['candidate_id']!=ident and r['contributions']['source_id']>0 for r in ranked):
        return {'status':'conflicting_duplicate_mapping'}
    cap=sum(policy.weights.values())-policy.weights['source_id']
    for rival in ranked[1:]:
        identity=min(0,rival['contributions']['source_id'])
        previous=rival['upper_score']
        rival['upper_score']=min(previous,cap+identity)
        rival['upper_bound_basis']='unique_checked_tracker_mapping'
    return {'status':'bounded','basis':'unique_checked_tracker_mapping',
            'mapped_candidate_id':ident,'unseen_upper_score':cap if complete is not True else None,
            'search_complete':complete is True,
            'assumption':'unique_mapping_current_unless_contradictory_evidence'}


def evaluate(case,policy=None):
    policy=policy or Policy();candidates=case.get('candidates')
    if not isinstance(candidates,list) or len(candidates)>100:raise ValueError('candidate_capacity')
    ranked=[score_candidate(case['source'],c,policy) for c in candidates]
    if len({r['candidate_id'] for r in ranked})!=len(ranked):raise ValueError('duplicate_candidate')
    ranked.sort(key=lambda r:(-r['score'],r['candidate_id']))
    if not ranked:return {'decision':'review','selected_id':None,'ranked':[],'margin':None,'reasons':['no_candidates']}
    bounded=bound_identity_rivals(case['source'],ranked,case.get('candidate_set_complete'),policy)
    unseen=[bounded['unseen_upper_score']] if bounded and bounded.get('unseen_upper_score') is not None else []
    top=ranked[0];margin=top['score']-max([r['upper_score'] for r in ranked[1:]]+unseen or [0])
    resolved=resolve_alias_comparison(case['source'],ranked,case.get('candidate_set_complete'),policy)
    reasons=list(top['blocks'])
    if bounded and bounded['status']=='conflicting_duplicate_mapping':reasons.append('conflicting_duplicate_mapping')
    if case.get('candidate_set_complete') is not True and not (bounded and bounded['status']=='bounded'):reasons.append('candidate_set_incomplete')
    if top['score']<policy.threshold:reasons.append('score_below_threshold')
    if margin<policy.margin:reasons.append('insufficient_margin')
    accepted=not reasons
    return {'decision':'would_identify' if accepted else 'review','selected_id':top['candidate_id'] if accepted else None,
            'ranked':ranked,'margin':margin,'reasons':reasons,
            **({'rival_bound_audit':bounded} if bounded else {}),
            **({'alias_resolution':'complete_candidate_comparison'} if resolved else {})}
