"""Trusted-main gate for one normalized snapshot review, default closed.

A local file or hash is not owner authentication. Only the existing trusted
supervisor may enter this context after independently reviewing the exact owner
scope, snapshot origin, and source/catalogue observations. No CLI or environment
variable enables this gate. The caller must hold the enrolled root lock when
creating or consuming a grant. This module never calls a provider.
"""
from contextlib import contextmanager
from contextvars import ContextVar
import hashlib
from pathlib import Path
import time
from .contracts import decode,digest,encoded,hash_id,require,shape,stamp

_ACTIVE=ContextVar('approved_snapshot_review',default=None)

class _Approved:
    def __init__(self,path,pin):
        from .supervised_credit import _read_evidence
        self.path=Path(path);self.pin=hash_id(pin)
        raw,self.identity=_read_evidence(self.path,65536)
        require(hashlib.sha256(raw).hexdigest()==pin,'snapshot_authority_changed')
        self.record=decode(raw,65536)
        shape(self.record,'kind owner_scope main_review root_identity root_prefix_sha256 root_count project account_reference output_dir output_identity snapshot source catalogue source_original catalogue_original local_context attestation runtime_manifest_sha256 issued_at expires_at'+(' correction' if 'correction' in self.record else '')+(' reassessment' if 'reassessment' in self.record else ''))
        require(raw==encoded(self.record) and self.record['kind']=='trusted_main_normalized_snapshot_v1','snapshot_authority_changed')
        self.pins={}
        for name in ('owner_scope','main_review','snapshot','source','catalogue','source_original','catalogue_original','local_context'):
            pin_record=self.record[name];shape(pin_record,'path sha256');hash_id(pin_record['sha256'])
            limit=1048576 if name=='snapshot' else 65536
            data,identity=_read_evidence(Path(pin_record['path']),limit)
            require(hashlib.sha256(data).hexdigest()==pin_record['sha256'],'snapshot_authority_artifact')
            self.pins[name]=(data,identity,limit)
        self.revalidate()

    def revalidate(self):
        from .supervised_credit import _read_evidence
        from .installation import verify_installation
        raw,identity=_read_evidence(self.path,65536)
        require(identity==self.identity and hashlib.sha256(raw).hexdigest()==self.pin and
                decode(raw,65536)==self.record,'snapshot_authority_changed')
        a=self.record;now=time.time()
        require(stamp(a['issued_at']) <= now < stamp(a['expires_at']), 'snapshot_authority_expired')
        require(type(a['root_identity']) is list and len(a['root_identity'])==2 and
                all(type(x) is int and x>=0 for x in a['root_identity']) and
                type(a['root_count']) is int and a['root_count']>=21,'snapshot_authority_changed')
        hash_id(a['root_prefix_sha256']);hash_id(a['runtime_manifest_sha256'])
        for name,(old,old_identity,limit) in self.pins.items():
            current=_read_evidence(Path(a[name]['path']),limit)
            require(current==(old,old_identity),'snapshot_authority_artifact_changed')
        from .private_files import private_chain
        import os
        output=Path(a['output_dir'])
        require(output.is_absolute() and type(a['output_identity']) is list and len(a['output_identity'])==2 and
                all(type(x) is int and x>=0 for x in a['output_identity']), 'snapshot_output_changed')
        with private_chain(output) as output_fd:
            st=os.fstat(output_fd)
            require([st.st_dev,st.st_ino]==a['output_identity'],'snapshot_output_changed')
        manifest=verify_installation(Path(__file__).resolve().parent.parent)
        require(digest(manifest)==a['runtime_manifest_sha256'],'snapshot_runtime_changed')
        from .snapshot_private_report import validate_local_context
        validate_local_context(self.pins['local_context'][0])
        scope=decode(self.pins['owner_scope'][0],65536)
        correcting='correction' in a;reassessing='reassessment' in a
        require(not (correcting and reassessing),'snapshot_reassessment_changed')
        shape(scope,'kind case_id version max_calls disclosure_allowed production_allowed'+(' prior_slot' if correcting or reassessing else ''))
        att=a['attestation']
        expected_scope=dict(kind='snapshot_correction_scope_v1' if correcting else 'snapshot_reassessment_scope_v1' if reassessing else 'snapshot_assessment_scope_v1',
            case_id=att['case_id'],version=att['version'],max_calls=1,disclosure_allowed=True,production_allowed=False)
        if correcting:expected_scope['prior_slot']=a['correction']['prior_slot']
        if reassessing:expected_scope['prior_slot']=a['reassessment']['prior_slot']
        require(scope==expected_scope,'snapshot_owner_scope')
        review=decode(self.pins['main_review'][0],65536)
        shape(review,'kind owner_scope_sha256 snapshot_sha256 source_sha256 catalogue_sha256 source_original_sha256 catalogue_original_sha256 local_context_sha256 provenance_reviewed'+(' correction_sha256' if correcting else '')+(' reassessment_sha256' if reassessing else ''))
        expected_review=dict(kind='snapshot_main_review_v1',owner_scope_sha256=a['owner_scope']['sha256'],
            snapshot_sha256=a['snapshot']['sha256'],source_sha256=a['source']['sha256'],catalogue_sha256=a['catalogue']['sha256'],
            source_original_sha256=a['source_original']['sha256'],catalogue_original_sha256=a['catalogue_original']['sha256'],
            local_context_sha256=a['local_context']['sha256'],provenance_reviewed=True)
        if correcting:expected_review['correction_sha256']=digest(a['correction'])
        if reassessing:expected_review['reassessment_sha256']=digest(a['reassessment'])
        require(review==expected_review,'snapshot_main_review')
        require(att['snapshot_sha256']==a['snapshot']['sha256'] and
                att['source_sha256']==a['source']['sha256'] and att['catalogue_sha256']==a['catalogue']['sha256'] and
                att['source_original_sha256']==a['source_original']['sha256'] and
                att['catalogue_original_sha256']==a['catalogue_original']['sha256'] and
                stamp(att['expires_at'])<=a['expires_at'],'snapshot_authority_artifact')
        from .snapshot_review import projection
        return projection(self.pins['snapshot'][0],a['snapshot']['sha256'],att['case_id'],att['version'],
                          self.pins['source'][0],self.pins['catalogue'][0],att,now=now)

    def check_root(self,root,events,evidence):
        root.require_write_transaction(events);a=self.record
        require(list(root.identity)==a['root_identity'] and len(events)>=a['root_count'] and
                digest(events[:a['root_count']])==a['root_prefix_sha256'] and
                evidence['project']==a['project'] and evidence['account_reference']==a['account_reference'],
                'snapshot_root_changed')
        return self.revalidate()

