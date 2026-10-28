"""Offline issue #86 experiment. No production imports, credentials, or network.

Run this file to regenerate results.json, comparison.csv and breakdowns.md.
--check compares their bytes without writing. Inputs are deliberately separate
from the frozen historical model and from live scoring/qualification.
"""
import argparse
from collections import Counter
import csv
import hashlib
import io
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FAMILIES = {
    "european_recognition": 20,
    "independent_cinema": 10,
    "us_institutional": 10,
    "critics_groups_consensus": 10,
}
VENUES = {
    "european_recognition": ["Cannes", "Venice", "Berlin", "BAFTA", "EFA"],
    "independent_cinema": ["Sundance", "Spirit", "Gotham"],
    "us_institutional": ["Academy", "Golden Globes"],
    "critics_groups_consensus": ["NSFC", "NYFCC", "LAFCA", "Critics Choice"],
}
# (family, venue, winner, nominee/competition), on the historical 0..100 scale.
# evidence_sources.py:223-326 and evidence_sources_extra.py EXTRA_SOURCES,
# both pinned at 9c5a0f06e1c39e48653338fd0865ddabdc525a61.
POLICY = {
    "academy_best_picture": ("us_institutional", "Academy", 100, 65),
    "academy_international": ("us_institutional", "Academy", 70, 35),
    "academy_animated": ("us_institutional", "Academy", 60, 30),
    "academy_documentary": ("us_institutional", "Academy", 60, 30),
    "globe_best_picture": ("us_institutional", "Golden Globes", 25, 10),
    "globe_non_english": ("us_institutional", "Golden Globes", 15, 5),
    "globe_animated": ("us_institutional", "Golden Globes", 15, 5),
    "bafta_best_film": ("european_recognition", "BAFTA", 50, 25),
    "bafta_non_english": ("european_recognition", "BAFTA", 35, 15),
    "efa_best_film": ("european_recognition", "EFA", 40, 12),
    "cannes_main": ("european_recognition", "Cannes", 70, 10),
    "cannes_grand_prix": ("european_recognition", "Cannes", 55, 0),
    "cannes_jury": ("european_recognition", "Cannes", 40, 0),
    "cannes_director": ("european_recognition", "Cannes", 30, 0),
    "berlin_main": ("european_recognition", "Berlin", 70, 10),
    "berlin_grand_jury": ("european_recognition", "Berlin", 55, 0),
    "berlin_jury": ("european_recognition", "Berlin", 40, 0),
    "berlin_director": ("european_recognition", "Berlin", 30, 0),
    "venice_main": ("european_recognition", "Venice", 70, 10),
    "venice_grand_jury": ("european_recognition", "Venice", 55, 0),
    "venice_jury": ("european_recognition", "Venice", 40, 0),
    "venice_director": ("european_recognition", "Venice", 30, 0),
    "sundance_grand_jury": ("independent_cinema", "Sundance", 60, 8),
    "sundance_audience": ("independent_cinema", "Sundance", 30, 0),
    "sundance_director": ("independent_cinema", "Sundance", 25, 0),
    "sundance_special_jury": ("independent_cinema", "Sundance", 15, 0),
    "spirit_best_feature": ("independent_cinema", "Spirit", 50, 20),
    "spirit_first_feature": ("independent_cinema", "Spirit", 30, 10),
    "gotham_best_feature": ("independent_cinema", "Gotham", 35, 10),
    "nsfc_best_picture": ("critics_groups_consensus", "NSFC", 35, 0),
    "nyfcc_best_film": ("critics_groups_consensus", "NYFCC", 35, 0),
    "lafca_best_film": ("critics_groups_consensus", "LAFCA", 35, 0),
    "critics_choice_best_picture": ("critics_groups_consensus", "Critics Choice", 25, 8),
}
SCALES = {"imdb": (6.0, 8.5), "letterboxd": (3.0, 4.3)}
# Illustrative pseudo-counts, NOT accepted production parameters. Midpoints
# give 12.5/25 neutral quality points on either source before clamping.
SCENARIOS = {"unsmoothed": 0, "modest": 1000, "stronger": 10000}
EXTENSIONS = {"base": (), "tiff": ("tiff",), "screenplay": ("screenplay",),
              "both": ("tiff", "screenplay")}


