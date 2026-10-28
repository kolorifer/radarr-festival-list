"""Compare audience-source architectures using cached ReelDB data.

Research only. The active evidence score remains IMDb 100 + Letterboxd 100.
TMDb and Trakt are evaluated as alternative third audience populations, both
at a full 300-point mode and at a combined 200-point audience cap. A four-source
200-point mode is included as a diagnostic only. No network requests are made.
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
SOURCES = ("imdb", "letterboxd", "tmdb", "trakt")


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


def audience_values(row):
    active = row.get("source_points") or {}
    experimental = row.get("experimental_source_points") or {}
    return {
        "imdb": float(active.get("imdb_audience") or 0.0),
        "letterboxd": float(active.get("letterboxd_audience") or 0.0),
        "tmdb": float(experimental.get("tmdb_audience") or 0.0),
        "trakt": float(experimental.get("trakt_audience") or 0.0),
    }


def non_audience_score(row):
    vals = audience_values(row)
    return float(row.get("overall_score") or 0.0) - vals["imdb"] - vals["letterboxd"]


def scenario_spec(mode):
    specs = {
        "two_source_200": (("imdb", "letterboxd"), 1.0),
        "tmdb_three_source_300": (("imdb", "letterboxd", "tmdb"), 1.0),
        "tmdb_three_source_200": (("imdb", "letterboxd", "tmdb"), 2.0 / 3.0),
        "trakt_three_source_300": (("imdb", "letterboxd", "trakt"), 1.0),
        "trakt_three_source_200": (("imdb", "letterboxd", "trakt"), 2.0 / 3.0),
        "four_source_200": (("imdb", "letterboxd", "tmdb", "trakt"), 0.5),
    }
    return specs[mode]


def scenario_rows(rows, mode):
    included, scale = scenario_spec(mode)
    out = []
    for row in rows:
        vals = audience_values(row)
        non_aud = non_audience_score(row)
        audience = sum(vals[k] for k in included) * scale
        active_audience_hits = sum(1 for k in included if vals[k] > 0)
        non_audience_hits = max(0, int(row.get("source_hits") or 0) - sum(1 for k in ("imdb", "letterboxd") if vals[k] > 0))
        x = dict(row)
        x["scenario_score"] = round(non_aud + audience, 2)
        x["scenario_audience"] = round(audience, 2)
        x["scenario_source_hits"] = non_audience_hits + active_audience_hits
        for key, value in vals.items():
            x[f"{key}_points"] = value
        out.append(x)
    out.sort(key=lambda r: (-r["scenario_score"], -r["scenario_source_hits"], r.get("title") or ""))
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
        "audience_total": row.get("scenario_audience"),
        "imdb": round(row.get("imdb_points", 0), 2),
        "letterboxd": round(row.get("letterboxd_points", 0), 2),
        "tmdb": round(row.get("tmdb_points", 0), 2),
        "trakt": round(row.get("trakt_points", 0), 2),
        "source_hits": row.get("scenario_source_hits"),
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


def _raw_item(ratings, imdb_id, source):
    rr = ((ratings.get("ratings") or {}).get(imdb_id) or {}).get("reeldb") or {}
    return rr.get(source) or {}


def _raw_rating(item):
    value = item.get("rating")
    return float(value) if isinstance(value, (int, float)) else None


def _raw_votes(item):
    value = item.get("votes") if item.get("votes") is not None else item.get("ratings")
    return float(value) if isinstance(value, (int, float)) else None


def source_coverage(ratings, rows):
    result = {}
    for source in SOURCES:
        raw_count = 0
        positive_count = 0
        for row in rows:
            item = _raw_item(ratings, row.get("imdb_id"), source)
            if _raw_rating(item) is not None and _raw_votes(item) is not None:
                raw_count += 1
            if audience_values(row)[source] > 0:
                positive_count += 1
        result[source] = {"raw_rating_and_votes": raw_count, "positive_scored": positive_count}
    return result


def source_correlations(ratings, rows):
    pairs = {}
    for i, a in enumerate(SOURCES):
        for b in SOURCES[i + 1:]:
            raw_x, raw_y, point_x, point_y = [], [], [], []
            for row in rows:
                item_a = _raw_item(ratings, row.get("imdb_id"), a)
                item_b = _raw_item(ratings, row.get("imdb_id"), b)
                ra, rb = _raw_rating(item_a), _raw_rating(item_b)
                if ra is not None and rb is not None:
                    raw_x.append(ra)
                    raw_y.append(rb)
                vals = audience_values(row)
                if vals[a] > 0 and vals[b] > 0:
                    point_x.append(vals[a])
                    point_y.append(vals[b])
            pairs[f"{a}_vs_{b}"] = {
                "n_raw": len(raw_x),
                "pearson_raw_rating": pearson(raw_x, raw_y),
                "spearman_raw_rating": spearman(raw_x, raw_y),
                "n_points": len(point_x),
                "pearson_points": pearson(point_x, point_y),
                "spearman_points": spearman(point_x, point_y),
            }
    return pairs


def controls_for(scenarios):
    by_scenario = {}
    for name, rows in scenarios.items():
        by_title = {}
        for row in rows:
            title = row.get("title")
            current = by_title.get(title)
            if current is None or row["scenario_rank"] < current["scenario_rank"]:
                by_title[title] = row
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
    mode_names = (
        "two_source_200",
        "tmdb_three_source_300",
        "tmdb_three_source_200",
        "trakt_three_source_300",
        "trakt_three_source_200",
        "four_source_200",
    )
    scenarios = {name: scenario_rows(rows, name) for name in mode_names}
    base = scenarios["two_source_200"]

    output = {
        "mode": "audience-source-comparison-v2-tmdb-trakt",
        "production_unchanged": True,
        "qualification_unchanged": True,
        "film_count": len(rows),
        "modes": {
            "two_source_200": "IMDb 0..100 + Letterboxd 0..100 (active baseline)",
            "tmdb_three_source_300": "IMDb + Letterboxd + TMDb, each 0..100",
            "tmdb_three_source_200": "IMDb + Letterboxd + TMDb equally weighted, combined audience cap 200",
            "trakt_three_source_300": "IMDb + Letterboxd + Trakt, each 0..100",
            "trakt_three_source_200": "IMDb + Letterboxd + Trakt equally weighted, combined audience cap 200",
            "four_source_200": "IMDb + Letterboxd + TMDb + Trakt equally weighted, combined audience cap 200",
        },
        "coverage": source_coverage(ratings, rows),
        "correlations": source_correlations(ratings, rows),
        "cutoff_deltas_vs_two_source_200": {},
        "controls": controls_for(scenarios),
        "rank_changes_vs_two_source_200": {},
    }
    compared = mode_names[1:]
    for name in compared:
        output["cutoff_deltas_vs_two_source_200"][name] = {
            str(n): cutoff_delta(base, scenarios[name], n) for n in (50, 100, 200, 300, 500)
        }
        output["rank_changes_vs_two_source_200"][name] = biggest_rank_changes(base, scenarios[name])

    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    focus = {"Melancholia", "The Tree of Life", "Blade Runner 2049", "1917", "Memento", "La Commune (Paris, 1871)"}
    compact_out = {
        "coverage": output["coverage"],
        "correlations": output["correlations"],
        "overlap": {
            name: {n: output["cutoff_deltas_vs_two_source_200"][name][str(n)]["overlap"] for n in (50, 100, 200, 300, 500)}
            for name in compared
        },
        "top100": {name: output["cutoff_deltas_vs_two_source_200"][name]["100"] for name in compared},
        "focus_controls": {
            name: [x for x in output["controls"][name] if x["title"] in focus]
            for name in mode_names
        },
    }
    print(json.dumps(compact_out, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
