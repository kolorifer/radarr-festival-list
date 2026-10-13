"""Research-only calibration of frozen Evidence Scores; never writes production inputs."""
import argparse
import copy
import csv
import hashlib
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path
import subprocess

import audience_cap_simulation as sim

OUT = Path("simulations/qualification-calibration")
SCORE = Path("simulations/data-identity-integrity/evidence-score-150.json")
CONFIG = Path("qualification-calibration-config.json")
POLICIES = {
    "score_only": "Evidence Score >= threshold",
    "A_keep_existing": "Existing qualification OR Evidence Score >= threshold",
    "B_two_families": "Score >= threshold AND at least 2 independent non-audience families",
    "C_one_family": "Score >= threshold AND at least 1 independent non-audience family",
    "D_audience_half": "Score >= threshold AND Audience <= 50% of total",
    "E_low_evidence_guard": "Score >= threshold AND >=1 non-audience family; with only 1 family, Audience <=50%",
}
FIXED = [
    SCORE, Path("simulation-qualifiers.json"), Path("backcatalog-details.json"),
    Path("sources/evidence-families.json"), Path("sources/identity-overrides.json"),
    Path("sources/phase-b-institutional.json"), Path("sources/critics-choice-best-picture.json"),
    Path("sources/tspdt-21c.json"), Path("audience-ratings.json"),
    Path("evidence_score.py"), Path("audience_cap_simulation.py"),
    Path("canon_overlap_score.py"), Path("broad_critic_score.py"),
    Path("simulations/data-identity-integrity/award-identity-audit.json"),
]
CANON = {"tspdt_21c", "sight_sound"}

def decimal(value):
    return Decimal(str(value))

def family_keys(row, independent=True):
    keys = {k for k,v in row["non_audience_points"].items() if v > 0}
    if independent and keys & CANON:
        keys -= CANON
        keys.add("canon")
    return sorted(keys)

def audience_dominant(row):
    return 2 * decimal(row["audience_score"]) > decimal(row["overall_score"])

def qualifies(row, policy, threshold):
    if policy not in POLICIES:
        raise ValueError("Unknown research policy: " + policy)
    reached = decimal(row["overall_score"]) >= decimal(threshold)
    if policy == "A_keep_existing":
        return bool(row["qualified"] or reached)
    if not reached:
        return False
    count = len(family_keys(row))
    if policy == "B_two_families":
        return count >= 2
    if policy == "C_one_family":
        return count >= 1
    if policy == "D_audience_half":
        return not audience_dominant(row)
    if policy == "E_low_evidence_guard":
        return count >= 1 and (count >= 2 or not audience_dominant(row))
    return True

def key(policy, threshold):
    return policy + "_" + str(threshold)

def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True,
                               indent=2, allow_nan=False) + "\n", encoding="utf-8")

def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n",
                                extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k:json.dumps(row.get(k),ensure_ascii=False,sort_keys=True)
                             if isinstance(row.get(k),(list,dict)) else row.get(k)
                             for k in fields})

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def validate_baseline(root, config, payload, frozen):
    for path in FIXED:
        original = subprocess.check_output(
            ["git","show",config["baseline_commit"]+":"+str(path)],cwd=root)
        if original != (root/path).read_bytes():
            raise ValueError("Frozen baseline changed: " + str(path))
    rows = payload["films"]
    ids = [r["imdb_id"] for r in rows]
    current = {r["imdb_id"]:r for r in frozen}
    if len(ids)!=1909 or len(set(ids))!=1909 or len(current)!=255:
        raise ValueError("Frozen universe/qualification size changed")
    if payload["audience_cap"]!=150 or payload["current_score_ceiling"]!=1000:
        raise ValueError("Agreed score model changed")
    if max(r["eligible_max_score"] for r in rows)!=1000:
        raise ValueError("Effective ceiling changed")
    for r in rows:
        if not (0<=r["audience_score"]<=150 and 0<=r["overall_score"]<=r["eligible_max_score"]<=1000):
            raise ValueError("Score range mismatch")
        if r["qualified"] != (r["imdb_id"] in current):
            raise ValueError("Frozen qualification mismatch")
        if r["routes"] != current.get(r["imdb_id"],{}).get("routes",[]):
            raise ValueError("Frozen routes mismatch")
    if set(current)-set(ids):
        raise ValueError("Qualified film absent from frozen universe")
    return {str(path):digest(root/path) for path in FIXED}

