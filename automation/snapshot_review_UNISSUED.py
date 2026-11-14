"""UNISSUED normalized snapshot assessment; reviewed main must issue exact pins.

Run only in an isolated one-shot Python -I -S -B process. No flag or environment
setting supplies authority. No actual case, credentials or result is included.
"""
import sys,os,stat,json,hashlib,ast
from contextlib import ExitStack
from pathlib import Path

ISSUED = None

def file_record(path,limit):
    path=Path(path)
    if not path.is_absolute() or path.resolve(strict=True)!=path:raise ValueError('private_path')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC)
    try:
        before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_uid!=os.getuid() or stat.S_IMODE(before.st_mode)!=0o600 or before.st_nlink!=1 or not 0<before.st_size<=limit:raise ValueError('private_file')
        raw=os.read(fd,limit+1);after=os.fstat(fd)
        fields=('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
        if len(raw)!=before.st_size or any(getattr(before,k)!=getattr(after,k)for k in fields):raise ValueError('private_file_changed')
        if not os.path.samestat(after,os.stat(path,follow_symlinks=False)):raise ValueError('private_file_replaced')
        return raw
    finally:os.close(fd)


def executable_record(path,limit):
    path=Path(path)
    if not path.is_absolute() or path.resolve(strict=True)!=path:raise ValueError('executable_path')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC)
    try:
        before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_uid not in (0,os.getuid()) or before.st_mode&0o022 or not before.st_mode&0o100 or not 0<before.st_size<=limit:raise ValueError('executable_file')
        h=hashlib.sha256();remaining=before.st_size
        while remaining:
            part=os.read(fd,min(1048576,remaining))
            if not part:raise ValueError('executable_changed')
            h.update(part);remaining-=len(part)
        after=os.fstat(fd)
        fields=('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
        if any(getattr(before,k)!=getattr(after,k) for k in fields) or not os.path.samestat(after,os.stat(path,follow_symlinks=False)):raise ValueError('executable_changed')
        return h.hexdigest()
    finally:os.close(fd)


def bootstrap_guard(runtime,pins):
    # Execute ONLY frozen bytes whose hashes are literal in the accepted wrapper.
    # Reuse the accepted private_files guard verbatim, not runtime imports from
    # an unchecked directory. Its two tiny dependencies are exact AST nodes
    # from the same pinned contracts/history source; all I/O rules are unchanged.
    frozen={}
    for name in ('contracts','history','private_files'):
        relative='ai_movie_investigator/'+name+'.py'
        raw=file_record(runtime/relative,1048576)
        if hashlib.sha256(raw).hexdigest()!=pins[relative]:raise ValueError('bootstrap_changed')
        frozen[name]=ast.parse(raw)
    nodes=[]
    for name,selected in (('contracts',{'Refusal','require'}),('history',{'checked'})):
        nodes.extend(n for n in frozen[name].body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in selected)
    nodes.extend(n for n in frozen['private_files'].body if not(isinstance(n,ast.ImportFrom)and n.level))
    namespace={'os':os,'stat':stat}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'pinned-private-guard','exec'),namespace)
    return namespace



def verify_closure(runtime,pins,read_private):
    relative='ai_movie_investigator/installation.py'
    raw=read_private(runtime/relative,1048576)
    if hashlib.sha256(raw).hexdigest()!=pins[relative]:raise ValueError('installation_changed')
    tree=ast.parse(raw);assignments=[n.value for n in tree.body if isinstance(n,ast.Assign) and
        len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='RUNTIME_FILES']
    if len(assignments)!=1:raise ValueError('runtime_closure_changed')
    files=ast.literal_eval(assignments[0])
    if not isinstance(files,tuple) or len(files)!=len(set(files)) or set(files)!=set(pins):raise ValueError('runtime_closure_changed')
    frozen=json.loads(read_private(runtime/'runtime-files.json',131072))
    if frozen!=pins:raise ValueError('runtime_manifest_changed')
    for name,expected in pins.items():
        if hashlib.sha256(read_private(runtime/name,1048576)).hexdigest()!=expected:raise ValueError('runtime_changed')


def main():
    if ISSUED is None:raise SystemExit('snapshot_authority_unissued')
    if sys.argv[1:]!=['--main-accepted-snapshot-review']:raise SystemExit('main_acceptance_required')
    if not (sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode):raise ValueError('isolated_python_required')
    os.umask(0o077);p=ISSUED
    if executable_record(Path(sys.executable),104857600)!=p['python_sha256']:raise ValueError('python_changed')
    runtime=Path(p['runtime']);guard=bootstrap_guard(runtime,p['runtime_files'])
    with ExitStack() as chains:
        paths=(runtime,Path(__file__).parent,Path(p['main_acceptance_path']).parent,Path(p['authority']['path']).parent,
               Path(p['account_evidence']['path']).parent,Path(p['state']),Path(p['output_dir']))
        for path in paths:chains.enter_context(guard['private_chain'](path))
        def pin(record,limit):
            if set(record)!={'path','sha256'}:raise ValueError('exact_pin_schema')
            data=guard['read_private'](Path(record['path']),limit)
            if hashlib.sha256(data).hexdigest()!=record['sha256']:raise ValueError('exact_pin_changed')
            return data
        acceptance=json.loads(guard['read_private'](Path(p['main_acceptance_path']),131072))
        if acceptance.get('decision')!='accepted_exact_normalized_snapshot_assessment' or acceptance.get('wrapper_sha256')!=hashlib.sha256(guard['read_private'](Path(__file__),65536)).hexdigest() or acceptance.get('issued_pins')!=p:raise ValueError('main_acceptance_changed')
        authority=json.loads(pin(p['authority'],65536));pin(p['account_evidence'],16384)
        if authority.get('root_prefix_sha256')!=p['root_prefix_sha256'] or authority.get('output_dir')!=p['output_dir']:raise ValueError('authority_scope_changed')
        verify_closure(runtime,p['runtime_files'],guard['read_private'])
        sys.path.insert(0,str(runtime))
        from ai_movie_investigator import snapshot_authorization as gate,supervised_credit as c
        from ai_movie_investigator.installation import verify_installation
        from ai_movie_investigator.history import History
        from ai_movie_investigator.contracts import digest
        if verify_installation(runtime)!=p['runtime_files']:raise ValueError('runtime_manifest_changed')
        selected=c.read_evidence(Path(p['account_evidence']['path']))
        if selected.sha256!=p['account_evidence']['sha256']:raise ValueError('account_evidence_changed')
        root=History(Path(p['state']))
        with root.transaction(write=True) as (events,_):
            if digest(events)!=p['root_prefix_sha256']:raise ValueError('root_prefix_changed')
            if 7+len(c._standing_attempts(events,events[1]))!=p['expected_slot']:raise ValueError('expected_slot_changed')
        with gate.approved_snapshot_wrapper(p['authority']['path'],p['authority']['sha256']):
            result=gate.execute(p['state'],selected,p['output_dir'])
            if result.get('slot')!=p['expected_slot']:raise ValueError('expected_slot_changed')
    print(json.dumps(result,sort_keys=True))

if __name__=='__main__':main()
