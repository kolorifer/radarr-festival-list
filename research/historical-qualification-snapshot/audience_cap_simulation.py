"""Reproducible IMDb + Letterboxd audience-weight calibration; research only."""
import argparse
import copy
import csv
import hashlib
import json
import math
import statistics
from pathlib import Path

import audience_calibration_enrichment as ace
import broad_critic_score
import canon_overlap_score
import evidence_score as es
from score_band_analysis import BANDS

OUT = ace.OUT
CAPS = (150, 200)
FAMILY_WEIGHTS = {key: (200 if key == "european_recognition" else 100)
                  for key in es.NON_AUDIENCE_FAMILIES}
BAND_FLOORS = tuple(sorted({0, *BANDS}))
AUDIENCE_SOURCES = ("imdb", "letterboxd")


def digest(value):
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False,
                         separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def rank_rows(rows, score_key="overall_score", rank_key="overall_rank"):
    rows.sort(key=lambda r: (-r[score_key], -r["source_hits"],
                            r.get("title") or "", r["imdb_id"]))
    previous = None
    competition = 0
    for rank, row in enumerate(rows, 1):
        row[rank_key] = rank
        if row[score_key] != previous:
            competition = rank
        row["score_rank"] = competition
        previous = row[score_key]
    return rows


def prepare_shared(inputs, fallback):
    """Rebuild base components once; reuse existing critic/canon modifiers."""
    working = copy.deepcopy(inputs)
    audience = working[str(es.AUDIENCE)]
    ratings = audience.setdefault("ratings", {})
    seeds = {r["imdb_id"]: r for r in inputs[str(es.DISCOVERY)].get("films", [])
             if r.get("imdb_id")}
    provenance = {}
    for film in ace.universe(inputs):
        iid = film["imdb_id"]
        rr = (ratings.setdefault(iid, {}).get("reeldb") or {}).copy()
        provenance[iid] = {}
        for source in AUDIENCE_SOURCES:
            item = rr.get(source)
            origin = "ReelDB cached"
            if not ace.valid_provider(item, source) and source == "imdb":
                item = (fallback.get("ratings") or {}).get(iid)
                origin = "IMDb official title.ratings"
                if not ace.valid_provider(item, source):
                    seed = seeds.get(iid) or {}
                    item = {"rating": seed.get("imdb_rating"),
                            "votes": seed.get("imdb_votes")}
                    origin = "Frozen IMDb audience-discovery snapshot"
            if ace.valid_provider(item, source):
                votes = item.get("votes") if item.get("votes") is not None else item.get("ratings")
                rr[source] = {"rating": item["rating"], "votes": votes}
                provenance[iid][source] = {"available": True, "origin": origin,
                                          "rating": item["rating"], "votes": votes}
            else:
                rr[source] = {}
                reason = ("ReelDB HTTP 404" if iid in (audience.get("unavailable") or {})
                          else "Cached provider absent or incomplete" if iid in inputs[str(es.AUDIENCE)].get("ratings", {})
                          else "No ReelDB cache")
                provenance[iid][source] = {"available": False, "origin": None,
                                          "reason": reason}
        for source in ("trakt", "tmdb", "metacritic", "tomatoes"):
            if not ace.valid_provider(rr.get(source), source):
                rr[source] = {}
        ratings[iid]["reeldb"] = rr

    rows = es.build_rows(*(working[str(p)] for p in ace.INPUT_PATHS))
    payload = {"films": rows}
    broad_critic_score.apply(payload, audience)
    canon_overlap_score.apply(payload)
    shared = []
    for row in payload["films"]:
        iid = row["imdb_id"]
        rr = ratings[iid]["reeldb"]
        raw = {"imdb": es.imdb_points(rr), "letterboxd": es.letterboxd_points(rr)}
        normalized = {key: float(row["source_points"].get(key) or 0)
                      for key in es.NON_AUDIENCE_FAMILIES}
        nonaud = {key: round(value * FAMILY_WEIGHTS[key] / 100, 2)
                  for key, value in normalized.items()}
        year = row.get("year")
        year_int = int(year) if str(year).isdigit() else None
        eligible = {}
        ranked = inputs[str(es.SOURCE_SNAPSHOT)].get("ranked_sources") or {}
        for key in es.NON_AUDIENCE_FAMILIES:
            cutoff = (ranked.get(key) or {}).get("eligible_through_year")
            eligible[key] = not (year_int and cutoff and year_int > int(cutoff))
        max_nonaud = sum(FAMILY_WEIGHTS[key] for key, valid in eligible.items() if valid)
        max_nonaud += (row.get("canon_correlation") or {}).get("eligible_max_adjustment", 0)
        total_nonaud = round(sum(nonaud.values()), 2)
        shared.append({
            "imdb_id": iid, "title": row["title"], "year": year,
            "qualified": row["qualified"], "routes": copy.deepcopy(row["routes"]),
            "candidate_sources": row["candidate_sources"],
            "audience_discovery_seed": row["audience_discovery_seed"],
            "audience_raw_points": raw, "audience_raw_sum": round(sum(raw.values()), 2),
            "audience_coverage": provenance[iid],
            "audience_complete": all(x["available"] for x in provenance[iid].values()),
            "normalized_non_audience_points": normalized,
            "non_audience_points": nonaud, "non_audience_score": total_nonaud,
            "non_audience_eligible_max": max_nonaud, "family_eligibility": eligible,
            "source_hits": sum(v > 0 for v in nonaud.values()) + sum(v > 0 for v in raw.values()),
            "non_audience_family_hits": sum(v > 0 for v in nonaud.values()),
            "source_evidence": {key: row["source_evidence"].get(key, [])
                                for key in es.NON_AUDIENCE_FAMILIES},
            "canon_correlation": row.get("canon_correlation"),
            "broad_critic_consensus": row.get("broad_critic_consensus"),
        })
    return sorted(shared, key=lambda r: r["imdb_id"])


