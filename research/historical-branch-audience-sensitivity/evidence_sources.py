"""Build research-only evidence families for Phase B scoring.

The output is a compact, reproducible snapshot keyed by IMDb id. It deliberately
keeps source families independent: ranked canon polls, US institutions, European
recognition, and independent-cinema recognition. Production Radarr feeds and the
frozen Phase-4 qualification routes are untouched.
"""

import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

BACKCATALOG = Path("backcatalog-details.json")
INSTITUTIONAL = Path("sources/phase-b-institutional.json")
QUALIFIERS = Path("simulation-qualifiers.json")
OUTPUT = Path("sources/evidence-families.json")
MIN_YEAR = 2000
UA = {"User-Agent": "Mozilla/5.0 (radarr-festival-list research; contact via GitHub)"}

BBC_URL = "https://en.wikipedia.org/wiki/BBC%27s_100_Greatest_Films_of_the_21st_Century"
NYT_URL = "https://en.wikipedia.org/wiki/NYT%27s_100_Best_Movies_of_the_21st_Century"
SIGHT_SOUND_URL = "https://raw.githubusercontent.com/servindigitalart/prisma-site/main/pipeline/sources/sight_and_sound_2022.txt"
KOMETA_BASE = "https://raw.githubusercontent.com/Kometa-Team/IMDb-Awards/master/events"
EVENTS = {
    "academy": "ev0000003.yml",
    "berlin": "ev0000091.yml",
    "bafta": "ev0000123.yml",
    "cannes": "ev0000147.yml",
    "golden_globes": "ev0000292.yml",
    "spirit": "ev0000349.yml",
    "sundance": "ev0000631.yml",
    "venice": "ev0000681.yml",
}


def get_text(url):
    r = requests.get(url, headers=UA, timeout=45)
    r.raise_for_status()
    return r.text


def norm(value):
    text = unicodedata.normalize("NFKD", str(value).casefold())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "", text)


def build_catalog():
    back = json.loads(BACKCATALOG.read_text())
    inst = json.loads(INSTITUTIONAL.read_text())
    quals = json.loads(QUALIFIERS.read_text())
    out = {}
    for group in (back.get("candidates", []), inst.get("films", []), quals):
        for row in group:
            iid = row.get("imdb_id")
            if not iid:
                continue
            current = out.setdefault(iid, {})
            current["imdb_id"] = iid
            current["title"] = current.get("title") or row.get("title") or row.get("resolved_title")
            current["year"] = current.get("year") or row.get("year") or row.get("resolved_year")
    return out


def local_match(title, year, catalog):
    key = norm(title)
    hits = []
    for iid, row in catalog.items():
        if not row.get("title") or norm(row["title"]) != key:
            continue
        row_year = row.get("year")
        if year and row_year and abs(int(row_year) - int(year)) > 1:
            continue
        hits.append(iid)
    return hits[0] if len(hits) == 1 else None