def load(name):
    return json.loads((ROOT / "inputs" / name).read_text(encoding="utf-8"))


def quality(rating, source):
    low, high = SCALES[source]
    return 25 * max(0.0, min(1.0, (rating - low) / (high - low)))


def audience_component(observation, source, strength):
    """Missing pairs stay missing, even for the unsmoothed scenario."""
    rating, votes = observation.get("rating"), observation.get("votes")
    if rating is None or votes is None:
        return {"status": observation["status"], "points": None,
                "adjustment_points": None, "adjusted_rating": None}
    if (isinstance(votes, bool) or not isinstance(votes, int) or votes <= 0
            or isinstance(rating, bool) or not isinstance(rating, (int, float))
            or not math.isfinite(rating) or not 0 <= rating <= (10 if source == "imdb" else 5)
            or not math.isfinite(strength) or strength < 0):
        raise ValueError("Invalid rating/count/prior strength")
    low, high = SCALES[source]
    prior = (low + high) / 2
    adjusted = (votes * rating + strength * prior) / (votes + strength)
    points = quality(adjusted, source)
    return {"status": observation["status"], "points": points,
            "prior_mean": prior, "prior_strength": strength,
            "data_weight": votes / (votes + strength),
            "adjusted_rating": adjusted,
            "adjustment_points": points - quality(rating, source)}


def historical_records(film, source_url):
    """Translate only inspected labels; unknown facts fail rather than vanish."""
    out = []
    for family, labels in film.get("family_evidence", {}).items():
        for label in labels:
            s = label.casefold()
            status = "winner" if "(winner)" in s else "nominee"
            if s.startswith("academy:"):
                component = ("academy_best_picture" if "motion picture of the year" in s
                             else "academy_international" if "international" in s
                             else "academy_animated" if "animated" in s
                             else "academy_documentary" if "documentary" in s else None)
            elif s.startswith("golden globes:"):
                component = ("globe_non_english" if "non-english" in s else
                             "globe_animated" if "animated" in s else "globe_best_picture")
            elif s.startswith("bafta:"):
                component = "bafta_non_english" if "not in the english" in s else "bafta_best_film"
            elif s.startswith("cannes:"):
                component = ("cannes_main" if "palme d'or" in s else
                             "cannes_grand_prix" if "grand prize" in s else
                             "cannes_jury" if "jury prize" in s else
                             "cannes_director" if "director" in s else None)
            elif s.startswith("venice:"):
                component = ("venice_main" if "golden lion" in s else
                             "venice_grand_jury" if "grand jury" in s else
                             "venice_director" if "director" in s else None)
            elif s.startswith("spirit:"):
                component = "spirit_best_feature" if "best feature" in s else "spirit_first_feature"
            else:
                prefixes = {"european film awards": "efa_best_film", "gotham": "gotham_best_feature",
                            "nsfc": "nsfc_best_picture", "nyfcc": "nyfcc_best_film",
                            "lafca": "lafca_best_film", "critics choice": "critics_choice_best_picture"}
                component = next((v for k, v in prefixes.items() if s.startswith(k)), None)
            if component not in POLICY or POLICY[component][0] != family:
                raise ValueError("Unmapped historical evidence: " + label)
            if component.endswith("_main") and status == "nominee":
                status = "competition"
            out.append({"component": component, "status": status,
                        "category": label, "source_url": source_url,
                        "verification": "archived_secondary", "event_year": None,
                        "observed_at": None})
    return out


