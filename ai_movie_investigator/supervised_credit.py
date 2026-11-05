"""One supervised fixed-synthetic command with ephemeral interactive authority.

No automatic enrollment, retry, reset, credential discovery or movie inputs.
Operator evidence pins are correspondence, never live authentication by themselves.
"""
from contextlib import contextmanager
from contextvars import ContextVar
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
from .credit_test import POLICY, PER_REQUEST, CONTEXT_TOKENS, CONTEXT_COVERAGE, INPUT_RATE, OUTPUT_RATE, request, ledger_total, TOTAL
from .history import History, FILENAME, checked
from .responses_http import ExplicitCredential, headers
from .responses_protocol import INTEGRATION_MODEL, OUTPUT_TOKENS
from .responses_transport import ResponsesTransport
from .supervised_authorization import command_authority
from .spending import rational
from .private_files import read_private

_PROMPTED = ContextVar("supervised_prompted_credential", default=None)


@contextmanager
def interactive_credential(root):
    credential = prompt_credential()
    marker = _PROMPTED.set((root, credential))
    try:
        yield credential
    finally:
        _PROMPTED.reset(marker)


def require_prompted(root, credential):
    selected = _PROMPTED.get()
    require(selected is not None and selected[0] is root and selected[1] is credential,
            "supervised_prompt_required")


def file_identity(history):
    p=history.directory / FILENAME
    info=p.lstat(); checked(info)
    return [info.st_dev,info.st_ino]


def enroll(directory, selected=None):
    if selected is not None:
        require(type(selected) is SelectedEvidence,'supervised_evidence_selection')
        selected.revalidate()
        validate_evidence(selected.data,time.time())
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
            attempts={str(n):list(History(root.directory/f'attempt-{n}').identity) for n in (1,2)},
            evidence_sha256=selected.sha256 if selected else None,
            project=selected.data['project'] if selected else None))


def _read_evidence(path):
    path=Path(path)
    before=path.lstat()
    raw=read_private(path,16384)
    after=path.lstat()
    identity=lambda info:(info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns)
    require(identity(before)==identity(after),'supervised_evidence_changed')
    # Persistent selection binds bytes and dev/inode/size/mtime. ctime is a
    # per-read race check, not proof against same-owner change-and-restore.
    return raw,identity(after)[:4]


_EVIDENCE_READER = object()


class SelectedEvidence:
    __slots__=('path','raw','identity','sha256')
    def __init__(self,path,raw,identity,reader):
        require(reader is _EVIDENCE_READER,'supervised_evidence_selection')
        self.path,self.raw,self.identity=Path(path),raw,identity
        self.sha256=hashlib.sha256(raw).hexdigest()
    @property
    def data(self):return decode(self.raw,16384)
    def revalidate(self):
        raw,identity=_read_evidence(self.path)
        require(raw==self.raw and identity==self.identity,'supervised_evidence_changed')


def read_evidence(path):
    raw,identity=_read_evidence(path)
    decode(raw,16384)
    return SelectedEvidence(path,raw,identity,_EVIDENCE_READER)


def validate_evidence(e,now):
    shape(e,'project account_reference observed_at expires_at credit_expires_at available_usd '
          'billing_reference paid_fallback owner_reference model policy context_window pricing_reference context_reference model_access_reference input_rate cached_input_rate output_rate')
    require(isinstance(e['project'],str) and e['project'].startswith('proj_'),'supervised_project')
    require(stamp(e['observed_at'])<=now<stamp(e['expires_at'])<=stamp(e['credit_expires_at']) and
            e['expires_at']-e['observed_at']<=300,'supervised_evidence_stale')
    require(rational(e['available_usd'])>=rational([5,100]) and e['paid_fallback'] is False,
            'supervised_credit_only')
    for name in ('account_reference','billing_reference','owner_reference','pricing_reference','context_reference','model_access_reference'):
        require(isinstance(e[name],str) and 1<=len(e[name])<=300 and e[name]!='unknown','supervised_evidence_missing')
    require(e['model']==INTEGRATION_MODEL and e['policy']==POLICY and type(e['context_window']) is int and
            e['context_window']==CONTEXT_TOKENS and rational(e['input_rate'])==INPUT_RATE and
            rational(e['cached_input_rate'])==INPUT_RATE/10 and rational(e['output_rate'])==OUTPUT_RATE,
            'supervised_model_pricing_unknown')


def prompt_credential():
    require(sys.stdin.isatty() and sys.stderr.isatty(),'supervised_interactive_terminal_required')
    # getpass falls back to echoed input if terminal setup fails; forbid that.
    with warnings.catch_warnings():
        warnings.simplefilter('error',getpass.GetPassWarning)
        value=getpass.getpass('Restricted project API key (not saved): ')
    return ExplicitCredential(value)


