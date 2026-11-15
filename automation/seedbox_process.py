"""Live metadata for one selected actor across Landlock process visibility limits.

Only fixed read-only metadata handles and a nonsignalling pidfd are retained.
No memory, environment, process enumeration or cached observation is authority.
"""
from contextlib import contextmanager
from contextvars import ContextVar
import hashlib,os,select,stat
from pathlib import Path
from ai_movie_investigator.contracts import require

_HELD=ContextVar('seedbox_selected_actor_handles',default=None)


def _validate(pin,raw,command):
    require(type(pin['pid']) is int and pin['pid']>1,'host_actor_process')
    require(0<len(raw)<=8192 and 0<len(command)<=8192,'host_actor_process')
    fields=raw.rsplit(b') ',1)[1].split()
    require(raw.split(b'(',1)[0].strip()==str(pin['pid']).encode() and len(fields)>19 and fields[0] not in (b'Z',b'X',b'x'),'host_actor_process_changed')
    start=int(fields[19])
    require(start==pin['start_ticks'] and hashlib.sha256(command).hexdigest()==pin['cmdline_sha256'],'host_actor_process_changed')
    return dict(pid=pin['pid'],start_ticks=start,cmdline_sha256=pin['cmdline_sha256'])


def _owner(pin,status):
    require(0<len(status)<=65536,'host_actor_status')
    def fields(name,count):
        rows=[line.split() for line in status.splitlines() if line.startswith(name+b':')]
        require(len(rows)==1 and len(rows[0])==count+1 and all(v.isdigit() and len(v)<=10 for v in rows[0][1:]),'host_actor_status')
        return [int(v) for v in rows[0][1:]]
    require(fields(b'Uid',4)==[os.getuid()]*4,'host_actor_owner')
    require(fields(b'Pid',1)==[pin['pid']] and fields(b'Tgid',1)==[pin['pid']],'host_actor_process_changed')


def _read(held,pin):
    require(pin==held['pin'],'host_actor_selection_changed')
    require(not select.select([held['pidfd']],[],[],0)[0],'host_actor_exited')
    _owner(pin,os.pread(held['status'],65537,0))
    values=[]
    for name in ('stat','cmdline'):
        fd=held[name]
        # Offset zero re-reads current kernel metadata, never a cached snapshot.
        values.append(os.pread(fd,8193,0))
    result=_validate(pin,*values)
    _owner(pin,os.pread(held['status'],65537,0))
    require(not select.select([held['pidfd']],[],[],0)[0],'host_actor_exited')
    return result


@contextmanager
def actor_lifetime(pin):
    require(_HELD.get() is None and type(pin['pid']) is int and pin['pid']>1,'host_actor_process')
    require(hasattr(os,'pidfd_open'),'host_actor_pidfd_required')
    opened=[];token=None
    try:
        directory=os.open('/proc/'+str(pin['pid']),os.O_PATH|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC);opened.append(directory)
        require(os.fstat(directory).st_uid==os.getuid(),'host_actor_owner')
        held=dict(pin=dict(pin))
        for name in ('stat','cmdline','status'):
            fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=directory);opened.append(fd);held[name]=fd
            info=os.fstat(fd);require(stat.S_ISREG(info.st_mode) and info.st_uid==os.getuid(),'host_actor_owner')
        held['pidfd']=os.pidfd_open(pin['pid'],0);opened.append(held['pidfd']);os.set_inheritable(held['pidfd'],False)
        os.close(directory);opened.remove(directory)
        _read(held,pin);token=_HELD.set(held)
        yield
    finally:
        if token is not None:_HELD.reset(token)
        for fd in reversed(opened):os.close(fd)


def retained(pin):
    held=_HELD.get()
    if held is None:return False
    _read(held,pin);return True


def observe(pin):
    held=_HELD.get()
    if held is not None:return _read(held,pin)
    pid=pin['pid'];require(type(pid) is int and pid>1,'host_actor_process')
    proc=Path('/proc')/str(pid);require(proc.stat().st_uid==os.getuid(),'host_actor_owner')
    return _validate(pin,(proc/'stat').read_bytes(),(proc/'cmdline').read_bytes())
