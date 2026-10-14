"""Final research-only P225/P250 comparison using the deployed 224-film snapshot."""
import argparse
import copy
import hashlib
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path
import subprocess

import qualification_calibration as qc

CONFIG=Path("production-threshold-config.json")
OUT=Path("simulations/p225-vs-p250")
FAMILIES=tuple(qc.sim.FAMILY_WEIGHTS)+("audience",)
BANDS=((210,225),(225,240),(240,250),(250,265))

def selected(row, deployed_ids, threshold):
    """Only deployed qualification can grandfather a film."""
    return row["imdb_id"] in deployed_ids or Decimal(str(row["overall_score"]))>=Decimal(str(threshold))

def classification(row):
    score=Decimal(str(row["overall_score"]))
    return "naturally_ge250" if score>=250 else "naturally_ge225_lt250" if score>=225 else "neither_threshold"

def routes_map(rows):
    result={r["imdb_id"]:r["routes"] for r in rows}
    if len(result)!=len(rows):
        raise ValueError("Duplicate qualifier IDs")
    return result

def validate(root,config,payload,research,deployed,history):
    hashes=qc.validate_baseline(root,json.loads((root/qc.CONFIG).read_text()),payload,research)
    if routes_map(deployed)!=routes_map(json.loads(subprocess.check_output(
        ["git","show",config["deployed_commit"]+":simulation-qualifiers.json"],cwd=root))):
        raise ValueError("Deployed IDs/routes changed")
    if qc.digest(root/config["deployed_path"])!=config["deployed_sha256"] or len(deployed)!=224:
        raise ValueError("Frozen deployed snapshot changed")
    deployed_ids=set(routes_map(deployed));research_ids=set(routes_map(research))
    difference=research_ids-deployed_ids
    previous=json.loads((root/"simulations/qualification-calibration/verification.json").read_text())
    documented={r["id"] for r in previous["production_snapshot_comparison"]["only_research"]}
    if len(difference)!=31 or difference!=documented or difference!=set(history["records"]) or difference!=set(history["research_only_ids"]):
        raise ValueError("Research31 difference changed")
    if not deployed_ids<=research_ids or any(routes_map(research)[i]!=routes_map(deployed)[i] for i in deployed_ids):
        raise ValueError("Shared routes changed")
    current={r["imdb_id"]:r for r in research}
    for iid,record in history["records"].items():
        commit=record["introduction_commit"]
        first={r["imdb_id"]:r for r in json.loads(subprocess.check_output(
            ["git","show",commit+":simulation-qualifiers.json"],cwd=root))}
        if first.get(iid)!=record["first_qualification_record"]:
            raise ValueError("History first qualification mismatch")
        if not record["institutional_seed_already_present_before_introduction"] or not record["generator_unchanged_from_parent"]:
            raise ValueError("History explanation needs review")
        if (record.get("prior_generated_phase_b_record") or {}).get("qualified") is not False:
            raise ValueError("Prior qualification explanation needs review")
    fixed=[qc.SCORE,Path("simulation-qualifiers.json"),Path(config["deployed_path"]),
           Path("qualification_calibration.py"),qc.CONFIG,
           Path("simulations/qualification-calibration/calibration.json"),
           Path("simulations/qualification-calibration/verification.json")]
    for path in fixed:
        frozen=subprocess.check_output(["git","show",config["baseline_commit"]+":"+str(path)],cwd=root)
        if frozen!=(root/path).read_bytes():
            raise ValueError("Latest calibration baseline changed: "+str(path))
        hashes[str(path)]=qc.digest(root/path)
    hashes[config["history_path"]]=qc.digest(root/config["history_path"])
    return hashes

def statistic(values,bounds):
    values=sorted(values)
    if not values:return {"count":0,"min":None,"max":None,"mean":None,"percentiles":{},"bands":{}}
    def percentile(p):
        position=(len(values)-1)*p/100;lo=int(position);hi=min(lo+1,len(values)-1)
        return round(values[lo]+(values[hi]-values[lo])*(position-lo),2)
    return {"count":len(values),"min":min(values),"max":max(values),
        "mean":round(sum(values)/len(values),2),
        "percentiles":{str(p):percentile(p) for p in (10,25,50,75,90,95,99)},
        "bands":{str(lo)+"-<"+str(hi):sum(lo<=x<hi for x in values) for lo,hi in zip(bounds,bounds[1:])},
        "at_ceiling":sum(x==bounds[-1] for x in values)}

