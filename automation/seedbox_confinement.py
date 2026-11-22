"""Linux ABI6 selected-file confinement for the event worker.

Only selected source files, existing SQLite files, public runtime/CA libraries,
private worker state and actor SQLite subtree are accessible. HTTPS only; no TCP
listener. No write grant to producer code/config or collector source directory.
"""
import ctypes,os,stat,sys
from pathlib import Path
from ai_movie_investigator.contracts import require
from identity_triage_sandbox import _kernel,_call,Ruleset,Beneath,HANDLED_FS,READ,STATE

class Port(ctypes.Structure):
    _fields_=[('access',ctypes.c_uint64),('port',ctypes.c_uint64)]


def prevent_collector_creation(config):
    """Stack a narrow no-create layer before SQLite opens any source handle.

    Only regular-file creation is handled here; the existing complete confinement
    follows after validated WAL handles are retained. No collector creation grant.
    """
    from ai_movie_investigator.private_files import private_chain
    lib=_kernel();abi=_call(lib,444,ctypes.c_void_p(),ctypes.c_size_t(0),ctypes.c_uint(1));require(abi>=6,'host_sandbox_abi')
    require(lib.prctl(38,1,0,0,0)==0,'host_sandbox_privileges')
    create=1<<8;policy=Ruleset(create,0,0)
    rules=_call(lib,444,ctypes.byref(policy),ctypes.sizeof(policy),0)
    collector=Path(config['collector_database']['path']).parent.resolve(strict=True)
    try:
        for selected in (Path(config['state']),Path(config['actor_database']['path']).parent):
            require(selected!=collector and selected not in collector.parents,'host_collector_creation_scope')
            with private_chain(selected) as fd:
                rule=Beneath(create,fd);_call(lib,445,rules,1,ctypes.byref(rule),0)
        _call(lib,446,rules,0)
    finally:os.close(rules)


def confine(config,code_root,*,source_preflight=None):
    lib=_kernel();abi=_call(lib,444,ctypes.c_void_p(),ctypes.c_size_t(0),ctypes.c_uint(1));require(abi>=6,'host_sandbox_abi')
    require(lib.prctl(38,1,0,0,0)==0,'host_sandbox_privileges')
    policy=Ruleset(HANDLED_FS,3,3);rules=_call(lib,444,ctypes.byref(policy),ctypes.sizeof(policy),0)
    paths={str(code_root):READ,str(Path(sys.prefix).resolve()):READ,'/usr':READ,'/proc':1<<3,
        '/etc/ld.so.cache':READ,'/etc/passwd':READ,'/etc/group':READ,
        '/etc/ssl':READ,'/etc/resolv.conf':READ,'/etc/hosts':READ,'/etc/nsswitch.conf':READ,
        config['state']:STATE|(1<<7),
        **({str(Path(config['credential']['path']).parent):READ} if source_preflight is None else {}),
        config['source_configuration']['path']:READ,config['cookie_file']['path']:READ}
    # Credentials IPC is a filesystem Unix socket; no new abstract sockets may
    # escape this service. It does not grant the hidden master key as a file.
    if source_preflight is None:
        ipc=Path('/run/systemd/io.systemd.Credentials')
        require(ipc.exists(),'host_credential_ipc_missing')
    # ABI6 filesystem Unix-socket connect is not path-mediated. The fixed
    # reviewed executable uses this literal endpoint; abstract IPC is scoped.
    # No claim that Landlock itself authenticates the credential service.
    from automation.seedbox_process import retained
    process=config['sender']['process']
    if not retained(process):
        for name in ('cmdline','stat'):paths[str(Path('/proc')/str(process['pid'])/name)]=READ
    if source_preflight is None:
        paths['/usr/bin/systemd-creds']=READ|1
        loader=Path('/lib64/ld-linux-x86-64.so.2').resolve(strict=True)
        info=loader.stat();require(stat.S_ISREG(info.st_mode) and info.st_uid==0 and not info.st_mode&0o022,'host_system_loader')
        paths[str(loader)]=READ|1
    from automation.seedbox_sender import actor_directory_scope
    actor_directory_scope(config['actor_database'])
    collector=Path(config['collector_database']['path'])
    require(config['collector_database']['journal_mode']=='wal' and config['actor_database']['journal_mode']=='delete','host_journal_selection')
    paths[str(collector.parent)]=1<<3
    for path in (collector,collector.with_name(collector.name+'-wal'),collector.with_name(collector.name+'-shm')):
        require(path.exists(),'host_collector_sidecar_missing')
        paths[str(path)]=READ|((1<<1) if path.name.endswith('-shm') else 0)
    actor=Path(config['actor_database']['path'])
    # DELETE mode creates/removes a future rollback-journal filename. Landlock
    # cannot grant that filename before it exists: the truthful kernel grant is
    # this actor state subtree, including existing binding-spool descendants.
    # No directory creation/removal; trusted fixed SQL/sender code constrains
    # actual writes to the selected DB and SQLite's own journal lifecycle.
    paths[str(actor.parent)]=READ|(1<<1)|(1<<5)|(1<<8)|(1<<14)
    # Descriptor-relative guards open ancestor directories; directory-name
    # traversal is allowed, while file contents remain separately selected.
    paths['/']=1<<3
    spool=Path(config['actor_database']['path']).parent/'message-bindings'
    if spool.exists():paths[str(spool)]=READ
    # The inherited actor-subtree mutation grant also reaches this spool.
    for pin in config['sender']['deployed_files'].values():paths[pin['path']]=READ
    try:
        for path,rights in paths.items():
            if source_preflight is not None:
                source_preflight({
                    config['source_configuration']['path']: 'source_configuration_access',
                    config['cookie_file']['path']: 'cookie_access',
                }.get(path, 'confinement'))
                rights &= READ
            p=Path(path);resolved=p.resolve(strict=True)
            fd=os.open(resolved,os.O_PATH|os.O_CLOEXEC)
            try:
                if not stat.S_ISDIR(os.fstat(fd).st_mode):rights &= ~(1<<3)
                rule=Beneath(rights,fd);_call(lib,445,rules,1,ctypes.byref(rule),0)
            finally:os.close(fd)
        if source_preflight is None:
            port=Port(2,443);_call(lib,445,rules,2,ctypes.byref(port),0)
        else:
            source_preflight('confinement')
        _call(lib,446,rules,0)
    finally:os.close(rules)
    return abi
