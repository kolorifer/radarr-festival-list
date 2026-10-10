import json
import re
import sys
from pathlib import Path
from urllib.request import Request, urlopen

# Add the next annual IMDb Editors list ID here when it appears.
LISTS = {"2026": "ls4179043772"}
OUTPUT = Path("festival.json")
GRAPHQL_URL = "https://api.graphql.imdb.com/"
# IMDb's public website query, verified against the festival list.
# If IMDb retires it, update from Kometa-Team/IMDb-Hash's LIST_HASH.
LIST_QUERY_HASH = "dc98c1b896ffcb97e619b888d27721ff40fea6985fd022bca920615ed744ee0b"


def fetch_page(list_id, after=None, page_size=100):
    payload = {
        "operationName": "TitleListMainPage",
        "variables": {
            "lsConst": list_id, "first": page_size, "after": after,
            "locale": "en-US", "isInPace": False,
            "sort": {"by": "LIST_ORDER", "order": "ASC"},
        },
        "extensions": {"persistedQuery": {"version": 1, "sha256Hash": LIST_QUERY_HASH}},
    }
    request = Request(
        GRAPHQL_URL, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-imdb-client-name": "imdb-web-next-localized"},
    )
    with urlopen(request, timeout=30) as response:
        data = json.load(response)
    if data.get("errors"):
        raise RuntimeError("IMDb GraphQL: " + "; ".join(e.get("message", "unknown error") for e in data["errors"]))
    result = (data.get("data") or {}).get("list")
    if not result or not isinstance(result.get("titleListItemSearch"), dict):
        raise RuntimeError(f"IMDb returned no public title list for {list_id}")
    return result["titleListItemSearch"]


def fetch_list(list_id, page_size=100):
    movies = []
    seen = set()
    cursors = set()
    after = None
    expected_total = None
    while True:
        search = fetch_page(list_id, after, page_size)
        total = search.get("total")
        if type(total) is not int or total < 1:
            raise RuntimeError("IMDb returned an empty or invalid list count")
        if expected_total is None:
            expected_total = total
        elif total != expected_total:
            raise RuntimeError("IMDb list changed during pagination; retry later")
        edges = search.get("edges")
        if not isinstance(edges, list) or not edges:
            raise RuntimeError("IMDb returned an empty or invalid page")
        for edge in edges:
            item = edge.get("listItem") or {}
            imdb_id = item.get("id", "")
            title = (item.get("titleText") or {}).get("text")
            if not isinstance(imdb_id, str) or not re.fullmatch(r"tt[0-9]+", imdb_id):
                raise RuntimeError("IMDb list entry has no valid title ID")
            if not isinstance(title, str) or not title.strip():
                raise RuntimeError("IMDb list entry has no title")
            if imdb_id in seen:
                raise RuntimeError("IMDb returned a duplicate title; refusing a partial feed")
            seen.add(imdb_id)
            movies.append({"title": title, "imdb_id": imdb_id})
        info = search.get("pageInfo") or {}
        if info.get("hasNextPage") is False:
            break
        if info.get("hasNextPage") is not True or len(movies) >= expected_total:
            raise RuntimeError("IMDb returned inconsistent pagination")
        after = info.get("endCursor")
        if not isinstance(after, str) or not after or after in cursors:
            raise RuntimeError("IMDb returned a missing or repeated pagination cursor")
        cursors.add(after)
    if len(movies) != expected_total:
        raise RuntimeError("IMDb list count does not match the returned entries")
    return movies


def main():
    all_movies = []
    seen = set()
    for year, list_id in LISTS.items():
        movies = fetch_list(list_id)
        print(f"{year}: found {len(movies)} movies")
        for movie in movies:
            if movie["imdb_id"] not in seen:
                seen.add(movie["imdb_id"])
                all_movies.append(movie)
    if not all_movies:
        raise RuntimeError("No movies found; refusing to overwrite festival.json")
    # Replace only after every configured list has been fetched and validated.
    temporary = OUTPUT.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(all_movies, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(OUTPUT)
    print(f"Wrote {len(all_movies)} movies to {OUTPUT}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