@contextmanager
def approved_snapshot_wrapper(path,sha256):
    require(_ACTIVE.get() is None,'snapshot_nested')
    selected=_Approved(path,sha256);token=_ACTIVE.set(selected)
    try:yield selected
    finally:_ACTIVE.reset(token)


def active():
    selected=_ACTIVE.get()
    require(type(selected) is _Approved,'snapshot_activation_unissued')
    return selected


def proposal(root,events,evidence):
    from .snapshot_review import build
    held=active();p=held.check_root(root,events,evidence);require_operation_window(p)
    b=build(p,prose_limited='correction' not in held.record)
    case=dict(source='normalized',case_id=p['case_id'],version=p['version'],occurrence=None)
    a=held.record
    return dict(snapshot_profile='normalized_snapshot_v1',authority_path=str(held.path),authority_sha256=held.pin,
        case=case,run=b['run'],fingerprint=digest(dict(case_id=p['case_id'])),request=b['request'],
        projection_sha256=digest(p),local_context_sha256=a['local_context']['sha256'],selected_evidence=b['selected_evidence'],disclosure=b['disclosure'],
        root_prefix_sha256=a['root_prefix_sha256'],root_count=a['root_count'],
        contract_version='status_candidate_v2' if 'correction' in a else 'prose_length_v3',
        **({'correction':a['correction']} if 'correction' in a else {}),
        **({'reassessment':a['reassessment']} if 'reassessment' in a else {}))


