"""Serialized durable preparation and offline receipt reconciliation; never sends."""
import contextlib
import copy
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat

from automation import coordinator as c
from automation.coordinator_io import directory, read_bytes, decode, digest, encode
from automation.coordinator_sources import hex64, material_report
from automation.coordinator_parent import number
from automation.supervisor_policy import PRIVATE_REPOSITORY, exact_path, hex_value
from automation.terminal_receipt import validate_receipt

MAX_REPORTS = 20
MAX_PAYLOAD = 524288
MAX_STATE = 8 * 1024 * 1024


@contextlib.contextmanager
def locked(path):
    """Coordinator-owned lock, held over read/reconcile/prepare/fsync/save.

    The containing directory is owner-only, stable, and supplied explicitly.
    This lock is never a dispatcher execution lock or proof of writer liveness.
    """
    path = Path(path).absolute()
    checkout = Path(__file__).resolve().parent.parent
    c.require(checkout != path and checkout not in path.parents, 'state_inside_checkout')
    with directory(path.parent) as parent:
        info = os.fstat(parent)
        c.require(info.st_uid == os.getuid() and info.st_mode & 0o077 == 0, 'state_directory')
        lock_name = path.name + '.coordinator.lock'
        flags = os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK
        try:
            fd = os.open(lock_name, flags | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=parent)
        except FileExistsError:
            fd = os.open(lock_name, flags, dir_fd=parent)
        try:
            info = os.fstat(fd)
            c.require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_uid == os.getuid()
                      and info.st_mode & 0o077 == 0, 'coordinator_lock')
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield path
        finally:
            os.close(fd)


def empty():
    return {'version': 2, 'reconciliation': c.empty_state(), 'sequence': 0, 'outbox': [],
            'migration': 'new'}


def validate_intent(value):
    c.keys(value, 'identity destination')
    c.keys(value['identity'], 'repository issue task')
    c.require(value['identity']['repository'] == c.REPOSITORY, 'intent_repository')
    number(value['identity']['issue']); number(value['identity']['task'])
    dest = value['destination']
    c.keys(dest, 'repository path expected_blob')
    c.require(dest['repository'] == PRIVATE_REPOSITORY, 'intent_destination')
    exact_path(dest['path'], destination=True)
    c.require(dest['expected_blob'] == 'absent' or hex_value(dest['expected_blob'], 40), 'intent_blob')
    return value


def validate(value):
    c.keys(value, 'version reconciliation sequence outbox migration')
    c.require(type(value['version']) is int and value['version'] == 2, 'outbox_version')
    c.validate_state(value['reconciliation'])
    c.require(type(value['sequence']) is int and 0 <= value['sequence'] < 2**63, 'outbox_sequence')
    c.require(value['migration'] in ('new', 'v1_reprepared_unacknowledged'), 'outbox_migration')
    c.require(isinstance(value['outbox'], list) and len(value['outbox']) <= MAX_REPORTS, 'outbox_capacity')
    ids = set()
    for item in value['outbox']:
        c.keys(item, 'id sequence material payload sha256 publication recipient_delivery')
        hex64(item['id']); hex64(item['material']); hex64(item['sha256'])
        c.require(item['id'] not in ids and type(item['sequence']) is int
                  and 0 < item['sequence'] <= value['sequence'], 'outbox_identity')
        ids.add(item['id'])
        c.require(item['id'] == c.fingerprint({'version': 2, 'sequence': item['sequence'],
                                             'material': item['material']}), 'outbox_identity')
        c.require(isinstance(item['payload'], str) and len(item['payload'].encode()) <= MAX_PAYLOAD
                  and digest(item['payload'].encode()) == item['sha256'], 'outbox_payload')
        payload = decode(item['payload'].encode())
        comparison = payload.get('comparison_version', 1)
        c.require(type(comparison) is int and comparison in (1, 2), 'outbox_comparison')
        materializer = c.material_value if comparison == 1 else material_report
        c.require(payload['fingerprint'] == item['material'] and payload['changed'] is True
                  and c.fingerprint(materializer(payload['report'])) == item['material'], 'outbox_payload')
        c.require(item['recipient_delivery'] == 'not_configured', 'recipient_delivery')
        publication = item['publication']
        c.keys(publication, 'status intent evidence')
        c.require(publication['status'] in ('pending', 'uncertain', 'verified'), 'publication_status')
        if publication['intent'] is not None:
            validate_intent(publication['intent'])
        evidence = publication['evidence']
        if publication['status'] == 'verified':
            c.require(publication['intent'] is not None, 'publication_intent')
            c.keys(evidence, 'receipt_sha256 artifact_blob')
            hex64(evidence['receipt_sha256'])
            c.require(hex_value(evidence['artifact_blob'], 40), 'publication_evidence')
        else:
            c.require(evidence is None, 'publication_evidence')
    if value['reconciliation']['material'] is not None:
        c.require(value['outbox'] and value['outbox'][-1]['material'] == value['reconciliation']['material']
                  and value['outbox'][-1]['sequence'] == value['sequence'], 'outbox_transition_payload_missing')
    c.require(len(encode(value)) <= MAX_STATE, 'outbox_bytes')
    return value


