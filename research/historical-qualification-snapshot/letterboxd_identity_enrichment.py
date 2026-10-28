"""Verified public Letterboxd JSON-LD fallback; retain unavailable components."""
import argparse, copy, hashlib, json, re, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup
import audience_calibration_enrichment as ace
import film_identity as fi
from identity_integrity import OUT

PATH=OUT/"inputs/letterboxd-fallback.json"

def structured_movie(html):
    soup=BeautifulSoup(html,"html.parser")
    for tag in soup.select('script[type="application/ld+json"]'):
        raw=tag.get_text().strip()
        try: data=json.loads(raw[raw.index("{"):raw.rindex("}")+1])
        except (ValueError,AttributeError):continue
        if data.get("@type")=="Movie":
            return data
    return {}

def verified_rating(iid, movie, metadata, html):
    imdb_ids=set(re.findall(r"tt[0-9]{7,10}",html))
    directors=[x.get("name") for x in movie.get("director",[]) if isinstance(x,dict) and x.get("name")]
    if iid not in imdb_ids or not fi.director_matches(metadata.get("director"),directors):
        return None,"identity_not_corroborated"
    created=str(movie.get("dateCreated") or "")[:4]
    if not created.isdigit() or abs(int(created)-int(metadata["year"]))>1:
        return None,"year_not_corroborated"
    aggregate=movie.get("aggregateRating") or {}
    if aggregate.get("bestRating")!=5 or "ratingCount" not in aggregate:
        return None,"no_published_aggregate_rating_count"
    value={"rating":aggregate.get("ratingValue"),"votes":aggregate.get("ratingCount")}
    if not ace.valid_provider(value,"letterboxd"):
        return None,"invalid_rating_or_count"
    return value,None

def collect(root):
    inputs=ace.load_inputs(root)
    metadata=json.loads((root/"sources/identity-audit/tmdb.json").read_text())["films"]
    candidates=ace.universe(inputs)
    pending=[r for r in candidates if not ace.valid_provider(
        ((inputs[str(ace.es.AUDIENCE)]["ratings"].get(r["imdb_id"]) or {}).get("reeldb") or {}).get("letterboxd"),"letterboxd")]
    payload={"provider":"Letterboxd public JSON-LD","observed_at":datetime.now(timezone.utc).isoformat(),
             "ratings":{},"records":[]}
    for r in sorted(pending,key=lambda r:r["imdb_id"]):
        iid=r["imdb_id"]
        m=metadata.get(iid) or {}
        m=m.get("episode_metadata") or m
        expected={"director":" & ".join(m.get("directors") or []),"year":r["year"]}
        record={"imdb_id":iid,"title":r["title"]}
        try:
            with urlopen(Request("https://letterboxd.com/imdb/"+iid+"/",headers={"User-Agent":"Mozilla/5.0"}),timeout=20) as response:
                raw=response.read(); url=response.geturl()
            if not url.startswith("https://letterboxd.com/film/"):
                record["status"]="no_film_redirect"
            else:
                html=raw.decode("utf-8")
                movie=structured_movie(html)
                rating,error=verified_rating(iid,movie,expected,html)
                record.update({"source_url":url,"page_sha256":hashlib.sha256(raw).hexdigest(),
                               "status":error or "rating_verified"})
                if rating:
                    payload["ratings"][iid]={**rating,"source_url":url,"imdb_id":iid,
                                            "observed_at":payload["observed_at"]}
        except HTTPError as exc:record["status"]="HTTP "+str(exc.code)
        except (URLError,TimeoutError,ValueError):record["status"]="network_or_schema_error"
        payload["records"].append(record)
        time.sleep(.4)
    ace.write_json(root/PATH,payload)
    return {"requested":len(pending),"verified_ratings":len(payload["ratings"])}

def apply(root):
    path=root/ace.es.AUDIENCE
    ratings=json.loads(path.read_text())
    payload=json.loads((root/PATH).read_text())
    used=[]
    for iid,value in payload["ratings"].items():
        item=ratings["ratings"].setdefault(iid,{})
        rr=item.setdefault("reeldb",{})
        if ace.valid_provider(rr.get("letterboxd"),"letterboxd"):
            continue
        rr["letterboxd"]={k:value[k] for k in ("rating","votes")}
        item.setdefault("rating_provenance",{})["letterboxd"]={
            "provider":"Letterboxd public JSON-LD","source_url":value["source_url"],
            "observed_at":value["observed_at"]}
        used.append(iid)
    ratings["ratings_count"]=len(ratings["ratings"])
    ace.write_json(path,ratings)
    ace.write_json(root/OUT/"letterboxd-fallback-used.json",{"imdb_ids":sorted(used),"existing_valid_ratings_preserved":True})
    return {"fallbacks_applied":len(used)}

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--collect",action="store_true")
    args=p.parse_args()
    print(json.dumps(collect(Path(".")) if args.collect else apply(Path("."))))
