import json
import re
import sys
from pathlib import Path

import requests

# Add the next annual IMDb Editors list here when it appears.
LISTS = {
    "2026": "https://www.imdb.com/list/ls4179043772/",
}

OUTPUT = Path("festival.json")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


def extract_movies(html: str):
    """Extract IMDb title IDs and names from a public IMDb list page."""
    movies = []
    seen = set()

    # Current IMDb pages expose title IDs in embedded JSON. Look for titleText
    # close to each ID; this is less dependent on visual page markup.
    pattern = re.compile(
        r'"id":"(tt\d+)".{0,2000}?"titleText":\{"text":"((?:\\.|[^"\\])*)"',
        re.DOTALL,
    )
    for imdb_id, escaped_title in pattern.findall(html):
        if imdb_id in seen:
            continue
        try:
            title = json.loads(f'"{escaped_title}"')
        except json.JSONDecodeError:
            title = escaped_title
        seen.add(imdb_id)
        movies.append({"title": title, "imdb_id": imdb_id})

    # Fallback for older/server-rendered IMDb markup.
    if not movies:
        link_pattern = re.compile(
            r'href="/title/(tt\d+)/[^\"]*"[^>]*>([^<]+)</a>', re.DOTALL
        )
        for imdb_id, title in link_pattern.findall(html):
            title = re.sub(r"\s+", " ", title).strip()
            if imdb_id in seen or not title:
                continue
            seen.add(imdb_id)
            movies.append({"title": title, "imdb_id": imdb_id})

    return movies


def fetch_list(url: str):
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return extract_movies(response.text)


def main():
    all_movies = []
    seen = set()

    for year, url in LISTS.items():
        movies = fetch_list(url)
        if not movies:
            raise RuntimeError(f"No movies found for {year}: {url}")
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