def read_state(path):
    try:
        value = decode(read_bytes(path.parent, path.name, MAX_STATE))
    except FileNotFoundError:
        return empty()
    if value.get('version') == 1:
        # Fingerprints alone cannot recover the old payload, nor prove delivery.
        # Reprepare one current report, keeping prior stage history for comparison.
        c.validate_state(value)
        result = empty()
        result['reconciliation'] = copy.deepcopy(value)
        result['reconciliation'].update(material=None, sections={})
        result['migration'] = 'v1_reprepared_unacknowledged'
        return result
    return validate(value)


def pending(value):
    # Even verified publication remains undelivered without a recipient interface.
    return [{'id': item['id'], 'sha256': item['sha256'], 'payload': item['payload'],
             'publication': copy.deepcopy(item['publication']),
             'recipient_delivery': item['recipient_delivery']} for item in value['outbox']]


def save(path, value):
    validate(value)
    # atomic_save uses the standard spaced JSON representation on disk.
    c.require(len(json.dumps(value, sort_keys=True, allow_nan=False).encode()) <= MAX_STATE,
              'outbox_bytes')
    c.atomic_save(path, value)


def poll(path, report_factory, intent=None):
    """Prepare before exposing stdout. Unchanged replay exposes identical outbox.

    No publication attempt is made here. Intent is explicit local configuration,
    not derived from imported source content and not an execution authorization.
    """
    if intent is not None:
        validate_intent(intent)
    with locked(path) as path:
        value = read_state(path)
        baseline = value['reconciliation']
        if value['outbox']:
            # Rebase comparison only in memory from the actual last immutable
            # payload. Never rewrite legacy IDs/bytes/hashes/intents/receipts or
            # label its provenance as a newer observation. Quiet polls don't save.
            previous = decode(value['outbox'][-1]['payload'].encode())['report']
            baseline, _ = c.reconcile_report(previous, baseline, material_report)
        updated, output = c.reconcile_report(report_factory(), baseline, material_report)
        output['comparison_version'] = 2
        if output['changed']:
            if len(value['outbox']) >= MAX_REPORTS:
                return {'changed': False, 'material_change_pending': True,
                        'backpressure': True, 'reason': 'outbox_full',
                        'pending_outbox': pending(value)}
            sequence = value['sequence'] + 1
            raw = encode(output)
            if len(raw) > MAX_PAYLOAD:
                return {'changed': False, 'material_change_pending': True,
                        'backpressure': True, 'reason': 'report_too_large',
                        'pending_outbox': pending(value)}
            item = {'id': c.fingerprint({'version': 2, 'sequence': sequence, 'material': output['fingerprint']}),
                    'sequence': sequence, 'material': output['fingerprint'],
                    'payload': raw.decode(), 'sha256': digest(raw),
                    'publication': {'status': 'pending', 'intent': copy.deepcopy(intent), 'evidence': None},
                    'recipient_delivery': 'not_configured'}
            candidate = copy.deepcopy(value)
            candidate.update(reconciliation=updated, sequence=sequence)
            candidate['outbox'].append(item)
            if len(json.dumps(candidate, sort_keys=True, allow_nan=False).encode()) > MAX_STATE:
                return {'changed': False, 'material_change_pending': True,
                        'backpressure': True, 'reason': 'outbox_bytes_full',
                        'pending_outbox': pending(value)}
            value = candidate
            # Payload + suppressing material transition share one fsynced atomic
            # state commit. A crash before/after it leaves no payload-less gap.
            save(path, value)
        return {**output, 'backpressure': False, 'pending_outbox': pending(value)}


