"""Augment the Phase-B evidence snapshot with additional award families.

This layer intentionally stays separate from the original source builder. It adds:
- European Film Awards Best Film to European recognition.
- Gotham Best Feature to independent cinema.
- NSFC, NYFCC and LAFCA Best Film winners to critics consensus.
- Critics Choice Best Picture from a reproducible static snapshot of the official
  archive, as modest corroboration inside the same critics family.

All families remain capped at 100. Critics consensus requires agreement across
multiple sources; Critics Choice is deliberately weaker than the three critics-
group wins and is not a separate 100-point family.
"""

import json
import re
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote

import requests
import film_identity as fi
from bs4 import BeautifulSoup

import evidence_sources as es

SNAPSHOT = Path("sources/evidence-families.json")
BACKCATALOG = Path("backcatalog-details.json")
CRITICS_CHOICE_SOURCE = Path("sources/critics-choice-best-picture.json")
MAX_FILM_YEAR = 2025

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
    "critics_choice_best_picture": {
        "url": "https://www.criticschoice.com/critics-choice-awards-archives/",
        "static_path": str(CRITICS_CHOICE_SOURCE),
        "family": "critics_groups_consensus",
        "winner_points": 25,
        "nominee_points": 8,
        "label": "Critics Choice Best Picture",
    },
}


def clean_text(value):
    text = re.sub(r"\[[^\]]*\]", "", str(value or ""))
    text = text.replace("≈", "").replace("±", "")
    return re.sub(r"\s+", " ", text).strip()


def extract_title(cell):
    if cell is None:
        return None
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


def canonical_ids():
    try:
        data = json.loads(BACKCATALOG.read_text())
    except (OSError, json.JSONDecodeError):
        return set()
    return {x.get("imdb_id") for x in data.get("candidates", []) if x.get("imdb_id")}


def local_lookup(title, year, catalog, preferred_ids):
    """Resolve a unique local title/year, preferring the canonical TSPDT ID."""
    verified = fi.verified_award(title, year) or fi.verified_identity(title, year)
    if verified and verified["imdb_id"] in catalog:
        return verified["imdb_id"]
    key = es.norm(title)
    hits = []
    for iid, item in catalog.items():
        if not item.get("title") or es.norm(item["title"]) != key:
            continue
        item_year = item.get("year")
        if item_year and abs(int(item_year) - int(year)) <= 1:
            hits.append((iid, item))
    if len(hits) == 1:
        return hits[0][0]
    preferred = [iid for iid, _ in hits if iid in preferred_ids]
    return preferred[0] if len(preferred) == 1 else None


def strict_imdb_lookup(title, year):
    """Resolve an exact movie suggestion and reject TV/short-form lookalikes."""
    verified = fi.verified_award(title, year) or fi.verified_identity(title, year)
    if verified:
        return verified["imdb_id"], verified["title"], verified["year"]
    try:
        data = requests.get(
            "https://v2.sg.media-imdb.com/suggestion/x/" + quote(title) + ".json",
            headers=es.UA,
            timeout=20,
        ).json()
    except Exception:
        return None

    candidates = []
    for item in data.get("d", []):
        iid = item.get("id", "")
        iy = item.get("y")
        it = item.get("l", "")
        if not iid.startswith("tt") or not isinstance(iy, int):
            continue
        if not (es.MIN_YEAR <= iy <= MAX_FILM_YEAR):
            continue
        if abs(iy - int(year)) > 1 or es.norm(it) != es.norm(title):
            continue
        kind = " ".join(str(item.get(k) or "").casefold() for k in ("q", "qid"))
        blocked = ("tv series", "tv mini", "episode", "podcast", "video game", "music video", "short")
        if any(token in kind for token in blocked):
            continue
        candidates.append((abs(iy - int(year)), iid, it, iy))

    if not candidates:
        return None
    candidates.sort()
    distance = candidates[0][0]
    best = [x for x in candidates if x[0] == distance]
    if len(best) != 1:
        return None
    _, iid, resolved_title, resolved_year = best[0]
    return iid, resolved_title, resolved_year


def resolve_rows(rows, catalog, preferred_ids=None):
    preferred_ids = preferred_ids or set()
    resolved = []
    unresolved = []
    for row in rows:
        iid = local_lookup(row["title"], row["year"], catalog, preferred_ids)
        title = row["title"]
        year = row["year"]
        if iid:
            local = catalog.get(iid, {})
            title = local.get("title") or title
            year = local.get("year") or year
        else:
            hit = strict_imdb_lookup(title, year)
            if hit:
                iid, title, year = hit
                catalog.setdefault(iid, {"imdb_id": iid, "title": title, "year": year})
        if iid and es.MIN_YEAR <= int(year) <= MAX_FILM_YEAR:
            resolved.append({**row, "imdb_id": iid, "resolved_title": title, "resolved_year": year})
        else:
            unresolved.append(row)
    return resolved, unresolved


def load_static_rows(path):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = payload.get("films") or []
    unresolved = payload.get("unresolved") or []
    return rows, unresolved, payload


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
    preferred_ids = canonical_ids()

    resolved_by_source = {}
    unresolved = {}
    static_metadata = {}
    for key, spec in EXTRA_SOURCES.items():
        if spec.get("static_path"):
            resolved, missing, metadata = load_static_rows(spec["static_path"])
            resolved_by_source[key] = resolved
            unresolved[key] = missing
            static_metadata[key] = {
                "records_parsed": metadata.get("records_parsed"),
                "resolved": metadata.get("resolved"),
                "pages_discovered": metadata.get("pages_discovered"),
            }
            continue

        html = es.get_text(spec["url"])
        rows = parse_wikipedia_award_rows(html, winners_only=spec["winners_only"])
        resolved, missing = resolve_rows(rows, catalog, preferred_ids)
        resolved_by_source[key] = resolved
        unresolved[key] = missing

    merge_contributions(snapshot, resolved_by_source)
    snapshot["extra_award_sources"] = {
        key: {
            "url": spec["url"],
            "static_path": spec.get("static_path"),
            "family": spec["family"],
            "winner_points": spec["winner_points"],
            "nominee_points": spec["nominee_points"],
            "resolved": len(resolved_by_source[key]),
            "unresolved": len(unresolved[key]),
            **(static_metadata.get(key) or {}),
        }
        for key, spec in EXTRA_SOURCES.items()
    }
    snapshot["award_family_policy"] = {
        "us_institutional": "Academy + Golden Globes, capped at 100",
        "european_recognition": "BAFTA + Cannes + Berlin + Venice + European Film Awards, capped at 100",
        "independent_cinema": "Sundance + Film Independent Spirit + Gotham, capped at 100",
        "critics_groups_consensus": (
            "NSFC + NYFCC + LAFCA Best Film wins (35 each) plus Critics Choice Best Picture "
            "winner/nominee corroboration (25/8); family capped at 100"
        ),
    }
    snapshot["unresolved_extra_awards"] = unresolved
    SNAPSHOT.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({
        "extra_sources": {k: len(v) for k, v in resolved_by_source.items()},
        "extra_unresolved": {k: len(v) for k, v in unresolved.items()},
    }))


if __name__ == "__main__":
    augment_snapshot()
