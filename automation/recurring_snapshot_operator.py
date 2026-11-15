"""Trusted supervisor helper, never a scheduler, sender or source authenticator.

Import from the main's reviewed operator process with its exact installed runtime.
All input pins and delivery attestations must be independently verified by main.
No CLI/environment setting grants authority. State uses a separate private History.
"""
from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import time

from ai_movie_investigator.contracts import decode, digest, encoded, require, shape, stamp, text
from ai_movie_investigator.history import History, FILENAME
from ai_movie_investigator.private_files import private_chain, read_private
from ai_movie_investigator import snapshot_authorization as gate, snapshot_review as review
from ai_movie_investigator import supervised_credit as credit


def pin_read(pin, limit=65536):
    shape(pin, 'path sha256')
    raw=read_private(Path(pin['path']),limit)
    require(hashlib.sha256(raw).hexdigest()==pin['sha256'],'operator_pin_changed')
    return raw


def consumed_cases(events):
    # Include starts even if preparation, authorization or sending was interrupted.
    # Same case_id is the established normalized/captured identity across versions.
    used=set()
    for row in events:
        if row.get('type')!='supervised_standing_attempt_started':continue
        for case in (row.get('historical',{}).get('case'),
                     row.get('captured',{}).get('authorization',{}).get('case')):
            if case is not None:used.add(case['case_id'])
    return used


def _write(directory,name,raw):
    with private_chain(Path(directory)) as fd:gate._write_once(fd,name,raw)
    path=Path(directory)/name
    require(read_private(path,1048576)==raw,'operator_write_changed')
    return dict(path=str(path),sha256=hashlib.sha256(raw).hexdigest())


