"""Version-1 staged observations. Fixed sources; no URL, home or credential API."""
import copy
import re

from automation import coordinator as c
from automation.coordinator_io import read_bytes, decode, digest
from automation.coordinator_parent import validate_export
from automation.supervisor_policy import PolicyError

SOURCES = ('engineering', 'investigations', 'research_report', 'parent_status', 'quality_release')
MAX_AGE = {'engineering': 3600, 'investigations': 3600, 'research_report': 172800,
           'parent_status': 3600, 'quality_release': 3600}
FAILURES = (ValueError, PolicyError, OSError, KeyError, TypeError, AttributeError, RecursionError)


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
    return result


def hex64(value):
    c.require(isinstance(value, str) and re.fullmatch('[a-f0-9]{64}', value), 'source_hash')


def manifest(value, now):
    c.keys(value, 'version repository sources')
    c.require(type(value['version']) is int and value['version'] == 1
              and value['repository'] == c.REPOSITORY, 'manifest_version')
    c.require(isinstance(value['sources'], list) and len(value['sources']) == len(SOURCES), 'expected_sources')
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
    return value


def validate_report(report, now, eligible=None):
    """Validate actual write_report v1 independently of paired availability."""
    from identity_triage_store import digest as producer_digest
    c.keys(report, 'version generated_at coverage oldest_unresolved_age_seconds budget cases changed_cases versions telegram_digest_enabled review_controls_enabled unassessed_policy historical_seeds')
    c.require(type(report['version']) is int and report['version'] == 1, 'movie_report_version')
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
            c.require(proposal['created_at'] <= now + 300, 'movie_proposal_future')
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
    from identity_triage_store import digest as producer_digest
    validate_snapshot(snapshot, now)
    eligible = {item['case_id']: producer_digest({k: v for k, v in item.items() if k != 'observed_at'})
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
        availability[source] = info
        if entry['path'] is None:
            continue
        try:
            c.require(all(entry[k] is None or entry[k] <= now + 300
                          for k in ('generated_at', 'observed_at', 'collected_at')), 'source_future')
            raw = read_bytes(root, entry['path'])
            c.require(digest(raw) == entry['sha256'], 'source_identity')
            content = decode(raw)
            c.require(isinstance(content, dict), 'source_object')
            event = entry['observed_at'] if entry['observed_at'] is not None else entry['generated_at']
            if source in ('investigations', 'research_report'):
                c.require(entry['generated_at'] == content.get('generated_at') and entry['generated_at'] is not None,
                          'source_time_identity')
                # Export freshness is generation time, never a later collection.
                event = content['generated_at']
            elif source == 'engineering':
                c.require(entry['observed_at'] == content.get('observed_at')
                          and entry['revision'] == content.get('github', {}).get('revision'), 'source_identity')
            elif source == 'parent_status':
                validate_export(content)
                c.require(entry['collected_at'] == content['read_at']
                          and entry['generated_at'] is None and entry['observed_at'] is None, 'source_identity')
                # Journals have unknown transition times; freshness of a read is
                # useful coverage, but never freshness of an execution event.
                event = content['read_at']
            if event is not None:
                c.stamp(event)
                c.require(event <= now + 300, 'source_future')
                if now - event >= entry['max_age_seconds']:
                    info.update(status='stale', reason='expired')
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
        except FAILURES:
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
