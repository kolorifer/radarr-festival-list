"""Invented installed-confinement probe only; no provider/source/Telegram calls."""
import hashlib,os
from pathlib import Path
from ai_movie_investigator.contracts import require,decode
from ai_movie_investigator.private_files import read_private,private_chain
from ai_movie_investigator.snapshot_authorization import _write_once


def probe(config):
    require(config['kind']=='seedbox_invented_probe_v1' and config['credential']['project']=='proj_invented_fixture','host_probe_only')
    selection=config['credential'];parent=Path(selection['path']).parent
    provision=decode(read_private(parent/'provision-reserved.json'))
    require(provision['project']=='proj_invented_fixture' and provision['name']=='movie-assessment-api-key','host_probe_credential')
    from automation.seedbox_encrypted_credential import credential
    value=credential(selection,project='proj_invented_fixture')
    require(hashlib.sha256(value.value.encode()).hexdigest()==hashlib.sha256(b'sk-SYNTHETIC_FIXTURE').hexdigest(),'host_probe_invented_only')
    state=Path(config['state'])
    with private_chain(state) as fd:os.mkdir('probe-evidence',0o700,dir_fd=fd)
    with private_chain(state/'probe-evidence') as fd:_write_once(fd,'retained.bin',b'INVENTED')
    require(read_private(state/'probe-evidence'/'retained.bin')==b'INVENTED','host_probe_retention')
    try:fd=os.open(config['denied_fixture_file'],os.O_RDONLY|os.O_NOFOLLOW)
    except PermissionError:pass
    else:os.close(fd);raise ValueError('host_probe_isolation_failed')
    print('seedbox_invented_credential_and_retention_verified')
