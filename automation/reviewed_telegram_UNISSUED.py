"""UNISSUED one-shot original-card edit; exact main acceptance is mandatory.

No actor startup, environment mutation, provider call or credential CLI argument.
Main selects existing files and supplies private pins only after independent review.
"""
from contextlib import ExitStack,contextmanager
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import stat
import sys
import types
from urllib.request import Request,urlopen
from urllib.error import HTTPError

ISSUED = None
MODULES=('identity_triage_store','identity_triage_intake','identity_outcome_outbox',
         'identity_triage_observer','retry_telegram','torrent_research_evidence')


def read_file(path,limit,private=True):
    p=Path(path)
    if not p.is_absolute() or p.resolve(strict=True)!=p:raise ValueError('selected_path')
    for parent in p.parents:
        s=parent.lstat()
        if not stat.S_ISDIR(s.st_mode) or s.st_uid not in (0,os.getuid()) or s.st_mode&0o022:
            raise ValueError('selected_ancestor')
    fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        before=os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or before.st_uid not in ((os.getuid(),) if private else (0,os.getuid()))
            or before.st_mode&0o022 or private and stat.S_IMODE(before.st_mode)!=0o600 or not 0<before.st_size<=limit):raise ValueError('selected_file')
        body=bytearray()
        while len(body)<before.st_size:
            part=os.read(fd,min(65536,before.st_size-len(body)))
            if not part:raise ValueError('selected_file_changed')
            body.extend(part)
        after=os.fstat(fd);fields=('st_dev','st_ino','st_size','st_mode','st_uid','st_gid','st_nlink','st_mtime_ns','st_ctime_ns')
        if any(getattr(before,k)!=getattr(after,k) for k in fields) or not os.path.samestat(after,p.lstat()):raise ValueError('selected_file_changed')
        return bytes(body)
    finally:os.close(fd)


def pinned(pin,limit=131072,private=True,reader=None):
    if set(pin)!={'path','sha256'}:raise ValueError('selected_pin')
    raw=reader(Path(pin['path']),limit) if reader else read_file(pin['path'],limit,private)
    if hashlib.sha256(raw).hexdigest()!=pin['sha256']:raise ValueError('selected_pin_changed')
    return raw


def bootstrap_guard(pins):
    # Public guard bytes are hash-verified before execution. Reuse the existing
    # accepted private-file ACL and descriptor-relative chain checks unchanged.
    if set(pins)!={'contracts','history','private_files'}:raise ValueError('guard_closure')
    frozen={name:ast.parse(pinned(pin,1048576)) for name,pin in pins.items()}
    nodes=[]
    for name,selected in (('contracts',{'Refusal','require'}),('history',{'checked'})):
        nodes.extend(n for n in frozen[name].body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in selected)
    nodes.extend(n for n in frozen['private_files'].body if not(isinstance(n,ast.ImportFrom) and n.level))
    namespace={'os':os,'stat':stat}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'verified-private-guard','exec'),namespace)
    return namespace


def selected_functions(raw,names,namespace):
    tree=ast.parse(raw);nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
    if {n.name for n in nodes}!=set(names):raise ValueError('selected_functions')
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'verified-existing-functions','exec'),namespace)


def sender(actor_raw,environment_raw):
    # Reuse the deployed literal-value parser on a frozen guarded snapshot.
    class Snapshot:
        def stat(self):return types.SimpleNamespace(st_mode=0o600)
        def read_text(self):return environment_raw.decode('utf-8')
    ns={'re':re,'shlex':shlex}
    selected_functions(actor_raw['deploy/run.py'],{'read_environment'},ns)
    values=ns['read_environment'](Snapshot())
    token=values.get('TELEGRAM_BOT_TOKEN');chat=values.get('TELEGRAM_CHAT_ID');values.clear()
    if not token or not chat:raise ValueError('selected_bot_configuration')
    def forbidden(*_):raise ValueError('reviewed_actions_disabled')
    api=dict(json=json,Request=Request,urlopen=urlopen,HTTPError=HTTPError,
        TELEGRAM_BOT_TOKEN=token,TELEGRAM_CHAT_ID=chat,get_action=forbidden,
        public_action_url=forbidden,_reply_markup=forbidden)
    selected_functions(actor_raw['movie_intel_service.py'],{'_telegram_request','edit_retry_message'},api)
    return api['edit_retry_message']