def score_variant(shared, cap):
    if cap not in CAPS:
        raise ValueError("Only the agreed audience caps are supported")
    result = []
    for base in shared:
        row = copy.deepcopy(base)
        audience = round(row["audience_raw_sum"] * cap / 200, 2)
        row.update({
            "variant": "audience_cap_" + str(cap),
            "audience_cap": cap, "audience_score": audience,
            "audience_score_unrounded": round(row["audience_raw_sum"] * cap / 200, 4),
            "overall_score": round(row["non_audience_score"] + audience, 2),
            "eligible_max_score": row["non_audience_eligible_max"] + cap,
            "source_points": {**row["non_audience_points"], "audience": audience},
        })
        row["eligible_score_pct"] = round(
            100 * row["overall_score"] / row["eligible_max_score"], 2)
        row["audience_share_pct"] = (round(100 * audience / row["overall_score"], 2)
                                     if row["overall_score"] else 0)
        result.append(row)
    return rank_rows(result)


def band(score):
    lower = max(floor for floor in BAND_FLOORS if score >= floor)
    higher = next((floor for floor in BAND_FLOORS if floor > lower), None)
    return str(lower) + ("+" if higher is None else "-<" + str(higher))


def percentile(values, percent):
    values = sorted(values)
    if not values:
        return None
    position = (len(values) - 1) * percent / 100
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    return round(values[lower] + (values[upper] - values[lower]) * (position - lower), 2)


def distribution(rows):
    values = [r["overall_score"] for r in rows]
    return {
        "count": len(values), "min": min(values) if values else None,
        "max": max(values) if values else None,
        "mean": round(statistics.mean(values), 2) if values else None,
        "median": round(statistics.median(values), 2) if values else None,
        "stddev_population": round(statistics.pstdev(values), 2) if values else None,
        "percentiles": {str(p): percentile(values, p) for p in (10, 25, 50, 75, 90, 95, 99)},
        "bands": {band(floor): sum(band(r["overall_score"]) == band(floor) for r in rows)
                  for floor in BAND_FLOORS},
        "at_or_above": {str(floor): sum(v >= floor for v in values)
                       for floor in BANDS},
    }


def compact(row):
    return {key: row[key] for key in (
        "imdb_id", "title", "year", "overall_rank", "score_rank", "overall_score",
        "audience_score", "audience_raw_points", "non_audience_score",
        "non_audience_points", "audience_share_pct", "audience_complete",
        "qualified", "routes")}


