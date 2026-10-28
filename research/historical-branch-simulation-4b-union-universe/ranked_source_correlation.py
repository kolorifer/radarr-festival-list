"""Audit overlap/correlation among ranked critical/canon evidence sources.

Diagnostic only. The purpose is to detect whether TSPDT, Sight & Sound, BBC and
NYT are so correlated that counting each as a full 100-point family would amount
to repeated voting by essentially the same critical consensus.
"""

import json
import math
from itertools import combinations
from pathlib import Path

BACKCATALOG = Path("backcatalog-details.json")
SNAPSHOT = Path("sources/evidence-families.json")
OUTPUT_JSON = Path("ranked-source-correlation.json")
OUTPUT_MD = Path("ranked-source-correlation.md")

SOURCE_ORDER = ("tspdt_21c", "sight_sound", "bbc_21c", "nyt_21c")
LABELS = {
    "tspdt_21c": "TSPDT 21C",
    "sight_sound": "Sight & Sound 2022",
    "bbc_21c": "BBC 2016",
    "nyt_21c": "NYT 2025",
}


def _rankdata(values):
    """Average ranks, 1-based, preserving ties."""
    indexed = sorted(enumerate(values), key=lambda x: x[1])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(indexed):
        j = i + 1
        while j < len(indexed) and indexed[j][1] == indexed[i][1]:
            j += 1
        avg = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks[indexed[k][0]] = avg
        i = j
    return ranks


def _pearson(xs, ys):
    if len(xs) != len(ys) or len(xs) < 2:
        return None
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    dx = [x - mx for x in xs]
    dy = [y - my for y in ys]
    denom = math.sqrt(sum(x * x for x in dx) * sum(y * y for y in dy))
    if denom == 0:
        return None
    return sum(x * y for x, y in zip(dx, dy)) / denom


def spearman(xs, ys):
    if len(xs) < 3:
        return None
    return _pearson(_rankdata(xs), _rankdata(ys))


def load_sources():
    back = json.loads(BACKCATALOG.read_text(encoding="utf-8"))
    snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    sources = {
        "tspdt_21c": {
            row["imdb_id"]: int(row["tspdt_rank"])
            for row in back.get("candidates", [])
            if row.get("imdb_id") and isinstance(row.get("tspdt_rank"), int)
        }
    }
    ranked = snap.get("ranked_sources") or {}
    for key in ("sight_sound", "bbc_21c", "nyt_21c"):
        sources[key] = {
            row["imdb_id"]: int(row["rank"])
            for row in (ranked.get(key) or {}).get("films", [])
            if row.get("imdb_id") and isinstance(row.get("rank"), int)
        }
    return sources


def pair_metrics(a_name, a, b_name, b):
    aset, bset = set(a), set(b)
    common = sorted(aset & bset)
    union = aset | bset
    rho = spearman([a[i] for i in common], [b[i] for i in common])
    containment = len(common) / min(len(aset), len(bset)) if min(len(aset), len(bset)) else 0.0
    jaccard = len(common) / len(union) if union else 0.0
    if len(common) < 10:
        reliability = "small-common-sample"
    elif rho is not None and abs(rho) >= 0.75 and containment >= 0.60:
        reliability = "high-redundancy-signal"
    elif rho is not None and abs(rho) >= 0.50 and containment >= 0.40:
        reliability = "moderate-redundancy-signal"
    else:
        reliability = "limited-redundancy-signal"
    return {
        "source_a": a_name,
        "source_b": b_name,
        "size_a": len(aset),
        "size_b": len(bset),
        "common_films": len(common),
        "jaccard": round(jaccard, 4),
        "smaller_source_containment": round(containment, 4),
        "spearman_common_films": round(rho, 4) if rho is not None else None,
        "assessment": reliability,
    }


def build_markdown(payload):
    lines = [
        "# Ranked critical-source correlation audit",
        "",
        "Diagnostic only. Correlation is calculated on films shared by each pair; containment shows how much of the smaller source is present in the larger one.",
        "",
        "| Pair | Sizes | Common | Containment | Jaccard | Spearman ρ | Assessment |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for p in payload["pairs"]:
        rho = "—" if p["spearman_common_films"] is None else f"{p['spearman_common_films']:.2f}"
        lines.append(
            f"| {LABELS[p['source_a']]} ↔ {LABELS[p['source_b']]} | "
            f"{p['size_a']} / {p['size_b']} | {p['common_films']} | "
            f"{p['smaller_source_containment']:.1%} | {p['jaccard']:.1%} | {rho} | {p['assessment']} |"
        )
    lines.extend([
        "",
        "## Interpretation rule",
        "",
        "A pair is only flagged as a strong redundancy concern when it has both substantial rank correlation (|ρ| ≥ 0.75) and at least 60% containment of the smaller list. Fewer than 10 common films is treated as too small a sample for a weighting decision.",
        "",
    ])
    high = [p for p in payload["pairs"] if p["assessment"] == "high-redundancy-signal"]
    moderate = [p for p in payload["pairs"] if p["assessment"] == "moderate-redundancy-signal"]
    if high:
        lines.append("**Result:** at least one pair shows a high redundancy signal; full independent 100-point weighting should be reconsidered.")
    elif moderate:
        lines.append("**Result:** no pair reaches the high-redundancy threshold, but at least one pair is moderately correlated. Keep separate families for now and stress-test diminishing returns before freezing weights.")
    else:
        lines.append("**Result:** no pair reaches even the moderate redundancy threshold on the available common samples. There is no empirical reason yet to compress the four ranked sources into one family.")
    lines.append("")
    return "\n".join(lines)


def main():
    sources = load_sources()
    pairs = [pair_metrics(a, sources[a], b, sources[b]) for a, b in combinations(SOURCE_ORDER, 2)]
    payload = {
        "mode": "research-ranked-source-correlation-v1",
        "qualification_unchanged": True,
        "sources": {key: {"label": LABELS[key], "films": len(sources[key])} for key in SOURCE_ORDER},
        "pairs": pairs,
    }
    OUTPUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUTPUT_MD.write_text(build_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
