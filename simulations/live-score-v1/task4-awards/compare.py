"""Task 4 awards-only, deterministic/offline. No audience calculation or network.

Imports only the preserved research Recognition function. Never writes baseline
files. Run --check for byte-for-byte verification without writes.
"""
import argparse
from collections import Counter
import csv
import hashlib
import io
import json
from pathlib import Path

from inventory import BASE, ROOT, inventory, policy, read

REPO = BASE.parents[1]
BASELINE = '824ed090e93c69e7ee5af6fe7df398725d8a6056'
VARIANTS = {'base': (), 'tiff': ('tiff',), 'screenplay': ('screenplay',),
            'both': ('tiff', 'screenplay')}
STATES = {'verified_positive', 'verified_no_award', 'source_not_checked',
          'unavailable', 'not_yet_announced'}
BONUS_BINDINGS = {('tt14905854', 'tiff'): ('TIFF', 'main'),
                  ('tt17526714', 'screenplay'): ('Cannes', 'main_competition'),
                  ('tt29271639', 'screenplay'): ('Berlin', 'main_competition')}
CATEGORIES = {
    'academy_best_picture': 'Best Picture', 'academy_international': 'International Feature Film',
    'academy_animated': 'Animated Feature Film', 'academy_documentary': 'Documentary Feature Film',
    'globe_best_picture': 'Best Motion Picture — Drama OR Musical or Comedy (retained shared component)',
    'globe_non_english': 'Best Motion Picture — Non-English Language',
    'globe_animated': 'Best Motion Picture — Animated',
    'bafta_best_film': 'Best Film', 'bafta_non_english': 'Film Not in the English Language',
    'efa_best_film': 'European Film',
    'cannes_main': 'Main Competition / Palme d’or', 'cannes_grand_prix': 'Grand Prix',
    'cannes_jury': 'Jury Prize', 'cannes_director': 'Best Director',
    'berlin_main': 'Main Competition / Golden Bear for Best Film',
    'berlin_grand_jury': 'Silver Bear Grand Jury Prize', 'berlin_jury': 'Silver Bear Jury Prize',
    'berlin_director': 'Silver Bear for Best Director',
    'venice_main': 'Venezia Competition / Golden Lion for Best Film',
    'venice_grand_jury': 'Silver Lion — Grand Jury Prize', 'venice_jury': 'Special Jury Prize',
    'venice_director': 'Silver Lion — Best Director',
    'sundance_grand_jury': 'Grand Jury: US Dramatic / US Documentary / World Cinema Dramatic / World Cinema Documentary',
    'sundance_audience': 'Audience: four feature Competition sections (retained scope)',
    'sundance_director': 'Directing: four feature Competition sections',
    'sundance_special_jury': 'Special Jury: four feature Competition sections',
    'spirit_best_feature': 'Best Feature', 'spirit_first_feature': 'Best First Feature',
    'gotham_best_feature': 'Best Feature', 'nsfc_best_picture': 'Best Picture (winner only)',
    'nyfcc_best_film': 'Best Film (winner only)', 'lafca_best_film': 'Best Picture (winner only)',
    'critics_choice_best_picture': 'Best Picture',
}


def dump(data):
    return json.dumps(policy.rounded(data), indent=2, ensure_ascii=False) + '\n'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_preservation():
    manifest = read(ROOT / 'inputs/baseline-manifest.json')
    if manifest['preservation_commit'] != BASELINE:
        raise ValueError('Unexpected preservation baseline')
    for name, digest in manifest['files'].items():
        if sha(REPO / name) != digest:
            raise ValueError('Preserved packet changed: ' + name)
    if inventory() != read(ROOT / 'inputs/gap-inventory.json'):
        raise ValueError('Pre-research inventory drift')
    return manifest


def stages(component):
    return ['selection_or_nomination', 'winner'] if policy.POLICY[component][3] else ['winner']


