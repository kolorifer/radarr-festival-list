"""Runtime corrections layered over the evidence source builder.

Kept separate so the research pipeline can be corrected without rewriting the
larger source-family policy module. This preserves true Sight & Sound positions
when pre-2000 films are filtered and uses the canonical 2025 NYT Wikipedia page.
"""
import re

import evidence_sources as es

NYT_URL = "https://en.wikipedia.org/wiki/NYT%27s_100_Best_Movies_of_the_21st_Century_%28June_2025%29"


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


def main():
    es.NYT_URL = NYT_URL
    es.parse_sight_sound = parse_sight_sound
    es.main()


if __name__ == "__main__":
    main()
