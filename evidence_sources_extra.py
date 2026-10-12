"""Augment the Phase-B evidence snapshot with additional award families.

This layer intentionally stays separate from the original source builder. It adds:
- European Film Awards Best Film to European recognition.
- Gotham Best Feature to independent cinema.
- NSFC, NYFCC and LAFCA Best Film winners as a separate critics consensus family.

All families remain capped at 100. Critics consensus requires agreement across
multiple groups: each Best Film win contributes 35 points, so one group alone
cannot dominate the score.
"""

import json
import re
from collections import defaultdict
from pathlib import Path

import requests
from bs4 import BeautifulSoup

import evidence_sources as es

SNAPSHOT = Path("sources/evidence-families.json")

EXTRA_SOURCES = {
    "efa_best_film": {
        "url": "https://en.wikipedia.org/wiki/European_Film_Award_for_Best_Film",
        "family": "european_recognition",
        "winner_points": 40,
        "nominee_points": 12,
        "winners_only": False,
        "label": "European Film Awards Best Film",
    },
    "gotham_best_feature": {
        "url": "https://en.wikipedia.org/wiki/Gotham_Independent_Film_Award_for_Best_Feature",
        "family": "independent_cinema",
        "winner_points": 35,
        "nominee_points": 10,
        "winners_only": False,
        "label": "Gotham Best Feature",
    },
    "nsfc_best_picture": {
        "url": "https://en.wikipedia.org/wiki/National_Society_of_Film_Critics_Award_for_Best_Picture",
        "family": "critics_groups_consensus",
        "winner_points": 35,
        "nominee_points": 0,
        "winners_only": True,
        "label": "NSFC Best Picture",
    },
    "nyfcc_best_film": {
        "url": "https://en.wikipedia.org/wiki/New_York_Film_Critics_Circle_Award_for_Best_Film",
        "family": "critics_groups_consensus",
        "winner_points": 35,
        "nominee_points": 0,
        "winners_only": True,
        "label": "NYFCC Best Film",
    },
    "lafca_best_film": {
        "url": "https://en.wikipedia.org/wiki/Los_Angeles_Film_Critics_Association_Award_for_Best_Film",
        "family": "critics_groups_consensus",
        "winner_points": 35,
        "nominee_points": 0,
        "winners_only": True,
        "label": "LAFCA Best Film",
    },
}


def clean_text(value):
    text = re.sub(r"\[[^\]]*\]", "", str(value or ""))
    text = text.replace("≈", "").replace("±", "")
    return re.sub(r"\s+", " ", text).strip()


def extract_title(cell):
    if cell is None:
        return None
    # Film-title cells normally link the film before any ancillary references.
    for a in cell.find_all("a"):
        title = clean_text(a.get_text(" ", strip=True))
        if title:
            return title
    return clean_text(cell.get_text(" ", strip=True)) or None


def parse_wikipedia_award_rows(html_text, winners_only=False):
    """Parse year/title rows from Wikipedia award tables.

    On winners-and-nominees pages, the first film under each year is the winner
    and subsequent rowspan continuations are nominees. Winners-only pages mark
    every film row as a winner, including ties that share a year.
    """
    soup = BeautifulSoup(html_text, "html.parser")
    out = []
    seen = set()

    for table in soup.select("table.wikitable"):
        current_year = None
        for tr in table.find_all("tr"):
            cells = tr.find_all(["th", "td"], recursive=False)
            if not cells:
                continue
            first = clean_text(cells[0].get_text(" ", strip=True))
            m = re.match(r"^(20\d{2})(?:\s|\(|$)", first)
            starts_year = bool(m)
            if starts_year:
                current_year = int(m.group(1))
                title_cell = cells[1] if len(cells) > 1 else None
            elif current_year is not None:
                title_cell = cells[0]
            else:
                continue

            if current_year < es.MIN_YEAR:
                continue
            title = extract_title(title_cell)
            if not title or title.casefold() in {"film", "winner", "english title", "title"}:
                continue

            row = {
                "year": current_year,
                "title": title,
                "winner": True if winners_only else starts_year,
            }
            key = (row["year"], es.norm(row["title"]), row["winner"])
            if key not in seen:
                seen.add(key)
                out.append(row)
    return out


