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
ACCOUNT_EVIDENCE_SECONDS = 900


def refusal_category(error):
    # Exact static membership only: never echo an exception, path or input.
    code=error.args[0] if type(error) is Refusal and len(error.args)==1 and type(error.args[0]) is str else None
    groups={
        'evidence_expired_or_invalid_window':('supervised_evidence_stale',),
        'evidence_changed':('supervised_evidence_changed','packet_changed'),
        'session_expired':('supervised_session_expired','binding_expired','operator_authority_stale'),
        'clock_changed':('supervised_clock_rollback',),
        'privacy_or_storage_refused':('unsafe_parent','unsafe_packet','unsafe_history_path','storage_acl',
            'storage_acl_unsupported','acl_unsupported','parent_changed','supervised_storage_changed','supervised_root_changed'),
        'state_or_binding_refused':('supervised_not_enrolled','supervised_enrollment_binding','supervised_attempt_consumed',
            'supervised_enrollment_exists','supervised_reauthorization_state','supervised_reauthorization_binding',
            'supervised_reauthorization_uncertain','supervised_reauthorization_evidence'),
        'credit_limit_refused':('credit_total_ceiling','supervised_credit_only'),
        'interactive_input_refused':('supervised_interactive_terminal_required','supervised_prompt_required'),
        'credential_format_invalid':('responses_credential_invalid',),
        'http_rejected':('responses_http_rejected',),
        'network_outcome_unknown':('responses_network_completion_unknown',),
        'send_or_response_refused':('supervised_authorization_refused','responses_real_authorization_unimplemented',
            'binding_response_unknown','binding_usage_unknown','binding_receipt_refused'),
    }
    for category,codes in groups.items():
        if code in codes:return category
    if isinstance(error,(EOFError,getpass.GetPassWarning,KeyboardInterrupt)):return 'interactive_input_cancelled'
    if isinstance(error,OSError):return 'io_refused'
    return 'unclassified_refusal'


@contextmanager
def interactive_credential(root):
    credential = prompt_credential()
    marker = _PROMPTED.set((root, credential,time.time(),time.monotonic()))
    try:
        yield credential
    finally:
        _PROMPTED.reset(marker)


def require_prompted(root, credential):
    selected = _PROMPTED.get()
    require(selected is not None and selected[0] is root and selected[1] is credential,
            "supervised_prompt_required")
    return selected[2:]


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
            e['expires_at']-e['observed_at']<=ACCOUNT_EVIDENCE_SECONDS,'supervised_evidence_stale')
    require(rational(e['available_usd'])>=rational([5,100]) and e['paid_fallback'] is False,
            'supervised_credit_only')
    for name in ('account_reference','billing_reference','owner_reference','pricing_reference','context_reference','model_access_reference'):
        require(isinstance(e[name],str) and 1<=len(e[name])<=300 and e[name]!='unknown','supervised_evidence_missing')
    require(e['model']==INTEGRATION_MODEL and e['policy']==POLICY and type(e['context_window']) is int and
            e['context_window']==CONTEXT_TOKENS and rational(e['input_rate'])==INPUT_RATE and
            rational(e['cached_input_rate'])==INPUT_RATE/10 and rational(e['output_rate'])==OUTPUT_RATE,
            'supervised_model_pricing_unknown')


def selection_binding(events,enrolled,selected,slot):
    """Resolve one manual renewal without replacing enrollment or old slots."""
    require(enrolled.get('project')==selected.data['project'],'supervised_enrollment_binding')
    renewals=[e for e in events if e.get('type')=='supervised_reauthorized']
    if not renewals:
        require(enrolled.get('evidence_sha256')==selected.sha256,'supervised_enrollment_binding')
        return
    require(len(renewals)==1 and len(events)>=4 and events[3] is renewals[0],
            'supervised_reauthorization_binding')
    renewal=renewals[0]
    shape(renewal,'type at previous_sha256 evidence_sha256 project expires_at prefix_sha256 permitted_slot')
    require(slot==2 and type(renewal['permitted_slot']) is int and renewal['permitted_slot']==2 and
            renewal['previous_sha256']==enrolled['evidence_sha256'] and
            renewal['evidence_sha256']==selected.sha256 and
            renewal['project']==enrolled['project'] and
            renewal['expires_at']==selected.data['expires_at'] and
            renewal['prefix_sha256']==digest(events[:3]) and
            events[2].get('type')=='supervised_started' and events[2].get('slot')==1 and
            selected.data['observed_at']<=stamp(renewal['at'])<renewal['expires_at'],
            'supervised_reauthorization_binding')