def validate_checks(checks, records, identities, sources):
    for c in checks:
        if c['component'] not in policy.POLICY or c['status'] not in STATES:
            raise ValueError('Unknown component/coverage state')
        if c['imdb_id'] not in identities or c['tmdb_id'] != identities[c['imdb_id']]['tmdb_id']:
            raise ValueError('Check identity mismatch')
        if c['stage'] not in stages(c['component']):
            raise ValueError('Invalid category stage')
        source = sources[c['source_id']]
        if source['institution'] != policy.POLICY[c['component']][1]:
            raise ValueError('Institution/component mismatch')
        if c['status'] == 'verified_no_award':
            scope = [c['component'], c['stage']]
            if (source['source_class'] != 'primary_origin_page_cache_possible'
                    or source['result'] != 'read'
                    or scope not in source.get('complete_category_scopes', [])
                    or source['event_year'] != c['event_year']):
                raise ValueError('Absence lacks complete inspected primary scope')
            for r in records:
                if (r['imdb_id'] == c['imdb_id'] and r['component'] == c['component']
                        and r.get('event_year') == c['event_year']
                        and (c['stage'] == 'selection_or_nomination' or r['status'] == 'winner')):
                    raise ValueError('Positive evidence contradicts scoped absence')


def validate_bonus(fact):
    kind = fact.get('candidate_kind')
    if (kind not in ('tiff', 'screenplay') or fact['status'] != 'winner'
            or fact.get('unique_film_attribution') is not True):
        raise ValueError('Candidate must be a uniquely attributed winner')
    if kind == 'tiff' and (fact['institution'], fact['section']) != ('TIFF', 'main'):
        raise ValueError('TIFF candidate must be main People’s Choice')
    if kind == 'screenplay' and (fact['institution'] not in ('Cannes', 'Berlin', 'Venice')
                                  or fact['section'] != 'main_competition'):
        raise ValueError('Screenplay candidate must be main Competition')
    return kind


def score(records, bonuses=(), variant='base'):
    enabled = sorted({validate_bonus(f) for f in bonuses} & set(VARIANTS[variant]))
    return policy.recognition(records, enabled)


def compare_variant(records, bonuses, variant, old_base, previous_variant):
    points = score(records, bonuses, variant)['observed_points']
    subtotal = sum(points.values())
    return {'families': points, 'observed_recognition_subtotal': subtotal,
            'complete_recognition_score': None,
            'task2_same_variant_subtotal': previous_variant,
            'evidence_delta_vs_task2_same_variant': subtotal - previous_variant,
            'bonus_delta_vs_new_base': subtotal - sum(score(records)['observed_points'].values()),
            'total_delta_vs_task2_base': subtotal - old_base}


def retained_records(films):
    return [dict(r, imdb_id=f['imdb_id']) for f in films
            for slot in f['award_breakdown']['components'].values()
            for r in slot['evidence']]


def retained_checks(cohort):
    """Only explicit Task 2 negatives/pending with component+edition scopes.

    Task 1's broad positive coverage flags never prove remaining categories
    negative. Its one cohort negative (Accident Critics Choice) is exact-bound.
    """
    out = []
    for c in read(BASE / 'task2/inputs/observations.json')['coverage_checks']:
        if c['status'] == 'verified_positive':
            continue  # Positive facts, not a blanket per-component claim.
        for iid in sorted(set(c['imdb_ids']) & set(cohort)):
            for comp in c['components']:
                for stage in stages(comp) if c['status'] == 'not_yet_announced' else [stages(comp)[0]]:
                    out.append({'imdb_id': iid, 'tmdb_id': cohort[iid]['tmdb_id'],
                                'component': comp, 'event_year': c['event_year'], 'stage': stage,
                                'status': c['status'], 'source_url': c['source_url'],
                                'observed_at': c['observed_at'], 'access_method': c['verification'],
                                'reason': c['scope'], 'origin': 'retained_task2'})
    c = next(c for c in read(BASE / 'inputs/observations.json')['coverage_checks']
             if c['imdb_ids'] == ['tt36491653'] and c['venue'] == 'Critics Choice')
    out.append({'imdb_id': 'tt36491653', 'tmdb_id': cohort['tt36491653']['tmdb_id'],
                'component': 'critics_choice_best_picture', 'event_year': 2026,
                'stage': 'selection_or_nomination', 'status': c['status'],
                'source_url': c['source_url'], 'observed_at': c['observed_at'],
                'access_method': 'retained_primary_web_observation', 'reason': c['scope'],
                'origin': 'retained_task1'})
    return out


