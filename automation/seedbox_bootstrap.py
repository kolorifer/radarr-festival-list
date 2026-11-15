"""Isolated installed entry. Hash-check all code before importing the worker."""
import hashlib,json,os,runpy,stat,sys,threading
from pathlib import Path


def read(path,limit=1048576):
    p=Path(path)
    if p.resolve(strict=True)!=p:raise ValueError('bootstrap_path')
    for parent in p.parents:
        s=parent.lstat()
        if not stat.S_ISDIR(s.st_mode) or s.st_uid not in (0,os.getuid()) or s.st_mode&0o022:raise ValueError('bootstrap_ancestor')
    fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        s=os.fstat(fd)
        if not stat.S_ISREG(s.st_mode) or s.st_uid!=os.getuid() or s.st_nlink!=1 or stat.S_IMODE(s.st_mode)!=0o600 or not 0<s.st_size<=limit:raise ValueError('bootstrap_file')
        raw=os.read(fd,limit+1);after=os.fstat(fd)
        if len(raw)!=s.st_size or any(getattr(s,k)!=getattr(after,k) for k in ('st_dev','st_ino','st_size','st_mtime_ns','st_ctime_ns','st_mode')) or not os.path.samestat(after,p.lstat()):raise ValueError('bootstrap_changed')
        return raw
    finally:os.close(fd)


def main():
    if not sys.flags.isolated or not sys.dont_write_bytecode or len(sys.argv)<4:raise ValueError('bootstrap_entry')
    manifest_path=Path(sys.argv[1]);raw=read(manifest_path)
    if hashlib.sha256(raw).hexdigest()!=sys.argv[2]:raise ValueError('bootstrap_manifest')
    manifest=json.loads(raw);root=manifest_path.parent
    if manifest['kind']!='seedbox_runtime_v1' or not manifest['files']:raise ValueError('bootstrap_manifest')
    for name,expected in manifest['files'].items():
        if not isinstance(name,str) or name.startswith('/') or '..' in Path(name).parts:raise ValueError('bootstrap_name')
        if hashlib.sha256(read(root/name)).hexdigest()!=expected:raise ValueError('bootstrap_hash')
    if Path(__file__).resolve()!=root/'automation/seedbox_bootstrap.py':raise ValueError('bootstrap_location')
    sys.path.insert(0,str(root));mode=sys.argv[3]
    if mode=='verify':
        for module in ('requests','bs4','automation.seedbox_worker','automation.seedbox_sender','automation.seedbox_evidence','automation.seedbox_automated_review','automation.seedbox_keychain_bridge'):
            __import__(module)
        print('seedbox_runtime_verified');return
    if mode=='bridge':
        sys.argv=['automation.seedbox_keychain_bridge',*sys.argv[4:]]
        runpy.run_module('automation.seedbox_keychain_bridge',run_name='__main__',alter_sys=True);return
    if mode=='provision':
        timer=threading.Timer(40,lambda:os._exit(124));timer.daemon=True;timer.start()
        try:
            sys.argv=['automation.seedbox_credential_provision',*sys.argv[4:]]
            runpy.run_module('automation.seedbox_credential_provision',run_name='__main__',alter_sys=True)
        finally:timer.cancel()
        return
    if mode=='recover' and len(sys.argv)==7:
        from automation.seedbox_assessment_queue import Queue
        from automation.seedbox_circuit import recover
        recover(Queue(sys.argv[4]),sys.argv[5],sys.argv[6]);return
    if mode not in ('enroll','run','probe') or len(sys.argv)!=6:raise ValueError('bootstrap_mode')
    config_raw=read(Path(sys.argv[4]),131072)
    if hashlib.sha256(config_raw).hexdigest()!=sys.argv[5]:raise ValueError('bootstrap_configuration')
    config=json.loads(config_raw)
    from ai_movie_investigator.private_files import private_chain
    from ai_movie_investigator.contracts import digest,require
    from automation.seedbox_credit_policy import validate
    if mode!='probe':validate(config['credit_policy'],now=__import__('time').time())
    with private_chain(Path(config['state'])):pass
    if mode=='enroll':
        from automation.seedbox_assessment_queue import Queue
        require(len(set(config['legacy_consumed_cases']))==7,'host_legacy_cutover')
        Queue.enroll(config['state'],collector_identity=config['collector_identity'],prior_consumed_cases=config['legacy_consumed_cases'],prior_history_sha256=config['credit_policy']['prior_history_sha256'],prior_credit_sha256=config['credit_policy']['prior_credit_sha256'],delegated_policy=config['credit_policy'],configuration_sha256=sys.argv[5],initial_cursor=config['initial_cursor'],configuration=config)
        return
    from automation.seedbox_confinement import confine
    from automation.seedbox_worker import run
    if mode=='probe':
        confine(config,root)
        from automation.seedbox_probe import probe
        probe(config);return
    from automation.seedbox_confinement import prevent_collector_creation
    from automation.seedbox_host_io import collector_lifetime
    from automation.seedbox_process import actor_lifetime
    with actor_lifetime(config['sender']['process']):
        prevent_collector_creation(config)
        with collector_lifetime(config['collector_database']):
            confine(config,root)
            run(config,sys.argv[5])

if __name__=='__main__':
    try:main()
    except SystemExit:raise
    except BaseException:
        print('seedbox_worker_stopped_safe',file=sys.stderr);raise SystemExit(1) from None