def compare(variants):
    a, b = variants[150], variants[200]
    by_a = {r["imdb_id"]: r for r in a}
    by_b = {r["imdb_id"]: r for r in b}
    if set(by_a) != set(by_b) or len(by_a) != len(a) or len(by_b) != len(b):
        raise ValueError("Universe differs or contains duplicate IDs")
    movement = []
    for iid in sorted(by_a):
        x, y = by_a[iid], by_b[iid]
        for key in ("non_audience_points", "qualified", "routes", "audience_raw_points"):
            if x[key] != y[key]:
                raise ValueError("Non-audience or qualification invariance failed")
        delta = round(y["overall_score"] - x["overall_score"], 2)
        expected = (x["audience_raw_sum"] * 0.25)
        if abs(delta - expected) > 0.010001:
            raise ValueError("Unexpected score delta")
        movement.append({
            "imdb_id": iid, "title": x["title"], "year": x["year"],
            "rank_150": x["overall_rank"], "rank_200": y["overall_rank"],
            "score_rank_150": x["score_rank"], "score_rank_200": y["score_rank"],
            "rank_change": x["overall_rank"] - y["overall_rank"],
            "score_150": x["overall_score"], "score_200": y["overall_score"],
            "score_change": delta, "audience_150": x["audience_score"],
            "audience_200": y["audience_score"],
            "audience_raw_points": x["audience_raw_points"],
            "non_audience_score": x["non_audience_score"],
            "non_audience_points": x["non_audience_points"],
            "audience_share_200_pct": y["audience_share_pct"],
            "audience_complete": x["audience_complete"],
            "qualified": x["qualified"], "routes": x["routes"],
            "band_150": band(x["overall_score"]), "band_200": band(y["overall_score"]),
            "crossed_boundaries": [floor for floor in BANDS
                                   if x["overall_score"] < floor <= y["overall_score"]],
        })
    up = sorted([m for m in movement if m["rank_change"] > 0],
                key=lambda m: (-m["rank_change"], -m["score_change"], m["imdb_id"]))
    down = sorted([m for m in movement if m["rank_change"] < 0],
                  key=lambda m: (m["rank_change"], m["imdb_id"]))
    gains = sorted(movement, key=lambda m: (-m["score_change"], m["rank_200"]))
    crossings = [m for m in movement if m["crossed_boundaries"]]
    baseline = [copy.deepcopy(r) for r in a]
    for r in baseline:
        r["overall_score"] = r["non_audience_score"]
    rank_rows(baseline)
    baseline_ranks = {r["imdb_id"]: r["overall_rank"] for r in baseline}
    lifts = []
    for m in movement:
        lift = baseline_ranks[m["imdb_id"]] - m["rank_200"]
        if lift > 0 and m["audience_complete"] and m["non_audience_score"] > 0:
            lifts.append({**m, "rank_without_audience": baseline_ranks[m["imdb_id"]],
                          "lift_from_no_audience": lift})
    lifts.sort(key=lambda m: (-m["lift_from_no_audience"], m["rank_200"]))
    dominance = [m for m in up if m["audience_complete"]
                 and m["non_audience_score"] > 0 and m["audience_share_200_pct"] >= 50]
    pairs = []
    critical = ("tspdt_21c", "sight_sound", "bbc_21c", "nyt_21c", "critics_groups_consensus")
    for x in b[:300]:
        if not x["audience_complete"]:
            continue
        for y in a[:300]:
            if (x["imdb_id"] == y["imdb_id"] or not y["audience_complete"]
                    or x["non_audience_score"] >= y["non_audience_score"]
                    or not any(y["non_audience_points"][k] > 0 for k in critical)):
                continue
            if (by_a[x["imdb_id"]]["overall_rank"] > y["overall_rank"]
                    and x["overall_rank"] < by_b[y["imdb_id"]]["overall_rank"]):
                pairs.append({
                    "audience_favoured": compact(x),
                    "higher_non_audience_evidence": compact(by_b[y["imdb_id"]]),
                    "rank_150_favoured": by_a[x["imdb_id"]]["overall_rank"],
                    "rank_150_higher_evidence": y["overall_rank"],
                    "non_audience_gap": round(y["non_audience_score"] - x["non_audience_score"], 2),
                })
    pairs.sort(key=lambda p: (-p["non_audience_gap"],
                             p["audience_favoured"]["overall_rank"],
                             p["audience_favoured"]["imdb_id"],
                             p["higher_non_audience_evidence"]["imdb_id"]))
    cutoffs = {}
    for n in (50, 100, 200, 300, 500):
        n = min(n, len(a))
        ids_a = {r["imdb_id"] for r in a[:n]}
        ids_b = {r["imdb_id"] for r in b[:n]}
        cutoffs[str(n)] = {
            "overlap": len(ids_a & ids_b),
            "entered_at_200": [m for m in movement if m["imdb_id"] in ids_b - ids_a],
            "exited_at_200": [m for m in movement if m["imdb_id"] in ids_a - ids_b],
        }
    return {
        "mode": "research-audience-cap-comparison-v1",
        "production_unchanged": True, "qualification_unchanged": True,
        "film_count": len(a), "movements": movement,
        "top_150": [compact(r) for r in a[:30]],
        "top_200": [compact(r) for r in b[:30]],
        "largest_upward_movers": up[:30], "largest_downward_movers": down[:30],
        "largest_score_changes": gains[:30], "band_crossings": crossings,
        "boundary_crossing_counts": {str(floor): sum(floor in m["crossed_boundaries"]
                                    for m in movement) for floor in BANDS},
        "distributions": {"audience_cap_150": distribution(a),
                          "audience_cap_200": distribution(b)},
        "complete_pair_distributions": {
            "audience_cap_150": distribution([r for r in a if r["audience_complete"]]),
            "audience_cap_200": distribution([r for r in b if r["audience_complete"]])},
        "cutoffs": cutoffs, "audience_lift_examples": lifts[:30],
        "potential_audience_dominance": dominance[:30],
        "critical_evidence_inversions_top300": pairs[:30],
        "summary": {
            "score_changed": sum(m["score_change"] != 0 for m in movement),
            "rank_changed": sum(m["rank_change"] != 0 for m in movement),
            "rank_up": len(up), "rank_down": len(down),
            "any_band_crossing": len(crossings),
            "complete_audience_pairs": sum(m["audience_complete"] for m in movement),
            "incomplete_audience_pairs": sum(not m["audience_complete"] for m in movement),
        },
        "diagnostic_definitions": {
            "bands": "Existing score_band_analysis boundaries, plus a below-100 bucket; not qualification tiers",
            "lift": "Ordinal rank at audience=200 compared with the same non-audience-only baseline",
            "dominance": "Complete audience data, positive non-audience score, audience share >=50%, and rank rises from cap150 to cap200; diagnostic only",
            "inversions": "Complete-data films within either variant's top300; lower non-audience evidence overtakes higher non-audience evidence solely as audience weight increases",
            "missing": "Missing components score zero without renormalizing; this is a lower bound, not evidence of weak audience reception",
            "rank_ties": "Ordinal score/source-hits/title/IMDb-ID ordering; score_rank separately reports competition ties",
            "rounding": "Scores round to 2 decimals. Delta matches 0.25 × raw sum within 0.01.",
        },
    }