def coverage_matrix(entries, records, checks):
    cells = []
    for entry in entries:
        for comp in entry['components']:
            for year in entry['edition_envelope']:
                for stage in stages(comp):
                    matching = [c for c in checks if c['imdb_id'] == entry['imdb_id']
                                and c['component'] == comp and c['event_year'] == year
                                and (c['stage'] == stage or c['stage'] == 'selection_or_nomination'
                                     and c['status'] == 'verified_no_award')]
                    facts = [r for r in records if r['imdb_id'] == entry['imdb_id']
                             and r['component'] == comp and r.get('event_year') == year
                             and (stage == 'selection_or_nomination' or r['status'] == 'winner')]
                    statuses = {c['status'] for c in matching}
                    if {'verified_no_award', 'not_yet_announced'} <= statuses:
                        raise ValueError('Conflicting scoped coverage: absence versus pending')
                    if facts and ('verified_no_award' in statuses or 'not_yet_announced' in statuses):
                        raise ValueError('Conflicting scoped coverage')
                    status = ('verified_positive' if facts else 'verified_no_award' if 'verified_no_award' in statuses
                              else 'not_yet_announced' if 'not_yet_announced' in statuses
                              else 'unavailable' if 'unavailable' in statuses else 'source_not_checked')
                    reason = ('Dated film-attributed positive; no assertion about other categories/editions.' if facts else
                              ' | '.join(dict.fromkeys(c['reason'] for c in matching)) if matching else
                              'No adequate complete category/edition record checked in Tasks 1/2/4; eligibility not inferred. Future outcome remains unresolved, never a verified negative.')
                    cells.append({'key': '/'.join([entry['imdb_id'], comp, str(year), stage]),
                                  'imdb_id': entry['imdb_id'], 'institution': entry['institution'],
                                  'component': comp, 'original_category_scope': CATEGORIES[comp],
                                  'event_year': year, 'stage': stage, 'status': status,
                                  'scope_role': 'focus_release_season_candidate' if year == entry['focus_edition'] else 'additional_audit_window',
                                  'check_ids': [c['id'] for c in matching],
                                  'positive_record_ids': [r['id'] for r in facts], 'reason': reason})
    return cells


