"""Reproducible TSPDT identity audit and explicitly scoped data repair."""
import copy, json, subprocess
from pathlib import Path
import audience_calibration_enrichment as ace
import film_identity as fi
import evidence_sources as es

BASELINE = "4d7943b6f4a2cff3b4ddc38fb8ff096747efc3bf"
OUT = Path("simulations/data-identity-integrity")
CORRECTIONS = {
    290: ("tt11416746", "Time", 2020),
    338: ("tt2562232", "Birdman or (The Unexpected Virtue of Ignorance)", 2014),
    509: ("tt0806125", "La Morte rouge", 2006),
    603: ("tt0278731", "Spider", 2002),
    897: ("tt12913444", "The Inheritance", 2020),
}

def baseline(root, path):
    return json.loads(subprocess.check_output(
        ["git", "show", BASELINE + ":" + str(path)], cwd=root, text=True))

def effective_metadata(tmdb):
    return tmdb.get("episode_metadata") or tmdb

def audit(root):
    source = json.loads((root / "sources/tspdt-21c.json").read_text())
    before = baseline(root, "backcatalog-details.json")
    source_by_rank = {r["rank"]: r for r in source}
    tmdb = json.loads((root / "sources/identity-audit/tmdb.json").read_text())["films"]
    basics = json.loads((root / "sources/identity-audit/imdb-basics.json").read_text())["films"]
    audit_rows = []
    for row in sorted(before["candidates"], key=lambda r: r["tspdt_rank"]):
        s = source_by_rank[row["tspdt_rank"]]
        target_id, title, year = CORRECTIONS.get(s["rank"], (row["imdb_id"], row["title"], row["year"]))
        official = basics.get(target_id) or {}
        m = effective_metadata(tmdb.get(target_id) or {})
        imdb_year = official.get("startYear")
        if str(imdb_year).isdigit():
            year = int(imdb_year)
        flags = []
        if fi.normalized(s["title"]) != fi.normalized(row["title"]):
            flags.append("source_resolved_title_difference")
        if s["year"] != row["year"]:
            flags.append("source_resolved_year_difference")
        if len(fi.normalized(s["title"])) <= 7:
            flags.append("short_common_title")
        conflicts = fi.supporting_conflicts(s, effective_metadata(tmdb.get(row["imdb_id"]) or {}))
        flags.extend(conflicts)
        if row["imdb_id"] in basics and basics[row["imdb_id"]]["titleType"] not in ("movie","short","documentary","tvMovie","tvEpisode","video"):
            flags.append("non_film_imdb_type")
        official_titles = {fi.normalized(official.get(k)) for k in ("primaryTitle", "originalTitle")}
        metadata_titles = {fi.normalized(m.get(k)) for k in ("title", "original_title")} | {fi.normalized(x) for x in m.get("aliases", [])}
        alias_valid = fi.normalized(s["title"]) in official_titles | metadata_titles
        director_valid = fi.director_matches(s["director"], m.get("directors"))
        # Some metadata omits a co-director; exact title/year/runtime plus a
        # credited source director corroborates this work without inventing credit.
        if not director_valid and alias_valid and official.get("startYear")==str(s["year"]):
            import re
            source_directors = re.split(r"\s*&\s*|\s+and\s+|/", s["director"])
            partial = any(fi.director_matches(part, m.get("directors")) for part in source_directors)
            runtime = m.get("runtime")
            if partial and isinstance(runtime,(int,float)) and abs(runtime-s["runtime"])<=max(5,s["runtime"]*.1):
                director_valid=True
                flags.append("partial_codirector_credit")
        # IMDb year is the work's start year; TMDb may use a later theatrical date.
        official_year_valid = str(imdb_year).isdigit() and abs(int(imdb_year)-s["year"]) <= 1
        title_valid = alias_valid or (director_valid and isinstance(m.get("runtime"), (int,float))
                                     and abs(m["runtime"]-s["runtime"]) <= max(5,s["runtime"]*.1))
        if not alias_valid:
            flags.append("title_alias_requires_corroboration")
        if not director_valid:
            flags.append("director_metadata_incomplete_or_conflicting")
        if not official_year_valid:
            flags.append("official_year_requires_review")
        corrected = target_id != row["imdb_id"] or year != row["year"]
        verified = director_valid and official_year_valid and title_valid
        status = "corrected" if corrected and verified else "confirmed_correct" if verified else "unresolved"
        reason = ("Verified IMDb replacement; source rank and original evidence retained" if target_id != row["imdb_id"]
                  else "Official IMDb year correction; identity retained" if corrected
                  else "Official IMDb title/year and TMDb director/alias evidence corroborate identity" if verified
                  else "Supporting metadata needs manual review; no alternate identity guessed")
        audit_rows.append({
            "tspdt_rank": s["rank"], "source": s, "before": row,
            "after": {"imdb_id":target_id,"title":title,"year":year},
            "status":status,"suspicious":bool(flags),"flags":sorted(set(flags)),
            "reason":reason,"official_imdb":official,
            "metadata":{k:v for k,v in m.items() if k!="aliases"},
            "evidence_urls": ["https://www.imdb.com/title/" + target_id + "/"] +
                             ([m["source_url"]] if m.get("source_url") else []),
        })
    result = {"baseline":BASELINE,"source_snapshot_rows":len(source),
              "in_scope_source_rows":sum(2000<=r["year"]<=2023 for r in source),
              "audited":len(audit_rows),
              "counts":{status:sum(r["status"]==status for r in audit_rows)
                        for status in ("confirmed_correct","corrected","unresolved")},
              "suspicious_count":sum(r["suspicious"] for r in audit_rows),"records":audit_rows}
    ace.write_json(root / OUT / "identity-audit.json", result)
    return result

