"""UNISSUED one-shot template. Main must review actual pins before execution.

The private wrapper is the trusted issuer, not a caller-hash authentication API.
Run only as its own disposable Python -I -S -B process; never inside an app.
"""
import sys,os,stat,json,hashlib,runpy,ast
from contextlib import ExitStack
from pathlib import Path

# Corrected-code purpose proof, account evidence, exact consent and main acceptance
# have not been issued. No inferred authority or current credential operation.
ISSUED = None


def file_record(path,limit):
    path=Path(path)
    if not path.is_absolute() or path.resolve(strict=True)!=path:raise ValueError('private_path')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC)
    try:
        before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_uid!=os.getuid() or stat.S_IMODE(before.st_mode)!=0o600 or before.st_nlink!=1 or not 0<before.st_size<=limit:raise ValueError('private_file')
        raw=os.read(fd,limit+1);after=os.fstat(fd)
        fields=('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
        if len(raw)!=before.st_size or any(getattr(before,k)!=getattr(after,k)for k in fields):raise ValueError('private_file_changed')
        if not os.path.samestat(after,os.stat(path,follow_symlinks=False)):raise ValueError('private_file_replaced')
        return raw
    finally:os.close(fd)


def bootstrap_guard(runtime,pins):
    # Execute ONLY frozen bytes whose hashes are literal in the accepted wrapper.
    # Reuse the accepted private_files guard verbatim, not runtime imports from
    # an unchecked directory. Its two tiny dependencies are exact AST nodes
    # from the same pinned contracts/history source; all I/O rules are unchanged.
    frozen={}
    for name in ('contracts','history','private_files'):
        relative='ai_movie_investigator/'+name+'.py'
        raw=file_record(runtime/relative,1048576)
        if hashlib.sha256(raw).hexdigest()!=pins[relative]:raise ValueError('bootstrap_changed')
        frozen[name]=ast.parse(raw)
    nodes=[]
    for name,selected in (('contracts',{'Refusal','require'}),('history',{'checked'})):
        nodes.extend(n for n in frozen[name].body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in selected)
    nodes.extend(n for n in frozen['private_files'].body if not(isinstance(n,ast.ImportFrom)and n.level))
    namespace={'os':os,'stat':stat}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'pinned-private-guard','exec'),namespace)
    return namespace


def selected_report(rows,authority,request_hash,digest):
    matches=[r for r in rows if r.get('type')=='new_case_completed' and r.get('job')==authority['job']]
    if len(matches)!=1:raise ValueError('selected_report_missing_or_ambiguous')
    row=matches[0];report=row['report']
    if report['request_hash']!=request_hash or report['job']!=authority['job'] or report['binding']!=authority['case'] or digest(report)!=row['report_hash'] or report['generation_invoked'] is not True or report['provider_receipt_correlated'] is not True or report['draft']['sent'] is not False:raise ValueError('selected_report_binding')
    return row