def calculate():
    manifest = verify_preservation()
    identities = read(BASE / 'source-validation/cohort.json')['films']
    cohort = {f['imdb_id']: f for f in identities}
    baseline = {f['imdb_id']: f for f in read(BASE / 'task2/results.json')['films']}
    old_films = [baseline[iid] for iid in cohort]
    evidence = read(ROOT / 'inputs/evidence.json')
    if evidence['task'] != 4 or evidence['scored_awards_added'] or evidence['corrections']:
        raise ValueError('This evidence packet asserts no new scored facts/corrections')
    records = retained_records(old_films)
    for index, r in enumerate(records):
        r['id'] = 'R%04d' % (index + 1)
    checks = retained_checks(cohort)
    validate_checks(evidence['checks'], records, cohort, evidence['sources'])
    for c in evidence['checks']:
        source = evidence['sources'][c['source_id']]
        checks.append({**c, 'source_url': source['url'], 'observed_at': source['observed_at'],
                       'access_method': source['access_method'], 'origin': 'task4'})
    for index, c in enumerate(checks):
        c['id'] = 'C%04d' % (index + 1)
    for fact in evidence['facts']:
        identity = cohort[fact['imdb_id']]
        if (fact['tmdb_id'] != identity['tmdb_id'] or fact['film_title'] != identity['title']
                or fact['institution'] != evidence['sources'][fact['source_id']]['institution']):
            raise ValueError('Fact identity/institution mismatch')
        if fact['candidate_kind']:
            validate_bonus(fact)
    entries = read(ROOT / 'inputs/gap-inventory.json')['entries']
    before = coverage_matrix(entries, records, [c for c in checks if c['origin'] != 'task4'])
    cells = coverage_matrix(entries, records, checks)
    closed = [c['key'] for b, c in zip(before, cells)
              if b['status'] in ('source_not_checked', 'unavailable')
              and c['status'] in ('verified_positive', 'verified_no_award')]
    pending_resolved = [c['key'] for b, c in zip(before, cells)
                        if b['status'] == 'source_not_checked' and c['status'] == 'not_yet_announced']
    films = []
    for identity in identities:
        iid = identity['imdb_id']
        old = baseline[iid]
        film_records = [r for r in records if r['imdb_id'] == iid]
        bonuses = []
        for retained in old['extension_evidence']:
            venue, section = BONUS_BINDINGS[(iid, retained['kind'])]
            bonuses.append({**retained, 'institution': venue, 'section': section,
                            'status': 'winner', 'candidate_kind': retained['kind'],
                            'origin': 'retained_task1_no_new_points'})
        new = score(film_records)['observed_points']
        old_base = old['variants']['unsmoothed/base']['recognition_observed_points']
        variants = {}
        for variant in VARIANTS:
            previous = old['variants']['unsmoothed/' + variant]['recognition_subtotal']
            variants[variant] = compare_variant(film_records, bonuses, variant, sum(old_base.values()), previous)
        film_cells = [c for c in cells if c['imdb_id'] == iid]
        films.append({'identity': identity, 'release_context': old['notes'],
                      'identity_conflict': read(BASE / 'source-validation/cohort.json')['conflicts'].get(iid),
                      'task2_base_families': old_base, 'new_base_families': new,
                      'task2_base_subtotal': sum(old_base.values()), 'new_base_observed_subtotal': sum(new.values()),
                      'signed_evidence_delta': sum(new.values()) - sum(old_base.values()),
                      'family_evidence_deltas': {f: new[f] - old_base[f] for f in new},
                      'coverage_status': 'partial_observed_subtotal', 'complete_recognition_score': None,
                      'coverage_counts': dict(Counter(c['status'] for c in film_cells)),
                      'closed_gap_keys': [k for k in closed if k.startswith(iid + '/')],
                      'unresolved_cell_keys': [c['key'] for c in film_cells if c['status'] not in
                                               ('verified_positive', 'verified_no_award')],
                      'component_breakdown': score(film_records), 'retained_bonus_evidence': bonuses,
                      'candidate_coverage': {kind: {
                          'status': 'verified_positive' if any(b['candidate_kind'] == kind for b in bonuses) else 'source_not_checked',
                          'reason': 'Retained qualifying winner evidence; no new marginal points versus Task 2.' if any(b['candidate_kind'] == kind for b in bonuses) else 'No qualifying positive in retained packet; absence of this candidate signal is not certified.'}
                          for kind in ('tiff', 'screenplay')},
                      'task4_context_facts': [f for f in evidence['facts'] if f['imdb_id'] == iid],
                      'changes': {'newly_scored_components': [], 'corrections': [],
                                  'corroborations_add_points': False}, 'variants': variants})
    return policy.rounded({'task': 4, 'research_cutoff': evidence['research_cutoff'],
                           'publication_baseline': BASELINE, 'task2_numerical_baseline': manifest['task2_commit'],
                           'historical_policy_revision': manifest['historical_commit'],
                           'family_caps': policy.FAMILIES, 'components': policy.POLICY,
                           'input_sha256': {p.name: sha(p) for p in sorted((ROOT / 'inputs').glob('*.json'))},
                           'diagnostics': {'films': len(films), 'institutions': 14, 'inventory_entries': len(entries),
                                           'coverage_cells': len(cells),
                                           'coverage_counts': dict(Counter(c['status'] for c in cells)),
                                           'focus_coverage_counts': dict(Counter(c['status'] for c in cells if c['scope_role'] == 'focus_release_season_candidate')),
                                           'closed_evidence_gaps': len(closed),
                                           'newly_classified_pending_cells': len(pending_resolved),
                                           'new_scored_components': 0, 'base_score_changes': 0},
                           'films': films, 'coverage': cells, 'checks': checks, 'retained_award_records': records})


