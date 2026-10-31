"""Allowlisted, read-only observation of explicitly selected parent journals.

Caller-selected root/issue names bind journals that have no embedded identity.
No directory enumeration, lock/claim acquisition, PID inspection or task replay.
"""
from automation.coordinator import REPOSITORY, require, keys, stamp
from automation.coordinator_io import read_json
from automation.supervisor_policy import PolicyError
from automation.terminal_receipt import NEXT_ACTION, validate_receipt

LIMIT = 262144
STATES = ('READY_FOR_REVIEW', 'NEEDS_USER', 'FAILED')
EXECUTION = {
    'publication_mode': ('code', 'operations_only'),
    'child_process': ('not_started', 'running', 'exited', 'failed'),
    'worker_state': (None, *STATES),
    'code_publication': ('not_started', 'disabled', 'started', 'completed'),
    'terminal_state': (None, *STATES),
    'terminal_code': (None, *NEXT_ACTION),
    'receipt': ('not_attempted', 'not_authorized', 'unavailable', 'verified'),
    'public_result': ('not_attempted', 'unconfirmed', 'posted'),
}


def number(value):
    require(type(value) is int and 0 < value < 2**31, 'parent_number')


def association(value, issue, task=None):
    """Validate every association present; absence stays absent, never guessed."""
    require(isinstance(value, dict), 'parent_object')
    if 'repository' in value:
        require(value['repository'] == REPOSITORY, 'parent_identity')
    if 'issue' in value:
        require(type(value['issue']) is int and value['issue'] == issue, 'parent_identity')
    if 'task' in value and task is not None:
        require(type(value['task']) is int and value['task'] == task, 'parent_identity')
    if 'identity' in value:
        identity = value['identity']
        require(isinstance(identity, dict), 'parent_identity')
        association(identity, issue, task)


def execution(value, issue, task):
    association(value, issue, task)
    require(type(value.get('schema_version')) is int and value['schema_version'] == 1
            and value.get('task') == task, 'parent_execution')
    for name, allowed in EXECUTION.items():
        require(value.get(name) in allowed, 'parent_execution')
    require(value.get('checkout_unchanged') is None or type(value['checkout_unchanged']) is bool,
            'parent_execution')
    return {**{k: value.get(k) for k in EXECUTION},
            'checkout_unchanged': value.get('checkout_unchanged'), 'event_at': None}


def terminal(value, issue, task):
    validate_receipt(value)
    require(value['identity'] == {'repository': REPOSITORY, 'issue': issue, 'task': task}, 'parent_identity')
    # No private artifact reference, snapshot or runtime paths in this projection.
    return {'state': value['state'], 'code': value['code'],
            'artifact_readback': value['verification']['artifact_readback'],
            'artifact_reference_present': bool(value['artifacts']), 'event_at': None}


def delivery(value, issue, task):
    association(value, issue, task)
    require(value.get('receipt') in ('unavailable', 'not_authorized', 'verified')
            and type(value.get('public_result')) is bool and value.get('code') in NEXT_ACTION,
            'parent_delivery')
    if 'receipt_hashes' in value:
        hashes = value['receipt_hashes']
        from automation.supervisor_policy import hex_value
        require(isinstance(hashes, dict) and set(hashes) == {'sha256', 'blob', 'verified'}
                and hex_value(hashes['sha256'], 64) and hex_value(hashes['blob'], 40)
                and hashes['verified'] is True, 'parent_delivery')
    return {'receipt': value['receipt'], 'public_result_posted': value['public_result'],
            'code': value['code'], 'event_at': None}


def combined_status(records, tasks):
    statuses = {r['status'] for r in records.values()}
    if 'inconsistent' in statuses:
        return 'inconsistent'
    consumed = (records['state']['value'] or {}).get('consumed')
    for task in tasks:
        e = records[f'execution-{task}']['value']
        t = records[f'terminal-{task}']['value']
        d = records[f'delivery-{task}']['value']
        if consumed is not None and task not in consumed and (e or t or d):
            return 'inconsistent'
        # Receipt upload failure can leave intended and resulting terminal facts
        # different. Retain both without certifying a consistent observation.
        if e and t and (e['terminal_state'] != t['state'] or e['terminal_code'] != t['code']):
            return 'inconsistent'
        if e and d and (e['receipt'] != d['receipt']
                       or (e['public_result'] == 'posted') != d['public_result_posted']):
            return 'inconsistent'
        if t and d and t['code'] != d['code']:
            return 'inconsistent'
    return 'partial' if 'unavailable' in statuses else 'available'


