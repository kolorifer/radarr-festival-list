"""Audit low-scoring calibration films for missing independent evidence coverage.

This is diagnostic only. The calibration set is never used as a scoring source;
it simply helps distinguish a genuinely weak multi-source record from a film that
is low because one or more evidence families have not been ingested.
"""

import json
from pathlib import Path

SCORES = Path("evidence-scores.json")
RATINGS = Path("audience-ratings.json")
OUTPUT_JSON = Path("missing-evidence-audit.json")
OUTPUT_MD = Path("missing-evidence-audit.md")

TARGETS = {
    "Blade Runner 2049": 2017,
    "Ex Machina": 2014,
    "Scott Pilgrim vs. the World": 2010,
    "The Batman": 2022,
    "Midsommar": 2019,
    "Nocturnal Animals": 2016,
    "The Machinist": 2004,
    "Tenet": 2020,
    "Into the Wild": 2007,
    "The Killing of a Sacred Deer": 2017,
    "Shame": 2011,
}

GROUPS = {
    "canon": ("tspdt_21c", "sight_sound"),
    "bbc": ("bbc_21c",),
    "nyt": ("nyt_21c",),
    "us": ("us_institutional",),
    "europe": ("european_recognition",),
    "indie": ("independent_cinema",),
    "critics": ("critics_groups_consensus",),
}

LABELS = {
    "canon": "Canon",
    "bbc": "BBC",
    "nyt": "NYT",
    "us": "US inst.",
    "europe": "Europe",
    "indie": "Indie",
    "critics": "Critics",
}


def find_target(rows, title, year):
    exact = [r for r in rows if r.get("title") == title and str(r.get("year") or "") == str(year)]
    if len(exact) == 1:
        return exact[0]
    nearby = [
        r for r in rows
        if r.get("title") == title
        and str(r.get("year") or "").isdigit()
        and abs(int(r.get("year")) - int(year)) <= 1
    ]
    return nearby[0] if len(nearby) == 1 else None


def grouped_points(row):
    points = row.get("source_points") or {}
    return {
        group: round(sum(float(points.get(key) or 0) for key in keys), 2)
        for group, keys in GROUPS.items()
    }


def critic_cache(rr):
    out = {}
    for source in ("metacritic", "tomatoes", "roger_ebert"):
        value = (rr or {}).get(source) or {}
        if value:
            out[source] = {
                "rating": value.get("rating"),
                "votes_or_reviews": value.get("votes"),
            }
    return out


def compact_evidence(row):
    evidence = row.get("source_evidence") or {}
    out = {}
    for group, keys in GROUPS.items():
        items = []
        for key in keys:
            items.extend(evidence.get(key) or [])
        if items:
            out[group] = items
    return out


def diagnosis(row, groups):
    active = [key for key, value in groups.items() if value > 0]
    audience = float(row.get("audience_score") or 0)
    score = float(row.get("overall_score") or 0)
    if len(active) <= 2 and audience >= 130:
        return "strong-audience-sparse-nonaudience-coverage"
    if len(active) <= 2:
        return "sparse-nonaudience-coverage"
    if score < 225 and len(active) >= 4:
        return "broad-coverage-but-low-strength"
    if score < 225:
        return "moderate-coverage-below-threshold"
    return "above-225-review-floor"


def build_markdown(payload):
    lines = [
        "# Missing-evidence audit for calibration controls",
        "",
        "Diagnostic only. These films do not influence scoring weights or qualification; they are used to expose coverage gaps.",
        "",
        "| Film | Score / rank | Audience | Active non-audience families | Missing families | Diagnosis |",
        "|---|---:|---:|---|---|---|",
    ]
    for row in payload["films"]:
        active = ", ".join(f"{LABELS[k]} {v:.0f}" for k, v in row["non_audience_points"].items() if v > 0) or "none"
        missing = ", ".join(LABELS[k] for k in row["missing_non_audience_families"]) or "none"
        lines.append(
            f"| {row['title']} ({row['year']}) | {row['score']:.1f} / #{row['rank']} | {row['audience']:.1f} | "
            f"{active} | {missing} | {row['diagnosis']} |"
        )

    lines.extend(["", "## Existing evidence detail", ""])
    for row in payload["films"]:
        lines.append(f"### {row['title']} ({row['year']})")
        lines.append("")
        lines.append(
            f"Score **{row['score']:.1f}**, rank **#{row['rank']}**, audience **{row['audience']:.1f}/200**, "
            f"qualified={str(row['qualified']).lower()}, routes={', '.join(row['routes']) or 'none'}."
        )
        for group, items in row["evidence"].items():
            lines.append(f"- **{LABELS[group]}:** " + "; ".join(str(x) for x in items))
        cache = row.get("cached_critic_data") or {}
        if cache:
            text = "; ".join(
                f"{name}: rating={value.get('rating')}, reviews={value.get('votes_or_reviews')}"
                for name, value in cache.items()
            )
            lines.append(f"- **Cached critic aggregates:** {text}")
        lines.append("")
    return "\n".join(lines)


def main():
    scores = json.loads(SCORES.read_text(encoding="utf-8"))
    ratings = json.loads(RATINGS.read_text(encoding="utf-8")).get("ratings") or {}
    rows = scores.get("films") or []
    audited = []
    missing_targets = []

    for title, year in TARGETS.items():
        row = find_target(rows, title, year)
        if not row:
            missing_targets.append({"title": title, "year": year})
            continue
        groups = grouped_points(row)
        rr = ((ratings.get(row.get("imdb_id")) or {}).get("reeldb") or {})
        audited.append({
            "title": row.get("title"),
            "year": row.get("year"),
            "imdb_id": row.get("imdb_id"),
            "score": float(row.get("overall_score") or 0),
            "rank": row.get("overall_rank"),
            "eligible_max": row.get("eligible_max_score"),
            "eligible_pct": row.get("eligible_score_pct"),
            "audience": float(row.get("audience_score") or 0),
            "audience_gateway": bool(row.get("audience_gateway_pass")),
            "qualified": bool(row.get("qualified")),
            "routes": row.get("routes") or [],
            "candidate_sources": row.get("candidate_sources") or [],
            "non_audience_points": groups,
            "active_non_audience_families": [key for key, value in groups.items() if value > 0],
            "missing_non_audience_families": [key for key, value in groups.items() if value <= 0],
            "evidence": compact_evidence(row),
            "cached_critic_data": critic_cache(rr),
            "diagnosis": diagnosis(row, groups),
        })

    audited.sort(key=lambda row: (-row["score"], row["title"]))
    payload = {
        "mode": "research-missing-evidence-audit-v1",
        "qualification_unchanged": True,
        "score_mode": scores.get("mode"),
        "policy": "Calibration controls reveal source coverage gaps only; they are never a scoring source.",
        "films": audited,
        "missing_targets": missing_targets,
    }
    OUTPUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUTPUT_MD.write_text(build_markdown(payload), encoding="utf-8")
    print(json.dumps({
        "audited": len(audited),
        "missing": missing_targets,
        "summary": [
            {
                "title": row["title"],
                "score": row["score"],
                "families": row["active_non_audience_families"],
                "missing_families": row["missing_non_audience_families"],
                "diagnosis": row["diagnosis"],
            }
            for row in audited
        ],
    }, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
