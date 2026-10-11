import json
import os
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_KEY = os.environ["REELDB_API_KEY"]
SOURCE = Path("backcatalog-details.json")
OUTPUT = Path("audience-ratings.json")
API_BASE = "https://api.reeldb.io"
MAX_REQUESTS_PER_RUN = 50


def fetch_rating(imdb_id):
    query = urlencode({"apikey": API_KEY})
    url = f"{API_BASE}/v1/title/{imdb_id}/ratings?{query}"
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "radarr-festival-list/1.0"})
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def main():
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    movies = source["candidates"]
    if OUTPUT.exists():
        existing = json.loads(OUTPUT.read_text(encoding="utf-8"))
        results = existing.get("ratings", {})
    else:
        results = {}

    pending_all = [m for m in movies if m.get("imdb_id") and m["imdb_id"] not in results]
    pending = pending_all[:MAX_REQUESTS_PER_RUN]
    print(f"{len(movies)} resolved movies")
    print(f"{len(results)} already cached")
    print(f"{len(pending_all)} total missing; attempting at most {len(pending)} this run")
    failures = []

    for index, movie in enumerate(pending, 1):
        imdb_id = movie["imdb_id"]
        try:
            data = fetch_rating(imdb_id)
            results[imdb_id] = {"title": movie["title"], "year": movie["year"],
                                "tspdt_rank": movie["tspdt_rank"], "reeldb": data}
            print(f"[{index}/{len(pending)}] {movie['title']} ({movie['year']}) OK")
        except HTTPError as exc:
            print(f"[{index}/{len(pending)}] {movie['title']} HTTP {exc.code}")
            failures.append({"imdb_id": imdb_id, "title": movie["title"], "error": f"HTTP {exc.code}"})
            if exc.code == 429:
                print("Rate limit reached; stopping cleanly.")
                break
        except (URLError, TimeoutError) as exc:
            print(f"[{index}/{len(pending)}] {movie['title']} ERROR: {exc}")
            failures.append({"imdb_id": imdb_id, "title": movie["title"], "error": str(exc)})
        time.sleep(1.2)
        if index % 25 == 0:
            write_output(results, failures)

    write_output(results, failures)
    print(f"Ratings collected: {len(results)}")
    print(f"Failures this run: {len(failures)}")


def write_output(results, failures):
    payload = {"source": "ReelDB", "purpose": "audience-rating research; not yet part of production scoring",
               "ratings_count": len(results), "ratings": results, "failures": failures}
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