def reauthorize(directory,previous,selected):
    """Append once for unused slot2 only when slot1 provably never reserved."""
    require(type(previous) is SelectedEvidence and type(selected) is SelectedEvidence,
            'supervised_evidence_selection')
    previous.revalidate();selected.revalidate()
    old,new=previous.data,selected.data
    now=time.time()
    validate_evidence(old,stamp(old['observed_at'])) # Retained facts, not fresh authority.
    validate_evidence(new,now)
    require(previous.path!=selected.path and previous.identity[:2]!=selected.identity[:2] and
            previous.sha256!=selected.sha256 and old['project']==new['project'] and
            old['expires_at']<=new['observed_at']<=now,'supervised_reauthorization_evidence')
    root=History(Path(directory))
    with root.transaction(write=True) as (events,append):
        require(len(events)==3 and events[0].get('type')=='supervised_enrollment_started' and
                events[1].get('type')=='supervised_enrolled','supervised_reauthorization_state')
        enrolled=events[1];started=events[2]
        shape(started,'type slot at evidence_hash')
        require(started['type']=='supervised_started' and type(started['slot']) is int and started['slot']==1 and
                started['evidence_hash']==digest(old) and old['observed_at']<=stamp(started['at'])<old['expires_at'],
                'supervised_reauthorization_state')
        require(enrolled['root']==list(root.identity),'supervised_root_changed')
        selection_binding(events,enrolled,previous,1)
        credit=History(root.directory/'credit')
        require(enrolled['credit']==list(credit.identity) and enrolled['credit_file']==file_identity(credit),
                'supervised_storage_changed')
        with credit.transaction(file_identity=enrolled['credit_file']) as (reservations,_):
            require(not reservations,'supervised_reauthorization_uncertain')
            for slot in (1,2):
                attempt=History(root.directory/f'attempt-{slot}')
                require(enrolled['attempts'][str(slot)]==list(attempt.identity),'supervised_storage_changed')
                # Even an empty/unknown journal is outside this precise no-reservation case.
                require(not any(attempt.directory.iterdir()),'supervised_reauthorization_uncertain')
            previous.revalidate();selected.revalidate()
            now=time.time();validate_evidence(new,now)
            root.require_write_transaction(events)
            append(dict(type='supervised_reauthorized',at=now,previous_sha256=previous.sha256,
                evidence_sha256=selected.sha256,project=new['project'],expires_at=new['expires_at'],
                prefix_sha256=digest(events),permitted_slot=2))
    return dict(status='reauthorized_no_api_call',permitted_slot=2)


def prompt_credential():
    require(sys.stdin.isatty() and sys.stderr.isatty(),'supervised_interactive_terminal_required')
    # getpass falls back to echoed input if terminal setup fails; forbid that.
    with warnings.catch_warnings():
        warnings.simplefilter('error',getpass.GetPassWarning)
        value=getpass.getpass('Secret API key (not Tracking ID or project ID; hidden): ')
    return ExplicitCredential(value)


def operator_context(e,history,credit,enrollment,run,case,now,*,expires_at=None):
    selection=dict(run=run,case=case,request_sha256=digest(decode(request(run))),
                   local_context_sha256=digest(e))
    r=dict(mode='synthetic_api_integration',selection=selection,project=e['project'],model=INTEGRATION_MODEL,
        issued_at=now,expires_at=min(e['expires_at'],expires_at) if expires_at is not None else e['expires_at'],history_identity=list(history.identity),currency='USD',
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
        selection_binding(events,enrolled,selected,slot)
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
        with interactive_credential(root) as credential:
            # Validate format without serializing or storing the resulting headers.
            headers(credential,evidence['project'])
            # Conservative typo/identifier filter, not authentication. Keep the
            # root lock held; no slot/debit is consumed by invalid input.
            require(credential.value.startswith('sk-'),'responses_credential_invalid')
            append(dict(type='supervised_started',slot=slot,at=clock(),evidence_hash=digest(evidence)))
            validate_evidence(evidence,max(clock(),time.time()))
            body=request(run_id)
            require(credential.value.encode() not in body and credential.value.encode() not in encoded(evidence),
                    'supervised_credential_disclosed')
            with command_authority(root,events,enrolled,selected,slot,credit,history,credential) as authority:
                context,selection=operator_context(evidence,history,credit,enrolled,run_id,case,clock(),
                    expires_at=authority.deadline)
                parent=HistoricalDiagnosticParent(context,history=history,credit_history=credit,credential=credential)
                answer=ResponsesTransport(enabled=True,credential=credential,clock=clock).complete_credit_test(
                    history=history,run=run_id,case=case,context_sha256=selection['local_context_sha256'],parent=parent)
                append(dict(type='supervised_completed',slot=slot,at=clock(),answer=decode(answer),
                            request_hash=selection['request_sha256'],reserved_usd=[3,100]))
                return dict(status='completed',slot=slot,request_hash=selection['request_sha256'],
                            input_upper_bound=CONTEXT_TOKENS,reserved_usd=[3,100])


class _SafeParser(argparse.ArgumentParser):
    def error(self,message):
        self.exit(2,'Supervised synthetic command refused: category=invalid_arguments; action=unknown. '
                  'Retain state; do not retry automatically.\n')


def main(argv=None):
    parser=_SafeParser(description=__doc__)
    parser.add_argument('--state',required=True,type=Path)
    sub=parser.add_subparsers(dest='action',required=True)
    registration=sub.add_parser('enroll');registration.add_argument('--evidence',required=True,type=Path)
    renewal=sub.add_parser('reauthorize')
    renewal.add_argument('--previous-evidence',required=True,type=Path)
    renewal.add_argument('--evidence',required=True,type=Path)
    send=sub.add_parser('run');send.add_argument('--evidence',required=True,type=Path)
    send.add_argument('--slot',required=True,type=int,choices=(1,2))
    args=parser.parse_args(argv)
    try:
        if args.action=='enroll':
            selected=read_evidence(args.evidence)
            enroll(args.state,selected);result=dict(status='enrolled_no_api_call')
        elif args.action=='reauthorize':
            previous=read_evidence(args.previous_evidence);selected=read_evidence(args.evidence)
            result=reauthorize(args.state,previous,selected)
        else:result=run(args.state,read_evidence(args.evidence),args.slot)
        print(encoded(result).decode());return 0
    except (Exception,KeyboardInterrupt) as error:
        # Never print raw exceptions, remote bodies, credentials or a traceback.
        print('Supervised synthetic command refused: category='+refusal_category(error)+
              '; action='+args.action+'; '+('request status unconfirmed' if args.action=='run' else 'no API request')+
              '. Retain state; do not retry automatically.',file=sys.stderr)
        return 1


if __name__=='__main__':
    # -m executes this file as __main__; authority imports the canonical module.
    # Use its classes and prompt ContextVar throughout the executable command.
    from ai_movie_investigator.supervised_credit import main as canonical_main
    raise SystemExit(canonical_main())