def recognition(records, extensions=()):
    """Strongest per component, then sum and cap. Keep corroborating facts."""
    components = {}
    for record in records:
        component = record["component"]
        if component not in POLICY:
            raise ValueError("Unknown award component: " + component)
        family, venue, win, nom = POLICY[component]
        if record["status"] not in ("winner", "nominee", "competition"):
            raise ValueError("Invalid award status")
        points = win if record["status"] == "winner" else nom
        slot = components.setdefault(component, {"family": family, "venue": venue,
                                                  "normalized_points": 0, "evidence": []})
        slot["normalized_points"] = max(slot["normalized_points"], points)
        slot["evidence"].append(record)
    raw = {family: sum(c["normalized_points"] for c in components.values()
                       if c["family"] == family) for family in FAMILIES}
    if (components.get("sundance_grand_jury", {}).get("normalized_points", 0) >= 60
            and components.get("sundance_audience", {}).get("normalized_points", 0) >= 30):
        raw["independent_cinema"] += 10
    capped = {f: min(100, n) for f, n in raw.items()}
    scaled = {f: n * FAMILIES[f] / 100 for f, n in capped.items()}
    # Conservative sensitivity convention: at most one bonus per kind/film.
    # These are points on the NEW 0..100 scale, applied inside family caps.
    if "tiff" in extensions:
        scaled["independent_cinema"] = min(10, scaled["independent_cinema"] + 4)
    if "screenplay" in extensions:
        scaled["european_recognition"] = min(20, scaled["european_recognition"] + 6)
    return {"components": components, "normalized_uncapped": raw,
            "normalized_capped": capped, "observed_points": scaled}