def export_parent(root, issue, tasks, now):
    number(issue); stamp(now)
    require(isinstance(tasks, list) and 1 <= len(tasks) <= 8 and len(set(tasks)) == len(tasks), 'parent_selection')
    for task in tasks:
        number(task)
    records = {}
    def read(name, validate):
        try:
            raw = read_json(root, f'{issue}/{name}.json', LIMIT)
            association(raw, issue)
            value = validate(raw)
            records[name] = {'status': 'available', 'reason': 'validated', 'value': value}
            return value
        except FileNotFoundError:
            records[name] = {'status': 'unavailable', 'reason': 'missing', 'value': None}
        except (ValueError, PolicyError, OSError, KeyError, TypeError, AttributeError, RecursionError):
            records[name] = {'status': 'inconsistent', 'reason': 'invalid', 'value': None}
        return None
    def state(value):
        consumed = value.get('consumed')
        require(isinstance(consumed, list) and len(consumed) <= 8 and len(set(consumed)) == len(consumed), 'parent_consumed')
        for task in consumed:
            number(task)
        # Only the explicitly selected task numbers leave this projection.
        return {'consumed': sorted(set(consumed) & set(tasks))}
    read('state', state)
    def heartbeat(value):
        number(value.get('task')); stamp(value.get('updated_at'))
        require(type(value.get('active')) is bool and type(value.get('pid')) is int
                and value['pid'] > 0 and value['updated_at'] <= now + 300, 'parent_heartbeat')
        require(value['task'] in tasks, 'parent_heartbeat_selection')
        return {'task': value['task'], 'observed_at': value['updated_at'],
                'reported_active': value['active'], 'writer_liveness': 'unknown'}
    read('heartbeat', heartbeat)
    for task in sorted(tasks):
        read(f'execution-{task}', lambda v: execution(v, issue, task))
        read(f'terminal-{task}', lambda v: terminal(v, issue, task))
        read(f'delivery-{task}', lambda v: delivery(v, issue, task))
    status = combined_status(records, tasks)
    return {'version': 1, 'repository': REPOSITORY, 'issue': issue, 'tasks': sorted(tasks),
            'read_at': now, 'event_at': None, 'writer_liveness': 'unknown',
            'status': status, 'reason': 'conflicting_or_invalid' if status == 'inconsistent' else
            'missing_records' if status == 'partial' else 'validated', 'records': records}


def validate_export(value):
    """Revalidate the projected contract; imported projections are not authority."""
    keys(value, 'version repository issue tasks read_at event_at writer_liveness status reason records')
    require(type(value['version']) is int and value['version'] == 1 and value['repository'] == REPOSITORY,
            'parent_export')
    number(value['issue']); stamp(value['read_at'])
    require(value['event_at'] is None and value['writer_liveness'] == 'unknown', 'parent_liveness')
    require(value['status'] in ('available', 'partial', 'inconsistent'), 'parent_status')
    require(value['reason'] in ('validated', 'missing_records', 'conflicting_or_invalid'), 'parent_reason')
    require(isinstance(value['tasks'], list) and 1 <= len(value['tasks']) <= 8
            and len(set(value['tasks'])) == len(value['tasks']), 'parent_selection')
    for task in value['tasks']:
        number(task)
    expected = {'state', 'heartbeat'} | {f'{kind}-{n}' for n in value['tasks'] for kind in ('execution', 'terminal', 'delivery')}
    require(isinstance(value['records'], dict) and set(value['records']) == expected, 'parent_records')
    # Revalidate every projected field; no arbitrary strings reach the report.
    for name, record in value['records'].items():
        keys(record, 'status reason value')
        require(record['status'] in ('available', 'unavailable', 'inconsistent')
                and record['reason'] in ('validated', 'missing', 'invalid'), 'parent_record')
        require(record['reason'] == {'available': 'validated', 'unavailable': 'missing',
                                    'inconsistent': 'invalid'}[record['status']], 'parent_record_reason')
        v = record['value']
        if record['status'] != 'available':
            require(v is None, 'parent_record')
            continue
        if name == 'state':
            keys(v, 'consumed')
            require(isinstance(v['consumed'], list) and len(set(v['consumed'])) == len(v['consumed'])
                    and all(type(n) is int for n in v['consumed'])
                    and set(v['consumed']) <= set(value['tasks']), 'parent_consumed')
        elif name == 'heartbeat':
            keys(v, 'task observed_at reported_active writer_liveness')
            require(v['task'] in value['tasks'] and type(v['reported_active']) is bool
                    and v['writer_liveness'] == 'unknown', 'parent_heartbeat')
            number(v['task']); stamp(v['observed_at'])
        elif name.startswith('execution-'):
            keys(v, ' '.join(EXECUTION) + ' checkout_unchanged event_at')
            for key, allowed in EXECUTION.items():
                require(v[key] in allowed, 'parent_execution')
            require(v['event_at'] is None and (v['checkout_unchanged'] is None
                    or type(v['checkout_unchanged']) is bool), 'parent_execution')
        elif name.startswith('terminal-'):
            keys(v, 'state code artifact_readback artifact_reference_present event_at')
            require(v['state'] in STATES and v['code'] in NEXT_ACTION and v['event_at'] is None
                    and type(v['artifact_readback']) is bool and type(v['artifact_reference_present']) is bool,
                    'parent_terminal')
        else:
            keys(v, 'receipt public_result_posted code event_at')
            require(v['receipt'] in ('unavailable', 'not_authorized', 'verified')
                    and type(v['public_result_posted']) is bool and v['code'] in NEXT_ACTION
                    and v['event_at'] is None, 'parent_delivery')
    require(value['status'] == combined_status(value['records'], value['tasks']), 'parent_status_conflict')
    require(value['reason'] == {'available': 'validated', 'partial': 'missing_records',
                               'inconsistent': 'conflicting_or_invalid'}[value['status']], 'parent_reason_conflict')
    return value
