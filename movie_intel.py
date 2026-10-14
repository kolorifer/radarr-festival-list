"""Production D016 lookup core for enriched autobrr notifications."""
import re
from pathlib import Path
from production_scoring import load_catalog

ROOT = Path(__file__).resolve().parent


def _norm(s):
    return re.sub(r"[^a-z0-9]+", "", str(s).lower())


def build_index():
    return load_catalog(ROOT)


def find_local(title, year, index=None):
    if index is None:
        index = build_index()
    key = _norm(title)
    hits = []
    for row in index.values():
        titles = [row.get("title"), *row.get("aliases", [])]
        if any(t and _norm(t) == key for t in titles) and (
                not year or str(row.get("year")) == str(year)):
            hits.append(row)
    return hits[0] if len(hits) == 1 else None


def rejection_class(rejections):
    text = " ".join(rejections or []).lower()
    if "unknown movie" in text:
        return "unknown_movie"
    if "quality" in text:
        return "quality"
    if "upgrade" in text:
        return "not_upgrade"
    if "existing" in text or "already" in text:
        return "existing"
    return "other"
