"""Audit provider coverage already present in the ReelDB cache.

Research-only: no network access and no score changes. The output is used to
decide whether any cached critic aggregate can fill the missing non-audience
coverage without inventing a new data source.
"""

import json
from collections import Counter, defaultdict
from pathlib import Path

INPUT = Path("audience-ratings.json")
OUTPUT = Path("rating-source-audit.json")

SAMPLES = {
    "tt1856101": "Blade Runner 2049",
    "tt0470752": "Ex Machina",
    "tt1392214": "Prisoners",
    "tt1130884": "Shutter Island",
    "tt1877830": "The Batman",
    "tt6723592": "Tenet",
    "tt0361862": "The Machinist",
    "tt15239678": "Dune: Part Two",
}


def simple_shape(value):
    if isinstance(value, dict):
        return sorted(value.keys())
    return type(value).__name__


def safe_sample(value):
    if isinstance(value, dict):
        return {
            str(k): v
            for k, v in value.items()
            if isinstance(v, (str, int, float, bool)) or v is None
        }
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return None


def main():
    payload = json.loads(INPUT.read_text(encoding="utf-8"))
    ratings = payload.get("ratings") or {}

    provider_counts = Counter()
    provider_shapes = defaultdict(Counter)
    for row in ratings.values():
        rr = row.get("reeldb") or {}
        for provider, value in rr.items():
            if value is None:
                continue
            provider_counts[provider] += 1
            provider_shapes[provider][json.dumps(simple_shape(value), sort_keys=True)] += 1

    samples = {}
    for imdb_id, label in SAMPLES.items():
        row = ratings.get(imdb_id) or {}
        rr = row.get("reeldb") or {}
        samples[label] = {
            "imdb_id": imdb_id,
            "providers": {k: safe_sample(v) for k, v in rr.items() if safe_sample(v) is not None},
        }

    out = {
        "mode": "cached-rating-source-audit-v1",
        "network_requests": 0,
        "cached_titles": len(ratings),
        "provider_counts": dict(provider_counts.most_common()),
        "provider_shapes": {
            provider: [
                {"shape": json.loads(shape), "count": count}
                for shape, count in counts.most_common(5)
            ]
            for provider, counts in sorted(provider_shapes.items())
        },
        "samples": samples,
    }
    OUTPUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "cached_titles": len(ratings),
        "providers": dict(provider_counts.most_common()),
        "sample_provider_keys": {
            label: sorted((samples[label].get("providers") or {}).keys())
            for label in samples
        },
    }, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
