"""Pure, local-only HTML rendering for a selected captured assessment.

The caller must authenticate the selected report and local evidence/context pins
before using this renderer. It never opens a file, link, browser, or network.
"""
from html import escape
from urllib.parse import urlsplit
from .contracts import digest, require, shape


def render_private_report(report, report_hash, context, context_hash, packet):
    require(digest(report)==report_hash and digest(context)==context_hash, 'private_report_pin')
    shape(context,'tracker_url release_name nfo source_facts catalogue_facts provenance prior_failure job binding report_sha256 source_evidence_sha256 catalogue_evidence_sha256')
    from .contracts import hash_id, scope, validate_packet
    validate_packet(packet)
    require(digest(packet)==report.get('job') and packet['binding']==report.get('binding'), 'private_report_binding')
    scope(context['binding']);require(context['binding']['occurrence'] is not None,'private_report_binding');hash_id(context['source_evidence_sha256']);hash_id(context['catalogue_evidence_sha256'])
    require(context['report_sha256']==report_hash and context['job']==report.get('job') and context['binding']==report.get('binding'), 'private_report_binding')
    require(report.get('kind')=='supervised_new_case_review' and report.get('draft',{}).get('sent') is False,
            'private_report_selection')
    provenance=report.get('provenance',{});mode=provenance.get('mode')
    require(mode in ('simulation','supervised_supplied','receipt_correlated_generation'), 'private_report_provenance')
    if mode=='receipt_correlated_generation':
        require(report.get('generation_invoked') is True and report.get('provider_receipt_correlated') is True, 'private_report_provenance')
        hash_id(report.get('receipt_hash'))
    else:require(report.get('generation_invoked') is False,'private_report_provenance')
    evidence=packet['evidence']
    for kind,key in (('source','source_evidence_sha256'),('catalogue','catalogue_evidence_sha256')):
        require(any(r['kind']==kind and r['scope']==packet['binding'] and r['provenance']['digest']==context[key] for r in evidence), 'private_report_evidence_binding')
    require(context['prior_failure']=='unsupported_candidate','private_report_failure')
    assessment=report.get('assessment');require(isinstance(assessment,dict),'private_report_selection')
    require(assessment.get('status') in ('supported_candidate','unresolved','blocked'), 'private_report_selection')
    shape(context['source_facts'],'title year runtime cast edition')
    shape(context['catalogue_facts'],'title year runtime cast imdb tmdb')
    for key in ('tracker_url','release_name','nfo','provenance','prior_failure'):
        require(isinstance(context[key],str) and len(context[key])<=16384,'private_report_context')
    try:u=urlsplit(context['tracker_url'])
    except ValueError:require(False,'private_report_url')
    require(u.scheme=='https' and bool(u.hostname) and not u.username and not u.password and
            not any(ord(c)<32 for c in context['tracker_url']), 'private_report_url')
    def show(value):
        if value is None or value=='':return 'Not established'
        require(type(value) in (str,int), 'private_report_context')
        require(len(str(value))<=16384, 'private_report_context')
        return str(value)
    def line(label,value):return '<li><strong>'+escape(label)+':</strong> '+escape(show(value))+'</li>'
    source=context['source_facts'];cat=context['catalogue_facts']
    def missing(value):
        return value is None or (isinstance(value,str) and value.strip().casefold() in ('','unknown','not established','not available','unverified','n/a'))
    rows=[]
    for key in ('title','year','runtime','cast'):
        rows.append(line('Source page '+key,source[key]));rows.append(line('Catalogue '+key,cat[key]))
        left,right=source[key],cat[key]
        if missing(left) or missing(right):comparison='Missing fact; cannot compare'
        elif str(left).casefold().strip()==str(right).casefold().strip():comparison='Observed values agree'
        else:comparison='Observed values differ; review required'
        rows.append(line(key+' comparison',comparison))
    rows.extend((line('Catalogue IMDb',cat['imdb']),line('Catalogue TMDb',cat['tmdb']),
                 line('Uploader edition assertion',source['edition'])))
    body=['<!doctype html><html><head><meta charset="utf-8">',
          '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'">',
          '<title>Private captured assessment</title></head><body>',
          '<h1>Private captured assessment</h1><h2>Source</h2><ul>',
          line('Tracker link',context['tracker_url']),line('Release name',context['release_name']),
          line('Evidence provenance',context['provenance']),'</ul>',
          '<h3>Retained NFO</h3><pre>'+escape(show(context['nfo']))+'</pre>',
          '<h2>Observed facts</h2><ul>',*rows,'</ul>',
          '<p>Catalogue runtime and uploader edition are assertions; measured media runtime and physical edition remain unverified.</p>',
          '<h2>Qualifications</h2><ul>',line('Assessment provenance',mode),line('Limitations',str(report.get('qualifications','Not recorded'))),
          line('Source evidence digest',context['source_evidence_sha256']),line('Catalogue evidence digest',context['catalogue_evidence_sha256']),'</ul>',
          '<h2>Application history</h2><ul>',line('Earlier recorded failure',context['prior_failure']),'</ul>',
          '<p>An application failure does not establish film identity or edition.</p>',
          '<h2>Structured assessment</h2><ul>',line('Result',assessment['status']),
          line('Candidate',str(assessment.get('candidate'))),line('Citations',str(assessment.get('citations'))),
          line('Alternatives',str(assessment.get('alternatives'))),line('Rationale',assessment.get('rationale')),
          line('Uncertainty',assessment.get('uncertainty')),line('Next action',assessment.get('next_action')),
          line('Prose handling',str(report.get('prose_handling','Not recorded'))),'</ul>',
          '<p>Identity and acquisition require separate human approval. This report is local, unsent and does not approve a download.</p>',
          '</body></html>']
    return ''.join(body)
