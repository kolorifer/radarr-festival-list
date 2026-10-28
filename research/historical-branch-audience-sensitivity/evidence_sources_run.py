"""Runtime corrections layered over the evidence source builder.

This wrapper feeds complete BBC 2016 and NYT 2025 rankings into the ranked-source
resolver, replaces the old third-party Sight & Sound seed with a static snapshot
of the official BFI 2022 critics' poll top 250, prevents parallel/technical
Cannes prizes from being mistaken for the main Grand Prix, adds audience-
discovered films to the identity catalog so current awards can corroborate them,
and then adds EFA, Gotham and critics-group evidence.
"""
import csv
import io
import json
from pathlib import Path

import evidence_sources as es

BBC_URL = "https://pt.wikipedia.org/wiki/Os_100_melhores_filmes_do_s%C3%A9culo_XXI_segundo_a_BBC"
NYT_URL = "https://gist.githubusercontent.com/mvark/2273ae29bfc5d7033016df4b6cebbc6d/raw/b088026b06661cadfcd5386dd13507309140bfb3/NYT-100-Best-Movies.csv"
DISCOVERY = Path("sources/imdb-audience-discovery.json")
SIGHT_SOUND_SOURCE = Path("sources/sight-sound-2022-top250-modern.json")
SIGHT_SOUND_SENTINEL = "local:official-sight-sound-2022"
SIGHT_SOUND_MATCH_TITLES = {
    "Mulholland Dr.": "Mulholland Drive",
    "The Gleaners and I": "The Gleaners & I",
    "La ciénaga": "The Swamp",
    "West of the Tracks": "Tie Xi Qu: West of the Tracks",
}
_ORIGINAL_RANKED_PARSER = es.parse_wikipedia_ranked
_ORIGINAL_PUT_COMPONENT = es.put_component
_ORIGINAL_BUILD_CATALOG = es.build_catalog
_ORIGINAL_GET_TEXT = es.get_text


def build_catalog_with_discovery():
    catalog = _ORIGINAL_BUILD_CATALOG()
    if not DISCOVERY.exists():
        return catalog
    payload = json.loads(DISCOVERY.read_text(encoding="utf-8"))
    for row in payload.get("films", []):
        iid = row.get("imdb_id")
        if not iid:
            continue
        current = catalog.setdefault(iid, {"imdb_id": iid})
        current["title"] = current.get("title") or row.get("title") or row.get("original_title")
        current["year"] = current.get("year") or row.get("year")
    return catalog


def get_text(url):
    # The active Sight & Sound source is local and official-derived; do not fetch
    # the old third-party top-100 seed merely to overwrite it later.
    if url == SIGHT_SOUND_SENTINEL:
        return ""
    return _ORIGINAL_GET_TEXT(url)


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


def build_official_sight_sound(catalog):
    payload = json.loads(SIGHT_SOUND_SOURCE.read_text(encoding="utf-8"))
    resolved = []
    unresolved = []
    for source_row in payload.get("films", []):
        iid = source_row.get("imdb_id")
        title = SIGHT_SOUND_MATCH_TITLES.get(source_row.get("title"), source_row.get("title"))
        year = source_row.get("year")
        if not iid:
            iid = es.local_match(title, year, catalog)
        if not iid:
            hit = es.imdb_lookup(title, year)
            if hit:
                iid, resolved_title, resolved_year = hit
                catalog.setdefault(iid, {"imdb_id": iid, "title": resolved_title, "year": resolved_year})
        if not iid:
            unresolved.append(source_row)
            continue
        current = catalog.setdefault(iid, {"imdb_id": iid})
        current["title"] = current.get("title") or title
        current["year"] = current.get("year") or year
        resolved.append({
            "rank": int(source_row["rank"]),
            "title": current.get("title") or title,
            "year": current.get("year") or year,
            "imdb_id": iid,
        })
    return {
        "published_depth": int(payload.get("published_depth") or 250),
        "eligible_through_year": int(payload.get("eligible_through_year") or 2022),
        "source_url": payload.get("source_url"),
        "films": sorted(resolved, key=lambda row: (row["rank"], row["title"])),
    }, unresolved, catalog


def replace_sight_sound_snapshot():
    snapshot = json.loads(es.OUTPUT.read_text(encoding="utf-8"))
    catalog = build_catalog_with_discovery()
    source, unresolved, catalog = build_official_sight_sound(catalog)
    snapshot.setdefault("ranked_sources", {})["sight_sound"] = source
    snapshot.setdefault("unresolved_ranked", {})["sight_sound"] = unresolved
    films = snapshot.setdefault("films", {})
    for row in source["films"]:
        films.setdefault(row["imdb_id"], {
            "title": row.get("title"),
            "year": row.get("year"),
        })
    snapshot["sight_sound_source_policy"] = (
        "Official BFI 2022 critics' poll top 250 static snapshot; published tie positions preserved; "
        "feature films in the project's 2000+ universe only."
    )
    es.OUTPUT.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "sight_sound_official_resolved": len(source["films"]),
        "sight_sound_official_unresolved": len(unresolved),
        "sight_sound_depth": source["published_depth"],
    }, separators=(",", ":")))


def main():
    es.BBC_URL = BBC_URL
    es.NYT_URL = NYT_URL
    es.SIGHT_SOUND_URL = SIGHT_SOUND_SENTINEL
    es.build_catalog = build_catalog_with_discovery
    es.get_text = get_text
    es.parse_wikipedia_ranked = parse_ranked
    es.put_component = put_component
    es.main()
    replace_sight_sound_snapshot()

    # Keep the extra awards in a separate module so the original Phase-B builder
    # remains easy to audit and the added family can be calibrated independently.
    import evidence_sources_extra
    evidence_sources_extra.augment_snapshot()


if __name__ == "__main__":
    main()
