"""Research-only scoring simulation. Does not modify production backcatalog scoring."""
import json
import math
from pathlib import Path

BACKCATALOG = Path("backcatalog-details.json")
AUDIENCE = Path("audience-ratings.json")
OUTPUT = Path("scoring-simulation.json")

# Phase-2 verified film-level recognition. Kept deliberately narrow: only signals
# independently checked against the Academy / Festival de Cannes before inclusion.
# This is simulation data, not production policy.
RECOGNITION = {
    "tt2543164": (0.50, "Academy Best Picture nominee"),              # Arrival
    "tt2024544": (1.50, "Academy Best Picture winner"),               # 12 Years a Slave
    "tt1454468": (0.50, "Academy Best Picture nominee"),              # Gravity
    "tt0993846": (0.50, "Academy Best Picture nominee"),              # The Wolf of Wall Street
    "tt2042568": (0.50, "Cannes Grand Prix"),                         # Inside Llewyn Davis
    "tt2758880": (0.50, "Cannes Jury Prize"),                         # Goodbye to Language
    "tt3808342": (1.00, "Academy Foreign Language Film winner + Cannes Grand Prix"), # Son of Saul
    "tt3508840": (0.50, "Cannes Best Director"),                      # The Assassin
}


def quantile(values, q):
    values = sorted(v for v in values if isinstance(v, (int, float)))
    if not values: return None
    pos = (len(values) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    if lo == hi: return values[lo]
    return values[lo] * (hi - pos) + values[hi] * (pos - lo)


def revised_tspdt(rank):
    if rank <= 25: return 5.0
    if rank <= 50: return 4.0
    if rank <= 100: return 3.0
    if rank <= 150: return 2.5
    if rank <= 250: return 2.0
    if rank <= 500: return 1.0
    return 0.5


def production_base(rank):
    if rank <= 25: return 5.0
    if rank <= 50: return 4.0
    if rank <= 100: return 3.0
    if rank <= 250: return 2.0
    if rank <= 500: return 1.0
    return 0.5


def non_tspdt_existing(candidate):
    return round(float(candidate["score"]) - production_base(candidate["tspdt_rank"]), 3)


def audience_bonus(row, thresholds):
    ir, iv = row["imdb_rating"], row["imdb_votes"]
    lr, lv = row["letterboxd_rating"], row["letterboxd_votes"]
    bonus, signals = 0.0, []
    if lr is not None and lv is not None:
        raw = .50 if lr >= thresholds["letterboxd_exceptional"] else (.25 if lr >= thresholds["letterboxd_strong"] else 0)
        if raw:
            confidence = 1.0 if lv >= thresholds["letterboxd_votes_median"] else (.5 if lv >= thresholds["letterboxd_vote_floor"] else 0)
            bonus += raw * confidence
            if raw * confidence: signals.append(f"Letterboxd {'exceptional' if raw == .50 else 'strong'} x{confidence:g} confidence")
    if ir is not None and iv is not None:
        raw = .25 if ir >= thresholds["imdb_exceptional"] else (.125 if ir >= thresholds["imdb_strong"] else 0)
        if raw:
            confidence = 1.0 if iv >= thresholds["imdb_votes_median"] else (.5 if iv >= thresholds["imdb_vote_floor"] else 0)
            bonus += raw * confidence
            if raw * confidence: signals.append(f"IMDb {'exceptional' if raw == .25 else 'strong'} x{confidence:g} confidence")
    return min(.5, bonus), signals


def main():
    back = json.loads(BACKCATALOG.read_text(encoding="utf-8")); aud = json.loads(AUDIENCE.read_text(encoding="utf-8"))
    candidates, ratings = back["candidates"], aud["ratings"]
    candidate_ids, rating_ids = {c["imdb_id"] for c in candidates}, set(ratings)
    rows = []
    for c in candidates:
        r = ratings.get(c["imdb_id"], {}).get("reeldb", {}); imdb = r.get("imdb") or {}; lb = r.get("letterboxd") or {}
        rows.append({"title": c["title"], "year": c["year"], "imdb_id": c["imdb_id"], "rank": c["tspdt_rank"],
                     "production_score": c["score"], "existing_bonus": non_tspdt_existing(c),
                     "imdb_rating": imdb.get("rating"), "imdb_votes": imdb.get("votes"),
                     "letterboxd_rating": lb.get("rating"), "letterboxd_votes": lb.get("votes")})
    imdb_ratings=[r["imdb_rating"] for r in rows if r["imdb_rating"] is not None]; imdb_votes=[r["imdb_votes"] for r in rows if r["imdb_votes"] is not None]
    lb_ratings=[r["letterboxd_rating"] for r in rows if r["letterboxd_rating"] is not None]; lb_votes=[r["letterboxd_votes"] for r in rows if r["letterboxd_votes"] is not None]
    thresholds={"imdb_strong":round(quantile(imdb_ratings,.75),3),"imdb_exceptional":round(quantile(imdb_ratings,.90),3),
                "letterboxd_strong":round(quantile(lb_ratings,.75),3),"letterboxd_exceptional":round(quantile(lb_ratings,.90),3),
                "imdb_vote_floor":round(quantile(imdb_votes,.10)),"letterboxd_vote_floor":round(quantile(lb_votes,.10)),
                "imdb_votes_median":round(quantile(imdb_votes,.50)),"letterboxd_votes_median":round(quantile(lb_votes,.50))}
    simulated=[]
    for r in rows:
        ab,asig=audience_bonus(r,thresholds); rb,rsig=RECOGNITION.get(r["imdb_id"],(0.0,None))
        score=round(revised_tspdt(r["rank"])+r["existing_bonus"]+ab+rb,3)
        simulated.append({**r,"audience_bonus":ab,"audience_signals":asig,"recognition_bonus":rb,"recognition_signal":rsig,"simulated_score":score})
    oldq={r["imdb_id"] for r in rows if r["production_score"]>=3}; newq={r["imdb_id"] for r in simulated if r["simulated_score"]>=3}
    promoted=sorted((r for r in simulated if r["imdb_id"] in newq-oldq),key=lambda x:(-x["simulated_score"],x["rank"]))
    demoted=sorted((r for r in simulated if r["imdb_id"] in oldq-newq),key=lambda x:(x["simulated_score"],x["rank"]))
    near=sorted((r for r in simulated if 2.5<=r["simulated_score"]<3),key=lambda x:(-x["simulated_score"],x["rank"]))
    names={"Arrival","12 Years a Slave","Gravity","The Wolf of Wall Street","La Commune (Paris, 1871)","Inside Llewyn Davis","Son of Saul","The Assassin"}
    output={"mode":"simulation-2-verified-recognition","production_unchanged":True,
            "coverage":{"tspdt_candidates":len(candidates),"audience_records":len(ratings),"candidate_ids_with_audience":len(candidate_ids&rating_ids),"candidate_ids_missing_audience":len(candidate_ids-rating_ids)},
            "thresholds_used":thresholds,
            "model":{"tspdt":"5/4/3/2.5/2/1/0.5 with #101-150=2.5","audience":"p75/p90 strength; p10 minimum; half confidence below median vote count; combined cap +0.5","recognition":"verified film-level Academy/Cannes signals only in this phase; Best Picture winner +1.5; major film-level win/combined recognition up to +1; nominee/major secondary Cannes prize +0.5","cutoff":3.0},
            "counts":{"production_qualifiers":len(oldq),"simulated_qualifiers":len(newq),"promoted":len(promoted),"demoted":len(demoted),"near_below":len(near)},
            "calibration":sorted([r for r in simulated if r["title"] in names],key=lambda x:x["rank"]),"promoted":promoted,"demoted":demoted,"near_below":near}
    OUTPUT.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"coverage":output["coverage"],"thresholds":thresholds,"counts":output["counts"],"calibration":output["calibration"]},ensure_ascii=False,indent=2))

if __name__ == "__main__": main()
