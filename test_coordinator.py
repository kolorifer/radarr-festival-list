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


def receipt(s, purpose, reference, observed_at, payload, revision=HEAD):
    """Synthetic owner publication; not an assertion of real review by this worker."""
    goal = s['goals'][0]
    value = {'version': 1, 'role': 'independent_supervisor', 'repository': c.REPOSITORY,
             'issue': goal['issue'], 'task': goal['task'], 'pr': goal['pr'], 'source': goal['source'],
             'revision': revision, 'purpose': purpose, 'reference': reference,
             'observed_at': observed_at, 'payload_sha256': c.fingerprint(payload)}
    comments = s['github']['comments'][str(goal['issue'])]['items']
    row = {'id': max(r['id'] for r in comments) + 1, 'user': {'login': 'owner'},
           'body': 'COORDINATOR_RECEIPT: ' + json.dumps(value, sort_keys=True)}
    comments.append(row)
    return {'comment_id': row['id'], 'body_sha256': c.fingerprint(row['body'])}


def bind_ci(s, observation):
    resolution = observation['ci_resolution']
    resolution['supervisor_receipt'] = receipt(s, 'ci_applicability', resolution['reference'],
                                              resolution['observed_at'], c.ci_payload(observation),
                                              observation['revision'])


def bind_review(s, observation):
    observation['supervisor_receipt'] = receipt(s, 'review', observation['reference'],
        observation['observed_at'], {'result': observation['result']}, observation['revision'])


