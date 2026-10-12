"""Test diminishing returns between TSPDT and Sight & Sound.

The ranked-source audit found 100% containment of the 29 modern Sight & Sound
entries inside TSPDT and a Spearman rho around 0.83. Treating both as fully
independent 100-point votes therefore risks double-counting the same long-term
canon signal. This diagnostic compares several combined-canon formulas without
changing active scores or qualification.
"""

import json
from pathlib import Path

SCORES = Path("evidence-scores.json")
OUTPUT = Path("canon-overlap-experiment.json")

VARIANTS = {
    "separate_200": {"mode": "separate", "ceiling": 1000},
    "canon150_half_corroboration": {"mode": "merge", "corroboration": 0.50, "cap": 150.0, "ceiling": 950},
    "canon125_quarter_corroboration": {"mode": "merge", "corroboration": 0.25, "cap": 125.0, "ceiling": 925},
    "canon100_single_family": {"mode": "merge", "corroboration": 0.25, "cap": 100.0, "ceiling": 900},
}

CONTROLS = {
    "There Will Be Blood": 2007,
    "Parasite": 2019,
    "Moonlight": 2016,
    "Mulholland Drive": 2001,
    "Get Out": 2017,
    "The Tree of Life": 2011,
    "Mad Max: Fury Road": 2015,
    "Melancholia": 2011,
    "Yi Yi": 2000,
    "The Gleaners & I": 2000,
    "Goodbye, Dragon Inn": 2003,
    "The Swamp": 2001,
    "Zama": 2017,
    "Caché": 2005,
    "Dogville": 2003,
    "The Turin Horse": 2011,
    "Blade Runner 2049": 2017,
    "La Commune (Paris, 1871)": 2000,
}


def canon_points(tspdt, ss, spec):
    tspdt = float(tspdt or 0)
    ss = float(ss or 0)
    if spec["mode"] == "separate":
        return round(tspdt + ss, 2)
    if tspdt <= 0:
        return round(min(spec["cap"], ss), 2)
    if ss <= 0:
        return round(min(spec["cap"], tspdt), 2)
    strongest = max(tspdt, ss)
    weaker = min(tspdt, ss)
    return round(min(spec["cap"], strongest + spec["corroboration"] * weaker), 2)


def compact(row):
    return {
        "title": row.get("title"),
        "year": row.get("year"),
        "base_score": row.get("overall_score"),
        "new_score": row.get("experimental_score"),
        "base_rank": row.get("overall_rank"),
        "new_rank": row.get("experimental_rank"),
        "tspdt": row.get("_tspdt"),
        "sight_sound": row.get("_ss"),
        "base_canon": row.get("_base_canon"),
        "new_canon": row.get("_new_canon"),
        "delta": row.get("_canon_delta"),
        "qualified": bool(row.get("qualified")),
    }


def control_lookup(rows, title, year):
    matches = [
        row for row in rows
        if row.get("title") == title
        and str(row.get("year") or "").isdigit()
        and abs(int(row.get("year")) - int(year)) <= 1
    ]
    return matches[0] if len(matches) == 1 else None


def run_variant(rows, name, spec):
    experimental = []
    for row in rows:
        points = row.get("source_points") or {}
        tspdt = float(points.get("tspdt_21c") or 0)
        ss = float(points.get("sight_sound") or 0)
        old = tspdt + ss
        new = canon_points(tspdt, ss, spec)
        exp = dict(row)
        exp.update({
            "_tspdt": round(tspdt, 2),
            "_ss": round(ss, 2),
            "_base_canon": round(old, 2),
            "_new_canon": round(new, 2),
            "_canon_delta": round(new - old, 2),
            "experimental_score": round(float(row.get("overall_score") or 0) - old + new, 2),
        })
        experimental.append(exp)
    experimental.sort(key=lambda r: (-r["experimental_score"], r.get("title") or ""))
    for rank, row in enumerate(experimental, 1):
        row["experimental_rank"] = rank

    base_top100 = {r.get("imdb_id") for r in rows[:100]}
    top100 = {r.get("imdb_id") for r in experimental[:100]}
    thresholds = {}
    for floor in (300, 275, 250, 225, 200):
        selected = [r for r in experimental if r["experimental_score"] >= floor and r.get("has_non_audience_evidence")]
        thresholds[str(floor)] = {
            "selected": len(selected),
            "promotions_vs_old": sum(not bool(r.get("qualified")) for r in selected),
            "old_qualified_retained": sum(bool(r.get("qualified")) for r in selected),
        }
    changed = [r for r in experimental if abs(r["_canon_delta"]) > 0.001]
    changed.sort(key=lambda r: (r["_canon_delta"], r.get("title") or ""))
    controls = {}
    for title, year in CONTROLS.items():
        row = control_lookup(experimental, title, year)
        if row:
            controls[title] = compact(row)
    return {
        "variant": name,
        "score_ceiling": spec["ceiling"],
        "top100_overlap_with_base": len(base_top100 & top100),
        "thresholds": thresholds,
        "controls": controls,
        "affected_films": len(changed),
        "largest_reductions": [compact(r) for r in changed[:40]],
    }


def main():
    payload = json.loads(SCORES.read_text(encoding="utf-8"))
    rows = payload.get("films") or []
    results = {name: run_variant(rows, name, spec) for name, spec in VARIANTS.items()}
    out = {
        "mode": "research-canon-overlap-experiment-v2-title-year-controls",
        "qualification_unchanged": True,
        "active_score_mode": payload.get("mode"),
        "reason": "TSPDT and Sight & Sound show 100% containment for the 29 modern S&S entries and Spearman rho ~0.83; test diminishing returns before freezing weights.",
        "variants": results,
    }
    OUTPUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        name: {
            "ceiling": result["score_ceiling"],
            "top100_overlap": result["top100_overlap_with_base"],
            "thresholds": result["thresholds"],
            "controls": result["controls"],
        }
        for name, result in results.items()
    }, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
