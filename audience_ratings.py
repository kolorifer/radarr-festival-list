import json
import os
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_KEY = os.environ["REELDB_API_KEY"]
SOURCE = Path("backcatalog-details.json")
PHASE_B = Path("sources/phase-b-institutional.json")
EVIDENCE = Path("sources/evidence-families.json")
DISCOVERY = Path("sources/imdb-audience-discovery.json")
OUTPUT = Path("audience-ratings.json")
API_BASE = "https://api.reeldb.io"

# ReelDB documents 60 requests/minute and 1000/day for this account tier.
# Stay comfortably below the minute limit while allowing one research run to
# expand the 2000+ union universe with audience-discovery seeds.
MAX_REQUESTS_PER_RUN = 400
REQUEST_INTERVAL_SECONDS = 1.35
RATE_LIMIT_RETRY_SECONDS = 65


def fetch_rating(imdb_id):
    query = urlencode({"apikey": API_KEY})
    url = f"{API_BASE}/v1/title/{imdb_id}/ratings?{query}"
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "radarr-festival-list/1.0"})
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def append_unique_movie(movies, seen, imdb_id, title, year, tspdt_rank=None):
    if not imdb_id or imdb_id in seen:
        return
    movies.append({"imdb_id": imdb_id, "title": title, "year": year, "tspdt_rank": tspdt_rank})
    seen.add(imdb_id)


def build_movie_universe():
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    movies = list(source["candidates"])
    seen = {m.get("imdb_id") for m in movies if m.get("imdb_id")}

    if PHASE_B.exists():
        phase_b = json.loads(PHASE_B.read_text(encoding="utf-8"))
        for film in phase_b.get("films", []):
            append_unique_movie(movies, seen, film.get("imdb_id"), film.get("title"), film.get("year"))

    if EVIDENCE.exists():
        snapshot = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        for imdb_id, film in (snapshot.get("films") or {}).items():
            append_unique_movie(movies, seen, imdb_id, film.get("title"), film.get("year"))

    # IMDb discovery is only a broad seed. ReelDB coverage collected here lets
    # the scoring layer test genuine IMDb + Letterboxd + Trakt convergence.
    # Audience evidence alone never qualifies a film.
    if DISCOVERY.exists():
        discovery = json.loads(DISCOVERY.read_text(encoding="utf-8"))
        for film in discovery.get("films", []):
            append_unique_movie(movies, seen, film.get("imdb_id"), film.get("title"), film.get("year"))

    return movies


def fetch_with_single_rate_limit_retry(imdb_id):
    try:
        return fetch_rating(imdb_id)
    except HTTPError as exc:
        if exc.code != 429:
            raise
        print(f"Rate limit reached; waiting {RATE_LIMIT_RETRY_SECONDS}s before one retry.")
        time.sleep(RATE_LIMIT_RETRY_SECONDS)
        return fetch_rating(imdb_id)


def main():
    movies = build_movie_universe()
    if OUTPUT.exists():
        existing = json.loads(OUTPUT.read_text(encoding="utf-8"))
        results = existing.get("ratings", {})
        unavailable = existing.get("unavailable", {})
    else:
        results = {}
        unavailable = {}

    pending_all = [
        m for m in movies
        if m.get("imdb_id") and m["imdb_id"] not in results and m["imdb_id"] not in unavailable
    ]
    pending = pending_all[:MAX_REQUESTS_PER_RUN]
    print(f"{len(movies)} resolved movies in expanded evidence universe")
    print(f"{len(results)} already cached")
    print(f"{len(unavailable)} known unavailable")
    print(f"{len(pending_all)} total missing; attempting at most {len(pending)} this run")
    failures = []

    for index, movie in enumerate(pending, 1):
        imdb_id = movie["imdb_id"]
        try:
            data = fetch_with_single_rate_limit_retry(imdb_id)
            results[imdb_id] = {
                "title": movie.get("title"),
                "year": movie.get("year"),
                "tspdt_rank": movie.get("tspdt_rank"),
                "reeldb": data,
            }
            print(f"[{index}/{len(pending)}] {movie.get('title')} ({movie.get('year')}) OK")
        except HTTPError as exc:
            print(f"[{index}/{len(pending)}] {movie.get('title')} HTTP {exc.code}")
            if exc.code == 404:
                unavailable[imdb_id] = {
                    "title": movie.get("title"),
                    "year": movie.get("year"),
                    "error": "HTTP 404",
                }
                print("Cached as unavailable; future runs will not spend another request on this ID.")
            else:
                failures.append({"imdb_id": imdb_id, "title": movie.get("title"), "error": f"HTTP {exc.code}"})
            if exc.code == 429:
                print("Rate limit still active after retry; stopping cleanly.")
                break
        except (URLError, TimeoutError) as exc:
            print(f"[{index}/{len(pending)}] {movie.get('title')} ERROR: {type(exc).__name__}")
            failures.append({"imdb_id": imdb_id, "title": movie.get("title"), "error": type(exc).__name__})

        if index % 25 == 0:
            write_output(results, unavailable, failures)
        if index < len(pending):
            time.sleep(REQUEST_INTERVAL_SECONDS)

    write_output(results, unavailable, failures)
    print(f"Ratings collected: {len(results)}")
    print(f"Unavailable IDs: {len(unavailable)}")
    print(f"Transient failures this run: {len(failures)}")


def write_output(results, unavailable, failures):
    payload = {
        "source": "ReelDB",
        "purpose": "audience-rating research; not yet part of production scoring",
        "ratings_count": len(results),
        "unavailable_count": len(unavailable),
        "ratings": results,
        "unavailable": unavailable,
        "failures": failures,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
