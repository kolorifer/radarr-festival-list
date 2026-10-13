"""Collect missing research ratings without changing the candidate universe."""
import argparse
import copy
import csv
import gzip
import hashlib
import io
import json
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import evidence_score as es

OUT = Path("simulations/audience-cap-comparison")
IMDB_URL = "https://datasets.imdbws.com/title.ratings.tsv.gz"
INPUT_PATHS = (es.BACKCATALOG, es.INSTITUTIONAL, es.QUALIFIERS,
               es.AUDIENCE, es.SOURCE_SNAPSHOT, es.DISCOVERY)
PROVIDERS = ("imdb", "letterboxd", "trakt", "tmdb", "metacritic",
             "metacritic_user", "tomatoes", "tomatoes_audience",
             "roger_ebert", "myanimelist", "mdblist")


def load_inputs(root):
    return {str(p): json.loads((root / p).read_text(encoding="utf-8"))
            for p in INPUT_PATHS}


def universe(inputs):
    rows = es.build_rows(*(inputs[str(p)] for p in INPUT_PATHS))
    return [{k: r[k] for k in ("imdb_id", "title", "year")} for r in rows]


def valid_number(value):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value))


def valid_provider(item, source):
    if not isinstance(item, dict):
        return False
    votes = item.get("votes") if item.get("votes") is not None else item.get("ratings")
    maximum = {"imdb": 10, "letterboxd": 5}.get(source, 100)
    return (valid_number(item.get("rating")) and 0 <= item["rating"] <= maximum
            and valid_number(votes) and votes >= 0)


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2,
                                    allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def safe_ratings(payload):
    """Retain rating fields only; never persist arbitrary response text/URLs."""
    result = {}
    if not isinstance(payload, dict):
        raise ValueError("Unexpected provider schema")
    for source in PROVIDERS:
        item = payload.get(source)
        if not isinstance(item, dict):
            continue
        fields = {}
        for name in ("rating", "votes", "ratings"):
            if name not in item:
                continue
            value = item.get(name)
            if value is None or valid_number(value):
                fields[name] = value
        if isinstance(item.get("certified_fresh"), bool):
            fields["certified_fresh"] = item["certified_fresh"]
        if fields:
            result[source] = fields
    if not result:
        raise ValueError("No rating providers returned")
    return result


def fetch_reeldb(imdb_id, api_key):
    url = ("https://api.reeldb.io/v1/title/" + imdb_id + "/ratings?"
           + urlencode({"apikey": api_key}))
    request = Request(url, headers={"Accept": "application/json",
                      "User-Agent": "radarr-festival-list/audience-calibration"})
    with urlopen(request, timeout=30) as response:
        return safe_ratings(json.load(response))


def collect_reeldb(root, api_key, max_requests=400, interval=1.6,
                   fetch=fetch_reeldb, sleep=time.sleep, only_ids=None):
    inputs = load_inputs(root)
    movies = sorted(universe(inputs), key=lambda r: r["imdb_id"])
    payload = copy.deepcopy(inputs[str(es.AUDIENCE)])
    ratings = payload.setdefault("ratings", {})
    unavailable = payload.setdefault("unavailable", {})
    pending = [m for m in movies if m["imdb_id"] not in unavailable
               and any(not valid_provider(
                   (ratings.get(m["imdb_id"], {}).get("reeldb") or {}).get(src), src)
                   for src in ("imdb", "letterboxd"))]
    pending_universe = len(pending)
    if only_ids is not None:
        pending = [m for m in pending if m["imdb_id"] in only_ids]
    report = {"candidate_count": len(movies), "pending_before": len(pending),
              "pending_universe_before": pending_universe,
              "max_requests": max_requests, "attempted": 0, "succeeded": 0,
              "failures": [], "status": "complete", "network_requests": 0,
              "observed_at": datetime.now(timezone.utc).isoformat()}
    if pending and not api_key:
        report["status"] = "missing_REELDB_API_KEY"
    else:
        for movie in pending[:max_requests]:
            iid = movie["imdb_id"]
            report["attempted"] += 1
            report["network_requests"] += 1
            try:
                data = safe_ratings(fetch(iid, api_key))
                item = copy.deepcopy(ratings.get(iid) or {})
                existing = item.get("reeldb") or {}
                for src, value in data.items():
                    if valid_provider(value, src) or not valid_provider(existing.get(src), src):
                        existing[src] = value
                item.update({"title": movie["title"], "year": movie["year"],
                             "reeldb": existing})
                ratings[iid] = item
                report["succeeded"] += 1
            except HTTPError as exc:
                report["failures"].append({"imdb_id": iid, "error": "HTTP " + str(exc.code)})
                if exc.code == 404:
                    unavailable[iid] = {**movie, "error": "HTTP 404"}
                elif exc.code in (401, 403, 429):
                    report["status"] = "stopped_HTTP_" + str(exc.code)
                    break
            except (URLError, TimeoutError, ValueError) as exc:
                report["failures"].append({"imdb_id": iid, "error": type(exc).__name__})
            if report["attempted"] % 25 == 0:
                print(json.dumps({k: report[k] for k in
                                  ("attempted", "succeeded", "status")}), flush=True)
            if report["attempted"] < min(max_requests, len(pending)):
                sleep(interval)
        if len(pending) > max_requests and report["status"] == "complete":
            report["status"] = "request_budget_exhausted"
        payload["ratings_count"] = len(ratings)
        payload["unavailable_count"] = len(unavailable)
        payload["failures"] = report["failures"]
        write_json(root / es.AUDIENCE, payload)
    report["complete_pair_after"] = sum(all(valid_provider(
        (ratings.get(m["imdb_id"], {}).get("reeldb") or {}).get(src), src)
        for src in ("imdb", "letterboxd")) for m in movies)
    report["known_404_in_universe"] = sum(m["imdb_id"] in unavailable for m in movies)
    write_json(root / OUT / "enrichment-status.json", report)
    return report