def validate_grant(grant,project):
    held=active();p=held.revalidate();a=held.record
    from .snapshot_review import build
    version=grant.get('contract_version');corrected=version in ('status_candidate_v2','prose_length_v3');limited=version=='prose_length_v3'
    require(('correction' not in grant or version=='status_candidate_v2') and ('reassessment' not in grant or limited),'snapshot_correction_changed')
    b=build(p,corrected=corrected,prose_limited=limited)
    shape(grant,'snapshot_profile authority_path authority_sha256 case run fingerprint request projection_sha256 local_context_sha256 selected_evidence disclosure root_prefix_sha256 root_count'+(' contract_version' if corrected else '')+(' correction' if 'correction' in grant else '')+(' reassessment' if 'reassessment' in grant else ''))
    expected=dict(snapshot_profile='normalized_snapshot_v1',authority_path=str(held.path),authority_sha256=held.pin,
        case=dict(source='normalized',case_id=p['case_id'],version=p['version'],occurrence=None),run=b['run'],
        fingerprint=digest(dict(case_id=p['case_id'])),request=b['request'],projection_sha256=digest(p),
        local_context_sha256=a['local_context']['sha256'],selected_evidence=b['selected_evidence'],disclosure=b['disclosure'],root_prefix_sha256=a['root_prefix_sha256'],root_count=a['root_count'])
    if corrected:expected['contract_version']=version
    if 'correction' in a:expected['correction']=a['correction']
    if 'reassessment' in a:expected['reassessment']=a['reassessment']
    require(project==a['project'] and grant==expected,'snapshot_grant_changed')
    return encoded(b['request'])


def validate_correction(root,events,grant,*,creating,descendant=None):
    """Bind one successor to the exact consumed, receipt-backed schema failure."""
    from . import supervised_credit as c
    from .history import History
    from .snapshot_review import build
    root.require_write_transaction(events)
    proof=grant.get('correction')
    shape(proof,'kind prior_slot prior_start_sha256 prior_grant_sha256 prior_terminal_sha256 prior_attempt_sha256 prior_receipt_sha256 prior_credit_sha256 prior_credit_count prior_request_sha256 root_prefix_sha256 new_request_sha256 reviewed')
    require(proof['kind']=='snapshot_candidate_status_correction_v1' and proof['reviewed'] is True and
            type(proof['prior_slot']) is int and proof['prior_slot']>=7 and
            type(proof['prior_credit_count']) is int and proof['prior_credit_count']>=1 and
            proof['root_prefix_sha256']==grant['root_prefix_sha256'] and
            grant.get('contract_version')=='status_candidate_v2' and
            proof['new_request_sha256']==digest(grant['request']), 'snapshot_correction_changed')
    for key in ('prior_start_sha256','prior_grant_sha256','prior_terminal_sha256','prior_attempt_sha256',
                'prior_receipt_sha256','prior_credit_sha256','prior_request_sha256','root_prefix_sha256','new_request_sha256'):
        hash_id(proof[key])
    attempts=c._standing_attempts(events,events[1]);prior=[s for s,_ in attempts if s['slot']==proof['prior_slot']]
    require(len(prior)==1 and 'historical' in prior[0],'snapshot_correction_prior')
    start=prior[0];old=start['historical']
    require(old.get('snapshot_profile')=='normalized_snapshot_v1' and 'correction' not in old and
            'contract_version' not in old and digest(start)==proof['prior_start_sha256'] and
            digest(old)==proof['prior_grant_sha256'] and start['request_sha256']==proof['prior_request_sha256'],
            'snapshot_correction_prior')
    terminal=[r for r in events[:grant['root_count']] if r.get('slot')==proof['prior_slot'] and r.get('type')=='supervised_diagnostic']
    require(len(terminal)==1 and terminal[0].get('phase')=='receipt_recorded' and
            terminal[0].get('reason')=='candidate_status' and terminal[0].get('category')=='historical_report_refused' and
            'cleanup_reason' not in terminal[0] and digest(terminal[0])==proof['prior_terminal_sha256'] and
            not any(r.get('slot')==proof['prior_slot'] and r.get('type')=='supervised_completed' for r in events),
            'snapshot_correction_prior')
    rows=History(root.directory/f"attempt-{proof['prior_slot']}").read()
    require([r.get('type') for r in rows]==['bound_send_reserved','bound_send_attempted','bound_send_receipt'] and
            rows[-1].get('request_sha256')==proof['prior_request_sha256'] and
            digest(rows)==proof['prior_attempt_sha256'] and digest(rows[-1])==proof['prior_receipt_sha256'],
            'snapshot_correction_receipt')
    credit=History(root.directory/'credit').read();count=proof['prior_credit_count']
    require(len(credit)>=count and digest(credit[:count])==proof['prior_credit_sha256'] and
            len([r for r in credit[:count] if r.get('request_hash')==proof['prior_request_sha256'] and r.get('reserved_usd')==[3,100]])==1,
            'snapshot_correction_credit')
    require(all(old[k]==grant[k] for k in ('case','run','fingerprint','projection_sha256','local_context_sha256','selected_evidence','disclosure')),
            'snapshot_correction_disclosure')
    p=active().revalidate();legacy=build(p,corrected=False)['request'];corrected=build(p,corrected=True,prose_limited=False)['request']
    require(old['request']==legacy and grant['request']==corrected and legacy!=corrected and
            digest(legacy)==proof['prior_request_sha256'], 'snapshot_correction_disclosure')
    prior_wire=dict(legacy);new_wire=dict(corrected);prior_text=dict(prior_wire.pop('text'));new_text=dict(new_wire.pop('text'))
    prior_format=dict(prior_text.pop('format'));new_format=dict(new_text.pop('format'))
    prior_format.pop('schema');new_format.pop('schema')
    require(prior_wire==new_wire and prior_text==new_text and prior_format==new_format,
            'snapshot_correction_disclosure')
    children=[s for s,_ in attempts if s.get('historical',{}).get('correction',{}).get('prior_slot')==proof['prior_slot']]
    if creating:
        require(not children and attempts[-1][0] is start and len(credit)==count and len(events)==grant['root_count'],
                'snapshot_correction_consumed')
    else:
        is_last=children and children[0] is attempts[-1][0]
        if descendant is not None:
            is_last=len(attempts)>=2 and children and children[0] is attempts[-2][0] and attempts[-1][0].get('historical')==descendant
        require(len(children)==1 and is_last and children[0]['slot']==proof['prior_slot']+1 and
                children[0]['historical']==grant and children[0]['prefix_sha256']==grant['root_prefix_sha256'] and
                children[0]['credit_count']==count and children[0]['credit_sha256']==proof['prior_credit_sha256'],
                'snapshot_correction_consumed')
    return proof['prior_slot']


