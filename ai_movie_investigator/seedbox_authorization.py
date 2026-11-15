"""Separate finite host authority for the unchanged v13 assessment contract.

No legacy history repair or synthetic main-review records. The installed trusted
host runner authenticates inputs and cutover; this capability exists only while
its canonical queue transaction is held. JSON, model output and a timer cannot
construct a live permit. Every potentially sent attempt retains its full debit.
"""
from contextvars import ContextVar
import hashlib,time
from .contracts import require,encoded,decode,digest
from .credit_test import MINI_MODEL,MINI_PROFILE

_ACTIVE=ContextVar('seedbox_assessment_authority',default=None)

class _Permit:pass


def handles(token):return type(token) is _Permit


def _current(token=None):
    current=_ACTIVE.get();require(current is not None and (token is None or token is current['token']),'host_authority_missing')
    current['queue'].history.require_write_transaction(current['rows'])
    return current


def refusal(token,*,body,credential,project,path,consume=True):
    try:
        c=_current(token)
        require(path=='/v1/responses' and body==c['body'] and credential is c['credential'] and project==c['project'],'host_wire_changed')
        require(c['started_at']<=time.time()<c['expires_at'] and time.monotonic()<c['monotonic_expires'],'host_authority_expired')
        if consume:
            require(not c['consumed'],'host_wire_consumed');c['consumed']=True
        else:require(c['consumed'],'host_wire_unreserved')
    except ValueError:return 'host_wire_refused'
    return None


def observation(token,body,credential,project,path):
    c=_current(token)
    require(c['consumed'] and body==c['body'] and credential is c['credential'] and project==c['project'] and path=='/v1/responses','host_observation_binding')
    return 120


def bind(token,result,body,credential,project,path):
    from .responses_http import HTTPResult
    observation(token,body,credential,project,path);c=_current(token)
    require(c['received'] is None and type(result) is HTTPResult and result.status==200 and result.project==project and result.path==path and result.request_sha256==hashlib.sha256(body).hexdigest(),'host_observation_binding')
    c['received']=result


def selected(result):
    c=_ACTIVE.get()
    if c is None or result is None or c['received'] is not result:return False
    _current();return True


def limits(result,raw,request_id,model):
    require(selected(result) and raw is result.body and request_id==result.request_id and model==MINI_MODEL,'host_observation_binding')
    return 1048576,1048576


