"""Research experiment: add Critics Choice Best Picture as modest critic corroboration.

Critics Choice is an official, systematic professional-critic award archive. It is
NOT a new 100-point family. Best Picture winner/nominee evidence is tested inside
the existing critics_groups_consensus family at 25 / 8 points respectively, then
merged with the already-capped Metacritic + Rotten Tomatoes broad-critic signal.

The experiment is diagnostic only and does not change evidence-scores.json or
qualification. Network/parser failures are reported explicitly rather than silently
changing the model.
"""

import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from broad_critic_score import merge_critics_family
from hybrid_selection_experiment import evaluate

SCORES = Path("evidence-scores.json")
SNAPSHOT = Path("sources/evidence-families.json")
OUTPUT = Path("critics-choice-experiment.json")
REVIEW = Path("critics-choice-review.md")

ARCHIVE_URL = "https://www.criticschoice.com/critics-choice-awards-archives/"
UA = {"User-Agent": "Mozilla/5.0 (radarr-festival-list research; Critics Choice archive audit)"}
WINNER_POINTS = 25.0
NOMINEE_POINTS = 8.0

ALIASES = {
    "birdman": ("birdmanortheunexpectedvirtueofignorance",),
    "precious": ("preciousbasedonthenovelpushbysapphire",),
    "onceuponatimeinhollywood": ("onceuponatimeinhollywood",),
    "thelordoftheringsthereturnoftheking": ("thelordoftheringsthereturnoftheking",),
}

GUARDED_POLICY = {
    "new_floor": 225,
    "legacy_floor": 175,
    "protect_multi_route": True,
    "min_non_audience_families": 2,
}

CONTROLS = (
    "Blade Runner 2049",
    "Ex Machina",
    "Scott Pilgrim vs. the World",
    "The Batman",
    "Tenet",
    "The Machinist",
    "Dune: Part Two",
    "Midsommar",
    "Nocturnal Animals",
    "The Odyssey",
    "1917",
    "Arrival",
    "Get Out",
    "Mad Max: Fury Road",
    "Her",
    "Manchester by the Sea",
)


def norm(value):
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "", text)


def get(url):
    response = requests.get(url, headers=UA, timeout=25)
    response.raise_for_status()
    return response.text


def archive_links(html):
    soup = BeautifulSoup(html, "html.parser")
    links = []
    seen = set()
    pattern = re.compile(r"annual-critics-choice-awards-list-of-nominees-and-winners-(20\d{2})", re.I)
    for a in soup.find_all("a", href=True):
        href = urljoin(ARCHIVE_URL, a.get("href"))
        m = pattern.search(href)
        if not m or href in seen:
            continue
        ceremony_year = int(m.group(1))
        # 2000 ceremony primarily honors 1999 films, outside this project's 2000+ scope.
        if ceremony_year < 2001:
            continue
        seen.add(href)
        links.append({"url": href, "ceremony_year": ceremony_year})
    return sorted(links, key=lambda row: (row["ceremony_year"], row["url"]))


def _winner_marked_text(root):
    # Official pages mark winners in bold. Prefix those DOM nodes before flattening
    # so the parser remains independent of visual CSS.
    clone = BeautifulSoup(str(root), "html.parser")
    for tag in clone.find_all(["strong", "b"]):
        text = tag.get_text(" ", strip=True)
        if text and not text.startswith("**"):
            tag.string = "**" + text
    text = clone.get_text("\n")
    return [re.sub(r"\s+", " ", line).strip() for line in text.splitlines() if line.strip()]


def parse_best_picture_page(html, ceremony_year, source_url=None):
    soup = BeautifulSoup(html, "html.parser")
    root = (
        soup.select_one("article .entry-content")
        or soup.select_one(".entry-content")
        or soup.find("article")
        or soup.find("main")
        or soup
    )
    lines = _winner_marked_text(root)
    start = next((i for i, line in enumerate(lines) if line.upper() == "BEST PICTURE"), None)
    if start is None:
        return []

    block = []
    for line in lines[start + 1:]:
        plain = line.lstrip("*").strip()
        if plain.upper().startswith("BEST ") and block:
            break
        if plain.upper() in {"FILM CATEGORIES", "TELEVISION CATEGORIES", "SPECIAL AWARDS"}:
            if block:
                break
            continue
        if plain:
            block.append(line)

    by_title = {}
    for line in block:
        winner = line.startswith("**")
        title = line[2:].strip() if winner else line.strip()
        # Defensive cleanup for stray winner labels sometimes embedded in copied archive text.
        title = re.sub(r"\s+\(WINNER\)\s*$", "", title, flags=re.I).strip()
        if not title:
            continue
        key = norm(title)
        if not key:
            continue
        current = by_title.get(key)
        if current is None:
            by_title[key] = {
                "title": title,
                "winner": winner,
                "ceremony_year": ceremony_year,
                "film_year_hint": ceremony_year - 1,
                "source_url": source_url,
            }
        elif winner:
            current["winner"] = True

    return list(by_title.values())


