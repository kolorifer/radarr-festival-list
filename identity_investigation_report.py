"""Private changed-case review artifact; never sends messages or applies proposals."""
import json
from identity_triage_store import private_path, digest
from identity_research_handoff import atomic_json


def write_report(state,snapshot,store):
    previous={};path=state/'review-report.json'
    try:
        private_path(path)
        previous=json.loads(path.read_text()).get('versions',{})
    except FileNotFoundError:pass
    with store.tx() as c:
        proposals={}
        for row in c.execute('select e.case_id,p.created,p.result,p.version from proposals p join evidence e on e.version=p.version order by p.created'):
            proposals[row['case_id']]={'created_at':row['created'],'evidence_version':row['version'],'result':json.loads(row['result'])}
        jobs={row['case_id']:dict(row) for row in c.execute('select case_id,status,version from jobs')}
    cases=[];all_cases=[];versions={}
    for case in snapshot['cases']:
        row=dict(case)
        row['research_status']=jobs.get(case['case_id'],{}).get('status','not_admitted')
        row['proposal']=proposals.get(case['case_id'])
        if row['proposal']:
            row['proposal']['current_evidence']=row['proposal']['evidence_version']==jobs.get(case['case_id'],{}).get('version')
        row['proposed_fix']='Review evidence before any identity correction; no automatic correction.'
        all_cases.append(row)
        stable={k:v for k,v in row.items() if k!='observed_at'}
        key=digest(stable);versions[row['case_id']]=key
        if previous.get(row['case_id'])!=key:cases.append(row)
    report={'version':1,'generated_at':snapshot['generated_at'],'coverage':snapshot['coverage'],
            'oldest_unresolved_age_seconds':max([snapshot['generated_at']-x['observed_at'] for x in snapshot['cases'] if x['route'] not in ('verified','routine')]+[0]),
            'budget':store.summary(),'cases':all_cases,'changed_cases':cases,'versions':versions,
            'telegram_digest_enabled':False,'review_controls_enabled':False,
            'unassessed_policy':'Announcements without explicit outcomes are not identification failures.',
            'historical_seeds':'Four existing proposals retained in the closed pilot; unchanged seeds are not reimported.'}
    # Keep each changed report until a human has seen it; daily no-change scans do not erase it.
    if cases:
        atomic_json(state/'review-changes.json',report)
    atomic_json(path,report)
    return len(cases)