def rounded(value):
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, dict):
        return {str(k): rounded(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [rounded(v) for v in value]
    return value


def calculate():
    identities = load("identities.json")["films"]
    historical = load("historical-awards.json")
    ratings = load("historical-ratings.json")
    research = load("observations.json")
    for extension in research["extensions"]:
        if (extension["kind"] not in ("tiff", "screenplay")
                or extension.get("unique_film_attribution") is not True
                or extension.get("verification") != "primary_web_observation"
                or not extension.get("source_url", "").startswith("https://")):
            raise ValueError("Candidate extension lacks verified unique film attribution")
    films = []
    for identity in identities:
        iid = identity["imdb_id"]
        old = historical["films"].get(iid, {})
        archive = historical_records(old, historical["provenance"]["url"])
        frozen = recognition(archive)
        expected = {f: old.get("family_scores", {}).get(f, 0) for f in FAMILIES}
        if frozen["normalized_capped"] != expected:
            raise ValueError("Historical family reconstruction drift: " + iid)
        facts = [r for r in research["awards"] if r["imdb_id"] == iid]
        records = archive + facts
        known_extensions = [r["kind"] for r in research["extensions"] if r["imdb_id"] == iid]
        observations = {}
        for source in SCALES:
            pair = ratings["films"].get(iid, {}).get(source)
            observations[source] = ({**pair, "status": "archived", "measurement_date": None,
                                     "available_by": ratings["available_by"],
                                     "source_url": ratings["provenance"]["url"],
                                     "provider_url": "https://api.reeldb.io/v1/title/" + iid + "/ratings",
                                     "freshness": "unknown; archived, not refreshed"} if pair else
                                    {"rating": None, "votes": None, "status": "unavailable",
                                     "source_url": research["letterboxd_access_url"],
                                     "measurement_date": None, "freshness": "no usable pair"})
        for r in research["ratings"]:
            if r["imdb_id"] == iid:
                observations[r["source"]] = r
        coverage = {}
        checks = [c for c in research["coverage_checks"] if iid in c["imdb_ids"]]
        for family, venues in VENUES.items():
            coverage[family] = {}
            for venue in venues:
                scoped_checks = [c for c in checks if c["venue"] == venue]
                has_fact = any(POLICY[r["component"]][1] == venue for r in records)
                coverage[family][venue] = {
                    "status": ("positive_evidence_partial" if has_fact else
                               "not_yet_announced" if scoped_checks and all(
                                   c["status"] == "not_yet_announced" for c in scoped_checks) else
                               "checked_scoped" if scoped_checks else "source_not_checked"),
                    "checks": scoped_checks,
                }
                # Never extrapolate an edition/category check to all awards.
                # Individual checks may say verified_no_award/not_yet_announced.
        variants = {}
        for confidence, strength in SCENARIOS.items():
            audience = {s: audience_component(o, s, strength) for s, o in observations.items()}
            complete_audience = all(a["points"] is not None for a in audience.values())
            observed_audience = sum(a["points"] or 0 for a in audience.values())
            for variant, requested in EXTENSIONS.items():
                enabled = sorted(set(requested) & set(known_extensions))
                awards = recognition(records, enabled)
                points = awards["observed_points"]
                key = confidence + "/" + variant
                variants[key] = {
                    "audience_components": audience,
                    "audience_points": observed_audience if complete_audience else None,
                    "observed_audience_subtotal": observed_audience,
                    "recognition_observed_points": points,
                    "recognition_family_scores": {f: points[f] if points[f] == FAMILIES[f] else None
                                                  for f in FAMILIES},
                    "recognition_subtotal": sum(points.values()),
                    "provisional_observed_subtotal": observed_audience + sum(points.values()),
                    "overall_score": None, "status": "provisional_incomplete",
                    "enabled_extensions": enabled,
                    "missing_audience_capacity": 25 * sum(a["points"] is None for a in audience.values()),
                    "unverified_recognition_capacity": sum(FAMILIES[f] - points[f] for f in FAMILIES),
                }
        films.append({**identity, "notes": research["film_notes"].get(iid, []),
                      "ratings": observations, "coverage": coverage,
                      "historical_normalized_scores": old.get("family_scores", {}),
                      "historical_recognition_projection": frozen["observed_points"],
                      "award_breakdown": recognition(records),
                      "extension_evidence": [e for e in research["extensions"] if e["imdb_id"] == iid],
                      "variants": variants})
    # Audience ranks ONLY: same archived paired-source batch, no award ranks.
    paired = [f for f in films if all(o["status"] == "archived" for o in f["ratings"].values())]
    ranks = {}
    for scenario in SCENARIOS:
        vals = {f["imdb_id"]: f["variants"][scenario + "/base"]["audience_points"] for f in paired}
        ranks[scenario] = {iid: 1 + sum(v > value + 1e-9 for v in vals.values()) for iid, value in vals.items()}
    diagnostics = {
        "film_count": len(films), "years": dict(Counter(f["year"] for f in films)),
        "ratings": {s: dict(Counter(f["ratings"][s]["status"] for f in films)) for s in SCALES},
        "complete_overall_scores": 0,
        "archive_paired_audience_comparison": {"film_count": len(paired), "ranks": ranks},
        "coverage_check_statuses": dict(Counter(c["status"] for c in research["coverage_checks"])),
        "fresh_award_fact_count": len(research["awards"]),
        "maximum_audience_change": {},
    }
    for scenario in ("modest", "stronger"):
        deltas = [(f["variants"][scenario + "/base"]["observed_audience_subtotal"] -
                   f["variants"]["unsmoothed/base"]["observed_audience_subtotal"], f["imdb_id"])
                  for f in films]
        diagnostics["maximum_audience_change"][scenario] = max(deltas, key=lambda x: abs(x[0]))
    return rounded({"schema_version": 1, "research_date": research["research_date"],
                    "warning": "Mixed-age evidence. Observed subtotals are conditional on pinned ratings; "
                               "they are not current-score lower bounds or comparable overall ranks.",
                    "policy": {"family_caps": FAMILIES, "audience_caps": {s: 25 for s in SCALES},
                               "rating_scales": SCALES, "prior_means": {s: sum(v)/2 for s, v in SCALES.items()},
                               "experimental_prior_strengths": SCENARIOS,
                               "historical_award_components": POLICY},
                    "input_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                     for p in sorted((ROOT / "inputs").glob("*.json"))},
                    "diagnostics": diagnostics, "films": films})


def render_csv(result):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["imdb_id", "tmdb_id", "title", "year", "variant", "imdb_points", "letterboxd_points",
                     *FAMILIES, "observed_subtotal", "overall_score", "status"])
    for film in result["films"]:
        for name, variant in film["variants"].items():
            writer.writerow([film["imdb_id"], film["tmdb_id"], film["title"], film["year"], name,
                             *(variant["audience_components"][s]["points"] for s in SCALES),
                             *(variant["recognition_observed_points"][f] for f in FAMILIES),
                             variant["provisional_observed_subtotal"], None, variant["status"]])
    return stream.getvalue()


def render_markdown(result):
    lines = ["# Film-level breakdowns — " + result["research_date"], "",
             "Generated offline by `calibrate.py`; see [report.md](report.md) for interpretation.", "",
             "All totals below are **provisional observed subtotals**, conditional on mixed-age pinned "
             "ratings. They are not current-score lower bounds. An unchecked family has unknown "
             "points; a displayed 0 is only its observed contribution. No overall ranks are assigned.", "",
             "Overview: **modest/base** (1,000 equivalent prior votes per source, no candidate bonuses).", "",
             "| Film | Year | IMDb / TMDb | IMDb points | LB points | EU | Indie | US | Critics | Observed subtotal |",
             "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    def fmt(value):
        return "unavailable" if value is None else f"{value:.1f}"
    for f in result["films"]:
        v = f["variants"]["modest/base"]
        vals = [v["audience_components"][s]["points"] for s in SCALES]
        vals += list(v["recognition_observed_points"].values()) + [v["provisional_observed_subtotal"]]
        lines.append(f"| {f['title']} | {f['year']} | {f['imdb_id']} / {f['tmdb_id']} | " +
                     " | ".join(fmt(x) for x in vals) + " |")
    for f in result["films"]:
        lines += ["", "## " + f["title"], "",
                  f"[{f['imdb_id']}](https://www.imdb.com/title/{f['imdb_id']}/) · "
                  f"[TMDb {f['tmdb_id']}]({f['tmdb_url']}) · [ID mapping]({f['wikidata_url']})", "",
                  f"Stratum: `{f['stratum']}`. TMDb release event: "
                  + ", ".join(e["startDate"] for e in f["tmdb_release_events"]) + ".", ""]
        lines.extend(note + "\n" for note in f["notes"])
        for s, o in f["ratings"].items():
            lines.append(f"- {s}: {o.get('rating')} / {o.get('votes')} votes; `{o['status']}`; "
                         f"measurement date {o.get('measurement_date')}; [source]({o['source_url']}).")
        lines += ["", "| Scenario | IMDb | LB | Audience change vs unsmoothed | Subtotal base / TIFF / script / both |",
                  "| --- | ---: | ---: | ---: | --- |"]
        for scenario in SCENARIOS:
            v = f["variants"][scenario + "/base"]
            a = v["audience_components"]
            delta = sum(x["adjustment_points"] or 0 for x in a.values())
            totals = " / ".join(fmt(f["variants"][scenario + "/" + e]["provisional_observed_subtotal"])
                                for e in EXTENSIONS)
            lines.append(f"| {scenario} | {fmt(a['imdb']['points'])} | {fmt(a['letterboxd']['points'])} | "
                         f"{delta:+.1f} | {totals} |")
        lines += ["", "Award facts (component duplicates take the strongest value):", ""]
        for key, component in f["award_breakdown"]["components"].items():
            lines.append(f"- `{key}` = {component['normalized_points']}/100 before family scaling/cap.")
            for evidence in component["evidence"]:
                lines.append(f"  - {evidence['category']}; {evidence['status']}; "
                             f"{evidence['verification']}; [evidence]({evidence['source_url']}).")
        if not f["award_breakdown"]["components"]:
            lines.append("- No scored award facts in this evidence packet; this is not verified absence.")
        for e in f["extension_evidence"]:
            lines.append(f"- Candidate `{e['kind']}` only: {e['fact']}; [source]({e['source_url']}).")
        lines += ["", "Coverage checks (scoped absences do not certify whole-family absence):", ""]
        for family, venues in f["coverage"].items():
            lines.append(f"- {family}: " + "; ".join(f"{venue}={c['status']}" for venue, c in venues.items()))
            for venue, c in venues.items():
                for check in c["checks"]:
                    lines.append(f"  - {venue}: `{check['status']}`, {check['scope']}; "
                                 f"[source]({check['source_url']}).")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = calculate()
    outputs = {"results.json": json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
               "comparison.csv": render_csv(result), "breakdowns.md": render_markdown(result)}
    stale = []
    for name, content in outputs.items():
        path = ROOT / name
        if args.check:
            if not path.exists() or path.read_bytes() != content.encode("utf-8"):
                stale.append(name)
        else:
            path.write_bytes(content.encode("utf-8"))
    if stale:
        parser.exit(1, "Stale research outputs: " + ", ".join(stale) + "\n")
    print(f"{'Checked' if args.check else 'Generated'} {len(result['films'])} films, "
          "12 variants each; no network or production changes.")


if __name__ == "__main__":
    main()
