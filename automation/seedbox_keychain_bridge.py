"""Genuine one-shot -m entry: native no-UI Keychain directly to fixed SSH stdin.

No key in argv/environment/file/log. Exact main-selected config and destination;
failed or uncertain provisioning is not repeated. Remote expiry is mandatory.
"""
import hashlib,os,re,shlex,stat,sys,threading,time
from pathlib import Path
from ai_movie_investigator.contracts import require,decode,digest
from ai_movie_investigator.private_files import private_chain,read_private
from ai_movie_investigator.snapshot_authorization import _write_once
from automation.seedbox_child import captured


def run(path,expected):
    raw=read_private(Path(path),65536);require(hashlib.sha256(raw).hexdigest()==expected,'bridge_selection_changed');p=decode(raw,65536)
    require(p['kind']=='seedbox_keychain_bridge_v1' and re.fullmatch(r'[a-zA-Z0-9.-]+',p['host']) and re.fullmatch(r'[a-zA-Z0-9_-]+',p['user']) and type(p['port']) is int and 1<=p['port']<=65535,'bridge_destination')
    from automation.seedbox_credit_policy import validate
    validate(p['credit_policy'],now=time.time())
    require(p['not_after_epoch']==p['credit_policy']['expires_at'],'bridge_expiry')
    from datetime import datetime,timezone
    expiry=datetime.fromtimestamp(p['not_after_epoch'],timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    # SSH alone reads its private key. Python checks metadata without reading,
    # hashing or copying key bytes. Main pins the already approved identity.
    key_path=Path(p['ssh_key']['path'])
    from ai_movie_investigator.private_files import safe_acl
    with private_chain(key_path.parent) as parent:
        fd=os.open(key_path.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
        try:
            info=os.fstat(fd)
            require(stat.S_ISREG(info.st_mode) and info.st_uid==os.getuid() and stat.S_IMODE(info.st_mode)==0o600 and info.st_nlink==1 and [info.st_dev,info.st_ino,info.st_uid,info.st_mode,info.st_nlink]==p['ssh_key']['metadata'],'bridge_ssh_key_changed')
            safe_acl(fd,False)
        finally:os.close(fd)
    from automation.reviewed_telegram_UNISSUED import read_file
    known=read_file(Path(p['known_hosts']['path']),65536,False)
    require(hashlib.sha256(known).hexdigest()==p['known_hosts']['sha256'],'bridge_known_hosts_changed')
    with private_chain(Path(p['state'])) as parent:
        _write_once(parent,'bridge-reserved.json',raw)
        remote=[p['python'],'-I','-B',p['bootstrap'],p['manifest_path'],p['manifest_sha256'],'provision',p['destination'],expiry,p['credit_policy']['project'],digest(p['credit_policy']),p['systemd_creds_sha256']]
        require(all(type(v) is str and '\x00' not in v and '\n' not in v for v in remote),'bridge_command')
        argv=['/usr/bin/ssh','-F','/dev/null','-T','-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=yes','-o','GlobalKnownHostsFile=/dev/null','-o','UserKnownHostsFile='+p['known_hosts']['path'],'-o','ConnectTimeout=5','-o','ServerAliveInterval=5','-o','ServerAliveCountMax=1','-i',p['ssh_key']['path'],'-p',str(p['port']),p['user']+'@'+p['host'],shlex.join(remote)]
        from ai_movie_investigator.keychain_credential import one_shot_process,credential
        with one_shot_process():secret=credential(p['credit_policy']['project'])
        result=captured(argv,secret.value.encode('ascii'),seconds=40,output_limit=128,environment={'PATH':'/usr/bin:/bin'})
        require(result==b'encrypted_credential_stored\n','bridge_uncertain')
        _write_once(parent,'bridge-completed.json',b'{"status":"encrypted_credential_stored"}\n')


def main():
    # A hard outer deadline includes native code and remote stdin handling. It
    # never prints secrets or tries to unlock/change Keychain permissions.
    timer=threading.Timer(50,lambda:os._exit(124));timer.daemon=True;timer.start()
    try:
        require(len(sys.argv)==3 and sys.flags.isolated and sys.dont_write_bytecode,'bridge_entry')
        run(sys.argv[1],sys.argv[2]);return 0
    except BaseException:
        return 1
    finally:timer.cancel()

if __name__=='__main__':raise SystemExit(main())
