"""Durable host intake foundation. No provider, credential, review or send authority.

The caller authenticates the collector connection and pins its database identity.
An event is discovery, never source evidence. Consumed cases are imported once by
main; a provider reservation, including an interrupted one, consumes a case.
Pre-send evidence-preparation claims remain explicitly resumable.
"""
from pathlib import Path
from ai_movie_investigator.contracts import decode, digest, encoded, require, shape, hash_id, stamp
from ai_movie_investigator.history import History, FILENAME
from ai_movie_investigator.private_files import private_chain, read_private
from ai_movie_investigator.snapshot_authorization import _write_once


def collector_page(connection, after, *, limit=100):
    """Read committed event history, not only the latest projection; no DB writes.

    SQLite rowids are stable here only while the pinned collector DB and its
    append-only selection_events are retained. Deployment must bind that identity.
    """
    import json
    require(type(after) is int and after>=0 and type(limit) is int and 1<=limit<=100,'queue_cursor')
    own_transaction=not connection.in_transaction
    if own_transaction:connection.execute('BEGIN')
    try:
        return _collector_page_locked(connection,after,limit)
    finally:
        if own_transaction:connection.rollback()


def _collector_page_locked(connection,after,limit):
    import json
    high=connection.execute('select coalesce(max(rowid),0) from selection_events').fetchone()[0]
    require(after<=high,'queue_collector_rollback')
    rows=connection.execute('select s.rowid,s.id,s.release,s.observed,s.received,s.outcome,e.metadata from selection_events s left join evidence e on e.id=s.evidence where s.rowid>? order by s.rowid limit ?', (after,limit)).fetchall()
    require(all(r[6] is not None for r in rows),'queue_missing_evidence')
    events=[]
    for r in rows:
        event=dict(cursor=r[0],event_id=r[1],case_id='outcome-'+r[2],observed_at=r[3],received_at=r[4],outcome=json.loads(r[5]),metadata=json.loads(r[6]))
        require(len(encoded(event))<=16384,'queue_event_size')
        if len(encoded(events+[event]))>65536:break
        events.append(event)
    return dict(kind='collector_assessment_events_v1',after=after,through=events[-1]['cursor'] if events else after,high_water=high,events=events)


