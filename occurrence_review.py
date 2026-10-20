"""Evidence and owner choices for one expiring occurrence, never matching rules."""
import html
import json
from pathlib import Path
from identity_triage_store import private_path
from reviewed_corrections import binding
from torrent_research_evidence import validate
from private_text import redact_text


def packet(payload, context):
    data=payload.get('data') or {}; meta=context.get('meta') or {}
    if context.get('category')!='unknown_movie' or meta.get('identity_status')!='needs_review':return None
    listing=context.get('review_listing') or {}
    try:
        bound=binding(data['release'],data['indexer'],listing,meta['identity_reason'])
        return {'bound':bound,'evidence':validate(listing['torrent_evidence'])}
    except (ValueError,KeyError,TypeError):return None


def candidates(action):
    """Show stored proposals only; no network, no implicit acceptance."""
    path=Path.home().resolve()/'.local/state/movie-identity-research/review-report.json'
    try:
        private_path(path)
        if path.stat().st_size>4_000_000:return []
        report=json.loads(path.read_text()); rows=[]
        for case in report['cases']:
            proposal=case.get('proposal') or {};result=proposal.get('result') or {};facts=result.get('original_facts') or {}
            if (facts.get('title')==action['release'].get('title') and facts.get('year')==action['release'].get('year')
                    and facts.get('torrent_evidence')==action['review']['evidence']):
                rows.extend({'candidate':c,'current':proposal.get('current_evidence') is True,
                             'researched_at':proposal.get('created_at')} for c in result.get('candidates',[])[:3])
        return rows[:3]
    except (OSError,ValueError,KeyError,TypeError):return []


def render(action):
    def esc(value):return html.escape(redact_text(str(value)))
    review=action['review']; evidence=validate(review['evidence'])
    body='<h2>Review movie identity</h2><p>This choice applies only to this occurrence. It does not approve a download or teach a movie-specific exception.</p>'
    body+='<h3>Release</h3><p>'+esc(action['release'].get('name'))+'</p>'
    body+='<p>Filename year: '+esc(action['release'].get('year'))+'; tracker IMDb: '+esc(review['bound']['source_imdb'])+'; conflict: '+esc(review['bound']['reason'])+'</p>'
    for key in ('description','nfo'):
        body+='<h3>'+key.upper()+'</h3><p style="white-space:pre-wrap;overflow-wrap:anywhere">'+esc(evidence[key]['text'] or 'Not available')+'</p>'
    body+='<p>Tracker text may describe the wrong film. Screenshots have not been automatically analysed.</p>'
    for i,image in enumerate(evidence['images'],1):
        body+='<p><a target="_blank" rel="noopener noreferrer" href="'+html.escape(image['url'],quote=True)+'">View image '+str(i)+' ('+esc(image['section'])+')</a></p>'
    body+='<p>Unsupported images: '+str(evidence['unavailable_images'])+'. Text/reference collection truncated: '+str(evidence['truncated'])+'.</p><h3>Researched candidates</h3>'
    rows=candidates(action)
    if not rows:body+='<p>No matching research proposal available yet. You can review this evidence with ChatGPT and enter the verified candidate IDs below.</p>'
    for row in rows:
        candidate=row['candidate']; record=candidate.get('record') or {}
        body+='<h4>'+esc(record.get('title','Unknown'))+' ('+esc(record.get('date','Unknown date'))+')</h4>'
        body+='<p>'+('Current research proposal.' if row['current'] else 'Historical research proposal; recheck required.')+'</p><dl>'
        for label,key in (('Original title','original_title'),('IMDb','imdb'),('TMDb','id'),('Runtime (minutes)','runtime'),('Directors','directors'),('Cast','cast'),('Language','language'),('Other titles','aliases')):
            body+='<dt>'+label+'</dt><dd>'+esc(record.get(key) or 'Not available')+'</dd>'
        body+='</dl>'
        for label,key in (('Conflicts','contradictions'),('Missing or unreviewed evidence','support_gaps'),('Source comparison','source_review')):
            body+='<p>'+label+': '+esc(candidate.get(key) or 'None reported')+'</p>'
        if not action.get('chosen') and record.get('imdb') and record.get('id'):
            body+='<form method="post"><input type="hidden" name="imdb" value="'+esc(record['imdb'])+'"><input type="hidden" name="tmdb" value="'+esc(record['id'])+'"><label><input type="checkbox" name="confirm_identity" value="yes" required> I reviewed the evidence for this movie.</label><button>Select '+esc(record.get('title'))+' — no download</button></form>'
    if action.get('chosen'):
        movie=action['movie'];body+='<h3>Selected for this occurrence</h3><p>'+esc(movie['title'])+' ('+esc(movie['year'])+') — '+esc(movie['imdb_id'])+' / TMDb '+esc(movie['tmdb_id'])+'</p><p>No download started. Future occurrences require their own review.</p>'
        body+='<form method="post"><button name="prepare_download" value="yes">Open separate download confirmation</button></form>'
    else:
        body+='''<form method="post"><label>Chosen IMDb ID <input name="imdb" pattern="tt[0-9]{7,10}" required></label><label>Chosen TMDb movie ID <input name="tmdb" type="number" min="1" required></label><label><input type="checkbox" name="confirm_identity" value="yes" required> I reviewed the evidence and select this movie for this occurrence only.</label><button>Select movie — no download</button></form>'''
    return body


def verified_target(action, imdb, tmdb, lookup, resolver):
    """Recheck source evidence plus ordinary target crosswalk/title/year gates."""
    release=action['release'];listing=lookup(release,action['indexer'])
    if binding(release,action['indexer'],listing,action['review']['bound']['reason'])!=action['review']['bound']:raise ValueError('changed_evidence')
    target=resolver(release['title'],release['year'],imdb_id=imdb,tmdb_id=tmdb)
    if target.get('identity_status')!='verified_tmdb' or target.get('imdb_id')!=imdb or target.get('tmdb_id')!=tmdb:raise ValueError('target_not_verified')
    return dict(target,identity_source='owner_occurrence_choice')