def validate_reassessment(root,events,grant,*,creating):
    """Permit one distinct assessment after the exact completed length withholding."""
    from . import supervised_credit as c
    from .history import History
    from .snapshot_review import build
    root.require_write_transaction(events);proof=grant.get('reassessment')
    shape(proof,'kind prior_slot prior_start_sha256 prior_grant_sha256 prior_completion_sha256 prior_report_sha256 prior_retained_reply_sha256 prior_attempt_sha256 prior_receipt_sha256 prior_credit_sha256 prior_credit_count prior_request_sha256 root_prefix_sha256 new_request_sha256 prior_status prior_candidate reviewed')
    require(proof['kind']=='snapshot_prose_length_reassessment_v1' and proof['reviewed'] is True and
        type(proof['prior_slot']) is int and proof['prior_slot']>=8 and type(proof['prior_credit_count']) is int and
        proof['prior_credit_count']>=1 and grant.get('contract_version')=='prose_length_v3' and
        proof['root_prefix_sha256']==grant['root_prefix_sha256'] and proof['new_request_sha256']==digest(grant['request']),
        'snapshot_reassessment_changed')
    for key in ('prior_start_sha256','prior_grant_sha256','prior_completion_sha256','prior_report_sha256',
                'prior_retained_reply_sha256','prior_attempt_sha256','prior_receipt_sha256','prior_credit_sha256',
                'prior_request_sha256','root_prefix_sha256','new_request_sha256'):hash_id(proof[key])
    attempts=c._standing_attempts(events,events[1]);prior=[s for s,_ in attempts if s['slot']==proof['prior_slot']]
    require(len(prior)==1 and 'historical' in prior[0],'snapshot_reassessment_prior')
    start=prior[0];old=start['historical']
    require(old.get('snapshot_profile')=='normalized_snapshot_v1' and old.get('contract_version')=='status_candidate_v2' and
        'correction' in old and 'reassessment' not in old and digest(start)==proof['prior_start_sha256'] and
        digest(old)==proof['prior_grant_sha256'] and start['request_sha256']==proof['prior_request_sha256'],
        'snapshot_reassessment_prior')
    completions=[r for r in events[:grant['root_count']] if r.get('slot')==proof['prior_slot'] and r.get('type')=='supervised_completed']
    require(len(completions)==1 and digest(completions[0])==proof['prior_completion_sha256'] and
        not any(r.get('slot')==proof['prior_slot'] and r.get('type')=='supervised_diagnostic' for r in events[:grant['root_count']]),
        'snapshot_reassessment_prior')
    completed=completions[0];report=completed.get('historical_report');answer=completed.get('answer')
    require(type(report) is dict and report.get('kind')=='receipt_bound_snapshot_review_v1' and
        report.get('generation_invoked') is True and report.get('provider_receipt_correlated') is True and
        report.get('sent') is False and digest(report)==proof['prior_report_sha256'] and
        digest(answer)==proof['prior_retained_reply_sha256']==report.get('retained_reply_hash') and
        completed.get('request_hash')==report.get('request_sha256')==proof['prior_request_sha256'] and
        report.get('prose_handling',{}).get('rationale')==dict(status='withheld',predicate='length') and
        report.get('prose_handling',{}).get('uncertainty')==dict(status='retained',predicate=None),
        'snapshot_reassessment_result')
    result=report['result'];require(result['status']==answer['result']['status']==proof['prior_status'] and
        result['candidate']==answer['result']['candidate']==proof['prior_candidate'], 'snapshot_reassessment_result')
    rows=History(root.directory/f"attempt-{proof['prior_slot']}").read()
    require([r.get('type') for r in rows]==['bound_send_reserved','bound_send_attempted','bound_send_receipt'] and
        digest(rows)==proof['prior_attempt_sha256'] and digest(rows[-1])==proof['prior_receipt_sha256']==report.get('receipt_hash') and
        rows[-1]==report.get('receipt') and rows[-1].get('request_sha256')==proof['prior_request_sha256'],
        'snapshot_reassessment_receipt')
    credit=History(root.directory/'credit').read();count=proof['prior_credit_count']
    require(len(credit)>=count and digest(credit[:count])==proof['prior_credit_sha256'] and
        len([r for r in credit[:count] if r.get('request_hash')==proof['prior_request_sha256'] and r.get('reserved_usd')==[3,100]])==1,
        'snapshot_reassessment_credit')
    require(all(old[k]==grant[k] for k in ('case','run','fingerprint','projection_sha256','local_context_sha256','selected_evidence','disclosure')),
        'snapshot_reassessment_disclosure')
    p=active().revalidate();old_wire=build(p,corrected=True,prose_limited=False)['request'];new_wire=build(p,corrected=True,prose_limited=True)['request']
    require(old['request']==old_wire and grant['request']==new_wire and old_wire!=new_wire and
        digest(old_wire)==proof['prior_request_sha256'] and old_wire['input']==new_wire['input'],
        'snapshot_reassessment_disclosure')
    children=[s for s,_ in attempts if s.get('historical',{}).get('reassessment',{}).get('prior_slot')==proof['prior_slot']]
    if creating:
        require(not children and attempts[-1][0] is start and len(credit)==count and len(events)==grant['root_count'],
            'snapshot_reassessment_consumed')
        ancestor=validate_correction(root,events,old,creating=False)
    else:
        require(len(children)==1 and children[0] is attempts[-1][0] and children[0]['slot']==proof['prior_slot']+1 and
            children[0]['historical']==grant and children[0]['prefix_sha256']==grant['root_prefix_sha256'] and
            children[0]['credit_count']==count and children[0]['credit_sha256']==proof['prior_credit_sha256'],
            'snapshot_reassessment_consumed')
        ancestor=validate_correction(root,events,old,creating=False,descendant=grant)
    return (ancestor,proof['prior_slot'])


