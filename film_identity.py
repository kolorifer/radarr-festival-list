"""Deterministic research-film identity checks; no fuzzy-only acceptance."""
import json, re, unicodedata
from pathlib import Path

REGISTRY = Path(__file__).parent / "sources/identity-overrides.json"
METADATA = Path(__file__).parent / "sources/identity-audit/tmdb.json"

def normalized(value):
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in text if not unicodedata.combining(c)))

def name_tokens(value):
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    text = "".join(c for c in text if not unicodedata.combining(c)).replace("ł", "l").replace("-", "")
    tokens = frozenset(re.findall(r"[a-z0-9]+", text))
    return NAME_ALIASES.get(tokens, tokens)

# Explicit director name forms observed in the source and matching title's credits.
def _tokens(value):
    text = unicodedata.normalize("NFKD", value.casefold()).replace("ł", "l").replace("-", "")
    return frozenset(re.findall(r"[a-z0-9]+", "".join(c for c in text if not unicodedata.combining(c))))

NAME_ALIASES = {_tokens(a): _tokens(b) for a, b in [["Bong Joon-ho", "Bong Joon Ho"], ["Alejandro G. Iñárritu","Alejandro González Iñárritu"],["Dan Kwan","Daniel Kwan"],["Andrew Lau","Andrew Lau Wai-Keung"],["Alan Mak","Alan Mak Siu-Fai"],["Marzieh Makhmalbaf","Marziyeh Meshkiny"],["Peter B. Hutton","Peter Hutton"],["Gerhard Benedikt Friedl","Gerhard Friedl"],["Victor Kossakovsky","Viktor Kossakovsky"],["James LeBrecht","Jim LeBrecht"],["Juan Antonio Bayona","J. A. Bayona"],["Alejandro Landes","Alejandro Landes Echavarría"],["Aleksandre Koberidze","Alexandre Koberidze"],["Bill Ross IV","Bill Ross"]]}

def director_matches(source, actual):
    expected = [name_tokens(x) for x in re.split(r"\s*&\s*|\s+and\s+|/", source or "") if x.strip()]
    names = [name_tokens(x) for x in actual or []]
    return bool(expected and names) and all(any(e == n for n in names) for e in expected)

COUNTRIES = {"usa": "us", "unitedstatesofamerica": "us", "unitedstates": "us",
             "uk": "gb", "unitedkingdom": "gb", "greatbritain": "gb",
             "hongkong": "hk", "southkorea": "kr", "republicofkorea": "kr",
             "france": "fr", "germany": "de", "spain": "es", "italy": "it",
             "japan": "jp", "canada": "ca", "china": "cn", "taiwan": "tw",
             "belgium": "be", "denmark": "dk", "sweden": "se", "norway": "no",
             "finland": "fi", "austria": "at", "australia": "au", "brazil": "br",
             "argentina": "ar", "mexico": "mx", "russia": "ru", "iran": "ir",
             "turkey": "tr", "romania": "ro", "poland": "pl", "india": "in",
             "portugal": "pt", "thailand": "th", "newzealand": "nz", "senegal": "sn",
             "chad": "td", "mali": "ml", "southafrica": "za"}

def country_codes(value):
    parts = value if isinstance(value, list) else re.split(r"/|,|&|;|\s+and\s+", value or "")
    return {COUNTRIES.get(normalized(x), normalized(x)) for x in parts if normalized(x)}

def supporting_conflicts(source, metadata):
    conflicts = []
    source_year = source.get("year")
    actual_year = str(metadata.get("release_date") or metadata.get("year") or "")[:4]
    if source_year and actual_year.isdigit() and abs(int(source_year) - int(actual_year)) > 1:
        conflicts.append("year_conflict")
    if source.get("director") and metadata.get("directors") and not director_matches(source["director"], metadata["directors"]):
        conflicts.append("director_conflict")
    a, b = source.get("runtime"), metadata.get("runtime")
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and a > 0 and b > 0 and abs(a-b) > max(5, a*0.1):
        conflicts.append("runtime_conflict")
    wanted, actual = country_codes(source.get("country")), country_codes(metadata.get("countries"))
    if wanted and actual and not wanted & actual:
        conflicts.append("country_conflict")
    return conflicts

def registry():
    return json.loads(REGISTRY.read_text()) if REGISTRY.exists() else {"identities": [], "awards": []}

def verified_identity(title, year):
    matches = [r for r in registry().get("identities", [])
               if normalized(r["source_title"]) == normalized(title) and int(r["source_year"]) == int(year)]
    return matches[0] if len(matches) == 1 else None

def verified_award(title, year):
    matches = [r for r in registry().get("awards", [])
               if normalized(r["source_title"]) == normalized(title) and int(r["source_year"]) == int(year)]
    return matches[0] if len(matches) == 1 else None

def cached_metadata(iid):
    if not METADATA.exists():
        return {}
    return (json.loads(METADATA.read_text()).get("films") or {}).get(iid) or {}

def accepts(source, candidate, metadata=None, aliases=()):
    """An exact verified title plus corroboration, never a similarity threshold."""
    metadata = metadata or {}
    if supporting_conflicts(source, metadata):
        return False
    titles = [source.get("title"), *aliases]
    actual = candidate.get("title") or candidate.get("l")
    if normalized(actual) not in {normalized(t) for t in titles if t}:
        return False
    year = candidate.get("year") if candidate.get("year") is not None else candidate.get("y")
    if not isinstance(year, int) or not isinstance(source.get("year"), int):
        return False
    director_ok = director_matches(source.get("director"), metadata.get("directors"))
    runtime_ok = (source.get("runtime") and metadata.get("runtime")
                  and abs(source["runtime"]-metadata["runtime"]) <= max(5, source["runtime"]*.1))
    if year != source["year"]:
        return abs(year-source["year"]) <= 1 and bool(director_ok and runtime_ok)
    if len(normalized(source.get("title"))) <= 7:
        return bool(director_ok and runtime_ok)
    return True
