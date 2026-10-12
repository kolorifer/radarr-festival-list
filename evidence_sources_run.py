"""Runtime corrections layered over the evidence source builder.

This wrapper preserves true Sight & Sound published positions, feeds complete
BBC 2016 and NYT 2025 rankings into the ranked-source resolver, and prevents
parallel/technical Cannes prizes from being mistaken for the main Grand Prix.
"""
import csv
import io
import re

import evidence_sources as es

BBC_URL = "https://pt.wikipedia.org/wiki/Os_100_melhores_filmes_do_s%C3%A9culo_XXI_segundo_a_BBC"
NYT_URL = "https://gist.githubusercontent.com/mvark/2273ae29bfc5d7033016df4b6cebbc6d/raw/b088026b06661cadfcd5386dd13507309140bfb3/NYT-100-Best-Movies.csv"
_ORIGINAL_RANKED_PARSER = es.parse_wikipedia_ranked
_ORIGINAL_PUT_COMPONENT = es.put_component


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


def put_component(store, iid, family, component, points, evidence):
    if component == "cannes_grand_prix":
        text = evidence.casefold()
        valid = (
            "cannes: grand prize of the festival /" in text
            or "cannes: grand prize of the jury /" in text
        )
        if not valid:
            return
    return _ORIGINAL_PUT_COMPONENT(store, iid, family, component, points, evidence)


def main():
    es.BBC_URL = BBC_URL
    es.NYT_URL = NYT_URL
    es.parse_sight_sound = parse_sight_sound
    es.parse_wikipedia_ranked = parse_ranked
    es.put_component = put_component
    es.main()


if __name__ == "__main__":
    main()
