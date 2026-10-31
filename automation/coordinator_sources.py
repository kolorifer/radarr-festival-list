"""Version-1 staged observations. Fixed sources; no URL, home or credential API."""
import copy
import re

from automation import coordinator as c
from automation import coordinator_diagnostics as d
from automation.coordinator_io import read_bytes, decode, digest
from automation.coordinator_parent import validate_export
from automation.supervisor_policy import PolicyError

SOURCES = ('engineering', 'investigations', 'research_report', 'parent_status', 'quality_release')
MAX_AGE = {'engineering': 3600, 'investigations': 3600, 'research_report': 172800,
           'parent_status': 3600, 'quality_release': 3600}
FAILURES = (ValueError, PolicyError, OSError, KeyError, TypeError, AttributeError, RecursionError)


def producer_epoch(budget):
    """Select a documented writer contract, never infer it by trying hashes.

    The original ResearchStore has no epoch. Both observed recurring-v1 budget
    shapes use the SAME evidence semantics. Budget values remain observations,
    with their original names; they confer no request or scheduling authority.
    """
    c.require(isinstance(budget, dict), 'movie_budget_schema')
    if 'epoch' not in budget:
        return 'research-store-v1'
    c.require(budget['epoch'] == 'recurring-v1', 'movie_producer_epoch')
    daily = {'daily_case_cap', 'daily_request_cap', 'cases_rolling_day', 'requests_rolling_day'}
    weekly = {'weekly_case_cap', 'weekly_request_cap', 'cases_rolling_week', 'requests_rolling_week'}
    present = set(budget) & (daily | weekly)
    c.require(present in (daily, weekly), 'movie_budget_schema')
    c.require(all(type(budget[k]) is int and budget[k] >= 0 for k in present), 'movie_budget_schema')
    return 'recurring-v1'


def evidence_version(item, epoch):
    """Pure writer digest; no Store, transaction, entrypoint or provider call."""
    from identity_triage_store import digest
    c.require(epoch in ('research-store-v1', 'recurring-v1'), 'movie_producer_epoch')
    material = {k: v for k, v in item.items() if k != 'observed_at'}
    if epoch == 'recurring-v1':
        material['provenance'] = [{**p, 'observed_at': 1} for p in item['provenance']]
    return digest(material)


def material_report(report):
    """Compare validated findings, retaining byte provenance in the real payload.

    Only the manifest's raw serialization hash and export-generation clock are
    provenance here. Evidence/version hashes, explicit revisions, source status,
    freshness limits and all other report fields retain their existing meaning.
    """
    result = c.material_value(report)
    for info in result.get('sources', {}).values():
        info.pop('sha256', None)
        info.pop('generated_at', None)
        # Private diagnostic detail does not revise coarse availability semantics
        # or force an upgrade report for immutable pre-diagnostic payloads.
        info.pop('diagnostics', None)
    return result


def hex64(value):
    c.require(isinstance(value, str) and re.fullmatch('[a-f0-9]{64}', value), 'source_hash')


def manifest(value, now):
    c.require(isinstance(value, dict), 'manifest_schema')
    version = value.get('version')
    c.keys(value, 'version repository sources diagnostics' if version == 2 else 'version repository sources')
    c.require(type(version) is int and version in (1, 2)
              and value['repository'] == c.REPOSITORY, 'manifest_version')
    c.require(isinstance(value['sources'], list) and len(value['sources']) == len(SOURCES), 'expected_sources')
    if version == 2:
        d.validate(value['diagnostics'])
        c.require(all(x['source'] in ('investigations', 'research_report')
                      and x['stage'] in ('acquisition', 'staging') for x in value['diagnostics']),
                  'manifest_diagnostics')
    ids, paths = set(), set()
    for entry in value['sources']:
        c.keys(entry, 'id path sha256 revision generated_at observed_at collected_at max_age_seconds')
        source = entry['id']
        c.require(source in SOURCES and source not in ids, 'source_identity')
        ids.add(source)
        if entry['revision'] is not None:
            c.sha(entry['revision'])
        for field in ('generated_at', 'observed_at', 'collected_at'):
            if entry[field] is not None:
                c.stamp(entry[field])
        c.require(type(entry['max_age_seconds']) is int
                  and 0 < entry['max_age_seconds'] <= MAX_AGE[source], 'source_freshness')
        if entry['path'] is None:
            c.require(entry['sha256'] is None, 'source_identity')
        else:
            from automation.coordinator_io import relative_path
            relative_path(entry['path']); hex64(entry['sha256'])
            c.require(entry['path'] not in paths, 'source_identity')
            paths.add(entry['path'])
    if version == 2:
        by_source = {e['id']: e for e in value['sources']}
        for source in ('investigations', 'research_report'):
            entry = by_source[source]
            facts = {x['stage']: x['reason'] for x in value['diagnostics'] if x['source'] == source}
            c.require('acquisition' in facts, 'manifest_acquisition')
            if entry['path'] is None:
                c.require(facts['acquisition'] != 'read_complete' and 'staging' not in facts
                          and all(entry[k] is None for k in ('generated_at', 'observed_at', 'collected_at', 'revision')),
                          'manifest_unread')
            else:
                c.require(facts == {'acquisition': 'read_complete', 'staging': 'staged'}
                          and entry['path'] == source + '.json' and entry['collected_at'] is not None,
                          'manifest_staged')
    return value