def annotate(rows, back):
    """Only existing published taste/watch annotations; never change score or decisions."""
    back_index = {r["imdb_id"]:r for r in back["candidates"]}
    result = []
    for original in rows:
        r = copy.deepcopy(original)
        source = back_index.get(r["imdb_id"],{})
        positive = [s for s in source.get("signals",[]) if s.startswith("personal-positive +")]
        r["taste_positive"] = bool(positive)
        r["taste_signals"] = positive
        r["watch_state"] = source.get("watch_state","unknown")
        r["taste_observation"] = "positive" if positive else "unlabelled"
        r["independent_non_audience_families"] = family_keys(r)
        r["independent_non_audience_family_count"] = len(family_keys(r))
        r["raw_non_audience_family_count"] = len(family_keys(r,False))
        r["contributing_scoring_family_count"] = len(family_keys(r,False)) + int(r["audience_score"]>0)
        r["audience_dominant"] = audience_dominant(r)
        r["audience_only"] = r["audience_score"]>0 and not family_keys(r)
        r["major_composition"] = "+".join(family_keys(r)+(["audience"] if r["audience_score"]>0 else [])) or "no_positive_points"
        r["critics_award_evidence"] = any(not s.startswith("Broad critics:") for s in r["source_evidence"].get("critics_groups_consensus",[]))
        r["critics_family_from_broad_ratings_only"] = r["non_audience_points"].get("critics_groups_consensus",0)>0 and not r["critics_award_evidence"]
        result.append(r)
    return result

def percent(count, total):
    return round(100*count/total,2) if total else None

def counters(rows, field):
    return dict(sorted(Counter(str(r[field]) for r in rows).items()))

def detailed_bands(rows):
    boundaries = list(range(0,401,25)) + [450,500,600,700,800,900,1000]
    counts = {f"{low}-<{high}":sum(low<=r["overall_score"]<high for r in rows)
              for low,high in zip(boundaries,boundaries[1:])}
    counts["1000"] = sum(r["overall_score"]==1000 for r in rows)
    return counts

def population(rows, config):
    return {
        "count":len(rows),"score_distribution":sim.distribution(rows) if rows else None,
        "detailed_score_bands":detailed_bands(rows),
        "audience_complete":sum(r["audience_complete"] for r in rows),
        "audience_incomplete":sum(not r["audience_complete"] for r in rows),
        "audience_only":sum(r["audience_only"] for r in rows),
        "audience_dominant":sum(r["audience_dominant"] for r in rows),
        "year_counts":counters(rows,"year"),
        "recent_count":sum(r["year"]>=config["recent_year_start"] for r in rows),
        "older_count":sum(r["year"]<config["recent_year_start"] for r in rows),
        "independent_non_audience_family_count":counters(rows,"independent_non_audience_family_count"),
        "raw_non_audience_family_count":counters(rows,"raw_non_audience_family_count"),
        "contributing_scoring_family_count":counters(rows,"contributing_scoring_family_count"),
        "major_family_composition":counters(rows,"major_composition"),
        "known_positive_taste":sum(r["taste_positive"] for r in rows),
        "known_watched":sum(r["watch_state"]=="watched" for r in rows),
        "critics_family_from_broad_ratings_only":sum(r["critics_family_from_broad_ratings_only"] for r in rows),
        "eligible_max_score_counts":counters(rows,"eligible_max_score"),
    }

def public_row(row):
    fields = (
        "imdb_id","title","year","overall_rank","overall_score","audience_score",
        "non_audience_score","audience_share_pct","audience_complete","audience_coverage",
        "eligible_max_score","qualified","routes","source_points","source_evidence",
        "independent_non_audience_families","independent_non_audience_family_count",
        "raw_non_audience_family_count","contributing_scoring_family_count",
        "major_composition","audience_only","audience_dominant","taste_positive",
        "taste_signals","taste_observation","watch_state","critics_award_evidence",
        "critics_family_from_broad_ratings_only")
    return {field:row[field] for field in fields}

