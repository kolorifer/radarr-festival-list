"""Reproducible local-only report: python -m research.identity_scoring.evaluate."""
import argparse
from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from .scorer import Policy,evaluate

FIXTURES=Path(__file__).with_name('cases.json')

def controls(cases):
    base=next(c for c in cases if c['name']=='2018 Everyone Is a Hero')
    output=[]
    def add(name,change,expected='review'):
        case=deepcopy(base);case.update(name=name,kind='synthetic_control',expected_id=None,expected_decision=expected)
        change(case);output.append(case)
    add('Two-minute runtime difference',lambda c:None,'would_identify')
    add('Five-minute runtime difference (proposed boundary)',lambda c:c['source'].update(runtime=145),'would_identify')
    add('Six-minute runtime difference',lambda c:c['source'].update(runtime=144))
    add('Missing runtime',lambda c:c['source'].update(runtime=None))
    add('Missing audio language',lambda c:c['source'].update(language=None))
    add('Missing source year',lambda c:c['source'].update(year=None))
    add('Title and year only',lambda c:c['source'].update(runtime=None,language=None))
    add('Contradictory year',lambda c:c['source'].update(year=1999))
    add('Contradictory audio language',lambda c:c['source'].update(language='fr'))
    add('Conflicting source IMDb',lambda c:c['source'].update(imdb='tt1234567'))
    add('Crosswalk unverified',lambda c:c['candidates'][0].update(crosswalk_verified=False))
    add('Listing not checked',lambda c:c['source'].update(checked_listing=False))
    add('NFO from another release',lambda c:c['source'].update(nfo_bound=False))
    add('Source contradiction flagged',lambda c:c['source'].update(conflicting_evidence=True))
    add('Incomplete candidate set',lambda c:c.update(candidate_set_complete=False))
    add('TV candidate',lambda c:c['candidates'][0].update(media_type='tv'))
    add('Wrong numeric title',lambda c:c['candidates'][0].update(titles=['2019','2019 Everyone Is a Hero']))
    def rival(c,**values):
        other=deepcopy(c['candidates'][0]);other.update(id=999999,imdb='tt1234567',**values);c['candidates'].append(other)
    add('Equally supported competing movie',lambda c:rival(c))
    add('Close competing movie',lambda c:rival(c,runtime=136))
    add('Rival missing runtime and language',lambda c:rival(c,runtime=None,language=None))
    return output


def result(case,policy):
    r=evaluate(case,policy)
    expected=case.get('expected_id');selected=r['selected_id']
    return {'name':case['name'],'kind':case['kind'],'baseline':case.get('baseline'),
            'expected_id':expected,'expected_decision':case.get('expected_decision'),
            'changed_from_baseline':case.get('baseline') in ('identify','review') and ((case['baseline']=='identify')!=(r['decision']=='would_identify')),
            'wrong_labeled_automatic_choice':selected is not None and expected is not None and selected!=expected,
            **r}


def report(document):
    cases=document['cases'];synthetic=controls(cases);p=Policy()
    real=[result(c,p) for c in cases];stress=[result(c,p) for c in synthetic]
    sensitivity=[]
    for threshold in (65.,68.,70.,72.,75.,78.):
        policy=Policy(threshold=threshold)
        sensitivity.append({'threshold':threshold,
            'real_would_identify':[c['name'] for c in cases if evaluate(c,policy)['decision']=='would_identify'],
            'synthetic_changes_from_proposal':[c['name'] for c in synthetic if evaluate(c,policy)['decision']!=evaluate(c,p)['decision']]})
    runtime=[]
    for scale in (.05,.10,.20):
        policy=Policy(runtime_scale=scale)
        runtime.append({'runtime_scale':scale,'real_would_identify':[c['name'] for c in cases if evaluate(c,policy)['decision']=='would_identify'],
            'synthetic_changes_from_proposal':[c['name'] for c in synthetic if evaluate(c,policy)['decision']!=evaluate(c,p)['decision']]})
    margins=[]
    for margin in (5.,10.,15.,20.):
        policy=Policy(margin=margin)
        margins.append({'margin':margin,'synthetic_changes_from_proposal':[c['name'] for c in synthetic if evaluate(c,policy)['decision']!=evaluate(c,p)['decision']]})
    weights=[]
    for name,w in [('equal_weights',dict.fromkeys(p.weights,20.)),('less_id_more_runtime',dict(title=30.,year=20.,runtime=20.,language=10.,source_id=20.)),('less_runtime_more_title',dict(title=35.,year=20.,runtime=10.,language=10.,source_id=25.))]:
        policy=Policy(weights=w)
        weights.append({'name':name,'weights':w,'real_would_identify':[c['name'] for c in cases if evaluate(c,policy)['decision']=='would_identify']})
    omitted=deepcopy(next(c for c in cases if c['name']=='2018 Everyone Is a Hero'))
    omitted.update(name='Synthetic retrieval blind spot: correct movie absent, indistinguishable wrong candidate',kind='synthetic_blind_spot')
    omitted['candidates'][0].update(id=999999,imdb='tt1234567')
    blind_spot=result(omitted,p)
    return {'synthetic_blind_spots':[blind_spot],'scope':'OFFLINE ONLY — no production integration','policy':asdict(p),'cases':real,'synthetic_controls':stress,
            'threshold_sensitivity':sensitivity,'runtime_sensitivity':runtime,'margin_sensitivity':margins,'weight_sensitivity':weights,
            'limitations':document['limitations']}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path);args=parser.parse_args()
    raw=FIXTURES.read_bytes();r=report(json.loads(raw));r['fixture_sha256']=hashlib.sha256(raw).hexdigest()
    text=json.dumps(r,ensure_ascii=False,indent=2)+'\n'
    if args.output:args.output.write_text(text)
    else:print(text,end='')

if __name__=='__main__':main()
