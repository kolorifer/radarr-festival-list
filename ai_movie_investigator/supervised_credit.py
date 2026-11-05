"""One supervised synthetic count+generation command. Real HTTP remains closed.

No automatic enrollment, retry, reset, credential discovery or movie inputs.
Operator evidence pins are correspondence, never live authentication by themselves.
"""
import argparse
import getpass
import hashlib
import os
from pathlib import Path
import sys
import time
import warnings

from .bound_send import HistoricalDiagnosticParent, OperatorContext
from .contracts import Refusal, decode, digest, encoded, require, shape, stamp
from .credit_test import POLICY, PER_REQUEST, count_request, count_receipt, request, reserve
from .history import History, FILENAME, checked
from .pilot_account import COVERAGE
from .responses_http import ExplicitCredential, FixedResponsesHTTP, headers
from .responses_protocol import INTEGRATION_MODEL, OUTPUT_TOKENS
from .responses_transport import ResponsesTransport, real_activation_refusal
from .spending import rational


def file_identity(history):
    p=history.directory / FILENAME
    info=p.lstat(); checked(info)
    return [info.st_dev,info.st_ino]


def enroll(directory):
    root=History(Path(directory))
    with root.transaction(write=True) as (events,append):
        require(not events, 'supervised_enrollment_exists')
        append(dict(type='supervised_enrollment_started',at=root.clock()))
        for name in ('credit','attempt-1','attempt-2'):
            (root.directory/name).mkdir(mode=0o700)
        credit=History(root.directory/'credit')
        with credit.transaction(write=True):pass
        append(dict(type='supervised_enrolled', root=list(root.identity),
            credit=list(credit.identity),credit_file=file_identity(credit),
            attempts={str(n):list(History(root.directory/f'attempt-{n}').identity) for n in (1,2)}))


def read_evidence(path):
    path=Path(path)
    require(path.is_absolute() and path.parent.resolve(strict=True)==path.parent,'supervised_evidence_path')
    checked(path.parent.lstat(),True)
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        info=os.fstat(fd);checked(info)
        require(info.st_size<=16384,'supervised_evidence_size')
        raw=os.read(fd,16385)
        current=os.stat(path,follow_symlinks=False)
        require((info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns)==
                (current.st_dev,current.st_ino,current.st_size,current.st_mtime_ns),'supervised_evidence_changed')
        return decode(raw,16384)
    finally:os.close(fd)


def validate_evidence(e,now):
    shape(e,'project account_reference observed_at expires_at credit_expires_at available_usd '
          'billing_reference paid_fallback owner_reference count_fee_reference count_fee_maximum count_coverage_reference')
    require(isinstance(e['project'],str) and e['project'].startswith('proj_'),'supervised_project')
    require(stamp(e['observed_at'])<=now<stamp(e['expires_at'])<=stamp(e['credit_expires_at']) and
            e['expires_at']-e['observed_at']<=300,'supervised_evidence_stale')
    require(rational(e['available_usd'])>=rational([5,100]) and e['paid_fallback'] is False,
            'supervised_credit_only')
    for name in ('account_reference','billing_reference','owner_reference','count_fee_reference','count_coverage_reference'):
        require(isinstance(e[name],str) and 1<=len(e[name])<=300 and e[name]!='unknown','supervised_evidence_missing')
    require(0<=rational(e['count_fee_maximum'])<=PER_REQUEST,'supervised_count_fee_unknown')


def prompt_credential():
    require(sys.stdin.isatty() and sys.stderr.isatty(),'supervised_interactive_terminal_required')
    # getpass falls back to echoed input if terminal setup fails; forbid that.
    with warnings.catch_warnings():
        warnings.simplefilter('error',getpass.GetPassWarning)
        value=getpass.getpass('Restricted project API key (not saved): ')
    return ExplicitCredential(value)


def operator_context(e,history,credit,enrollment,run,case,count,now):
    selection=dict(run=run,case=case,request_sha256=digest(decode(request(run))),
                   local_context_sha256=digest(dict(evidence=e,count=count)))
    r=dict(mode='synthetic_api_integration',selection=selection,project=e['project'],model=INTEGRATION_MODEL,
        issued_at=now,expires_at=e['expires_at'],history_identity=list(history.identity),currency='USD',
        ceiling=[1,100],output_limit=OUTPUT_TOKENS,credit_history_identity=enrollment['credit'],
        credit_history_file_identity=enrollment['credit_file'])
    facts=dict(owner=dict(operation=r['mode'],max_calls=1,currency='USD',ceiling=[1,100]),
        privacy=dict(request_sha256=selection['request_sha256'],store=False,tools=[]),
        account=dict(project=e['project'],model=INTEGRATION_MODEL,policy=POLICY),
        credential_route=dict(project=e['project'],injection_route='local-no-echo-memory-only'),
        coverage=dict(request_sha256=selection['request_sha256'],policy=POLICY,coverage=COVERAGE,
            counter_identity=count['request_id'],input_upper_bound=count['input_tokens']),
        pricing=dict(policy=POLICY,currency='USD',input=[5,100000000],cache_read=[5,1000000000],
            cache_write=[0,1],output=[4,10000000],ancillary_maximum=[0,1]))
    binding=digest(r)
    r['evidence']={role:dict(binding_hash=binding,issuer='supervised-operator',
        reference=digest(e),observed_at=e['observed_at'],expires_at=e['expires_at'],facts=value)
        for role,value in facts.items()}
    raw=encoded(r)
    return OperatorContext(raw,hashlib.sha256(raw).hexdigest(),tuple((k,digest(v)) for k,v in r['evidence'].items())),selection