def _execute(queue,preparation,*,policy,credential):
    """Trusted installed runner only; real fixed HTTPS, no injected transport.

    Source authentication and immutable bundle derivation precede this call.
    Result is pending independent review; no notification or identity approval.
    """
    from .supervised_authorization import observe_phase
    from .snapshot_review import build_film_prose,validate_film_prose
    from .snapshot_private_report import validate_local_context,render
    from .responses_http import FixedResponsesHTTP,headers
    from .responses_protocol import parse_response
    from .new_case import _captured_prose_copy
    from automation.seedbox_credit_policy import validate
    require(_ACTIVE.get() is None,'host_nested_authority')
    from automation.seedbox_evidence import load,verify_current
    evidence=load(queue,preparation)
    projection=evidence['projection'];local_raw=evidence['local_raw'];evidence_sha256=evidence['evidence_sha256']
    now=time.time();validate(policy,now=now);validate_local_context(local_raw)
    require(policy['model_profile']==MINI_PROFILE,'host_model_profile')
    require(now+180<min(policy['expires_at'],projection['evidence_expires_at'],projection['generated_at']+3600),'host_evidence_window')
    with queue.locked() as (rows,_):
        claims=[r for r in rows if r['type']=='seedbox_preparation_claimed_v1' and digest(r)==preparation]
        configuration_sha256=rows[0]['configuration_sha256']
        require(len(claims)==1 and (projection['case_id'],projection['version'])==(claims[0]['case_id'],claims[0]['version']),'host_preparation_changed')
    verify_current(queue,preparation,evidence,configuration_sha256)
    built=build_film_prose(projection);body=encoded(built['request']);headers(credential,policy['project'])
    require(len(body)<=65536 and credential.value.encode() not in body,'host_disclosure_size')
    attempt=queue.reserve_provider(preparation,policy=policy,request_sha256=digest(built['request']),evidence_sha256=evidence_sha256,now=now)
    with queue.locked() as (rows,append):
        require(rows[-1]==attempt,'host_attempt_changed')
        c=dict(queue=queue,rows=rows,body=body,credential=credential,project=policy['project'],token=_Permit(),consumed=False,received=None,
               started_at=now,expires_at=min(now+60,policy['expires_at']),monotonic_expires=time.monotonic()+60)
        marker=_ACTIVE.set(c)
        try:
            verify_current(queue,preparation,evidence,configuration_sha256)
            result=FixedResponsesHTTP().post(body,credential=credential,project=policy['project'],timeout=25,authorization=c['token'])
            require(selected(result),'host_response_unbound')
            observe_phase('response_parsing')
            answer,accounting=parse_response(result.body,built['request']['text']['format']['schema'],result.request_id,expected_model=MINI_MODEL,http_result=result)
            require(accounting['usage']['input_tokens']<=400000 and accounting['usage']['output_tokens']<=25000,'host_usage_limit')
            parsed=decode(answer,65536)
            require(parsed['kind']=='final' and parsed['lookups']==[] and parsed['binding_hash']==decode(built['request']['input'][0]['content'][0]['text'],65536)['binding_hash'],'host_answer_binding')
            observe_phase('historical_result_validation')
            retained,handling=_captured_prose_copy(parsed,film_assessment=True,film_prose_v13=True)
            assessment=validate_film_prose(projection,built,retained,now=time.time())
            receipt=dict(kind='seedbox_provider_receipt_v1',request_sha256=digest(built['request']),accounting=accounting,reserved_usd=attempt['reserved_usd'],at=time.time(),provider_signed=False,token_bill_verified=False)
            report=dict(kind='receipt_bound_snapshot_review_v1',request_sha256=digest(built['request']),projection_sha256=digest(projection),local_context_sha256=hashlib.sha256(local_raw).hexdigest(),result=assessment,receipt=receipt,receipt_hash=digest(receipt),reply_hash=digest(parsed),retained_reply_hash=digest(retained),prose_handling=handling,generation_invoked=True,provider_receipt_correlated=True,provider_signed=False,token_bill_verified=False,source_origin='authenticated_host_observations',captured_original='not_established',current_queue='unknown',complete_decisions='unknown',physical_edition='unknown',identity_approval=False,acquisition_approval=False,sent=False,conflict_status='Producer conflict remains for independent review.',assessment_label='complete_film_explanation_v13')
            html=render(report,digest(report),projection,local_raw,report['local_context_sha256'])
            append(dict(type='seedbox_assessment_pending_review_v1',preparation=preparation,attempt_sha256=digest(attempt),report=report,answer=retained,html_sha256=hashlib.sha256(html.encode()).hexdigest(),at=time.time()))
            return dict(report=report,html=html,projection=projection)
        except BaseException as error:
            if str(error) in ('responses_http_401','responses_http_403'):
                from automation.seedbox_circuit import record
                append(record(rows,'provider',str(error),preparation))
            append(dict(type='seedbox_assessment_uncertain_or_refused_v1',preparation=preparation,attempt_sha256=digest(attempt),diagnostic=diagnostic(error),at=time.time()))
            raise ValueError('host_assessment_uncertain_or_refused') from None
        finally:_ACTIVE.reset(marker)


def diagnostic(error):
    from .supervised_credit import safe_diagnostic
    result=safe_diagnostic(error)
    result['wire_status']=('proven_pre_send_refusal' if result['phase'] in ('preflight','slot_started','request_validation','attempt_recording','credit_reservation','wire_authorization','http_setup','tls_setup','dns_lookup','socket_connect','tls_handshake') else 'request_may_have_been_sent')
    result['automatic_retry']=False
    return result


def execute(*args,**kwargs):
    from .supervised_authorization import diagnostic_scope
    with diagnostic_scope():result=_execute(*args,**kwargs)
    from automation.seedbox_evidence import persist_report
    persist_report(args[0],args[1])
    return result
