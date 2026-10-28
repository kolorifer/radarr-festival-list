"""Compare hybrid final-selection policies on the research score.

The continuous evidence score is now strong enough to propose candidates, but the
frozen Phase-4 routes still contain useful historical/canonical signal. This
experiment compares unions and bounded legacy overrides without changing either
research scores or production qualification.
"""

import json
from pathlib import Path

from score_rule_experiment import non_audience_hits

SCORES = Path("evidence-scores.json")
OUTPUT = Path("hybrid-selection-experiment.json")

POLICIES = {
    "union250_all_legacy": {"new_floor": 250, "legacy_floor": 0, "protect_multi_route": True, "min_non_audience_families": 1},
    "union225_all_legacy": {"new_floor": 225, "legacy_floor": 0, "protect_multi_route": True, "min_non_audience_families": 1},
    "balanced250_legacy150": {"new_floor": 250, "legacy_floor": 150, "protect_multi_route": True, "min_non_audience_families": 1},
    "balanced225_legacy150": {"new_floor": 225, "legacy_floor": 150, "protect_multi_route": True, "min_non_audience_families": 1},
    "balanced225_legacy175": {"new_floor": 225, "legacy_floor": 175, "protect_multi_route": True, "min_non_audience_families": 1},
    "balanced225_legacy175_twofam": {"new_floor": 225, "legacy_floor": 175, "protect_multi_route": True, "min_non_audience_families": 2},
    "clean225_legacy200": {"new_floor": 225, "legacy_floor": 200, "protect_multi_route": True, "min_non_audience_families": 1},
}


def has_nonaudience(row):
    return bool(row.get("has_non_audience_evidence"))


def legacy_keep(row, legacy_floor, protect_multi_route):
    if not row.get("qualified"):
        return False
    score = float(row.get("overall_score") or 0)
    if score >= legacy_floor:
        return True
    if protect_multi_route and len(row.get("routes") or []) >= 2:
        return True
    return False


def score_keep(row, new_floor, min_non_audience_families=1):
    return (
        float(row.get("overall_score") or 0) >= new_floor
        and has_nonaudience(row)
        and non_audience_hits(row) >= min_non_audience_families
    )


def compact(row):
    return {
        "rank": row.get("overall_rank"),
        "title": row.get("title"),
        "year": row.get("year"),
        "imdb_id": row.get("imdb_id"),
        "score": row.get("overall_score"),
        "audience": row.get("audience_score"),
        "non_audience_families": non_audience_hits(row),
        "old_qualified": bool(row.get("qualified")),
        "routes": row.get("routes") or [],
    }


def evaluate(rows, policy):
    selected = []
    reasons = {}
    min_families = int(policy.get("min_non_audience_families") or 1)
    for row in rows:
        iid = row.get("imdb_id")
        by_score = score_keep(row, policy["new_floor"], min_families)
        by_legacy = legacy_keep(row, policy["legacy_floor"], policy["protect_multi_route"])
        if by_score or by_legacy:
            selected.append(row)
            reasons[iid] = {
                "score": by_score,
                "legacy": by_legacy,
                "protected_multi_route": bool(
                    row.get("qualified")
                    and float(row.get("overall_score") or 0) < policy["legacy_floor"]
                    and len(row.get("routes") or []) >= 2
                ),
            }

    selected_ids = {r.get("imdb_id") for r in selected}
    old = [r for r in rows if r.get("qualified")]
    old_ids = {r.get("imdb_id") for r in old}
    promotions = [r for r in selected if r.get("imdb_id") not in old_ids]
    dropped_old = [r for r in old if r.get("imdb_id") not in selected_ids]
    protected = [r for r in selected if reasons[r.get("imdb_id")]["protected_multi_route"]]

    return {
        "selected": len(selected),
        "promotions_vs_old": len(promotions),
        "legacy_retained": len(old_ids & selected_ids),
        "legacy_dropped": len(dropped_old),
        "multi_route_protected_below_legacy_floor": len(protected),
        "lowest_selected": [compact(r) for r in selected[-25:]],
        "top_promotions": [compact(r) for r in promotions[:60]],
        "legacy_dropped_lowest": [
            compact(r) for r in sorted(dropped_old, key=lambda x: (float(x.get("overall_score") or 0), x.get("title") or ""))[:80]
        ],
        "multi_route_protected": [
            compact(r) for r in sorted(protected, key=lambda x: (float(x.get("overall_score") or 0), x.get("title") or ""))
        ],
    }


def main():
    payload = json.loads(SCORES.read_text(encoding="utf-8"))
    rows = payload.get("films") or []
    results = {name: evaluate(rows, policy) for name, policy in POLICIES.items()}

    old_low = [r for r in rows if r.get("qualified") and float(r.get("overall_score") or 0) < 225]
    out = {
        "mode": "research-hybrid-selection-experiment-v2-two-family-safeguard",
        "qualification_unchanged": True,
        "score_mode": payload.get("mode"),
        "policy_note": "Score-based promotion always requires non-audience evidence. The guarded variant requires two independent non-audience families, with TSPDT + Sight & Sound counted as one correlated canon family. Legacy policies may retain old route qualifiers below the score floor; multi-route legacy films are protected in all bounded variants.",
        "film_count": len(rows),
        "old_qualified_count": sum(bool(r.get("qualified")) for r in rows),
        "old_qualifiers_below_225": len(old_low),
        "policies": {name: {**POLICIES[name], **result} for name, result in results.items()},
        "legacy_below_225": [compact(r) for r in sorted(old_low, key=lambda x: float(x.get("overall_score") or 0))],
    }
    OUTPUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "films": len(rows),
        "old": out["old_qualified_count"],
        "old_below_225": len(old_low),
        "policies": {
            name: {
                k: result[k]
                for k in ("selected", "promotions_vs_old", "legacy_retained", "legacy_dropped", "multi_route_protected_below_legacy_floor")
            }
            for name, result in results.items()
        },
    }, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