def quality(**changes):
    value = {'id': 'synthetic-notification', 'design': 'historical', 'observed_at': NOW,
             'rating': 7, 'count': 100, 'recognition_complete': True, 'score_complete': True,
             'identity_verified': False, 'notification_state': 'confirmed',
             'notification_type': 'informational', 'action_eligible': False, 'acquisition_approved': False}
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

    def test_current_head_failed_ci_conflicts_with_supplied_pass(self):
        goal = self.s['goals'][0]
        goal['evidence'] = [evidence(s) for s in ('implementation', 'test', 'docs')]
        detail = self.s['github']['details']['112']
        detail['reviews'] = rows([{'id': 1, 'commit_id': HEAD, 'state': 'APPROVED',
                                  'user': {'login': 'reviewer'}}])
        detail['checks'] = rows([{'head_sha': HEAD, 'status': 'completed', 'conclusion': 'failure'}])
        result = c.findings(self.s, NOW)['goals'][0]
        self.assertFalse(result['complete'])
        self.assertEqual(result['stages']['test']['status'], 'pending')
        self.assertEqual(result['stages']['test']['ci']['failed'], 1)
        self.assertEqual(result['stages']['review']['status'], 'passed')
        self.assertEqual(result['stages']['merge']['status'], 'not_applicable')
        self.assertEqual(result['stages']['deploy']['status'], 'not_applicable')
        state, _ = c.reconcile(self.s, c.empty_state(), NOW)
        c.validate_state(state)
        self.assertFalse(c.reconcile(self.s, state, NOW)[1]['changed'])
        detail['checks']['items'][0]['conclusion'] = 'success'
        self.assertTrue(c.findings(self.s, NOW)['goals'][0]['complete'])

    def test_pending_partial_and_unavailable_ci_block_supplied_pass(self):
        self.s['goals'][0]['evidence'] = [evidence('test')]
        for status, runs in (
                ('complete', [{'head_sha': HEAD, 'status': 'in_progress', 'conclusion': None}]),
                ('complete', [{'head_sha': HEAD, 'status': 'completed', 'conclusion': 'success'},
                              {'head_sha': HEAD, 'status': 'queued', 'conclusion': None}]),
                ('partial', [{'head_sha': HEAD, 'status': 'completed', 'conclusion': 'success'}]),
                ('unavailable', [])):
            with self.subTest(status=status, runs=runs):
                self.s['github']['details']['112']['checks'] = rows(runs, status)
                result = c.findings(self.s, NOW)['goals'][0]['stages']['test']
                self.assertEqual(result['status'], 'pending')
                self.assertEqual(result['ci']['result'], 'incomplete')

    def test_successful_ci_supplements_current_tests_but_not_prior_head(self):
        self.s['github']['details']['112']['checks'] = rows([
            {'head_sha': HEAD, 'status': 'completed', 'conclusion': 'success'},
            {'head_sha': OLD, 'status': 'completed', 'conclusion': 'failure'}])
        self.s['goals'][0]['evidence'] = [evidence('test')]
        result = c.findings(self.s, NOW)['goals'][0]['stages']['test']
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(result['ci']['other_head'], 1)
        self.s['goals'][0]['evidence'][0]['revision'] = OLD
        self.assertEqual(c.findings(self.s, NOW)['goals'][0]['stages']['test']['status'], 'pending')

    def test_ci_conflict_requires_bound_independent_dated_applicability(self):
        detail = self.s['github']['details']['112']
        detail['checks'] = rows([{'head_sha': HEAD, 'status': 'completed', 'conclusion': 'failure'}])
        resolution = {'checks_fingerprint': c.fingerprint({'head': HEAD, 'checks': detail['checks']}),
                      'observed_at': NOW, 'reference': 'independent-applicability-artifact',
                      'reviewer': 'independent-reviewer', 'disposition': 'unrelated'}
        self.s['goals'][0]['evidence'] = [evidence('test', ci_resolution=resolution)]
        bind_ci(self.s, self.s['goals'][0]['evidence'][0])
        result = c.findings(self.s, NOW)['goals'][0]['stages']['test']
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(result['ci']['result'], 'failed')  # Never rewrite GitHub's observation.
        self.assertEqual(result['ci']['resolution'], 'unrelated')
        for change in ({'reviewer': 'implementer'}, {'observed_at': NOW-2}, {'observed_at': NOW+1},
                       {'checks_fingerprint': '0'*64}, {'reference': 'synthetic-evidence'}):
            with self.subTest(change=change):
                self.s['goals'][0]['evidence'][0]['ci_resolution'] = dict(resolution, **change)
                self.assertEqual(c.findings(self.s, NOW)['goals'][0]['stages']['test']['status'], 'pending')
        self.s['goals'][0]['evidence'][0]['ci_resolution'] = resolution
        detail['checks']['status'] = 'partial'
        resolution['checks_fingerprint'] = c.fingerprint({'head': HEAD, 'checks': detail['checks']})
        self.assertEqual(c.findings(self.s, NOW)['goals'][0]['stages']['test']['status'], 'pending')
        detail['checks']['status'] = 'complete'
        resolution['checks_fingerprint'] = c.fingerprint({'head': HEAD, 'checks': detail['checks']})
        resolution['disposition'] = 'superseded'
        self.assertEqual(c.findings(self.s, NOW)['goals'][0]['stages']['test']['status'], 'pending')
        self.s['goals'][0]['evidence'][0]['observed_at'] = NOW
        bind_ci(self.s, self.s['goals'][0]['evidence'][0])
        self.assertEqual(c.findings(self.s, NOW)['goals'][0]['stages']['test']['status'], 'passed')
        self.s['goals'][0]['evidence'][0]['result'] = 'failed'
        self.assertEqual(c.findings(self.s, NOW)['goals'][0]['stages']['test']['status'], 'failed')
        self.s['goals'][0]['evidence'][0]['result'] = 'passed'
        self.s['observed_at'] += 1
        self.assertEqual(c.findings(self.s, NOW+1)['goals'][0]['stages']['test']['status'], 'pending')

    def test_ci_resolution_schema_rejects_undated_or_unsupported_assertions(self):
        base = {'checks_fingerprint': '0'*64, 'observed_at': NOW,
                'reference': 'independent-artifact', 'reviewer': 'reviewer', 'disposition': 'unrelated'}
        invalid = [dict(base, disposition='ignore'), dict(base, observed_at=None),
                   dict(base, checks_fingerprint='bad'), dict(base, extra=True),
                   {k: v for k, v in base.items() if k != 'reviewer'}]
        for resolution in invalid:
            with self.subTest(resolution=resolution), self.assertRaises(ValueError):
                self.s['goals'][0]['evidence'] = [evidence('test', ci_resolution=resolution)]
                c.validate_snapshot(self.s)

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
        self.assertIn('notification_action_evidence_unknown', result[0]['findings'])
        self.assertIn('approval_identity_inconsistent', result[0]['findings'])
        self.assertNotIn('score', result[0])

    def test_delivered_unknown_movie_is_informational_with_unresolved_identity(self):
        result = c.quality_review([quality()], NOW)[0]
        self.assertEqual(result['findings'], [])
        self.assertEqual(result['delivery'], 'confirmed')
        self.assertFalse(result['identity_verified'])
        self.assertFalse(result['action_eligible'])
        self.assertFalse(result['acquisition_approved'])
        review = quality(notification_type='identity_review')
        self.assertEqual(c.quality_review([review], NOW)[0]['findings'], [])

    def test_verified_action_eligibility_does_not_imply_acquisition_approval(self):
        row = quality(identity_verified=True, notification_type='acquisition', action_eligible=True)
        result = c.quality_review([row], NOW)[0]
        self.assertEqual(result['findings'], [])
        self.assertFalse(result['acquisition_approved'])
        row['acquisition_approved'] = True
        self.assertEqual(c.quality_review([row], NOW)[0]['findings'], [])

    def test_unresolved_acquisition_action_and_approval_are_separate_findings(self):
        row = quality(notification_type='acquisition', action_eligible=True)
        self.assertEqual(c.quality_review([row], NOW)[0]['findings'], ['actionable_identity_unverified'])
        row['acquisition_approved'] = True
        self.assertEqual(c.quality_review([row], NOW)[0]['findings'],
                         ['actionable_identity_unverified', 'approval_identity_inconsistent'])
        row.update(notification_type='informational', action_eligible=False)
        self.assertEqual(c.quality_review([row], NOW)[0]['findings'], ['approval_identity_inconsistent'])

    def test_unknown_notification_eligibility_stays_unknown_and_invalid_fields_fail(self):
        row = quality(); row.pop('notification_type'); row.pop('action_eligible')
        result = c.quality_review([row], NOW)[0]
        self.assertEqual(result['findings'], ['notification_action_evidence_unknown'])
        self.assertIsNone(result['action_eligible'])
        for changes in ({'action_eligible': 1}, {'notification_type': 'arbitrary'}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                c.quality_review([quality(**changes)], NOW)
        self.assertIn('acquisition_action_ineligible', c.quality_review([
            quality(identity_verified=True, notification_type='acquisition')], NOW)[0]['findings'])
        self.assertIn('notification_action_inconsistent', c.quality_review([
            quality(identity_verified=True, action_eligible=True)], NOW)[0]['findings'])

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


class CorrectionTests(unittest.TestCase):
    def setUp(self):
        self.s = snapshot()

    def result(self):
        return c.findings(self.s, NOW)['goals'][0]

    def comments(self):
        return self.s['github']['comments']['111']['items']

    def test_normal_claim_terminal_lifecycle_all_terminal_states(self):
        for state in ('READY_FOR_REVIEW', 'FAILED', 'NEEDS_USER'):
            with self.subTest(state=state):
                self.s = snapshot()
                self.comments().extend([task(id=2, body='SUPERVISOR_TASK: 1\nSTATE: RUNNING'),
                    task(id=3, body='WORKER_RESULT: 1\nSTATE: ' + state)])
                consumed = c.dispatcher.remote_consumed(self.comments(), {'owner'})
                self.assertIsNone(c.dispatcher.choose_task(self.comments(), 'owner', consumed))
                self.assertEqual(c.findings(self.s, NOW)['tasks'][0]['state'], state)
                self.assertEqual(c.findings(self.s, NOW)['tasks'][0]['worker_liveness'], 'unknown')
                self.assertEqual(c.render_task(self.s, 'synthetic-support', 2, 'owner', NOW)['status'], 'draft_only')
                self.assertEqual(self.result()['authority'], 'owner_task_bound')

    def test_latest_result_not_an_older_tasks_late_result(self):
        self.comments().extend([task(2), task(id=3, body='SUPERVISOR_TASK: 2\nSTATE: RUNNING'),
                               task(id=4, body='WORKER_RESULT: 1\nSTATE: FAILED')])
        report = c.findings(self.s, NOW)
        self.assertEqual(report['tasks'][0]['latest_owner_task'], 2)
        self.assertEqual(report['tasks'][0]['state'], 'RUNNING')
        self.comments().extend([task(id=5, body='WORKER_RESULT: 2\nSTATE: FAILED'),
                               task(id=6, body='WORKER_RESULT: 2\nSTATE: READY_FOR_REVIEW')])
        self.assertEqual(c.findings(self.s, NOW)['tasks'][0]['state'], 'READY_FOR_REVIEW')
        with self.assertRaises(ValueError): c.render_task(self.s, 'synthetic-support', 3, 'owner', NOW)

    def test_duplicate_conflicting_partial_lifecycle_records_refuse_drafts(self):
        for body in ('WORKER_RESULT: 1\nSTATE: FAILED\nSTATE: READY_FOR_REVIEW',
                     'WORKER_RESULT: 1', 'SUPERVISOR_TASK: 1\nWORKER_RESULT: 1\nSTATE: FAILED',
                     'SUPERVISOR_TASK: 1', 'WORKER_RESULT: unknown', 'WORKER_RESULT: 01\nSTATE: FAILED',
                     'SUPERVISOR_TASK: 1\nSTATE: RUNNING\n state: READY_FOR_CODEX', task()['body']):
            with self.subTest(body=body):
                self.s = snapshot(); self.comments().append(task(id=2, body=body))
                self.assertEqual(c.findings(self.s, NOW)['tasks'][0]['state'], 'unknown')
                with self.assertRaises((ValueError, PolicyError)):
                    c.render_task(self.s, 'synthetic-support', 2, 'owner', NOW)
        self.s = snapshot(); self.s['github']['comments']['111']['status'] = 'partial'
        self.assertEqual(c.findings(self.s, NOW)['tasks'][0]['state'], 'unknown')

    def test_public_projection_keeps_ambiguity_and_failed_terminal_metadata(self):
        row = task(id=2, body='WORKER_RESULT: 1\nSTATE: FAILED\nSTATE: READY_FOR_REVIEW\nhttps://private.invalid')
        projected = c.PublicGitHub.project('/issues/111/comments', row)
        self.assertEqual(projected['body'], 'WORKER_RESULT: 1\nSTATE: UNKNOWN')
        self.assertNotIn('private.invalid', json.dumps(projected))
        self.comments().append(projected)
        self.assertEqual(c.findings(self.s, NOW)['tasks'][0]['state'], 'unknown')
        row['body'] = 'WORKER_RESULT: 1\nSTATE: FAILED'
        self.comments()[-1] = c.PublicGitHub.project('/issues/111/comments', row)
        self.assertEqual(c.findings(self.s, NOW)['tasks'][0]['state'], 'FAILED')

    def test_terminal_metadata_does_not_replace_local_execution_or_consumption(self):
        self.comments().append(task(id=2, body='WORKER_RESULT: 1\nSTATE: READY_FOR_REVIEW'))
        for changes in ({'writer_active': None}, {'writer_active': True}, {'terminal_tasks': []}, {'consumed': None}):
            self.s['local'] = dict(snapshot()['local'], **changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                c.render_task(self.s, 'synthetic-support', 2, 'owner', NOW)
        self.s['local'] = snapshot()['local']
        self.comments().append(task(id=3, body='WORKER_RESULT: 2\nSTATE: FAILED'))
        with self.assertRaises(ValueError): c.render_task(self.s, 'synthetic-support', 2, 'owner', NOW)

    def test_failed_or_ambiguous_result_blocks_completion_but_keeps_stage_facts(self):
        for body in ('WORKER_RESULT: 1\nSTATE: FAILED', 'WORKER_RESULT: 1\nSTATE: NEEDS_USER',
                     'WORKER_RESULT: 1\nSTATE: FAILED\nSTATE: READY_FOR_REVIEW'):
            with self.subTest(body=body):
                self.s = snapshot(); self.passing_plan()
                self.comments().append(task(id=2, body=body))
                self.assertFalse(self.result()['complete'])
                self.assertTrue(self.result()['blocked'])
                self.assertEqual(self.result()['stages']['test']['status'], 'passed')

    def passing_plan(self):
        self.s['goals'][0]['evidence'] = [evidence(stage) for stage in ('implementation', 'test', 'docs')]
        self.s['github']['details']['112']['reviews'] = rows([
            {'id': 1, 'commit_id': HEAD, 'state': 'APPROVED', 'user': {'login': 'reviewer'}}])
        self.assertTrue(self.result()['complete'])

    def test_superseding_revoking_corrective_or_unclear_instructions_block_old_completion(self):
        for scope in ('Stop and revoke the previous plan.', 'Revise previous acceptance criteria.',
                      'Correct the remaining implementation findings.', 'Implement a later unrelated objective.',
                      'Implement synthetic coordinator support.'):
            with self.subTest(scope=scope):
                self.s = snapshot(); self.passing_plan()
                self.comments().append(task(2, body=task(2)['body'].replace('Implement synthetic coordinator support.', scope)))
                self.assertEqual(c.dispatcher.task_number(c.dispatcher.choose_task(self.comments(), 'owner', {1})['body']), 2)
                result = self.result()
                self.assertFalse(result['complete'])
                self.assertEqual(result['authority_reason'], 'authorization_newer_instructions_require_rebinding')
                self.assertEqual(result['stages']['test']['evidence'], ['synthetic-evidence'])

    def test_status_results_and_untrusted_later_text_do_not_supersede_scope(self):
        self.passing_plan()
        self.comments().extend([task(id=2, body='SUPERVISOR_TASK: 1\nSTATE: RUNNING'),
            task(id=3, body='WORKER_RESULT: 1\nSTATE: READY_FOR_REVIEW'),
            task(2, author='outsider', id=4), task(id=5, body='Stop the previous goal (unbound prose).')])
        self.assertTrue(self.result()['complete'])
        self.s['github']['comments']['111']['status'] = 'partial'
        self.assertFalse(self.result()['complete'])

    def test_latest_rebound_goal_and_nonready_scope_barrier(self):
        self.passing_plan()
        latest = task(2); self.comments().append(latest)
        self.s['goals'][0].update(task=2, source={'comment_id': 2, 'body_sha256': c.fingerprint(latest['body'])})
        self.assertTrue(self.result()['complete'])
        # A scope-bearing non-ready task blocks the dispatcher's selection too.
        self.comments().append(task(3, body=task(3)['body'].replace('READY_FOR_CODEX', 'DONE')))
        self.assertIsNone(c.dispatcher.choose_task(self.comments(), 'owner', set()))
        self.assertFalse(self.result()['complete'])

    def deployed_plan(self):
        self.passing_plan()
        goal = self.s['goals'][0]
        source = self.comments()[0]
        source['body'] = source['body'].replace('implementation,review,test,docs', 'implementation,review,test,docs,deploy,live')
        goal['source']['body_sha256'] = c.fingerprint(source['body'])
        goal['required_stages'] += ['deploy', 'live']
        goal['evidence'] += [evidence('deploy', component='actor', configuration='config-a', observed_at=NOW-30),
                             evidence('live', component='actor', configuration='config-a', observed_at=NOW-20)]
        self.assertTrue(self.result()['complete'])
        return goal

    def test_later_rollback_invalidates_current_deploy_live_without_erasing_history(self):
        goal = self.deployed_plan()
        goal['evidence'] += [evidence(stage, revision=OLD, component='actor', configuration='config-b', observed_at=NOW-t)
                             for stage, t in (('deploy', 10), ('live', 1))]
        result = self.result(); self.assertFalse(result['complete'])
        for stage in ('deploy', 'live'):
            self.assertEqual(result['stages'][stage]['status'], 'pending')
            self.assertEqual(result['stages'][stage]['observations'][0]['revision'], OLD)
            self.assertEqual(len(result['stages'][stage]['history']), 4)

    def test_configuration_replacement_needs_a_new_live_check(self):
        goal = self.deployed_plan()
        goal['evidence'].append(evidence('deploy', component='actor', configuration='config-b', observed_at=NOW-10))
        result = self.result()
        self.assertEqual(result['stages']['deploy']['status'], 'passed')
        self.assertEqual(result['stages']['deploy']['observations'][0]['configuration'], 'config-b')
        self.assertEqual(result['stages']['live']['status'], 'pending')
        goal['evidence'].append(evidence('live', component='actor', configuration='config-b', observed_at=NOW-1))
        self.assertTrue(self.result()['complete'])

    def test_live_must_postdate_latest_deployment_and_not_be_stale(self):
        goal = self.deployed_plan()
        goal['evidence'].append(evidence('deploy', component='actor', configuration='config-a', observed_at=NOW-10))
        self.assertEqual(self.result()['stages']['live']['status'], 'pending')
        for observation in goal['evidence']:
            if observation['stage'] in ('deploy', 'live'):
                observation['observed_at'] = NOW-90000 if observation['stage'] == 'live' else NOW-90001
        self.assertEqual(self.result()['stages']['live']['status'], 'pending')

    def lineage(self, goal):
        detail = self.s['github']['details']['112']; detail.update(merged=True, merge_commit=OLD)
        deployment = goal['evidence'][-2]; deployment['revision'] = OLD
        goal['evidence'][-1]['revision'] = OLD
        deployment['merged_from'] = {'revision': HEAD, 'receipt': receipt(self.s, 'merge_lineage',
            deployment['reference'], deployment['observed_at'], {'deployed_revision': OLD, 'component': 'actor',
            'configuration': 'config-a', 'merge_commit': OLD})}
        return detail, deployment

    def test_verified_merge_or_squash_lineage_allows_actual_deployed_revision(self):
        goal = self.deployed_plan(); detail, deployment = self.lineage(goal)
        self.assertTrue(self.result()['complete'])
        self.assertEqual(self.result()['stages']['deploy']['observations'][0]['revision'], OLD)
        self.assertEqual(self.result()['head'], HEAD)
        # Removing review still leaves deployed/merged facts separate from review.
        detail['reviews'] = rows()
        self.assertEqual(self.result()['stages']['deploy']['status'], 'passed')
        self.assertFalse(self.result()['complete'])

    def test_missing_unrelated_conflicting_or_prospective_lineage_remains_pending(self):
        for change in ('missing', 'unmerged', 'different_merge', 'wrong_head', 'untrusted_receipt'):
            with self.subTest(change=change):
                self.s = snapshot(); goal = self.deployed_plan(); detail, deployment = self.lineage(goal)
                if change == 'missing': deployment.pop('merged_from')
                if change == 'unmerged': detail['merged'] = False
                if change == 'different_merge': detail['merge_commit'] = 'c'*40
                if change == 'wrong_head': deployment['merged_from']['revision'] = 'c'*40
                if change == 'untrusted_receipt': self.comments()[-1]['user']['login'] = 'worker'
                result = self.result()
                self.assertFalse(result['complete'])
                self.assertEqual(result['stages']['deploy']['status'], 'pending')
                self.assertEqual(result['stages']['live']['status'], 'pending')

    def test_conflicting_latest_deployments_and_multiple_components_are_conservative(self):
        goal = self.deployed_plan()
        goal['evidence'].append(evidence('deploy', component='actor', configuration='config-b', observed_at=NOW-30))
        self.assertEqual(self.result()['stages']['deploy']['status'], 'pending')
        goal['evidence'].pop()
        goal['evidence'].append(evidence('deploy', component='collector', configuration='config-a', observed_at=NOW-1))
        self.assertEqual(self.result()['stages']['deploy']['status'], 'passed')
        self.assertEqual(self.result()['stages']['live']['status'], 'pending')

    def test_same_owner_supervisor_receipt_survives_empty_github_reviews(self):
        self.s['github']['details']['112']['author'] = 'owner'
        observation = evidence('review'); bind_review(self.s, observation)
        self.s['goals'][0]['evidence'] = [observation]
        result = self.result()['stages']['review']
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(result['evidence'], ['synthetic-evidence'])
        state, _ = c.reconcile(self.s, c.empty_state(), NOW)
        c.validate_state(state)
        self.assertFalse(c.reconcile(self.s, state, NOW)[1]['changed'])

    def test_review_receipts_require_bound_independent_provenance(self):
        for change in ('no_receipt', 'worker_author', 'worker_role', 'different_source', 'different_revision',
                       'different_result', 'changed_body', 'unknown_comment', 'future', 'different_task',
                       'boolean_task', 'boolean_source', 'boolean', 'list'):
            with self.subTest(change=change):
                self.s = snapshot(); observation = evidence('review'); bind_review(self.s, observation)
                self.s['goals'][0]['evidence'] = [observation]
                row = self.comments()[-1]; payload = json.loads(row['body'].split(': ', 1)[1])
                if change == 'no_receipt': observation.pop('supervisor_receipt')
                if change == 'worker_author': row['user']['login'] = 'implementer'
                if change == 'worker_role': payload['role'] = 'worker'
                if change == 'different_source': payload['source']['body_sha256'] = '0'*64
                if change == 'different_revision': payload['revision'] = OLD
                if change == 'different_result': observation['result'] = 'failed'
                if change == 'changed_body': row['body'] += ' '
                if change == 'unknown_comment': observation['supervisor_receipt']['comment_id'] = 999
                if change == 'future': observation['observed_at'] = NOW+1; bind_review(self.s, observation)
                if change == 'different_task': payload['task'] = 2
                if change == 'boolean_task': payload['task'] = True
                if change == 'boolean_source': payload['source']['comment_id'] = True
                if change == 'boolean': payload = {'approved': True}
                if change == 'list': payload = []
                if change in ('worker_role', 'different_source', 'different_revision', 'different_task',
                              'boolean_task', 'boolean_source', 'boolean', 'list'):
                    row['body'] = 'COORDINATOR_RECEIPT: ' + json.dumps(payload)
                    observation['supervisor_receipt']['body_sha256'] = c.fingerprint(row['body'])
                self.assertEqual(self.result()['stages']['review']['status'], 'pending')

    def test_conflicting_supervisor_receipts_at_same_time_remain_failed(self):
        passed = evidence('review'); bind_review(self.s, passed)
        failed = evidence('review', result='failed', reference='correction-required'); bind_review(self.s, failed)
        self.s['goals'][0]['evidence'] = [passed, failed]
        self.assertEqual(self.result()['stages']['review']['status'], 'failed')
        self.s['goals'][0]['evidence'].reverse()
        self.assertEqual(self.result()['stages']['review']['status'], 'failed')

    def test_receipt_cannot_hide_head_change_conflicts_or_incomplete_reads(self):
        observation = evidence('review'); bind_review(self.s, observation)
        self.s['goals'][0]['evidence'] = [observation]
        detail = self.s['github']['details']['112']; detail['author'] = 'owner'
        detail['reviews'] = rows([{'id': 1, 'commit_id': HEAD, 'state': 'APPROVED', 'user': {'login': 'owner'}}])
        self.assertEqual(self.result()['stages']['review']['status'], 'passed')
        detail['reviews']['items'].append({'id': 2, 'commit_id': HEAD, 'state': 'CHANGES_REQUESTED',
                                          'user': {'login': 'owner'}})
        self.assertEqual(self.result()['stages']['review']['status'], 'failed')
        detail['reviews']['status'] = 'partial'
        self.assertEqual(self.result()['stages']['review']['status'], 'pending')
        detail['reviews'] = rows(); detail['head'] = OLD
        self.assertEqual(self.result()['stages']['review']['status'], 'pending')
        detail['head'] = HEAD; self.s['github']['comments']['111']['status'] = 'partial'
        self.assertEqual(self.result()['stages']['review']['status'], 'pending')

    def test_ci_uses_supervisor_receipt_even_through_shared_owner_account(self):
        detail = self.s['github']['details']['112']; detail['author'] = 'owner'
        detail['checks'] = rows([{'head_sha': HEAD, 'status': 'completed', 'conclusion': 'failure'}])
        observation = evidence('test', ci_resolution={'checks_fingerprint': c.fingerprint({'head': HEAD, 'checks': detail['checks']}),
            'observed_at': NOW, 'reference': 'separate-ci-inspection', 'reviewer': 'owner', 'disposition': 'unrelated'})
        self.s['goals'][0]['evidence'] = [observation]
        self.assertEqual(self.result()['stages']['test']['status'], 'pending')
        bind_ci(self.s, observation)
        self.assertEqual(self.result()['stages']['test']['status'], 'passed')
        observation['reference'] = 'worker-replaced-test-artifact'
        self.assertEqual(self.result()['stages']['test']['status'], 'pending')

    def movie_fixture(self):
        export, report = movies()
        self.s['movies'] = {'snapshot': export, 'report': report}
        proposal = report['cases'][0]['proposal']
        record = {'id': 321, 'type': 'movie', 'runtime': 90, 'date': '2000-01-01', 'year': 2000,
                  'imdb': 'tt1234567', 'title': 'Synthetic Candidate'}
        proposal['result']['candidates'][0].update(record=deepcopy(record), confidence='review_required')
        proposal['result']['evidence'][0]['result']['data'] = deepcopy(record)
        return export, report, proposal

    def material_change(self, change):
        export, report, proposal = self.movie_fixture()
        state, _ = c.reconcile(self.s, c.empty_state(), NOW)
        change(export, report, proposal)
        _, output = c.reconcile(self.s, state, NOW)
        self.assertTrue(output['changed'])
        self.assertIn('movies', output['changed_sections'])
        return output

    def test_movie_runtime_change_is_material(self):
        def change(export, report, proposal):
            proposal['result']['candidates'][0]['record']['runtime'] = 120
            proposal['result']['evidence'][0]['result']['data']['runtime'] = 120
        self.material_change(change)

    def test_movie_date_change_is_material(self):
        self.material_change(lambda e, r, p: p['result']['evidence'][0]['result']['data'].update(date='2001-01-01'))

    def test_movie_candidate_year_change_is_material(self):
        self.material_change(lambda e, r, p: p['result']['candidates'][0]['record'].update(year=2001))

    def test_movie_crosswalk_change_is_material(self):
        self.material_change(lambda e, r, p: p['result']['evidence'][0]['result']['data'].update(imdb='tt7654321'))

    def test_movie_confidence_change_is_material(self):
        self.material_change(lambda e, r, p: p['result']['candidates'][0].update(confidence='search_only_unverified'))

    def test_movie_query_association_change_is_material(self):
        self.material_change(lambda e, r, p: p['result']['evidence'][0].update(query=322))

    def test_movie_search_query_candidate_association_is_material_and_private(self):
        export, report, proposal = self.movie_fixture()
        proposal['result']['evidence'].append({'method': 'movie_search', 'query': 'Synthetic Private Query',
            'result': {'reason': 'ok', 'data': {'results': [proposal['result']['candidates'][0]['record']]}}})
        state, first = c.reconcile(self.s, c.empty_state(), NOW)
        proposal['result']['evidence'][-1]['query'] = 'Different Private Query'
        state, second = c.reconcile(self.s, state, NOW)
        self.assertTrue(second['changed'])
        self.assertNotIn('Private Query', json.dumps(second))
        self.assertNotIn('Synthetic Candidate', json.dumps(second))
        self.assertNotIn('Synthetic Movie', json.dumps(state))

    def test_movie_evidence_timestamp_refresh_and_restart_are_quiet_and_private(self):
        export, report, proposal = self.movie_fixture()
        proposal['private'] = 'SYNTHETIC_PRIVATE_RAW https://tracker.invalid/passkey=SYNTHETIC'
        state, first = c.reconcile(self.s, c.empty_state(), NOW)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'state.json'; c.atomic_save(path, state)
            self.s['observed_at'] += 1; export['generated_at'] += 1; report['generated_at'] += 1
            proposal['created_at'] += 1
            proposal['result']['evidence'][0]['observed_at'] = NOW
            state, second = c.reconcile(self.s, c.load(path), NOW+1)
            self.assertFalse(second['changed']); self.assertIsNone(second['report'])
            for private in ('SYNTHETIC_PRIVATE_RAW', 'tracker.invalid', 'passkey=', 'Synthetic Candidate'):
                self.assertNotIn(private, json.dumps(first) + json.dumps(state))
            proposal['result']['candidates'][0]['record']['runtime'] = 120
            self.assertTrue(c.reconcile(self.s, c.load(path), NOW+1)[1]['changed'])

    def test_movie_material_invalid_fields_fail_without_echoing_content(self):
        for key, value in (('runtime', 'private'), ('year', True), ('imdb', 'https://private.invalid'),
                           ('date', 'https://private.invalid')):
            with self.subTest(key=key):
                self.s = snapshot(); export, report, proposal = self.movie_fixture()
                proposal['result']['candidates'][0]['record'][key] = value
                with self.assertRaises(ValueError) as error: c.findings(self.s, NOW)
                self.assertNotIn('private', str(error.exception))


class GitHubTests(unittest.TestCase):
    def test_selected_pr_head_reviews_checks_and_projection(self):
        adapter = c.PublicGitHub()
        def get(path):
            if path == '/pulls/112':
                return {'number': 112, 'state': 'open', 'head': {'sha': HEAD, 'ref': 'automation/issue-111-worker'},
                        'user': {'login': 'implementer'}, 'merged': False, 'merge_commit_sha': None,
                        'body': 'UNPROJECTED'}, False
            if path == '/issues/111':
                return {'number': 111, 'state': 'open', 'user': {'login': 'owner'}}, False
            if path.startswith('/pulls/112/reviews?'):
                return [{'id': 1, 'commit_id': HEAD, 'state': 'APPROVED', 'user': {'login': 'reviewer'},
                         'body': 'UNPROJECTED'}], False
            if path.startswith('/commits/' + HEAD + '/check-runs?'):
                return {'check_runs': [{'head_sha': HEAD, 'status': 'completed', 'conclusion': 'success',
                                        'output': 'UNPROJECTED'}]}, False
            if path == '':
                return {'default_branch': 'main'}, False
            if path == '/commits/main':
                return {'sha': OLD}, False
            return [], False
        with patch.object(adapter, 'get', side_effect=get) as transport:
            result = adapter.snapshot(issues=(111,), pulls=(112,))
        detail = result['github']['details']['112']
        self.assertEqual(detail['head'], HEAD)
        self.assertEqual(detail['reviews']['items'][0]['commit_id'], HEAD)
        self.assertEqual(detail['checks']['items'][0]['head_sha'], HEAD)
        self.assertEqual(result['github']['pulls']['items'][0]['number'], 112)
        self.assertEqual(list(result['github']['comments']), ['111'])
        self.assertNotIn('UNPROJECTED', json.dumps(result))
        self.assertNotIn('/pulls/110', [call.args[0] for call in transport.call_args_list])

    def test_cli_selection_defaults_and_validation_before_network(self):
        with tempfile.TemporaryDirectory() as directory:
            args = ['snapshot', '--output', str(Path(directory) / 'snapshot.json')]
            with patch.object(c.PublicGitHub, 'snapshot', return_value=snapshot()) as read, patch('builtins.print'):
                self.assertEqual(c.main(args), 0)
                read.assert_called_once_with(issues=(111, 86), pulls=(110,))
                read.reset_mock()
                self.assertEqual(c.main(args + ['--issue', '111', '--pr', '112']), 0)
                read.assert_called_once_with(issues=(111,), pulls=(112,))
            for extra in (['--pr', 'https://example.invalid'], ['--pr', '0'], ['--issue', '-1'],
                          ['--pr', '01'], ['--pr', '2147483648'], ['--pr', '1.2'],
                          ['--pr', '112', '--pr', '112'], ['--issue', '111', '--issue', '111'],
                          ['--pr', '1', '--pr', '2', '--pr', '3'],
                          ['--issue', '1', '--issue', '2', '--issue', '3']):
                with self.subTest(extra=extra), patch.object(c.PublicGitHub, 'get') as network, \
                        patch('sys.stderr', new_callable=io.StringIO), patch('builtins.print'):
                    try:
                        self.assertEqual(c.main(args + extra), 1)
                    except SystemExit as error:
                        self.assertEqual(error.code, 2)
                    network.assert_not_called()
        for options in ({'pulls': (True,)}, {'issues': (111, 111)}, {'pulls': (1, 2, 3)},
                        {'pulls': (2**31,)}):
            with self.subTest(options=options), patch.object(c.PublicGitHub, 'get') as network:
                with self.assertRaises(ValueError): c.PublicGitHub().snapshot(**options)
                network.assert_not_called()

    def test_selected_pr_failure_stays_unknown(self):
        adapter = c.PublicGitHub()
        with patch.object(adapter, 'get', side_effect=OSError()):
            result = adapter.snapshot(issues=(111,), pulls=(112,))
        self.assertNotIn('112', result['github']['details'])
        self.assertEqual(result['github']['pulls']['status'], 'partial')

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