def write_csv(path, rows, columns):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(row[key], ensure_ascii=False)
                             if isinstance(row.get(key), (dict, list))
                             else row.get(key) for key in columns})


def cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def table(headers, rows):
    return "\n".join(["| " + " | ".join(headers) + " |",
                     "| " + " | ".join("---" for _ in headers) + " |"] +
                    ["| " + " | ".join(cell(x) for x in row) + " |" for row in rows])


def report_markdown(result, manifest, coverage):
    lines = ["# Audience=150 vs Audience=200 calibration", "",
             "Research only. No cap is selected and no qualification or production behavior changes.", "",
             "## Reproduction and scoring", "",
             "Frozen universe: " + str(result["film_count"]) + " IMDb IDs. Universe SHA-256: " + manifest["universe_sha256"] + ".",
             "Shared evidence SHA-256: " + manifest["shared_evidence_sha256"] + ".",
             "Baseline: " + manifest["research_baseline"] + ". Exact inputs and implementation hashes are in [manifest.json](manifest.json).", "",
             "Audience=150 uses 0.75 × (IMDb + Letterboxd); Audience=200 uses 1.0 × the same raw sum.",
             "IMDb calibration remains 6.5–8.5 and Letterboxd 3.0–4.3, with the existing logarithmic vote-confidence discount (1,000–100,000 votes).",
             "European Recognition uses 2 × its normalized 100-point family score. Other family weights are fixed.",
             "The existing 50% Sight & Sound corroboration alongside TSPDT remains in both runs. Critics Groups Consensus retains the existing NSFC/NYFCC/LAFCA wins, implemented Critics Choice Best Picture evidence, and capped 40-point broad-critic component.",
             "Nominal family ceilings are 1,050/1,100 before the inherited canon overlap reduction; fully eligible ceilings after that reduction are 1,000/1,050.",
             "Trakt/TMDb do not contribute. Missing audience components score zero without renormalization.", "",
             "## Data completeness", "",
             table(["Measure", "Count"], [[key, value] for key, value in coverage["counts"].items()]), "",
             "Per-film missing-data reasons are in [coverage.json](coverage.json). Valid low ratings and small vote counts are distinct from unavailable data.",
             "Cached ReelDB values have no historical collection timestamps. Official IMDb fallback provenance is retained separately.",
             "The same missingness applies to both variants; incomplete rows can underestimate audience contribution and movements.", "",
             "## Comparison summary", "",
             table(["Measure", "Count"], [[key, value] for key, value in result["summary"].items()]), "",
             "## Top-ranked films", ""]
    for key, label in (("top_150", "Audience=150"), ("top_200", "Audience=200")):
        lines += ["### " + label, "", table(
            ["Rank", "Film", "Year", "Score", "Audience", "Non-audience", "Complete pair"],
            [[r["overall_rank"], r["title"], r["year"], r["overall_score"],
              r["audience_score"], r["non_audience_score"], r["audience_complete"]]
             for r in result[key][:25]]), ""]
    for key, label in (("largest_upward_movers", "Biggest ranking gains"),
                       ("largest_downward_movers", "Biggest ranking losses"),
                       ("largest_score_changes", "Biggest score increases")):
        lines += ["## " + label, "", table(
            ["Film", "Year", "Rank 150", "Rank 200", "Rank gain", "Score 150", "Score 200", "Delta", "Complete"],
            [[r["title"], r["year"], r["rank_150"], r["rank_200"], r["rank_change"],
              r["score_150"], r["score_200"], r["score_change"], r["audience_complete"]]
             for r in result[key][:20]]), ""]
    lines += ["## Diagnostic band crossings", "",
              "Boundaries reuse the existing analysis bands; crossing one does not qualify a film.",
              table(["Boundary", "Films crossing upward"],
                    result["boundary_crossing_counts"].items()), "",
              table(["Film", "Year", "Band 150", "Band 200", "Score 150", "Score 200", "Complete"],
                    [[r["title"], r["year"], r["band_150"], r["band_200"],
                      r["score_150"], r["score_200"], r["audience_complete"]]
                     for r in sorted(result["band_crossings"], key=lambda x: x["rank_200"])[:25]]), "",
              "## Score distributions", ""]
    distributions = result["distributions"]
    x, y = distributions["audience_cap_150"], distributions["audience_cap_200"]
    lines += [table(["Statistic", "Audience=150", "Audience=200"],
                    [[key, x[key], y[key]] for key in
                     ("count", "min", "max", "mean", "median", "stddev_population")] +
                    [["p" + p, x["percentiles"][p], y["percentiles"][p]]
                     for p in x["percentiles"]]), "",
              table(["Band", "Audience=150", "Audience=200"],
                    [[key, count, y["bands"][key]] for key, count in x["bands"].items()]), "",
              "Complete-pair-only distributions are also provided in comparison.json for missing-data sensitivity.", "",
              "## Audience strength materially improves position", "",
              table(["Film", "Year", "Rank without audience", "Rank 150", "Rank 200", "Lift", "Audience 200", "Non-audience"],
                    [[r["title"], r["year"], r["rank_without_audience"], r["rank_150"],
                      r["rank_200"], r["lift_from_no_audience"], r["audience_200"],
                      r["non_audience_score"]] for r in result["audience_lift_examples"][:15]]), "",
              "These complete-data examples quantify audience lift; they are not endorsements or preferred-cap choices.", "",
              "## Potential audience dominance over other evidence", "",
              "The first diagnostic shows rising complete-data films whose audience share is at least 50%.",
              table(["Film", "Rank 150", "Rank 200", "Audience share %", "Audience 200", "Non-audience"],
                    [[r["title"], r["rank_150"], r["rank_200"], r["audience_share_200_pct"],
                      r["audience_200"], r["non_audience_score"]]
                     for r in result["potential_audience_dominance"][:15]]), "",
              "The following pairs invert order solely when the audience weight changes; the overtaken film has more non-audience evidence.",
              table(["Audience-favoured film", "Higher-evidence film", "Non-audience gap", "Ranks at 150", "Ranks at 200"],
                    [[p["audience_favoured"]["title"], p["higher_non_audience_evidence"]["title"],
                      p["non_audience_gap"],
                      str(p["rank_150_favoured"]) + " / " + str(p["rank_150_higher_evidence"]),
                      str(p["audience_favoured"]["overall_rank"]) + " / " +
                      str(p["higher_non_audience_evidence"]["overall_rank"])]
                     for p in result["critical_evidence_inversions_top300"][:15]]), "",
              "Point breakdowns for both films are retained in comparison.json. Dominance/inversion is a diagnostic for review, not proof that either film is better or that a cap is wrong.",
              "Critics-group award identity gaps and missing broad-critic cache are reported in coverage.json; absent critical evidence is not proof of absence of acclaim.", "",
              "## Artifacts and limits", "",
              "- [Audience=150 JSON](audience_cap_150.json) / [CSV](audience_cap_150.csv)",
              "- [Audience=200 JSON](audience_cap_200.json) / [CSV](audience_cap_200.csv)",
              "- [Full comparison JSON](comparison.json) / [per-film CSV](comparison.csv)",
              "- [Coverage and unresolved data](coverage.json) / [reproduction manifest](manifest.json)",
              "- [Official IMDb fallback input](inputs/imdb-fallback.json)",
              "- [ReelDB collection status](enrichment-status.json)", "",
              "This is evidence for the user and ChatGPT. No cap is chosen, no production threshold is changed, and no runtime scoring deployment is performed.", ""]
    return "\n".join(lines)


