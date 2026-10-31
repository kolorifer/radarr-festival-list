"""One fixed loopback export into a narrow incoming directory, after confinement.

No tracker credentials, Stage1 database, research ledger, or TMDb token access.
"""
import http.client
import json
import os
from pathlib import Path
import re
import resource
import socket
import stat
import time
from identity_triage_store import private_path, private_directory, create_private
from identity_research_provider import validate_case, clean, strict_json, IMDB, ident, request_deadline
from identity_triage_intake import REASONS

ROUTES={'eligible','retry_later','review_only','quarantine','unmatched','unassessed','verified','routine','reviewed_occurrence','existing_seed'}


def validate_snapshot(value,now):
    if not isinstance(value,dict) or set(value)!={'version','generated_at','coverage','cases','items'} or value['version']!=1:
        raise ValueError('snapshot_schema')
    if type(value['generated_at']) not in (int,float) or not now-3600<value['generated_at']<=now+300:raise ValueError('snapshot_stale')
    if not isinstance(value['cases'],list) or len(value['cases'])>1000:raise ValueError('snapshot_capacity')
    ids=set()
    for case in value['cases']:
        if set(case)!={'case_id','version','observed_at','first_observed_at','title','year','route','reason','correlation','original_type','source_identity'}:raise ValueError('snapshot_case')
        if not re.fullmatch('outcome-[a-f0-9]{64}',case['case_id']) or case['case_id'] in ids:raise ValueError('snapshot_case_id')
        ids.add(case['case_id'])
        if not re.fullmatch('[a-f0-9]{64}',case['version']) or case['route'] not in ROUTES or case['reason'] not in REASONS:raise ValueError('snapshot_case_status')
        identity=case['source_identity']
        if not isinstance(identity,dict) or set(identity)!={'imdb','tmdb','asserted_imdb','asserted_tmdb'}:raise ValueError('snapshot_identity')
        for key in ('imdb','asserted_imdb'):
            if identity[key] is not None and (not isinstance(identity[key],str) or not IMDB.fullmatch(identity[key])):raise ValueError('snapshot_imdb')
        for key in ('tmdb','asserted_tmdb'):
            if identity[key] is not None:ident(identity[key])
        clean(case['title'],256)
        if type(case['year'])!=int or not 1870<=case['year']<=2100:raise ValueError('snapshot_year')
        if type(case['first_observed_at']) not in (int,float) or not 0<case['first_observed_at']<=case['observed_at']:raise ValueError('snapshot_first_observed')
        if type(case['observed_at']) not in (int,float) or not 0<case['observed_at']<=now+300:raise ValueError('snapshot_observed')
        if case['correlation'] not in {'strong_source_id','uncertain_name_only','outcome_only','context_conflict','simultaneous_conflict','identifier_conflict'} or case['original_type'] not in {'movie','episode'}:raise ValueError('snapshot_provenance')
    if not isinstance(value['items'],list) or len(value['items'])>100:raise ValueError('snapshot_items')
    items=[validate_case(item) for item in value['items']]
    eligible={x['case_id']:x['version'] for x in value['cases'] if x['route']=='eligible'}
    if len(items)!=len(eligible) or {x['case_id']:x['provenance'][0]['digest'] for x in items}!=eligible:raise ValueError('snapshot_incomplete')
    # Only allow the collector's fixed aggregate shape; no arbitrary text crosses.
    coverage=value['coverage']
    allowed={'source_releases_observed','source_releases_without_outcome','outcome_events','assessed_release_cases','routes','correlation','existing_unresolved_seeds','legacy_outcome_rows_without_chronology','counters','researching','automatic_research_enabled','coverage'}
    if not isinstance(coverage,dict) or set(coverage)!=allowed:raise ValueError('coverage_schema')
    for key in allowed-{'routes','correlation','counters','automatic_research_enabled','coverage'}:
        if type(coverage[key])!=int or coverage[key]<0:raise ValueError('coverage_count')
    for key in ('routes','correlation','counters'):
        if not isinstance(coverage[key],dict) or len(coverage[key])>50 or any(not re.fullmatch('[a-z_]{1,64}',k) or type(v)!=int or v<0 for k,v in coverage[key].items()):raise ValueError('coverage_counts')
    if coverage['coverage']!='incomplete' or coverage['automatic_research_enabled'] is not False or coverage['assessed_release_cases']!=len(value['cases']):raise ValueError('coverage_state')
    return value


def atomic_json(path,value):
    # All writes confined to private state. Refuse links and never truncate a target.
    private_directory(path.parent)
    tmp=path.with_name(path.name+'.new')
    try:private_path(tmp);tmp.unlink()
    except FileNotFoundError:pass
    create_private(tmp)
    with tmp.open('w') as f:
        json.dump(value,f,sort_keys=True,allow_nan=False);f.flush();os.fsync(f.fileno())
    os.replace(tmp,path)
    fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)


