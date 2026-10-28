"""Compare 150-point and 200-point audience weighting on the research evidence table.

Research only: this does not change qualification or production scoring.
"""

import json
from pathlib import Path

INPUT = Path("evidence-scores.json")
OUTPUT = Path("audience-150-vs-200.json")


def adjusted(rows, multiplier):
    out = []
    for row in rows:
        audience = float((row.get("source_points") or {}).get("audience_consensus") or 0.0)
        score = round(float(row.get("overall_score") or 0.0) + (multiplier - 1.0) * audience, 2)
        out.append({**row, "audience_points": audience, "adjusted_score": score})
    out.sort(key=lambda r: (-r["adjusted_score"], -r.get("source_hits", 0), r.get("title") or ""))
    for rank, row in enumerate(out, 1):
        row["adjusted_rank"] = rank
    return out


def key(row):
    return row.get("imdb_id") or f"{row.get('title')}|{row.get('year')}"


def compact(row):
    return {
        "title": row.get("title"),
        "year": row.get("year"),
        "imdb_id": row.get("imdb_id"),
        "audience": row.get("audience_points", 0.0),
        "source_hits": row.get("source_hits", 0),
        "routes": row.get("routes", []),
        "qualified": bool(row.get("qualified")),
    }


def main():
    payload = json.loads(INPUT.read_text())
    rows = payload.get("films", [])
    r150 = adjusted(rows, 1.5)
    r200 = adjusted(rows, 2.0)
    by150 = {key(r): r for r in r150}
    by200 = {key(r): r for r in r200}

    movement = []
    for k, a in by150.items():
        b = by200[k]
        movement.append({
            **compact(a),
            "rank_150": a["adjusted_rank"],
            "rank_200": b["adjusted_rank"],
            "rank_change": a["adjusted_rank"] - b["adjusted_rank"],
            "score_150": a["adjusted_score"],
            "score_200": b["adjusted_score"],
        })

    upward = sorted(movement, key=lambda x: (-x["rank_change"], -x["audience"], x["title"] or ""))
    downward = sorted(movement, key=lambda x: (x["rank_change"], x["audience"], x["title"] or ""))

    cutoffs = {}
    for n in (50, 100, 200, 300, 500):
        a_ids = {key(r) for r in r150[:n]}
        b_ids = {key(r) for r in r200[:n]}
        entered_ids = b_ids - a_ids
        exited_ids = a_ids - b_ids
        entered = sorted((by200[k] for k in entered_ids), key=lambda r: r["adjusted_rank"])
        exited = sorted((by150[k] for k in exited_ids), key=lambda r: r["adjusted_rank"])
        cutoffs[str(n)] = {
            "overlap": len(a_ids & b_ids),
            "entered_at_200": [
                {**compact(r), "rank_200": r["adjusted_rank"], "rank_150": by150[key(r)]["adjusted_rank"]}
                for r in entered
            ],
            "exited_at_200": [
                {**compact(r), "rank_150": r["adjusted_rank"], "rank_200": by200[key(r)]["adjusted_rank"]}
                for r in exited
            ],
        }

    def summary(rows_adjusted):
        top50 = rows_adjusted[:50]
        top100 = rows_adjusted[:100]
        return {
            "top50_mean_audience": round(sum(r["audience_points"] for r in top50) / len(top50), 2),
            "top100_mean_audience": round(sum(r["audience_points"] for r in top100) / len(top100), 2),
            "top50_audience_75_plus": sum(r["audience_points"] >= 75 for r in top50),
            "top100_audience_75_plus": sum(r["audience_points"] >= 75 for r in top100),
            "top50_audience_below_50": sum(0 < r["audience_points"] < 50 for r in top50),
            "top100_audience_below_50": sum(0 < r["audience_points"] < 50 for r in top100),
        }

    thin_evidence_climbers = [
        x for x in upward
        if x["rank_change"] > 0 and x["source_hits"] <= 2 and x["audience"] >= 70
    ][:30]

    result = {
        "mode": "audience-150-vs-200-v1",
        "production_unchanged": True,
        "qualification_unchanged": True,
        "film_count": len(rows),
        "summary_150": summary(r150),
        "summary_200": summary(r200),
        "cutoffs": cutoffs,
        "largest_upward_movers": upward[:40],
        "largest_downward_movers": downward[:40],
        "thin_evidence_high_audience_climbers": thin_evidence_climbers,
    }
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")

    print(json.dumps({
        "film_count": result["film_count"],
        "summary_150": result["summary_150"],
        "summary_200": result["summary_200"],
        "cutoff_changes": {
            n: {
                "overlap": v["overlap"],
                "entered": [x["title"] for x in v["entered_at_200"]],
                "exited": [x["title"] for x in v["exited_at_200"]],
            }
            for n, v in cutoffs.items()
        },
        "up": [{"title": x["title"], "delta": x["rank_change"], "r150": x["rank_150"], "r200": x["rank_200"], "aud": x["audience"], "hits": x["source_hits"]} for x in upward[:20]],
        "down": [{"title": x["title"], "delta": x["rank_change"], "r150": x["rank_150"], "r200": x["rank_200"], "aud": x["audience"], "hits": x["source_hits"]} for x in downward[:20]],
        "thin": [{"title": x["title"], "delta": x["rank_change"], "r150": x["rank_150"], "r200": x["rank_200"], "aud": x["audience"], "hits": x["source_hits"]} for x in thin_evidence_climbers[:20]],
    }, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
