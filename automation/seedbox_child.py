"""Bounded captured child I/O. No secret-bearing output or shell execution."""
import os,selectors,signal,subprocess,time
from ai_movie_investigator.contracts import require


def captured(argv,data,*,seconds,output_limit,environment):
    require(type(data) is bytes and len(data)<=16384,'host_child_input')
    process=subprocess.Popen(argv,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
        env=environment,start_new_session=True,close_fds=True)
    deadline=time.monotonic()+seconds;out=bytearray();err=0;offset=0
    try:
        with selectors.DefaultSelector() as selector:
            for stream in (process.stdin,process.stdout,process.stderr):os.set_blocking(stream.fileno(),False)
            selector.register(process.stdin,selectors.EVENT_WRITE,'input')
            selector.register(process.stdout,selectors.EVENT_READ,'output');selector.register(process.stderr,selectors.EVENT_READ,'error')
            while selector.get_map():
                remaining=deadline-time.monotonic();require(remaining>0,'host_child_deadline')
                for key,_ in selector.select(min(remaining,.1)):
                    if key.data=='input':
                        if offset<len(data):offset+=os.write(key.fd,data[offset:])
                        if offset==len(data):selector.unregister(key.fileobj);key.fileobj.close()
                    else:
                        chunk=os.read(key.fd,4096)
                        if not chunk:selector.unregister(key.fileobj);key.fileobj.close();continue
                        if key.data=='output':out.extend(chunk);require(len(out)<=output_limit,'host_child_output_bound')
                        else:err+=len(chunk);require(err<=4096,'host_child_error_bound')
            require(process.wait(timeout=max(.001,deadline-time.monotonic()))==0,'host_child_failed')
            return bytes(out)
    finally:
        if process.poll() is None:
            os.killpg(process.pid,signal.SIGKILL)
            try:process.wait(timeout=2)
            except subprocess.TimeoutExpired:pass
        for stream in (process.stdin,process.stdout,process.stderr):
            if not stream.closed:stream.close()