def resolve_rows(rows, catalog):
    resolved = []
    unresolved = []
    for row in rows:
        iid = es.local_match(row["title"], row["year"], catalog)
        title = row["title"]
        year = row["year"]
        if not iid:
            hit = es.imdb_lookup(title, year)
            if hit:
                iid, title, year = hit
                catalog.setdefault(iid, {"imdb_id": iid, "title": title, "year": year})
        if iid:
            resolved.append({**row, "imdb_id": iid, "resolved_title": title, "resolved_year": year})
        else:
            unresolved.append(row)
    return resolved, unresolved


def add_contribution(contrib, iid, family, source_key, points, evidence):
    if points <= 0:
        return
    slot = contrib[iid][family]
    old = slot.get(source_key)
    if old is None or points > old[0]:
        slot[source_key] = (float(points), evidence)


def merge_contributions(snapshot, resolved_by_source):
    """Merge extra evidence into an already-built snapshot in place."""
    films = snapshot.setdefault("films", {})
    contrib = defaultdict(lambda: defaultdict(dict))

    for source_key, rows in resolved_by_source.items():
        spec = EXTRA_SOURCES[source_key]
        for row in rows:
            points = spec["winner_points"] if row["winner"] else spec["nominee_points"]
            status = "winner" if row["winner"] else "nominee"
            add_contribution(
                contrib,
                row["imdb_id"],
                spec["family"],
                source_key,
                points,
                f"{spec['label']} ({status})",
            )
            films.setdefault(
                row["imdb_id"],
                {"title": row.get("resolved_title") or row["title"], "year": row.get("resolved_year") or row["year"]},
            )

    for iid, families in contrib.items():
        film = films.setdefault(iid, {})
        scores = film.setdefault("family_scores", {})
        evidence = film.setdefault("family_evidence", {})
        for family, components in families.items():
            extra = sum(v[0] for v in components.values())
            base = float(scores.get(family) or 0.0)
            scores[family] = round(min(100.0, base + extra), 2)
            existing = list(evidence.get(family) or [])
            for _, item in components.values():
                if item not in existing:
                    existing.append(item)
            evidence[family] = existing


def augment_snapshot():
    snapshot = json.loads(SNAPSHOT.read_text())
    catalog = es.build_catalog()
    for iid, row in (snapshot.get("films") or {}).items():
        catalog.setdefault(iid, {"imdb_id": iid, "title": row.get("title"), "year": row.get("year")})

    resolved_by_source = {}
    unresolved = {}
    for key, spec in EXTRA_SOURCES.items():
        html = es.get_text(spec["url"])
        rows = parse_wikipedia_award_rows(html, winners_only=spec["winners_only"])
        resolved, missing = resolve_rows(rows, catalog)
        resolved_by_source[key] = resolved
        unresolved[key] = missing

    merge_contributions(snapshot, resolved_by_source)
    snapshot["extra_award_sources"] = {
        key: {
            "url": spec["url"],
            "family": spec["family"],
            "winner_points": spec["winner_points"],
            "nominee_points": spec["nominee_points"],
            "resolved": len(resolved_by_source[key]),
            "unresolved": len(unresolved[key]),
        }
        for key, spec in EXTRA_SOURCES.items()
    }
    snapshot["award_family_policy"] = {
        "us_institutional": "Academy + Golden Globes, capped at 100",
        "european_recognition": "BAFTA + Cannes + Berlin + Venice + European Film Awards, capped at 100",
        "independent_cinema": "Sundance + Film Independent Spirit + Gotham, capped at 100",
        "critics_groups_consensus": "NSFC + NYFCC + LAFCA Best Film wins; 35 points per group, capped at 100",
    }
    snapshot["unresolved_extra_awards"] = unresolved
    SNAPSHOT.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({
        "extra_sources": {k: len(v) for k, v in resolved_by_source.items()},
        "extra_unresolved": {k: len(v) for k, v in unresolved.items()},
    }))


if __name__ == "__main__":
    augment_snapshot()