def authorize(directory,selected):
    """Append one exact case grant under existing root lock, without sending."""
    from . import supervised_credit as c
    from .history import History
    require(type(selected) is c.SelectedEvidence,'supervised_evidence_selection')
    selected.revalidate();c.validate_evidence(selected.data,time.time(),standing=True)
    root=History(Path(directory))
    with root.transaction(write=True) as (events,append):
        grant=proposal(root,events,selected.data)
        require(len(events)==grant['root_count'],'snapshot_root_changed')
        slot=c._prepare_next_locked(root,events,append,selected,create=True,historical=grant)
    return dict(status='snapshot_authorized_no_api_call',slot=slot,request_sha256=digest(grant['request']))


def report(grant,answer,history):
    """Finish only after the existing bound transport stored its real receipt."""
    from .snapshot_review import build, validate_answer
    from .supervised_authorization import consume_snapshot_completion
    proof=consume_snapshot_completion(grant,answer)
    held=active();validate_grant(grant,held.record['project']);p=held.revalidate()
    from .responses_protocol import schema_value
    from .new_case import _captured_prose_copy
    version=grant.get('contract_version');corrected=version in ('status_candidate_v2','prose_length_v3');limited=version=='prose_length_v3'
    prepared=build(p,corrected=corrected,prose_limited=limited);schema_value(answer,prepared['request']['text']['format']['schema'])
    require(answer['binding_hash']==decode(prepared['request']['input'][0]['content'][0]['text'],8192)['binding_hash'] and
            answer['kind']=='final' and answer['lookups']==[],'snapshot_reply_binding')
    retained,handling=_captured_prose_copy(answer)
    result=validate_answer(p,prepared,retained,now=time.time(),corrected=corrected,prose_limited=limited)
    rows=history.read()
    require(len(rows)==3 and rows[-1]['type']=='bound_send_receipt' and
            rows[-1]['request_sha256']==digest(grant['request']) and digest(rows[-1])==proof['receipt_hash'],'snapshot_receipt_missing')
    result_report=dict(kind='receipt_bound_snapshot_review_v1',request_sha256=digest(grant['request']),
        projection_sha256=digest(p),local_context_sha256=grant['local_context_sha256'],
        result=result,receipt=rows[-1],reply_hash=digest(answer),retained_reply_hash=digest(retained),
        prose_handling=handling,receipt_hash=proof['receipt_hash'],generation_invoked=not proof['simulated'],
        provider_receipt_correlated=not proof['simulated'],
        provider_signed=False,token_bill_verified=False,source_origin='trusted_supervisor_attested',
        captured_original='not_established',current_queue='unknown',complete_decisions='unknown',
        physical_edition='unknown',identity_approval=False,acquisition_approval=False,sent=False,
        conflict_status='Producer conflict remains for human review; matching IDs alone do not resolve it.')
    if 'reassessment' in grant:
        prior=grant['reassessment']
        result_report['previous_assessment']=dict(slot=prior['prior_slot'],status=prior['prior_status'],
            candidate=prior['prior_candidate'],report_sha256=prior['prior_report_sha256'],rationale='withheld_unrecoverable')
        result_report['assessment_label']='distinct_new_assessment'
    return result_report


