"""Regenerate the final Audience=150 research model and an identity-cleanup comparison."""
import copy, hashlib, json, statistics
from pathlib import Path
import audience_calibration_enrichment as ace
import audience_cap_simulation as sim
from identity_integrity import BASELINE, OUT

def coverage(rows):
    return {"candidates":len(rows),
            "IMDb":sum(r["audience_coverage"]["imdb"]["available"] for r in rows),
            "Letterboxd":sum(r["audience_coverage"]["letterboxd"]["available"] for r in rows),
            "complete_pairs":sum(r["audience_complete"] for r in rows)}

def top_change(before,after,n):
    b={r["imdb_id"]:r for r in before[:n]}
    a={r["imdb_id"]:r for r in after[:n]}
    common=b.keys() & a.keys()
    return {"size":n,"membership_changed":len(b.keys()-a.keys()),
            "left":[sim.compact(b[i]) for i in sorted(b.keys()-a.keys(),key=lambda i:b[i]["overall_rank"])],
            "entered":[sim.compact(a[i]) for i in sorted(a.keys()-b.keys(),key=lambda i:a[i]["overall_rank"])],
            "common_rank_changed":sum(a[i]["overall_rank"]!=b[i]["overall_rank"] for i in common),
            "largest_common_rank_change":max([abs(a[i]["overall_rank"]-b[i]["overall_rank"]) for i in common] or [0])}

