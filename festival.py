import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

import requests

# Add the next annual IMDb Editors list ID here when it appears.
LISTS = {
    "2026": "ls4179043772",
}

OUTPUT = Path("festival.json")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36",
    "Accept": "text/html",
    "Accept-Language": "en-US,en;q=0.9",
}


class PageDataParser(HTMLParser):
    """Read only IMDb's embedded page data, never unrelated title links."""

    def __init__(self):
        super().__init__()
        self.capture = False
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag == "script" and dict(attrs).get("id") == "__NEXT_DATA__":
            self.capture = True

    def handle_data(self, data):
        if self.capture:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag == "script":
            self.capture = False


def find_title_search(value):
    if isinstance(value, dict):
        search = value.get("titleListItemSearch")
        if isinstance(search, dict) and isinstance(search.get("edges"), list):
            return search
        for child in value.values():
            found = find_title_search(child)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = find_title_search(child)
            if found is not None:
                return found
    return None


def parse_page(html):
    parser = PageDataParser()
    parser.feed(html)
    if not parser.parts:
        raise RuntimeError("IMDb returned no embedded page data (possibly a challenge page)")
    data = json.loads("".join(parser.parts))
    search = find_title_search(data.get("props", {}).get("pageProps", {}))
    if search is None:
        raise RuntimeError("IMDb page data contains no title list; markup may have changed")

    # Never publish only the first page of a larger list. This also protects
    # against unexpected changes to IMDb's initial page size.
    page_info = search.get("pageInfo") or {}
    if page_info.get("hasNextPage") is not False:
        raise RuntimeError(
            "IMDb did not provide a complete list in its public page data; "
            "refusing to publish a partial feed"
        )

    movies = []
    seen = set()
    for edge in search["edges"]:
        item = edge.get("listItem") or {}
        imdb_id = item.get("id", "")
        if not re.fullmatch(r"tt[0-9]+", imdb_id):
            raise RuntimeError("IMDb list entry has no valid title ID")
        if imdb_id in seen:
            continue
        seen.add(imdb_id)
        title = (item.get("titleText") or {}).get("text") or imdb_id
        movies.append({"title": title, "imdb_id": imdb_id})

    total = search.get("total")
    if isinstance(total, int) and total != len(search["edges"]):
        raise RuntimeError("IMDb list count does not match the returned entries")
    return movies


def fetch_list(list_id: str):
    response = requests.get(
        f"https://www.imdb.com/list/{list_id}/",
        headers=HEADERS,
        timeout=30,
    )
    response.raise_for_status()
    return parse_page(response.text)


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