def nearest(rows, threshold, above, n):
    side = [r for r in rows if (r["overall_score"]>=threshold)==above]
    return sorted(side,key=lambda r:(abs(r["overall_score"]-threshold),r["imdb_id"]))[:n]

def incomplete_sensitivity(rows, threshold, policy, config):
    result = []
    for r in rows:
        if r["audience_complete"]:
            continue
        missing = [k for k,v in r["audience_coverage"].items() if not v["available"]]
        # Each missing IMDb/Letterboxd component has the existing weighted ceiling75.
        upper_gain = 75*len(missing)
        item = {"imdb_id":r["imdb_id"],"title":r["title"],"year":r["year"],
                "observed_score":r["overall_score"],"threshold":threshold,
                "distance":round(r["overall_score"]-threshold,2),"missing":missing,
                "upper_possible_score":round(min(1000,r["overall_score"]+upper_gain),2),
                "near_threshold":abs(r["overall_score"]-threshold)<=config["borderline_window"],
                "could_cross_score_boundary":r["overall_score"]<threshold<=r["overall_score"]+upper_gain,
                "selected_observed":qualifies(r,policy,threshold),
                "warning":"Upper bound only; no ratings inferred. Extra audience can also fail the 50% guard."}
        result.append(item)
    return result

def summarize(rows, policy, threshold, config):
    chosen = [r for r in rows if qualifies(r,policy,threshold)]
    newly = [r for r in chosen if not r["qualified"]]
    lost = [r for r in rows if r["qualified"] and not qualifies(r,policy,threshold)]
    overlap = sum(r["qualified"] for r in chosen)
    stats = {
        "policy":policy,"threshold":threshold,"policy_key":key(policy,threshold),
        "total_qualifying":len(chosen),"newly_qualifying":len(newly),
        "current_retained":overlap,"current_lost":len(lost),
        "current_lost_due_score":sum(r["overall_score"]<threshold for r in lost),
        "current_lost_due_guard":sum(r["overall_score"]>=threshold for r in lost),
        "new_excluded_by_guard":sum(not r["qualified"] and r["overall_score"]>=threshold and not qualifies(r,policy,threshold) for r in rows),
        "overlap_selected_pct":percent(overlap,len(chosen)),
        "baseline_retention_pct":percent(overlap,255),
        "selected_audience_only":sum(r["audience_only"] for r in chosen),
        "selected_audience_dominant":sum(r["audience_dominant"] for r in chosen),
        "new_audience_only":sum(r["audience_only"] for r in newly),
        "new_audience_dominant":sum(r["audience_dominant"] for r in newly),
        "selected_incomplete_audience":sum(not r["audience_complete"] for r in chosen),
        "recent_selected":sum(r["year"]>=config["recent_year_start"] for r in chosen),
        "recent_new":sum(r["year"]>=config["recent_year_start"] for r in newly),
        "new_known_positive_taste":sum(r["taste_positive"] for r in newly),
        "lost_known_positive_taste":sum(r["taste_positive"] for r in lost),
        "selected_known_positive_taste":sum(r["taste_positive"] for r in chosen),
        "positive_taste_retention_pct":percent(sum(r["taste_positive"] for r in chosen),sum(r["taste_positive"] for r in rows)),
        "selected_known_watched":sum(r["watch_state"]=="watched" for r in chosen),
        "new_known_watched":sum(r["watch_state"]=="watched" for r in newly),
    }
    return {
        "summary":stats,"selected_ids":[r["imdb_id"] for r in chosen],
        "newly_qualifying_ids":[r["imdb_id"] for r in newly],
        "currently_qualified_lost_ids":[r["imdb_id"] for r in lost],
        "selected_population":population(chosen,config),
        "new_population":population(newly,config),
        "lost_population":population(lost,config),
        "incomplete_audience_sensitivity":incomplete_sensitivity(rows,threshold,policy,config),
    }

