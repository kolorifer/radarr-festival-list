"""Research-only scoring simulation. Does not modify production backcatalog scoring."""
import json
import math
import re
import unicodedata
from pathlib import Path

BACKCATALOG = Path("backcatalog-details.json")
AUDIENCE = Path("audience-ratings.json")
OUTPUT = Path("scoring-simulation.json")


def norm(text):
    text = unicodedata.normalize("NFKD", text.casefold())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "", text)


def quantile(values, q):
    values = sorted(v for v in values if isinstance(v, (int, float)))
    if not values:
        return None
    pos = (len(values) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    if lo == hi:
        return values[lo]
    return values[lo] * (hi - pos) + values[hi] * (pos - lo)


def revised_tspdt(rank):
    if rank <= 25: return 5.0
    if rank <= 50: return 4.0
    if rank <= 100: return 3.0
    if rank <= 150: return 2.5
    if rank <= 250: return 2.0
    if rank <= 500: return 1.0
    return 0.5


def non_tspdt_existing(candidate):
    old_base = next((float(s.split("#", 1)[1]) for s in []), 0.0)  # documentation marker
    rank = candidate["tspdt_rank"]
    if rank <= 25: production_base = 5.0
    elif rank <= 50: production_base = 4.0
    elif rank <= 100: production_base = 3.0
    elif rank <= 250: production_base = 2.0
    elif rank <= 500: production_base = 1.0
    else: production_base = 0.5
    return round(float(candidate["score"]) - production_base, 3)


def main():
    back = json.loads(BACKCATALOG.read_text(encoding="utf-8"))
    aud = json.loads(AUDIENCE.read_text(encoding="utf-8"))
    candidates = back["candidates"]
    ratings = aud["ratings"]
    candidate_ids = {c["imdb_id"] for c in candidates}
    rating_ids = set(ratings)

    rows = []
    for c in candidates:
        r = ratings.get(c["imdb_id"], {}).get("reeldb", {})
        imdb = r.get("imdb") or {}
        lb = r.get("letterboxd") or {}
        rows.append({
            "title": c["title"], "year": c["year"], "imdb_id": c["imdb_id"],
            "rank": c["tspdt_rank"], "production_score": c["score"],
            "existing_bonus": non_tspdt_existing(c),
            "imdb_rating": imdb.get("rating"), "imdb_votes": imdb.get("votes"),
            "letterboxd_rating": lb.get("rating"), "letterboxd_votes": lb.get("votes"),
        })

    imdb_ratings = [r["imdb_rating"] for r in rows if r["imdb_rating"] is not None]
    imdb_votes = [r["imdb_votes"] for r in rows if r["imdb_votes"] is not None]
    lb_ratings = [r["letterboxd_rating"] for r in rows if r["letterboxd_rating"] is not None]
    lb_votes = [r["letterboxd_votes"] for r in rows if r["letterboxd_votes"] is not None]

    # Data-derived thresholds: upper quartile = strong, upper decile = exceptional.
    # Vote floors are deliberately modest and only prevent tiny-sample promotion.
    thresholds = {
        "imdb_strong": round(quantile(imdb_ratings, .75), 3),
        "imdb_exceptional": round(quantile(imdb_ratings, .90), 3),
        "letterboxd_strong": round(quantile(lb_ratings, .75), 3),
        "letterboxd_exceptional": round(quantile(lb_ratings, .90), 3),
        "imdb_vote_floor": round(quantile(imdb_votes, .10)),
        "letterboxd_vote_floor": round(quantile(lb_votes, .10)),
    }

    simulated = []
    for r in rows:
        audience_bonus = 0.0
        audience_signals = []
        ir, iv = r["imdb_rating"], r["imdb_votes"]
        lr, lv = r["letterboxd_rating"], r["letterboxd_votes"]
        if lr is not None and lv is not None and lv >= thresholds["letterboxd_vote_floor"]:
            if lr >= thresholds["letterboxd_exceptional"]:
                audience_bonus += .50; audience_signals.append("Letterboxd exceptional")
            elif lr >= thresholds["letterboxd_strong"]:
                audience_bonus += .25; audience_signals.append("Letterboxd strong")
        if ir is not None and iv is not None and iv >= thresholds["imdb_vote_floor"]:
            if ir >= thresholds["imdb_exceptional"]:
                audience_bonus += .25; audience_signals.append("IMDb exceptional")
            elif ir >= thresholds["imdb_strong"]:
                audience_bonus += .125; audience_signals.append("IMDb strong")
        audience_bonus = min(.5, audience_bonus)
        score = round(revised_tspdt(r["rank"]) + r["existing_bonus"] + audience_bonus, 3)
        simulated.append({**r, "audience_bonus": audience_bonus,
                          "audience_signals": audience_signals, "simulated_score": score})

    old_qualifiers = {r["imdb_id"] for r in rows if r["production_score"] >= 3.0}
    new_qualifiers = {r["imdb_id"] for r in simulated if r["simulated_score"] >= 3.0}
    promoted = sorted((r for r in simulated if r["imdb_id"] in new_qualifiers - old_qualifiers),
                      key=lambda x: (-x["simulated_score"], x["rank"]))
    demoted = sorted((r for r in simulated if r["imdb_id"] in old_qualifiers - new_qualifiers),
                     key=lambda x: (x["simulated_score"], x["rank"]))
    near_below = sorted((r for r in simulated if 2.5 <= r["simulated_score"] < 3.0),
                        key=lambda x: (-x["simulated_score"], x["rank"]))

    output = {
        "mode": "simulation-only",
        "production_unchanged": True,
        "coverage": {
            "tspdt_candidates": len(candidates), "audience_records": len(ratings),
            "candidate_ids_with_audience": len(candidate_ids & rating_ids),
            "candidate_ids_missing_audience": len(candidate_ids - rating_ids),
            "audience_ids_not_in_current_candidates": len(rating_ids - candidate_ids),
            "missing_audience": [
                {"title": c["title"], "year": c["year"], "imdb_id": c["imdb_id"], "rank": c["tspdt_rank"]}
                for c in candidates if c["imdb_id"] not in rating_ids
            ],
        },
        "distributions": {
            "imdb_rating": {"n": len(imdb_ratings), "p10": quantile(imdb_ratings,.10), "p25": quantile(imdb_ratings,.25), "median": quantile(imdb_ratings,.50), "p75": quantile(imdb_ratings,.75), "p90": quantile(imdb_ratings,.90)},
            "imdb_votes": {"n": len(imdb_votes), "p10": quantile(imdb_votes,.10), "median": quantile(imdb_votes,.50), "p90": quantile(imdb_votes,.90)},
            "letterboxd_rating": {"n": len(lb_ratings), "p10": quantile(lb_ratings,.10), "p25": quantile(lb_ratings,.25), "median": quantile(lb_ratings,.50), "p75": quantile(lb_ratings,.75), "p90": quantile(lb_ratings,.90)},
            "letterboxd_votes": {"n": len(lb_votes), "p10": quantile(lb_votes,.10), "median": quantile(lb_votes,.50), "p90": quantile(lb_votes,.90)},
        },
        "thresholds_used": thresholds,
        "model": {
            "tspdt": "5/4/3/2.5/2/1/0.5 with #101-150=2.5",
            "existing_non_tspdt_signals": "preserved exactly from production for this first simulation",
            "audience": "Letterboxd +0.25/+0.50; IMDb +0.125/+0.25; combined cap +0.50; thresholds from p75/p90; vote floors p10",
            "cutoff": 3.0,
        },
        "counts": {"production_qualifiers": len(old_qualifiers), "simulated_qualifiers": len(new_qualifiers),
                   "promoted": len(promoted), "demoted": len(demoted), "near_below": len(near_below)},
        "promoted": promoted,
        "demoted": demoted,
        "near_below": near_below,
    }
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"coverage": output["coverage"], "thresholds": thresholds, "counts": output["counts"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
