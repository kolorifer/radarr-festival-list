"""Explicit public-code package builder, never installs services or private data."""
import ast,hashlib,json,os
from pathlib import Path
from ai_movie_investigator.contracts import require,encoded
from ai_movie_investigator.private_files import private_chain
from ai_movie_investigator.snapshot_authorization import _write_once
from ai_movie_investigator.installation import RUNTIME_FILES


def closure(source):
    source=Path(source);pending=set(RUNTIME_FILES)|{str(p.relative_to(source)) for p in (source/'automation').glob('seedbox_*.py')}|{'automation/reviewed_telegram_operator.py','automation/reviewed_telegram_UNISSUED.py'}
    found=set()
    while pending:
        name=pending.pop()
        if name in found:continue
        found.add(name)
        if not name.endswith('.py'):continue
        tree=ast.parse((source/name).read_bytes());package=Path(name).parent.parts
        for node in ast.walk(tree):
            modules=[]
            if isinstance(node,ast.Import):modules=[a.name for a in node.names]
            elif isinstance(node,ast.ImportFrom):
                prefix=list(package[:len(package)-node.level+1]) if node.level else []
                if node.module:prefix+=node.module.split('.')
                modules=['.'.join(prefix)]+['.'.join(prefix+[a.name]) for a in node.names if a.name!='*']
            for module in modules:
                if not module:continue
                path=Path(*module.split('.'))
                for candidate in (path.with_suffix('.py'),path/'__init__.py'):
                    if (source/candidate).is_file():pending.add(str(candidate))
        # Include package initializers for a closed import path.
        for parent in Path(name).parents:
            candidate=parent/'__init__.py'
            if (source/candidate).is_file():pending.add(str(candidate))
    return sorted(found)


def build(source,destination):
    source=Path(source).resolve();dest=Path(destination).resolve();files=closure(source);pins={}
    with private_chain(dest) as root:
        require(not os.listdir(root),'host_package_not_empty')
        for name in files:
            raw=(source/name).read_bytes();require(len(raw)<=1048576,'host_package_size')
            parent=dest/Path(name).parent
            parent.mkdir(parents=True,exist_ok=True,mode=0o700)
            with private_chain(parent) as fd:_write_once(fd,Path(name).name,raw)
            pins[name]=hashlib.sha256(raw).hexdigest()
        manifest=encoded(dict(kind='seedbox_runtime_v1',files=pins))
        _write_once(root,'seedbox-runtime.json',manifest)
    return dict(files=len(files),manifest_sha256=hashlib.sha256(manifest).hexdigest())
