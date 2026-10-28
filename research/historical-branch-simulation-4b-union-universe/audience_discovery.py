"""Build a broad 2000+ audience-discovery seed from IMDb public datasets.

Research only. This does not qualify films by itself. It widens the candidate
universe so films absent from critic/institutional source lists can still be
examined once independent non-audience evidence is available.
"""

import csv
import gzip
import io
import json
from pathlib import Path
from urllib.request import Request, urlopen

RATINGS_URL = "https://datasets.imdbws.com/title.ratings.tsv.gz"
BASICS_URL = "https://datasets.imdbws.com/title.basics.tsv.gz"
OUTPUT = Path("sources/imdb-audience-discovery.json")
MIN_YEAR = 2000
MAX_YEAR = 2026

# Deliberately permissive discovery tiers. These are only a gateway into the
# research universe, never a qualification rule.
DISCOVERY_TIERS = (
    {"min_votes": 100_000, "min_rating": 7.2, "label": "broad"},
    {"min_votes": 25_000, "min_rating": 7.8, "label": "strong"},
    {"min_votes": 10_000, "min_rating": 8.2, "label": "exceptional"},
)


def qualifies(rating, votes):
    if not isinstance(rating, (int, float)) or not isinstance(votes, int):
        return None
    for tier in DISCOVERY_TIERS:
        if votes >= tier["min_votes"] and rating >= tier["min_rating"]:
            return tier["label"]
    return None


def open_gzip_tsv(url):
    req = Request(url, headers={"User-Agent": "radarr-festival-list research/1.0"})
    response = urlopen(req, timeout=120)
    gz = gzip.GzipFile(fileobj=response)
    return io.TextIOWrapper(gz, encoding="utf-8", newline="")


def collect_rating_seeds():
    seeds = {}
    with open_gzip_tsv(RATINGS_URL) as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            try:
                rating = float(row["averageRating"])
                votes = int(row["numVotes"])
            except (KeyError, TypeError, ValueError):
                continue
            tier = qualifies(rating, votes)
            if tier:
                seeds[row["tconst"]] = {
                    "imdb_id": row["tconst"],
                    "imdb_rating": rating,
                    "imdb_votes": votes,
                    "discovery_tier": tier,
                }
    return seeds


def attach_titles(seeds):
    films = []
    wanted = set(seeds)
    with open_gzip_tsv(BASICS_URL) as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            imdb_id = row.get("tconst")
            if imdb_id not in wanted:
                continue
            if row.get("titleType") != "movie" or row.get("isAdult") == "1":
                continue
            try:
                year = int(row.get("startYear") or "")
            except ValueError:
                continue
            if not MIN_YEAR <= year <= MAX_YEAR:
                continue
            seed = seeds[imdb_id]
            films.append({
                **seed,
                "title": row.get("primaryTitle") or row.get("originalTitle"),
                "original_title": row.get("originalTitle"),
                "year": year,
            })
    films.sort(key=lambda x: (-x["imdb_votes"], -x["imdb_rating"], x["title"] or ""))
    return films


def main():
    seeds = collect_rating_seeds()
    films = attach_titles(seeds)
    payload = {
        "mode": "research-imdb-audience-discovery-v1",
        "purpose": "candidate discovery only; audience alone never qualifies a film",
        "year_range": [MIN_YEAR, MAX_YEAR],
        "source": "IMDb public title.ratings + title.basics datasets",
        "tiers": list(DISCOVERY_TIERS),
        "count": len(films),
        "films": films,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"discovery_candidates": len(films), "year_range": [MIN_YEAR, MAX_YEAR]}))


if __name__ == "__main__":
    main()
