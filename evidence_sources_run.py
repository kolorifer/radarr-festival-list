"""Runtime corrections layered over the evidence source builder.

This wrapper preserves true Sight & Sound published positions when pre-2000 films
are filtered and feeds the complete 2025 NYT top-100 CSV into the generic ranked
source resolver.
"""
import csv
import io
import re

import evidence_sources as es

NYT_URL = "https://gist.githubusercontent.com/mvark/2273ae29bfc5d7033016df4b6cebbc6d/raw/b088026b06661cadfcd5386dd13507309140bfb3/NYT-100-Best-Movies.csv"
_ORIGINAL_RANKED_PARSER = es.parse_wikipedia_ranked


def parse_sight_sound(text):
    rows = []
    published_position = 0
    for line in text.splitlines():
        m = re.match(r"^\s*\d+\s+#\s+(.+?)\s+\((\d{4})\)", line)
        if not m:
            continue
        published_position += 1
        year = int(m.group(2))
        if year < es.MIN_YEAR:
            continue
        rows.append({"rank": published_position, "title": m.group(1).strip(), "year": year})
    return rows


def parse_ranked(text):
    first = text.splitlines()[0].casefold() if text.splitlines() else ""
    if "moviename" not in first or "director" not in first:
        return _ORIGINAL_RANKED_PARSER(text)
    rows = []
    for row in csv.DictReader(io.StringIO(text)):
        try:
            rank = int(str(row.get("rating", "")).strip())
            year = int(str(row.get("year", "")).strip())
        except ValueError:
            continue
        title = str(row.get("moviename", "")).strip()
        if title and year >= es.MIN_YEAR:
            rows.append({"rank": rank, "title": title, "year": year})
    return sorted(rows, key=lambda x: x["rank"])


def main():
    es.NYT_URL = NYT_URL
    es.parse_sight_sound = parse_sight_sound
    es.parse_wikipedia_ranked = parse_ranked
    es.main()


if __name__ == "__main__":
    main()