def run(root, output=OUT):
    inputs = ace.load_inputs(root)
    fallback_path = root / OUT / "inputs/imdb-fallback.json"
    fallback = json.loads(fallback_path.read_text()) if fallback_path.exists() else {}
    shared = prepare_shared(inputs, fallback)
    ids = sorted(r["imdb_id"] for r in shared)
    original_ids = sorted(r["imdb_id"] for r in ace.universe(inputs))
    if ids != original_ids or len(set(ids)) != len(ids):
        raise ValueError("Candidate universe changed")
    variants = {cap: score_variant(shared, cap) for cap in CAPS}
    result = compare(variants)
    source_paths = list(ace.INPUT_PATHS) + [Path("evidence_score.py"),
        Path("broad_critic_score.py"), Path("canon_overlap_score.py"),
        Path("audience_cap_simulation.py"), Path("audience_calibration_enrichment.py")]
    if fallback_path.exists():
        source_paths.append(OUT / "inputs/imdb-fallback.json")
    hashes = {str(path): hashlib.sha256((root / path).read_bytes()).hexdigest()
              for path in source_paths}
    manifest = {
        "mode": "frozen-audience-cap-input-manifest-v1",
        "research_baseline": "8363f9393b9bc6961dc829b8ce01c9cd02fec641",
        "implementation_reference": "Containing Git commit plus exact implementation hashes",
        "input_sha256": hashes, "universe_sha256": digest(ids),
        "shared_evidence_sha256": digest(shared), "candidate_ids": ids,
        "family_weights": FAMILY_WEIGHTS,
        "audience_weights": {"audience_cap_150": 0.75, "audience_cap_200": 1.0},
        "canon_correlation": "Existing 50% Sight & Sound corroboration; joint canon max150",
        "critics_policy": "Existing group wins plus capped broad critics, merged as strongest +25% weaker, family max100",
        "qualification_source": str(es.QUALIFIERS),
        "production_unchanged": True, "preferred_cap": None,
    }
    missing = [{key: r[key] for key in ("imdb_id", "title", "year", "audience_coverage")}
               for r in shared if not r["audience_complete"]]
    cache = inputs[str(es.AUDIENCE)].get("ratings") or {}
    def provider_count(src):
        return sum(ace.valid_provider((cache.get(iid, {}).get("reeldb") or {}).get(src), src)
                   for iid in ids)
    coverage = {
        "counts": {
            "candidate_count": len(ids),
            "ReelDB_cached_in_universe": sum(iid in cache for iid in ids),
            "IMDb_available_after_fallback": sum(r["audience_coverage"]["imdb"]["available"] for r in shared),
            "Letterboxd_available": sum(r["audience_coverage"]["letterboxd"]["available"] for r in shared),
            "complete_IMDb_Letterboxd_pairs": len(ids) - len(missing),
            "incomplete_audience_pairs": len(missing),
            "IMDb_official_fallback_used": sum(r["audience_coverage"]["imdb"].get("origin") == "IMDb official title.ratings" for r in shared),
            "IMDb_seed_fallback_used": sum(r["audience_coverage"]["imdb"].get("origin") == "Frozen IMDb audience-discovery snapshot" for r in shared),
            "Metacritic_usable": provider_count("metacritic"),
            "Rotten_Tomatoes_critics_usable": provider_count("tomatoes"),
            "positive_critics_family": sum(r["non_audience_points"]["critics_groups_consensus"] > 0 for r in shared),
            "qualified_unchanged": sum(r["qualified"] for r in shared),
        },
        "missing_audience": missing,
        "cache_has_collection_dates": False,
        "source_snapshot_status": {
            "implemented_critics_groups": inputs[str(es.SOURCE_SNAPSHOT)].get("extra_award_sources"),
            "unresolved_extra_awards": inputs[str(es.SOURCE_SNAPSHOT)].get("unresolved_extra_awards"),
            "unresolved_ranked": inputs[str(es.SOURCE_SNAPSHOT)].get("unresolved_ranked")},
        "remaining_not_inferred": "Letterboxd values and broad-critic data are never guessed from IMDb or other populations.",
    }
    target = root / output
    target.mkdir(parents=True, exist_ok=True)
    for cap, rows in variants.items():
        payload = {"variant": "audience_cap_" + str(cap), "film_count": len(rows),
                   "universe_sha256": manifest["universe_sha256"],
                   "shared_evidence_sha256": manifest["shared_evidence_sha256"],
                   "family_weights": FAMILY_WEIGHTS, "audience_max": cap,
                   "qualification_unchanged": True, "production_unchanged": True,
                   "films": rows}
        ace.write_json(target / ("audience_cap_" + str(cap) + ".json"), payload)
        write_csv(target / ("audience_cap_" + str(cap) + ".csv"), rows, (
            "overall_rank", "score_rank", "imdb_id", "title", "year", "overall_score",
            "audience_score", "audience_raw_points", "non_audience_score",
            "non_audience_points", "audience_complete", "qualified", "routes"))
    ace.write_json(target / "manifest.json", manifest)
    ace.write_json(target / "coverage.json", coverage)
    ace.write_json(target / "comparison.json", result)
    write_csv(target / "comparison.csv", result["movements"], (
        "imdb_id", "title", "year", "rank_150", "rank_200", "rank_change",
        "score_150", "score_200", "score_change", "audience_150", "audience_200",
        "non_audience_score", "audience_raw_points", "audience_complete",
        "band_150", "band_200", "crossed_boundaries", "qualified", "routes"))
    (target / "comparison.md").write_text(report_markdown(result, manifest, coverage),
                                         encoding="utf-8")
    return {"summary": result["summary"], "coverage": coverage["counts"],
            "universe_sha256": manifest["universe_sha256"],
            "top_150": result["top_150"][:5], "top_200": result["top_200"][:5]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    print(json.dumps(run(args.root, args.output), ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