class Operator:
    @staticmethod
    def enroll(state):
        """One explicit main operation; interrupted/old enrollment is never reset."""
        root=History(Path(state))
        with private_chain(root.directory) as dfd,root.transaction(write=True):
            journal_path=root.directory/'recurring-intake-v1'
            anchor_path=root.directory/'recurring-intake-anchor-v1'
            require(not any(os.path.lexists(p) for p in (journal_path,anchor_path,
                root.directory/'recurring-intake-binding.json')),'operator_already_enrolled')
            os.mkdir('recurring-intake-v1',mode=0o700,dir_fd=dfd)
            os.mkdir('recurring-intake-anchor-v1',mode=0o700,dir_fd=dfd)
            journal=History(journal_path);anchor=History(anchor_path)
            with journal.transaction(write=True) as (rows,append):
                append(dict(type='operator_enrolled_v1',root_identity=list(root.identity),root_path=str(root.directory)))
                with anchor.transaction(write=True) as (_,save):
                    save(dict(type='operator_high_water_v1',count=len(rows),sha256=digest(rows)))
            def identity(p):
                st=p.lstat();return [st.st_dev,st.st_ino]
            binding=dict(kind='operator_storage_v1',root_identity=list(root.identity),
                journal_identity=list(journal.identity),anchor_identity=list(anchor.identity),
                journal_file=identity(journal_path/FILENAME),anchor_file=identity(anchor_path/FILENAME))
            return _write(root.directory,'recurring-intake-binding.json',encoded(binding))

    def __init__(self,state,journal,*,clock=time.time):
        self.root=History(Path(state));self.journal=History(Path(journal));self.clock=clock
        require(self.journal.directory==self.root.directory/'recurring-intake-v1','operator_canonical_journal')
        self.anchor=History(self.root.directory/'recurring-intake-anchor-v1')
        self.binding_path=self.root.directory/'recurring-intake-binding.json'
        self.binding_raw=read_private(self.binding_path)
        self.binding=decode(self.binding_raw)
        shape(self.binding,'kind root_identity journal_identity anchor_identity journal_file anchor_file')
        require(self.binding['kind']=='operator_storage_v1' and
            self.binding['root_identity']==list(self.root.identity) and
            self.binding['journal_identity']==list(self.journal.identity) and
            self.binding['anchor_identity']==list(self.anchor.identity),'operator_storage_changed')

    @contextmanager
    def locked(self):
        # Fixed lock order: account root, high-water journal, intake journal.
        # Both files must already exist at their enrolled inodes. Each durable
        # intake append precedes its high-water append; a crash between them
        # causes mismatch and stops instead of reopening any reservation.
        with private_chain(self.root.directory),private_chain(self.journal.directory),private_chain(self.anchor.directory):
            with self.root.transaction(write=True) as (root,_):
                require(read_private(self.binding_path)==self.binding_raw,'operator_storage_changed')
                with self.anchor.transaction(write=True,file_identity=self.binding['anchor_file']) as (marks,save):
                    with self.journal.transaction(write=True,file_identity=self.binding['journal_file']) as (rows,append):
                        binding=dict(type='operator_enrolled_v1',root_identity=list(self.root.identity),root_path=str(self.root.directory))
                        require(rows and rows[0]==binding and marks,'operator_root_changed')
                        require(marks[-1]==dict(type='operator_high_water_v1',count=len(rows),sha256=digest(rows)),
                                'operator_journal_uncertain')
                        require(len(marks)==len(rows) and all(set(m)=={'type','count','sha256'} and
                            m['type']=='operator_high_water_v1' and m['count']==i
                            for i,m in enumerate(marks,1)),'operator_journal_uncertain')
                        for r in rows:
                            if r['type']=='operator_reserved_v1':
                                require(len(root)>=r['root_count'] and digest(root[:r['root_count']])==r['root_prefix_sha256'],
                                        'operator_root_rollback')
                        def durable(event):
                            append(event)
                            save(dict(type='operator_high_water_v1',count=len(rows),sha256=digest(rows)))
                        yield root,rows,durable

    def status(self):
        with self.locked() as (_,rows,__):return list(rows)

    def select(self,snapshot,*,authenticated_reference):
        """One durable reservation per UTC hour; main authenticates snapshot origin.

        Returns discovery only, not source evidence or send approval. A reserved
        case is never automatically selected again, including after a crash.
        """
        text(authenticated_reference,512)
        from identity_research_handoff import validate_snapshot
        with self.locked() as (root,rows,append):
            now=stamp(self.clock());cycle=int(now//3600)
            require(all(r.get('at',0)<=now for r in rows),'operator_clock_rollback')
            raw=pin_read(snapshot,1048576)
            snap=validate_snapshot(decode(raw,1048576),now)
            if any(r.get('cycle')==cycle for r in rows):return dict(status='cycle_consumed',cycle=cycle)
            used=consumed_cases(root)|{r['case_id'] for r in rows if r['type']=='operator_reserved_v1'}
            candidates=[]
            for case in snap['cases']:
                if case['case_id'] in used or case['route']!='eligible':continue
                try:review.select(raw,snapshot['sha256'],case['case_id'],case['version'],now=now)
                except ValueError:continue
                ids=case['source_identity']
                conflicting=any(ids[a] is not None and ids[b] is not None and ids[a]!=ids[b]
                    for a,b in (('imdb','asserted_imdb'),('tmdb','asserted_tmdb')))
                priority=0 if conflicting or case['reason'] in ('identity_conflict','title_conflict','year_conflict','local_identity_conflict') else 1
                candidates.append((priority,-case['first_observed_at'],case['case_id'],case))
            if not candidates:return dict(status='no_eligible_unassessed_case',cycle=cycle)
            case=min(candidates)[-1]
            event=dict(type='operator_reserved_v1',cycle=cycle,at=now,case_id=case['case_id'],
                       version=case['version'],snapshot=snapshot,authenticated_reference=authenticated_reference,
                       root_count=len(root),root_prefix_sha256=digest(root))
            append(event)
            return dict(status='needs_main_verified_inputs',reservation=digest(event),selection=event)

    @staticmethod
    def _reservation(rows,reservation):
        matches=[r for r in rows if r['type']=='operator_reserved_v1' and digest(r)==reservation]
        require(len(matches)==1,'operator_reservation_missing')
        return matches[0]

    def blocked(self,reservation,reason):
        require(reason in ('source_needed','catalogue_needed','account_needed','privacy_needed',
                           'input_guard_refused','preparation_interrupted','send_uncertain'),'operator_reason')
        with self.locked() as (_,rows,append):
            self._reservation(rows,reservation)
            require(not any(r.get('reservation')==reservation for r in rows),'operator_already_prepared')
            event=dict(type='operator_needed_v1',reservation=reservation,reason=reason,at=stamp(self.clock()))
            append(event);return event

    def prepare(self,reservation,*,authority,account_evidence,runtime,python,template,output):
        """Generate exact unchanged v13 wrapper from main-verified authority pins.

        Does not write acceptance or execute. Main must inspect and accept the
        returned exact wrapper through its existing trusted acceptance process.
        `output` is a new empty private directory for wrapper artifacts, distinct
        from authority.output_dir (which the existing runner keeps empty).
        """
        from ai_movie_investigator.installation import verify_installation
        from automation.snapshot_review_UNISSUED import executable_record
        runtime=Path(runtime);output=Path(output)
        manifest=verify_installation(runtime);template_raw=pin_read(template)
        require(template_raw.count(b'ISSUED = None')==1,'operator_template')
        selected=credit.read_evidence(Path(account_evidence['path']))
        require(selected.sha256==account_evidence['sha256'],'operator_account_changed')
        with self.locked() as (root,rows,append):
            chosen=self._reservation(rows,reservation)
            require(not any(r.get('reservation')==reservation for r in rows),'operator_already_prepared')
            require(len(root)==chosen['root_count'] and digest(root)==chosen['root_prefix_sha256'],
                    'operator_root_advanced')
            require(chosen['case_id'] not in consumed_cases(root),'operator_case_consumed')
            with gate.approved_snapshot_wrapper(authority['path'],authority['sha256']) as held:
                a=held.record
                require(str(output)!=a['output_dir'],'operator_separate_output')
                require(a.get('assessment',{}).get('kind')=='snapshot_film_prose_v13' and
                        a['assessment']['mode']=='first','operator_first_only')
                require(a['snapshot']==chosen['snapshot'] and a['attestation']['case_id']==chosen['case_id'] and
                        a['attestation']['version']==chosen['version'] and a['runtime_manifest_sha256']==digest(manifest),
                        'operator_selection_changed')
                grant=gate.proposal(self.root,root,selected.data)
                attempts=credit._standing_attempts(root,root[1]);slot=7+len(attempts)
                issued=dict(runtime=str(runtime),runtime_files=manifest,
                    python_sha256=executable_record(Path(python),104857600),
                    main_acceptance_path=str(output/'main-acceptance.json'),authority=authority,
                    account_evidence=account_evidence,state=str(self.root.directory),output_dir=a['output_dir'],
                    root_prefix_sha256=digest(root),expected_slot=slot)
                with private_chain(output) as fd:require(not os.listdir(fd),'operator_output_not_empty')
                # Durable intent precedes every write. Interrupted preparation is
                # not resumed/reissued: unrelated cases may progress later.
                append(dict(type='operator_preparing_v1',reservation=reservation,at=stamp(self.clock()),
                            authority=authority,request_sha256=digest(grant['request']),slot=slot))
                wrapper=_write(output,'snapshot-wrapper.py',template_raw.replace(b'ISSUED = None',
                                ('ISSUED = '+repr(issued)).encode(),1))
                acceptance=dict(decision='accepted_exact_normalized_snapshot_assessment',
                                wrapper_sha256=wrapper['sha256'],issued_pins=issued)
                event=dict(type='operator_prepared_v1',reservation=reservation,at=stamp(self.clock()),
                           slot=slot,wrapper=wrapper,issued=issued,acceptance_proposal=acceptance,
                           grant_sha256=digest(grant),projection=held.revalidate(),local_context=a['local_context'],
                           publisher_edition=a['assessment'].get('publisher_edition'))
                append(event);return event

    def pending_review(self,reservation,*,report):
        """Read back a completed v13 attempt and exact private HTML, without resend.

        Main supplies the actual report pin returned by the existing wrapper.
        This transition never calls credentials, provider, or the wrapper.
        """
        html=pin_read(report,1048576)
        with self.locked() as (root,rows,append):
            self._reservation(rows,reservation)
            prior=[r for r in rows if r.get('reservation')==reservation]
            require(prior and prior[-1]['type']=='operator_prepared_v1','operator_pending_transition')
            prepared=prior[-1];slot=prepared['slot']
            require(report['path']==str(Path(prepared['issued']['output_dir'])/'movie-review.html'),
                    'operator_report_path')
            attempts=credit._standing_attempts(root,root[1]);matches=[(s,a) for s,a in attempts if s['slot']==slot]
            starts=[s for s,_ in matches]
            done=[r for r in root if r.get('slot')==slot and r.get('type')=='supervised_completed']
            require(len(starts)==len(done)==1,'operator_completion_missing')
            start=starts[0];completion=done[0];g=start.get('historical',{});result=completion['historical_report']
            require(g.get('authority_sha256')==prepared['issued']['authority']['sha256'] and
                    g.get('contract_version')=='film_prose_v13' and g['assessment']['mode']=='first' and
                    g['case']['case_id']==self._reservation(rows,reservation)['case_id'] and
                    digest(g)==prepared['grant_sha256'] and
                    result['request_sha256']==start['request_sha256'] and
                    result['projection_sha256']==digest(prepared['projection']) and
                    result['local_context_sha256']==prepared['local_context']['sha256'], 'operator_completion_binding')
            attempt=History(self.root.directory/f'attempt-{slot}')
            require(list(attempt.identity)==matches[0][1]['attempt'],'operator_attempt_identity')
            receipt=attempt.read()
            require([r.get('type') for r in receipt]==['bound_send_reserved','bound_send_attempted','bound_send_receipt'] and
                result['receipt']==receipt[-1] and result['receipt_hash']==digest(receipt[-1]) and
                receipt[-1]['request_sha256']==start['request_sha256']==completion['request_hash'] and
                result['retained_reply_hash']==digest(completion['answer']) and
                result['generation_invoked'] is True and result['provider_receipt_correlated'] is True and
                result['sent'] is False,'operator_receipt_binding')
            from ai_movie_investigator.snapshot_private_report import render
            local=pin_read(prepared['local_context'])
            publisher=pin_read(prepared['publisher_edition']) if prepared['publisher_edition'] else None
            expected=render(result,digest(result),prepared['projection'],local,
                            prepared['local_context']['sha256'],publisher_raw=publisher).encode('utf-8')
            require(html==expected,'operator_report_bytes')
            event=dict(type='operator_pending_review_v1',reservation=reservation,at=stamp(self.clock()),
                slot=slot,completion_sha256=digest(completion),report_sha256=digest(result),
                attempt_sha256=digest(receipt),html=report,html_bytes=len(html))
            append(event);return event

    def reviewed(self,reservation,*,report_sha256,html_sha256,review_reference,observed_at):
        """Explicit main attestation AFTER inspecting the entire bound report."""
        text(review_reference,512);now=stamp(self.clock());stamp(observed_at)
        with self.locked() as (_,rows,append):
            prior=[r for r in rows if r.get('reservation')==reservation]
            require(prior and prior[-1]['type']=='operator_pending_review_v1','operator_review_transition')
            p=prior[-1];pin_read(p['html'],1048576)
            require(p['report_sha256']==report_sha256 and p['html']['sha256']==html_sha256 and
                    p['at']<=observed_at<=now,'operator_review_binding')
            e=dict(type='operator_reviewed_v1',reservation=reservation,at=now,pending_sha256=digest(p),
                   observed_at=observed_at,review_reference=review_reference)
            append(e);return e

    def delivered(self,reservation,*,review_sha256,delivery_reference,delivered_at):
        """Record actual user-facing delivery AFTER it happened; never sends.

        A crash between actual delivery and this acknowledgement is ambiguous:
        main checks the chat and binds its real reference; never blindly resends.
        """
        text(delivery_reference,512);now=stamp(self.clock());stamp(delivered_at)
        with self.locked() as (_,rows,append):
            prior=[r for r in rows if r.get('reservation')==reservation]
            require(prior and prior[-1]['type']=='operator_reviewed_v1','operator_delivery_transition')
            r=prior[-1]
            require(digest(r)==review_sha256 and r['at']<=delivered_at<=now,'operator_delivery_binding')
            e=dict(type='operator_delivered_v1',reservation=reservation,at=now,review_sha256=review_sha256,
                   delivered_at=delivered_at,delivery_reference=delivery_reference)
            append(e);return e