def validate_report(report, now, eligible=None):
    """Validate actual write_report v1 independently of paired availability."""
    from identity_triage_store import digest as producer_digest
    c.keys(report, 'version generated_at coverage oldest_unresolved_age_seconds budget cases changed_cases versions telegram_digest_enabled review_controls_enabled unassessed_policy historical_seeds')
    c.require(type(report['version']) is int and report['version'] == 1, 'movie_report_version')
    producer_epoch(report['budget'])
    c.require(report['telegram_digest_enabled'] is False and report['review_controls_enabled'] is False,
              'movie_report_controls')
    c.stamp(report['generated_at'])
    c.require(now - 172800 < report['generated_at'] <= now + 300, 'movie_report_stale')
    c.require(isinstance(report['cases'], list) and len(report['cases']) <= 1000, 'movie_report_capacity')
    c.require(isinstance(report['versions'], dict) and len(report['versions']) == len(report['cases']),
              'movie_report_versions')
    for row in report['cases']:
        c.require(isinstance(row, dict), 'movie_report_case')
        cid = row['case_id']
        stable = {k: v for k, v in row.items() if k != 'observed_at'}
        c.require(report['versions'].get(cid) == producer_digest(stable), 'movie_report_versions')
        proposal = row.get('proposal')
        if proposal is not None:
            c.require(isinstance(proposal, dict) and type(proposal.get('current_evidence')) is bool,
                      'movie_proposal')
            hex64(proposal.get('evidence_version')); c.stamp(proposal.get('created_at'))
            d.check(proposal['created_at'] <= now + 300, 'freshness', 'future_evidence')
            if proposal['current_evidence'] and eligible is not None:
                c.require(cid in eligible and proposal['evidence_version'] == eligible[cid], 'movie_proposal_version')
    c.require(set(report['versions']) == {r['case_id'] for r in report['cases']}, 'movie_report_versions')
    c.require(isinstance(report['changed_cases'], list) and len(report['changed_cases']) <= len(report['cases']),
              'movie_report_changes')
    by_id = {row['case_id']: row for row in report['cases']}
    c.require(len({r['case_id'] for r in report['changed_cases']}) == len(report['changed_cases'])
              and all(by_id.get(r['case_id']) == r for r in report['changed_cases']), 'movie_report_changes')
    return report


def movie_pair(snapshot, report, now):
    """Actual write_report v1, not a made-up list or digest/sender projection."""
    from identity_research_handoff import validate_snapshot
    validate_snapshot(snapshot, now)
    epoch = producer_epoch(report['budget'])
    eligible = {item['case_id']: evidence_version(item, epoch)
                for item in snapshot['items']}
    validate_report(report, now, eligible)
    # The foundation compares the complete ID set, every base field and coverage,
    # validates proposal/candidate/evidence bounds, and preserves retained evidence.
    result = c.movie_review(snapshot, report, now)
    result.update(status='partial', reason='incomplete_upstream',
                  known_cases=known_cases(snapshot), eligible_cases=sorted(eligible),
                  upstream_coverage=copy.deepcopy(snapshot['coverage']),
                  eligible_versions=eligible,
                  proposal_versions={r['case_id']: {
                      'report_version': report['versions'][r['case_id']],
                      'evidence_version': (r.get('proposal') or {}).get('evidence_version'),
                      'current_evidence': (r.get('proposal') or {}).get('current_evidence'),
                      'created_at': (r.get('proposal') or {}).get('created_at')}
                      for r in report['cases']})
    if epoch == 'recurring-v1':
        result.update(producer_epoch=epoch, research_budget=copy.deepcopy(report['budget']))
    return result


def known_cases(snapshot):
    """All validated base fields, including titles, stay in the private payload.

    The integration CLI emits only public_projection, never these private rows.
    Arbitrary report/evidence fields are never copied; pinned staged bytes retain
    the full proposal evidence for the separately authorized private reviewer.
    """
    return [copy.deepcopy(row)
            for row in sorted(snapshot['cases'], key=lambda row: row['case_id'])]