def run(directory,evidence,slot,*,clock=time.time):
    require(type(slot) is int and slot in (1,2),'supervised_slot')
    validate_evidence(evidence,clock()) # Before prompt, journal mutation or HTTP.
    refusal=real_activation_refusal(None)
    require(refusal is None,refusal or 'supervised_activation_refused')
    root=History(Path(directory),clock=clock)
    with root.transaction(write=True) as (events,append):
        require(len(events)>=2 and events[0]['type']=='supervised_enrollment_started' and
                events[1]['type']=='supervised_enrolled','supervised_not_enrolled')
        enrolled=events[1]
        require(enrolled['root']==list(root.identity),'supervised_root_changed')
        require(not any(e.get('slot')==slot for e in events),'supervised_attempt_consumed')
        credit=History(root.directory/'credit',clock=clock)
        history=History(root.directory/f'attempt-{slot}',clock=clock)
        require(enrolled['credit']==list(credit.identity) and enrolled['credit_file']==file_identity(credit) and
                enrolled['attempts'][str(slot)]==list(history.identity),'supervised_storage_changed')
        with credit.transaction(file_identity=enrolled['credit_file']):pass
        require(not history.read(),'supervised_attempt_consumed')
        run_id=f'synthetic-integration-{slot}'
        case=dict(source='synthetic-credit-integration',case_id='outcome-'+digest('synthetic-example'),
                  version=digest(decode(request(run_id))),occurrence=None)
        append(dict(type='supervised_started',slot=slot,at=clock(),evidence_hash=digest(evidence)))
        credential=prompt_credential()
        # Validate format without serializing or storing the resulting headers.
        headers(credential,evidence['project'])
        validate_evidence(evidence,clock())
        body=count_request(run_id)
        require(credential.value.encode() not in body and credential.value.encode() not in encoded(evidence),
                'supervised_credential_disclosed')
        reserve(credit,project=evidence['project'],request_hash=digest(decode(body)),input_bound=65536,
                now=clock(),file_identity=enrolled['credit_file'])
        append(dict(type='supervised_count_attempted',slot=slot,at=clock(),request_hash=digest(decode(body))))
        validate_evidence(evidence,clock())
        # Caller facts cannot unlock the unconditionally closed fixed HTTP gate.
        result=FixedResponsesHTTP().count(body,credential=credential,project=evidence['project'],timeout=25,
            authorization=dict(operation='supervised_synthetic_count',evidence_hash=digest(evidence)))
        require(credential.value.encode() not in result.body and
                credential.value not in (result.request_id or ''),'supervised_credential_echo')
        counted=count_receipt(result,run=run_id,project=evidence['project'])
        validate_evidence(evidence,clock())
        append(dict(type='supervised_count_observed',slot=slot,at=clock(),receipt=counted))
        context,selection=operator_context(evidence,history,credit,enrolled,run_id,case,counted,clock())
        parent=HistoricalDiagnosticParent(context,history=history,credit_history=credit,credential=credential)
        answer=ResponsesTransport(enabled=True,credential=credential,clock=clock).complete_credit_test(
            history=history,run=run_id,case=case,context_sha256=selection['local_context_sha256'],parent=parent)
        append(dict(type='supervised_completed',slot=slot,at=clock(),answer=decode(answer),
                    request_hash=selection['request_sha256'],reserved_usd=[2,100]))
        return dict(status='completed',slot=slot,request_hash=selection['request_sha256'],
                    input_tokens=counted['input_tokens'],reserved_usd=[2,100])


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state',required=True,type=Path)
    sub=parser.add_subparsers(dest='action',required=True)
    sub.add_parser('enroll')
    send=sub.add_parser('run');send.add_argument('--evidence',required=True,type=Path)
    send.add_argument('--slot',required=True,type=int,choices=(1,2))
    args=parser.parse_args(argv)
    try:
        if args.action=='enroll':
            enroll(args.state);result=dict(status='enrolled_no_api_call')
        else:result=run(args.state,read_evidence(args.evidence),args.slot)
        print(encoded(result).decode());return 0
    except (Refusal,OSError,ValueError,TypeError,KeyError,EOFError,getpass.GetPassWarning):
        # Never print raw exceptions, remote bodies, credentials or a traceback.
        print('Supervised synthetic command refused; retain state, do not retry automatically.',file=sys.stderr)
        return 1


if __name__=='__main__':
    raise SystemExit(main())