def group(rows,config):
    result=qc.population(rows,{"recent_year_start":config["recent_start"]})
    result["audience_share_distribution"]=statistic([r["audience_share_pct"] for r in rows],(0,10,25,50,75,100))
    result["families_contributing_films"]={f:sum(r["source_points"].get(f,0)>0 for r in rows) for f in FAMILIES}
    result["family_points_total"]={f:round(sum(r["source_points"].get(f,0) for r in rows),2) for f in FAMILIES}
    result["non_audience_minimum"]=min((r["non_audience_score"] for r in rows),default=None)
    return result

def public(row):
    fields=("imdb_id","title","year","overall_score","overall_rank","audience_score",
        "non_audience_score","audience_share_pct","audience_complete","audience_coverage",
        "eligible_max_score","source_points","source_evidence",
        "independent_non_audience_families","independent_non_audience_family_count",
        "raw_non_audience_family_count","major_composition","taste_positive","taste_signals",
        "watch_state","production_qualified","production_routes","research_255_qualified",
        "research_255_routes","recent","very_recent","P225","P250")
    return {f:row[f] for f in fields}

CSV_FIELDS=("title","year","imdb_id","overall_score","overall_rank","audience_score",
    "non_audience_score","audience_share_pct","independent_non_audience_families",
    "independent_non_audience_family_count","raw_non_audience_family_count","source_points",
    *FAMILIES,"production_qualified","production_routes","research_255_qualified",
    "research_255_routes","recent","very_recent","taste_positive","taste_signals","watch_state",
    "audience_complete","eligible_max_score","P225","P250","source_evidence")

def csv_rows(rows):
    return [{**public(r),**r["source_points"]} for r in rows]

def history_reason(record):
    routes=record["first_qualification_record"]["routes"]
    reason="Existing institutional seed; previous generated snapshot had no IMDb/Letterboxd ratings and did not qualify. Ratings enrichment then activated the unchanged Phase B "
    if "convergence" in routes:
        reason+="outside-TSPDT convergence rule:institutional_strength>=1, both sources strong/broad, at least one exceptional."
    elif "corroboration" in routes:
        reason+="outside-TSPDT corroboration rule:institutional_strength>=2 and at least one source strong/broad."
    else:
        reason+="qualification route:"+", ".join(routes)
    return reason+" It was research regeneration, not Evidence Score qualification or deployment."

def research_review(rows,history):
    result=[]
    for row in rows:
        iid=row["imdb_id"]
        if iid not in history["records"]:continue
        origin=history["records"][iid]
        result.append({**public(row),"classification":classification(row),
            "naturally_P225":row["overall_score"]>=225,"naturally_P250":row["overall_score"]>=250,
            "below_225_by":round(max(0,225-row["overall_score"]),2),
            "research_grandfathering_needed_P225":row["overall_score"]<225,
            "research_grandfathering_needed_P250":row["overall_score"]<250,
            "included_only_by_research_255_below_P225":row["overall_score"]<225,
            "introduction_commit":origin["introduction_commit"],
            "first_usable_audience_cache_commit":origin.get("first_usable_audience_cache_commit"),
            "original_introduction_routes":origin["first_qualification_record"]["routes"],
            "institutional_seed_signals":origin["institutional_seed"]["signals"],
            "institutional_strength_at_introduction":origin["institutional_seed"]["institutional_strength"],
            "why_entered":history_reason(origin)})
    return result

