"""Pure local rendering of an exact receipt-bound snapshot assessment."""
from html import escape
import hashlib
from urllib.parse import urlsplit
from .contracts import decode,digest,require,shape


def validate_local_context(local_raw):
    local=decode(local_raw,65536);shape(local,'tracker_url release_name nfo_text')
    try:
        for value in local.values():
            require(type(value) is str and len(value)<=16384,'snapshot_report_local')
            value.encode('utf-8')
        u=urlsplit(local['tracker_url'])
        require(u.scheme=='https' and bool(u.hostname) and not u.username and not u.password and
                not any(ord(c)<32 for c in local['tracker_url']),'snapshot_report_url')
    except (ValueError,UnicodeError):require(False,'snapshot_report_url')
    return local


def render(report, report_sha256, projection, local_raw, local_sha256):
    require(digest(report)==report_sha256 and report.get('kind')=='receipt_bound_snapshot_review_v1' and
        report.get('projection_sha256')==digest(projection) and
        report.get('local_context_sha256')==local_sha256 and
        type(local_raw) is bytes and hashlib.sha256(local_raw).hexdigest()==local_sha256 and
        report.get('generation_invoked') is True and report.get('provider_receipt_correlated') is True and
        report.get('sent') is False, 'snapshot_report_binding')
    local=validate_local_context(local_raw)
    result=report['result'];source=projection['listing'];cat=projection['catalogue']
    def show(v):
        if v is None or v=='':return 'Not established'
        if isinstance(v,list):return ', '.join(str(x) for x in v) or 'Not established'
        return str(v)
    def row(label,left,right):
        return '<tr><th>'+escape(label)+'</th><td>'+escape(show(left))+'</td><td>'+escape(show(right))+'</td></tr>'
    def li(label,value):return '<li><strong>'+escape(label)+':</strong> '+escape(show(value))+'</li>'
    def duration_ms(value):
        if value is None:return 'Not established'
        hours,remainder=divmod(value,3600000);minutes,remainder=divmod(remainder,60000)
        seconds,millis=divmod(remainder,1000)
        return str(hours)+' h '+str(minutes)+' min '+str(seconds)+'.'+format(millis,'03d')+' s'
    def reason_label(value):
        return {'title_conflict':'The producer flagged conflicting titles.',
                'year_conflict':'The producer flagged conflicting years.',
                'identifier_conflict':'The producer flagged conflicting identifiers.'}.get(value,
                'The producer flagged '+value.replace('_',' ')+'.')
    ids=projection['source_identifiers'];candidate=result['candidate']
    rows=[row('Listing and catalogue title',source['title'],cat['title']),row('Year',source['year'],cat['theatrical_year']),
          row('Festival years',None,cat['festival_years']),row('Description runtime in minutes',source['description_runtime_minutes'],None),
          row('NFO runtime ('+source['nfo_runtime_kind']+')',duration_ms(source['nfo_runtime_milliseconds']),None),
          row('Catalogue runtime in minutes',None,cat['runtime_minutes']),row('Cast',source['cast'],cat['cast']),
          row('Directors',source['directors'],cat['directors']),row('Listing IMDb versus catalogue IMDb',source['imdb'],cat['imdb']),
          row('Catalogue TMDb',None,cat['tmdb'])]
    prior=report.get('previous_assessment')
    prior_html=''
    if prior is not None:
        prior_rationale=('Its original rationale was withheld and cannot be recovered.' if prior['rationale'] in ('withheld_unrecoverable','withheld')
                         else 'The previous explanation remains in the earlier retained report.')
        prior_html=('<h2>Earlier distinct assessment</h2><p>Status: '+escape(show(prior['status']))+
            '; proposed identity: '+escape(show(prior['candidate']))+'. '+prior_rationale+' '
            'The assessment below is a distinct new result, not a reconstruction of that rationale.</p>')
    findings_html=''
    if 'film_findings' in result:
        def field_label(field, default):
            return ('collector or producer field ' if field.startswith(('collector_','asserted_')) else default)+field.replace('_',' ')
        findings_html=('<h3>Film identity findings</h3><p>Reconciliations are model interpretations for human review, not verified facts.</p><ul>'+''.join(
            li(f['aspect'].replace('_',' '),f['disposition']+': '+f['explanation']+
                ' ('+field_label(f['source_field'],'listing field ')+'; '+field_label(f['catalogue_field'],'catalogue field ')+
                '; cited '+', '.join(f['evidence'])+')') for f in result['film_findings'])+'</ul>'+
            '<h3>Remaining film identity blockers</h3><ul>'+(''.join(
            li(b['aspect'].replace('_',' '),b['reason'].replace('_',' ')+'; cited '+', '.join(b['evidence']))
            for b in result['film_blockers']) if result['film_blockers'] else '<li>None reported</li>')+'</ul>')
    text=['<!doctype html><html><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'"><title>Private movie review</title></head><body>',
          '<h1>Private movie review</h1><p><a rel="noreferrer noopener" href="'+escape(local['tracker_url'],quote=True)+'">Open the exact source listing</a></p>',
          '<h2>Identification problem</h2><p>'+escape(reason_label(projection['reason']))+'</p><ul>',
          li('Original release name',local['release_name']),li('Collector title',projection['title']),li('Collector year',projection['year']),
          li('Producer reason',projection['reason']),li('Producer contradictions',projection['producer_contradictions']),'</ul>',
          '<h2>Evidence comparison</h2><table><thead><tr><th>Fact</th><th>Listing</th><th>Catalogue</th></tr></thead><tbody>',*rows,'</tbody></table>',
          '<p>NFO duration is uploader-reported for the indicated stream or container; it is not an independently measured edition.</p><ul>',
          li('Collector source IMDb',ids['imdb']),li('Collector source TMDb',ids['tmdb']),
          li('Producer asserted IMDb',ids['asserted_imdb']),li('Producer asserted TMDb',ids['asserted_tmdb']),
          li('Identity fields conflict',projection['conflicting_ids']),'</ul>',
          prior_html,'<h2>Assessment</h2><ul>',li('Result',result['status']),li('Proposed IMDb',candidate.get('imdb') if candidate else None),
          li('Proposed TMDb',candidate.get('tmdb') if candidate else None),li('Rationale',result['rationale']),
          li('Uncertainty',result['uncertainty']),li('Next action',result['next_action']),'</ul>',
          findings_html,
          '<h3>Evidence cited by the model</h3><ul>',
          *[li('Listing' if c['evidence_id']=='source' else 'Catalogue',c['claim'].replace('_',' ')) for c in result['citations']],'</ul>',
          '<p>The model proposal was checked against the bound identifiers and citations. No numeric score was assigned.</p>',
          '<p>Producer conflict remains for human review; matching IDs alone do not resolve it. This is an unsent review proposal, not identity or download approval.</p>',
          ('<h3>Separate nonblocking limitations</h3>' if 'film_findings' in result else '')+
          '<p>Original collector bytes, current queue, complete decisions and physical edition remain unverified. '+
          ('Identity and acquisition remain unapproved. ' if 'film_findings' in result else '')+
          'Listing and catalogue provenance were independently reviewed by the supervisor; provider receipt is correlated, not provider-signed billing proof.</p>',
          '<details><summary>Retained NFO text</summary><pre>'+escape(show(local['nfo_text']))+'</pre></details></body></html>']
    return ''.join(text)
