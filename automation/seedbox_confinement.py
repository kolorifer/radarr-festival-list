"""Linux ABI6 selected-file confinement for the event worker.

Only selected source files, existing SQLite files, public runtime/CA libraries,
private worker state and user credential IPC are accessible. HTTPS only; no TCP
listener. No write grant to producer code/config or collector source directory.
"""
import ctypes,os,stat,sys
from pathlib import Path
from ai_movie_investigator.contracts import require
from identity_triage_sandbox import _kernel,_call,Ruleset,Beneath,HANDLED_FS,READ,STATE

class Port(ctypes.Structure):
    _fields_=[('access',ctypes.c_uint64),('port',ctypes.c_uint64)]


def confine(config,code_root):
    lib=_kernel();abi=_call(lib,444,ctypes.c_void_p(),ctypes.c_size_t(0),ctypes.c_uint(1));require(abi>=6,'host_sandbox_abi')
    require(lib.prctl(38,1,0,0,0)==0,'host_sandbox_privileges')
    policy=Ruleset(HANDLED_FS,3,3);rules=_call(lib,444,ctypes.byref(policy),ctypes.sizeof(policy),0)
    paths={str(code_root):READ,str(Path(sys.prefix).resolve()):READ,'/usr':READ,'/proc':1<<3,
        '/etc/ld.so.cache':READ,'/etc/passwd':READ,'/etc/group':READ,
        '/etc/ssl':READ,'/etc/resolv.conf':READ,'/etc/hosts':READ,'/etc/nsswitch.conf':READ,
        config['state']:STATE|(1<<7),str(Path(config['credential']['path']).parent):READ,
        config['source_configuration']['path']:READ,config['cookie_file']['path']:READ}
    # Credentials IPC is a filesystem Unix socket; no new abstract sockets may
    # escape this service. It does not grant the hidden master key as a file.
    ipc=Path('/run/systemd/io.systemd.Credentials')
    require(ipc.exists(),'host_credential_ipc_missing')
    # ABI6 filesystem Unix-socket connect is not path-mediated. The fixed
    # reviewed executable uses this literal endpoint; abstract IPC is scoped.
    # No claim that Landlock itself authenticates the credential service.
    pid=config['sender']['process']['pid']
    for name in ('cmdline','stat'):paths[str(Path('/proc')/str(pid)/name)]=READ
    paths['/usr/bin/systemd-creds']=READ|1
    for name,writable in (('collector_database',False),('actor_database',True)):
        db=Path(config[name]['path']);paths[str(db.parent)]=1<<3
        for path in (db,db.with_name(db.name+'-wal'),db.with_name(db.name+'-shm')):
            require(path.exists(),'host_database_sidecar_missing')
            paths[str(path)]=READ|((1<<1) if writable or path.name.endswith('-shm') else 0)
    # Descriptor-relative guards open ancestor directories; directory-name
    # traversal is allowed, while file contents remain separately selected.
    paths['/']=1<<3
    spool=Path(config['actor_database']['path']).parent/'message-bindings'
    if spool.exists():paths[str(spool)]=READ
    # The actor's original-message binding spool is read-only.
    for pin in config['sender']['deployed_files'].values():paths[pin['path']]=READ
    try:
        for path,rights in paths.items():
            p=Path(path);resolved=p.resolve(strict=True)
            fd=os.open(resolved,os.O_PATH|os.O_CLOEXEC)
            try:
                if not stat.S_ISDIR(os.fstat(fd).st_mode):rights &= ~(1<<3)
                rule=Beneath(rights,fd);_call(lib,445,rules,1,ctypes.byref(rule),0)
            finally:os.close(fd)
        port=Port(2,443);_call(lib,445,rules,2,ctypes.byref(port),0)
        _call(lib,446,rules,0)
    finally:os.close(rules)
    return abi