def observations(root, manifest_name, now):
    """Per-source rejection is explicit and cannot erase independent findings."""
    value = manifest(decode(read_bytes(root, manifest_name)), now)
    data, availability = {}, {}
    for entry in value['sources']:
        source = entry['id']
        info = {k: entry[k] for k in ('id', 'sha256', 'revision', 'generated_at', 'observed_at',
                                      'collected_at', 'max_age_seconds')}
        info.update(read_at=now, status='unavailable', reason='not_staged')
        info['diagnostics'] = [x.copy() for x in value.get('diagnostics', []) if x['source'] == source]
        availability[source] = info
        if entry['path'] is None:
            continue
        stage = 'acquisition'
        try:
            raw = read_bytes(root, entry['path'])
            stage = 'identity'
            d.check(digest(raw) == entry['sha256'], 'identity', 'hash_mismatch')
            stage = 'decoding'
            content = decode(raw)
            stage = 'schema'
            c.require(isinstance(content, dict), 'source_object')
            d.check(all(entry[k] is None or entry[k] <= now + 300
                        for k in ('generated_at', 'observed_at', 'collected_at')),
                    'freshness', 'future_evidence')
            event = entry['observed_at'] if entry['observed_at'] is not None else entry['generated_at']
            if source in ('investigations', 'research_report'):
                c.stamp(content.get('generated_at'))
                d.check(entry['generated_at'] == content.get('generated_at') and entry['generated_at'] is not None,
                        'provenance', 'time_mismatch')
                # Export freshness is generation time, never a later collection.
                event = content['generated_at']
            elif source == 'engineering':
                d.check(entry['observed_at'] == content.get('observed_at'), 'provenance', 'time_mismatch')
                d.check(entry['revision'] == content.get('github', {}).get('revision'),
                        'provenance', 'revision_mismatch')
            elif source == 'parent_status':
                validate_export(content)
                d.check(entry['collected_at'] == content['read_at']
                        and entry['generated_at'] is None and entry['observed_at'] is None,
                        'provenance', 'time_mismatch')
                # Journals have unknown transition times; freshness of a read is
                # useful coverage, but never freshness of an execution event.
                event = content['read_at']
            if event is not None:
                c.stamp(event)
                d.check(event <= now + 300, 'freshness', 'future_evidence')
                if now - event >= entry['max_age_seconds']:
                    info.update(status='stale', reason='expired')
                    info['diagnostics'].append(d.diagnostic(source, 'freshness', 'stale_evidence'))
                    continue
            else:
                info.update(status='partial', reason='event_time_unknown')
            if source == 'quality_release':
                # No passive production contract exists yet. Even [] cannot
                # establish a complete review, nor coerce unknown approvals.
                info.update(status='unavailable', reason='passive_export_missing')
                continue
            if source == 'engineering':
                c.require(content['movies'] is None and content['quality'] == [], 'separate_sources_required')
                data[source] = c.findings(content, now)
            elif source == 'investigations':
                from identity_research_handoff import validate_snapshot
                c.require(type(content['version']) is int, 'movie_version')
                validate_snapshot(content, now)
                data[source] = content
            elif source == 'parent_status':
                data[source] = content
                info.update(status=content['status'], reason=content['reason'])
            else:
                validate_report(content, now)
                data[source] = content
            if info['reason'] == 'not_staged':
                info.update(status='available', reason='validated')
        except FAILURES as exc:
            if isinstance(exc, d.ValidationFailure):
                failure_stage, reason = exc.stage, exc.reason
            else:
                failure_stage = stage
                reason = (d.acquisition_reason(exc) if stage == 'acquisition' else
                          {'identity': 'hash_mismatch', 'decoding': 'invalid_json',
                           'schema': 'invalid_source_schema'}[stage])
            # Replace a prior acquisition success if staged bytes became unreadable.
            info['diagnostics'] = [x for x in info['diagnostics'] if x['stage'] != failure_stage]
            info['diagnostics'].append(d.diagnostic(source, failure_stage, reason))
            info.update(status='inconsistent', reason='invalid_or_conflicting')
            data.pop(source, None)
    # No raw paths, manifest text, exception messages or capability strings leave.
    report = copy.deepcopy(data.get('engineering', {
        'repository': c.REPOSITORY, 'revision': None, 'freshness': 'unknown', 'reads': {},
        'goals': [], 'inventory': {}, 'tasks': [], 'documentation': [],
        'execution': 'proposals_only', 'deployment': 'not_observed'}))
    report['sources'] = availability
    report['quality'] = {'status': 'unavailable', 'reason': 'passive_export_missing',
                         'review_completed': False, 'identity_approval': 'unknown',
                         'acquisition_approval': 'unknown', 'recipient_delivery': 'unknown'}
    if 'investigations' in data:
        export = data['investigations']
        report['movies'] = {'status': 'partial', 'reason': 'compatible_report_missing',
                            'coverage': 'incomplete_upstream', 'review_completed': False,
                            'upstream_coverage': copy.deepcopy(export['coverage']),
                            'known_cases': known_cases(export),
                            'eligible_cases': sorted(x['case_id'] for x in export['items'])}
        if 'research_report' in data:
            try:
                report['movies'] = movie_pair(export, data['research_report'], now)
            except FAILURES:
                availability['research_report']['diagnostics'].append(
                    d.diagnostic('research_report', 'pair', 'incompatible_movie_pair'))
                availability['research_report'].update(status='inconsistent', reason='invalid_or_conflicting')
                report['movies']['reason'] = 'incompatible_report'
    else:
        report['movies'] = {'status': 'unavailable', 'reason': 'snapshot_unavailable', 'review_completed': False}
        if availability['research_report']['status'] == 'available':
            availability['research_report'].update(status='partial', reason='snapshot_unavailable')
    if 'parent_status' in data:
        report['parent'] = data['parent_status']
    else:
        report['parent'] = {'status': 'unavailable', 'reason': 'parent_unavailable', 'writer_liveness': 'unknown'}
    return report