def csv_text(rows, fields):
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def outputs(result):
    coverage = result['coverage']
    film_rows, lines = [], ['# Task 4 Recognition comparison', '',
        'Observed subtotals only, as of 2026-10-28. Cohort order is retained; no leaderboard.', '',
        '| Film | Europe /20 | Independent /10 | US /10 | Critics /10 | Task 2 base | New base /50 | Evidence Δ | TIFF (Δ) | Screenplay (Δ) | Both (Δ) | Coverage |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |']
    for film in result['films']:
        identity = film['identity']
        points = film['new_base_families']
        vs = film['variants']
        row = {'imdb_id': identity['imdb_id'], 'tmdb_id': identity['tmdb_id'], 'title': identity['title'],
               'retained_year': identity['year'], **points,
               'coverage_status': film['coverage_status'], 'complete_recognition_score': '',
               'task2_base': film['task2_base_subtotal'], 'new_base_observed_subtotal': film['new_base_observed_subtotal'],
               'signed_evidence_delta': film['signed_evidence_delta']}
        for kind, variant in vs.items():
            row[kind + '_subtotal'] = variant['observed_recognition_subtotal']
            row[kind + '_bonus_delta'] = variant['bonus_delta_vs_new_base']
            row[kind + '_evidence_delta_vs_task2_same_variant'] = variant['evidence_delta_vs_task2_same_variant']
        film_rows.append(row)
        numbers = [points[f] for f in policy.FAMILIES] + [film['task2_base_subtotal'], film['new_base_observed_subtotal'], film['signed_evidence_delta']]
        optional = ['%g (%+g)' % (vs[k]['observed_recognition_subtotal'], vs[k]['bonus_delta_vs_new_base']) for k in ('tiff', 'screenplay', 'both')]
        lines.append('| ' + identity['title'] + ' | ' + ' | '.join('%g' % x for x in numbers) + ' | ' + ' | '.join(optional) + ' | Partial |')
    lines += ['', 'All eight complete Recognition scores remain null. Family zeros mean no observed scored component, not verified whole-family absence. See [report](report.md), [results](results.json), and [all coverage cells](coverage.csv).', '',
              '## Component attribution', '',
              'Strongest value once per component; different components may add. Raw family sums cap at 100, then scale to 20/10/10/10. Candidate points apply inside those caps.', '']
    for film in result['films']:
        lines += ['### ' + film['identity']['title'], '',
                  '`' + film['identity']['imdb_id'] + '` / TMDb ' + str(film['identity']['tmdb_id']) + '; retained year ' + str(film['identity']['year']) + '.', '',
                  '| Component | Strongest normalized points /100 | Family | Evidence |', '| --- | ---: | --- | --- |']
        for comp, slot in film['component_breakdown']['components'].items():
            citations = list(dict.fromkeys('[%s, %s, %s](%s)' % (r['id'], r['status'], r.get('observed_at') or 'archived date unknown', r['source_url']) for r in slot['evidence']))
            lines.append('| %s | %g | %s | %s |' % (comp, slot['normalized_points'], slot['family'], '; '.join(citations)))
        lines += ['', 'Coverage: `' + json.dumps(film['coverage_counts'], sort_keys=True) + '`. Exact unresolved category/edition/stage cells are in [unresolved.csv](unresolved.csv).', '']
    fields = list(film_rows[0])
    coverage_fields = ['key', 'imdb_id', 'institution', 'component', 'original_category_scope', 'event_year', 'stage', 'status', 'scope_role', 'check_ids', 'positive_record_ids', 'reason']
    rows = [{**c, 'check_ids': ';'.join(c['check_ids']), 'positive_record_ids': ';'.join(c['positive_record_ids'])} for c in coverage]
    return {'results.json': dump({k: v for k, v in result.items() if k != 'coverage'}),
            'coverage.json': dump({'research_cutoff': result['research_cutoff'], 'scope': 'Defined retained components, three-edition audit envelope; phase-specific statuses, no film eligibility inference.', 'cells': coverage}),
            'comparison.csv': csv_text(film_rows, fields),
            'coverage.csv': csv_text(rows, coverage_fields),
            'unresolved.csv': csv_text([c for c in rows if c['status'] not in ('verified_positive', 'verified_no_award')], coverage_fields),
            'breakdowns.md': '\n'.join(lines)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    expected = outputs(calculate())
    for name, content in expected.items():
        path = ROOT / name
        if args.check:
            if not path.exists() or path.read_bytes() != content.encode('utf-8'):
                raise SystemExit('Generated output differs: ' + name)
        else:
            path.write_bytes(content.encode('utf-8'))
    print(('Checked' if args.check else 'Generated') + ' six Task 4 awards-only artifacts; eight films; no network/audience calculation.')


if __name__ == '__main__':
    main()