def reconcile(rows,deployed_ids,research_ids,old,threshold):
    name="P"+str(threshold)
    current={r["imdb_id"] for r in rows if r[name]}
    previous=set(old["policies"][qc.key("A_keep_existing",threshold)]["selected_ids"])
    calculated={r["imdb_id"] for r in rows if r["imdb_id"] in research_ids or r["overall_score"]>=threshold}
    if previous!=calculated:raise ValueError("Previous A results mismatch")
    extra=research_ids-deployed_ids
    removed={r["imdb_id"] for r in rows if r["imdb_id"] in extra and r["overall_score"]<threshold}
    natural=extra-removed
    assert previous-current==removed and current<=previous
    old_new=len(previous-research_ids);new_new=len(current-deployed_ids)
    assert len(current)==len(previous)-len(removed)
    assert new_new==old_new+len(natural)
    return {"threshold":threshold,"old_policy":"A"+str(threshold),"old_baseline":255,
        "old_total":len(previous),"old_new":old_new,"new_policy":name,"new_baseline":224,
        "new_total":len(current),"new_new":new_new,"research31_naturally_qualifying":len(natural),
        "research31_removed_from_old_total":len(removed),
        "total_equation":f"{len(previous)} - {len(removed)} = {len(current)}",
        "new_equation":f"{old_new} + {len(natural)} = {new_new}",
        "removed_ids":sorted(removed),"research31_natural_ids":sorted(natural)}

def shortlists(cohort,rows,config):
    sorted_nonaud=sorted(cohort,key=lambda r:(-r["non_audience_score"],-r["overall_score"],r["imdb_id"]))
    popular=sorted(cohort,key=lambda r:(-(r["audience_coverage"]["imdb"].get("votes") or 0),-r["overall_score"],r["imdb_id"]))
    festival=[r for r in sorted_nonaud if r["source_points"].get("european_recognition",0)>0 or r["source_points"].get("independent_cinema",0)>0]
    scarce=sorted(cohort,key=lambda r:(r["source_points"].get("critics_groups_consensus",0),-r["audience_share_pct"],-r["overall_score"],r["imdb_id"]))
    heavy=sorted(cohort,key=lambda r:(-r["audience_share_pct"],-r["overall_score"],r["imdb_id"]))
    groups={"strongest_by_score":cohort[:8],"most_questionable_for_review_high_share":heavy[:5],
        "most_questionable_for_review_low_modeled_critic_points":scarce[:5],
        "festival_cinephile_evidence":festival[:8],"mainstream_popular_vote_volume":popular[:8],
        "audience_heavy":heavy[:5],"low_audience_strong_other_evidence":sorted_nonaud[:8]}
    return {name:[public(r) for r in group] for name,group in groups.items()}

REPRESENTATIVE_IDS=("tt0248845","tt1136608","tt0970179","tt6217608","tt1174732","tt2762506",
    "tt5649144","tt5363618","tt2380307","tt8399288","tt4772188","tt19652910","tt17526714",
    "tt7282468","tt27714581","tt0408664","tt0976051","tt0421715")

