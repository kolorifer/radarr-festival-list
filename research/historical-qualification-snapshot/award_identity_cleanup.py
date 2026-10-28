"""Repair explicit award-title aliases inside the existing research universe."""
import json
from pathlib import Path
import audience_calibration_enrichment as ace
import evidence_sources_extra as extra
from identity_integrity import baseline, OUT

ALIASES = {"nsfc_best_picture":[["Pan's Labyrinth (El laberinto del fauno)",2006,"tt0457430"],["Waltz with Bashir (Vals im Bashir)",2008,"tt1185616"],["Goodbye to Language (Adieu au Langage)",2014,"tt2400275"],["Parasite (Gisaengchung)",2019,"tt6751668"]],"lafca_best_film":[["Crouching Tiger, Hidden Dragon (Wo hu cang long)",2000,"tt0190332"]],"efa_best_film":[["Hidden",2005,"tt0387898"],["BPM (Beats per Minute)",2017,"tt6135348"],["Compartment No. 6",2021,"tt10262648"]],"critics_choice_best_picture":[["Lord of the Rings: The Fellowship of the Ring",2001,"tt0120737"],["Lord of the Rings: The Two Towers",2002,"tt0167261"],["Lord of the Rings: The Return of the King",2003,"tt0167260"],["Master and Commander",2003,"tt0311113"],["Sweeney Todd",2007,"tt0408236"],["Birdman",2014,"tt2562232"],["Star Wars: The Force Awakens",2015,"tt2488496"]]}

def apply(root):
    path=root/"sources/evidence-families.json"
    snapshot=json.loads(path.read_text())
    original=baseline(root,path.name if path.parent==root else "sources/evidence-families.json")
    registry_path=root/"sources/identity-overrides.json"
    registry=json.loads(registry_path.read_text())
    cc_path=root/"sources/critics-choice-best-picture.json"
    cc=json.loads(cc_path.read_text())
    records=[]
    for source, rows in original["unresolved_extra_awards"].items():
        index={(title,year):iid for title,year,iid in ALIASES.get(source,[])}
        remaining=[]
        for row in rows:
            year=row.get("year") or row.get("film_year_hint")
            iid=index.get((row["title"],year))
            if not iid or iid not in snapshot["films"]:
                reason=("Anthology award; allocation to individual Small Axe films requires a product decision"
                        if row["title"]=="Small Axe"
                        else "Award covers both volumes/director cut; a single-film allocation is not inferred"
                        if row["title"].startswith("Nymphomaniac")
                        else "Not an obvious alias for an existing candidate; retained outside-universe/identity review")
                remaining.append(row)
                records.append({"source":source,"record":row,"status":"unresolved","reason":reason})
                continue
            film=snapshot["films"][iid]
            spec=extra.EXTRA_SOURCES[source]
            family=spec["family"]
            points=spec["winner_points"] if row["winner"] else spec["nominee_points"]
            label=spec["label"]+(" (winner)" if row["winner"] else " (nominee)")
            labels=film.setdefault("family_evidence",{}).setdefault(family,[])
            if label not in labels:
                scores=film.setdefault("family_scores",{})
                scores[family]=round(min(100,float(scores.get(family) or 0)+points),2)
                labels.append(label)
            mapping={"source_title":row["title"],"source_year":year,"imdb_id":iid,
                     "title":film["title"],"year":film["year"],"source":source,
                     "reason":"Explicit source-title alias to verified existing film identity",
                     "evidence_urls":[row.get("source_url") or spec["url"],
                                      "https://www.imdb.com/title/"+iid+"/"]}
            if not any(r["source_title"]==mapping["source_title"] and r["source_year"]==year for r in registry["awards"]):
                registry["awards"].append(mapping)
            records.append({"source":source,"record":row,"status":"corrected","imdb_id":iid,
                            "family":family,"points":points,"evidence":label})
            if source=="critics_choice_best_picture" and not any(r["imdb_id"]==iid for r in cc["films"]):
                cc["films"].append({"imdb_id":iid,"title":film["title"],"year":film["year"],
                                   "winner":row["winner"],"ceremony_year":row["ceremony_year"],
                                   "source_url":row["source_url"]})
        snapshot["unresolved_extra_awards"][source]=remaining
        meta=snapshot["extra_award_sources"][source]
        meta["unresolved"]=len(remaining)
        meta["resolved"]=int(original["extra_award_sources"][source]["resolved"])+len(rows)-len(remaining)
        if source=="critics_choice_best_picture":
            cc["unresolved"]=remaining
            cc["resolved"]=len(cc["films"])
    cc["films"].sort(key=lambda r:(r["year"],r["title"]))
    ace.write_json(path,snapshot)
    ace.write_json(cc_path,cc)
    ace.write_json(registry_path,registry)
    report={"before":{k:len(v) for k,v in original["unresolved_extra_awards"].items()},
            "after":{k:len(v) for k,v in snapshot["unresolved_extra_awards"].items()},
            "corrected":sum(r["status"]=="corrected" for r in records),"records":records,
            "candidate_universe_expansion":False,"weights_unchanged":True}
    ace.write_json(root/OUT/"award-identity-audit.json",report)
    return {k:v for k,v in report.items() if k!="records"}

if __name__=="__main__":print(json.dumps(apply(Path("."))))
