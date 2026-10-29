"""Read-only Movie Project support. No executor, credentials or publication API."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile
import time
import urllib.error
import urllib.request

from automation import github_worker as dispatcher
from automation.supervisor_policy import (PolicyError, unique_object, publication_mode,
                                         private_inputs, private_artifact,
                                         private_diagnostic, continuation)

REPOSITORY = 'kolorifer/radarr-festival-list'
STAGES = ('implementation', 'review', 'test', 'merge', 'deploy', 'live', 'docs', 'acceptance')
REQUIRED = ('GOAL', 'ACCEPTANCE_CRITERIA', 'AUTHORIZATION', 'FORBIDDEN', 'INSTRUCTIONS')
MAX_BYTES = 2_097_152


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def material_value(value):
    """Observation refreshes alone are quiet; expiry/status transitions are not."""
    if isinstance(value, dict):
        return {k: material_value(v) for k, v in value.items()
                if k not in ('observed_at', 'proposal_observed_at')}
    if isinstance(value, list):
        return [material_value(v) for v in value]
    return value


def keys(value, expected):
    require(isinstance(value, dict) and set(value) == set(expected.split()), 'schema_keys')


def stamp(value):
    require(type(value) in (int, float) and math.isfinite(value) and value > 0, 'timestamp')


def sha(value):
    require(isinstance(value, str) and re.fullmatch('[a-f0-9]{40}', value), 'revision')
    return value


def identifier(value):
    require(isinstance(value, str) and re.fullmatch('[A-Za-z0-9_.-]{1,80}', value), 'identifier')
    return value


def load(path):
    require(not path.is_symlink() and path.is_file() and path.stat().st_size <= MAX_BYTES, 'input_file')
    return json.loads(path.read_text(), object_pairs_hook=unique_object,
                      parse_constant=lambda _: require(False, 'nonfinite_json'))


def atomic_save(path, value):
    """Single-writer replacement: mode600 temp, file fsync, rename, directory fsync.

    Caller supplies a new task-local directory outside the checkout. No discovery
    of operational state. A crash exposes either the old or the complete new file.
    """
    require(path.parent.is_dir() and not path.is_symlink(), 'state_path')
    checkout = Path(__file__).resolve().parent.parent
    require(checkout != path.resolve() and checkout not in path.resolve().parents, 'state_inside_checkout')
    fd, name = tempfile.mkstemp(prefix='.coordinator-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream, sort_keys=True, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def task_sections(task, owner):
    require(isinstance(task, dict) and isinstance(task.get('user'), dict)
            and isinstance(task.get('body'), str), 'task_shape')
    require(task.get('user', {}).get('login') == owner, 'untrusted_author')
    reserved = '|'.join(('SUPERVISOR_TASK', 'STATE', *REQUIRED))
    for line in task['body'].splitlines():
        if re.match(r'^\s*(?:' + reserved + r')\s*:', line, re.I):
            match = dispatcher.FIELDS.fullmatch(line)
            require(match is not None and match[1] in ('SUPERVISOR_TASK', 'STATE', *REQUIRED),
                    'noncanonical_task_field')
    require(dispatcher.choose_task([task], owner, set()) is not None, 'invalid_task')
    dispatcher.capabilities(task, owner)
    publication_mode(task, owner)
    for policy in (private_inputs, private_artifact, private_diagnostic, continuation):
        policy(task['body'])
    matches = list(dispatcher.FIELDS.finditer(task['body']))
    return {m[1]: (m[2] + task['body'][m.end():
            matches[i + 1].start() if i + 1 < len(matches) else len(task['body'])]).strip()
            for i, m in enumerate(matches)}


def collection(value):
    keys(value, 'status items')
    require(value['status'] in ('complete', 'partial', 'unavailable'), 'read_status')
    require(isinstance(value['items'], list) and len(value['items']) <= 152, 'read_capacity')


def validate_snapshot(value):
    keys(value, 'version repository observed_at github goals local movies quality documentation')
    require(type(value['version']) is int and value['version'] == 1, 'snapshot_version')
    require(value['repository'] == REPOSITORY, 'repository')
    stamp(value['observed_at'])
    gh = value['github']
    keys(gh, 'default_branch revision branches issues pulls comments details')
    identifier(gh['default_branch'])
    if gh['revision'] is not None:
        sha(gh['revision'])
    for name in ('branches', 'issues', 'pulls'):
        collection(gh[name])
        field = 'name' if name == 'branches' else 'number'
        require(len({r[field] for r in gh[name]['items']}) == len(gh[name]['items']), 'duplicate_api_item')
    for number, rows in gh['comments'].items():
        require(number.isdecimal() and int(number) > 0, 'issue_number')
        collection(rows)
        require(len({r['id'] for r in rows['items']}) == len(rows['items']), 'duplicate_api_comment')
    for number, detail in gh['details'].items():
        require(number.isdecimal(), 'pull_number')
        keys(detail, 'head author merged merge_commit reviews checks')
        identifier(detail['author'])
        sha(detail['head'])
        require(type(detail['merged']) is bool, 'merged')
        if detail['merge_commit'] is not None:
            sha(detail['merge_commit'])
        collection(detail['reviews']); collection(detail['checks'])
    require(isinstance(value['goals'], list) and len(value['goals']) <= 20, 'goal_capacity')
    require(len({g['id'] for g in value['goals']}) == len(value['goals']), 'duplicate_goal')
    for goal in value['goals']:
        keys(goal, 'id source scope allowed_actions acceptance_criteria dependencies issue task pr head blocker next_action evidence required_stages corrections')
        identifier(goal['id'])
        keys(goal['source'], 'comment_id body_sha256')
        require(type(goal['source']['comment_id']) is int and goal['source']['comment_id'] > 0
                and isinstance(goal['source']['body_sha256'], str)
                and re.fullmatch('[a-f0-9]{64}', goal['source']['body_sha256']), 'source_reference')
        require(type(goal['issue']) is int and goal['issue'] > 0 and type(goal['task']) is int
                and goal['task'] > 0, 'goal_task')
        require(goal['pr'] is None or type(goal['pr']) is int and goal['pr'] > 0, 'goal_pr')
        if goal['head'] is not None:
            sha(goal['head'])
        require(isinstance(goal['dependencies'], list), 'dependencies')
        for dep in goal['dependencies']:
            identifier(dep)
        require(isinstance(goal['required_stages'], list) and
                set(goal['required_stages']) <= set(STAGES), 'required_stages')
        require(type(goal['corrections']) is int and 0 <= goal['corrections'] <= 8, 'correction_limit')
        require(goal['next_action'] in ('review', 'prepare_task', 'await_evidence', 'owner_decision', 'none'), 'next_action')
        require(isinstance(goal['evidence'], list) and len(goal['evidence']) <= 100, 'evidence_capacity')
        for evidence in goal['evidence']:
            keys(evidence, 'stage revision observed_at reference result component configuration')
            require(evidence['stage'] in STAGES and evidence['result'] in ('passed', 'failed'), 'evidence_stage')
            sha(evidence['revision']); stamp(evidence['observed_at']); identifier(evidence['reference'])
            for name in ('component', 'configuration'):
                if evidence[name] is not None:
                    identifier(evidence[name])
    local = value['local']
    keys(local, 'consumed terminal_tasks writer_active worktrees retained dependencies preservation')
    require(local['writer_active'] is None or type(local['writer_active']) is bool, 'writer_evidence')
    for name in ('consumed', 'terminal_tasks'):
        require(local[name] is None or isinstance(local[name], list) and
                all(type(n) is int and n > 0 for n in local[name]), 'local_numbers')
    for name in ('worktrees', 'retained', 'dependencies', 'preservation'):
        require(local[name] is None or isinstance(local[name], list), 'local_inventory')
    require(isinstance(value['quality'], list) and len(value['quality']) <= 1000, 'quality_capacity')
    require(isinstance(value['documentation'], list) and len(value['documentation']) <= 50, 'documentation_capacity')
    return value


def authorized_goal(goal, snapshot):
    """Imported work text never grants authority; bind to an exact owner comment."""
    gh = snapshot['github']
    require(gh['issues']['status'] == 'complete', 'authorization_issue_unavailable')
    issues = [i for i in gh['issues']['items'] if i['number'] == goal['issue']]
    require(len(issues) == 1, 'authorization_issue_unknown')
    owner = issues[0]['user']['login']
    rows = gh['comments'].get(str(goal['issue']))
    require(rows is not None and rows['status'] == 'complete', 'authorization_comments_incomplete')
    sources = [c for c in rows['items'] if c['id'] == goal['source']['comment_id']]
    require(len(sources) == 1, 'authorization_missing')
    source = sources[0]
    require(fingerprint(source['body']) == goal['source']['body_sha256'], 'authorization_changed')
    sections = task_sections(source, owner)
    require(dispatcher.task_number(source['body']) == goal['task'], 'authorization_task')
    require(goal['scope'] == sections['GOAL'] and goal['allowed_actions'] == sections['AUTHORIZATION']
            and goal['acceptance_criteria'] == sections['ACCEPTANCE_CRITERIA'], 'authorization_scope_changed')
    return owner, source, sections


def stages_for(goal, snapshot, now):
    detail = snapshot['github']['details'].get(str(goal['pr']))
    head = detail['head'] if detail else (None if goal['pr'] else goal['head'])
    output = {}
    for stage in STAGES:
        status = 'pending' if stage in goal['required_stages'] else 'not_applicable'
        reason = 'missing_evidence' if status == 'pending' else 'outside_approved_plan'
        refs, observations = [], []
        if status == 'pending' and head:
            candidates = [e for e in goal['evidence'] if e['stage'] == stage]
            current = [e for e in candidates if e['revision'] == head
                       and e['observed_at'] <= now + 300]
            if stage in ('deploy', 'live'):
                current = [e for e in current if e['component'] and e['configuration']]
            if stage == 'live':
                current = [e for e in current if now - e['observed_at'] <= 86400]
                deployments = [e for e in goal['evidence'] if e['stage'] == 'deploy'
                               and e['result'] == 'passed' and e['revision'] == head]
                current = [e for e in current if any(d['component'] == e['component']
                    and d['configuration'] == e['configuration'] and
                    d['observed_at'] <= e['observed_at'] for d in deployments)]
            if current:
                latest = max(current, key=lambda e: e['observed_at'])
                status, reason = latest['result'], 'revision_bound_evidence'
                refs = [latest['reference']]
                observations = [{k: latest[k] for k in ('revision', 'observed_at', 'component', 'configuration')}]
            elif candidates:
                reason = 'stale_or_inapplicable_evidence'
            if stage == 'review' and detail:
                rows = detail['reviews']
                reviews = [r for r in rows['items'] if r.get('commit_id') == head
                           and r['user']['login'] != detail['author']]
                # Latest opinion per reviewer; changes requested cannot be hidden by an older approval.
                latest = {}
                for r in sorted(reviews, key=lambda r: r['id']):
                    if r['state'] in ('APPROVED', 'CHANGES_REQUESTED', 'DISMISSED'):
                        latest[r['user']['login']] = r['state']
                status = ('failed' if 'CHANGES_REQUESTED' in latest.values() else
                          'passed' if 'APPROVED' in latest.values() else 'pending')
                reason = 'current_head_reviews' if rows['status'] == 'complete' else 'review_read_incomplete'
                if rows['status'] != 'complete':
                    status = 'pending'
            if stage == 'test' and detail and not current:
                checks = detail['checks']
                runs = checks['items']
                applicable = [r for r in runs if r.get('head_sha') == head]
                # CI is supplementary, not proof of the approved task's tests.
                if checks['status'] == 'complete' and applicable and len(applicable) == len(runs):
                    reason = 'current_ci_present_task_test_evidence_missing'
            if stage == 'merge' and detail:
                status = 'passed' if detail['merged'] else 'pending'
                reason = 'github_merge_only'
        output[stage] = {'status': status, 'reason': reason, 'evidence': refs, 'observations': observations}
    return head, output


def movie_review(snapshot, report, now):
    """Consume the complete existing export + report, never a private state path.

    Exact occurrence IDs survive grouping. Only strict identifiers/enums/counts
    leave this adapter; titles, source references and raw evidence never do.
    """
    from identity_research_handoff import validate_snapshot as validate_export
    validate_export(snapshot, now)
    # Compare every base field to the validated export. Do not invoke the
    # notification projection (it reads sender environment for redaction).
    require(isinstance(report, dict) and report.get('version') == 1, 'movie_report_version')
    stamp(report.get('generated_at'))
    require(now - 172800 < report['generated_at'] <= now + 300, 'movie_report_stale')
    require(isinstance(report.get('cases'), list) and len(report['cases']) <= 1000, 'movie_report_cases')
    require(report['coverage'] == snapshot['coverage'], 'movie_coverage_changed')
    by_id = {c['case_id']: c for c in report['cases']}
    require(len(by_id) == len(report['cases']) and
            set(by_id) == {c['case_id'] for c in snapshot['cases']}, 'movie_set_incomplete')
    groups = {}
    for case in snapshot['cases']:
        row = by_id[case['case_id']]
        require(all(row.get(k) == v for k, v in case.items()), 'movie_occurrence_changed')
        if case['route'] not in {'eligible', 'review_only', 'quarantine', 'unmatched', 'retry_later', 'existing_seed'}:
            continue
        identity = case['source_identity']
        group = fingerprint([case['title'], case['year'], identity])
        proposal = row.get('proposal') or {}
        require(isinstance(proposal, dict), 'movie_proposal')
        created = proposal.get('created_at')
        if created is not None:
            stamp(created)
            require(created <= now + 300, 'movie_proposal_future')
        freshness = ('fresh' if proposal.get('current_evidence') and created is not None
                     and now - created < 172800 else 'retained') if proposal else 'missing'
        result = proposal.get('result') or {}
        require(isinstance(result, dict), 'movie_result')
        candidate_rows = result.get('candidates', []) + proposal.get('search_candidates', [])
        require(isinstance(candidate_rows, list) and len(candidate_rows) <= 23, 'movie_candidate_capacity')
        candidates = []
        for item in candidate_rows:
            record = item.get('record', {})
            if record.get('type') in ('movie', 'tv') and type(record.get('id')) is int and 0 < record['id'] < 2**31:
                candidates.append({'type': record['type'], 'tmdb': record['id']})
        facts = []
        raw_evidence = result.get('evidence', [])
        require(isinstance(raw_evidence, list) and len(raw_evidence) <= 100, 'movie_evidence_capacity')
        for observation in raw_evidence:
            method, answer = observation.get('method'), observation.get('result', {})
            if method not in ('find', 'details', 'movie_search', 'tv_search'):
                continue
            reason, data = answer.get('reason'), answer.get('data')
            negative = reason == 'not_found' or reason == 'ok' and isinstance(data, dict) and (
                method == 'find' and data.get('movies') == [] and data.get('tv') == [] and data.get('tv_other') is False
                or method in ('movie_search', 'tv_search') and data.get('results') == [])
            facts.append({'method': method, 'status': 'verified_negative' if negative else
                          'available' if reason == 'ok' and data is not None else 'missing',
                          'freshness': freshness})
        groups.setdefault(group, []).append({
            'occurrence': case['case_id'], 'version': case['version'], 'identity': identity,
            'route': case['route'], 'reason': case['reason'],
            'evidence': freshness, 'proposal_observed_at': created, 'provider_measurement_time': 'unknown',
            'conflicting': case['correlation'] in ('identifier_conflict', 'context_conflict', 'simultaneous_conflict'),
            'candidates': candidates, 'facts': facts, 'disposition': 'review_evidence' if proposal else 'await_evidence',
            'edition': 'unknown', 'identity_approval': 'unknown', 'acquisition_approval': 'unknown'})
    reasons = {}
    for occurrences in groups.values():
        for occurrence in occurrences:
            reasons[occurrence['reason']] = reasons.get(occurrence['reason'], 0) + 1
    return {'coverage': 'incomplete_upstream', 'assessed': len(snapshot['cases']),
            'groups': [{'group': k, 'occurrences': sorted(v, key=lambda x: x['occurrence'])}
                       for k, v in sorted(groups.items())],
            'recurring_findings': [{'reason': k, 'occurrences': v, 'proposal': 'review_generic_correction',
                                    'expected_benefit': 'reduce_repeated_owner_review', 'effort': 'unestimated',
                                    'risk': 'identity_policy_requires_owner_review',
                                    'validation': 'synthetic_reproduction_then_existing_safeguard_tests'}
                                   for k, v in sorted(reasons.items()) if v > 1][:20],
            'provider_requests': 0, 'budget': 'existing_limits_unchanged'}


def quality_review(rows, now):
    output = []
    for row in rows:
        keys(row, 'id design observed_at rating count recognition_complete score_complete identity_verified notification_state acquisition_approved')
        identifier(row['id'])
        require(row['design'] in ('historical', 'experimental_audience50_recognition50'), 'score_design')
        require(row['notification_state'] in ('unknown', 'proposed', 'confirmed'), 'notification_state')
        for field in ('recognition_complete', 'score_complete', 'identity_verified', 'acquisition_approved'):
            require(type(row[field]) is bool, 'quality_boolean')
        if row['observed_at'] is not None:
            stamp(row['observed_at'])
        require(row['rating'] is None or type(row['rating']) in (int, float)
                and math.isfinite(row['rating']) and row['rating'] >= 0, 'rating_value')
        require(row['count'] is None or type(row['count']) is int and row['count'] >= 0, 'rating_count')
        findings = []
        if row['rating'] is None or row['count'] is None:
            findings.append('missing_rating_evidence')
        if not row['recognition_complete'] or not row['score_complete']:
            findings.append('partial_score_not_final')
        if row['observed_at'] is None or not now - 86400 <= row['observed_at'] <= now + 300:
            findings.append('stale_or_undated')
        if row['notification_state'] == 'confirmed' and not row['identity_verified']:
            findings.append('notification_identity_inconsistent')
        if row['acquisition_approved'] and not row['identity_verified']:
            findings.append('approval_identity_inconsistent')
        output.append({'id': row['id'], 'design': row['design'], 'findings': findings,
                       'action': 'review_only'})
    return output


def inventory(snapshot):
    gh, local = snapshot['github'], snapshot['local']
    rows = []
    for branch in gh['branches']['items']:
        name = branch['name']
        require(isinstance(name, str) and re.fullmatch('[A-Za-z0-9_./-]{1,200}', name), 'branch_name')
        sha(branch['commit']['sha'])
        prs = [p for p in gh['pulls']['items'] if p['head']['ref'] == name]
        reasons = []
        if name in ('main', gh['default_branch']) or branch.get('protected'):
            reasons.append('protected_branch')
        if re.search(r'(?:^|/)automation/issue-[^/]+-claim-[^/]+$', name):
            reasons.append('permanent_claim')
        if name.startswith(('research/', 'production/', 'runtime/')) or name == 'automation/issue-86-worker':
            reasons.append('retained_research_or_runtime')
        for field in ('worktrees', 'retained', 'dependencies'):
            if local[field] is None:
                reasons.append(field + '_unknown')
            elif name in local[field]:
                reasons.append(field + '_protected')
        state = 'awaiting_review' if any(p['state'] == 'open' for p in prs) else 'unresolved'
        if 'permanent_claim' in reasons:
            state = 'execution_record'
        elif 'retained_research_or_runtime' in reasons:
            state = 'retained_research'
        elif name in (local['worktrees'] or []) or name in (local['dependencies'] or []):
            state = 'active'
        elif prs and all(p['state'] == 'closed' for p in prs):
            state = 'closed_preservation_unverified'
        preserved = name in (local['preservation'] or [])
        rows.append({'branch': name, 'head': branch['commit']['sha'], 'classification': state,
                     'protections': reasons, 'preservation': 'supplied' if preserved else 'unknown',
                     'proposal': 'retain' if reasons else 'verify_preservation_and_dependencies',
                     'prs': sorted(p['number'] for p in prs)})
    return {'remote_read': gh['branches']['status'], 'local_process': 'unknown' if local['writer_active'] is None
            else 'active' if local['writer_active'] else 'supplied_inactive', 'branches': sorted(rows, key=lambda x: x['branch'])}


def findings(snapshot, now):
    validate_snapshot(snapshot)
    gh = snapshot['github']
    freshness = 'fresh' if now - 3600 < snapshot['observed_at'] <= now + 300 else 'stale'
    reads = {k: gh[k]['status'] for k in ('branches', 'issues', 'pulls')}
    goals = []
    for goal in snapshot['goals']:
        plan_bound = False
        try:
            _, _, sections = authorized_goal(goal, snapshot)
            authority = 'owner_task_bound'
            # A supplied stage subset cannot silently redefine completion. An
            # optional owner-declared stage list binds the machine-readable plan;
            # absent declaration leaves observations useful but completion open.
            declared = sections.get('COORDINATOR_STAGES', '').split(',')
            plan_bound = bool(goal['required_stages']) and set(declared) == set(goal['required_stages'])
        except (ValueError, PolicyError, KeyError, TypeError):
            authority = 'unverified_no_execution'
        head, stages = stages_for(goal, snapshot, now)
        if authority != 'owner_task_bound' or freshness != 'fresh':
            for value in stages.values():
                if value['status'] == 'passed':
                    value.update(status='pending', reason='authority_or_snapshot_unverified')
        goals.append({'id': goal['id'], 'issue': goal['issue'], 'task': goal['task'], 'pr': goal['pr'],
                      'source': goal['source'],
                      'scope_fingerprint': fingerprint(goal['scope']),
                      'allowed_actions_fingerprint': fingerprint(goal['allowed_actions']),
                      'acceptance_fingerprint': fingerprint(goal['acceptance_criteria']),
                      'completion_plan': 'owner_bound' if plan_bound else 'unverified',
                      'head': head, 'authority': authority, 'stages': stages,
                      'dependencies': goal['dependencies'], 'blocked': bool(goal['blocker']),
                      'next_proposal': goal['next_action'], 'complete': bool(goal['required_stages']) and
                      authority == 'owner_task_bound' and plan_bound and freshness == 'fresh' and not goal['blocker']
                      and not goal['dependencies'] and all(stages[k]['status'] == 'passed' for k in goal['required_stages'])})
    movies = {'status': 'not_supplied'}
    if snapshot['movies'] is not None:
        keys(snapshot['movies'], 'snapshot report')
        movies = movie_review(snapshot['movies']['snapshot'], snapshot['movies']['report'], now)
    docs = []
    for row in snapshot['documentation']:
        keys(row, 'id expected observed')
        identifier(row['id'])
        if row['expected'] != row['observed']:
            docs.append({'id': row['id'], 'finding': 'reconcile_documentation_evidence_only'})
    task_inventory = []
    for number, comments in sorted(gh['comments'].items()):
        issue = next((i for i in gh['issues']['items'] if i['number'] == int(number)), None)
        owner = issue['user']['login'] if issue else None
        trusted = [r for r in comments['items'] if r['user']['login'] == owner]
        numbered = [r for r in trusted if dispatcher.task_number(r['body'])]
        latest = max(numbered, key=lambda r: r['id']) if numbered else None
        fields = dispatcher.fields(latest['body']) if latest else {}
        task_inventory.append({'issue': int(number), 'read': comments['status'],
            'latest_owner_task': dispatcher.task_number(latest['body']) if latest else None,
            'state': fields.get('STATE') if fields.get('STATE') in
                ('READY_FOR_CODEX', 'RUNNING', 'DONE', 'NEEDS_USER', 'READY_FOR_REVIEW') else 'unknown',
            'worker_liveness': 'unknown'})
    return {'repository': REPOSITORY, 'revision': gh['revision'], 'freshness': freshness,
            'reads': reads, 'goals': goals, 'inventory': inventory(snapshot), 'movies': movies,
            'tasks': task_inventory,
            'quality': sorted(quality_review(snapshot['quality'], now), key=lambda r: r['id']),
            'documentation': sorted(docs, key=lambda r: r['id']),
            'execution': 'proposals_only', 'deployment': 'not_observed'}


def empty_state():
    return {'version': 1, 'material': None, 'sections': {}, 'work': [], 'proposals': [], 'delivery': 'not_confirmed'}


def validate_state(state):
    keys(state, 'version material sections work proposals delivery')
    require(type(state['version']) is int and state['version'] == 1
            and state['delivery'] == 'not_confirmed', 'state_version_delivery')
    require(state['material'] is None or re.fullmatch('[a-f0-9]{64}', state['material']), 'state_material')
    require(isinstance(state['sections'], dict) and len(state['sections']) <= 20, 'state_sections')
    for name, digest in state['sections'].items():
        identifier(name)
        require(isinstance(digest, str) and re.fullmatch('[a-f0-9]{64}', digest), 'section_digest')
    require(isinstance(state['work'], list) and isinstance(state['proposals'], list)
            and len(state['work']) <= 20 and len(state['proposals']) <= 20, 'state_capacity')
    for work in state['work']:
        keys(work, 'id issue task pr source scope_fingerprint allowed_actions_fingerprint acceptance_fingerprint completion_plan head authority stages dependencies blocked next_proposal complete')
        identifier(work['id'])
        keys(work['stages'], ' '.join(STAGES))
        require(work['authority'] in ('owner_task_bound', 'unverified_no_execution'), 'work_authority')
        for stage in work['stages'].values():
            keys(stage, 'status reason evidence observations')
            require(stage['status'] in ('passed', 'failed', 'pending', 'not_applicable'), 'work_stage')
    for proposal in state['proposals']:
        keys(proposal, 'fingerprint status')
        require(re.fullmatch('[a-f0-9]{64}', proposal['fingerprint']) and proposal['status'] == 'proposed', 'proposal_state')
    return state


def reconcile(snapshot, state, now):
    validate_state(state)
    report = findings(snapshot, now)
    material = fingerprint(material_value(report))
    sections = {k: fingerprint(material_value(v)) for k, v in report.items()}
    changed_sections = sorted(k for k, v in sections.items() if state['sections'].get(k) != v)
    changed = material != state['material']
    updated = copy.deepcopy(state)
    updated.update(material=material, sections=sections, work=report['goals'])
    if changed and material not in {p['fingerprint'] for p in updated['proposals']}:
        updated['proposals'] = (updated['proposals'] + [{'fingerprint': material, 'status': 'proposed'}])[-20:]
    previous = {g['id']: g for g in state['work']}
    return updated, {'changed': changed, 'changed_sections': changed_sections,
                     'fingerprint': material, 'delivery': 'not_confirmed',
                     'summary': ({'new_completed_stages': [{g['id']: [k for k, v in g['stages'].items()
                                      if v['status'] == 'passed' and (previous.get(g['id'], {}).get('head') != g['head']
                                      or previous.get(g['id'], {}).get('stages', {}).get(k, {}).get('status') != 'passed')]}
                                                         for g in report['goals']],
                                  'blockers': [g['id'] for g in report['goals'] if g['blocked'] or
                                               g['authority'] == 'unverified_no_execution'],
                                  'prepared_decisions': [g['id'] for g in report['goals']
                                                         if g['next_proposal'] == 'owner_decision'],
                                  'documentation_corrections': len(report['documentation'])
                                      if 'documentation' in changed_sections else 0,
                                  'quality_reviews': sum(bool(r['findings']) for r in report['quality'])
                                      if 'quality' in changed_sections else 0}
                                 if changed else None),
                     'report': report if changed else None}


def render_task(snapshot, goal_id, number, author, now):
    validate_snapshot(snapshot)
    require(now - 3600 < snapshot['observed_at'] <= now + 300, 'draft_stale_snapshot')
    matches = [g for g in snapshot['goals'] if g['id'] == goal_id]
    require(len(matches) == 1, 'draft_goal')
    goal = matches[0]
    owner, source, sections = authorized_goal(goal, snapshot)
    require(author == owner, 'untrusted_author')
    local = snapshot['local']
    require(local['consumed'] is not None and local['terminal_tasks'] is not None
            and local['writer_active'] is False, 'local_execution_unknown_or_active')
    comments = snapshot['github']['comments'][str(goal['issue'])]['items']
    trusted = [c for c in comments if c['user']['login'] == owner]
    owner_tasks = [c for c in trusted if dispatcher.task_number(c['body']) is not None]
    require(source['id'] == max(c['id'] for c in owner_tasks), 'draft_authority_not_latest')
    issue = next(i for i in snapshot['github']['issues']['items'] if i['number'] == goal['issue'])
    require(issue['state'] == 'open', 'draft_issue_closed')
    consumed = set(local['consumed']) | dispatcher.remote_consumed(comments, {owner})
    claims = snapshot['github']['branches']
    require(claims['status'] == 'complete', 'claims_incomplete')
    for branch in claims['items']:
        match = re.fullmatch('automation/issue-' + str(goal['issue']) + r'-claim-(\d+)', branch['name'])
        if match:
            consumed.add(int(match[1]))
    tasks = {dispatcher.task_number(c['body']) for c in trusted} - {None}
    require(not (consumed - set(local['terminal_tasks'])), 'outstanding_consumption')
    require(dispatcher.choose_task(comments, owner, consumed) is None, 'outstanding_task')
    require(type(number) is int and number == max(tasks | consumed | {0}) + 1, 'ambiguous_number')
    require(len(consumed) < 8 and goal['corrections'] < 8, 'iteration_limit')
    require(not goal['blocker'] and not goal['dependencies'], 'goal_blocked')
    # No new authority/capabilities are synthesized. An exact scoped draft is a
    # proposal; this deliberately excludes private/operational capability fields.
    require(dispatcher.capabilities(source, owner) == (False, 'none')
            and publication_mode(source, owner) == 'code'
            and not any(policy(source['body']) for policy in
                        (private_inputs, private_artifact, private_diagnostic, continuation)), 'draft_requires_supervisor_capability_review')
    body = f'SUPERVISOR_TASK: {number}\nSTATE: READY_FOR_CODEX\n' + '\n'.join(
        name + ':\n' + sections[name] for name in REQUIRED) + '\n'
    if 'COORDINATOR_STAGES' in sections:
        body += 'COORDINATOR_STAGES: ' + sections['COORDINATOR_STAGES'] + '\n'
    require(not re.search(r'https?://|magnet:|(?:token|passkey|password|secret|api_key)\s*[=:]\s*\S+',
                          body, re.I), 'draft_requires_privacy_review')
    candidate = {'id': max([c['id'] for c in comments] + [0]) + 1,
                 'user': {'login': author}, 'body': body}
    task_sections(candidate, owner)
    require(dispatcher.choose_task(comments + [candidate], owner, consumed) == candidate, 'parser_preflight')
    return {'body': body, 'fingerprint': fingerprint(body), 'source_comment': source['id'],
            'source_fingerprint': goal['source']['body_sha256'], 'status': 'draft_only',
            'number_consumed': False}


class PublicGitHub:
    """Fixed public repository; GET only, no environment/config/authentication read.

    At most 3 pages x 50 per collection, two selected issues/PRs, 40 requests,
    1 MiB per response, 10 second timeout, no redirect or retry.
    """
    def __init__(self):
        self.requests = 0
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs):
                return None
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def get(self, path):
        self.requests += 1
        require(self.requests <= 40 and (path == '' or path.startswith('/')), 'github_request_limit')
        request = urllib.request.Request('https://api.github.com/repos/' + REPOSITORY + path,
                                         headers={'Accept': 'application/vnd.github+json',
                                                  'User-Agent': 'movie-coordinator-read-only'})
        with self.opener.open(request, timeout=10) as response:
            raw = response.read(1_048_577)
            require(len(raw) <= 1_048_576, 'github_response_limit')
            return json.loads(raw), bool(response.headers.get('Link') and 'rel="next"' in response.headers['Link'])

    def pages(self, path):
        rows = []
        try:
            for page in range(1, 4):
                data, more = self.get(path + ('&' if '?' in path else '?') + f'per_page=50&page={page}')
                if isinstance(data, dict):
                    data = data['check_runs']
                require(isinstance(data, list) and len(data) <= 50, 'github_page')
                rows.extend(self.project(path, row) for row in data)
                if not more:
                    return {'status': 'complete', 'items': rows}
            return {'status': 'partial', 'items': rows}
        except (OSError, ValueError, KeyError):
            return {'status': 'partial' if rows else 'unavailable', 'items': rows}

    @staticmethod
    def project(path, row):
        """Discard bodies, titles, URLs and payloads before task-local persistence.

        Public snapshots retain protocol state/number metadata, not task authority.
        A trusted supervisor supplies pinned full task fixtures for draft preflight.
        """
        if path == '/branches':
            return {'name': row['name'], 'commit': {'sha': row['commit']['sha']},
                    'protected': row['protected']}
        if path.startswith('/issues?'):
            return {'number': row['number'], 'user': {'login': row['user']['login']}, 'state': row['state']}
        if path.startswith('/pulls?'):
            return {'number': row['number'], 'head': {'ref': row['head']['ref']}, 'state': row['state']}
        if path.endswith('/comments'):
            fields = dispatcher.fields(row['body'])
            lines = []
            for name in ('SUPERVISOR_TASK', 'WORKER_RESULT'):
                if fields.get(name, '').isdecimal():
                    lines.append(name + ': ' + fields[name])
            if fields.get('STATE') in ('READY_FOR_CODEX', 'RUNNING', 'DONE', 'NEEDS_USER', 'READY_FOR_REVIEW'):
                lines.append('STATE: ' + fields['STATE'])
            return {'id': row['id'], 'user': {'login': row['user']['login']}, 'body': '\n'.join(lines)}
        if path.endswith('/reviews'):
            return {k: row[k] for k in ('id', 'commit_id', 'state')} | {'user': {'login': row['user']['login']}}
        if '/check-runs' in path:
            return {k: row[k] for k in ('head_sha', 'status', 'conclusion')}
        raise ValueError('github_projection')

    def snapshot(self, issues=(111, 86), pulls=(110,)):
        require(len(issues) <= 2 and len(pulls) <= 2 and
                all(type(n) is int and n > 0 for n in (*issues, *pulls)), 'github_targets')
        value = {'version': 1, 'repository': REPOSITORY, 'observed_at': time.time(),
                 'goals': [], 'local': dict.fromkeys(('consumed', 'terminal_tasks', 'writer_active',
                     'worktrees', 'retained', 'dependencies', 'preservation')),
                 'movies': None, 'quality': [], 'documentation': []}
        gh = {'default_branch': 'main', 'revision': None, 'branches': self.pages('/branches'),
              'issues': self.pages('/issues?state=all&sort=updated&direction=desc'),
              'pulls': self.pages('/pulls?state=all&sort=updated&direction=desc'), 'comments': {}, 'details': {}}
        # A selected issue can lie outside the bounded all-issues window.
        for number in issues:
            try:
                row, _ = self.get(f'/issues/{number}')
                gh['issues']['items'] = [i for i in gh['issues']['items'] if i['number'] != number] + [self.project('/issues?', row)]
            except (OSError, ValueError, KeyError):
                gh['issues']['status'] = 'partial'
            gh['comments'][str(number)] = self.pages(f'/issues/{number}/comments')
        for number in pulls:
            try:
                row, _ = self.get(f'/pulls/{number}')
                gh['details'][str(number)] = {'head': row['head']['sha'], 'author': row['user']['login'], 'merged': row['merged'],
                    'merge_commit': row['merge_commit_sha'], 'reviews': self.pages(f'/pulls/{number}/reviews'),
                    'checks': self.pages('/commits/' + row['head']['sha'] + '/check-runs')}
            except (OSError, ValueError, KeyError):
                pass  # Missing details stay unknown; never synthesize a closed/merged PR.
        try:
            repo, _ = self.get('')
            gh['default_branch'] = repo['default_branch']
            head, _ = self.get('/commits/' + gh['default_branch'])
            gh['revision'] = head['sha']
        except (OSError, ValueError, KeyError):
            pass
        value['github'] = gh
        return validate_snapshot(value)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    network = sub.add_parser('snapshot')
    network.add_argument('--output', type=Path, required=True)
    report = sub.add_parser('report')
    report.add_argument('--snapshot', type=Path, required=True)
    report.add_argument('--state', type=Path, required=True)
    draft = sub.add_parser('draft')
    draft.add_argument('--snapshot', type=Path, required=True)
    draft.add_argument('--goal', required=True)
    draft.add_argument('--number', type=int, required=True)
    draft.add_argument('--author', required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'snapshot':
            value = PublicGitHub().snapshot()
            atomic_save(args.output, value)
            print(json.dumps({'status': 'snapshot_saved', 'revision': value['github']['revision'],
                              'observed_at': value['observed_at']}))
        elif args.command == 'report':
            state = load(args.state) if args.state.exists() else empty_state()
            updated, output = reconcile(load(args.snapshot), state, time.time())
            atomic_save(args.state, updated)
            print(json.dumps(output, sort_keys=True))
        else:
            print(json.dumps(render_task(load(args.snapshot), args.goal, args.number, args.author, time.time())))
        return 0
    except (ValueError, PolicyError, OSError, KeyError, TypeError, AttributeError):
        # Never echo imported text, paths, API responses or exception messages.
        print(json.dumps({'state': 'NEEDS_USER', 'reason': 'invalid_or_unavailable_input'}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
