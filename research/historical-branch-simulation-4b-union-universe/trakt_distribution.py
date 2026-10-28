"""Research-only calibration of Trakt audience scoring.

Uses only cached ReelDB payloads already stored in audience-ratings.json.  The
active evidence model is not changed.  We compare several Trakt transforms,
inspect rating/vote distributions, and measure how a three-source audience
block capped at 200 would move rankings.
"""

import json
import math
from pathlib import Path

from evidence_score import _rating_component

RATINGS = Path("audience-ratings.json")
SCORES = Path("evidence-scores.json")
OUTPUT = Path("trakt-distribution.json")

FOCUS = {
    "Melancholia", "The Tree of Life", "Blade Runner 2049", "Memento", "1917",
    "La Commune (Paris, 1871)", "The Departed", "Arrival", "Ex Machina",
    "Into the Wild", "Midsommar", "Nocturnal Animals", "Scott Pilgrim vs. the World",
}

CURVES = {
    # Existing provisional curve copied from TMDb.
    "current_65_85_v100_10k": (65.0, 85.0, 100, 10_000),
    # Rating alternatives with the same breadth curve.
    "rating_60_85_v100_10k": (60.0, 85.0, 100, 10_000),
    "rating_65_90_v100_10k": (65.0, 90.0, 100, 10_000),
    "rating_60_90_v100_10k": (60.0, 90.0, 100, 10_000),
    # More conservative breadth alternatives.
    "current_rating_v250_25k": (65.0, 85.0, 250, 25_000),
    "conservative_65_90_v250_25k": (65.0, 90.0, 250, 25_000),
}