def imdb_lookup(title, year):
    try:
        data = requests.get(
            "https://v2.sg.media-imdb.com/suggestion/x/" + quote(title) + ".json",
            headers=UA,
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
        if year and abs(iy - int(year)) > 1:
            continue
        candidates.append(((0 if norm(it) == norm(title) else 1, abs(iy - int(year or iy))), iid, it, iy))
    if not candidates:
        return None
    _, iid, resolved_title, resolved_year = min(candidates)
    return iid, resolved_title, resolved_year


def parse_wikipedia_ranked(html_text):
    """Return the largest movie-like table as ordered rank/title/year rows."""
    soup = BeautifulSoup(html_text, "html.parser")
    choices = []
    for table in soup.find_all("table"):
        rows = []
        sequence = 0
        for tr in table.find_all("tr"):
            cells = tr.find_all(["td", "th"], recursive=False)
            if not cells or not tr.find_all("td", recursive=False):
                continue
            texts = [c.get_text(" ", strip=True) for c in cells]
            if not any(texts):
                continue
            m_rank = re.match(r"^\s*(\d{1,3})\b", texts[0])
            title_index = 1 if m_rank and len(cells) > 1 else 0
            title_cell = cells[title_index]
            title = title_cell.get_text(" ", strip=True)
            link = title_cell.find("a")
            if link and link.get_text(strip=True):
                title = link.get_text(" ", strip=True)
            year = None
            for text in reversed(texts):
                found = re.search(r"\b(20\d{2})\b", text)
                if found:
                    year = int(found.group(1))
                    break
            if not year or year < MIN_YEAR:
                continue
            sequence += 1
            rank = int(m_rank.group(1)) if m_rank else sequence
            rows.append({"rank": rank, "title": title, "year": year})
        if len(rows) >= 20:
            choices.append(rows)
    return max(choices, key=len) if choices else []


def parse_sight_sound(text):
    rows = []
    for line in text.splitlines():
        m = re.match(r"^\s*\d+\s+#\s+(.+?)\s+\((\d{4})\)", line)
        if not m:
            continue
        year = int(m.group(2))
        if year < MIN_YEAR:
            continue
        rows.append({"rank": len(rows) + 1, "title": m.group(1).strip(), "year": year})
    return rows


def resolve_ranked(rows, catalog):
    resolved = []
    unresolved = []
    for row in rows:
        iid = local_match(row["title"], row["year"], catalog)
        title, year = row["title"], row["year"]
        if not iid:
            hit = imdb_lookup(title, year)
            if hit:
                iid, title, year = hit
                catalog.setdefault(iid, {"imdb_id": iid, "title": title, "year": year})
        if iid:
            resolved.append({**row, "imdb_id": iid})
        else:
            unresolved.append(row)
    return resolved, unresolved


def parse_imdb_event_yaml(text):
    """Parse the small subset of Kometa's generated YAML that we need.

    This avoids adding a YAML runtime dependency. Event files use a stable
    year -> award -> category -> nominee/winner list structure.
    """
    year = None
    award = None
    category = None
    records = []
    for raw in text.splitlines():
        y = re.match(r"^'(\d{4})':", raw)
        if y:
            year = int(y.group(1))
            award = category = None
            continue
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if indent == 2 and stripped.endswith(":"):
            award = stripped[:-1].strip().casefold()
            category = None
            continue
        if indent == 4 and stripped.endswith(":"):
            category = stripped[:-1].strip().casefold()
            continue
        if indent >= 6 and (stripped.startswith("nominee:") or stripped.startswith("winner:")):
            status = "winner" if stripped.startswith("winner:") else "nominee"
            ids = re.findall(r"tt\d+", stripped)
            for iid in ids:
                records.append({"year": year, "award": award or "", "category": category or "", "status": status, "imdb_id": iid})
    return records


def component_store():
    return defaultdict(lambda: defaultdict(dict))


def put_component(store, iid, family, component, points, evidence):
    slot = store[iid][family]
    old = slot.get(component)
    if old is None or points > old[0]:
        slot[component] = (float(points), evidence)


def score_events(event_records):
    store = component_store()

    def award_points(records, venue):
        for r in records:
            iid, award, cat, status = r["imdb_id"], r["award"], r["category"], r["status"]
            win = status == "winner"
            label = f"{venue}: {award} / {cat} ({status})"

            if venue == "Academy":
                if cat in {"best motion picture of the year", "best picture"}:
                    put_component(store, iid, "us_institutional", "academy_best_picture", 100 if win else 65, label)
                elif "international feature" in cat or "foreign language film" in cat:
                    put_component(store, iid, "us_institutional", "academy_international", 70 if win else 35, label)
                elif "animated feature" in cat:
                    put_component(store, iid, "us_institutional", "academy_animated", 60 if win else 30, label)
                elif "documentary feature" in cat:
                    put_component(store, iid, "us_institutional", "academy_documentary", 60 if win else 30, label)

            elif venue == "Golden Globes":
                if cat in {"best motion picture - drama", "best motion picture - musical or comedy"}:
                    put_component(store, iid, "us_institutional", "globe_best_picture", 25 if win else 10, label)
                elif "best motion picture - non-english language" in cat:
                    put_component(store, iid, "us_institutional", "globe_non_english", 15 if win else 5, label)
                elif "best motion picture - animated" in cat:
                    put_component(store, iid, "us_institutional", "globe_animated", 15 if win else 5, label)

            elif venue == "BAFTA":
                if cat == "best film":
                    put_component(store, iid, "european_recognition", "bafta_best_film", 50 if win else 25, label)
                elif "film not in the english language" in cat:
                    put_component(store, iid, "european_recognition", "bafta_non_english", 35 if win else 15, label)

            elif venue == "Cannes":
                if award == "palme d'or" and cat == "palme d'or":
                    put_component(store, iid, "european_recognition", "cannes_main", 70 if win else 10, label)
                elif win and "grand prize" in award:
                    put_component(store, iid, "european_recognition", "cannes_grand_prix", 55, label)
                elif win and award == "jury prize":
                    put_component(store, iid, "european_recognition", "cannes_jury", 40, label)
                elif win and (award == "best director" or cat == "best director"):
                    put_component(store, iid, "european_recognition", "cannes_director", 30, label)

            elif venue == "Berlin":
                if award == "golden berlin bear" and cat == "best film":
                    put_component(store, iid, "european_recognition", "berlin_main", 70 if win else 10, label)
                elif win and award == "silver berlin bear" and cat == "grand jury prize":
                    put_component(store, iid, "european_recognition", "berlin_grand_jury", 55, label)
                elif win and award == "silver berlin bear" and cat == "jury prize":
                    put_component(store, iid, "european_recognition", "berlin_jury", 40, label)
                elif win and award == "silver berlin bear" and cat == "best director":
                    put_component(store, iid, "european_recognition", "berlin_director", 30, label)

            elif venue == "Venice":
                if award == "golden lion" and cat == "best film":
                    put_component(store, iid, "european_recognition", "venice_main", 70 if win else 10, label)
                elif win and award == "silver lion" and cat == "grand jury prize":
                    put_component(store, iid, "european_recognition", "venice_grand_jury", 55, label)
                elif win and award == "special jury prize":
                    put_component(store, iid, "european_recognition", "venice_jury", 40, label)
                elif win and award == "silver lion" and cat == "best director":
                    put_component(store, iid, "european_recognition", "venice_director", 30, label)

            elif venue == "Sundance":
                if award == "grand jury prize":
                    put_component(store, iid, "independent_cinema", "sundance_grand_jury", 60 if win else 8, label)
                elif win and award == "audience award":
                    put_component(store, iid, "independent_cinema", "sundance_audience", 30, label)
                elif win and award == "directing award":
                    put_component(store, iid, "independent_cinema", "sundance_director", 25, label)
                elif win and "special jury award" in award:
                    put_component(store, iid, "independent_cinema", "sundance_special_jury", 15, label)

            elif venue == "Spirit":
                if award == "independent spirit award" and cat == "best feature":
                    put_component(store, iid, "independent_cinema", "spirit_best_feature", 50 if win else 20, label)
                elif award == "independent spirit award" and cat == "best first feature":
                    put_component(store, iid, "independent_cinema", "spirit_first_feature", 30 if win else 10, label)

    venue_map = {
        "academy": "Academy",
        "golden_globes": "Golden Globes",
        "bafta": "BAFTA",
        "cannes": "Cannes",
        "berlin": "Berlin",
        "venice": "Venice",
        "sundance": "Sundance",
        "spirit": "Spirit",
    }
    for key, records in event_records.items():
        award_points(records, venue_map[key])

    out = {}
    for iid, families in store.items():
        family_scores = {}
        family_evidence = {}
        for family, components in families.items():
            total = sum(v[0] for v in components.values())
            if family == "independent_cinema":
                if components.get("sundance_grand_jury", (0,))[0] >= 60 and components.get("sundance_audience", (0,))[0] >= 30:
                    total += 10
                    components["sundance_jury_audience_convergence"] = (10.0, "Sundance: Grand Jury + Audience convergence bonus")
            family_scores[family] = round(min(100.0, total), 2)
            family_evidence[family] = [v[1] for v in components.values()]
        out[iid] = {"family_scores": family_scores, "family_evidence": family_evidence}
    return out


def main():
    catalog = build_catalog()

    ranked_specs = {
        "bbc_21c": (parse_wikipedia_ranked(get_text(BBC_URL)), 100, 2016, BBC_URL),
        "nyt_21c": (parse_wikipedia_ranked(get_text(NYT_URL)), 100, 2025, NYT_URL),
        "sight_sound": (parse_sight_sound(get_text(SIGHT_SOUND_URL)), 100, 2022, SIGHT_SOUND_URL),
    }
    ranked_sources = {}
    all_unresolved = {}
    for key, (rows, depth, eligible_through, url) in ranked_specs.items():
        resolved, unresolved = resolve_ranked(rows, catalog)
        ranked_sources[key] = {
            "published_depth": depth,
            "eligible_through_year": eligible_through,
            "source_url": url,
            "films": resolved,
        }
        all_unresolved[key] = unresolved

    event_records = {}
    for key, filename in EVENTS.items():
        event_records[key] = parse_imdb_event_yaml(get_text(f"{KOMETA_BASE}/{filename}"))
    award_scores = score_events(event_records)

    films = {}
    for iid, row in catalog.items():
        films[iid] = {"title": row.get("title"), "year": row.get("year")}
    for source in ranked_sources.values():
        for row in source["films"]:
            films.setdefault(row["imdb_id"], {"title": row["title"], "year": row["year"]})
    for iid, scored in award_scores.items():
        if iid in films:
            films[iid].update(scored)

    payload = {
        "mode": "evidence-family-snapshot-v1",
        "ranked_sources": ranked_sources,
        "award_family_policy": {
            "us_institutional": "Academy + Golden Globes, capped at 100",
            "european_recognition": "BAFTA + Cannes + Berlin + Venice, capped at 100; EFA can be added later",
            "independent_cinema": "Sundance + Film Independent Spirit, capped at 100; Gotham can be added later",
        },
        "films": films,
        "unresolved_ranked": all_unresolved,
    }
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({
        "films": len(films),
        "ranked": {k: len(v["films"]) for k, v in ranked_sources.items()},
        "unresolved": {k: len(v) for k, v in all_unresolved.items()},
        "award_scored": sum(1 for v in films.values() if v.get("family_scores")),
    }))


if __name__ == "__main__":
    main()
