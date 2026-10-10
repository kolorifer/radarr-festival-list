import json
import sys
from pathlib import Path

import requests

# Add the next annual IMDb Editors list ID here when it appears.
LISTS = {
    "2026": "ls4179043772",
}

OUTPUT = Path("festival.json")
GRAPHQL_URL = "https://caching.graphql.imdb.com/"
PERSISTED_QUERY_HASH = "e3aac5739487b9f7f1398fb345dcef9b5a5baa48b71522fa514e77e41d6502e7"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36",
    "Accept": "application/graphql+json, application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.imdb.com/",
    "Origin": "https://www.imdb.com",
    "x-imdb-client-name": "imdb-web-next-localized",
    "x-imdb-user-language": "en-US",
    "x-imdb-user-country": "US",
}


def request_page(list_id: str, after=None):
    variables = {
        "first": 100,
        "locale": "en-US",
        "lsConst": list_id,
        "sort": {"by": "LIST_ORDER", "order": "ASC"},
    }
    if after:
        variables["after"] = after

    params = {
        "operationName": "TitleListMainPage",
        "variables": json.dumps(variables, separators=(",", ":")),
        "extensions": json.dumps(
            {
                "persistedQuery": {
                    "sha256Hash": PERSISTED_QUERY_HASH,
                    "version": 1,
                }
            },
            separators=(",", ":"),
        ),
    }
    response = requests.get(GRAPHQL_URL, params=params, headers=HEADERS, timeout=30)
    response.raise_for_status()
    data = response.json()
    if data.get("errors"):
        raise RuntimeError(f"IMDb GraphQL error: {data['errors']}")
    return data


def fetch_list(list_id: str):
    movies = []
    seen = set()
    after = None

    while True:
        data = request_page(list_id, after)
        search = data["data"]["list"]["titleListItemSearch"]

        for edge in search.get("edges") or []:
            item = edge.get("listItem") or {}
            imdb_id = item.get("id")
            if not imdb_id or imdb_id in seen:
                continue

            # Radarr resolves the item by IMDb ID. A real title is included when
            # IMDb exposes it in this response; otherwise the ID is a safe label.
            title = imdb_id
            title_text = item.get("titleText")
            if isinstance(title_text, dict) and title_text.get("text"):
                title = title_text["text"]

            seen.add(imdb_id)
            movies.append({"title": title, "imdb_id": imdb_id})

        page_info = search.get("pageInfo") or {}
        if not page_info.get("hasNextPage"):
            break
        after = page_info.get("endCursor")
        if not after:
            raise RuntimeError("IMDb indicated another page but returned no cursor")

    return movies


def main():
    all_movies = []
    seen = set()

    for year, list_id in LISTS.items():
        movies = fetch_list(list_id)
        if not movies:
            raise RuntimeError(f"No movies found for {year}: {list_id}")
        print(f"{year}: found {len(movies)} movies")

        for movie in movies:
            if movie["imdb_id"] in seen:
                continue
            seen.add(movie["imdb_id"])
            all_movies.append(movie)

    if not all_movies:
        raise RuntimeError("No movies found; refusing to overwrite festival.json")

    OUTPUT.write_text(
        json.dumps(all_movies, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(all_movies)} movies to {OUTPUT}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
