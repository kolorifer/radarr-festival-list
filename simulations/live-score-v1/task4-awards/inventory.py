"""Derive the pre-research gap inventory from preserved Task 1/2 records."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
spec = importlib.util.spec_from_file_location('retained_award_policy', BASE / 'calibrate.py')
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def inventory():
    cohort = read(BASE / 'source-validation/cohort.json')['films']
    old = {f['imdb_id']: f for f in read(BASE / 'task2/results.json')['films']}
    observations = [(name, read(BASE / name)) for name in
                    ('inputs/observations.json', 'task2/inputs/observations.json')]
    entries = []
    for film in cohort:
        iid = film['imdb_id']
        for family, venues in policy.VENUES.items():
            for venue in venues:
                components = [k for k, v in policy.POLICY.items() if v[1] == venue]
                facts = {k: v for k, v in old[iid]['award_breakdown']['components'].items()
                         if k in components}
                checks = [{'packet': name, **c} for name, obs in observations
                          for c in obs['coverage_checks'] if iid in c['imdb_ids'] and c['venue'] == venue]
                gaps = []
                if not facts and not checks:
                    gaps.append('No retained fact or scoped check; absence unsupported.')
                if facts:
                    gaps.append('Positive facts do not establish absence in remaining categories/editions.')
                if any(c['status'] == 'unavailable' for c in checks):
                    gaps.append('Official record access failed in Task 2; do not treat as zero evidence.')
                if any(c['status'] == 'not_yet_announced' for c in checks):
                    gaps.append('Next release-season record remains pending; no film eligibility asserted.')
                missing = [c for c in components if c not in facts and not any(c in x.get('components', []) for x in checks)]
                if missing:
                    gaps.append('No component-specific retained check: ' + ', '.join(missing))
                entries.append({'imdb_id': iid, 'title': film['title'], 'institution': venue,
                                'family': family, 'components': components,
                                'retained_scored_components': facts, 'retained_checks': checks,
                                'known_gaps': gaps,
                                'focus_edition': (film['year'] + 1 if venue in ('Academy', 'Golden Globes', 'BAFTA', 'Spirit', 'Critics Choice') else
                                                  {2024: 2024, 2025: 2026, 2026: 2027}[film['year']] if venue == 'EFA' else film['year']),
                                'research_priority': 'access_or_attribution' if venue == 'LAFCA' or (iid == 'tt29271639' and venue == 'Berlin') else 'unchecked_scope' if missing else 'reuse_adequate_evidence',
                                'edition_envelope': [2024, 2025, 2026] if venue in ('Cannes', 'Venice', 'Berlin', 'Sundance', 'Gotham', 'NSFC', 'NYFCC', 'LAFCA') else [2024, 2026, 2027] if venue == 'EFA' else [2025, 2026, 2027]})
    return {'task': 4, 'prepared_before_new_checks': True, 'research_cutoff': '2026-10-28',
            'baseline_commit': '824ed090e93c69e7ee5af6fe7df398725d8a6056',
            'method': 'Derived only from Task 1/2; all 8 x 14 institutions. Edition envelope is an audit window, never inferred eligibility. Exact category/edition coverage expanded in coverage.json. Reuse adequate dated evidence; new checks must state their purpose.',
            'entries': entries}


if __name__ == '__main__':
    (ROOT / 'inputs/gap-inventory.json').write_text(json.dumps(inventory(), indent=2, ensure_ascii=False) + '\n')
