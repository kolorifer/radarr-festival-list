"""Research comparison for the official BFI Sight & Sound 2022 top 250.

The current snapshot was seeded from a third-party top-100 text file. This
experiment replaces only the Sight & Sound contribution with published BFI
positions from a static official-source snapshot, leaving all other evidence
families and qualification routes unchanged.
"""

import json
import re
import unicodedata
from pathlib import Path

SCORES = Path("evidence-scores.json")
SOURCE = Path("sources/sight-sound-2022-top250-modern.json")
OUTPUT = Path("sight-sound-top250-experiment.json")

ALIASES = {
    "mulhollanddr": ("mulhollanddrive",),
    "thegleanersandi": ("thegleanersi",),
    "westofthetracks": ("tiexiquwestofthetracks",),
}

CONTROLS = {
    "Melancholia": 2011,
    "Get Out": 2017,
    "The Tree of Life": 2011,
    "There Will Be Blood": 2007,
    "Mad Max: Fury Road": 2015,
    "Parasite": 2019,
    "Moonlight": 2016,
    "Caché": 2005,
    "Certified Copy": 2010,
    "First Reformed": 2017,
    "Goodbye, Dragon Inn": 2003,
    "Zama": 2017,
    "The Gleaners & I": 2000,
    "La Ciénaga": 2001,
}


def norm(value):
    text = unicodedata.normalize("NFKD", str(value).casefold())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "", text)


def ranked_points(rank, depth):
    if not isinstance(rank, int) or not isinstance(depth, int) or depth < 1:
        return 0.0
    if rank < 1 or rank > depth:
        return 0.0
    if depth == 1:
        return 100.0
    return round(100.0 - 99.0 * (rank - 1) / (depth - 1), 2)


def build_index(rows):
    out = {}
    for row in rows:
        key = norm(row.get("title"))
        out.setdefault(key, []).append(row)
    return out


def resolve(source_row, index):
    key = norm(source_row.get("title"))
    keys = (key,) + ALIASES.get(key, ())
    candidates = []
    for candidate_key in keys:
        candidates.extend(index.get(candidate_key, []))
    year = int(source_row.get("year") or 0)
    candidates = [
        r for r in candidates
        if not year or not str(r.get("year") or "").isdigit() or abs(int(r.get("year")) - year) <= 1
    ]
    unique = {r.get("imdb_id"): r for r in candidates if r.get("imdb_id")}
    return next(iter(unique.values())) if len(unique) == 1 else None


def compact(row):
    return {
        "title": row.get("title"),
        "year": row.get("year"),
        "imdb_id": row.get("imdb_id"),
        "base_rank": row.get("overall_rank"),
        "base_score": row.get("overall_score"),
        "new_rank": row.get("experimental_rank"),
        "new_score": row.get("experimental_score"),
        "old_sight_sound": row.get("old_sight_sound"),
        "new_sight_sound": row.get("new_sight_sound"),
        "delta": row.get("sight_sound_delta"),
        "qualified": bool(row.get("qualified")),
    }


def control_lookup(rows, title, year):
    title_key = norm(title)
    matches = [
        r for r in rows
        if norm(r.get("title")) == title_key
        and (not str(r.get("year") or "").isdigit() or abs(int(r.get("year")) - int(year)) <= 1)
    ]
    if len(matches) == 1:
        return matches[0]
    # Some repository titles use translated/alternate names. Prefer an official
    # Sight & Sound hit in the requested year if the display title is different.
    matches = [
        r for r in rows
        if r.get("official_sight_sound_rank") is not None
        and str(r.get("year") or "").isdigit()
        and abs(int(r.get("year")) - int(year)) <= 1
        and any(norm(alias) == norm(r.get("title")) for alias in ALIASES.get(title_key, ()))
    ]
    return matches[0] if len(matches) == 1 else None


def main():
    payload = json.loads(SCORES.read_text(encoding="utf-8"))
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    rows = payload.get("films") or []
    depth = int(source.get("published_depth") or 250)
    index = build_index(rows)

    resolved = {}
    unresolved = []
    for item in source.get("films", []):
        hit = resolve(item, index)
        if not hit:
            unresolved.append(item)
            continue
        resolved[hit.get("imdb_id")] = item

    experimental = []
    for row in rows:
        old_ss = float((row.get("source_points") or {}).get("sight_sound") or 0)
        source_row = resolved.get(row.get("imdb_id"))
        new_ss = ranked_points(int(source_row["rank"]), depth) if source_row else 0.0
        new_score = round(float(row.get("overall_score") or 0) - old_ss + new_ss, 2)
        exp = dict(row)
        exp.update({
            "old_sight_sound": round(old_ss, 2),
            "new_sight_sound": round(new_ss, 2),
            "sight_sound_delta": round(new_ss - old_ss, 2),
            "experimental_score": new_score,
            "official_sight_sound_rank": source_row.get("rank") if source_row else None,
        })
        experimental.append(exp)

    experimental.sort(key=lambda r: (-r["experimental_score"], r.get("title") or ""))
    for rank, row in enumerate(experimental, 1):
        row["experimental_rank"] = rank

    base_top100 = {r.get("imdb_id") for r in rows[:100]}
    new_top100 = {r.get("imdb_id") for r in experimental[:100]}

    threshold_summary = {}
    for floor in (300, 275, 250, 225, 200):
        selected = [r for r in experimental if r["experimental_score"] >= floor and r.get("has_non_audience_evidence")]
        threshold_summary[str(floor)] = {
            "selected": len(selected),
            "promotions_vs_old": sum(not bool(r.get("qualified")) for r in selected),
            "old_qualified_retained": sum(bool(r.get("qualified")) for r in selected),
        }

    changed = [r for r in experimental if abs(float(r.get("sight_sound_delta") or 0)) > 0.001]
    changed.sort(key=lambda r: (-abs(float(r.get("sight_sound_delta") or 0)), r.get("title") or ""))

    controls = {}
    for title, year in CONTROLS.items():
        row = control_lookup(experimental, title, year)
        if row:
            controls[title] = compact(row)

    out = {
        "mode": "research-sight-sound-official-top250-v2-matching",
        "qualification_unchanged": True,
        "source": source.get("source"),
        "source_url": source.get("source_url"),
        "published_depth": depth,
        "official_modern_entries": len(source.get("films", [])),
        "resolved_entries": len(resolved),
        "unresolved_entries": unresolved,
        "top100_overlap_with_base": len(base_top100 & new_top100),
        "thresholds": threshold_summary,
        "controls": controls,
        "largest_changes": [compact(r) for r in changed[:80]],
    }
    OUTPUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "official_entries": out["official_modern_entries"],
        "resolved": out["resolved_entries"],
        "unresolved": len(unresolved),
        "top100_overlap": out["top100_overlap_with_base"],
        "thresholds": threshold_summary,
        "controls": controls,
    }, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