def require_operation_window(projection):
    """Cover existing send and observation windows; local completion time is not bounded."""
    from .supervised_authorization import SEND_AUTHORITY_SECONDS, RESPONSE_OBSERVATION_SECONDS
    now=time.time();a=active().record
    require(now+SEND_AUTHORITY_SECONDS+RESPONSE_OBSERVATION_SECONDS < min(a['expires_at'],projection['generated_at']+3600,
                projection['evidence_expires_at']), 'snapshot_window_too_short')


def _write_once(dfd,name,raw):
    import os
    from .private_files import safe_acl,identity
    from .history import checked
    fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=dfd)
    try:
        before=os.fstat(fd);checked(before);acl=safe_acl(fd,False)
        with os.fdopen(fd,'wb',closefd=False) as stream:
            stream.write(raw);stream.flush();os.fsync(fd)
        after=os.fstat(fd);checked(after)
        require(identity(before)==identity(after)==identity(os.stat(name,dir_fd=dfd,follow_symlinks=False)) and
                safe_acl(fd,False)==acl,'snapshot_output_changed')
        os.fsync(dfd)
    finally:os.close(fd)


def write_completed(directory,selected,slot,output_dir):
    """Render the one durable, receipt-bound result; never send or allocate."""
    from . import supervised_credit as c
    from .history import History
    from .snapshot_review import build,validate_answer
    from .snapshot_private_report import render
    from .private_files import private_chain
    import os
    require(type(selected) is c.SelectedEvidence and type(slot) is int,'supervised_evidence_selection')
    selected.revalidate();root=History(Path(directory));held=active()
    with root.transaction(write=True) as (events,_):
        p=held.check_root(root,events,selected.data)
        c._standing_history(root,events,events[1],History(root.directory/'credit'))
        attempts=c._standing_attempts(events,events[1]);matches=[x for x,_ in attempts if x['slot']==slot]
        require(len(matches)==1 and 'historical' in matches[0],'snapshot_result_missing')
        grant=matches[0]['historical'];validate_grant(grant,selected.data['project'])
        rows=[r for r in events if r.get('slot')==slot and r.get('type')=='supervised_completed']
        require(len(rows)==1,'snapshot_result_missing');completed=rows[0]
        result=completed.get('historical_report');answer=completed.get('answer')
        require(isinstance(result,dict) and result.get('kind')=='receipt_bound_snapshot_review_v1' and
            completed['request_hash']==digest(grant['request'])==result['request_sha256'] and
            digest(answer)==result['retained_reply_hash'] and result['projection_sha256']==digest(p) and
            result['local_context_sha256']==held.record['local_context']['sha256'], 'snapshot_result_changed')
        receipt=History(root.directory/f'attempt-{slot}').read()
        require(len(receipt)==3 and receipt[-1]['type']=='bound_send_receipt' and
                receipt[-1]==result['receipt'] and digest(receipt[-1])==result['receipt_hash'] and
                receipt[-1]['request_sha256']==result['request_sha256'],
                'snapshot_receipt_missing')
        version=grant.get('contract_version');corrected=version in ('status_candidate_v2','prose_length_v3');limited=version=='prose_length_v3'
        require(validate_answer(p,build(p,corrected=corrected,prose_limited=limited),answer,now=time.time(),corrected=corrected,prose_limited=limited)==result['result'],'snapshot_result_changed')
        if 'reassessment' in grant:
            prior=grant['reassessment']
            require(result.get('assessment_label')=='distinct_new_assessment' and
                result.get('previous_assessment')==dict(slot=prior['prior_slot'],status=prior['prior_status'],
                    candidate=prior['prior_candidate'],report_sha256=prior['prior_report_sha256'],rationale='withheld_unrecoverable'),
                'snapshot_reassessment_result')
        local_raw=held.pins['local_context'][0]
        html=render(result,digest(result),p,local_raw,held.record['local_context']['sha256']).encode('utf-8')
        output_dir=Path(output_dir)
        require(str(output_dir)==held.record['output_dir'],'snapshot_output_changed')
        with private_chain(output_dir) as dfd:
            st=os.fstat(dfd)
            require([st.st_dev,st.st_ino]==held.record['output_identity'],'snapshot_output_changed')
            require(not os.listdir(dfd),'snapshot_output_not_empty')
            _write_once(dfd,'movie-review.html',html)
            from .private_files import safe_acl
            fd=os.open('movie-review.html',os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=dfd)
            try:
                import stat
                st=os.fstat(fd)
                require(stat.S_ISREG(st.st_mode) and st.st_uid==os.getuid() and st.st_nlink==1 and
                        stat.S_IMODE(st.st_mode)==0o600 and st.st_size==len(html),'snapshot_output_changed')
                safe_acl(fd,False);data=bytearray()
                while len(data)<len(html):
                    part=os.read(fd,min(65536,len(html)-len(data)))
                    require(bool(part),'snapshot_output_changed');data.extend(part)
                require(bytes(data)==html and os.read(fd,1)==b'','snapshot_output_changed')
                require(os.path.samestat(os.fstat(fd),os.stat('movie-review.html',dir_fd=dfd,follow_symlinks=False)),
                        'snapshot_output_changed')
            finally:os.close(fd)
    return dict(status='private_report_written',slot=slot,sha256=hashlib.sha256(html).hexdigest())