def imdb_rows(stream, wanted):
    result = {}
    for row in csv.DictReader(stream, delimiter="\t"):
        iid = row.get("tconst")
        if iid not in wanted:
            continue
        try:
            item = {"rating": float(row["averageRating"]),
                    "votes": int(row["numVotes"])}
        except (KeyError, TypeError, ValueError):
            continue
        if valid_provider(item, "imdb"):
            result[iid] = item
    return result


def collect_imdb(root):
    inputs = load_inputs(root)
    movies = universe(inputs)
    ratings = inputs[str(es.AUDIENCE)].get("ratings") or {}
    wanted = {m["imdb_id"] for m in movies if not valid_provider(
        (ratings.get(m["imdb_id"], {}).get("reeldb") or {}).get("imdb"), "imdb")}
    payload = {"source_url": IMDB_URL, "purpose": "Missing IMDb enrichment only",
               "requested_ids": sorted(wanted), "ratings": {},
               "observed_at": datetime.now(timezone.utc).isoformat(),
               "status": "complete", "network_requests": 0}
    if wanted:
        payload["network_requests"] = 1
        try:
            request = Request(IMDB_URL, headers={
                "User-Agent": "radarr-festival-list/audience-calibration"})
            with urlopen(request, timeout=60) as response:
                compressed = response.read()
            payload["download_sha256"] = hashlib.sha256(compressed).hexdigest()
            with gzip.open(io.BytesIO(compressed), "rt", encoding="utf-8") as stream:
                payload["ratings"] = imdb_rows(stream, wanted)
        except HTTPError as exc:
            payload["status"] = "HTTP_" + str(exc.code)
        except (URLError, TimeoutError, OSError, EOFError) as exc:
            payload["status"] = type(exc).__name__
    payload["unavailable_ids"] = sorted(wanted - set(payload["ratings"]))
    write_json(root / OUT / "inputs/imdb-fallback.json", payload)
    return {k: v for k, v in payload.items() if k not in ("ratings", "requested_ids")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--reeldb", action="store_true")
    parser.add_argument("--imdb", action="store_true")
    parser.add_argument("--max-requests", type=int, default=400)
    parser.add_argument("--only-id", action="append", default=None)
    args = parser.parse_args()
    if not (args.reeldb or args.imdb):
        parser.error("Choose --reeldb and/or --imdb")
    if not 0 <= args.max_requests <= 400:
        parser.error("Request budget must be between 0 and 400")
    if args.reeldb:
        print(json.dumps(collect_reeldb(args.root,
                         os.environ.get("REELDB_API_KEY", ""),
                         args.max_requests, only_ids=set(args.only_id) if args.only_id else None)), flush=True)
    if args.imdb:
        print(json.dumps(collect_imdb(args.root)), flush=True)


if __name__ == "__main__":
    main()