def run(root):
    config=json.loads((root/CONFIG).read_text())
    payload=json.loads((root/qc.SCORE).read_text())
    research=json.loads((root/"simulation-qualifiers.json").read_text())
    deployed=json.loads((root/config["deployed_path"]).read_text())
    history=json.loads((root/config["history_path"]).read_text())
    hashes=validate(root,config,payload,research,deployed,history)
    production_routes=routes_map(deployed);deployed_ids=set(production_routes);research_ids=set(routes_map(research))
    rows=qc.annotate(payload["films"],json.loads((root/"backcatalog-details.json").read_text()))
    for r in rows:
        iid=r["imdb_id"];r["production_qualified"]=iid in deployed_ids
        r["production_routes"]=production_routes.get(iid,[])
        r["research_255_qualified"]=r["qualified"];r["research_255_routes"]=r["routes"]
        r["recent"]=r["year"]>=config["recent_start"];r["very_recent"]=r["year"]>=config["very_recent_start"]
        r["P225"]=selected(r,deployed_ids,225);r["P250"]=selected(r,deployed_ids,250)
    old=json.loads((root/"simulations/qualification-calibration/calibration.json").read_text())
    cohort=[r for r in rows if r["P225"] and not r["P250"] and not r["production_qualified"]]
    assert all(225<=r["overall_score"]<250 for r in cohort)
    summaries={}
    for threshold in (225,250):
        name="P"+str(threshold);chosen=[r for r in rows if r[name]]
        new=[r for r in chosen if not r["production_qualified"]]
        assert sum(r["production_qualified"] for r in chosen)==224
        summaries[name]={"threshold":threshold,"total":len(chosen),"production_retained":224,
            "production_lost":0,"new":len(new),"audience_dominant_new":sum(qc.audience_dominant(r) for r in new),
            "audience_only_new":sum(r["audience_only"] for r in new),
            "fewer_than_two_non_audience_families_new":sum(len(qc.family_keys(r))<2 for r in new),
            "recent_selected":sum(r["recent"] for r in chosen),"recent_new":sum(r["recent"] for r in new),
            "selected_population":group(chosen,config),"new_population":group(new,config),
            "new_ids":[r["imdb_id"] for r in new],"selected_ids":[r["imdb_id"] for r in chosen],
            "audience_dominant_newcomers":[public(r) for r in new if qc.audience_dominant(r)],
            "very_recent_institutional":[public(r) for r in new if r["very_recent"] and r["source_points"].get("us_institutional",0)>0],
            "festival_canon_below_threshold":[public(r) for r in rows if not r["production_qualified"] and threshold-15<=r["overall_score"]<threshold and
                (r["source_points"].get("tspdt_21c",0)>0 or r["source_points"].get("european_recognition",0)>0)][:15]}
    assert set(summaries["P250"]["selected_ids"])<=set(summaries["P225"]["selected_ids"])
    review=research_review(rows,history)
    classes=dict(Counter(r["classification"] for r in review))
    reconciliation=[reconcile(rows,deployed_ids,research_ids,old,t) for t in (225,250)]
    representatives=[r for r in cohort if r["imdb_id"] in REPRESENTATIVE_IDS]
    assert 10<=len(representatives)<=20
    result={"mode":"final-production-baseline-threshold-comparison","baseline_commit":config["baseline_commit"],
        "deployed_commit":config["deployed_commit"],"authoritative_baseline":224,
        "research255_diagnostic_only":True,"audience_cap":150,"effective_ceiling":1000,
        "score_changed":False,"production_changed":False,"final_threshold":None,
        "policies":summaries,"P225_only_count":len(cohort),"P225_only":[public(r) for r in cohort],
        "P225_only_population":group(cohort,config),"research31":review,"research31_classification":classes,
        "baseline_reconciliation":reconciliation,"shortlists":shortlists(cohort,rows,config),
        "representatives":[public(r) for r in representatives],"films":[public(r) for r in rows],
        "diagnostic_definitions":{"independent_families":"Positive point families, canon combined; not a guard",
            "recent":">="+str(config["recent_start"]),"very_recent":">="+str(config["very_recent_start"]),
            "mainstream_popular":"Descending frozen IMDb vote volume; no genre/popularity gate",
            "questionable":"Highest Audience share or lowest modeled critic-family points; manual discussion, not negative labels"},
        "baseline_production_routes":production_routes,
        "history_explanation":"All 31 institutional seeds pre-existed. Previously generated snapshots had no Audience ratings; cache enrichment activated unchanged Phase B convergence/corroboration rules. No introduction commit is an ancestor of deployed c7."}
    target=root/OUT;target.mkdir(parents=True,exist_ok=True)
    qc.write_json(target/"comparison.json",result)
    qc.write_csv(target/"per-film.csv",csv_rows(rows),CSV_FIELDS)
    for t in (225,250):
        name="P"+str(t)
        qc.write_csv(target/(name+"-new.csv"),csv_rows([r for r in rows if r[name] and not r["production_qualified"]]),CSV_FIELDS)
        qc.write_csv(target/("borderline-"+name+".csv"),csv_rows([r for r in rows if abs(r["overall_score"]-t)<=15]),CSV_FIELDS)
    qc.write_csv(target/"P225-only-vs-P250.csv",csv_rows(cohort),CSV_FIELDS)
    qc.write_csv(target/"research-31-review.csv",[{**r,**r["source_points"]} for r in review],(*CSV_FIELDS,
        "classification","naturally_P225","naturally_P250","below_225_by",
        "research_grandfathering_needed_P225","research_grandfathering_needed_P250",
        "included_only_by_research_255_below_P225","original_introduction_routes",
        "introduction_commit","first_usable_audience_cache_commit",
        "institutional_seed_signals","institutional_strength_at_introduction","why_entered"))
    for low,high in BANDS:
        qc.write_csv(target/f"borderline-band-{low}-{high}.csv",csv_rows([r for r in rows if low<=r["overall_score"]<high]),CSV_FIELDS)
    qc.write_csv(target/"baseline-reconciliation.csv",reconciliation,("threshold","old_baseline","old_total","old_new",
        "new_baseline","new_total","new_new","research31_naturally_qualifying","research31_removed_from_old_total","total_equation","new_equation"))
    manifest={"baseline_commit":config["baseline_commit"],"deployed_commit":config["deployed_commit"],
        "input_sha256":hashes,"implementation_sha256":qc.digest(root/"production_threshold_calibration.py"),
        "config_sha256":qc.digest(root/CONFIG),"candidate_ids":sorted(r["imdb_id"] for r in rows),
        "production_routes":production_routes,"research_only_ids":sorted(research_ids-deployed_ids),
        "audience_cap":150,"effective_ceiling":1000,"family_weights":payload["family_weights"],
        "all_scores_unchanged":True,"deployed_224_preserved":True,"research31_not_grandfathered":True,
        "canon_adjustment_unchanged":True,"anthology_allocation":False,"final_threshold":None,"production_changed":False}
    qc.write_json(target/"manifest.json",manifest)
    (target/"summary.md").write_text(markdown(result,config),encoding="utf-8")
    return {"policies":{k:{f:v[f] for f in ("total","production_retained","new","audience_dominant_new","recent_selected","recent_new","audience_only_new","fewer_than_two_non_audience_families_new")} for k,v in summaries.items()},
        "P225_only_count":len(cohort),"research31_classification":classes,"baseline_reconciliation":reconciliation,
        "P225_only_titles":[r["title"] for r in cohort],"representatives":[r["title"] for r in representatives]}