def execute(directory,selected,output_dir):
    """One new grant and one send, followed by exact durable-report readback."""
    from . import supervised_credit as c
    from .private_files import private_chain
    import os
    held=active()
    require(str(Path(output_dir))==held.record['output_dir'],'snapshot_output_changed')
    with private_chain(Path(output_dir)) as dfd:
        st=os.fstat(dfd)
        require([st.st_dev,st.st_ino]==held.record['output_identity'],'snapshot_output_changed')
        require(not os.listdir(dfd),'snapshot_output_not_empty')
        require_operation_window(held.revalidate())
        allocated=authorize(directory,selected);slot=allocated['slot']
        import contextlib,io,runpy,sys
        previous_argv=sys.argv
        try:
            sys.argv=['ai_movie_investigator.supervised_credit','--state',str(directory),
                      'run-historical-keychain','--evidence',str(selected.path),'--slot',str(slot)]
            with contextlib.redirect_stdout(io.StringIO()):
                try:runpy.run_module('ai_movie_investigator.supervised_credit',run_name='__main__',alter_sys=True)
                except SystemExit as error:
                    require(error.code in (0,None),'snapshot_runner_failed')
        finally:sys.argv=previous_argv
        result=write_completed(directory,selected,slot,output_dir)
        after=os.fstat(dfd)
        require([after.st_dev,after.st_ino]==held.record['output_identity'],'snapshot_output_changed')
    return result
