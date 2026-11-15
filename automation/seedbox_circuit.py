"""Retained shared denial circuit; case-specific gaps never open this circuit."""
import time
from pathlib import Path
from ai_movie_investigator.contracts import require,decode,digest
from ai_movie_investigator.private_files import read_private


def active(rows):
    cleared={r['circuit_sha256'] for r in rows if r['type']=='seedbox_global_recovery_v1'}
    return [r for r in rows if r['type']=='seedbox_global_circuit_v1' and digest(r) not in cleared]


def record(rows,scope,reason,preparation=None):
    require(scope in ('source','credential','provider','telegram'),'host_circuit_scope')
    require(reason in ('shared_source_auth_denied','shared_source_configuration_or_access','host_credential_unavailable','responses_http_401','responses_http_403','telegram_auth_denied'),'host_circuit_reason')
    return dict(type='seedbox_global_circuit_v1',scope=scope,reason=reason,preparation=preparation,configuration_sha256=rows[0]['configuration_sha256'],at=time.time(),automatic_recovery=False)


def recover(queue,evidence_path,evidence_sha256):
    """Explicit main-issued material access-recovery evidence, never a timer.

    This private owner artifact is a trust input, not proof that a model or this
    worker tested restored access. Main may perform this routine authorized step.
    It cannot alter code, source grants, policy, legacy reservations or config.
    """
    import hashlib
    raw=read_private(Path(evidence_path),65536)
    require(hashlib.sha256(raw).hexdigest()==evidence_sha256,'host_recovery_pin')
    evidence=decode(raw,65536)
    require(set(evidence)=={'kind','circuit_sha256','configuration_sha256','observed_at','material_change','observation_reference'} and evidence['kind']=='main_verified_shared_access_recovery_v1' and evidence['material_change']=='access_restored' and type(evidence['observation_reference']) is str and 1<=len(evidence['observation_reference'])<=512,'host_recovery_evidence')
    with queue.locked() as (rows,append):
        matches=[r for r in active(rows) if digest(r)==evidence['circuit_sha256']]
        require(len(matches)==1,'host_recovery_circuit');blocked=matches[0]
        require(evidence['configuration_sha256']==blocked['configuration_sha256']==rows[0]['configuration_sha256'] and blocked['at']<=evidence['observed_at']<=time.time() and time.time()-evidence['observed_at']<=900,'host_recovery_changed')
        append(dict(type='seedbox_global_recovery_v1',circuit_sha256=digest(blocked),evidence_sha256=evidence_sha256,evidence=evidence,at=time.time()))
        if blocked['preparation']:
            prep=blocked['preparation']
            # Resume preparation/local work only. Existing provider and sender
            # reservations remain consumed and their no-replay checks still win.
            failures=[r for r in rows if r['type']=='seedbox_source_blocked_v1' and r['preparation']==prep]
            if failures:append(dict(type='seedbox_source_recovery_v1',preparation=prep,failure_sha256=digest(failures[-1]),reason='main_verified_access_restored',at=time.time()))
            append(dict(type='seedbox_operation_recovery_v1',preparation=prep,evidence_sha256=evidence_sha256,at=time.time()))
