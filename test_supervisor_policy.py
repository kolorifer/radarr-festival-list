"""Synthetic boundary tests: no private library or real credentials."""
import argparse
import base64
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from automation import github_worker as w
from automation import supervisor_policy as p
from test_github_worker import TASK, ISSUE, comment, FakeRunner

AUTH = {'repository': 'kolorifer/radarr-state', 'path': 'operations/synthetic-smoke.md',
        'expected_blob': 'absent', 'source': 'artifact.md'}
PRIVATE = TASK + 'PRIVATE_ARTIFACT: ' + json.dumps(AUTH) + '\n'


def item(data, sha='a' * 40):
    return {'type': 'file', 'encoding': 'base64', 'content': base64.b64encode(data).decode(), 'sha': sha}


class AuthorizationTests(unittest.TestCase):
    def test_exact_owner_capability_and_denied_destinations(self):
        self.assertEqual(p.private_artifact(PRIVATE), AUTH)
        for key, value in [('repository', 'other/repo'), ('path', 'operations/../private.md'),
                           ('path', 'operations//x.md'), ('path', '/operations/x.md'),
                           ('path', 'operations/x.md?ref=other'), ('expected_blob', 'main'),
                           ('source', '../artifact.md'), ('source', '/tmp/result.md')]:
            bad = dict(AUTH, **{key: value})
            with self.subTest(key=key, value=value), self.assertRaises(p.PolicyError):
                w.choose_task([comment(TASK + 'PRIVATE_ARTIFACT: ' + json.dumps(bad))], 'owner', set())
        self.assertIsNone(w.choose_task([comment(PRIVATE, login='stranger')], 'owner', set()))
        for suffix in ['private_artifact: {}', ' PRIVATE_ARTIFACT: {}', 'PRIVATE_ARTIFACT: {}\nPRIVATE_ARTIFACT: {}']:
            with self.assertRaises(p.PolicyError):
                p.private_artifact(suffix)

    def test_child_environment_and_config_cannot_inherit_host_tokens(self):
        with patch.dict(os.environ, GH_TOKEN='SYNTHETIC_PRIVATE_TOKEN', GITHUB_TOKEN='SYNTHETIC_PRIVATE_TOKEN',
                        SSH_AUTH_SOCK='/synthetic/socket', RADARR_API_KEY='SYNTHETIC_PRIVATE_TOKEN'):
            child = p.worker_environment()
        for key in ('GH_TOKEN', 'GITHUB_TOKEN', 'SSH_AUTH_SOCK', 'RADARR_API_KEY'):
            self.assertNotIn(key, child)
        command = w.codex_command(Path('/synthetic'), Path('/result'), Path('/schema'))
        self.assertIn('--ignore-user-config', command)
        self.assertIn('--ignore-rules', command)
        self.assertIn('model_reasoning_effort="high"', command)
        self.assertIn('approval_policy="never"', command)


class PrivatePublisherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.runner = FakeRunner(Path(self.temp.name))
        self.current = None
        self.writes = []
        self.private = True
        self.runner.api = lambda endpoint, **data: {'private': self.private, 'default_branch': 'main'}
        def gh(*args):
            if self.current is None:
                raise subprocess.CalledProcessError(1, ['gh'], stderr='HTTP 404')
            return json.dumps(self.current)
        def run(command, **kwargs):
            payload = json.loads(kwargs['input']); self.writes.append(payload)
            self.current = item(base64.b64decode(payload['content']))
            return '{}'
        self.runner.gh = gh; self.runner.run = run

    def test_create_readback_hash_and_identical_retry(self):
        receipt = self.runner.publish_private(AUTH, b'synthetic private bytes')
        self.assertEqual(receipt['sha256'], __import__('hashlib').sha256(b'synthetic private bytes').hexdigest())
        self.runner.publish_private(AUTH, b'synthetic private bytes')
        self.assertEqual(len(self.writes), 1)
        self.assertNotIn('sha', self.writes[0])

    def test_divergence_and_changed_expected_blob_refuse_before_write(self):
        self.current = item(b'previous private bytes')
        for expected in ('absent', 'b' * 40):
            with self.assertRaises(w.Stop):
                self.runner.publish_private(dict(AUTH, expected_blob=expected), b'new bytes')
        self.assertEqual(self.writes, [])

    def test_explicit_expected_blob_updates_with_cas(self):
        self.current = item(b'previous private bytes')
        self.runner.publish_private(dict(AUTH, expected_blob='a' * 40), b'new bytes')
        self.assertEqual(self.writes[0]['sha'], 'a' * 40)

    def test_public_repo_and_auth_failure_refuse(self):
        self.private = False
        with self.assertRaises(w.Stop): self.runner.publish_private(AUTH, b'new bytes')
        self.private = True
        self.runner.gh = lambda *args: (_ for _ in ()).throw(subprocess.CalledProcessError(1, ['gh'], stderr='HTTP 403'))
        with self.assertRaises(w.Stop): self.runner.publish_private(AUTH, b'new bytes')
        self.assertEqual(self.writes, [])

    def test_race_and_readback_corruption_fail_closed(self):
        self.runner.run = lambda *a, **k: (_ for _ in ()).throw(subprocess.CalledProcessError(1, ['gh'], stderr='HTTP 409'))
        with self.assertRaises(subprocess.CalledProcessError): self.runner.publish_private(AUTH, b'new bytes')
        self.runner.run = lambda *a, **k: setattr(self, 'current', item(b'corrupt')) or '{}'
        with self.assertRaises(w.Stop): self.runner.publish_private(AUTH, b'new bytes')
        self.assertFalse((self.runner.state_dir / 'private-receipt.json').exists())

    def test_linked_artifact_rejected(self):
        root = Path(self.temp.name)
        (root / 'elsewhere').write_text('synthetic')
        (root / 'artifact.md').symlink_to(root / 'elsewhere')
        with self.assertRaises(w.Stop): self.runner.artifact_bytes(AUTH, root)


class RealRetainedTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git('init', '-b', 'automation/issue-11-worker')
        self.git('config', 'user.email', 'test@example.invalid'); self.git('config', 'user.name', 'Synthetic')
        (self.root / 'base.txt').write_text('base'); self.git('add', '.'); self.git('commit', '-m', 'base')
        args = argparse.Namespace(repo=self.root, issue=11, github_repo='owner/project', base='main', sessions=self.root/'sessions', interval=10, once=True, dry_run=False)
        self.runner = w.Runner(args); self.runner.state_dir.mkdir(parents=True)
        self.runner.state['consumed'] = [1]
        (self.root / 'partial.txt').write_text('preserve exact synthetic bytes')
        self.fp = self.runner.record_retained(1, 'NEEDS_USER')
        self.follow = comment(TASK.replace('SUPERVISOR_TASK: 1', 'SUPERVISOR_TASK: 2') + 'CONTINUE_FROM: ' + json.dumps({'task': 1, 'snapshot': self.fp}))

    def git(self, *args):
        return subprocess.check_output(['git', *args], cwd=self.root, stderr=subprocess.DEVNULL)

    def test_exact_continuation_works_before_and_after_reservation_without_stash(self):
        self.assertTrue(self.runner.retained(self.follow, self.root))
        self.runner.state['consumed'].append(2)
        self.assertTrue(self.runner.retained(self.follow, self.root))
        self.assertEqual((self.root/'partial.txt').read_text(), 'preserve exact synthetic bytes')
        import tarfile
        with tarfile.open(self.runner.state_dir/'retained-1.tar') as backup:
            self.assertEqual(backup.extractfile('partial.txt').read(), b'preserve exact synthetic bytes')
        self.assertEqual(self.git('stash', 'list'), b'')

    def test_changed_working_index_head_and_wrong_task_fail(self):
        (self.root/'partial.txt').write_text('changed')
        with self.assertRaises(w.Stop): self.runner.retained(self.follow, self.root)
        (self.root/'partial.txt').write_text('preserve exact synthetic bytes')
        self.git('add', 'partial.txt')
        with self.assertRaises(w.Stop): self.runner.retained(self.follow, self.root)
        self.runner.state['consumed'] = [1, 3]
        with self.assertRaises(w.Stop): self.runner.retained(self.follow, self.root)

    def test_unexplained_dirty_state_never_authorized(self):
        self.assertFalse(self.runner.retained(comment(), self.root))
        self.runner.state['retained']['state'] = 'READY_FOR_REVIEW'
        with self.assertRaises(w.Stop): self.runner.retained(self.follow, self.root)


class PrivateExecutionTests(unittest.TestCase):
    def test_private_task_never_reflects_worker_prose_or_publishes_public_git(self):
        for state in ('READY_FOR_REVIEW', 'NEEDS_USER'):
            with self.subTest(state=state), tempfile.TemporaryDirectory() as directory:
                runner = FakeRunner(Path(directory)); actions = []; old_git = runner.git
                runner.git = lambda *args: actions.append(args) or old_git(*args)
                runner.publish_private = lambda *args: {'verified': True}
                sentinel = 'SYNTHETIC_PRIVATE_IDENTITY_AND_EVIDENCE'
                def child(command, **kwargs):
                    staging = Path(command[command.index('--add-dir') + 1]); (staging/'artifact.md').write_text(sentinel)
                    output = Path(command[command.index('--output-last-message') + 1])
                    output.write_text(json.dumps(dict(state=state, tests=sentinel, summary=sentinel, questions=sentinel)))
                with patch.object(w.subprocess, 'run', side_effect=child), patch.object(w, 'snapshot', return_value='a'*64):
                    w.Runner.execute(runner, ISSUE, comment(PRIVATE), 1)
                public = '\n'.join(body for action, body in runner.calls if action == 'post')
                self.assertNotIn(sentinel, public)
                self.assertNotIn(directory, public)
                self.assertFalse(any(a[0] in ('add', 'push', 'commit') for a in actions))
                for stage in runner.state.get('staging', {}).values():
                    import shutil; shutil.rmtree(stage)

    def test_dirty_private_result_is_never_published(self):
        with tempfile.TemporaryDirectory() as directory:
            runner = FakeRunner(Path(directory)); runner.publish_private = lambda *args: self.fail('published')
            def child(command, **kwargs):
                runner.dirty = True
                Path(command[command.index('--output-last-message')+1]).write_text(json.dumps(dict(state='READY_FOR_REVIEW', tests='', summary='', questions='')))
            with patch.object(w.subprocess, 'run', side_effect=child), patch.object(w, 'snapshot', return_value='a'*64), self.assertRaises(w.Stop):
                w.Runner.execute(runner, ISSUE, comment(PRIVATE), 1)
            self.assertFalse(any('READY_FOR_REVIEW' in str(body) for action, body in runner.calls if action == 'post'))
            import shutil
            for stage in runner.state.get('staging', {}).values(): shutil.rmtree(stage)


if __name__ == '__main__': unittest.main()