def run(root):
    inputs=ace.load_inputs(root)
    fallback_path=root/OUT/"inputs/imdb-fallback.json"
    fallback=json.loads(fallback_path.read_text()) if fallback_path.exists() else json.loads((root/ace.OUT/"inputs/imdb-fallback.json").read_text())
    shared=sim.prepare_shared(inputs,fallback)
    for row in shared:
        source_records=(inputs[str(ace.es.AUDIENCE)]["ratings"].get(row["imdb_id"]) or {}).get("rating_provenance") or {}
        for source,record in source_records.items():
            if source in row["audience_coverage"] and row["audience_coverage"][source]["available"]:
                row["audience_coverage"][source]["origin"]=record["provider"]
                row["audience_coverage"][source]["source_provenance"]=record
    rows=sim.score_variant(shared,150)
    assert max(r["eligible_max_score"] for r in rows)==1000
    assert all(r["overall_score"]<=1000 for r in rows)
    before_payload=json.loads((root/ace.OUT/"audience_cap_150.json").read_text())
    before=before_payload["films"]
    by_before={r["imdb_id"]:r for r in before}
    by_after={r["imdb_id"]:r for r in rows}
    quals={r["imdb_id"]:r for r in inputs[str(ace.es.QUALIFIERS)]}
    assert all(r["qualified"]==(r["imdb_id"] in quals) and r["routes"]==(quals.get(r["imdb_id"]) or {}).get("routes",[]) for r in rows)
    identity=json.loads((root/OUT/"identity-audit.json").read_text())
    identity_corrections=json.loads((root/OUT/"identity-corrections.json").read_text())
    awards=json.loads((root/OUT/"award-identity-audit.json").read_text())
    movements=[]
    for iid in sorted(by_before.keys()|by_after.keys()):
        b,a=by_before.get(iid),by_after.get(iid)
        change={"imdb_id":iid,"title":(a or b)["title"],"year":(a or b)["year"],
                "status":"retained" if a and b else "added_by_identity_correction" if a else "removed_false_identity",
                "score_before":b["overall_score"] if b else None,"score_after":a["overall_score"] if a else None,
                "rank_before":b["overall_rank"] if b else None,"rank_after":a["overall_rank"] if a else None,
                "score_change":round(a["overall_score"]-b["overall_score"],2) if a and b else None,
                "rank_change":b["overall_rank"]-a["overall_rank"] if a and b else None,
                "family_changes":{key:round(a["source_points"].get(key,0)-b["source_points"].get(key,0),2)
                                  for key in set(a["source_points"])|set(b["source_points"])
                                  if a["source_points"].get(key,0)!=b["source_points"].get(key,0)} if a and b else {}}
        movements.append(change)
    pairs=[]
    for correction in identity_corrections:
        old,new=correction["old_imdb_id"],correction["imdb_id"]
        pairs.append({**correction,"source_record_before":sim.compact(by_before[old]),
                      "correct_film_after":sim.compact(by_after[new]),
                      "correct_film_already_in_before_universe":new in by_before,
                      "warning":"Source identity substitution; these are different films, not a same-film rating change"})
    hashes={str(path):hashlib.sha256((root/path).read_bytes()).hexdigest() for path in ace.INPUT_PATHS}
    for path in ("sources/tspdt-21c.json","sources/identity-overrides.json",
                 "sources/identity-audit/tmdb.json","sources/identity-audit/imdb-basics.json",
                 "film_identity.py","identity_integrity.py","award_identity_cleanup.py",
                 "integrity_rating_enrichment.py","integrity_research_score.py",
                 "audience_cap_simulation.py","evidence_score.py","broad_critic_score.py","canon_overlap_score.py"):
        hashes[path]=hashlib.sha256((root/path).read_bytes()).hexdigest()
    if fallback_path.exists():hashes[str(OUT/"inputs/imdb-fallback.json")]=hashlib.sha256(fallback_path.read_bytes()).hexdigest()
    manifest={"baseline":BASELINE,"audience_cap":150,"audience_weight":.75,"effective_evidence_ceiling":1000,
              "family_weights":sim.FAMILY_WEIGHTS,"canon_correlation":"Unchanged existing adjustment",
              "qualification_unchanged":True,"production_unchanged":True,
              "universe_before_sha256":sim.digest(sorted(by_before)),
              "universe_after_sha256":sim.digest(sorted(by_after)),
              "ids_added":sorted(by_after.keys()-by_before.keys()),"ids_removed":sorted(by_before.keys()-by_after.keys()),
              "inputs_sha256":hashes,"candidate_ids":sorted(by_after)}
    changed=[r for r in movements if r["score_change"] is not None and r["score_change"]!=0]
    ranks=[r for r in movements if r["rank_change"] is not None and r["rank_change"]!=0]
    comparison={"baseline":BASELINE,"model":"Audience=150; effective ceiling1000; unchanged other weights",
                "identity_audit_summary":{k:v for k,v in identity.items() if k!="records"},
                "coverage_before":coverage(before),"coverage_after":coverage(rows),
                "critics_gaps_before":awards["before"],"critics_gaps_after":awards["after"],
                "same_film_score_changes":len(changed),"same_film_rank_changes":len(ranks),
                "identity_substitutions":pairs,"top_50":top_change(before,rows,50),
                "top_100":top_change(before,rows,100),
                "biggest_score_changes":sorted(changed,key=lambda r:-abs(r["score_change"])),
                "biggest_rank_changes":sorted(ranks,key=lambda r:-abs(r["rank_change"])),
                "movements":movements,
                "missing_audience_after":[{"imdb_id":r["imdb_id"],"title":r["title"],"year":r["year"],
                                           "coverage":r["audience_coverage"]} for r in rows if not r["audience_complete"]],
                "distribution_before":sim.distribution(before),"distribution_after":sim.distribution(rows)}
    payload={"mode":"research-evidence-score-audience150-identity-cleanup","audience_cap":150,
             "current_score_ceiling":1000,"family_weights":sim.FAMILY_WEIGHTS,
             "film_count":len(rows),"universe_sha256":manifest["universe_after_sha256"],
             "qualification_unchanged":True,"production_unchanged":True,"films":rows}
    target=root/OUT
    ace.write_json(target/"evidence-score-150.json",payload)
    sim.write_csv(target/"evidence-score-150.csv",rows,("overall_rank","score_rank","imdb_id","title","year","overall_score","audience_score","non_audience_score","source_points","audience_complete","qualified","routes"))
    sim.write_csv(target/"before-score-150.csv",before,("overall_rank","score_rank","imdb_id","title","year","overall_score","audience_score","non_audience_score","audience_complete"))
    sim.write_csv(target/"score-rank-changes.csv",movements,("imdb_id","title","year","status","score_before","score_after","score_change","rank_before","rank_after","rank_change","family_changes"))
    ace.write_json(target/"comparison.json",comparison)
    ace.write_json(target/"manifest.json",manifest)
    (target/"comparison.md").write_text(markdown(comparison,identity,awards),encoding="utf-8")
    return {k:comparison[k] for k in ("coverage_before","coverage_after","critics_gaps_before","critics_gaps_after","same_film_score_changes","same_film_rank_changes","top_50","top_100")}