class LoopbackConnection(http.client.HTTPConnection):
    def connect(self):raise PermissionError('handoff_reconnect_denied')


def confine(connection,config,incoming):
    from identity_research_sandbox import deny_syscalls
    from identity_triage_sandbox import _kernel, _private_directory, restrict, deny_check
    import sys
    _kernel();home=Path.home().resolve()
    code=_private_directory(home/'.local/lib/movie-identity-handoff')
    cfg=_private_directory(home/'.config/movie-identity-handoff')
    state=_private_directory(home/'.local/state/movie-identity-research/incoming')
    if Path(__file__).resolve().parent!=code or config!=cfg/'config.json' or incoming!=state:raise ValueError('handoff_layout')
    if os.environ.get('LC_ALL')!='C.UTF-8' or set(os.environ)-{'HOME','PATH','PYTHONDONTWRITEBYTECODE','LC_ALL'}:raise ValueError('handoff_environment')
    if not stat.S_ISCHR(os.fstat(0).st_mode) or os.fstat(0).st_rdev!=os.makedev(1,3) or any(not (stat.S_ISFIFO(os.fstat(fd).st_mode) or stat.S_ISSOCK(os.fstat(fd).st_mode)) for fd in (1,2)):raise ValueError('handoff_stdio')
    if not isinstance(connection,LoopbackConnection) or connection.host!='127.0.0.1' or connection.sock.getpeername()!=('127.0.0.1',connection.port):raise ValueError('handoff_socket')
    fd=connection.sock.fileno();limit=resource.getrlimit(resource.RLIMIT_NOFILE)[0]
    if not 4<=limit<=2**31-1:raise ValueError('handoff_fd_limit')
    os.closerange(3,fd);os.closerange(fd+1,limit)
    abi=restrict([code,cfg,Path('/usr/lib/python%d.%d'%sys.version_info[:2]),Path('/usr/lib/x86_64-linux-gnu')],state)
    deny_syscalls()
    for relative in ('.config/movie-intel','.apps','.ssh','radarr-festival-list','.local/state/movie-identity-triage',
                     '.config/movie-identity-research/config.json','.local/state/movie-identity-research/research.sqlite3'):
        deny_check(lambda relative=relative:os.open(home/relative,os.O_RDONLY))
    for path in ('/proc/self/environ','/proc/self/fd'):deny_check(lambda path=path:os.open(path,os.O_RDONLY))
    for family,kind in ((socket.AF_INET,socket.SOCK_STREAM),(socket.AF_INET6,socket.SOCK_STREAM),(socket.AF_INET,socket.SOCK_DGRAM),(socket.AF_UNIX,socket.SOCK_STREAM)):
        deny_check(lambda family=family,kind=kind:socket.socket(family,kind))
    deny_check(lambda:os.chmod(state,0o700))
    return abi


def main():
    os.umask(0o077);home=Path.home().resolve();connection=None
    config=home/'.config/movie-identity-handoff/config.json';incoming=home/'.local/state/movie-identity-research/incoming'
    stage='configuration'
    try:
        from identity_triage_observer import read_config
        cfg=read_config(config)
        connection=LoopbackConnection('127.0.0.1',cfg['port'],timeout=3)
        stage='connect'
        connection.sock=socket.create_connection(('127.0.0.1',cfg['port']),timeout=3)
        stage='confinement'
        abi=confine(connection,config,incoming)
        stage='export'
        with request_deadline():
            connection.request('GET','/v1/investigations',headers={'X-Identity-Intake-Key':cfg['key']})
            response=connection.getresponse()
            if response.status!=200:raise ValueError('handoff_status')
            raw=response.read(1_048_577)
        if len(raw)>1_048_576:raise ValueError('handoff_size')
        stage='validation'
        snapshot=validate_snapshot(strict_json(raw),time.time())
        stage='persistence'
        atomic_json(incoming/'snapshot.json',snapshot)
        print('handoff sandbox_verified abi='+str(abi)+' cases='+str(len(snapshot['cases']))+' eligible='+str(len(snapshot['items'])),flush=True)
        return 0
    except (ValueError,OSError,http.client.HTTPException) as exc:
        reason='timeout' if isinstance(exc,TimeoutError) else 'transport' if isinstance(exc,(OSError,http.client.HTTPException)) else 'validation'
        print('handoff stopped_safe stage='+stage+' reason='+reason,flush=True);return 1
    finally:
        if connection:connection.close()

if __name__=='__main__':raise SystemExit(main())