def quantile(values, q):
    vals = sorted(float(x) for x in values)
    if not vals:
        return None
    if len(vals) == 1:
        return round(vals[0], 3)
    pos = (len(vals) - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return round(vals[lo], 3)
    frac = pos - lo
    return round(vals[lo] * (1 - frac) + vals[hi] * frac, 3)


def describe(values):
    vals = [float(x) for x in values if isinstance(x, (int, float))]
    if not vals:
        return {"n": 0}
    return {
        "n": len(vals),
        "min": round(min(vals), 3),
        "p05": quantile(vals, 0.05),
        "p10": quantile(vals, 0.10),
        "p25": quantile(vals, 0.25),
        "median": quantile(vals, 0.50),
        "p75": quantile(vals, 0.75),
        "p90": quantile(vals, 0.90),
        "p95": quantile(vals, 0.95),
        "p99": quantile(vals, 0.99),
        "max": round(max(vals), 3),
        "mean": round(sum(vals) / len(vals), 3),
    }


def pearson(xs, ys):
    if len(xs) < 2 or len(xs) != len(ys):
        return None
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if not dx or not dy:
        return None
    return round(num / (dx * dy), 3)


def raw_trakt(ratings, imdb_id):
    rr = ((ratings.get("ratings") or {}).get(imdb_id) or {}).get("reeldb") or {}
    item = rr.get("trakt") or {}
    rating = item.get("rating")
    votes = item.get("votes") if item.get("votes") is not None else item.get("ratings")
    if not isinstance(rating, (int, float)) or not isinstance(votes, (int, float)):
        return None, None
    return float(rating), float(votes)


def curve_score(rating, votes, spec):
    floor, full, vote_low, vote_full = spec
    return _rating_component(rating, votes, floor, full, vote_low, vote_full)


def compact_curve_stats(values):
    positive = [x for x in values if x > 0]
    stats = describe(positive)
    stats.update({
        "zero_count": len(values) - len(positive),
        "positive_count": len(positive),
        "ge_50": sum(1 for x in values if x >= 50),
        "ge_75": sum(1 for x in values if x >= 75),
        "ge_90": sum(1 for x in values if x >= 90),
        "eq_100": sum(1 for x in values if x >= 99.999),
    })
    return stats


def active_point_distributions(score_rows):
    imdb = []
    lb = []
    for row in score_rows:
        points = row.get("source_points") or {}
        if isinstance(points.get("imdb_audience"), (int, float)):
            imdb.append(float(points["imdb_audience"]))
        if isinstance(points.get("letterboxd_audience"), (int, float)):
            lb.append(float(points["letterboxd_audience"]))
    return {
        "imdb_audience_positive": describe(imdb),
        "letterboxd_audience_positive": describe(lb),
    }


def rank_scenario(score_rows, ratings, curve):
    rows = []
    for row in score_rows:
        points = row.get("source_points") or {}
        imdb = float(points.get("imdb_audience") or 0.0)
        lb = float(points.get("letterboxd_audience") or 0.0)
        non_aud = float(row.get("overall_score") or 0.0) - imdb - lb
        rating, votes = raw_trakt(ratings, row.get("imdb_id"))
        trakt = curve_score(rating, votes, curve) if rating is not None else 0.0
        audience = (imdb + lb + trakt) * (2.0 / 3.0)
        x = {
            "title": row.get("title"),
            "year": row.get("year"),
            "imdb_id": row.get("imdb_id"),
            "score": round(non_aud + audience, 2),
            "audience": round(audience, 2),
            "imdb": round(imdb, 2),
            "letterboxd": round(lb, 2),
            "trakt": round(trakt, 2),
        }
        rows.append(x)
    rows.sort(key=lambda x: (-x["score"], x.get("title") or ""))
    for i, row in enumerate(rows, 1):
        row["rank"] = i
    return rows


def baseline_rows(score_rows):
    out = []
    for row in score_rows:
        out.append({
            "title": row.get("title"),
            "year": row.get("year"),
            "imdb_id": row.get("imdb_id"),
            "rank": row.get("overall_rank"),
            "score": row.get("overall_score"),
        })
    return out


def overlap(base, scenario, n):
    a = {x["imdb_id"] for x in base[:n]}
    b = {x["imdb_id"] for x in scenario[:n]}
    return len(a & b)


def controls(rows):
    by_title = {}
    for row in rows:
        if row.get("title") in FOCUS and row.get("title") not in by_title:
            by_title[row["title"]] = row
    return [by_title[t] for t in sorted(by_title)]


def main():
    ratings = json.loads(RATINGS.read_text())
    score_payload = json.loads(SCORES.read_text())
    score_rows = score_payload.get("films") or []

    raw_ratings, raw_votes = [], []
    curve_values = {name: [] for name in CURVES}
    correlations = {name: {"x": [], "y": []} for name in CURVES}

    for row in score_rows:
        rating, votes = raw_trakt(ratings, row.get("imdb_id"))
        if rating is None:
            continue
        raw_ratings.append(rating)
        raw_votes.append(votes)
        points = row.get("source_points") or {}
        imdb = float(points.get("imdb_audience") or 0.0)
        lb = float(points.get("letterboxd_audience") or 0.0)
        reference_components = [x for x in (imdb, lb) if x > 0]
        reference = sum(reference_components) / len(reference_components) if reference_components else None
        for name, spec in CURVES.items():
            score = curve_score(rating, votes, spec)
            curve_values[name].append(score)
            if score > 0 and reference is not None:
                correlations[name]["x"].append(score)
                correlations[name]["y"].append(reference)

    base = baseline_rows(score_rows)
    scenarios = {name: rank_scenario(score_rows, ratings, spec) for name, spec in CURVES.items()}

    curve_summary = {}
    for name, spec in CURVES.items():
        vals = curve_values[name]
        scenario = scenarios[name]
        curve_summary[name] = {
            "parameters": {
                "rating_floor": spec[0], "rating_full": spec[1],
                "vote_low": spec[2], "vote_full": spec[3],
            },
            "point_distribution": compact_curve_stats(vals),
            "corr_with_mean_imdb_letterboxd_points": pearson(correlations[name]["x"], correlations[name]["y"]),
            "correlation_n": len(correlations[name]["x"]),
            "top_overlap_vs_two_source_baseline": {str(n): overlap(base, scenario, n) for n in (50, 100, 200, 300, 500)},
            "focus_controls": controls(scenario),
        }

    output = {
        "mode": "trakt-distribution-v1",
        "production_unchanged": True,
        "qualification_unchanged": True,
        "film_count": len(score_rows),
        "raw_trakt": {
            "rating_0_100": describe(raw_ratings),
            "votes": describe(raw_votes),
            "vote_threshold_counts": {
                "ge_100": sum(1 for x in raw_votes if x >= 100),
                "ge_250": sum(1 for x in raw_votes if x >= 250),
                "ge_1000": sum(1 for x in raw_votes if x >= 1000),
                "ge_5000": sum(1 for x in raw_votes if x >= 5000),
                "ge_10000": sum(1 for x in raw_votes if x >= 10000),
                "ge_25000": sum(1 for x in raw_votes if x >= 25000),
                "ge_50000": sum(1 for x in raw_votes if x >= 50000),
            },
        },
        "active_audience_point_distributions": active_point_distributions(score_rows),
        "curves": curve_summary,
    }
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")

    concise = {
        "raw_trakt": output["raw_trakt"],
        "active_audience": output["active_audience_point_distributions"],
        "curves": {
            name: {
                "parameters": data["parameters"],
                "point_distribution": data["point_distribution"],
                "corr": data["corr_with_mean_imdb_letterboxd_points"],
                "overlap": data["top_overlap_vs_two_source_baseline"],
            }
            for name, data in curve_summary.items()
        },
    }
    print(json.dumps(concise, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
