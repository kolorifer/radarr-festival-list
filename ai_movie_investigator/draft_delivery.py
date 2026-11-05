"""Explicit disabled integration with the actor's existing Digest delivery ledger.

No daemon/CLI wiring, credentials or sender construction. A trusted supervisor
must select the exact immutable draft and existing outbox. HTTP success means
transport acknowledgement, not recipient ingestion or identity approval.
"""
import os

from identity_telegram_digest import Digest
from .contracts import decode, digest, encoded, require, shape, stamp
from .history import selected_current, research_dependency
from .new_case import admitted, projection, notification, request_for
from .controller import validate_final

FOOTER = 'DRAFT ONLY — not sent; no approval buttons or download authority.'


def outbox_identity(outbox):
    require(type(outbox) is Digest, 'notification_outbox_type')
    st = os.stat(outbox.path, follow_symlinks=False)
    return dict(path=str(outbox.path), device=st.st_dev, inode=st.st_ino)


def deliver(history, outbox, selection, send, *, enabled=False):
    """Send at most once through the supplied existing sender; disabled by default.

    Only an explicit 429 rejection can retry, under the existing Digest rule.
    Unknown sends remain uncertain across restart. Pre-reservation validation or
    storage failures do not call send. No claim of genuine inference is added.
    """
    require(enabled is True, 'investigator_delivery_disabled')
    selection = decode(encoded(selection), 4096)
    shape(selection, 'job binding report_hash draft_hash')
    with history.transaction(write=True) as (events, append):
        job = selection['job']
        done = [e for e in events if e['type'] == 'new_case_completed' and e['job'] == job]
        require(len(done) == 1, 'notification_report_missing')
        event = done[0]; report = event['report']
        require(digest(report) == event['report_hash'] == selection['report_hash'] and
                report['binding'] == selection['binding'] and report['job'] == job and
                digest(report['draft']) == selection['draft_hash'], 'notification_selection_changed')
        selected_current(events, job)
        research_dependency(events, job)
        packet = next(e['packet'] for e in events if e['type'] == 'intake' and e['job'] == job)
        prepared = next(e for e in events if e['type'] == 'new_case_prepared' and e['job'] == job)
        now = stamp(history.clock())
        require(now >= event['at'] >= prepared['at'], 'notification_clock_rollback')
        rec = admitted(packet, selection['binding'], now)
        require(digest(rec) == prepared['reconciliation_hash'], 'notification_applicability_changed')
        request = request_for(packet, rec, prepared['at'])
        require(request == prepared['request'] and digest(request) == report['request_hash'], 'notification_request_changed')
        _, supplied = projection(packet, rec, prepared['at'])
        validate_final(report['assessment'], supplied, rec, now)
        # Do not silently rewrite a selected draft when its freshness changes.
        data, _ = projection(packet, rec, now)
        expected = notification(packet, {'result': report['assessment']}, data, report['provenance'])
        require(expected == report['draft'], 'notification_draft_stale_or_changed')
        raw = expected['text']
        require(raw.endswith('\n' + FOOTER), 'notification_draft_footer')
        message = raw[:-len(FOOTER)] + 'Review proposal only; no identity or download approval.'
        identity = outbox_identity(outbox)
        # Bind ledger identity before attempting delivery; switching directories
        # or replacing the DB cannot refund an uncertain/sent opportunity.
        chosen = dict(selection=selection, outbox=identity, message_hash=digest(message))
        prior = [e for e in events if e['type'] == 'new_case_delivery_selected' and e['job'] == job]
        require(len(prior) <= 1 and (not prior or prior[0]['chosen'] == chosen), 'notification_outbox_or_selection_changed')
        if not prior:
            append(dict(type='new_case_delivery_selected', job=job, chosen=chosen, at=now))
        key = digest(dict(purpose='investigator-draft-delivery-v1', **chosen))
        cid = packet['binding']['case_id']
        starts = [e for e in events if e['type'] == 'new_case_delivery_send_started' and e['job'] == job]
        attempt = len(starts)
        invoked = False

        def bound_send(body):
            nonlocal attempt, invoked
            # Independent of the SQLite pathname: a replaced/restored outbox
            # cannot erase an ambiguous send. Only a retained explicit rejection
            # with its original due time permits another invocation.
            if starts:
                require(any(e['type'] == 'new_case_delivery_receipt' and
                    e['receipt']['job'] == job and e['receipt']['attempt'] == attempt and
                    e['receipt']['delivery_key'] == key and e['receipt']['state'] == 'retry' and
                    e['receipt']['due'] <= now for e in events), 'notification_send_already_consumed')
            require(body == message, 'notification_message_changed')
            attempt += 1
            append(dict(type='new_case_delivery_send_started', job=job, at=now,
                        delivery_key=key, attempt=attempt, message_hash=digest(body)))
            invoked = True
            response = send(body)
            if response == 200:
                append(dict(type='new_case_delivery_transport_ack', job=job, at=now,
                            delivery_key=key, attempt=attempt))
            return response

        # A missing ledger entry after a possible send is not a pre-send failure.
        with outbox.connect() as c:
            retained = c.execute('SELECT state,due FROM delivery WHERE case_id=? AND version=?', (cid,key)).fetchone()
        if starts:
            require(retained is not None, 'notification_uncertain_ledger_missing')
        else:
            require(retained is None, 'notification_unbound_delivery_state')
        def record_outcome(state, due):
            # Called by Digest after its single actual 429 parse and before the
            # mutable ledger update. Keep the original delay independently.
            if invoked and state == 'retry':
                append(dict(type='new_case_delivery_rejected_429', job=job, at=now,
                            delivery_key=key, attempt=attempt, due=due))

        outbox.tick([(cid, key, 'eligible', message)], bound_send, now,
                    exact_message=message, record_outcome=record_outcome)
        require(outbox_identity(outbox) == identity, 'notification_outbox_changed')
        with outbox.connect() as c:
            row = c.execute('SELECT state,due FROM delivery WHERE case_id=? AND version=?', (cid,key)).fetchone()
        require(row is not None and row[0] in ('sent','uncertain','retry'), 'notification_receipt_missing')
        require(attempt > 0, 'notification_send_start_missing')
        proof = {'sent': 'new_case_delivery_transport_ack', 'retry': 'new_case_delivery_rejected_429'}
        if row[0] in proof:
            require(any(e['type'] == proof[row[0]] and e['job'] == job and
                        e['attempt'] == attempt and e['delivery_key'] == key and
                        (row[0] != 'retry' or e['due'] == row[1]) for e in events),
                    'notification_transport_proof_missing')
        receipt = dict(job=job, attempt=attempt, binding=selection['binding'], report_hash=selection['report_hash'],
            draft_hash=selection['draft_hash'], message_hash=digest(message), delivery_key=key,
            outbox=identity, state=row[0], due=row[1],
            transport_acknowledged=row[0] == 'sent', recipient_ingestion_verified=False,
            simulation=report['provenance']['mode'] == 'simulation', identity_approval=False, download_approval=False)
        # On restart, an existing ledger acknowledgement can finish this local
        # receipt without calling the sender or fabricating recipient ingestion.
        if not any(e['type'] == 'new_case_delivery_receipt' and e['receipt'] == receipt for e in events):
            append(dict(type='new_case_delivery_receipt', job=job, at=now, receipt=receipt))
        return dict(receipt=receipt, attempted=invoked)
