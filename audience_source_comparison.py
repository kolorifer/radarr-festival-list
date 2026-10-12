"""Compare IMDb + Letterboxd against adding TMDb as a third audience source.

Research only. The active evidence score is IMDb 100 + Letterboxd 100. TMDb is
already present in the cached ReelDB payload, so this comparison needs no new
network requests or credentials.
"""

import json
import math
from pathlib import Path

SCORES = Path("evidence-scores.json")
RATINGS = Path("audience-ratings.json")
OUTPUT = Path("audience-source-comparison.json")

CONTROLS = [
    "Melancholia", "Get Out", "The Tree of Life", "Boyhood", "The Lives of Others",
    "Lost in Translation", "The White Ribbon", "Dogville", "The Turin Horse", "Arrival",
    "12 Years a Slave", "Gravity", "The Wolf of Wall Street", "Fish Tank",
    "Blue Is the Warmest Colour", "Winter Sleep", "Shame", "Nocturnal Animals",
    "Once Upon a Time in... Hollywood", "Donnie Darko", "There Will Be Blood", "Dune",
    "Midsommar", "Blade Runner 2049", "Memento", "1917", "Mad Max: Fury Road", "Her",
    "Ex Machina", "Manchester by the Sea", "Into the Wild", "The Lobster",
    "The Killing of a Sacred Deer", "Past Lives", "Scott Pilgrim vs. the World",
    "The Departed", "Amores Perros", "A Prophet", "Caché", "Phantom Thread",
    "La Commune (Paris, 1871)",
]


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


def rank_values(values):
    indexed = sorted(enumerate(values), key=lambda x: x[1])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(indexed):
        j = i + 1
        while j < len(indexed) and indexed[j][1] == indexed[i][1]:
            j += 1
        rank = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks[indexed[k][0]] = rank
        i = j
    return ranks


def spearman(xs, ys):
    if len(xs) < 2:
        return None
    return pearson(rank_values(xs), rank_values(ys))


def audience_triplet(row):
    active = row.get("source_points") or {}
    experimental = row.get("experimental_source_points") or {}
    return (
        float(active.get("imdb_audience") or 0.0),
        float(active.get("letterboxd_audience") or 0.0),
        float(experimental.get("tmdb_audience") or 0.0),
    )


def non_audience_score(row):
    imdb, lb, _ = audience_triplet(row)
    return float(row.get("overall_score") or 0.0) - imdb - lb


def scenario_rows(rows, mode):
    out = []
    for row in rows:
        imdb, lb, tmdb = audience_triplet(row)
        non_aud = non_audience_score(row)
        if mode == "two_source_200":
            audience = imdb + lb
        elif mode == "three_source_300":
            audience = imdb + lb + tmdb
        elif mode == "three_source_200":
            audience = (imdb + lb + tmdb) * (2.0 / 3.0)
        else:
            raise ValueError(mode)
        x = dict(row)
        x["scenario_score"] = round(non_aud + audience, 2)
        x["scenario_audience"] = round(audience, 2)
        x["imdb_points"] = imdb
        x["letterboxd_points"] = lb
        x["tmdb_points"] = tmdb
        out.append(x)
    out.sort(key=lambda r: (-r["scenario_score"], -r.get("source_hits", 0), r.get("title") or ""))
    for i, row in enumerate(out, 1):
        row["scenario_rank"] = i
    return out


def compact(row):
    return {
        "title": row.get("title"),
        "year": row.get("year"),
        "imdb_id": row.get("imdb_id"),
        "rank": row.get("scenario_rank"),
        "score": row.get("scenario_score"),
        "imdb": round(row.get("imdb_points", 0), 2),
        "letterboxd": round(row.get("letterboxd_points", 0), 2),
        "tmdb": round(row.get("tmdb_points", 0), 2),
        "source_hits": row.get("source_hits"),
        "qualified": row.get("qualified"),
        "routes": row.get("routes", []),
    }


def cutoff_delta(base, candidate, n):
    base_top = {r["imdb_id"]: r for r in base[:n]}
    cand_top = {r["imdb_id"]: r for r in candidate[:n]}
    entered_ids = set(cand_top) - set(base_top)
    exited_ids = set(base_top) - set(cand_top)
    entered = [compact(cand_top[x]) for x in entered_ids]
    exited = [compact(base_top[x]) for x in exited_ids]
    entered.sort(key=lambda r: r["rank"])
    exited.sort(key=lambda r: r["rank"])
    return {"overlap": n - len(entered), "entered": entered, "exited": exited}