def build_index(rows):
    out = defaultdict(list)
    for row in rows:
        out[norm(row.get("title"))].append(row)
    return out


def resolve_record(record, index):
    key = norm(record.get("title"))
    keys = (key,) + ALIASES.get(key, ())
    candidates = []
    for candidate_key in keys:
        candidates.extend(index.get(candidate_key, []))
    # Critics Choice ceremony year normally follows the film year; Dec-2016 is the
    # known exception and therefore the ±1 window intentionally accepts same-year films.
    hint = int(record.get("film_year_hint") or 0)
    candidates = [
        row for row in candidates
        if not str(row.get("year") or "").isdigit() or abs(int(row.get("year")) - hint) <= 1
    ]
    unique = {row.get("imdb_id"): row for row in candidates if row.get("imdb_id")}
    return next(iter(unique.values())) if len(unique) == 1 else None


def recompute_critics(row, snapshot_film, cca_points):
    base_group = float(((snapshot_film or {}).get("family_scores") or {}).get("critics_groups_consensus") or 0)
    broad = float(((row.get("broad_critic_consensus") or {}).get("active_points_max_40")) or 0)
    old_active = float((row.get("source_points") or {}).get("critics_groups_consensus") or 0)
    group_with_cca = min(100.0, base_group + cca_points)
    new_active = merge_critics_family(group_with_cca, broad)
    return {
        "base_group_before_cca": round(base_group, 2),
        "cca_points": round(cca_points, 2),
        "group_after_cca": round(group_with_cca, 2),
        "broad_points": round(broad, 2),
        "old_active_critics": round(old_active, 2),
        "new_active_critics": round(new_active, 2),
        "delta": round(new_active - old_active, 2),
    }


def compact(row):
    return {
        "title": row.get("title"),
        "year": row.get("year"),
        "imdb_id": row.get("imdb_id"),
        "base_score": row.get("overall_score"),
        "new_score": row.get("experimental_score"),
        "base_rank": row.get("overall_rank"),
        "new_rank": row.get("experimental_rank"),
        "cca": row.get("cca_best_picture"),
        "qualified_old": bool(row.get("qualified")),
    }


def build_review(payload):
    lines = [
        "# Critics Choice Best Picture experiment",
        "",
        "Diagnostic only. Critics Choice Best Picture is tested inside the existing Critics family at 25 points for a winner and 8 for a nominee; it is not a new 100-point family.",
        "",
        f"Official archive pages parsed: **{payload['pages_parsed']}** / **{payload['pages_discovered']}** · Best Picture records: **{payload['records']}** · resolved to research universe: **{payload['resolved_records']}**.",
        "",
        "## Guarded hybrid-policy impact",
        "",
        f"Baseline selected **{payload['hybrid']['baseline']['selected']}**, experimental **{payload['hybrid']['experimental']['selected']}**; promotions {payload['hybrid']['baseline']['promotions_vs_old']} → {payload['hybrid']['experimental']['promotions_vs_old']}.",
        "",
        "## Newly selected by Critics Choice evidence",
        "",
        "| Film | Base → new | Critics Choice |",
        "|---|---:|---|",
    ]
    for row in payload.get("newly_selected", []):
        cca = row.get("cca") or {}
        status = "winner" if cca.get("winner") else "nominee"
        lines.append(f"| {row['title']} ({row['year']}) | {row['base_score']:.1f} → {row['new_score']:.1f} | {status}, +{cca.get('points', 0):.0f} |")
    if not payload.get("newly_selected"):
        lines.append("| — | — | — |")

    lines.extend([
        "",
        "## Largest score changes",
        "",
        "| Film | Base → new | CCA |",
        "|---|---:|---|",
    ])
    for row in payload.get("largest_changes", [])[:40]:
        cca = row.get("cca") or {}
        status = "winner" if cca.get("winner") else "nominee"
        lines.append(f"| {row['title']} ({row['year']}) | {row['base_score']:.1f} → {row['new_score']:.1f} | {status} |")
    return "\n".join(lines) + "\n"


