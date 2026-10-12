"""Apply diminishing returns between TSPDT and Sight & Sound.

The correlation audit found that every modern Sight & Sound film in the current
snapshot is also in TSPDT and their common ranks have Spearman rho ~0.83. TSPDT
therefore remains the 100-point canon anchor, while Sight & Sound contributes at
50% strength when it corroborates a TSPDT film. A hypothetical Sight & Sound film
outside TSPDT keeps its full score. The joint canon block can contribute at most
150 points.

This rewrites research evidence-scores.json only. Frozen qualification routes and
production feeds remain unchanged.
"""

import json
from pathlib import Path

SCORES = Path("evidence-scores.json")
SIGHT_SOUND_CUTOFF_YEAR = 2022
CANON_JOINT_MAX = 150.0
SIGHT_SOUND_CORROBORATION_FACTOR = 0.5


def adjusted_sight_sound(tspdt, sight_sound):
    tspdt = float(tspdt or 0)
    sight_sound = float(sight_sound or 0)
    if sight_sound <= 0:
        return 0.0
    if tspdt <= 0:
        return round(min(100.0, sight_sound), 2)
    room = max(0.0, CANON_JOINT_MAX - tspdt)
    return round(min(room, sight_sound * SIGHT_SOUND_CORROBORATION_FACTOR), 2)


def apply(payload):
    rows = payload.get("films") or []
    affected = 0
    total_reduction = 0.0
    for row in rows:
        points = row.setdefault("source_points", {})
        tspdt = float(points.get("tspdt_21c") or 0)
        raw_ss = float(points.get("sight_sound") or 0)
        active_ss = adjusted_sight_sound(tspdt, raw_ss)
        delta = round(active_ss - raw_ss, 2)

        row["canon_correlation"] = {
            "tspdt_active": round(tspdt, 2),
            "sight_sound_raw": round(raw_ss, 2),
            "sight_sound_active": round(active_ss, 2),
            "joint_canon_points": round(tspdt + active_ss, 2),
            "joint_canon_max": CANON_JOINT_MAX,
        }
        if raw_ss > 0:
            row.setdefault("raw_correlated_source_points", {})["sight_sound"] = round(raw_ss, 2)
        if abs(delta) <= 0.001:
            continue

        affected += 1
        total_reduction += -delta
        points["sight_sound"] = active_ss
        evidence = row.setdefault("source_evidence", {})
        current = list(evidence.get("sight_sound") or [])
        current.append(
            f"Correlation adjustment: Sight & Sound raw {raw_ss:.2f} -> active {active_ss:.2f}; "
            "50% corroboration alongside TSPDT"
        )
        evidence["sight_sound"] = current
        row["overall_score"] = round(float(row.get("overall_score") or 0) + delta, 2)

        year = row.get("year")
        if str(year or "").isdigit() and int(year) <= SIGHT_SOUND_CUTOFF_YEAR:
            old_max = float(row.get("eligible_max_score") or 0)
            row["eligible_max_score"] = max(0, int(round(old_max - 50)))
            row["eligible_score_pct"] = round(
                100.0 * float(row.get("overall_score") or 0) / row["eligible_max_score"], 2
            ) if row["eligible_max_score"] else 0.0

    rows.sort(key=lambda r: (-float(r.get("overall_score") or 0), -int(r.get("source_hits") or 0), r.get("title") or ""))
    for rank, row in enumerate(rows, 1):
        row["overall_rank"] = rank

    payload["mode"] = "research-evidence-score-v9-canon150-audience200-broadcritics40"
    payload["current_score_ceiling"] = 950
    policy = payload.setdefault("score_policy", {})
    policy["non_audience_max"] = 750
    policy["current_score_ceiling"] = 950
    policy["canon_correlation_policy"] = (
        "TSPDT is the 100-point long-term canon anchor. Sight & Sound remains an independent source but, "
        "because its modern entries are fully contained in TSPDT and rank correlation is high, its points are "
        "halved when corroborating a TSPDT film. Joint TSPDT + Sight & Sound maximum is 150."
    )
    sources = payload.setdefault("sources", {})
    sources.setdefault("tspdt_21c", {}).update({"canon_anchor": True, "joint_canon_max": 150})
    sources.setdefault("sight_sound", {}).update({
        "raw_max_points": 100,
        "correlated_with": "tspdt_21c",
        "corroboration_factor_when_tspdt_present": 0.5,
        "joint_canon_max": 150,
    })
    payload["canon_correlation_affected_count"] = affected
    payload["canon_correlation_total_reduction"] = round(total_reduction, 2)
    return payload


def main():
    payload = json.loads(SCORES.read_text(encoding="utf-8"))
    payload = apply(payload)
    SCORES.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "films": len(payload.get("films") or []),
        "score_ceiling": payload.get("current_score_ceiling"),
        "affected": payload.get("canon_correlation_affected_count"),
        "total_reduction": payload.get("canon_correlation_total_reduction"),
        "top": [
            {"rank": r.get("overall_rank"), "title": r.get("title"), "score": r.get("overall_score")}
            for r in (payload.get("films") or [])[:5]
        ],
    }, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