def examples(rows, policy, threshold, config):
    n=config["example_limit"]
    new=[r for r in rows if qualifies(r,policy,threshold) and not r["qualified"]]
    lost=[r for r in rows if r["qualified"] and not qualifies(r,policy,threshold)]
    guard_excluded=[r for r in rows if r["overall_score"]>=threshold and not qualifies(r,policy,threshold)]
    weak=[r for r in rows if r["audience_dominant"] or r["independent_non_audience_family_count"]<2]
    strong=sorted([r for r in rows if r["non_audience_score"]>r["audience_score"]],
                  key=lambda r:(-r["non_audience_score"],r["imdb_id"]))
    groups={
        "top_newly_admitted":new[:n],
        "borderline_above_score":nearest(rows,threshold,True,n),
        "borderline_below_score":nearest(rows,threshold,False,n),
        "surprising_inclusions_review":sorted(new,key=lambda r:(r["independent_non_audience_family_count"],-r["audience_share_pct"],-r["overall_score"],r["imdb_id"]))[:n],
        "surprising_exclusions_review":sorted(lost,key=lambda r:(-r["overall_score"],r["imdb_id"]))[:n],
        "lowest_score_current_lost":sorted(lost,key=lambda r:(r["overall_score"],r["imdb_id"]))[:n],
        "highest_score_guard_exclusions":guard_excluded[:n],
        "high_audience_weak_evidence_selected":[r for r in weak if qualifies(r,policy,threshold)][:n],
        "high_audience_weak_evidence_excluded":[r for r in weak if not qualifies(r,policy,threshold)][:n],
        "strong_non_audience_low_audience_share":sorted([r for r in strong if r["non_audience_score"]>=threshold],key=lambda r:(r["audience_share_pct"],-r["non_audience_score"],r["imdb_id"]))[:n],
        "strong_critical_examples":strong[:n],
        "recent_new":[r for r in new if r["year"]>=config["recent_year_start"]][:n],
        "older_new":[r for r in new if r["year"]<config["recent_year_start"]][:n],
        "positive_taste_sanity_check":[r for r in rows if r["taste_positive"]],
    }
    return {k:[{**public_row(r),"selected":qualifies(r,policy,threshold)} for r in group]
            for k,group in groups.items()}

SUMMARY_FIELDS=("policy","threshold","total_qualifying","newly_qualifying","current_retained",
    "current_lost","current_lost_due_score","current_lost_due_guard","new_excluded_by_guard","overlap_selected_pct","baseline_retention_pct","selected_audience_only",
    "selected_audience_dominant","new_audience_only","new_audience_dominant",
    "selected_incomplete_audience","recent_selected","recent_new",
    "new_known_positive_taste","lost_known_positive_taste","selected_known_positive_taste","positive_taste_retention_pct","selected_known_watched","new_known_watched")
FILM_FIELDS=("imdb_id","title","year","overall_rank","overall_score","audience_score",
    "non_audience_score","audience_share_pct","audience_complete","qualified","routes",
    "eligible_max_score","independent_non_audience_families","independent_non_audience_family_count",
    "raw_non_audience_family_count","contributing_scoring_family_count","major_composition",
    "audience_only","audience_dominant","critics_family_from_broad_ratings_only",
    "taste_positive","watch_state","source_points")

def table(headers,rows):
    return sim.table(headers,rows)

def summary_table(rows):
    return table(["Policy","Threshold","Total","New","Retained","Lost","Overlap %","New Audience>50%","Recent new"],
        [[r[k] for k in ("policy","threshold","total_qualifying","newly_qualifying",
          "current_retained","current_lost","overlap_selected_pct","new_audience_dominant","recent_new")]
         for r in rows])

def film_table(rows):
    return table(["Film","Year","Score","Audience","Non-audience","Families","Current","Selected","Taste","Watched"],
        [[r["title"],r["year"],r["overall_score"],r["audience_score"],r["non_audience_score"],
          r["independent_non_audience_family_count"],r["qualified"],r.get("selected"),
          r["taste_positive"],r["watch_state"]] for r in rows])