def main():
    scores = json.loads(SCORES.read_text(encoding="utf-8"))
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    rows = scores.get("films") or []
    snapshot_films = snapshot.get("films") or {}
    index = build_index(rows)

    page_errors = []
    try:
        links = archive_links(get(ARCHIVE_URL))
    except Exception as exc:
        links = []
        page_errors.append({"url": ARCHIVE_URL, "error": f"{type(exc).__name__}: {exc}"})

    records = []
    parsed_pages = 0
    for link in links:
        try:
            page_records = parse_best_picture_page(get(link["url"]), link["ceremony_year"], link["url"])
        except Exception as exc:
            page_errors.append({"url": link["url"], "error": f"{type(exc).__name__}: {exc}"})
            continue
        if page_records:
            parsed_pages += 1
            records.extend(page_records)
        else:
            page_errors.append({"url": link["url"], "error": "BEST PICTURE block not found"})

    resolved_by_id = {}
    unresolved = []
    for record in records:
        row = resolve_record(record, index)
        if not row:
            unresolved.append(record)
            continue
        iid = row.get("imdb_id")
        current = resolved_by_id.get(iid)
        # Keep the strongest CCA result if a film appears in more than one ceremony.
        if current is None or (record["winner"] and not current["winner"]):
            resolved_by_id[iid] = {**record, "resolved_title": row.get("title"), "resolved_year": row.get("year")}

    experimental = []
    for row in rows:
        exp = dict(row)
        cca = resolved_by_id.get(row.get("imdb_id"))
        if cca:
            cca_points = WINNER_POINTS if cca["winner"] else NOMINEE_POINTS
            critic = recompute_critics(row, snapshot_films.get(row.get("imdb_id")), cca_points)
            exp["experimental_score"] = round(float(row.get("overall_score") or 0) + critic["delta"], 2)
            exp["cca_best_picture"] = {
                "winner": bool(cca["winner"]),
                "ceremony_year": cca["ceremony_year"],
                "source_url": cca["source_url"],
                "points": cca_points,
                "critic_recompute": critic,
            }
            if critic["new_active_critics"] > 0:
                source_points = dict(row.get("source_points") or {})
                source_points["critics_groups_consensus"] = critic["new_active_critics"]
                exp["source_points"] = source_points
                exp["has_non_audience_evidence"] = True
        else:
            exp["experimental_score"] = float(row.get("overall_score") or 0)
            exp["cca_best_picture"] = None
        experimental.append(exp)

    experimental.sort(key=lambda r: (-float(r.get("experimental_score") or 0), r.get("title") or ""))
    for rank, row in enumerate(experimental, 1):
        row["experimental_rank"] = rank

    base_hybrid = evaluate(rows, GUARDED_POLICY)
    # evaluate expects overall_score, so make a shallow experimental view using the new score.
    hybrid_rows = []
    for row in experimental:
        tmp = dict(row)
        tmp["overall_score"] = row["experimental_score"]
        hybrid_rows.append(tmp)
    experimental_hybrid = evaluate(hybrid_rows, GUARDED_POLICY)

    def selected_ids(input_rows):
        result = set()
        from hybrid_selection_experiment import legacy_keep, score_keep
        for row in input_rows:
            if score_keep(row, GUARDED_POLICY["new_floor"], GUARDED_POLICY["min_non_audience_families"]) or legacy_keep(row, GUARDED_POLICY["legacy_floor"], GUARDED_POLICY["protect_multi_route"]):
                result.add(row.get("imdb_id"))
        return result

    base_ids = selected_ids(rows)
    exp_ids = selected_ids(hybrid_rows)
    newly_selected_ids = exp_ids - base_ids
    newly_selected = [compact(r) for r in experimental if r.get("imdb_id") in newly_selected_ids]

    changes = [r for r in experimental if abs(float(r.get("experimental_score") or 0) - float(r.get("overall_score") or 0)) > 0.001]
    changes.sort(key=lambda r: (-(float(r.get("experimental_score") or 0) - float(r.get("overall_score") or 0)), r.get("title") or ""))
    by_title = {r.get("title"): r for r in experimental}

    thresholds = {}
    for floor in (300, 275, 250, 225, 200):
        chosen = [r for r in experimental if float(r.get("experimental_score") or 0) >= floor and r.get("has_non_audience_evidence")]
        thresholds[str(floor)] = {
            "selected": len(chosen),
            "promotions_vs_old": sum(not bool(r.get("qualified")) for r in chosen),
            "old_qualified_retained": sum(bool(r.get("qualified")) for r in chosen),
        }

    output = {
        "mode": "research-critics-choice-best-picture-v1",
        "qualification_unchanged": True,
        "active_score_unchanged": True,
        "source": "Critics Choice Awards official archive",
        "archive_url": ARCHIVE_URL,
        "weighting": {"winner": WINNER_POINTS, "nominee": NOMINEE_POINTS, "family": "critics_groups_consensus"},
        "pages_discovered": len(links),
        "pages_parsed": parsed_pages,
        "page_errors": page_errors,
        "records": len(records),
        "resolved_records": len(resolved_by_id),
        "unresolved_records": unresolved,
        "thresholds": thresholds,
        "hybrid": {
            "policy": GUARDED_POLICY,
            "baseline": {k: base_hybrid[k] for k in ("selected", "promotions_vs_old", "legacy_retained", "legacy_dropped")},
            "experimental": {k: experimental_hybrid[k] for k in ("selected", "promotions_vs_old", "legacy_retained", "legacy_dropped")},
        },
        "newly_selected": newly_selected,
        "controls": {title: compact(by_title[title]) for title in CONTROLS if title in by_title},
        "largest_changes": [compact(r) for r in changes[:100]],
    }
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REVIEW.write_text(build_review(output), encoding="utf-8")
    print(json.dumps({
        "pages": [parsed_pages, len(links)],
        "records": len(records),
        "resolved": len(resolved_by_id),
        "unresolved": len(unresolved),
        "errors": len(page_errors),
        "hybrid": output["hybrid"],
        "newly_selected": newly_selected,
        "controls": output["controls"],
    }, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
