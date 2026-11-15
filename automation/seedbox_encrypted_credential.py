"""User-scoped systemd credential IPC; plaintext remains in captured memory.

The host's LoadCredentialEncrypted user-service failure is NOT bypassed by
permission changes. This selects the separately permitted `systemd-creds --user
 decrypt` interface, verified with an invented credential before deployment.
No actual credential is read on import; no alternative store or plaintext fallback.
"""
import hashlib
from pathlib import Path
import re
import subprocess
from ai_movie_investigator.contracts import require,shape,hash_id
from ai_movie_investigator.private_files import private_chain,read_private
from ai_movie_investigator.responses_http import ExplicitCredential,headers

NAME='movie-assessment-api-key'


def credential(selection,*,project):
    shape(selection,'kind path sha256 project name executable_sha256')
    require(selection['kind']=='seedbox_systemd_user_encrypted_v1' and selection['project']==project and selection['name']==NAME,'host_credential_selection')
    hash_id(selection['sha256']);hash_id(selection['executable_sha256'])
    path=Path(selection['path'])
    with private_chain(path.parent):
        encrypted=read_private(path,16384)
        require(hashlib.sha256(encrypted).hexdigest()==selection['sha256'],'host_credential_changed')
        # Reuse the reviewed no-follow regular-file/ancestor executable reader.
        from automation.reviewed_telegram_UNISSUED import read_file
        binary=read_file(Path('/usr/bin/systemd-creds'),10485760,False)
        require(hashlib.sha256(binary).hexdigest()==selection['executable_sha256'],'host_credential_executable_changed')
        from automation.seedbox_child import captured
        try:
            plaintext=captured(['/usr/bin/systemd-creds','--user','--name='+NAME,'--newline=no','decrypt','-','-'],
                encrypted,seconds=15,output_limit=256,environment={'PATH':'/usr/bin:/bin'})
        except Exception:
            raise ValueError('host_credential_unavailable') from None
        require(8<=len(plaintext)<=256 and re.fullmatch(rb'sk-[A-Za-z0-9_-]+',plaintext),'host_credential_unavailable')
        require(read_file(Path('/usr/bin/systemd-creds'),10485760,False)==binary,'host_credential_executable_changed')
        value=ExplicitCredential(plaintext.decode('ascii'));headers(value,project)
        require(read_private(path,16384)==encrypted,'host_credential_changed')
    return value
