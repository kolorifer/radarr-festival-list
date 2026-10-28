"""Inspect the frozen 1000-point research score without choosing a threshold.

This is diagnostic only. It reports score bands, current route-qualified vs
unqualified films, audience-discovery coverage, and the calibration controls we
care about before any score is allowed to drive selection.
"""

import json
from pathlib import Path

SCORES = Path("evidence-scores.json")
OUTPUT = Path("score-band-analysis.json")

BANDS = (600, 500, 450, 400, 350, 300, 250, 200, 150, 100)
FOCUS = {
    "Dune: Part Two", "The Machinist", "Tenet", "The Batman",
    "Blade Runner 2049", "Ex Machina", "Midsommar", "Nocturnal Animals",
    "Scott Pilgrim vs. the World", "La Commune (Paris, 1871)",
}


def compact(row):
    return {
        "rank": row.get("overall_rank"),
        "title": row.get("title"),
        "year": row.get("year"),
        "imdb_id": row.get("imdb_id"),
        "score": row.get("overall_score"),
        "eligible_max": row.get("eligible_max_score"),
        "audience": row.get("audience_score"),
        "audience_raw": row.get("audience_raw_points"),
        "gateway": row.get("audience_gateway_pass"),
        "non_audience": row.get("has_non_audience_evidence"),
        "qualified": row.get("qualified"),
        "routes": row.get("routes", []),
        "sources": row.get("candidate_sources", []),
    }


def main():
    payload = json.loads(SCORES.read_text())
    rows = payload.get("films") or []

    bands = {}
    previous = None
    for floor in BANDS:
        if previous is None:
            selected = [r for r in rows if r.get("overall_score", 0) >= floor]
            label = f">={floor}"
        else:
            selected = [r for r in rows if floor <= r.get("overall_score", 0) < previous]
            label = f"{floor}-{previous - 0.01:.2f}"
        bands[label] = {
            "count": len(selected),
            "qualified": sum(bool(r.get("qualified")) for r in selected),
            "unqualified": sum(not r.get("qualified") for r in selected),
            "gateway": sum(bool(r.get("audience_gateway_pass")) for r in selected),
            "audience_only": sum(bool(r.get("audience_only_candidate")) for r in selected),
        }
        previous = floor

    high_unqualified = [compact(r) for r in rows if not r.get("qualified") and r.get("overall_score", 0) >= 200][:100]
    qualified_low = [compact(r) for r in rows if r.get("qualified") and r.get("overall_score", 0) < 200]
    qualified_low.sort(key=lambda r: (r["score"], r["title"] or ""))

    discovery = [r for r in rows if r.get("audience_discovery_seed")]
    discovery_gateway = [r for r in discovery if r.get("audience_gateway_pass")]
    discovery_nonaud = [r for r in discovery_gateway if r.get("has_non_audience_evidence")]
    discovery_audience_only = [r for r in discovery_gateway if not r.get("has_non_audience_evidence")]
    incomplete = [
        r for r in discovery
        if sum(1 for v in (r.get("audience_raw_points") or {}).values() if v > 0) < 3
    ]

    by_title = {r.get("title"): r for r in rows if r.get("title")}
    focus = {title: compact(by_title[title]) if title in by_title else None for title in sorted(FOCUS)}

    output = {
        "mode": "research-score-band-analysis-v1",
        "qualification_unchanged": True,
        "film_count": len(rows),
        "score_ceiling": payload.get("current_score_ceiling"),
        "bands": bands,
        "top_cutoffs": {
            str(n): {
                "score_at_cutoff": rows[n - 1]["overall_score"] if len(rows) >= n else None,
                "qualified": sum(bool(r.get("qualified")) for r in rows[:n]),
                "gateway": sum(bool(r.get("audience_gateway_pass")) for r in rows[:n]),
            }
            for n in (50, 100, 150, 200, 250, 300, 400, 500) if len(rows) >= n
        },
        "discovery": {
            "seeds": len(discovery),
            "gateway_pass": len(discovery_gateway),
            "gateway_with_non_audience_evidence": len(discovery_nonaud),
            "gateway_audience_only": len(discovery_audience_only),
            "incomplete_three_source_audience": len(incomplete),
            "top_gateway_audience_only": [compact(r) for r in discovery_audience_only[:50]],
        },
        "high_score_unqualified": high_unqualified,
        "qualified_below_200": qualified_low[:100],
        "focus": focus,
    }
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({
        "films": len(rows),
        "bands": bands,
        "discovery": output["discovery"] | {"top_gateway_audience_only": "omitted"},
        "focus": focus,
    }, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