def find(value, report_id):
    hex64(report_id)
    matches = [item for item in value['outbox'] if item['id'] == report_id]
    c.require(len(matches) == 1, 'unknown_report')
    return matches[0]


def publication_uncertain(path, report_id):
    """External owner records an attempt boundary before its one write attempt.

    Interruption thereafter requires exact readback reconciliation, never resend.
    Repeated calls only expose that same boundary; no attempt counter is advanced.
    """
    with locked(path) as path:
        value = read_state(path)
        item = find(value, report_id)
        c.require(item['publication']['intent'] is not None, 'publication_intent_missing')
        if item['publication']['status'] == 'pending':
            item['publication']['status'] = 'uncertain'
            save(path, value)
        return pending(value)


def reconcile_publication(path, report_id, worker_root, issue, task, receipt_sha256,
                          artifact_root, artifact_file):
    """Import a pinned parent terminal receipt and independently staged readback.

    Trust is external: the accountable operator must authenticate parent-root
    provenance and the exact receipt pin. A child-written JSON/flag is not proof.
    The pin is an integrity binding, not authentication or execution authority.
    Reads only the selected terminal-N.json and one exact staged artifact file.
    """
    number(issue); number(task); hex64(receipt_sha256)
    with locked(path) as path:
        value = read_state(path)
        item = find(value, report_id)
        intent = item['publication']['intent']
        c.require(intent is not None, 'publication_intent_missing')
        expected_identity = {'repository': c.REPOSITORY, 'issue': issue, 'task': task}
        c.require(intent['identity'] == expected_identity, 'receipt_identity')
        raw = read_bytes(worker_root, f'{issue}/terminal-{task}.json', 262144)
        c.require(digest(raw) == receipt_sha256, 'receipt_hash')
        receipt = validate_receipt(decode(raw))
        c.require(receipt['identity'] == expected_identity, 'receipt_identity')
        c.require(receipt['verification']['artifact_readback'] is True
                  and len(receipt['artifacts']) == 1, 'receipt_readback_missing')
        artifact = receipt['artifacts'][0]
        destination = intent['destination']
        c.require(all(artifact[k] == destination[k] for k in ('repository', 'path'))
                  and artifact['sha256'] == item['sha256'], 'receipt_artifact_conflict')
        content = read_bytes(artifact_root, artifact_file, MAX_PAYLOAD)
        c.require(content == item['payload'].encode() and digest(content) == artifact['sha256'],
                  'artifact_content_conflict')
        blob = hashlib.sha1(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest()
        c.require(artifact['blob'] == blob, 'artifact_blob_conflict')
        evidence = {'receipt_sha256': receipt_sha256, 'artifact_blob': artifact['blob']}
        previous = item['publication']
        if previous['status'] == 'verified':
            c.require(previous['evidence'] == evidence, 'receipt_conflicting_evidence')
        else:
            previous.update(status='verified', evidence=evidence)
            save(path, value)
        return pending(value)


def view(path):
    with locked(path) as path:
        return pending(read_state(path))