def source_coverage(ratings, rows):
    raw = ratings.get("ratings") or {}
    result = {}
    for source in ("imdb", "letterboxd", "tmdb"):
        raw_count = 0
        positive_count = 0
        for row in rows:
            rr = (raw.get(row.get("imdb_id")) or {}).get("reeldb") or {}
            item = rr.get(source) or {}
            votes = item.get("votes") if item.get("votes") is not None else item.get("ratings")
            if isinstance(item.get("rating"), (int, float)) and isinstance(votes, (int, float)):
                raw_count += 1
            idx = {"imdb": 0, "letterboxd": 1, "tmdb": 2}[source]
            if audience_triplet(row)[idx] > 0:
                positive_count += 1
        result[source] = {"raw_rating_and_votes": raw_count, "positive_scored": positive_count}
    return result


def source_correlations(rows):
    pairs = {}
    specs = (("imdb", 0, "letterboxd", 1), ("imdb", 0, "tmdb", 2), ("letterboxd", 1, "tmdb", 2))
    for a, ia, b, ib in specs:
        xs, ys = [], []
        for row in rows:
            vals = audience_triplet(row)
            if vals[ia] > 0 and vals[ib] > 0:
                xs.append(vals[ia])
                ys.append(vals[ib])
        pairs[f"{a}_vs_{b}"] = {
            "n": len(xs),
            "pearson_points": pearson(xs, ys),
            "spearman_points": spearman(xs, ys),
        }
    return pairs


def controls_for(scenarios):
    by_scenario = {}
    for name, rows in scenarios.items():
        by_title = {r.get("title"): r for r in rows}
        by_scenario[name] = [compact(by_title[t]) for t in CONTROLS if t in by_title]
    return by_scenario


def biggest_rank_changes(base, candidate, limit=25):
    base_rank = {r["imdb_id"]: r["scenario_rank"] for r in base}
    rows = []
    for row in candidate:
        old = base_rank.get(row["imdb_id"])
        if old is None:
            continue
        change = old - row["scenario_rank"]
        if change:
            item = compact(row)
            item["rank_two_source_200"] = old
            item["rank_change"] = change
            rows.append(item)
    up = sorted(rows, key=lambda r: -r["rank_change"])[:limit]
    down = sorted(rows, key=lambda r: r["rank_change"])[:limit]
    return {"up": up, "down": down}


def main():
    score_payload = json.loads(SCORES.read_text())
    ratings = json.loads(RATINGS.read_text())
    rows = score_payload.get("films") or []
    scenarios = {
        "two_source_200": scenario_rows(rows, "two_source_200"),
        "three_source_300": scenario_rows(rows, "three_source_300"),
        "three_source_200": scenario_rows(rows, "three_source_200"),
    }
    base = scenarios["two_source_200"]

    output = {
        "mode": "audience-source-comparison-v1",
        "production_unchanged": True,
        "qualification_unchanged": True,
        "film_count": len(rows),
        "modes": {
            "two_source_200": "IMDb 0..100 + Letterboxd 0..100 (active baseline)",
            "three_source_300": "IMDb 0..100 + Letterboxd 0..100 + TMDb 0..100",
            "three_source_200": "IMDb + Letterboxd + TMDb equally weighted, combined audience cap 200",
        },
        "coverage": source_coverage(ratings, rows),
        "correlations": source_correlations(rows),
        "cutoff_deltas_vs_two_source_200": {},
        "controls": controls_for(scenarios),
        "rank_changes_vs_two_source_200": {},
    }
    for name in ("three_source_300", "three_source_200"):
        output["cutoff_deltas_vs_two_source_200"][name] = {
            str(n): cutoff_delta(base, scenarios[name], n) for n in (50, 100, 200, 300, 500)
        }
        output["rank_changes_vs_two_source_200"][name] = biggest_rank_changes(base, scenarios[name])

    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    compact_out = {
        "coverage": output["coverage"],
        "correlations": output["correlations"],
        "top100": {name: output["cutoff_deltas_vs_two_source_200"][name]["100"] for name in ("three_source_300", "three_source_200")},
    }
    print(json.dumps(compact_out, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
