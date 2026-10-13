"""Fill only verified missing ratings for the identity cleanup; preserve existing values."""
import argparse, copy, gzip, hashlib, io, json, os, re, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import audience_calibration_enrichment as ace
import film_identity as fi

OUT = Path("simulations/data-identity-integrity")

def fetch(path, params, key):
    url = "https://api.reeldb.io" + path + "?" + urlencode({**params, "apikey": key})
    try:
        with urlopen(Request(url, headers={"Accept": "application/json"}), timeout=30) as response:
            data = json.load(response)
        return data, None
    except HTTPError as exc:
        return None, "HTTP " + str(exc.code)
    except (URLError, TimeoutError, ValueError):
        return None, "network_or_schema_error"

def public_metadata(data, allowed_titles=()):
    if not isinstance(data, dict):
        return {}
    ids = []
    for key in ("imdb_id", "imdb", "imdbId", "id"):
        value = data.get(key)
        if isinstance(value, str) and re.fullmatch(r"tt\d{7,10}", value):
            ids.append(value)
    for container in ("ids", "external_ids"):
        for value in (data.get(container) or {}).values() if isinstance(data.get(container), dict) else []:
            if isinstance(value, str) and re.fullmatch(r"tt\d{7,10}", value):
                ids.append(value)
    title = data.get("title") or data.get("name")
    matched = isinstance(title,str) and fi.normalized(title) in {fi.normalized(t) for t in allowed_titles}
    year = data.get("year")
    kind = data.get("type")
    return {"imdb_ids":sorted(set(ids)), "title":title if matched else None,
            "title_matches_expected":matched,
            "year":int(year) if str(year).isdigit() and 1880<=int(year)<=2100 else None,
            "type":kind if kind in ("movie","series","tvseries","episode","short","video","tvMovie") else None}

def safe_merge(existing, incoming):
    result = copy.deepcopy(existing)
    added = []
    for source, item in incoming.items():
        if not ace.valid_provider(result.get(source), source) and ace.valid_provider(item, source):
            result[source]=item
            added.append(source)
    return result, added

