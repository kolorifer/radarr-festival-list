#!/usr/bin/env python3
"""Synthetic executable only. No network, auth, real client or model invocation."""
import json
import os
from pathlib import Path
import sys
import time

STARTUP_DELAY = 0.0
if sys.argv[1:] in (['--version'], ['exec', '--help']):
    time.sleep(STARTUP_DELAY)

FLAGS = '--strict-config --ignore-user-config --ignore-rules --sandbox --skip-git-repo-check --cd --output-schema --json --ephemeral --model'
if sys.argv[1:] == ['--version']:
    print('synthetic-codex-fixture-1')
elif sys.argv[1:] == ['exec', '--help']:
    print(FLAGS)
else:
    args = sys.argv[1:]
    assert args[:3] == ['-c', 'approval_policy="never"', 'exec']
    assert args[-1] == '-'
    for flag in FLAGS.split():
        assert flag in args
    assert args[args.index('--sandbox') + 1] == 'read-only'
    assert args[args.index('--cd') + 1] == str(Path.cwd())
    assert '--resume' not in args and 'resume' not in args
    assert not any(k in os.environ for k in ('OPENAI_API_KEY', 'CODEX_API_KEY', 'NODE_OPTIONS', 'PYTHONPATH'))
    controls = [args[i + 1] for i, value in enumerate(args[:-1]) if value == '-c']
    for value in ('forced_login_method="chatgpt"', 'features.shell_tool=false',
                  'features.hooks=false', 'features.multi_agent=false', 'agents.enabled=false',
                  'web_search="disabled"', 'project_doc_max_bytes=0', 'tools.view_image=false'):
        assert value in controls
    for family in ('plugins', 'remote_plugin', 'browser_use', 'browser_use_external',
                   'browser_use_full_cdp_access', 'computer_use', 'in_app_browser',
                   'image_generation', 'code_mode_host', 'skill_search', 'request_permissions_tool'):
        assert 'features.' + family + '=false' in controls
    assert 'skills.max_context_tokens=0' in controls
    schema = json.loads(Path(args[args.index('--output-schema') + 1]).read_text())
    assert schema['additionalProperties'] is False
    packet = json.load(sys.stdin)
    assert set(Path.cwd().iterdir()) == {Path.cwd() / 'output-schema.json'}
    if 'binding_hash' in packet:
        reply = dict(binding_hash=packet['binding_hash'], kind='final', lookups=[],
                     result=dict(status='unresolved', candidate=None, alternatives=[], citations=[],
                                 rationale='Synthetic executable protocol proof only.',
                                 uncertainty='No real inference occurred.', next_action='obtain_retained_evidence'))
    else:
        reply = dict(synthetic=True)
    for event in [dict(type='thread.started', thread_id='synthetic-thread'),
                  dict(type='turn.started'),
                  dict(type='item.completed', item=dict(id='synthetic-item', type='agent_message', text=json.dumps(reply))),
                  dict(type='turn.completed', usage=dict(input_tokens=1, output_tokens=1))]:
        print(json.dumps(event))