def main():
    if ISSUED is None:raise SystemExit('actual_capture_authority_unissued')
    if sys.argv[1:]!=['--main-accepted-evidence-successor']:raise SystemExit('main_acceptance_required')
    import time
    os.umask(0o077);p=ISSUED
    if type(p['prior_slot']) is not int or type(p['expected_slot']) is not int or p['expected_slot']!=p['prior_slot']+1:raise ValueError('exact_successor_slot_required')
    runtime=Path(p['runtime'])
    guard=bootstrap_guard(runtime,p['runtime_files'])
    with ExitStack() as chains:
        paths=[runtime,Path(__file__).parent,Path(p['main_acceptance_path']).parent,
               Path(p['owner_scope']['path']).parent,Path(p['activation_seed']['path']).parent,
               Path(p['local_context']['path']).parent,Path(p['state']),Path(p['case_history'])]
        for path in paths:chains.enter_context(guard['private_chain'](path))
        destinations={}
        for name in ('authority_path','activation_path','report_path'):
            target=Path(p[name])
            if not target.is_absolute() or target.name in ('','.','..'):raise ValueError('private_output_path')
            destinations[name]=(target,chains.enter_context(guard['private_chain'](target.parent)))
        def guarded_pin(pin,limit):
            raw=guard['read_private'](Path(pin['path']),limit)
            if hashlib.sha256(raw).hexdigest()!=pin['sha256']:raise ValueError('exact_pin_changed')
            return raw
        def write_once(name,raw):
            target,dfd=destinations[name]
            if not os.path.samestat(os.fstat(dfd),os.stat(target.parent,follow_symlinks=False)):raise ValueError('private_output_parent')
            fd=os.open(target.name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=dfd)
            try:
                view=memoryview(raw)
                while view:
                    count=os.write(fd,view)
                    if count<=0:raise ValueError('private_output_write')
                    view=view[count:]
                os.fsync(fd);info=os.fstat(fd)
                if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or stat.S_IMODE(info.st_mode)!=0o600 or info.st_nlink!=1 or info.st_size!=len(raw):raise ValueError('private_output_write')
            finally:os.close(fd)
            os.fsync(dfd)
            if not os.path.samestat(os.fstat(dfd),os.stat(target.parent,follow_symlinks=False)):raise ValueError('private_output_parent')
            if guard['read_private'](target,1048576)!=raw:raise ValueError('private_output_changed')
        acceptance=json.loads(guard['read_private'](Path(p['main_acceptance_path']),32768))
        if acceptance['decision']!='accepted_exact_material_evidence_successor_and_private_report' or acceptance['wrapper_sha256']!=hashlib.sha256(guard['read_private'](Path(__file__),65536)).hexdigest() or acceptance['issued_pins']!=p:raise ValueError('main_acceptance_changed')
        owner=json.loads(guarded_pin(p['owner_scope'],32768))
        if owner.get('decision')!='authorized_exact_material_evidence_successor_and_private_report' or owner.get('prior_slot')!=p['prior_slot'] or owner.get('same_case_only') is not True:raise ValueError('owner_scope_changed')
        seed=json.loads(guarded_pin(p['activation_seed'],131072))
        audit_scope=guarded_pin(p['audit_owner_scope'],32768)
        if json.loads(audit_scope).get('decision')!='authorized_one_same_source_verified_identity_check_and_selective_restart':raise ValueError('audit_live_scope_required')
        if seed.get('kind')!='trusted_wrapper_verified_identity_check_v1' or seed.get('assessment_purpose')!='producer_verified_identity_check_v1' or seed['owner_scope']!=p['audit_owner_scope']:raise ValueError('audit_activation_scope')
        for relative,expected in p['runtime_files'].items():
            if hashlib.sha256(guard['read_private'](runtime/relative,1048576)).hexdigest()!=expected:raise ValueError('runtime_changed')
        sys.path.insert(0,str(runtime))
        from ai_movie_investigator import new_case as n,supervised_credit as c
        from ai_movie_investigator.installation import verify_installation
        from ai_movie_investigator.contracts import digest,encoded,decode,capture_qualification,captured_outcome,VERIFIED_IDENTITY_CHECK
        from ai_movie_investigator.history import History
        from ai_movie_investigator.captured_evidence_preflight import preflight_successor
        from ai_movie_investigator.captured_private_report import render_private_report,validate_local_context,validate_local_context
        manifest=verify_installation(runtime)
        if manifest!=p['runtime_files'] or digest(manifest)!=seed['runtime_manifest_sha256']:raise ValueError('runtime_closure_changed')
        group=seed['evidence_artifacts']
        if set(group)!={'attestation','catalogue','source','catalogue_original','source_original'}:raise ValueError('evidence_artifacts')
        artifacts={k:guarded_pin(v,65536) for k,v in group.items()}
        att=decode(artifacts['attestation'],65536);local=decode(guarded_pin(p['local_context'],65536),65536)
        if encoded(att)!=artifacts['attestation'] or digest(local)!=att['local_context_sha256']:raise ValueError('local_context_changed')
        validate_local_context(local)
        for name in ('catalogue','source'):
            if hashlib.sha256(artifacts[name+'_original']).hexdigest()!=att[name+'_original_sha256']:raise ValueError('original_artifact_changed')
        native_receipt=decode(guarded_pin(seed['receipt'],8192),8192);qualification=capture_qualification(native_receipt['capture_qualification'])
        capture_body=guarded_pin(seed['body'],65536);capture_grant=guarded_pin(seed['capture_grant'],4096)
        if native_receipt['body_sha256']!=hashlib.sha256(capture_body).hexdigest() or native_receipt['body_bytes']!=len(capture_body) or native_receipt['grant_sha256']!=hashlib.sha256(capture_grant).hexdigest():raise ValueError('capture_receipt_changed')
        g=decode(capture_grant,4096)
        if (native_receipt.get('version')!=1 or native_receipt.get('channel')!='outcome' or
            native_receipt.get('privacy')!='private_local_raw_observer_body_no_api_disclosure' or native_receipt.get('api_disclosure_authorized') is not False or
            g.get('version')!=1 or g.get('source')!=native_receipt['source'] or g.get('channel')!='outcome' or
            g.get('filter')!=dict(mode='first_verified_identity_check',category='unknown_movie',status='verified_tmdb',reason='external_id_verified') or
            g.get('destination')!=dict(body='capture-body.json',receipt='capture-receipt.json') or g.get('privacy')!=native_receipt['privacy'] or
            not native_receipt['received_at']<g['expires_at']):raise ValueError('capture_receipt_changed')
        selected=c.read_evidence(p['account_evidence']['path'])
        if selected.sha256!=p['account_evidence']['sha256']:raise ValueError('account_changed')
        now=time.time()
        if not p['prepared_at']<=now<p['preparation_expires_at'] or not seed['issued_at']<=now<seed['expires_at']:raise ValueError('preparation_expired')
        selected.revalidate();c.validate_evidence(selected.data,now,standing=True)
        root=History(Path(p['state']));history=History(Path(p['case_history']),clock=lambda:p['prepared_at'])
        # Hold root throughout case preflight and preparation. Case lock is
        # released before prepare to avoid reentrant flock acquisition.
        with root.transaction(write=True) as (events,_):
            if digest(events)!=p['root_prefix_sha256']:raise ValueError('root_prefix_changed')
            credit=History(Path(p['state'])/'credit').read()
            if digest(credit)!=p['credit_prefix_sha256']:raise ValueError('credit_prefix_changed')
            credit_history=History(Path(p['state'])/'credit')
            _,attempts,reservations,total=c._standing_history(root,events,events[1],credit_history)
            effective=c._credit_grant(events,events[1],p['expected_slot'])
            from ai_movie_investigator.spending import rational
            from ai_movie_investigator.credit_test import PER_REQUEST
            account=selected.data
            if (account['project']!=effective['project'] or account['account_reference']!=effective['account_reference'] or
                account['credit_expires_at']>effective['credit_expires_at'] or now>=effective['credit_expires_at'] or
                total+PER_REQUEST>min(rational(effective['ceiling_usd']),rational(account['available_usd']))):raise ValueError('credit_preflight_refused')
            matches=[x for x,_ in attempts if x['slot']==p['prior_slot']]
            if len(matches)!=1 or matches[0] is not attempts[-1][0]:raise ValueError('prior_selection_changed')
            old=matches[0];terminal=[x for x in events if x.get('slot')==p['prior_slot'] and x['type']=='supervised_diagnostic']
            oldattempt=History(Path(p['state'])/('attempt-'+str(p['prior_slot']))).read()
            if len(terminal)!=1 or digest(terminal[0])!=p['prior_terminal_sha256'] or terminal[0].get('reason')!='unsupported_candidate' or terminal[0].get('phase')!='captured_result_validation' or terminal[0].get('category')!='historical_report_refused' or 'cleanup_reason' in terminal[0] or any(r.get('type')=='supervised_completed' and r.get('slot')==p['prior_slot'] for r in events) or digest(oldattempt)!=p['prior_attempt_sha256'] or [r['type'] for r in oldattempt]!=['bound_send_reserved','bound_send_attempted','bound_send_receipt']:raise ValueError('prior_terminal_changed')
            with history.transaction(write=True) as (rows,_):
                if digest(rows)!=p['case_prefix_sha256']:raise ValueError('case_prefix_changed')
                intakes=[x for x in rows if x.get('type')=='intake' and x.get('job')==old['captured']['authorization']['job']]
                if len(intakes)!=1:raise ValueError('prior_packet_missing')
                oldpacket=intakes[0]['packet']
                receipt_binding=dict(source=native_receipt['source'],case_id=native_receipt['case_id'],version=native_receipt['case_version'],occurrence=dict(event_id=native_receipt['event_id'],delivery_id=native_receipt['delivery_rowid']))
                if receipt_binding!=oldpacket['binding']:raise ValueError('capture_receipt_changed')
                reconstructed=captured_outcome(capture_body,sources=seed['sources'],binding=oldpacket['binding'],evidence=oldpacket['evidence'],decisions=oldpacket['decisions'],trusted_issuers=oldpacket['trusted_issuers'],qualification=qualification)
                if reconstructed!=oldpacket:raise ValueError('prior_capture_changed')
                oldjob=old['captured']['authorization']['job'];oldrows=[r for r in rows if r.get('job')==oldjob]
                starts=[r for r in oldrows if r.get('type')=='new_case_generation_started'];done=[r for r in oldrows if r.get('type') in ('new_case_completion_started','new_case_completion_rejected','new_case_completed')]
                if not starts or starts[-1].get('grant_sha256')!=digest(old['captured']) or len(done)<2 or done[-2]['type']!='new_case_completion_started' or done[-1]['type']!='new_case_completion_rejected' or any(r['type']=='new_case_completed' for r in done):raise ValueError('prior_completion_changed')
            proposal=preflight_successor(oldpacket,artifacts['catalogue'],p['catalogue_pin'],artifacts['source'],p['source_pin'],att,now=p['prepared_at'],purpose=VERIFIED_IDENTITY_CHECK)
            packet=proposal['packet'];rec=n.admitted(packet,packet['binding'],p['prepared_at'],purpose=VERIFIED_IDENTITY_CHECK)
            current=preflight_successor(oldpacket,artifacts['catalogue'],p['catalogue_pin'],artifacts['source'],p['source_pin'],att,now=now,purpose=VERIFIED_IDENTITY_CHECK)
            if current['packet']!=packet or digest(n.admitted(packet,packet['binding'],now,purpose=VERIFIED_IDENTITY_CHECK))!=digest(rec):raise ValueError('evidence_or_decision_expired')
            proposed=n.request_for(packet,rec,p['prepared_at'],minimized_evidence=True)
            if digest(packet)!=p['packet_sha256'] or digest(proposed)!=p['request_hash'] or owner.get('packet_sha256')!=p['packet_sha256']:raise ValueError('proposal_changed')
            # All output paths must be absent before the first append or send.
            for name,(path,dfd) in destinations.items():
                try:os.stat(path.name,dir_fd=dfd,follow_symlinks=False)
                except FileNotFoundError:pass
                else:raise ValueError('private_output_exists')
            request=n.prepare(history,packet,packet['binding'],purpose=VERIFIED_IDENTITY_CHECK,minimized_evidence=True)
            if request!=proposed:raise ValueError('prepared_request_changed')
            with history.transaction(write=True) as (rows,_):
                authority=n.captured_consent(root,events,history,rows,digest(request),selected.data)
            if authority['evidence_prior']['slot']!=p['prior_slot'] or authority['root_prefix_sha256']!=p['root_prefix_sha256']:raise ValueError('authority_changed')
            authority_sha256=digest(authority)
            write_once('authority_path',encoded(authority))
            seed['authority']={'path':p['authority_path'],'sha256':authority_sha256}
            activation_raw=encoded(seed)
            activation_sha256=hashlib.sha256(activation_raw).hexdigest()
            write_once('activation_path',activation_raw)
        # Partial preparation is never replayed. The reviewed gate performs one
        # allocation and the existing CLI performs at most one send.
        with n.approved_captured_wrapper(p['activation_path'],activation_sha256):
            granted=n.authorize_captured(p['state'],selected,p['case_history'],p['request_hash'],p['authority_path'],authority_sha256)
            if granted['slot']!=p['expected_slot'] or p['expected_slot']!=p['prior_slot']+1:raise ValueError('exact_successor_slot_required')
            sys.argv=['ai_movie_investigator.supervised_credit','--state',p['state'],'run-captured-keychain','--evidence',p['account_evidence']['path'],'--slot',str(granted['slot'])]
            try:runpy.run_module('ai_movie_investigator.supervised_credit',run_name='__main__',alter_sys=True)
            except SystemExit as result:
                if result.code not in (0,None):raise
            rows=History(Path(p['case_history'])).read();report=selected_report(rows,authority,p['request_hash'],digest)
            if report['report'].get('capture_qualification')!=qualification:raise ValueError('qualified_report_changed')
            receipts=History(Path(p['state'])/('attempt-'+str(granted['slot']))).read()
            if not receipts or receipts[-1]['type']!='bound_send_receipt' or digest(receipts[-1])!=report['report']['receipt_hash']:raise ValueError('selected_report_receipt_changed')
            completed=[r for r in History(Path(p['state'])).read() if r.get('type')=='supervised_completed' and r.get('slot')==granted['slot']]
            if len(completed)!=1 or completed[0]['captured_report']!=report['report'] or digest(completed[0]['answer'])!=report['report']['retained_reply_hash'] or completed[0]['answer']['result']!=report['report']['assessment']:raise ValueError('retained_report_binding')
            intakes=[r for r in rows if r.get('type')=='intake' and r.get('job')==authority['job']]
            if len(intakes)!=1 or intakes[0]['packet']!=packet:raise ValueError('selected_packet_changed')
            cat,source=packet['evidence'][-2:]
            context=dict(local,prior_failure='unsupported_candidate',job=report['report']['job'],binding=report['report']['binding'],report_sha256=report['report_hash'],catalogue_evidence_sha256=cat['provenance']['digest'],source_evidence_sha256=source['provenance']['digest'])
            html=render_private_report(report['report'],report['report_hash'],context,digest(context),packet).encode('utf-8')
            write_once('report_path',html)
            success={'status':'private_report_ready_for_main','report_sha256':report['report_hash'],'html_sha256':hashlib.sha256(html).hexdigest()}
    print(json.dumps(success))

if __name__=='__main__':main()