def enrich(root, key):
    inputs=ace.load_inputs(root)
    movies=ace.universe(inputs)
    payload=copy.deepcopy(inputs[str(ace.es.AUDIENCE)])
    ratings=payload["ratings"]
    metadata=json.loads((root/"sources/identity-audit/tmdb.json").read_text())["films"]
    pending=[r for r in movies if any(not ace.valid_provider(
        (ratings.get(r["imdb_id"],{}).get("reeldb") or {}).get(source),source)
        for source in ("imdb","letterboxd"))]
    report={"observed_at":datetime.now(timezone.utc).isoformat(),"records":[],
            "requests":0,"request_budget":100,"existing_valid_values_preserved":True}
    if pending and not key:
        raise RuntimeError("Missing repository ReelDB key")
    for movie in sorted(pending,key=lambda r:r["imdb_id"]):
        iid=movie["imdb_id"]
        item=copy.deepcopy(ratings.get(iid) or {})
        rr=item.get("reeldb") or {}
        record={"imdb_id":iid,"title":movie["title"],"attempts":[],"added":[]}
        m=metadata.get(iid) or {}
        selectors=[("imdb",iid)]
        if m.get("status")=="movie" and m.get("imdb_id")==iid and m.get("tmdb_id"):
            selectors.append(("tmdb",str(m["tmdb_id"])))
        for kind, selector in selectors:
            if report["requests"]+2 > report["request_budget"]:
                record["status"]="budget_exhausted"
                break
            data, error=fetch("/v1/title",{kind:selector,"append":"ratings"},key)
            report["requests"]+=1
            safe=public_metadata(data, [movie["title"],m.get("title"),m.get("original_title"),*(m.get("aliases") or [])])
            attempt={"selector_type":kind,"selector":selector,"metadata_status":error or "ok",
                     "metadata":safe,"rating_status":None}
            record["attempts"].append(attempt)
            if error in ("HTTP 401","HTTP 403","HTTP 429"):
                raise RuntimeError("Provider stopped: "+error)
            if safe.get("imdb_ids") and iid not in safe["imdb_ids"]:
                attempt["rating_status"]="rejected_imdb_identity_conflict"
                continue
            incoming={}
            if isinstance(data,dict) and isinstance(data.get("ratings"),dict):
                try: incoming=ace.safe_ratings(data["ratings"])
                except ValueError: pass
            rd, rating_error=fetch("/v1/title/"+selector+"/ratings",{},key)
            report["requests"]+=1
            attempt["rating_status"]=rating_error or "ok"
            if rating_error in ("HTTP 401","HTTP 403","HTTP 429"):
                raise RuntimeError("Provider stopped: "+rating_error)
            if isinstance(rd,dict):
                try: incoming.update(ace.safe_ratings(rd))
                except ValueError: pass
            rr, added=safe_merge(rr,incoming)
            if added:
                record["added"].extend(added)
                item.setdefault("rating_provenance",{}).update({source:{
                    "provider":"ReelDB","selector_type":kind,"selector":selector,
                    "observed_at":report["observed_at"]} for source in added})
            time.sleep(1.6)
            if all(ace.valid_provider(rr.get(s),s) for s in ("imdb","letterboxd")):
                break
        if rr:
            item.update({"title":movie["title"],"year":movie["year"],"reeldb":rr})
            ratings[iid]=item
        if ace.valid_provider(rr.get("imdb"),"imdb") or ace.valid_provider(rr.get("letterboxd"),"letterboxd"):
            payload.get("unavailable",{}).pop(iid,None)
        record["complete_after"]=all(ace.valid_provider(rr.get(s),s) for s in ("imdb","letterboxd"))
        report["records"].append(record)
        print(json.dumps({"completed":len(report["records"]),"requested":len(pending),
                          "new_components":len(record["added"])}),flush=True)
    payload["ratings_count"]=len(ratings)
    payload["unavailable_count"]=len(payload.get("unavailable",{}))
    ace.write_json(root/ace.es.AUDIENCE,payload)
    ace.write_json(root/OUT/"rating-enrichment.json",report)
    return {"requested":len(pending),"requests":report["requests"],
            "complete_after":sum(r["complete_after"] for r in report["records"])}

def fallback(root):
    inputs=ace.load_inputs(root)
    before=json.loads((root/ace.OUT/"inputs/imdb-fallback.json").read_text())
    payload={"source_url":ace.IMDB_URL,"baseline_fallback_preserved":True,
             "ratings":copy.deepcopy(before["ratings"]),"observed_at":datetime.now(timezone.utc).isoformat()}
    wanted={r["imdb_id"] for r in ace.universe(inputs)
            if r["imdb_id"] not in payload["ratings"] and not ace.valid_provider(
                ((inputs[str(ace.es.AUDIENCE)]["ratings"].get(r["imdb_id"]) or {}).get("reeldb") or {}).get("imdb"),"imdb")}
    if wanted:
        with urlopen(Request(ace.IMDB_URL),timeout=60) as response:
            compressed=response.read()
        payload["additional_download_sha256"]=hashlib.sha256(compressed).hexdigest()
        with gzip.open(io.BytesIO(compressed),"rt",encoding="utf-8") as stream:
            payload["ratings"].update(ace.imdb_rows(stream,wanted))
    payload["requested_ids"]=sorted(wanted)
    payload["unavailable_ids"]=sorted(wanted-payload["ratings"].keys())
    ace.write_json(root/OUT/"inputs/imdb-fallback.json",payload)
    return {"requested":len(wanted),"unavailable":payload["unavailable_ids"]}

if __name__=="__main__":
    root=Path(".")
    print(json.dumps(enrich(root,os.environ.get("REELDB_API_KEY",""))))
    print(json.dumps(fallback(root)))
