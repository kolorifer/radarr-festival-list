"""Operator-only, bounded reconciliation after identity-rule deployments.

No scheduler, provider, acquisition or notification entry point. Caller prepares
fresh metadata-only outcomes, stops the actor/digest before publishing, and uses
its existing observer boundary. History and research budgets remain untouched.
"""
import copy
from identity_triage_store import digest


def prepare(payload, context, current, sources):
    from identity_triage_observer import envelope
    from identity_triage_intake import normalize
    event=envelope(payload,context,sources)
    record=normalize(event,sources,'outcome')
    if record.get('reason') or 'outcome-'+record['release']!=current['case_key']:
        raise ValueError('source_mismatch')
    if record['metadata']!=current['material']['metadata']:
        raise ValueError('source_metadata_changed')
    # Maintenance must not replace a meaningful decision with transient failure.
    outcome=record['outcome']
    if outcome['status'] not in {'verified_tmdb','needs_review'}:
        raise ValueError('inconclusive_refresh')
    if context.get('category')!='unknown_movie':raise ValueError('wrong_category')
    if outcome==current['material']['outcome']:return None
    return {'case_id':current['case_key'],'expected_version':current['version'],
            'event':event,'outcome':outcome}


def refreshed_report(previous,snapshot,case_ids):
    """Replace only explicit cases; refuse concurrent/unrelated projection drift."""
    ids=set(case_ids)
    if not ids or len(ids)>10 or len(ids)!=len(case_ids):raise ValueError('scope')
    old={x['case_id']:x for x in previous['cases']};fresh={x['case_id']:x for x in snapshot['cases']}
    if set(old)!=set(fresh) or not ids<=set(old):raise ValueError('case_set_changed')
    for cid in set(old)-ids:
        if old[cid]['version']!=fresh[cid]['version']:raise ValueError('unrelated_case_changed')
    result=copy.deepcopy(previous);result['cases']=[];result['versions']={};changed=[]
    for before in previous['cases']:
        row=copy.deepcopy(before);cid=row['case_id']
        if cid in ids:
            row.update({k:v for k,v in fresh[cid].items() if k in {
                "case_id","version","observed_at","first_observed_at","title","year",
                "route","reason","correlation","original_type","source_identity"}})
            if row.get('proposal') and before['version']!=row['version']:
                row['proposal']['current_evidence']=False
        key=digest({k:v for k,v in row.items() if k!='observed_at'})
        result['cases'].append(row);result['versions'][cid]=key
        if previous['versions'].get(cid)!=key:changed.append(row)
    result['changed_cases']=changed
    result['coverage']=snapshot['coverage'];result['generated_at']=snapshot['generated_at']
    result['oldest_unresolved_age_seconds']=max([snapshot['generated_at']-x['first_observed_at'] for x in result['cases'] if x['route'] not in {'verified','routine'}]+[0])
    return result


def suppress_refresh(connection,report,case_ids,now):
    """Record honest silent-maintenance receipts; never pretend a message was sent."""
    from identity_telegram_digest import projection
    ids=set(case_ids);rows=projection(report,now)
    found={cid for cid,key,route,text in rows if cid in ids}
    if found!=ids:raise ValueError('digest_scope')
    for cid,key,route,text in rows:
        if cid in ids:
            connection.execute('INSERT OR IGNORE INTO delivery VALUES (?,?,?,?)',(cid,key,'suppressed',now))
    return len(found)