class Queue:
    @staticmethod
    def enroll(directory, *, collector_identity, prior_consumed_cases, prior_history_sha256, prior_credit_sha256, delegated_policy, capacity=1000, configuration_sha256=None, initial_cursor=0, configuration=None):
        """Explicit cutover only; imports exclusions, not permission to spend.

        Main must freeze prior writers and verify the complete legacy histories,
        including uncertain attempts. Merely supplying hashes does not prove this.
        """
        path=Path(directory);hash_id(collector_identity);hash_id(prior_history_sha256);hash_id(prior_credit_sha256)
        require(type(capacity) is int and 1<=capacity<=1000,'queue_capacity')
        if configuration_sha256 is not None:hash_id(configuration_sha256)
        require(type(initial_cursor) is int and initial_cursor>=0,'queue_cursor')
        cases=sorted(set(prior_consumed_cases))
        for case in cases:_case(case)
        with private_chain(path) as fd:
            import os
            require(not os.listdir(fd),'queue_enrollment_not_empty')
            history=History(path)
            with history.transaction(write=True) as (_,append):
                append(dict(type='seedbox_queue_enrolled_v1',collector_identity=collector_identity,prior_consumed_cases=cases,
                    prior_history_sha256=prior_history_sha256,prior_credit_sha256=prior_credit_sha256,policy_sha256=digest(delegated_policy),capacity=capacity,configuration_sha256=configuration_sha256,initial_cursor=initial_cursor))
            os.mkdir('anchor',mode=0o700,dir_fd=fd)
            anchor=History(path/'anchor')
            with anchor.transaction(write=True) as (_,save):
                records=history.read();save(dict(type='seedbox_queue_high_water_v1',count=len(records),sha256=digest(records)))
            st=(path/FILENAME).lstat();ast=(path/'anchor'/FILENAME).lstat()
            binding=dict(kind='seedbox_queue_storage_v1',directory_identity=list(history.identity),history_identity=[st.st_dev,st.st_ino],anchor_identity=list(anchor.identity),anchor_file=[ast.st_dev,ast.st_ino])
            _write_once(fd,'queue-binding.json',encoded(binding))
            _write_once(fd,'runner.lock',b'seedbox-singleton-v1\n')
            if configuration is not None:
                require(digest(configuration)==configuration_sha256,'queue_configuration_changed')
                _write_once(fd,'configuration.json',encoded(configuration))
        return binding

    def __init__(self,directory):
        self.path=Path(directory);self.history=History(self.path)
        self.raw=read_private(self.path/'queue-binding.json');self.binding=decode(self.raw)
        shape(self.binding,'kind directory_identity history_identity anchor_identity anchor_file')
        self.anchor=History(self.path/'anchor')
        require(list(self.anchor.identity)==self.binding['anchor_identity'],'queue_storage_changed')
        require(self.binding['kind']=='seedbox_queue_storage_v1' and self.binding['directory_identity']==list(self.history.identity),'queue_storage_changed')

    def locked(self):
        from contextlib import contextmanager
        @contextmanager
        def transaction():
            with private_chain(self.path),private_chain(self.anchor.directory):
                with self.anchor.transaction(write=True,file_identity=self.binding['anchor_file']) as (marks,save):
                    with self.history.transaction(write=True,file_identity=self.binding['history_identity']) as (rows,append):
                        require(read_private(self.path/'queue-binding.json')==self.raw,'queue_storage_changed')
                        require(rows and rows[0]['type']=='seedbox_queue_enrolled_v1','queue_not_enrolled')
                        require(len(marks)==len(rows) and marks[-1]==dict(type='seedbox_queue_high_water_v1',count=len(rows),sha256=digest(rows)),'queue_journal_uncertain')
                        def durable(event):
                            append(event)
                            save(dict(type='seedbox_queue_high_water_v1',count=len(rows),sha256=digest(rows)))
                        yield rows,durable
        return transaction()

    def ingest(self,page,*,collector_identity):
        shape(page,'kind after through high_water events')
        require(page['kind']=='collector_assessment_events_v1' and type(page['events']) is list and len(page['events'])<=100,'queue_page')
        for key in ('after','through','high_water'):require(type(page[key]) is int and page[key]>=0,'queue_cursor')
        require(page['after']<=page['through']<=page['high_water'],'queue_cursor')
        with self.locked() as (rows,append):
            require(collector_identity==rows[0]['collector_identity'],'queue_collector_changed')
            pages=[r for r in rows if r['type']=='seedbox_queue_page_v1'];cursor=pages[-1]['page']['through'] if pages else rows[0]['initial_cursor']
            if page['after']!=cursor:
                require(any(r['page']==page for r in pages),'queue_cursor_changed')
                return 'duplicate_page'
            require(not pages or page['high_water']>=pages[-1]['page']['high_water'],'queue_collector_rollback')
            previous=cursor
            for event in page['events']:
                shape(event,'cursor event_id case_id observed_at received_at outcome metadata')
                require(type(event['cursor']) is int and event['cursor']>previous,'queue_event_order');previous=event['cursor']
                hash_id(event['event_id']);_case(event['case_id']);stamp(event['observed_at']);stamp(event['received_at'])
                require(type(event['outcome']) is dict and type(event['metadata']) is dict,'queue_event')
                require(len(encoded(event))<=16384,'queue_event_size')
            require(previous==page['through'],'queue_cursor_gap')
            if not page['events']:return 'quiet'
            pending=_pending(rows)
            all_events=pending+page['events'];dispositions={}
            from identity_selection import route
            latest={}
            for event in all_events:
                key=event['case_id'];latest[key]=max(latest.get(key,0),event['observed_at'])
            for event in all_events:
                try:decision=route(event['outcome'])
                except (KeyError,TypeError):raise ValueError('queue_event_outcome') from None
                reason=None
                if decision in ('verified','routine'):reason='successful_or_routine'
                elif decision=='retry_later':reason='producer_retry_pending'
                elif decision=='quarantine':reason='operator_needed_invalid_evidence'
                elif event['observed_at']<latest[event['case_id']]:reason='superseded_observation'
                if reason:dispositions[event['event_id']]=reason
            relevant=[e for e in all_events if e['event_id'] not in dispositions]
            # Event page, retained dispositions and cursor are one durable record.
            started={r['preparation'] for r in rows if r['type'] in ('seedbox_provider_started_v1','seedbox_preparation_superseded_v1')}
            preparing=sum(r['type']=='seedbox_preparation_claimed_v1' and digest(r) not in started for r in rows)
            require(len(relevant)+preparing<=rows[0]['capacity'],'queue_backpressure')
            record=dict(type='seedbox_queue_page_v1',page=page,dispositions=dispositions)
            require(len(encoded(record))<=180000,'queue_page_size')
            append(record)
            return 'accepted'

    def reserve(self,snapshot_raw,*,now):
        # Authenticated current snapshot must be reacquired after discovery;
        # discovery alone never burns an outcome-first or weakly correlated case.
        import hashlib
        from ai_movie_investigator.snapshot_review import select
        from identity_research_handoff import validate_snapshot,validate_host_snapshot
        value=decode(snapshot_raw,1048576)
        snapshot=(validate_host_snapshot if value.get('kind')=='seedbox_selected_snapshot_v1' else validate_snapshot)(value,now)
        current={case['case_id']:case for case in snapshot['cases']}
        snapshot_sha=hashlib.sha256(snapshot_raw).hexdigest()
        with self.locked() as (rows,append):
            consumed=set(rows[0]['prior_consumed_cases'])|{r['case_id'] for r in rows if r['type']=='seedbox_provider_started_v1'}
            retired={r['preparation'] for r in rows if r['type']=='seedbox_preparation_superseded_v1'}
            preparing={r['case_id'] for r in rows if r['type']=='seedbox_preparation_claimed_v1' and digest(r) not in retired}
            # Preparation is not a provider attempt. Claims remain resumable until
            # a separate atomic provider/credit reservation burns the case.
            for event in _pending(rows):
                if event['case_id'] in preparing:continue
                reason='previously_consumed' if event['case_id'] in consumed else None
                if reason is None:
                    case=current.get(event['case_id'])
                    if case is None:continue
                    if case['observed_at']>event['observed_at'] or case['route'] in ('verified','routine','reviewed_occurrence','existing_seed'):
                        append(dict(type='seedbox_queue_disposition_v1',event_id=event['event_id'],reason='superseded_or_resolved',at=stamp(now)))
                        continue
                    if case['observed_at']!=event['observed_at'] or case['reason']!=event['outcome'].get('reason'):continue
                    try:select(snapshot_raw,snapshot_sha,case['case_id'],case['version'],now=now)
                    except ValueError:
                        if not any(r['type']=='seedbox_waiting_source_v1' and r['event_id']==event['event_id'] and r['version']==case['version'] for r in rows):
                            append(dict(type='seedbox_waiting_source_v1',event_id=event['event_id'],case_id=event['case_id'],version=case['version'],reason='strong_current_source_linkage_unavailable',recovery='reconsider_when_collector_correlation_changes',at=stamp(now)))
                        continue
                if reason:
                    append(dict(type='seedbox_queue_disposition_v1',event_id=event['event_id'],reason=reason,at=stamp(now)))
                    continue
                reservation=dict(type='seedbox_preparation_claimed_v1',event_id=event['event_id'],case_id=event['case_id'],event_sha256=digest(event),version=case['version'],snapshot_sha256=snapshot_sha,at=stamp(now))
                append(reservation)
                return dict(reservation=digest(reservation),event=event,status='needs_authenticated_evidence')
            return dict(status='waiting_for_eligible_source' if _pending(rows) else 'quiet')

    def refresh_preparations(self,snapshot_raw,*,now):
        from identity_research_handoff import validate_snapshot,validate_host_snapshot
        value=decode(snapshot_raw,1048576)
        current={r['case_id']:r for r in (validate_host_snapshot if value.get('kind')=='seedbox_selected_snapshot_v1' else validate_snapshot)(value,now)['cases']}
        with self.locked() as (rows,append):
            terminal={r['preparation'] for r in rows if r['type'] in ('seedbox_provider_started_v1','seedbox_preparation_superseded_v1')}
            for claim in list(rows):
                if claim['type']!='seedbox_preparation_claimed_v1' or digest(claim) in terminal:continue
                case=current.get(claim['case_id'])
                if case and case['version']!=claim['version']:
                    append(dict(type='seedbox_preparation_superseded_v1',preparation=digest(claim),new_version=case['version'],snapshot_sha256=digest(decode(snapshot_raw,1048576)),at=stamp(now)))

    def pending_preparations(self):
        """Pre-send claims survive a source outage; no provider replay rights."""
        with self.locked() as (rows,_):
            started={r['preparation'] for r in rows if r['type'] in ('seedbox_provider_started_v1','seedbox_preparation_superseded_v1')}
            # A failed source read is an explicit audit outcome, never a hot
            # polling loop. An accepted recovery transition is required before
            # the connected runner may select this same preparation again.
            blocked=_source_blocked(rows)
            return [r for r in rows if r['type']=='seedbox_preparation_claimed_v1' and digest(r) not in started|blocked]

    def record_source_failure(self,preparation,*,reason,retry_after,now):
        """Retain a finite pre-provider outcome. Never debit model credit.

        Auth/identity ambiguity needs owner recovery. Temporary failures retain
        their server-directed pause; scheduling/recovery is separately selected.
        This method itself grants no retry and does not retire a preparation.
        """
        temporary={'source_rate_limited','source_temporary','source_deadline'}
        reasons=temporary|{'source_configuration_unavailable','source_auth_denied','source_missing','source_redirect',
            'source_http_refused','source_content_invalid','source_size_bound',
            'host_listing_crosswalk_needed','host_listing_ambiguous_or_missing',
            'host_catalogue_ambiguous','host_listing_not_authenticated'}
        hash_id(preparation);require(reason in reasons,'queue_source_reason');stamp(now)
        require(retry_after is None or type(retry_after) in (int,float) and 0<=retry_after<10**12,'queue_source_cooldown')
        require(reason in temporary or retry_after is None,'queue_source_cooldown')
        with self.locked() as (rows,append):
            require(any(r['type']=='seedbox_preparation_claimed_v1' and digest(r)==preparation for r in rows),'queue_preparation_missing')
            require(not any(r['type']=='seedbox_provider_started_v1' and r['preparation']==preparation for r in rows),'queue_provider_consumed')
            record=dict(type='seedbox_source_blocked_v1',preparation=preparation,
                reason=reason,scope='source',configuration_sha256=rows[0]['configuration_sha256'],owner_action=reason not in temporary,
                retry_not_before=now+max(60,retry_after or 60) if reason in temporary else None,
                provider_request_consumed=False,at=now)
            append(record)
            return record

    def reserve_provider(self,preparation,*,policy,request_sha256,evidence_sha256,now,stage='assessment',review_of=None):
        """Atomic retained debit and no-resend boundary, before provider I/O.

        The connected host engine must independently authenticate evidence and
        build/validate the exact v13 request before entering this boundary.
        This arithmetic reservation alone is not an HTTP authorization token.
        """
        from automation.seedbox_credit_policy import permit
        hash_id(preparation);hash_id(request_sha256);hash_id(evidence_sha256)
        with self.locked() as (rows,append):
            matches=[r for r in rows if r['type']=='seedbox_preparation_claimed_v1' and digest(r)==preparation]
            require(len(matches)==1,'queue_preparation_missing');claim=matches[0]
            require(not any(r['type']=='seedbox_preparation_superseded_v1' and r['preparation']==preparation for r in rows),'queue_preparation_superseded')
            require(preparation not in _source_blocked(rows),'queue_source_blocked')
            attempts=[r for r in rows if r['type']=='seedbox_provider_started_v1']
            require(stage in ('assessment','review'),'queue_provider_stage')
            require(not any(r['case_id']==claim['case_id'] and r['stage']==stage for r in attempts),'queue_provider_consumed')
            require(not any(r['request_sha256']==request_sha256 for r in attempts),'queue_request_consumed')
            require(digest(policy)==rows[0]['policy_sha256'],'queue_policy_changed')
            if stage=='review':
                require(review_of is not None and any(r['type']=='seedbox_assessment_pending_review_v1' and r['preparation']==preparation and digest(r['report'])==review_of for r in rows),'queue_review_assessment_missing')
            else:require(review_of is None,'queue_provider_stage')
            require(policy['prior_history_sha256']==rows[0]['prior_history_sha256'] and policy['prior_credit_sha256']==rows[0]['prior_credit_sha256'],'queue_cutover_changed')
            debit=permit(policy,[dict(request_sha256=r['request_sha256'],reserved_usd=r['reserved_usd']) for r in attempts],now=now)
            attempt=dict(type='seedbox_provider_started_v1',preparation=preparation,stage=stage,review_of=review_of,case_id=claim['case_id'],request_sha256=request_sha256,evidence_sha256=evidence_sha256,reserved_usd=debit,policy_sha256=digest(policy),at=stamp(now))
            append(attempt)
            return attempt


def _case(value):
    require(type(value) is str and value.startswith('outcome-'),'queue_case')
    hash_id(value[8:])


def _pending(rows):
    done={r['event_id'] for r in rows if r['type'] in ('seedbox_preparation_claimed_v1','seedbox_queue_disposition_v1')}
    done|={key for r in rows if r['type']=='seedbox_queue_page_v1' for key in r.get('dispositions',{})}
    return [e for r in rows if r['type']=='seedbox_queue_page_v1' for e in r['page']['events'] if e['event_id'] not in done]


def _source_blocked(rows):
    blocked=set()
    for row in rows:
        if row['type']=='seedbox_source_blocked_v1':blocked.add(row['preparation'])
        elif row['type']=='seedbox_source_recovery_v1':blocked.discard(row['preparation'])
    return blocked