def operator_context(e,history,credit,enrollment,run,case,now):
    selection=dict(run=run,case=case,request_sha256=digest(decode(request(run))),
                   local_context_sha256=digest(e))
    r=dict(mode='synthetic_api_integration',selection=selection,project=e['project'],model=INTEGRATION_MODEL,
        issued_at=now,expires_at=e['expires_at'],history_identity=list(history.identity),currency='USD',
        ceiling=[3,100],output_limit=OUTPUT_TOKENS,credit_history_identity=enrollment['credit'],
        credit_history_file_identity=enrollment['credit_file'])
    facts=dict(owner=dict(operation=r['mode'],max_calls=1,currency='USD',ceiling=[3,100]),
        privacy=dict(request_sha256=selection['request_sha256'],store=False,tools=[]),
        account=dict(project=e['project'],model=INTEGRATION_MODEL,policy=POLICY),
        credential_route=dict(project=e['project'],injection_route='local-no-echo-memory-only'),
        coverage=dict(request_sha256=selection['request_sha256'],policy=POLICY,coverage=CONTEXT_COVERAGE,
            counter_identity=e['context_reference'],input_upper_bound=CONTEXT_TOKENS),
        pricing=dict(policy=POLICY,currency='USD',input=[5,100000000],cache_read=[5,1000000000],
            cache_write=[0,1],output=[4,10000000],ancillary_maximum=[0,1]))
    binding=digest(r)
    r['evidence']={role:dict(binding_hash=binding,issuer='supervised-operator',
        reference=digest(e),observed_at=e['observed_at'],expires_at=e['expires_at'],facts=value)
        for role,value in facts.items()}
    raw=encoded(r)
    return OperatorContext(raw,hashlib.sha256(raw).hexdigest(),tuple((k,digest(v)) for k,v in r['evidence'].items())),selection


def run(directory,selected,slot,*,clock=time.time):
    require(type(slot) is int and slot in (1,2),'supervised_slot')
    require(type(selected) is SelectedEvidence,'supervised_evidence_selection')
    selected.revalidate()
    evidence=selected.data
    validate_evidence(evidence,max(clock(),time.time())) # Before prompt, journal mutation or HTTP.
    root=History(Path(directory),clock=clock)
    with root.transaction(write=True) as (events,append):
        require(len(events)>=2 and events[0]['type']=='supervised_enrollment_started' and
                events[1]['type']=='supervised_enrolled','supervised_not_enrolled')
        enrolled=events[1]
        require(enrolled['root']==list(root.identity),'supervised_root_changed')
        require(enrolled.get('evidence_sha256')==selected.sha256 and
                enrolled.get('project')==evidence['project'],'supervised_enrollment_binding')
        require(not any(e.get('slot')==slot for e in events),'supervised_attempt_consumed')
        credit=History(root.directory/'credit',clock=clock)
        history=History(root.directory/f'attempt-{slot}',clock=clock)
        require(enrolled['credit']==list(credit.identity) and enrolled['credit_file']==file_identity(credit) and
                enrolled['attempts'][str(slot)]==list(history.identity),'supervised_storage_changed')
        with credit.transaction(file_identity=enrolled['credit_file']) as (old,_):
            require(ledger_total(old,evidence['project'])+PER_REQUEST<=TOTAL,'credit_total_ceiling')
        require(not history.read(),'supervised_attempt_consumed')
        run_id=f'synthetic-integration-{slot}'
        case=dict(source='synthetic-credit-integration',case_id='outcome-'+digest('synthetic-example'),
                  version=digest(decode(request(run_id))),occurrence=None)
        append(dict(type='supervised_started',slot=slot,at=clock(),evidence_hash=digest(evidence)))
        with interactive_credential(root) as credential:
            # Validate format without serializing or storing the resulting headers.
            headers(credential,evidence['project'])
            validate_evidence(evidence,max(clock(),time.time()))
            body=request(run_id)
            require(credential.value.encode() not in body and credential.value.encode() not in encoded(evidence),
                    'supervised_credential_disclosed')
            with command_authority(root,events,enrolled,selected,slot,credit,history,credential):
                context,selection=operator_context(evidence,history,credit,enrolled,run_id,case,clock())
                parent=HistoricalDiagnosticParent(context,history=history,credit_history=credit,credential=credential)
                answer=ResponsesTransport(enabled=True,credential=credential,clock=clock).complete_credit_test(
                    history=history,run=run_id,case=case,context_sha256=selection['local_context_sha256'],parent=parent)
                append(dict(type='supervised_completed',slot=slot,at=clock(),answer=decode(answer),
                            request_hash=selection['request_sha256'],reserved_usd=[3,100]))
                return dict(status='completed',slot=slot,request_hash=selection['request_sha256'],
                            input_upper_bound=CONTEXT_TOKENS,reserved_usd=[3,100])


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state',required=True,type=Path)
    sub=parser.add_subparsers(dest='action',required=True)
    registration=sub.add_parser('enroll');registration.add_argument('--evidence',required=True,type=Path)
    send=sub.add_parser('run');send.add_argument('--evidence',required=True,type=Path)
    send.add_argument('--slot',required=True,type=int,choices=(1,2))
    args=parser.parse_args(argv)
    try:
        if args.action=='enroll':
            enroll(args.state,read_evidence(args.evidence));result=dict(status='enrolled_no_api_call')
        else:result=run(args.state,read_evidence(args.evidence),args.slot)
        print(encoded(result).decode());return 0
    except (Refusal,OSError,ValueError,TypeError,KeyError,EOFError,getpass.GetPassWarning):
        # Never print raw exceptions, remote bodies, credentials or a traceback.
        print('Supervised synthetic command refused; retain state, do not retry automatically.',file=sys.stderr)
        return 1


if __name__=='__main__':
    # -m executes this file as __main__; authority imports the canonical module.
    # Use its classes and prompt ContextVar throughout the executable command.
    from ai_movie_investigator.supervised_credit import main as canonical_main
    raise SystemExit(canonical_main())
