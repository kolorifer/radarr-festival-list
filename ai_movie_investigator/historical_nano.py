"""Explicit exact-disclosure historical Nano preparation; no automatic invocation."""
import sys
import time
from pathlib import Path
from .contracts import decode,digest,encoded,require,shape
from .private_files import read_private
from .credit_test import POLICY
from .history import History


def proposal(path,at):
    from .manual_offline import parse_packet,build_request
    raw=read_private(Path(path));packet,fingerprint=parse_packet(raw)
    require(packet['kind']=='historical_expanded_projection','historical_expanded_required')
    case,run,disclosure,body=build_request(packet,fingerprint,now=at)
    wire=decode(body,65536);wire.pop('prompt_cache_options');wire.update(POLICY)
    body=encoded(wire);require(len(body)<=65536,'historical_disclosure_size')
    # Conservative per asserted case ID; source authenticity is not established.
    stable=digest({k:packet[k] for k in ('case_id',)})
    return dict(input_path=str(Path(path)),input_sha256=fingerprint,prepared_at=at,
                fingerprint=stable,case=case,run=run,disclosure=disclosure,request=wire)


def consent(proposed,project):
    return dict(request_sha256=digest(proposed['request']),project=project,
        selected_case=proposed['case'],input_sha256=proposed['input_sha256'],
        policy=POLICY,maximum_debit_usd=[3,100],endpoint='https://api.openai.com/v1/responses',
        purpose='one_historical_manual_diagnostic',currentness='unknown',decisions='unknown',
        identity_approval=False,acquisition_approval=False)


def validate(grant,project):
    shape(grant,'input_path input_sha256 prepared_at fingerprint case run disclosure request consent owner_confirmation')
    expected=proposal(grant['input_path'],grant['prepared_at'])
    require({k:v for k,v in grant.items() if k not in ('owner_confirmation','consent')}==expected and
            grant['consent']==consent(expected,project) and
            grant['owner_confirmation']==digest(grant['consent']),'historical_disclosure_changed')
    return encoded(grant['request'])


def authorize(directory,selected,input_path):
    from . import supervised_credit as c
    require(type(selected) is c.SelectedEvidence,'supervised_evidence_selection')
    selected.revalidate();c.validate_evidence(selected.data,time.time(),standing=True)
    require(sys.stdin.isatty() and sys.stderr.isatty(),'supervised_interactive_terminal_required')
    grant=proposal(input_path,time.time());root=History(Path(directory))
    with root.transaction(write=True) as (events,append):
        # Check affordability/history and replay BEFORE displaying or confirming.
        slot=c._prepare_next_locked(root,events,append,selected,create=False,historical=grant)
        grant['consent']=consent(grant,selected.data['project'])
        fingerprint=digest(grant['consent'])
        print('Historical disclosure only; not a current queue or acquisition approval.',file=sys.stderr)
        print(encoded(grant['request']).decode(),file=sys.stderr)
        print(encoded(grant['consent']).decode(),file=sys.stderr)
        print('Exact disclosure grant SHA-256: '+fingerprint,file=sys.stderr)
        answer=input('Authorize this one disclosure by entering its full SHA-256: ')
        require(answer==fingerprint,'historical_owner_confirmation_required')
        grant['owner_confirmation']=fingerprint
        validate(grant,selected.data['project']);selected.revalidate()
        require(c._prepare_next_locked(root,events,append,selected,create=True,historical=grant)==slot,
                'historical_disclosure_changed')
    return dict(status='historical_disclosure_authorized_no_api_call',slot=slot,request_sha256=digest(grant['request']),grant_sha256=fingerprint)


def report(grant,answer,history):
    from .disclosure import restore
    from .controller import validate_final
    reply=restore(answer,run=grant['run'],disclosure=grant['disclosure'],binding_hash=digest(grant['case']))
    result=validate_final(reply['result'],{},dict(conflicting_ids=True,known_identity=None),time.time())
    require(result['status'] in ('unresolved','blocked') and not result['alternatives'],
            'normalized_identity_not_established')
    rows=history.read();require(len(rows)==3 and rows[-1]['type']=='bound_send_receipt' and
        rows[-1]['request_sha256']==digest(grant['request']),'historical_receipt_missing')
    data=decode(grant['request']['input'][0]['content'][0]['text'],32768)
    return dict(kind='receipt_bound_historical_manual_review',request_sha256=digest(grant['request']),
        input_sha256=grant['input_sha256'],case=grant['case'],result=result,
        qualifications=data['qualifications'],observations=data['historical_observations'],
        receipt=rows[-1],generation_invoked=True,provider_signed=False,token_bill_verified=False,
        source_authenticity_verified=False,currentness='unknown',decisions='unknown',captured_bytes=False,
        identity_approval=False,acquisition_approval=False,sent=False,
        qualification='Historical unresolved/blocked review only; proposals in rationale are not current identity or acquisition approval.')
