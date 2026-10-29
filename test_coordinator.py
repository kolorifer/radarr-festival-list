"""Synthetic inputs only; no worker launch, credential read or network in tests."""
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from automation import coordinator as c
from automation.supervisor_policy import PolicyError

NOW = 1_800_000_000
HEAD = 'a' * 40
OLD = 'b' * 40


def rows(items=(), status='complete'):
    return {'status': status, 'items': list(items)}


def task(number=1, author='owner', **changes):
    value = {'id': number, 'user': {'login': author}, 'body': (
        f'SUPERVISOR_TASK: {number}\nSTATE: READY_FOR_CODEX\n'
        'GOAL:\nImplement synthetic coordinator support.\n'
        'ACCEPTANCE_CRITERIA:\n- Focused tests and docs pass.\n'
        'COORDINATOR_STAGES: implementation,review,test,docs\n'
        'AUTHORIZATION:\n- Scoped repository edits and local tests.\n'
        'FORBIDDEN:\n- Deployments, notifications and provider calls.\n'
        'INSTRUCTIONS:\n- Inspect the actual diff.\n')}
    value.update(changes)
    return value


def snapshot():
    source = task()
    sections = c.task_sections(source, 'owner')
    goal = {'id': 'synthetic-support', 'source': {'comment_id': 1, 'body_sha256': c.fingerprint(source['body'])},
            'scope': sections['GOAL'], 'allowed_actions': sections['AUTHORIZATION'],
            'acceptance_criteria': sections['ACCEPTANCE_CRITERIA'], 'dependencies': [],
            'issue': 111, 'task': 1, 'pr': 112, 'head': HEAD, 'blocker': None,
            'next_action': 'review', 'evidence': [], 'required_stages': ['implementation', 'review', 'test', 'docs'],
            'corrections': 0}
    return {'version': 1, 'repository': c.REPOSITORY, 'observed_at': NOW,
            'github': {'default_branch': 'main', 'revision': HEAD,
                       'branches': rows([branch('main'), branch('automation/issue-111-claim-1'),
                                         branch('research/unique-findings'), branch('topic/closed')]),
                       'issues': rows([{'number': 111, 'user': {'login': 'owner'}, 'state': 'open'}]),
                       'pulls': rows([{'number': 112, 'head': {'ref': 'topic/closed'}, 'state': 'closed'}]),
                       'comments': {'111': rows([source])},
                       'details': {'112': {'head': HEAD, 'author': 'implementer', 'merged': False, 'merge_commit': None,
                                           'reviews': rows(), 'checks': rows()}}},
            'goals': [goal], 'local': {'consumed': [1], 'terminal_tasks': [1], 'writer_active': False,
                                     'worktrees': [], 'retained': [], 'dependencies': [], 'preservation': []},
            'movies': None, 'quality': [], 'documentation': []}


def branch(name):
    return {'name': name, 'commit': {'sha': HEAD}, 'protected': False}


def evidence(stage, revision=HEAD, **changes):
    value = {'stage': stage, 'revision': revision, 'observed_at': NOW - 1,
             'reference': 'synthetic-evidence', 'result': 'passed', 'component': None, 'configuration': None}
    value.update(changes)
    return value


def movies():
    """Actual collector export shape, with two distinct occurrences of one movie."""
    cases = []
    for char in ('a', 'b'):
        cases.append({'case_id': 'outcome-' + char * 64, 'version': char * 64,
                      'observed_at': NOW - 10, 'first_observed_at': NOW - 100,
                      'title': 'Synthetic Movie', 'year': 2000, 'route': 'review_only',
                      'reason': 'title_conflict', 'correlation': 'strong_source_id', 'original_type': 'movie',
                      'source_identity': {'imdb': 'tt1234567', 'tmdb': 123, 'asserted_imdb': None, 'asserted_tmdb': None}})
    coverage = dict.fromkeys(('source_releases_observed', 'source_releases_without_outcome', 'outcome_events',
                    'assessed_release_cases', 'existing_unresolved_seeds', 'legacy_outcome_rows_without_chronology',
                    'researching'), 0)
    coverage.update(assessed_release_cases=2, routes={}, correlation={}, counters={},
                    automatic_research_enabled=False, coverage='incomplete')
    export = {'version': 1, 'generated_at': NOW, 'coverage': coverage, 'cases': cases, 'items': []}
    report = {'version': 1, 'generated_at': NOW, 'coverage': coverage, 'cases': deepcopy(cases)}
    report['cases'][0]['proposal'] = {'current_evidence': True, 'created_at': NOW - 10, 'search_candidates': [],
        'result': {'candidates': [{'record': {'id': 321, 'type': 'movie'}}],
                   'evidence': [{'method': 'details', 'query': 321, 'result': {
                       'reason': 'ok', 'data': {'private': 'SYNTHETIC_PRIVATE_RAW https://tracker.invalid/passkey=SYNTHETIC'}}}]}}
    report['cases'][1]['proposal'] = {'current_evidence': False, 'result': {}}
    return export, report


class CoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.s = snapshot()

    def test_actual_parser_called_and_canonical_draft_does_not_consume(self):
        before = deepcopy(self.s)
        with patch.object(c.dispatcher, 'choose_task', wraps=c.dispatcher.choose_task) as parser:
            draft = c.render_task(self.s, 'synthetic-support', 2, 'owner', NOW)
        self.assertGreaterEqual(parser.call_count, 3)
        self.assertEqual(c.task_sections(task(body=draft['body']), 'owner')['GOAL'], self.s['goals'][0]['scope'])
        self.assertEqual(draft['status'], 'draft_only')
        self.assertFalse(draft['number_consumed'])
        self.assertEqual(self.s, before)

    def test_invalid_untrusted_missing_duplicate_fields(self):
        for body in (None, task()['body'].replace('GOAL:', 'NO_GOAL:'),
                     task()['body'] + 'AUTHORIZATION: more\n',
                     task()['body'] + ' goal: disguised duplicate\n',
                     task()['body'] + 'NETWORK_ACCESS: enabled\nNETWORK_ACCESS: disabled\n',
                     task()['body'] + 'PUBLICATION_MODE: mystery\n',
                     task()['body'] + 'PRIVATE_INPUTS: {}\n',
                     task()['body'] + 'SEEDBOX_PERMISSION: read-only\n'):
            with self.subTest(body=body), self.assertRaises((ValueError, PolicyError)):
                c.task_sections(task(body=body), 'owner')
        with self.assertRaisesRegex(ValueError, 'untrusted'):
            c.task_sections(task(author='worker'), 'owner')

    def test_proposed_goal_cannot_authorize(self):
        self.s['github']['comments']['111']['items'][0]['user']['login'] = 'worker'
        report = c.findings(self.s, NOW)
        self.assertEqual(report['goals'][0]['authority'], 'unverified_no_execution')
        self.assertFalse(report['goals'][0]['complete'])
        with self.assertRaises(ValueError):
            c.render_task(self.s, 'synthetic-support', 2, 'owner', NOW)

    def test_authorization_scope_cannot_expand(self):
        self.s['goals'][0]['allowed_actions'] += '\n- Deploy everything.'
        with self.assertRaisesRegex(ValueError, 'scope_changed'):
            c.authorized_goal(self.s['goals'][0], self.s)

    def test_number_and_consumption_ambiguity_outstanding_and_limits(self):
        for modify in (lambda s: s['local'].update(consumed=None),
                       lambda s: s['local'].update(writer_active=None),
                       lambda s: s['local'].update(writer_active=True),
                       lambda s: s['local'].update(terminal_tasks=[]),
                       lambda s: s['local'].update(consumed=[], terminal_tasks=[]),
                       lambda s: s['goals'][0].update(corrections=8),
                       lambda s: s['github']['branches'].update(status='partial'),
                       lambda s: s['github']['comments']['111']['items'].append(task(2)),
                       lambda s: s['github']['branches']['items'].append(branch('automation/issue-111-claim-2'))):
            value = deepcopy(self.s); modify(value)
            with self.subTest(value=value), self.assertRaises((ValueError, PolicyError)):
                c.render_task(value, 'synthetic-support', 2, 'owner', NOW)
        for number in (1, 3, True):
            with self.assertRaises(ValueError):
                c.render_task(self.s, 'synthetic-support', number, 'owner', NOW)

    def test_stale_incomplete_snapshot_not_authoritative(self):
        self.s['goals'][0]['evidence'] = [evidence('implementation')]
        self.s['observed_at'] = NOW - 4000
        report = c.findings(self.s, NOW)
        self.assertEqual(report['freshness'], 'stale')
        self.assertEqual(report['goals'][0]['stages']['implementation']['status'], 'pending')
        with self.assertRaises(ValueError):
            c.render_task(self.s, 'synthetic-support', 2, 'owner', NOW)
        self.s['observed_at'] = NOW
        self.s['github']['comments']['111']['status'] = 'partial'
        self.assertEqual(c.findings(self.s, NOW)['goals'][0]['authority'], 'unverified_no_execution')

    def test_restart_unchanged_and_timestamp_only_change(self):
        state, first = c.reconcile(self.s, c.empty_state(), NOW)
        self.assertTrue(first['changed'])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'state.json'
            c.atomic_save(path, state)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.s['observed_at'] += 10
            state, again = c.reconcile(self.s, c.load(path), NOW + 10)
            self.assertFalse(again['changed']); self.assertIsNone(again['report'])
            self.assertEqual(len(state['proposals']), 1)
            self.assertEqual(state['delivery'], 'not_confirmed')
            self.assertEqual(state['proposals'][0]['status'], 'proposed')

    def test_new_head_invalidates_review_test_and_implementation(self):
        goal = self.s['goals'][0]
        goal['evidence'] = [evidence(stage) for stage in ('implementation', 'review', 'test')]
        detail = self.s['github']['details']['112']
        detail['reviews'] = rows([{'id': 1, 'commit_id': HEAD, 'state': 'APPROVED', 'user': {'login': 'reviewer'}}])
        self.assertEqual(c.findings(self.s, NOW)['goals'][0]['stages']['test']['status'], 'passed')
        detail['head'] = OLD
        stages = c.findings(self.s, NOW)['goals'][0]['stages']
        for stage in ('implementation', 'review', 'test'):
            self.assertEqual(stages[stage]['status'], 'pending')
        goal['evidence'].append(evidence('test', revision=OLD, reference='explicit-current-applicability'))
        self.assertEqual(c.findings(self.s, NOW)['goals'][0]['stages']['test']['status'], 'passed')

    def test_changes_requested_and_partial_review_fail_closed(self):
        detail = self.s['github']['details']['112']
        detail['reviews'] = rows([{'id': i, 'commit_id': HEAD, 'state': state, 'user': {'login': 'reviewer'}}
                                  for i, state in ((1, 'APPROVED'), (2, 'CHANGES_REQUESTED'))])
        self.assertEqual(c.findings(self.s, NOW)['goals'][0]['stages']['review']['status'], 'failed')
        detail['reviews']['status'] = 'partial'
        self.assertEqual(c.findings(self.s, NOW)['goals'][0]['stages']['review']['status'], 'pending')

    def test_ci_only_current_complete_nonempty(self):
        detail = self.s['github']['details']['112']
        detail['checks'] = rows([{'head_sha': OLD, 'status': 'completed', 'conclusion': 'success'}])
        self.assertEqual(c.findings(self.s, NOW)['goals'][0]['stages']['test']['status'], 'pending')
        detail['checks']['items'][0]['head_sha'] = HEAD
        self.assertEqual(c.findings(self.s, NOW)['goals'][0]['stages']['test']['status'], 'pending')
        self.assertIn('task_test_evidence_missing', c.findings(self.s, NOW)['goals'][0]['stages']['test']['reason'])
        detail['checks']['status'] = 'partial'
        self.assertEqual(c.findings(self.s, NOW)['goals'][0]['stages']['test']['status'], 'pending')

    def test_merge_and_ready_never_imply_deployment(self):
        self.s['github']['details']['112'].update(merged=True, merge_commit=OLD)
        self.s['goals'][0]['required_stages'] += ['merge', 'deploy', 'live']
        stages = c.findings(self.s, NOW)['goals'][0]['stages']
        self.assertEqual(stages['merge']['status'], 'passed')
        for stage in ('deploy', 'live'):
            self.assertEqual(stages[stage]['status'], 'pending')
        self.s['goals'][0]['evidence'] = [evidence('deploy'), evidence('live')]
        stages = c.findings(self.s, NOW)['goals'][0]['stages']
        self.assertEqual(stages['deploy']['status'], 'pending')
        self.assertEqual(stages['live']['status'], 'pending')

    def test_components_configuration_and_dated_live_checks(self):
        goal = self.s['goals'][0]; goal['required_stages'] += ['deploy', 'live']
        goal['evidence'] = [evidence('deploy', component='collector', configuration='synthetic-v1'),
                            evidence('live', component='collector', configuration='synthetic-v1', observed_at=NOW-90000)]
        stages = c.findings(self.s, NOW)['goals'][0]['stages']
        self.assertEqual(stages['deploy']['status'], 'passed')
        self.assertEqual(stages['live']['status'], 'pending')

    def test_movie_full_set_and_occurrence_boundaries(self):
        export, report = movies()
        result = c.movie_review(export, report, NOW)
        self.assertEqual(len(result['groups']), 1)
        occurrences = result['groups'][0]['occurrences']
        self.assertEqual(len(occurrences), 2)
        self.assertEqual([o['evidence'] for o in occurrences], ['fresh', 'retained'])
        self.assertEqual(occurrences[0]['candidates'], [{'type': 'movie', 'tmdb': 321}])
        self.assertTrue(all(o['acquisition_approval'] == 'unknown' for o in occurrences))
        report['cases'].pop()
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            c.movie_review(export, report, NOW)

    def test_movie_source_identity_cannot_cross_occurrences(self):
        export, report = movies()
        report['cases'][1]['source_identity']['tmdb'] = 999
        with self.assertRaisesRegex(ValueError, 'occurrence_changed'):
            c.movie_review(export, report, NOW)

    def test_movie_missing_conflicting_and_stale(self):
        export, report = movies()
        report['cases'][0].pop('proposal')
        export['cases'][0]['correlation'] = report['cases'][0]['correlation'] = 'identifier_conflict'
        occurrence = c.movie_review(export, report, NOW)['groups'][0]['occurrences'][0]
        self.assertEqual(occurrence['evidence'], 'missing'); self.assertTrue(occurrence['conflicting'])
        export['generated_at'] -= 4000
        with self.assertRaises(ValueError):
            c.movie_review(export, report, NOW)

    def test_public_output_never_forwards_raw_private_evidence_or_capabilities(self):
        export, report = movies(); self.s['movies'] = {'snapshot': export, 'report': report}
        self.s['goals'][0]['blocker'] = 'SYNTHETIC_PRIVATE_RAW'
        self.s['documentation'] = [{'id': 'task-brief', 'expected': 'private token=SYNTHETIC', 'observed': 'different'}]
        state, output = c.reconcile(self.s, c.empty_state(), NOW)
        raw = json.dumps([state, output])
        for forbidden in ('SYNTHETIC_PRIVATE_RAW', 'tracker.invalid', 'passkey=', 'token=', 'AUTHORIZATION:', 'SEEDBOX_PERMISSION'):
            self.assertNotIn(forbidden, raw)
        self.assertIn('tt1234567', raw)

    def test_partial_score_separate_designs_no_calculation(self):
        row = {'id': 'synthetic-score', 'design': 'historical', 'observed_at': None, 'rating': None,
               'count': None, 'recognition_complete': False, 'score_complete': True,
               'identity_verified': False, 'notification_state': 'confirmed', 'acquisition_approved': True}
        result = c.quality_review([row, dict(row, id='experimental', design='experimental_audience50_recognition50')], NOW)
        self.assertEqual(len(result), 2)
        self.assertIn('partial_score_not_final', result[0]['findings'])
        self.assertIn('missing_rating_evidence', result[0]['findings'])
        self.assertIn('notification_identity_inconsistent', result[0]['findings'])
        self.assertNotIn('score', result[0])

    def test_claim_unique_research_and_closed_pr_protection(self):
        result = {r['branch']: r for r in c.inventory(self.s)['branches']}
        self.assertIn('permanent_claim', result['automation/issue-111-claim-1']['protections'])
        self.assertEqual(result['research/unique-findings']['proposal'], 'retain')
        closed = result['topic/closed']
        self.assertEqual(closed['classification'], 'closed_preservation_unverified')
        self.assertEqual(closed['preservation'], 'unknown')
        self.s['local']['worktrees'] = None
        self.assertIn('worktrees_unknown', c.inventory(self.s)['branches'][-1]['protections'])

    def test_invalid_version_duplicate_json_and_delivery_not_authorization(self):
        self.s['version'] = 2
        with self.assertRaises(ValueError): c.validate_snapshot(self.s)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'input.json'
            path.write_text('{"version":1,"version":1}')
            with self.assertRaises(PolicyError): c.load(path)
        state = c.empty_state(); state['delivery'] = 'confirmed'
        with self.assertRaises(ValueError): c.validate_state(state)

    def test_atomic_failure_preserves_previous_state(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'state.json'
            c.atomic_save(path, {'old': True})
            with patch.object(c.os, 'replace', side_effect=OSError('synthetic failure')):
                with self.assertRaises(OSError): c.atomic_save(path, {'new': True})
            self.assertEqual(c.load(path), {'old': True})
            link = Path(directory) / 'link.json'; link.symlink_to(path)
            with self.assertRaises(ValueError): c.atomic_save(link, {})

    def test_missing_pr_details_and_self_review_never_pass(self):
        self.s['goals'][0]['evidence'] = [evidence('test')]
        self.s['github']['details'] = {}
        self.assertIsNone(c.findings(self.s, NOW)['goals'][0]['head'])
        self.assertEqual(c.findings(self.s, NOW)['goals'][0]['stages']['test']['status'], 'pending')
        self.s = snapshot()
        self.s['github']['details']['112']['reviews'] = rows([{'id': 1, 'commit_id': HEAD,
            'state': 'APPROVED', 'user': {'login': 'implementer'}}])
        self.assertEqual(c.findings(self.s, NOW)['goals'][0]['stages']['review']['status'], 'pending')

    def test_evidence_refresh_only_quiet_but_expiry_changes(self):
        self.s['goals'][0]['required_stages'].append('live')
        self.s['goals'][0]['evidence'] = [evidence('live', component='actor', configuration='test-config'),
                                        evidence('deploy', component='actor', configuration='test-config')]
        state, first = c.reconcile(self.s, c.empty_state(), NOW)
        self.s['goals'][0]['evidence'][0]['observed_at'] += 10
        state, second = c.reconcile(self.s, state, NOW + 10)
        self.assertFalse(second['changed'])
        self.assertTrue(c.reconcile(self.s, state, NOW + 90000)[1]['changed'])

    def test_verified_negative_is_different_from_missing(self):
        export, report = movies()
        report['cases'][0]['proposal']['result']['evidence'] = [
            {'method': 'movie_search', 'result': {'reason': 'ok', 'data': {'results': []}}},
            {'method': 'details', 'result': {'reason': 'rate_limited'}}]
        facts = c.movie_review(export, report, NOW)['groups'][0]['occurrences'][0]['facts']
        self.assertEqual([f['status'] for f in facts], ['verified_negative', 'missing'])

    def test_public_projection_drops_bodies_urls_and_capabilities(self):
        row = task(body=task()['body'] + '\nPRIVATE_INPUTS: synthetic-private\nhttps://tracker.invalid\n')
        projected = c.PublicGitHub.project('/issues/111/comments', row)
        self.assertEqual(projected['body'], 'SUPERVISOR_TASK: 1\nSTATE: READY_FOR_CODEX')
        self.assertNotIn('PRIVATE', json.dumps(projected))
        self.assertNotIn('tracker', json.dumps(projected))

    def test_draft_closed_issue_or_private_text_requires_review(self):
        self.s['github']['issues']['items'][0]['state'] = 'closed'
        with self.assertRaisesRegex(ValueError, 'closed'):
            c.render_task(self.s, 'synthetic-support', 2, 'owner', NOW)
        self.s = snapshot()
        source = self.s['github']['comments']['111']['items'][0]
        source['body'] = source['body'].replace('Inspect the actual diff.', 'Read https://tracker.invalid.')
        self.s['goals'][0]['source']['body_sha256'] = c.fingerprint(source['body'])
        with self.assertRaisesRegex(ValueError, 'privacy_review'):
            c.render_task(self.s, 'synthetic-support', 2, 'owner', NOW)

    def test_duplicate_api_rows_are_not_complete_snapshots(self):
        self.s['github']['branches']['items'].append(branch('main'))
        with self.assertRaisesRegex(ValueError, 'duplicate_api'):
            c.findings(self.s, NOW)

    def test_supplied_stage_subset_cannot_redefine_owner_completion_plan(self):
        self.s['goals'][0]['required_stages'] = ['implementation']
        self.s['goals'][0]['evidence'] = [evidence('implementation')]
        goal = c.findings(self.s, NOW)['goals'][0]
        self.assertEqual(goal['completion_plan'], 'unverified')
        self.assertFalse(goal['complete'])

    def test_completion_requires_all_explicit_owner_bound_stages(self):
        self.s['goals'][0]['evidence'] = [evidence(s) for s in ('implementation', 'test', 'docs')]
        self.s['github']['details']['112']['reviews'] = rows([{'id': 1, 'commit_id': HEAD,
            'state': 'APPROVED', 'user': {'login': 'reviewer'}}])
        goal = c.findings(self.s, NOW)['goals'][0]
        self.assertEqual(goal['completion_plan'], 'owner_bound')
        self.assertTrue(goal['complete'])

    def test_movie_proposal_timestamp_only_is_quiet_and_undated_is_retained(self):
        export, report = movies(); self.s['movies'] = {'snapshot': export, 'report': report}
        state, _ = c.reconcile(self.s, c.empty_state(), NOW)
        report['cases'][0]['proposal']['created_at'] += 1
        self.assertFalse(c.reconcile(self.s, state, NOW)[1]['changed'])
        report['cases'][0]['proposal'].pop('created_at')
        self.assertEqual(c.movie_review(export, report, NOW)['groups'][0]['occurrences'][0]['evidence'], 'retained')

    def test_unrelated_inventory_change_does_not_repeat_completed_stage(self):
        self.s['goals'][0]['evidence'] = [evidence('implementation')]
        state, first = c.reconcile(self.s, c.empty_state(), NOW)
        self.assertEqual(first['summary']['new_completed_stages'], [{'synthetic-support': ['implementation']}])
        self.s['github']['branches']['items'].append(branch('topic/new-observation'))
        state, second = c.reconcile(self.s, state, NOW)
        self.assertEqual(second['changed_sections'], ['inventory'])
        self.assertEqual(second['summary']['new_completed_stages'], [{'synthetic-support': []}])


class GitHubTests(unittest.TestCase):
    def test_pagination_bound_partial_not_absent(self):
        adapter = c.PublicGitHub()
        with patch.object(adapter, 'get', side_effect=[([branch('test')], True)] * 3) as get:
            result = adapter.pages('/branches')
        self.assertEqual(result['status'], 'partial'); self.assertEqual(get.call_count, 3)
        with patch.object(adapter, 'get', side_effect=OSError()):
            self.assertEqual(adapter.pages('/branches'), rows(status='unavailable'))

    def test_midstream_failure_partial(self):
        adapter = c.PublicGitHub()
        with patch.object(adapter, 'get', side_effect=[([branch('test')], True), OSError()]):
            self.assertEqual(adapter.pages('/branches')['status'], 'partial')

    def test_fixed_get_only_no_auth_no_proxy_no_redirect(self):
        adapter = c.PublicGitHub()
        response = io.BytesIO(b'[]'); response.headers = {}
        with patch.object(adapter.opener, 'open', return_value=response) as transport:
            self.assertEqual(adapter.get('/branches'), ([], False))
        request = transport.call_args[0][0]
        self.assertEqual(request.get_method(), 'GET')
        self.assertFalse(request.has_header('Authorization'))
        self.assertTrue(request.full_url.startswith('https://api.github.com/repos/' + c.REPOSITORY + '/'))
        with self.assertRaises(ValueError): adapter.get('https://elsewhere.invalid')
        adapter.requests = 40
        with self.assertRaises(ValueError): adapter.get('/branches')


if __name__ == '__main__':
    unittest.main()