def markdown(c,identity,awards):
    def table(headers,rows):
        return sim.table(headers,rows)
    lines=["# Research data integrity: before and after","",
           "Audience=150 (0.75 × IMDb + Letterboxd), effective ceiling1000. Other family weights, canon correlation and qualification are unchanged. Research only; no production rollout.","",
           "## Identity audit",f"Audited {identity['audited']} TSPDT/backcatalog records; {identity['suspicious_count']} flagged for closer inspection. Counts: {identity['counts']}.","",
           "### Corrected identities",table(["TSPDT rank","Source film","Wrong ID","Correct ID"],[
               [r["tspdt_rank"],r["source"]["title"],r["before"]["imdb_id"],r["after"]["imdb_id"]]
               for r in identity["records"] if r["status"]=="corrected"]),"",
           "### All suspicious matches",
           table(["Rank","Source title","IMDb ID after","Classification","Flags"],[
               [r["tspdt_rank"],r["source"]["title"],r["after"]["imdb_id"],r["status"],", ".join(r["flags"])]
               for r in identity["records"] if r["suspicious"]]),"",
           "### Unresolved identities",table(["Rank","Title","Reason"],[
               [r["tspdt_rank"],r["source"]["title"],r["reason"]] for r in identity["records"] if r["status"]=="unresolved"]),"",
           "Metadata warnings remain visible for cuts, release dates, co-director omissions, and country definitions; identity confirmation does not rewrite those source fields.","",
           "## Audience coverage",table(["Measure","Before","After"],[[k,c["coverage_before"][k],c["coverage_after"][k]] for k in c["coverage_before"]]),"",
           "Missing components remain zero without renormalization. Missing data is not a claim that no Letterboxd page exists.","",
           table(["IMDb ID","Film","Missing"],[[r["imdb_id"],r["title"],", ".join(k for k,v in r["coverage"].items() if not v["available"])] for r in c["missing_audience_after"]]),"",
           "## Award-source identities",table(["Source","Unresolved before","After"],[[k,v,awards["after"][k]] for k,v in awards["before"].items()]),"",
           table(["Source","Title","Status","IMDb ID / reason"],[[r["source"],r["record"]["title"],r["status"],r.get("imdb_id") or r["reason"]] for r in awards["records"]]),"",
           "## Score and rank changes",
           f"{c['same_film_score_changes']} retained films change score; {c['same_film_rank_changes']} change ordinal rank. Substituted identities are shown separately because their before/after scores refer to different works.","",
           table(["Film","Score before","After","Delta","Rank before","After"],[[r["title"],r["score_before"],r["score_after"],r["score_change"],r["rank_before"],r["rank_after"]] for r in c["biggest_score_changes"]]),"",
           "### Largest ranking movements",table(["Film","Rank before","After","Movement","Score delta"],[[r["title"],r["rank_before"],r["rank_after"],r["rank_change"],r["score_change"]] for r in c["biggest_rank_changes"][:30]]),"",
           "### Top50 / top100",
           table(["Set","Membership changes","Common ranks changed","Largest rank change"],[[n,c["top_"+str(n)]["membership_changed"],c["top_"+str(n)]["common_rank_changed"],c["top_"+str(n)]["largest_common_rank_change"]] for n in (50,100)]),"",
           "The report gives numerical membership/order effects; materiality remains a product-review judgment.","",
           "### Distribution",table(["Metric","Before","After"],[[k,c["distribution_before"].get(k),c["distribution_after"].get(k)] for k in ["min","max","mean","median","stddev_population"]]),"",
           "Score percentiles and diagnostic-band counts are in comparison.json.", "",
           "## Provenance and reproduction",
           "See identity-audit.json for every source/metadata field and evidence URL; award-identity-audit.json for every source gap; rating-enrichment.json for attempted provider selectors; manifest.json for all inputs/code hashes.","",
           "Offline regeneration: python integrity_research_score.py. Existing audience-cap comparison artifacts remain historical baseline results. No scoring threshold has been selected.",""]
    return "\n".join(str(x) for x in lines)

if __name__=="__main__":print(json.dumps(run(Path("."))))
