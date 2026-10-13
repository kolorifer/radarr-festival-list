"""Build a reproducible Critics Choice Best Picture source snapshot.

This refresh utility reads the official Critics Choice archive, resolves Best Picture
winners/nominees against the current research universe, and writes a static source
file. The scoring pipeline will consume the static file rather than depending on
live archive availability on every run.
"""

import json
from pathlib import Path

from critics_choice_experiment import (
    ARCHIVE_URL,
    NOMINEE_POINTS,
    WINNER_POINTS,
    archive_links,
    build_index,
    get,
    parse_best_picture_page,
    resolve_record,
)

SCORES = Path("evidence-scores.json")
OUTPUT = Path("sources/critics-choice-best-picture.json")


def main():
    scores = json.loads(SCORES.read_text(encoding="utf-8"))
    rows = scores.get("films") or []
    index = build_index(rows)

    links = archive_links(get(ARCHIVE_URL))
    if len(links) < 20:
        raise RuntimeError(f"Critics Choice archive discovery unexpectedly returned only {len(links)} pages")

    records = []
    page_errors = []
    for link in links:
        try:
            page_records = parse_best_picture_page(get(link["url"]), link["ceremony_year"], link["url"])
        except Exception as exc:
            page_errors.append({"url": link["url"], "error": f"{type(exc).__name__}: {exc}"})
            continue
        if not page_records:
            page_errors.append({"url": link["url"], "error": "BEST PICTURE block not found"})
            continue
        records.extend(page_records)

    if page_errors:
        raise RuntimeError(f"Critics Choice snapshot incomplete: {page_errors}")

    resolved_by_id = {}
    unresolved = []
    for record in records:
        row = resolve_record(record, index)
        if not row:
            unresolved.append(record)
            continue
        iid = row.get("imdb_id")
        current = resolved_by_id.get(iid)
        resolved = {
            "imdb_id": iid,
            "title": row.get("title"),
            "year": row.get("year"),
            "winner": bool(record.get("winner")),
            "ceremony_year": record.get("ceremony_year"),
            "source_url": record.get("source_url"),
        }
        if current is None or (resolved["winner"] and not current["winner"]):
            resolved_by_id[iid] = resolved

    films = sorted(
        resolved_by_id.values(),
        key=lambda row: (int(row.get("year") or 0), str(row.get("title") or "")),
    )
    payload = {
        "source": "Critics Choice Awards official archive",
        "archive_url": ARCHIVE_URL,
        "category": "Best Picture",
        "family": "critics_groups_consensus",
        "weighting": {"winner": WINNER_POINTS, "nominee": NOMINEE_POINTS},
        "pages_discovered": len(links),
        "records_parsed": len(records),
        "resolved": len(films),
        "unresolved": unresolved,
        "films": films,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "pages": len(links),
        "records": len(records),
        "resolved": len(films),
        "unresolved": len(unresolved),
    }, separators=(",", ":")))


if __name__ == "__main__":
    main()