def restore_corrected_awards(snapshot, frozen, corrected_ids):
    """Reuse existing award rules only for newly admitted, verified identities."""
    scope = set(frozen["scope_imdb_ids"])
    if scope != set(corrected_ids):
        raise ValueError("Frozen award scope does not match new corrected identities")
    records = frozen["event_records"]
    if any(r["imdb_id"] not in scope for group in records.values() for r in group):
        raise ValueError("Award evidence contains an unrelated identity")
    scored = es.score_events(records)
    for iid in scope:
        target = snapshot["films"][iid]
        if target.get("family_scores"):
            raise ValueError("Refusing to overwrite existing award evidence: " + iid)
        if iid in scored:
            target.update(scored[iid])
    snapshot["corrected_identity_award_provenance"] = {
        "source_commit": frozen["source_commit"],
        "scope_imdb_ids": sorted(scope),
        "source_file": str(OUT / "inputs/corrected-award-evidence.json"),
        "scored": scored,
    }
    return scored

def repair(root, result):
    before = baseline(root, "backcatalog-details.json")
    records = {r["tspdt_rank"]:r for r in result["records"]}
    after = copy.deepcopy(before)
    for row in after["candidates"]:
        audited = records[row["tspdt_rank"]]
        row["source_title"] = audited["source"]["title"]
        row["source_year"] = audited["source"]["year"]
        row["identity_status"] = audited["status"]
        if audited["status"]=="corrected":
            row.update(audited["after"])
    ace.write_json(root / "backcatalog-details.json", after)
    ace.write_json(root / "backcatalog.json", [{"title":r["title"],"imdb_id":r["imdb_id"]} for r in after["candidates"]])
    registry = {"baseline":BASELINE, "identities": [], "awards": []}
    for r in result["records"]:
        if r["status"]!="unresolved":
            registry["identities"].append({"source_title":r["source"]["title"],
                "source_year":r["source"]["year"], **r["after"],"tspdt_rank":r["tspdt_rank"],
                "reason":r["reason"],"evidence_urls":r["evidence_urls"]})
    snap = baseline(root, "sources/evidence-families.json")
    inst = baseline(root, "sources/phase-b-institutional.json")
    ratings = baseline(root, "audience-ratings.json")
    discovery = baseline(root, "sources/imdb-audience-discovery.json")
    independent_ids = {r["imdb_id"] for r in discovery["films"]} | {r["imdb_id"] for r in baseline(root,"simulation-qualifiers.json")}
    original_snapshot_ids = set(snap["films"])
    replacements = []
    for r in result["records"]:
        old, new = r["before"]["imdb_id"], r["after"]["imdb_id"]
        if r["status"]!="corrected":
            continue
        replacements.append({"old_imdb_id":old, **r["after"], "tspdt_rank":r["tspdt_rank"]})
        if old==new:
            snap["films"].setdefault(new,{})["year"]=r["after"]["year"]
            continue
        prior = snap["films"].get(old,{})
        # Only Birdman's falsely attached Gotham award is transferable here.
        if r["tspdt_rank"]==338:
            correct = snap["films"][new]
            family="independent_cinema"
            label="Gotham Best Feature (winner)"
            if label in (prior.get("family_evidence") or {}).get(family,[]) and label not in correct["family_evidence"].get(family,[]):
                correct["family_scores"][family]=min(100,correct["family_scores"].get(family,0)+35)
                correct["family_evidence"].setdefault(family,[]).append(label)
        elif prior.get("family_scores"):
            raise ValueError("Unexpected transferable award evidence: "+old)
        snap["films"].setdefault(new,{"title":r["after"]["title"],"year":r["after"]["year"]})
        snap["films"][new]["title"]=r["after"]["title"]
        snap["films"][new]["year"]=r["after"]["year"]
        snap["films"].pop(old,None)
        for row in inst["films"]:
            if row.get("imdb_id")==old:
                if r["tspdt_rank"]!=290:
                    raise ValueError("Institutional correction requires explicit provenance")
                row.update({"imdb_id":new,"resolved_title":r["after"]["title"],"resolved_year":r["after"]["year"]})
        if old not in independent_ids:
            ratings["ratings"].pop(old,None)
            ratings.get("unavailable",{}).pop(old,None)
    new_corrected_ids = {r["imdb_id"] for r in replacements} - original_snapshot_ids
    frozen_awards = json.loads((root/OUT/"inputs/corrected-award-evidence.json").read_text())
    restore_corrected_awards(snap, frozen_awards, new_corrected_ids)
    ratings["ratings_count"]=len(ratings["ratings"])
    ratings["unavailable_count"]=len(ratings.get("unavailable",{}))
    ace.write_json(root/"sources/evidence-families.json",snap)
    ace.write_json(root/"sources/phase-b-institutional.json",inst)
    ace.write_json(root/"audience-ratings.json",ratings)
    ace.write_json(root/"sources/identity-overrides.json",registry)
    ace.write_json(root/OUT/"identity-corrections.json",replacements)
    return replacements

if __name__ == "__main__":
    root=Path(".")
    result=audit(root)
    changes=repair(root,result)
    print(json.dumps({"audit":result["counts"],"suspicious":result["suspicious_count"],"corrections":changes}))
