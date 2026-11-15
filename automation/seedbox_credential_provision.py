"""One-shot encrypted host provisioning. Secret arrives only over stdin.

Main verifies this exact installed code and the literal destination before use.
No plaintext file, environment value, command argument or diagnostic contains the
key. A failed/interrupted operation leaves a consumed reservation; no auto retry.
"""
import os
from pathlib import Path
import re
import subprocess
import sys
from ai_movie_investigator.private_files import private_chain
from ai_movie_investigator.contracts import require,encoded
from ai_movie_investigator.snapshot_authorization import _write_once

NAME='movie-assessment-api-key'
CIPHERTEXT='project-key.cred'
RESERVATION='provision-reserved.json'


def provision(directory,not_after,project,policy_sha256,executable_sha256):
    require(type(not_after) is str and re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ',not_after),'credential_expiry')
    from automation.reviewed_telegram_UNISSUED import read_file
    from automation.seedbox_child import captured
    from ai_movie_investigator.contracts import hash_id
    import hashlib
    hash_id(policy_sha256);hash_id(executable_sha256)
    require(re.fullmatch(r'proj_[A-Za-z0-9_-]{1,200}',project),'credential_project')
    binary=read_file(Path('/usr/bin/systemd-creds'),10485760,False)
    require(hashlib.sha256(binary).hexdigest()==executable_sha256,'credential_executable_changed')
    with private_chain(Path(directory)) as fd:
        _write_once(fd,RESERVATION,encoded(dict(kind='encrypted_credential_provision_v1',name=NAME,not_after=not_after,project=project,policy_sha256=policy_sha256)))
        raw=sys.stdin.buffer.read(513)
        require(8<=len(raw)<=256 and re.fullmatch(rb'sk-[A-Za-z0-9_-]+',raw),'credential_input')
        # Executable and option support are verified by main on the actual host.
        # stdout is encrypted ciphertext; stderr is deliberately never exposed.
        ciphertext=captured(['/usr/bin/systemd-creds','--user','--with-key=host','--name='+NAME,
            '--not-after='+not_after,'encrypt','-','-'],raw,seconds=25,output_limit=16384,environment={'PATH':'/usr/bin:/bin'})
        require(ciphertext and read_file(Path('/usr/bin/systemd-creds'),10485760,False)==binary,'credential_encryption_failed')
        _write_once(fd,CIPHERTEXT,ciphertext)
    return dict(status='encrypted_credential_stored',name=NAME)


def main():
    # Only public path/expiry arguments. Main must not supply the key in argv.
    if len(sys.argv)!=6:return 2
    try:
        result=provision(*sys.argv[1:]);print(result['status']);return 0
    except BaseException:
        print('credential_provision_refused_or_uncertain',file=sys.stderr);return 1

if __name__=='__main__':raise SystemExit(main())