def main():
    if ISSUED is None:raise SystemExit('reviewed_telegram_unissued')
    if sys.argv[1:]!=['--main-accepted-reviewed-telegram'] or not(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode):
        raise ValueError('isolated_main_acceptance_required')
    p=ISSUED;os.umask(0o077)
    if set(p)!={'python_sha256','main_acceptance_path','actor_root','actor_files','helper','plan','target','sources','boundary','state','output','bot_configuration','guard_files'}:raise ValueError('issued_schema')
    if hashlib.sha256(read_file(Path(sys.executable),104857600,False)).hexdigest()!=p['python_sha256']:raise ValueError('selected_python_changed')
    guard=bootstrap_guard(p['guard_files'])
    with ExitStack() as chains:
        directories={Path(p['actor_root']),Path(__file__).parent,Path(p['main_acceptance_path']).parent,
            Path(p['state']),Path(p['output']).parent}
        for key in ('helper','plan','target','sources','boundary','bot_configuration'):
            directories.add(Path(p[key]['path']).parent)
        for pin in p['guard_files'].values():directories.add(Path(pin['path']).parent)
        for directory in sorted(directories):chains.enter_context(guard['private_chain'](directory))
        acceptance=json.loads(guard['read_private'](Path(p['main_acceptance_path']),131072))
        if acceptance!={'decision':'accepted_exact_reviewed_telegram_edit','wrapper_sha256':hashlib.sha256(guard['read_private'](Path(__file__),65536)).hexdigest(),'issued_pins':p}:
            raise ValueError('main_acceptance_changed')
        required={name+'.py' for name in MODULES}|{'movie_intel_service.py','deploy/run.py'}
        if set(p['actor_files'])!=required:raise ValueError('actor_closure_changed')
        actor=Path(p['actor_root']);frozen={}
        for relative,sha in p['actor_files'].items():
            frozen[relative]=pinned(dict(path=str(actor/relative),sha256=sha),1048576,reader=guard['read_private'])
        for name in MODULES:
            if name in sys.modules:raise ValueError('actor_module_preloaded')
            module=types.ModuleType(name);module.__file__=str(actor/(name+'.py'));sys.modules[name]=module
            exec(compile(frozen[name+'.py'],module.__file__,'exec'),module.__dict__)
        helper=types.ModuleType('selected_reviewed_telegram_helper')
        exec(compile(pinned(p['helper'],1048576,reader=guard['read_private']),p['helper']['path'],'exec'),helper.__dict__)
        plan=json.loads(pinned(p['plan'],reader=guard['read_private']));target=json.loads(pinned(p['target'],reader=guard['read_private']));sources=json.loads(pinned(p['sources'],reader=guard['read_private']));boundary=json.loads(pinned(p['boundary'],reader=guard['read_private']))
        # Bind an existing store without its initializer, migrations or admission.
        from identity_outcome_outbox import Outbox
        from identity_triage_store import private_path
        store=Outbox.__new__(Outbox);store.directory=Path(p['state']);store.path=store.directory/'outcomes.sqlite3'
        private_path(store.directory,True);private_path(store.path)
        db_identity=guard['identity'](store.path.lstat())
        @contextmanager
        def checked_transaction():
            with guard['private_chain'](store.directory) as parent_fd:
                dbfd=os.open(store.path.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent_fd)
                try:
                    acl=guard['safe_acl'](dbfd,False)
                    def check_db():
                        info=os.fstat(dbfd);guard['checked'](info)
                        if (guard['identity'](info)!=db_identity or guard['safe_acl'](dbfd,False)!=acl or
                            guard['identity'](os.stat(store.path.name,dir_fd=parent_fd,follow_symlinks=False))!=db_identity):
                            raise ValueError('selected_database_changed')
                    check_db()
                    with Outbox.tx(store) as connection:
                        check_db();yield connection;check_db()
                    check_db()
                finally:os.close(dbfd)
        store.tx=checked_transaction
        # Mutable SQLite bytes are not copied or hashed; the existing transaction
        # and exact selected row pins govern them. Check its ancestor permissions.
        if store.path.resolve(strict=True)!=store.path:raise ValueError('selected_path')
        for parent in store.path.parents:
            info=parent.lstat()
            if not stat.S_ISDIR(info.st_mode) or info.st_uid not in (0,os.getuid()) or info.st_mode&0o022:raise ValueError('selected_ancestor')
        output=Path(p['output']);private_path(output.parent,True)
        if not output.is_absolute() or output.parent.resolve(strict=True)!=output.parent:raise ValueError('selected_path')
        for parent in [output.parent,*output.parent.parents]:
            info=parent.lstat()
            if not stat.S_ISDIR(info.st_mode) or info.st_uid not in (0,os.getuid()) or info.st_mode&0o022:raise ValueError('selected_ancestor')
        dfd=os.open(output.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:
            parent_identity=os.fstat(dfd)
            if os.path.lexists(output):raise ValueError('delivery_output_exists')
            # Exact bot values stay inside function globals; never os.environ/argv/output.
            edit=sender(frozen,pinned(p['bot_configuration'],65536,reader=guard['read_private']))
            result=helper.deliver(store,plan,target,sources,boundary,edit,private_guard=guard)
            raw=json.dumps(result,sort_keys=True,separators=(',',':')).encode()
            if not os.path.samestat(parent_identity,output.parent.lstat()):raise ValueError('delivery_output_changed')
            fd=os.open(output.name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=dfd)
            try:
                with os.fdopen(fd,'wb',closefd=False) as f:f.write(raw);f.flush();os.fsync(f.fileno())
            finally:os.close(fd)
            os.fsync(dfd)
        finally:os.close(dfd)
    print(json.dumps({'status':result['status'],'receipt_file_sha256':hashlib.sha256(raw).hexdigest()},sort_keys=True))


if __name__=='__main__':
    try:main()
    except SystemExit:raise
    except BaseException:
        # Never stringify exceptions: urllib errors can contain the bot URL.
        print('reviewed_telegram_stopped_safe',file=sys.stderr);raise SystemExit(1) from None