def film_table(rows,why=False):
    headers=["Film","Year","Score","Rank","Audience","Other","Audience%","Families","Prod224","Research 255"]
    cells=[[r["title"],r["year"],r["overall_score"],r["overall_rank"],r["audience_score"],
            r["non_audience_score"],r["audience_share_pct"],"+".join(r["independent_non_audience_families"]),
            r["production_qualified"],r["research_255_qualified"]] for r in rows]
    return qc.table(headers,cells)

def markdown(result,config):
    p=result["policies"];r=result["baseline_reconciliation"]
    lines=["# Final threshold comparison: P225 vs P250","",
        "Authoritative grandfathered baseline: 224 deployed films at c7a4582. Research 255 is diagnostic only; its 31 additions are not automatically retained.",
        "Frozen 1,909 Evidence Scores; Audience 150, ceiling 1000, weights/canon correlation and anthology attribution unchanged. Only the threshold differs. No final threshold chosen; no deployment or Radarr behavior change.","",
        "## Policy totals","",
        qc.table(["Policy","Total","Production retained","New","Audience-dominant new","Recent selected","Recent new"],
          [[k,*[v[f] for f in ("total","production_retained","new","audience_dominant_new","recent_selected","recent_new")]] for k,v in p.items()]),"",
        "Recent means 2020 onward, matching previous calibration. Very recent means 2024 onward for examples only. These are diagnostics, not guards.","",
        "## Exact baseline reconciliation","",
        qc.table(["Threshold","Old A total","Old new vs 255","P total","P new vs 224","Naturally qualifying research31","Removed legacy-only"],
          [[v[f] for f in ("threshold","old_total","old_new","new_total","new_new","research31_naturally_qualifying","research31_removed_from_old_total")] for v in r]),"",
        "\n".join(f"- {v['new_policy']}: total {v['total_equation']}; new admissions {v['new_equation']}." for v in r),"",
        "Lower total and higher newcomer count can coexist: research-only legacy inclusions below the threshold disappear, while research-only films meeting the score now count as newcomers to actual production.",
        "The old A225/A250 difference was 33; the true P225/P250 difference is 36 because Sound of Metal, Coco, The Salesman were previously grandfathered at both thresholds.","",
        "## P225-only newcomers","",
        f"{result['P225_only_count']} films have score 225–<250 and are not in deployed 224. Sorted by score descending, using frozen overall rank for ties.",
        film_table(result["P225_only"]),"",
        "Full family columns, source evidence, production/research routes and watched/taste annotations are in [P225-only-vs-P250.csv](P225-only-vs-P250.csv).",""]
    for name,rows in result["shortlists"].items():
        lines += ["### "+name.replace("_"," "),"",film_table(rows),""]
    lines += ["Questionable means a discussion focus: high Audience share or low modeled Critics Groups points. It is not a negative quality label. Mainstream/popular examples use frozen IMDb vote volume, not inferred genre. Festival/cinephile examples use positive European/Independent evidence; categories overlap.","",
        "## Research-only 31: no implicit grandfathering","",
        qc.table(["Classification","Count"],result["research31_classification"].items()),"",
        qc.table(["Film","IMDb","Score","Rank","Original research routes","Natural225","Natural250","Shortfall225","Classification"],
          [[x["title"],x["imdb_id"],x["overall_score"],x["overall_rank"],", ".join(x["research_255_routes"]),
            x["naturally_P225"],x["naturally_P250"],x["below_225_by"],x["classification"]] for x in result["research31"]]),"",
        "The 20 below 225 are included only by the old research qualifier flag under both A policies; neither P policy admits them. Three in 225–<250 need score 225, not legacy protection. Eight >=250 qualify naturally under both.","",
        "### How each entered the research comparator","",
        "All 31 already existed as institutional seeds. The preceding generated Phase B records lacked IMDb and Letterboxd ratings and were unqualified. Cache enrichment then caused the unchanged outside-TSPDT rules to qualify them:",
        "- Convergence: institutional strength>=1, both audience sources strong/broad, at least one exceptional.",
        "- Corroboration: institutional strength>=2, at least one audience source strong/broad, when no other route qualified.",
        "These are historical legacy rules, not new P225/P250 guards and not the final Evidence Score.",
        "No Man's Land entered at 0e0c822 after cache 4aaacb7; the other 30 entered at 0c3b8f7 after cache 662de6d. Neither introduction is an ancestor of deployed c7a4582. The generator did not change in either introduction commit.","",
        qc.table(["Film","Introduction","First usable cache","Institutional seed","Strength","Historical reason"],
          [[x["title"],x["introduction_commit"][:7],(x["first_usable_audience_cache_commit"] or "")[:7],
            " + ".join(x["institutional_seed_signals"]),x["institutional_strength_at_introduction"],x["why_entered"]] for x in result["research31"]]),"",
        "Exact first records, prior unqualified snapshots, rating/count observations, original thresholds, script/source hashes and commit provenance are frozen in [inputs/research31-history.json](inputs/research31-history.json). No values were inferred or refreshed.","",
        "## Selected and newcomer distributions",""]
    for name,policy in p.items():
        lines += ["### "+name,""]
        for population_key in ("selected_population","new_population"):
            pop=policy[population_key];dist=pop["score_distribution"];share=pop["audience_share_distribution"]
            lines += ["#### "+population_key.replace("_"," "),"",
                qc.table(["Statistic","Score","Audience share%"],
                  [[metric,dist.get(metric),share.get(metric)] for metric in ("count","min","max","mean")]+
                  [["p"+pc,dist["percentiles"].get(pc),share["percentiles"].get(pc)] for pc in ("10","25","50","75","90","95","99")]),"",
                qc.table(["Year","Films"],pop["year_counts"].items()),"",
                qc.table(["Family contributing","Films","Total points"],[[f,pop["families_contributing_films"][f],pop["family_points_total"][f]] for f in FAMILIES]),"",
                qc.table(["Independent non-audience families","Films"],pop["independent_non_audience_family_count"].items()),"",
                qc.table(["Score band","Films"],pop["detailed_score_bands"].items()),"",
                qc.table(["Audience-share band","Films"],share["bands"].items()),"",
                "Complete major-family composition counts and all distributions are in comparison.json. Canon is combined only for diagnostic family counts; points remain unchanged.",""]
    lines += ["## Borderline analysis","",
        "Both inclusive ±15 windows are published: [225](borderline-P225.csv), [250](borderline-P250.csv). Band files use lower-inclusive/upper-exclusive boundaries:210–<225,225–<240,240–<250,250–<265.",
        "Production films below threshold remain selected under both policies. A score band is not an exclusion list; inspect Prod224/P225/P250 flags.",""]
    for low,high in BANDS:
        band=[x for x in result["films"] if low<=x["overall_score"]<high]
        lines += ["### "+str(low)+"–<"+str(high),"",
            film_table(band),"","[Full family breakdown](borderline-band-"+str(low)+"-"+str(high)+".csv)",""]
    lines += ["## Quality sanity checks","",
        "Neither policy creates Audience-only newcomers or newcomers with fewer than two positive independent non-audience families in this dataset. No one very weak non-audience source plus large Audience score passes. This is observed evidence, not an added guard or a guarantee for future data.",
        "Audience dominance remains explicitly present; it is not silently excluded. Exact>50% uses points, not a rounded percent. A marginal 50.07% is different from pure Audience-only evidence.",""]
    for name,policy in p.items():
        lines += ["### "+name+" audience-dominant newcomers","",film_table(policy["audience_dominant_newcomers"]),"",
            "### "+name+" very recent with US institutional evidence","",film_table(policy["very_recent_institutional"][:10]),"",
            "### "+name+" festival/canon non-production films just below threshold","",film_table(policy["festival_canon_below_threshold"]),""]
    lines += ["Both preserve all known deployed watch/taste examples. Taste/watch annotations never affect scores or P flags. The previous 13 positive signals are a small positive-only sample, not preference ground truth for 36 newcomers.",
        "Very recent films have less historical-poll eligibility; eligible_max_score is exposed, but no normalization or age correction is applied.",
        "Nine missing Letterboxd components remain from PR #3; their prior bound cannot reach 125, so they cannot change P225/P250. Remaining award/critic gaps are not bounded. Small Axe and combined Nymphomaniac stay unallocated.","",
        "## Artifacts and reproduction","",
        "[comparison.json](comparison.json), [per-film.csv](per-film.csv), [P225-new.csv](P225-new.csv), [P250-new.csv](P250-new.csv), [research-31-review.csv](research-31-review.csv), [baseline-reconciliation.csv](baseline-reconciliation.csv), [manifest.json](manifest.json).",
        "Run python production_threshold_calibration.py through SSH in this worktree. Inputs/code/config hashes are frozen; no enrichment or Radarr API calls. Full suite and byte-for-byte checks are recorded in the engineering handoff.","",
        "### Product review summary","",
        "**Strongest argument for 225:** it adds 36 additional non-production films with real canon/festival/institutional support, including Hedwig and the Angry Inch, The Rider, Bacurau,The Florida Project, Memoria, EO and Sound of Metal. The delta is not Audience-only.",
        "**Strongest argument for 250:** a smaller 127-newcomer expansion rather than 163, excluding the entire 225–249.99 cohort and two additional audience-dominant newcomers. It is a clearer numerical margin, at the cost of omitting those supported discoveries. No measured taste precision establishes that 250 is better.",
        f"**Practical difference:** {result['P225_only_count']} films; P225={p['P225']['total']} total/{p['P225']['new']} new; P250={p['P250']['total']} total/{p['P250']['new']} new. All 224 production films retained. The 18 representatives below span that difference.","",
        film_table(result["representatives"]),"",
        "**Manual discussion:** Coco and Nobody Knows carry >50% Audience in the delta; The Reader and The Curious Case of Benjamin Button have low modeled critic-family points despite substantial institutional evidence. Flow, The Substance, Sentimental Value show recent-film eligibility limits. The 20 research-only films below 225 are not admitted and would need an explicit later grandfathering decision.",
        "Selected/new means hypothetical qualification, not live library absence or downloadability. No final threshold is chosen; the user and ChatGPT make that product decision.",""]
    return "\n".join(lines)

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--root",type=Path,default=Path("."))
    args=parser.parse_args();print(json.dumps(run(args.root),ensure_ascii=False,allow_nan=False))