def markdown(result,config):
    policies=result["policies"]
    lines=["# Evidence Score qualification calibration","",
        "Research-only. Frozen PR #3 dataset: 1,909 films; 255 existing qualified IDs/routes.",
        "Audience 150, effective ceiling 1000, all other weights and canon correlation unchanged.",
        "No policy/threshold is selected; no production change or Radarr action.","",
        "## Definitions and limits","",
        "Thresholds use the published absolute score and inclusive >=. Family contribution means positive points. TSPDT/Sight&Sound count together as canon for B/C/E; raw counts remain available. Critics Groups remains its existing merged award/broad-critic family; a small positive broad-critic contribution counts, so family count is not evidence strength.","",
        "Existing qualification is a comparison label, not ground truth for quality. Overlap%=existing-qualified selected / all selected; retention%=selected baseline /255. These are agreement metrics, not validated precision/recall of user taste.","",
        "Recent=2020 onward; borderline=within 10 points, diagnostics only. Known watched films retain their qualification; annotations describe existing monitoring context. Current Radarr library and live addability were not queried.","",
        "No taste value affects scores/decisions; unknown films are unlabelled, not negative examples. The thirteen existing positive signals are all baseline-qualified; the 33 watched annotations are also all baseline-qualified. This small positive-only sample cannot validate newly admitted films or estimate taste precision. No anthology/combined-work award is allocated to components.","",
        "Nine Letterboxd gaps and 32 unresolved award-source records remain from PR#3. ReelDB HTTP 403 is unchanged; no live enrichment in this task. Scores with missing data remain observed lower evidence; upper bounds never fabricate ratings. Recent films have fewer historical-poll eligibility opportunities; thresholds are not renormalized.","",
        table(["Code","Research predicate"],POLICIES.items()),"",
        "## Distribution",""]
    cohorts=result["distribution"]
    lines += [table(["Statistic","All","Current qualified","Unqualified","Audience complete","Incomplete"],
        [[metric,*[(cohorts[c]["score_distribution"] or {}).get(metric) for c in
          ("all","currently_qualified","currently_unqualified","audience_complete","audience_incomplete")]]
         for metric in ("count","min","max","mean","median","stddev_population")]),""]
    for cohort in ("all","currently_qualified","currently_unqualified","audience_complete","audience_incomplete"):
        dist=cohorts[cohort]["score_distribution"]
        lines += ["### "+cohort.replace("_"," "),"",
            table(["Score band","Count"],cohorts[cohort]["detailed_score_bands"].items()),"",
            table(["Percentile","Score"],dist["percentiles"].items()),"",
            table(["Independent non-audience families","Count"],cohorts[cohort]["independent_non_audience_family_count"].items()),""]
    lines += ["## Score-only threshold summary","",
        summary_table([policies[key("score_only",t)]["summary"] for t in config["thresholds"]]),"",
        "Full loss lists: [score-only-losses.csv](score-only-losses.csv). Every policy includes distributions by year/family composition and incomplete-data sensitivity in calibration.json.","",
        "## All policy comparisons","",
        summary_table([policies[key(p,t)]["summary"] for t in config["thresholds"] for p in config["policies"]]),"",
        "## Numerical shortlist for product review","",
        "These four operating points span retention-first, broad guarded discovery and evidence-led replacement. They are review candidates, not a quality ranking or a selected production policy.","",
        summary_table([policies[key(s["policy"],s["threshold"])]["summary"] for s in config["shortlist"]]),""]
    for option in config["shortlist"]:
        ident=key(option["policy"],option["threshold"]);s=policies[ident]["summary"]
        lines += ["### "+ident,"",option["rationale"],"",
            f"Trade-off: {s['newly_qualifying']} new; {s['current_lost']} current losses; {s['new_audience_dominant']} audience-dominant new; {s['recent_new']} recent new. Known positive taste losses: {s['lost_known_positive_taste']}.",
            "Full lists: [new]("+ "candidates/"+ident+"-new.csv"+"), [lost](candidates/"+ident+"-lost.csv), [borderline](candidates/"+ident+"-borderline.csv).",""]
        example=result["shortlist_examples"][ident]
        for label in ("top_newly_admitted","borderline_above_score","borderline_below_score",
            "surprising_inclusions_review","surprising_exclusions_review","highest_score_guard_exclusions",
            "high_audience_weak_evidence_selected","high_audience_weak_evidence_excluded",
            "strong_non_audience_low_audience_share","recent_new","older_new"):
            lines += ["#### "+label.replace("_"," "),"",film_table(example[label]),""]
        lines += ["#### Existing positive taste sanity check","",film_table(example["positive_taste_sanity_check"]),""]
    lines += ["## Findings and sensitivity","",
        "At thresholds 200 and above, B/C/E select exactly the score-only set in this universe: family-count guards add no filtering. This is an observed dataset result, not a guarantee for future candidates.",
        "Audience has a 150-point cap: above 300, it cannot exceed50% of total, so D is mathematically redundant. At 300, exact 50% ties pass; observed B/C/D/E also match score-only.",
        "At 100, score-only admits 48 audience-only films; at 125, 9; at 150 and above, none observed. C becomes identical to score-only from 150 in this dataset.",
        "E matters at the lower thresholds. It removes weak single-family/audience-dominant cases while retaining some strong single-family films that B would reject; many multi-family audience-dominant cases remain.",
        "D can remove strong known/currently qualified films whose audience share exceeds 50%; low share is not proof of better recommendations. At 200 it loses 73 current films: 48 below threshold and 25 additional share-guard losses, while filtering only 9 new admissions. Examples include Howl\'s Moving Castle, Kill Bill: Vol. 1, Interstellar and Memories of Murder. Known watched losses include The Swamp, A.I. Artificial Intelligence and Platform. This is the explicit cost of the evidence-led comparator.",
        "A preserves every baseline film and therefore also its 49 already audience-dominant cases. New-admission dominance is reported separately from retained baseline dominance.","",
        "### Incomplete Audience sensitivity","",
        table(["Film","Observed","Upper possible","Missing","Thresholds potentially crossed"],
            [[r["title"],r["observed_score"],r["upper_possible_score"],", ".join(r["missing"]),
              ", ".join(str(t) for t in config["thresholds"] if r["observed_score"]<t<=r["upper_possible_score"])]
             for r in policies[key("score_only",config["thresholds"][0])]["incomplete_audience_sensitivity"]]),"",
        "All nine incomplete rows currently score below 100; none is within 10 points of the tested thresholds. Only four could theoretically cross 100 at the maximum missing Letterboxd contribution; none can reach 125. Therefore the four shortlisted options are unaffected by these nine Audience gaps under this upper bound. Other missing award/critic evidence has not been bounded here.",
        "Potential upper-bound crossings do not assert recovered ratings or hybrid eligibility. More audience can cause D/E to reject a film even while increasing its total score.","",
        "## Artifacts and reproduction","",
        "[calibration.json](calibration.json) contains full film records/decisions, all policy ID lists, year/composition distributions and sensitivity. [Per-film CSV](per-film-policies.csv), [threshold table](threshold-summary.csv), [policy table](policy-comparison.csv), [manifest](manifest.json).",
        "Run python qualification_calibration.py in this research worktree. Frozen input/code/config hashes are in manifest.json. No external API requests are required.",""]
    return "\n".join(lines)

