"""Production D012 Evidence Score and D016 admission.

Promoted calibrated arithmetic from PR #5, without the research CLI, alternative
models, legacy admission gates or network access. Normalized award-source data
is frozen separately from ratings/ranks, preserving validated attribution.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
THRESHOLD = 225
AUDIENCE_MAX = 150
EFFECTIVE_CEILING = 1000
FAMILY_WEIGHTS = {
    "tspdt_21c": 100, "sight_sound": 100, "bbc_21c": 100,
    "nyt_21c": 100, "us_institutional": 100,
    "european_recognition": 200, "independent_cinema": 100,
    "critics_groups_consensus": 100,
}
BROAD_CAP = 40.0
CANON_JOINT_MAX = 150.0
SIGHT_SOUND_CORROBORATION_FACTOR = 0.5
GRANDFATHERED_SHA256 = "283ae2edec4b97cf4ba358e8941decc390480650333c3f098a41468b202435fb"
BASELINE_COMMIT = "c7a458241b4a8a2acbd4d4f5a957d71e5198adc1"

def ranked_points(rank, depth):
    """Map rank 1..depth onto 100..1 linearly."""
    if not isinstance(rank, int) or not isinstance(depth, int) or depth < 1:
        return 0.0
    if rank < 1 or rank > depth:
        return 0.0
    if depth == 1:
        return 100.0
    return round(100.0 - (99.0 * (rank - 1) / (depth - 1)), 2)


def clamp01(value):
    return max(0.0, min(1.0, float(value)))


def log_confidence(votes, low=1000, full=100000):
    """Log-scaled breadth confidence: tiny samples are strongly discounted."""
    if not isinstance(votes, (int, float)) or votes <= low:
        return 0.0
    if votes >= full:
        return 1.0
    return clamp01(math.log10(votes / low) / math.log10(full / low))


def _rating_component(rating, votes, rating_floor, rating_full, vote_low, vote_full):
    if not isinstance(rating, (int, float)) or not isinstance(votes, (int, float)):
        return 0.0
    if rating_full <= rating_floor:
        return 0.0
    quality = clamp01((float(rating) - rating_floor) / (rating_full - rating_floor)) * 100.0
    return round(quality * log_confidence(votes, vote_low, vote_full), 2)


def imdb_points(reeldb):
    imdb = (reeldb or {}).get("imdb") or {}
    return _rating_component(imdb.get("rating"), imdb.get("votes"), 6.5, 8.5, 1000, 100000)


def letterboxd_points(reeldb):
    lb = (reeldb or {}).get("letterboxd") or {}
    votes = lb.get("votes") if lb.get("votes") is not None else lb.get("ratings")
    return _rating_component(lb.get("rating"), votes, 3.0, 4.3, 1000, 100000)


def critic_component(rating, reviews, rating_floor, rating_full, review_min, review_full):
    if not isinstance(rating, (int, float)) or not isinstance(reviews, (int, float)):
        return 0.0
    if reviews < review_min or rating <= rating_floor:
        return 0.0
    quality = clamp01((float(rating) - rating_floor) / (rating_full - rating_floor)) * 100.0
    if reviews >= review_full:
        confidence = 1.0
    else:
        breadth = clamp01(math.log(float(reviews) / review_min) / math.log(review_full / review_min))
        confidence = 0.6 + 0.4 * breadth
    return round(quality * confidence, 2)


def broad_critic_raw(reeldb):
    """Return raw 0..100 broad critic consensus plus its two components."""
    mc = (reeldb or {}).get("metacritic") or {}
    rt = (reeldb or {}).get("tomatoes") or {}
    mc_score = critic_component(mc.get("rating"), mc.get("votes"), 65.0, 90.0, 15, 60)
    rt_score = critic_component(rt.get("rating"), rt.get("votes"), 70.0, 95.0, 50, 250)
    available = [value for value in (mc_score, rt_score) if value > 0]
    if len(available) == 2:
        combined = sum(available) / 2.0
    elif len(available) == 1:
        combined = available[0] * 0.75
    else:
        combined = 0.0
    return round(combined, 2), round(mc_score, 2), round(rt_score, 2)


def broad_critic_points(reeldb):
    raw, _, _ = broad_critic_raw(reeldb)
    return round(raw * BROAD_CAP / 100.0, 2)


def merge_critics_family(existing, broad_points):
    """Keep the stronger critic signal and add 25% corroboration from the weaker."""
    existing = float(existing or 0)
    broad_points = float(broad_points or 0)
    if existing <= 0:
        return round(min(100.0, broad_points), 2)
    if broad_points <= 0:
        return round(min(100.0, existing), 2)
    return round(min(100.0, max(existing, broad_points) + 0.25 * min(existing, broad_points)), 2)


def adjusted_sight_sound(tspdt, sight_sound):
    tspdt = float(tspdt or 0)
    sight_sound = float(sight_sound or 0)
    if sight_sound <= 0:
        return 0.0
    if tspdt <= 0:
        return round(min(100.0, sight_sound), 2)
    room = max(0.0, CANON_JOINT_MAX - tspdt)
    return round(min(room, sight_sound * SIGHT_SOUND_CORROBORATION_FACTOR), 2)



def encode(value):
    return (json.dumps(value, ensure_ascii=False, separators=(",", ":"),
                       allow_nan=False) + "\n").encode("utf-8")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def unique_rows(rows):
    result = {}
    for row in rows:
        iid = row.get("imdb_id")
        if not isinstance(iid, str) or not re.fullmatch(r"tt[0-9]+", iid) or iid in result:
            raise ValueError("Invalid or duplicate IMDb identity")
        result[iid] = row
    return result


def load_grandfathered(root=ROOT):
    path = root / "production/grandfathered-224.json"
    if hashlib.sha256(path.read_bytes()).hexdigest() != GRANDFATHERED_SHA256:
        raise ValueError("Frozen deployed-224 identity/route snapshot changed")
    payload = read_json(path)
    rows = unique_rows(payload["films"])
    if len(rows) != 224 or payload["deployed_commit"] != BASELINE_COMMIT:
        raise ValueError("Invalid deployed-224 baseline")
    return rows


def qualification(imdb_id, score, grandfathered):
    if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score) or score < 0:
        raise ValueError("Evidence Score must be finite and nonnegative")
    routes = []
    if imdb_id in grandfathered:
        routes.append("grandfathered_production")
    if score >= THRESHOLD:
        routes.append("evidence_score_225")
    return bool(routes), routes


def score_film(film, ranked_sources):
    """Apply the frozen D012 sequence and rounding, including canon correlation."""
    year = film.get("year")
    year_int = int(year) if str(year).isdigit() else None
    points = {key: 0.0 for key in FAMILY_WEIGHTS}
    eligible = {key: True for key in FAMILY_WEIGHTS}
    points["tspdt_21c"] = ranked_points(film.get("tspdt_rank"), 1000)
    for key in ("sight_sound", "bbc_21c", "nyt_21c"):
        spec = ranked_sources[key]
        cutoff = spec.get("eligible_through_year")
        if year_int and cutoff and year_int > int(cutoff):
            eligible[key] = False
        elif key in film.get("ranked_positions", {}):
            points[key] = ranked_points(int(film["ranked_positions"][key]),
                                        int(spec["published_depth"]))
    for key in ("us_institutional", "european_recognition",
                "independent_cinema", "critics_groups_consensus"):
        value = film.get("family_scores", {}).get(key)
        if isinstance(value, (int, float)) and value > 0:
            points[key] = round(min(100.0, float(value)), 2)
    ratings = film.get("ratings") or {}
    points["critics_groups_consensus"] = merge_critics_family(
        points["critics_groups_consensus"], broad_critic_points(ratings))
    points["sight_sound"] = adjusted_sight_sound(
        points["tspdt_21c"], points["sight_sound"])
    points = {key: round(value * FAMILY_WEIGHTS[key] / 100, 2)
              for key, value in points.items()}
    raw = {"imdb": imdb_points(ratings), "letterboxd": letterboxd_points(ratings)}
    # Preserve two-stage rounding from audience_cap_simulation.score_variant.
    audience = round(round(sum(raw.values()), 2) * 150 / 200, 2)
    non_audience = round(sum(points.values()), 2)
    eligible_max = sum(FAMILY_WEIGHTS[k] for k, ok in eligible.items() if ok)
    if year_int and year_int <= 2022:
        eligible_max -= 50
    return {
        "overall_score": round(non_audience + audience, 2),
        "audience_score": audience,
        "non_audience_score": non_audience,
        "source_points": {**points, "audience": audience},
        "eligible_max_score": eligible_max + AUDIENCE_MAX,
        "source_hits": sum(v > 0 for v in points.values()) + sum(v > 0 for v in raw.values()),
    }


def build_catalog(inputs, grandfathered):
    source = unique_rows(inputs["films"])
    if not set(grandfathered) <= source.keys():
        raise ValueError("A grandfathered identity is absent from the candidate universe")
    result = []
    for iid, film in source.items():
        scored = score_film(film, inputs["ranked_sources"])
        qualified, routes = qualification(iid, scored["overall_score"], grandfathered)
        ratings = film.get("ratings") or {}
        row = {
            "imdb_id": iid, "title": film["title"], "year": film["year"],
            "aliases": film.get("aliases", []), **scored,
            "qualified": qualified, "routes": routes,
            "grandfathered": iid in grandfathered,
            "legacy_routes": {
                "deployed": grandfathered.get(iid, {}).get("legacy_routes", []),
                "research": film.get("legacy_research_routes", []),
            },
            "tspdt_rank": film.get("tspdt_rank"),
            "imdb": ratings.get("imdb", {}), "letterboxd": ratings.get("letterboxd", {}),
            "audience_complete": all(film["audience_coverage"][k]["available"]
                                     for k in ("imdb", "letterboxd")),
            "institutional_signals": film.get("institutional_signals", []),
            "institutional_strength": film.get("institutional_strength", 0),
            "watch_state": film.get("watch_state", "unknown"),
        }
        result.append(row)
    result.sort(key=lambda r: (-r["overall_score"], -r["source_hits"],
                               r.get("title") or "", r["imdb_id"]))
    for rank, row in enumerate(result, 1):
        row["overall_rank"] = rank
    return {
        "schema_version": 1, "policy": "D016",
        "rule": "grandfathered_production OR evidence_score >= 225",
        "threshold_inclusive": THRESHOLD, "audience_max": AUDIENCE_MAX,
        "effective_ceiling": EFFECTIVE_CEILING, "family_weights": FAMILY_WEIGHTS,
        "grandfathered_revision": BASELINE_COMMIT,
        "source_revision": inputs["source_commit"],
        "input_sha256": hashlib.sha256(encode(inputs)).hexdigest(),
        "grandfathered_count": len(grandfathered),
        "candidate_count": len(result),
        "qualified_count": sum(row["qualified"] for row in result),
        "new_count": sum(row["qualified"] and not row["grandfathered"] for row in result),
        "films": result,
    }


def validate_frozen(catalog, root=ROOT):
    expected = read_json(root / "tests/fixtures/d016-frozen-scores.json")["films"]
    actual = unique_rows(catalog["films"])
    if set(actual) != set(expected) or len(actual) != 1909:
        raise ValueError("Frozen candidate universe drift")
    for iid, fields in expected.items():
        if any(actual[iid].get(key) != value for key, value in fields.items()):
            raise ValueError("Frozen score drift for " + iid)
    counts = (catalog["grandfathered_count"], catalog["new_count"],
              catalog["qualified_count"])
    if counts != (224, 163, 387):
        raise ValueError("Frozen D016 qualification count drift")


def load_catalog(root=ROOT):
    """Fail closed on missing/corrupt data; never fall back to legacy qualifiers."""
    payload = read_json(root / "production/movie-catalog.json")
    baseline = load_grandfathered(root)
    rows = unique_rows(payload["films"])
    if payload.get("policy") != "D016" or payload.get("threshold_inclusive") != THRESHOLD:
        raise ValueError("Unexpected production qualification policy")
    if not set(baseline) <= rows.keys():
        raise ValueError("Incomplete production grandfathered baseline")
    for iid, row in rows.items():
        qualified, routes = qualification(iid, row["overall_score"], baseline)
        if (row["qualified"] != qualified or row["routes"] != routes
                or row["grandfathered"] != (iid in baseline)):
            raise ValueError("Inconsistent production qualification for " + iid)
    if (payload.get("candidate_count") != len(rows)
            or payload.get("grandfathered_count") != len(baseline)
            or payload.get("qualified_count") != sum(r["qualified"] for r in rows.values())):
        raise ValueError("Inconsistent production catalog counts")
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify committed artifact without writing")
    args = parser.parse_args()
    catalog = build_catalog(read_json(ROOT / "production/evidence-inputs.json"),
                            load_grandfathered())
    validate_frozen(catalog)
    path = ROOT / "production/movie-catalog.json"
    expected = encode(catalog)
    if args.check:
        if path.read_bytes() != expected:
            raise SystemExit("Production catalog is not reproducible")
        load_catalog()
    else:
        temporary = path.with_suffix(".json.tmp")
        temporary.write_bytes(expected)
        temporary.replace(path)
    print(json.dumps({key: catalog[key] for key in
                      ("candidate_count", "grandfathered_count", "new_count", "qualified_count")}))


if __name__ == "__main__":
    main()
