"""Sourced packaging facts, never identity overrides. Shadow only."""
import json
import re
from pathlib import Path
from .scorer import words


def evidence(release, listing, facts, candidates):
    """Require an exact documented label/member plus independently checked media."""
    if len(facts.get('filenames', [])) != 1:
        return None
    description = listing.get('torrent_evidence', {}).get('description', {}).get('text', '')
    if not isinstance(description, str) or not description or len(description)>65536:
        return None
    if re.search(r'\b(?:box\s*set|complete collection|movie pack|film pack|double feature|triple feature|[2-9]\d* (?:films|movies))\b',description,re.I):
        return None
    records=json.loads(Path(__file__).with_name('edition-evidence.json').read_text())
    found=[]
    for record in records:
        if not record.get('source') or not record.get('retrieved'):continue
        label=words(record['label'])
        for member in record['members']:
            title=words(member['title'])
            # Exact whole title, no substring deletion or arbitrary numeric removal.
            if words(release['title']) not in (label+title,title+label):continue
            if release['year']!=member['year']:continue
            # Description title must occur at its start, on a word boundary.
            tokens=re.findall(r'[^\W_]+',description.casefold())
            if tokens[:len(title)]!=title:continue
            matches=[c for c in candidates if any(words(t)==title for t in c['titles'])]
            if len(matches)!=1:continue
            found.append({'candidate_id':matches[0]['id'], 'movie_title':member['title'],
                          'label':record['label'],'source':record['source'],
                          'retrieved':record['retrieved'], 'basis':'documented_edition_member_and_bound_single_file'})
    return found[0] if len(found)==1 else None
