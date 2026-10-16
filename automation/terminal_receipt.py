"""Version 1 parent-only diagnostics. No worker text or exception strings."""
import re

try:
    from automation.supervisor_policy import PolicyError, PRIVATE_REPOSITORY, exact_path, hex_value
except ModuleNotFoundError:
    from supervisor_policy import PolicyError, PRIVATE_REPOSITORY, exact_path, hex_value


# Codes describe the parent-observed boundary, not an inferred root cause.
NEXT_ACTION = {
    'OK': 'review',
    'WORKER_BLOCKED': 'new_task',
    'CLAIM_FAILED': 'inspect_local',
    'EXECUTION_FAILED': 'inspect_local',
    'CHECKOUT_FAILED': 'inspect_local',
    'INPUT_CHANGED': 'inspect_local',
    'CHILD_FAILED': 'inspect_local',
    'INVALID_RESULT': 'inspect_local',
    'PUBLIC_CHANGE_REFUSED': 'inspect_local',
    'ARTIFACT_INVALID': 'inspect_local',
    'ARTIFACT_PUBLICATION_FAILED': 'reconcile_private',
    'PUBLIC_CODE_PUBLICATION_FAILED': 'inspect_local',
    'RECEIPT_PUBLICATION_FAILED': 'inspect_local',
    'RESULT_PUBLICATION_FAILED': 'reconcile_private',
}
FLAGS = {'inputs_verified', 'inputs_unchanged', 'public_checkout_unchanged', 'artifact_readback'}


def validate_receipt(value):
    """An explicit allowlist, also used before every upload of a generated receipt."""
    def require(condition):
        if not condition:
            raise PolicyError('Invalid structured terminal receipt')
    require(isinstance(value, dict) and set(value) == {
        'schema_version', 'identity', 'state', 'code', 'next_action', 'runtime',
        'retained_snapshot', 'verification', 'artifacts'})
    require(type(value['schema_version']) is int and value['schema_version'] == 1)
    identity = value['identity']
    require(isinstance(identity, dict) and set(identity) == {'repository', 'issue', 'task'})
    require(isinstance(identity['repository'], str)
            and re.fullmatch(r'[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}', identity['repository']))
    require(all(type(identity[k]) is int and identity[k] > 0 for k in ('issue', 'task')))
    require(value['state'] in ('READY_FOR_REVIEW', 'NEEDS_USER', 'FAILED'))
    require(isinstance(value['code'], str) and value['code'] in NEXT_ACTION)
    require(value['next_action'] == NEXT_ACTION[value['code']])
    require((value['state'] == 'READY_FOR_REVIEW' and value['code'] == 'OK')
            or (value['state'] == 'NEEDS_USER' and value['code'] in ('WORKER_BLOCKED', 'CLAIM_FAILED'))
            or (value['state'] == 'FAILED' and value['code'] not in ('OK', 'WORKER_BLOCKED')))
    runtime = value['runtime']
    require(isinstance(runtime, dict) and set(runtime) == {'python', 'runner_revision', 'checkout_revision'})
    require(isinstance(runtime['python'], str) and re.fullmatch(r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}', runtime['python']))
    require(all(runtime[k] is None or hex_value(runtime[k], 40)
                for k in ('runner_revision', 'checkout_revision')))
    require(value['retained_snapshot'] is None or hex_value(value['retained_snapshot'], 64))
    flags = value['verification']
    require(isinstance(flags, dict) and set(flags) == FLAGS and all(type(v) is bool for v in flags.values()))
    require(isinstance(value['artifacts'], list) and len(value['artifacts']) <= 1)
    for artifact in value['artifacts']:
        require(isinstance(artifact, dict) and set(artifact) == {'repository', 'path', 'blob', 'sha256'})
        require(artifact['repository'] == PRIVATE_REPOSITORY)
        exact_path(artifact['path'], destination=True)
        require(hex_value(artifact['blob'], 40) and hex_value(artifact['sha256'], 64))
    return value
