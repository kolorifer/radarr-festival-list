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


def render(report, report_sha256, projection, local_raw, local_sha256, *, publisher_raw=None):
    require(digest(report)==report_sha256 and report.get('kind')=='receipt_bound_snapshot_review_v1' and
        report.get('projection_sha256')==digest(projection) and
        report.get('local_context_sha256')==local_sha256 and
        type(local_raw) is bytes and hashlib.sha256(local_raw).hexdigest()==local_sha256 and
        report.get('generation_invoked') is True and report.get('provider_receipt_correlated') is True and
        report.get('sent') is False, 'snapshot_report_binding')
    from .snapshot_review import film_comparisons
    from .new_case import _WITHHELD_PROSE
    local=validate_local_context(local_raw);result=report['result'];source=projection['listing'];cat=projection['catalogue']
    ids=projection['source_identifiers'];candidate=result['candidate'];status=result['status']
    require((status=='supported_candidate' and type(candidate) is dict) or
            (status in ('unresolved','blocked') and candidate is None),'snapshot_report_binding')
    def show(v):
        if v is None or v=='':return 'Not established'
        if isinstance(v,list):return ', '.join(str(x) for x in v) or 'Not established'
        return str(v)
    def li(label,value):return '<li><strong>'+escape(label)+':</strong> '+escape(show(value))+'</li>'
    def duration_ms(value):
        if value is None:return 'Not established'
        hours,remainder=divmod(value,3600000);minutes,remainder=divmod(remainder,60000)
        seconds,millis=divmod(remainder,1000)
        return str(hours)+' h '+str(minutes)+' min '+str(seconds)+'.'+format(millis,'03d')+' s'
    def minutes(value):return 'Not established' if value is None else show(value)+' minutes'
    def observed(value):
        from datetime import datetime,timezone
        return datetime.fromtimestamp(value,timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    def reason_label(value):
        return {'title_conflict':'The producer flagged conflicting titles.',
                'year_conflict':'The producer flagged conflicting years.',
                'identifier_conflict':'The producer flagged conflicting identifiers.'}.get(value,
                'The producer flagged '+value.replace('_',' ')+'.')
    labels={'title':'Titles','year':'Years','people':'People','runtime_description':'Description runtime',
            'runtime_nfo':'NFO runtime','ids':'Identifiers'}
    reason_labels={'missing_film_evidence':'missing film evidence',
                   'conflicting_film_evidence':'conflicting film evidence',
                   'ambiguous_film_evidence':'ambiguous film evidence'}
    def detail(aspect):
        if aspect=='title':return 'Collector: '+show(projection['title'])+'; listing: '+show(source['title'])+'; catalogue: '+show(cat['title'])
        if aspect=='year':return 'Collector: '+show(projection['year'])+'; listing: '+show(source['year'])+'; catalogue theatrical: '+show(cat['theatrical_year'])+'; catalogue festival: '+show(cat['festival_years'])
        if aspect=='people':return 'Listing cast: '+show(source['cast'])+'; catalogue cast: '+show(cat['cast'])+'; listing directors: '+show(source['directors'])+'; catalogue directors: '+show(cat['directors'])
        if aspect=='runtime_description':return 'Listing description: '+minutes(source['description_runtime_minutes'])+'; catalogue: '+minutes(cat['runtime_minutes'])
        if aspect=='runtime_nfo':return 'NFO '+show(source['nfo_runtime_kind'])+': '+duration_ms(source['nfo_runtime_milliseconds'])+'; catalogue: '+minutes(cat['runtime_minutes'])
        if aspect=='ids':return ('Listing IMDb: '+show(source['imdb'])+'; collector IMDb: '+show(ids['imdb'])+'; collector TMDb: '+show(ids['tmdb'])+
            '; producer asserted IMDb: '+show(ids['asserted_imdb'])+'; producer asserted TMDb: '+show(ids['asserted_tmdb'])+
            '; catalogue IMDb: '+show(cat['imdb'])+'; catalogue TMDb: '+show(cat['tmdb']))
        return 'No corresponding observation is available.'
    publisher_html=''
    if 'publisher_edition' in projection:
        from .snapshot_review import publisher_edition_context
        pub=projection['publisher_edition']
        require(type(publisher_raw) is bytes and publisher_edition_context(publisher_raw,projection,now=pub['observed_at'])==pub,'snapshot_report_binding')
        url=decode(publisher_raw,65536)['source_url']
        publisher_html=('<h3>Reviewed publisher-edition claim</h3><ul>'+li('Publisher',pub['publisher'])+
            li('Film',pub['title'])+li('Year',pub['year'])+li('Edition label',pub['edition_label'])+
            li('Publisher-stated runtime',minutes(pub['runtime_minutes']))+li('Observed',observed(pub['observed_at']))+
            li('Expires',observed(pub['expires_at']))+li('Provenance hash',pub['provenance_sha256'])+'</ul>'+
            '<p>Reviewed publisher source: '+escape(url)+'</p>'+
            '<p>This is a main-attested publisher claim about an edition, not a measurement or identification of this torrent or physical file. '
            'The original listing, NFO and catalogue observations remain unchanged. Identity and acquisition approval remain separate.</p>')
    else:require(publisher_raw is None,'snapshot_report_binding')
    comparisons=film_comparisons(projection)
    blockers=result.get('film_blockers')
    if not isinstance(blockers,list):blockers=[]
    decision={'supported_candidate':'A film identity is proposed for human review.',
              'unresolved':'Film identity remains unresolved; no identity is proposed.',
              'blocked':'The review is blocked; no identity is proposed.'}.get(status,'The recorded assessment status is not recognized.')
    action={'human_review':'Bring this assessment to human review.',
            'obtain_retained_evidence':'Review whether retained film evidence is available.',
            'verify_source_runtime_edition':'Review the source runtime and edition evidence.',
            'boundary_review':'Review the applicable evidence boundary.'}.get(result.get('next_action'),'Review the recorded next action.')
    handling=report.get('prose_handling') or {}
    def prose(field,label):
        state=handling.get(field,{}).get('status')
        if state=='withheld':return '<p><strong>'+escape(label)+':</strong> The model’s '+escape(field)+' was withheld by the local text policy; the original text is not retained.</p>'
        value=result.get(field)
        if state=='retained' and isinstance(value,str):return '<p><strong>'+escape(label)+':</strong> '+escape(value)+'</p>'
        if isinstance(value,str) and value!=_WITHHELD_PROSE:
            return '<p><strong>'+escape(label)+':</strong> '+escape(value)+' <em>Its text-handling status was not recorded.</em></p>'
        return '<p><strong>'+escape(label)+':</strong> Its text-handling status is not established.</p>'
    field_names={'title':'title','year':'year','theatrical_year':'theatrical','festival_years':'festival',
        'cast':'cast','directors':'directors','description_runtime_minutes':'description runtime',
        'nfo_runtime_milliseconds':'NFO runtime','imdb':'IMDb','tmdb':'TMDb',
        'asserted_imdb':'asserted IMDb','asserted_tmdb':'asserted TMDb','runtime_minutes':'runtime'}
    def field_value(origin,field):
        obj=source if origin=='listing' else cat if origin=='catalogue' else projection if field in ('title','year') else ids
        value=obj.get(field)
        if field=='nfo_runtime_milliseconds':return duration_ms(value)+' ('+show(source['nfo_runtime_kind'])+')'
        if field in ('description_runtime_minutes','runtime_minutes'):return minutes(value)
        return show(value)
    def pair(item):
        lo,lf,ro,rf=item['left_origin'],item['left_field'],item['right_origin'],item['right_field']
        left=lo+' '+field_names.get(lf,lf.replace('_',' '));right=ro+' '+field_names.get(rf,rf.replace('_',' '))
        relation={'exact':'matches','overlap':'shares at least one name with','different':'differs from',
                  'missing':'has missing information compared with','no_observed_overlap':'has no observed name overlap with'}[item['relation']]
        line=left+': '+field_value(lo,lf)+' '+relation+' '+right+': '+field_value(ro,rf)
        delta=item.get('difference_minutes')
        if delta is not None and delta!=0:line+=' ('+str(abs(delta))+' minute'+('s' if abs(delta)!=1 else '')+(' longer' if delta>0 else ' shorter')+')'
        delta=item.get('difference_milliseconds')
        if delta is not None and delta!=0:
            seconds,millis=divmod(abs(delta),1000);mins,secs=divmod(seconds,60)
            line+=' ('+str(mins)+' min '+str(secs)+'.'+format(millis,'03d')+' sec'+(' longer' if delta>0 else ' shorter')+')'
        return line
    def category(relations,heading,empty):
        rows=[]
        for aspect,items in comparisons.items():
            matches=[pair(item) for item in items if item['relation'] in relations]
            if matches:rows.append(li(labels[aspect],'; '.join(matches)))
        return '<h3>'+heading+'</h3>'+('<ul>'+''.join(rows)+'</ul>' if rows else '<p>'+empty+'</p>')
    prior=report.get('previous_assessment');prior_html=''
    if prior is not None:
        rationale=('Its original rationale was withheld and cannot be recovered.' if prior['rationale'] in ('withheld_unrecoverable','withheld') else 'The previous explanation remains in the earlier retained report.')
        if prior.get('uncertainty')=='withheld':rationale+=' Its original uncertainty explanation was withheld and cannot be recovered.'
        prior_html=('<h3>Earlier distinct assessment</h3><p>Status: '+escape(show(prior['status']))+'; proposed identity: '+escape(show(prior['candidate']))+'. '+rationale+' The assessment below is a distinct new result, not a reconstruction of that rationale.</p>')
    if report.get('previous_structure_refusal') is not None:prior_html='<p>The earlier assessment received a receipt but its findings failed structural validation. Its answer was not retained. This is a distinct corrected assessment.</p>'
    if report.get('previous_field_refusal') is not None:prior_html='<p>The earlier assessment received a receipt but failed a field validation check. Its answer was not retained, so the specific failed comparison is unknown. This is a distinct corrected assessment.</p>'
    if report.get('previous_quality_refusal') is not None:prior_html='<p>The earlier assessment received a receipt, then failed a composite explanation-quality check. Its answer was not retained; the specific failed predicate and original wording are unknown. This is a distinct corrected assessment, not recovery of that answer. The earlier operation and reservation remain recorded.</p>'
    if report.get('previous_result_refusal') is not None:prior_html='<p>The earlier assessment received a receipt but did not provide a required film blocker. Its answer was not retained. This is a distinct corrected assessment.</p>'
    raw_comparisons=''.join(li(aspect.replace('_',' '),item['left_origin']+' '+item['left_field'].replace('_',' ')+' versus '+item['right_origin']+' '+item['right_field'].replace('_',' ')+': '+item['relation'].replace('_',' ')+
        (('; difference in minutes '+show(item['difference_minutes'])) if item.get('difference_minutes') is not None else '')+
        (('; difference in milliseconds '+show(item['difference_milliseconds'])) if item.get('difference_milliseconds') is not None else '')+
        (('; NFO stream '+item['nfo_kind']) if 'nfo_kind' in item else '')) for aspect,items in comparisons.items() for item in items)
    model_findings=''.join(li(labels.get(f['aspect'],f['aspect'].replace('_',' ')),f['disposition']+': '+f['explanation']+
        '; source field: '+f['source_field'].replace('_',' ')+'; comparison field: '+f['catalogue_field'].replace('_',' ')+
        '; cited: '+', '.join(f['evidence']))
        for f in result.get('film_findings',[]))
    blocks=''.join(li(labels.get(b.get('aspect'),show(b.get('aspect')).replace('_',' ')),
        reason_labels.get(b.get('reason'),show(b.get('reason')).replace('_',' '))+'; observed values — '+detail(b.get('aspect'))+
        ('; support considered: '+b['support_considered']+'; why still material: '+b['material_conflict'] if 'support_considered' in b else '')+
        ('; cited evidence: '+(show(b['evidence']) if b['evidence'] else 'None recorded') if 'evidence' in b else '')) for b in blockers)
    structured=('Model-reported blockers: '+', '.join(labels.get(b.get('aspect'),show(b.get('aspect')).replace('_',' '))+' ('+reason_labels.get(b.get('reason'),show(b.get('reason')).replace('_',' '))+')' for b in blockers) if blockers else 'No structured film blockers were recorded')
    fallback=('<p><strong>Summary from recorded choices:</strong> '+escape(decision)+' '+escape(structured)+'. This summary is generated locally from retained structured choices; it is not the model’s original explanation.</p>' if any(handling.get(k,{}).get('status')=='withheld' for k in ('rationale','uncertainty')) else '')
    # A factual view of retained observations, never reconstructed model reasoning.
    current_rows=[comparisons['title'][0],*comparisons['year'][:2],*comparisons['people'],
                  comparisons['runtime_description'][0],comparisons['runtime_nfo'][0]]
    current_rows += [row for row in comparisons['ids']
                     if row['left_origin']=='listing' and row['right_origin']=='catalogue']
    evidence_summary=('<h2>Recorded decision and observed evidence</h2><p>'+escape(decision)+
        ' This summary is generated from the recorded status and computed comparisons; it is not the model’s reasoning and does not independently confirm identity.</p><ul>'+
        ''.join('<li>'+escape(pair(row)+'.')+'</li>' for row in current_rows)+'</ul>')
    if 'historical_id_discrepancy' in projection:
        d=projection['historical_id_discrepancy']
        evidence_summary+=('<p>'+escape('The retained earlier listing-derived assertion was '+d['old_asserted_imdb']+
            ', with evidence present by '+observed(d['historical_evidence_present_by'])+
            '; its exact fetch time is unknown. The later listing observation at '+observed(d['current_observed_at'])+
            ' records '+d['current_listing_imdb']+'. Both observations remain visible; the discrepancy does not establish source intent or physical identity.')+'</p>')
    evidence_summary+='<p>Retained producer flags describe the recorded identification problem; they are not themselves a model verdict. Physical edition, source independence and acquisition approval remain separate from the recorded identity proposal or unresolved outcome.</p>'
    import re
    possible_incomplete=any(isinstance(result.get(field),str) and
        result[field]!=_WITHHELD_PROSE and handling.get(field,{}).get('status')!='withheld' and
        not re.search(r"[.!?][\"'”’)\]]*$",result[field].rstrip()) for field in ('rationale','uncertainty'))
    collector_observation_html=''
    if report.get('collector_reobservation') is not None:
        co=report['collector_reobservation']
        collector_observation_html=('<p>Prior collector observation: '+escape(observed(co['prior_observed_at']))+
            '; selected collector observation: '+escape(observed(co['observed_at']))+
            '. The exact selected substantive case and item facts are unchanged; both versions and the earlier report remain recorded. '
            'This does not establish the current live queue.</p>')
    separate_labels={'physical_edition_unverified':'The physical edition and cut are unverified.',
        'acquisition_unapproved':'Acquisition remains unapproved.',
        'runtime_measurements_differ':'Listing or NFO runtime differs from catalogue runtime; this alone does not identify a different film.',
        'publisher_claim_not_torrent_measurement':'Publisher edition runtime is a claim about that edition, not a measurement of the torrent.',
        'collector_resolved_outputs_missing':'Collector resolved identifiers are missing outputs, not competing identifiers.',
        'producer_flag_without_current_competing_id':'The producer conflict label has no concrete current competing identifier in the selected observations.'}
    separate_html=('<h3>Separate edition and evidence limitations</h3><ul>'+''.join('<li>'+escape(separate_labels[k])+'</li>' for k in result['separate_limitations'])+'</ul>') if 'separate_limitations' in result else ''
    quality_labels={'no_alphabetic_words':'no alphabetic words',
        'no_terminal_punctuation':'no terminal punctuation', 'trailing_conjunction':'trailing conjunction',
        'category_labels_only':'category labels only', 'identical_support_and_conflict':'identical support and conflict wording'}
    quality=result.get('explanation_quality',[])
    quality_html=''
    if quality:
        quality_html=('<p><strong>Explanation quality caveats:</strong> These finite wording checks do not establish factual correctness or alter the recorded verdict.</p><ul>'+''.join(
            '<li>Blocker '+escape(str(q['blocker']+1))+', '+escape(q['field'])+': '+escape(quality_labels[q['predicate']])+'.</li>' for q in quality)+'</ul>')
    prose_quality_html=''
    if result.get('prose_quality'):
        prose_quality_html=('<p><strong>Original explanation quality:</strong> Wording checks are advisory, not proof of truncation or factual correctness. '
            'The original wording is preserved; no ending has been invented.</p><ul>'+''.join('<li>'+escape(q['field'])+': '+escape(quality_labels[q['predicate']])+'.</li>' for q in result['prose_quality'])+'</ul>')
    model_prose=prose_quality_html+'<div style="white-space:pre-wrap">'+prose('rationale','Rationale')+prose('uncertainty','Uncertainty')+'</div>'
    if possible_incomplete:
        model_prose=('<details><summary>Original model interpretation — possibly incomplete wording</summary>'+
            '<p>At least one field lacks a terminal sentence mark and may end mid-sentence. This is only a punctuation heuristic, not a grammar test or proof of truncation. The retained text below is unchanged; no missing reasoning has been reconstructed.</p>'+model_prose+'</details>')
    temporal=''
    if 'historical_id_discrepancy' in projection:
        d=projection['historical_id_discrepancy']
        temporal='<h3>Dated same-listing ID discrepancy</h3><ul>'+li('Earlier listing-derived asserted IMDb',d['old_asserted_imdb'])+li('Historical evidence present by outcome time',observed(d['historical_evidence_present_by']))+li('Exact historical listing fetch time','Unknown')+li('Recorded case observation',observed(d['historical_case_observed_at']))+li('Later listing IMDb',d['current_listing_imdb'])+li('Later observation',observed(d['current_observed_at']))+'</ul><p>Main reviewed same-listing continuity and unchanged release/NFO linkage. The earlier assertion is retained as historical contrary evidence. Source correction intent and physical identity remain unknown; this is not identity or download approval.</p>'
    return ''.join([
        '<!doctype html><html><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'"><title>Private movie review</title><style>body{font:16px system-ui,sans-serif;line-height:1.5;max-width:70rem;margin:2rem auto;padding:0 1rem;color:#202533}h1,h2,h3{line-height:1.2;margin-top:1.5em}li{margin:.4em 0}details{margin:1.2em 0}summary{cursor:pointer;font-weight:600}pre{white-space:pre-wrap;overflow-wrap:anywhere}table{border-collapse:collapse}th,td{padding:.35em .6em;text-align:left}</style></head><body>',
        '<h1>Private movie review</h1><h2>Decision summary</h2><p><strong>'+escape(decision)+'</strong></p>',
        '<p><a rel="noreferrer noopener" href="'+escape(local['tracker_url'],quote=True)+'">Open the exact source listing</a></p>',
        '<p>The model selected this status. The local reporting path checks the bound result and observations; this does not independently verify film identity.</p>',
        ('<p>Proposed IMDb: '+escape(show(candidate.get('imdb')))+'; proposed TMDb: '+escape(show(candidate.get('tmdb')))+'.</p>' if candidate else ''),
        '<p>Identity and acquisition remain unapproved. '+escape(action)+'</p>',
        evidence_summary,
        '<h2>Identification problem</h2><p>'+escape(reason_label(projection['reason']))+'</p><ul>',
        li('Original release name',local['release_name']),li('Collector title',projection['title']),li('Collector year',projection['year']),
        li('Producer contradictions',projection['producer_contradictions']),'</ul>',
        publisher_html,collector_observation_html,separate_html,'<h2>Model-reported film blockers</h2>',quality_html,('<ul>'+blocks+'</ul>' if blockers else '<p>None reported.</p>' if 'film_blockers' in result else '<p>No structured film blockers were recorded.</p>'),
        '<p>These are the model’s selected concerns. The values shown are observations, not a claim that they caused its decision.</p>',
        '<h2>Evidence at a glance</h2><p>Agreements and differences are direct comparisons; they do not establish identity or an edition. Lists may be partial.</p>',
        '<p>Snapshot generated: '+escape(observed(projection['generated_at']))+'; listing observed: '+escape(observed(source['observed_at']))+'; catalogue observed: '+escape(observed(cat['observed_at']))+'.</p>',
        category({'exact','overlap'},'Observed agreements','No direct agreement is established.'),
        category({'different'},'Observed differences','No direct difference is established.'),
        category({'missing','no_observed_overlap'},'Missing or inconclusive observations','No missing or inconclusive comparison was recorded.'),
        '<p>NFO duration is uploader-reported for the indicated stream or container; it is not an independently measured edition.</p>',
        temporal,
        '<h2>Model assessment</h2><p>Model interpretation, distinct from the factual summary above.</p>',model_prose,fallback,
        '<h3>Separate nonblocking limitations</h3><p>Original collector bytes, current queue, complete decisions and physical edition remain unverified. Identity and acquisition remain unapproved. Listing and catalogue provenance were reviewed by the supervisor; source independence is not established.</p>',
        '<details><summary>Technical details and previous attempts</summary>',prior_html,
        '<p>Recorded status: '+escape(show(status))+'. Provider receipt is correlated, not provider-signed billing proof.</p>',
        '<h3>Computed evidence comparisons</h3><ul>',raw_comparisons,'</ul>',
        ('<h3>Film identity findings</h3><p>Reconciliations are model interpretations for human review, not verified facts.</p><h4>Model-reported findings</h4><ul>'+model_findings+'</ul>' if model_findings else ''),
        '<h3>Evidence cited by the model</h3><ul>',
        *[li('Listing' if c['evidence_id']=='source' else 'Catalogue',c['claim'].replace('_',' ')) for c in result['citations']],'</ul>',
        '<p>Retained producer flags describe the recorded identification problem, not a model verdict; matching IDs alone do not establish identity. No numeric score was assigned.</p></details>',
        '<details><summary>Retained NFO text</summary><pre>'+escape(show(local['nfo_text']))+'</pre></details></body></html>'])
