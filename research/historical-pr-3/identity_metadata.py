"""Read-only, secret-safe metadata collection for the research identity audit."""
import argparse, json, os, shlex, threading, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import audience_calibration_enrichment as ace

OUT = Path("sources/identity-audit/tmdb.json")
_LOCK = threading.Lock()
_NEXT = 0.0

def private_token():
    path = Path.home() / ".config/movie-intel/environment"
    values = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        parts = shlex.split(value)
        values[key.strip()] = parts[0] if parts else ""
    return values.get("TMDB_API_TOKEN", "")

def request(path, params, token):
    global _NEXT
    for attempt in range(3):
        with _LOCK:
            delay = _NEXT - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            _NEXT = time.monotonic() + 0.18
        req = Request("https://api.themoviedb.org/3/" + path + "?" + urlencode(params),
                      headers={"Authorization": "Bearer " + token, "Accept": "application/json"})
        try:
            with urlopen(req, timeout=20) as response:
                return json.load(response)
        except HTTPError as exc:
            if exc.code == 429 and attempt < 2:
                time.sleep(3 * (attempt + 1))
                continue
            return {"_error": "HTTP " + str(exc.code)}
        except (URLError, TimeoutError, ValueError):
            if attempt < 2:
                continue
            return {"_error": "network_or_schema_error"}
    return {"_error": "retry_exhausted"}

def movie_metadata(d):
    return {
        "tmdb_id": d.get("id"), "imdb_id": d.get("imdb_id"),
        "title": d.get("title"), "original_title": d.get("original_title"),
        "release_date": d.get("release_date"), "runtime": d.get("runtime"),
        "directors": sorted({r["name"] for r in (d.get("credits") or {}).get("crew", [])
                            if r.get("job") == "Director" and r.get("name")}),
        "countries": [r.get("name") for r in d.get("production_countries", []) if r.get("name")],
        "country_codes": [r.get("iso_3166_1") for r in d.get("production_countries", [])],
        "aliases": sorted({r["title"] for r in (d.get("alternative_titles") or {}).get("titles", [])
                           if r.get("title")}),
        "source_url": "https://www.themoviedb.org/movie/" + str(d.get("id")),
    }

def find(iid, token):
    data = request("find/" + iid, {"external_source": "imdb_id"}, token)
    if data.get("_error"):
        return {"status": data["_error"]}
    movies = data.get("movie_results") or []
    if len(movies) == 1:
        d = request("movie/" + str(movies[0]["id"]),
                    {"append_to_response": "credits,alternative_titles"}, token)
        if d.get("_error"):
            return {"status": d["_error"], "tmdb_id": movies[0]["id"]}
        m = movie_metadata(d)
        return {"status": "movie" if m["imdb_id"] == iid else "external_id_conflict", **m}
    return {"status": "no_unique_movie",
            "movies": [{"tmdb_id": m.get("id"), "title": m.get("title"),
                        "release_date": m.get("release_date")} for m in movies],
            "tv_episodes": [{"tmdb_id": e.get("id"), "title": e.get("name"),
                             "air_date": e.get("air_date"), "show_id": e.get("show_id"),
                             "season_number": e.get("season_number"),
                             "episode_number": e.get("episode_number")}
                            for e in data.get("tv_episode_results", [])],
            "tv_series": [{"tmdb_id": t.get("id"), "title": t.get("name"),
                           "first_air_date": t.get("first_air_date")} for t in data.get("tv_results", [])]}

def collect(root, only_ids=None):
    token = private_token()
    if not token:
        raise SystemExit("Missing existing private TMDb read token")
    path = root / OUT
    payload = json.loads(path.read_text()) if path.exists() else {
        "source": "TMDb find by IMDb ID, movie details, credits and alternative titles",
        "observed_at": datetime.now(timezone.utc).isoformat(), "films": {}}
    back = json.loads((root / "backcatalog-details.json").read_text())["candidates"]
    gaps = json.loads((root / ace.OUT / "coverage.json").read_text())["missing_audience"]
    ids = only_ids or {r["imdb_id"] for r in back + gaps} | {"tt0806125"}
    pending = sorted(set(ids) - payload["films"].keys())
    with ThreadPoolExecutor(max_workers=4) as pool:
        jobs = {pool.submit(find, iid, token): iid for iid in pending}
        for i, future in enumerate(as_completed(jobs), 1):
            payload["films"][jobs[future]] = future.result()
            if i % 50 == 0:
                ace.write_json(path, payload)
                print(json.dumps({"metadata_collected": i, "requested": len(pending)}), flush=True)
    payload["count"] = len(payload["films"])
    ace.write_json(path, payload)
    print(json.dumps({"metadata_total": payload["count"], "requested": len(pending)}), flush=True)

def search(title, year, token):
    d = request("search/movie", {"query": title, "year": year}, token)
    return [movie_metadata(request("movie/" + str(r["id"]),
             {"append_to_response": "credits,alternative_titles"}, token))
            for r in (d.get("results") or [])[:5]]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--only-id", action="append")
    args = parser.parse_args()
    collect(args.root, set(args.only_id) if args.only_id else None)