def run(root):
    config=json.loads((root/CONFIG).read_text())
    payload=json.loads((root/SCORE).read_text())
    frozen=json.loads((root/"simulation-qualifiers.json").read_text())
    input_hashes=validate_baseline(root,config,payload,frozen)
    rows=annotate(payload["films"],json.loads((root/"backcatalog-details.json").read_text()))
    before_scores={r["imdb_id"]:r["overall_score"] for r in payload["films"]}
    policies={}
    for t in config["thresholds"]:
        for p in config["policies"]:
            policies[key(p,t)]=summarize(rows,p,t,config)
    selected_sets={ident:set(item["selected_ids"]) for ident,item in policies.items()}
    decisions=[{**public_row(r),"policies":{ident:r["imdb_id"] in ids
        for ident,ids in selected_sets.items()}} for r in rows]
    result={
        "mode":"research-qualification-calibration-v1","baseline_commit":config["baseline_commit"],
        "audience_cap":150,"effective_ceiling":1000,"production_changed":False,
        "final_policy":None,"final_threshold":None,"config":config,
        "baseline_qualified":frozen,
        "distribution":{
            "all":population(rows,config),
            "currently_qualified":population([r for r in rows if r["qualified"]],config),
            "currently_unqualified":population([r for r in rows if not r["qualified"]],config),
            "audience_complete":population([r for r in rows if r["audience_complete"]],config),
            "audience_incomplete":population([r for r in rows if not r["audience_complete"]],config)},
        "policies":policies,
        "taste_lens":{"source":"backcatalog-details.json, keyed by verified IMDb ID",
            "known_positive":[public_row(r) for r in rows if r["taste_positive"]],
            "known_watched":[r["imdb_id"] for r in rows if r["watch_state"]=="watched"],
            "used_for_scoring_or_gating":False,"negative_labels_inferred":False},
        "shortlist_examples":{key(s["policy"],s["threshold"]):examples(rows,s["policy"],s["threshold"],config) for s in config["shortlist"]},
        "films":decisions,
    }
    assert before_scores=={r["imdb_id"]:r["overall_score"] for r in rows}
    for t in config["thresholds"]:
        assert set(r["imdb_id"] for r in frozen)<=set(policies[key("A_keep_existing",t)]["selected_ids"])
    target=root/OUT;target.mkdir(parents=True,exist_ok=True)
    write_json(target/"calibration.json",result)
    summaries=[policies[key(p,t)]["summary"] for t in config["thresholds"] for p in config["policies"]]
    write_csv(target/"policy-comparison.csv",summaries,SUMMARY_FIELDS)
    write_csv(target/"threshold-summary.csv",[s for s in summaries if s["policy"]=="score_only"],SUMMARY_FIELDS)
    wide=[{**r,**r["policies"]} for r in decisions]
    write_csv(target/"per-film-policies.csv",wide,(*FILM_FIELDS,*policies))
    lost_rows=[{**public_row(r),"threshold":t,"policy":"score_only"} for t in config["thresholds"]
               for r in rows if r["qualified"] and not qualifies(r,"score_only",t)]
    write_csv(target/"score-only-losses.csv",lost_rows,("threshold","policy",*FILM_FIELDS))
    for option in config["shortlist"]:
        p,t=option["policy"],option["threshold"];ident=key(p,t)
        for suffix,selected in (
            ("new",[r for r in rows if qualifies(r,p,t) and not r["qualified"]]),
            ("lost",[r for r in rows if r["qualified"] and not qualifies(r,p,t)]),
            ("borderline",sorted([r for r in rows if abs(r["overall_score"]-t)<=config["borderline_window"]],key=lambda r:(r["overall_score"],r["imdb_id"])))):
            write_csv(target/"candidates"/(ident+"-"+suffix+".csv"),
                      [{**public_row(r),"selected":qualifies(r,p,t),"threshold":t} for r in selected],
                      (*FILM_FIELDS,"threshold","selected"))
    manifest={"baseline_commit":config["baseline_commit"],"input_sha256":input_hashes,
        "code_sha256":digest(root/"qualification_calibration.py"),"config_sha256":digest(root/CONFIG),
        "candidate_ids":[r["imdb_id"] for r in rows],"baseline_ids":[r["imdb_id"] for r in frozen],
        "family_weights":payload["family_weights"],"audience_cap":150,"effective_ceiling":1000,
        "policy_count":len(policies),"thresholds":config["thresholds"],
        "qualification_routes_preserved":True,"production_changed":False,
        "anthology_combined_work_allocation":False,"score_input_not_modified":True,
        "final_policy":None,"final_threshold":None}
    write_json(target/"manifest.json",manifest)
    (target/"summary.md").write_text(markdown(result,config),encoding="utf-8")
    return {"film_count":len(rows),"baseline_count":len(frozen),"policy_count":len(policies),
        "threshold_summary":[s for s in summaries if s["policy"]=="score_only"],
        "shortlist":[policies[key(s["policy"],s["threshold"])]["summary"] for s in config["shortlist"]],
        "top_new":{ident:example["top_newly_admitted"][:5] for ident,example in result["shortlist_examples"].items()},
        "positive_taste_count":len(result["taste_lens"]["known_positive"]),
        "known_watched_count":len(result["taste_lens"]["known_watched"])}

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",type=Path,default=Path("."))
    args=parser.parse_args()
    print(json.dumps(run(args.root),ensure_ascii=False,allow_nan=False))
