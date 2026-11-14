"""Pure, local-only HTML rendering for a selected captured assessment.

The caller must authenticate the selected report and local evidence/context pins
before using this renderer. It never opens a file, link, browser, or network.
"""
from html import escape
from urllib.parse import urlsplit
from .contracts import digest, require, shape


def validate_local_context(local):
    """Validate only reviewed local facts before any preparation or send."""
    shape(local,'tracker_url release_name nfo source_facts catalogue_facts provenance')
    shape(local['source_facts'],'title year runtime cast edition imdb tmdb')
    shape(local['catalogue_facts'],'title year runtime cast imdb tmdb')
    for key in ('tracker_url','release_name','nfo','provenance'):
        require(isinstance(local[key],str) and len(local[key])<=16384,'private_report_context')
    try:
        u=urlsplit(local['tracker_url'])
        for value in (local['tracker_url'],local['release_name'],local['nfo'],local['provenance']):value.encode('utf-8')
        for facts in (local['source_facts'],local['catalogue_facts']):
            for value in facts.values():
                if value is None:continue
                if isinstance(value,list):
                    require(len(value)<=64 and all(isinstance(x,str) and len(x)<=300 for x in value),'private_report_context')
                    for x in value:x.encode('utf-8')
                else:
                    require(type(value) in (str,int) and len(str(value))<=16384,'private_report_context')
                    str(value).encode('utf-8')
    except (ValueError,UnicodeError):require(False,'private_report_context')
    require(u.scheme=='https' and bool(u.hostname) and not u.username and not u.password and
            not any(ord(c)<32 for c in local['tracker_url']), 'private_report_url')
    return local


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
    validate_local_context({k:context[k] for k in ('tracker_url','release_name','nfo','source_facts','catalogue_facts','provenance')})
    for key in ('tracker_url','release_name','nfo','provenance','prior_failure'):
        require(isinstance(context[key],str) and len(context[key])<=16384,'private_report_context')
    try:u=urlsplit(context['tracker_url'])
    except ValueError:require(False,'private_report_url')
    require(u.scheme=='https' and bool(u.hostname) and not u.username and not u.password and
            not any(ord(c)<32 for c in context['tracker_url']), 'private_report_url')
    def show(value):
        if value is None or value=='':return 'Not established'
        if isinstance(value,list):
            require(len(value)<=64 and all(isinstance(x,str) and len(x)<=300 for x in value),'private_report_context')
            value=', '.join(value)
        require(type(value) in (str,int), 'private_report_context')
        require(len(str(value))<=16384, 'private_report_context')
        return str(value)
    def line(label,value):return '<li><strong>'+escape(label)+':</strong> '+escape(show(value))+'</li>'
    source=context['source_facts'];cat=context['catalogue_facts']
    def missing(value):
        return value is None or (isinstance(value,str) and value.strip().casefold() in ('','unknown','not established','not available','unverified','n/a'))
    def compare(key,left,right):
        if missing(left) or missing(right):return 'Missing fact; cannot compare'
        if key in ('runtime','year'):
            if type(left) is not int or type(right) is not int or left<=0 or right<=0:return 'Untyped or missing value; cannot compare'
            return 'Values agree' if left==right else 'Values differ; review required'
        if key=='cast':
            if not isinstance(left,(str,list)) or not isinstance(right,(str,list)):return 'Untyped or missing value; cannot compare'
            a={x.strip().casefold() for x in (left.split(',') if isinstance(left,str) else left) if isinstance(x,str) and not missing(x)}
            b={x.strip().casefold() for x in (right.split(',') if isinstance(right,str) else right) if isinstance(x,str) and not missing(x)}
            if not a or not b:return 'Missing fact; cannot compare'
            return 'Shared cast; lists may be incomplete' if a&b else 'No shared names in supplied lists; review needed'
        return 'Values agree' if str(left).casefold().strip()==str(right).casefold().strip() else 'Different wording; review needed'
    rows=[]
    for key in ('title','year','runtime','cast','imdb','tmdb'):
        rows.append('<tr><th>'+escape(key.title())+'</th><td>'+escape(show(source[key]))+'</td><td>'+escape(show(cat[key]))+'</td><td>'+escape(compare(key,source[key],cat[key]))+'</td></tr>')
    candidate=assessment.get('candidate')
    candidate_text=('IMDb '+str(candidate.get('imdb'))+', TMDb '+str(candidate.get('tmdb'))) if isinstance(candidate,dict) else 'No candidate established'
    cites=assessment.get('citations',[])
    require(isinstance(cites,list) and all(isinstance(c,dict) and set(c)=={'evidence_id','claim'} and isinstance(c['evidence_id'],str) and isinstance(c['claim'],str) for c in cites),'private_report_selection')
    roles={}
    for index,row in enumerate(packet['evidence']):
        if row['scope']!=packet['binding']:continue
        if row['provenance']['digest']==context['source_evidence_sha256'] and row['kind']=='source':roles['evidence-'+str(index+1)]='Source assertion'
        if row['provenance']['digest']==context['catalogue_evidence_sha256'] and row['kind']=='catalogue':roles['evidence-'+str(index+1)]='Catalogue external-ID mapping'
    cite_lines=['<li>'+escape(roles.get(c['evidence_id'],'Retained evidence'))+' ('+escape(c['evidence_id'])+') — '+escape(c['claim'].replace('_',' '))+'</li>' for c in cites]
    if not cite_lines:cite_lines=['<li>No citations were supplied in the accepted result.</li>']
    body=['<!doctype html><html><head><meta charset="utf-8">',
          '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'">',
          '<title>Private captured assessment</title></head><body>',
          '<h1>Private captured assessment</h1><h2>1. Original release</h2><ul>',
          '<li><strong>Tracker:</strong> <a rel="noreferrer noopener" href="'+escape(context['tracker_url'],quote=True)+'">Open the original source</a></li>',
          line('Release name',context['release_name']),'</ul>',
          '<details><summary>Retained NFO</summary><pre>'+escape(show(context['nfo']))+'</pre></details>',
          '<h2>2. Identification problem</h2><p>The earlier application attempt could not validate the proposed candidate because the cited evidence was not bound to that candidate. This evidence-binding failure does not establish a film or edition mismatch.</p><table><thead><tr><th>Fact</th><th>Source page</th><th>Catalogue</th><th>Comparison</th></tr></thead><tbody>',*rows,'</tbody></table>',
          '<p>Uploader edition assertion: '+escape(show(source['edition']))+'. Catalogue and source-page runtimes are not measured media runtime. Physical edition remains unverified.</p>',
          '<h2>3. Assessment and evidence</h2><ul>',line('Result',assessment['status'].replace('_',' ')),
          line('Proposed candidate',candidate_text),line('Model rationale',assessment.get('rationale')),
          line('Uncertainty',assessment.get('uncertainty')),line('Next action',str(assessment.get('next_action','unknown')).replace('_',' ')),'</ul>',
          '<h3>Cited evidence</h3><ul>',*cite_lines,'</ul>',
          '<p>This is a review proposal, not identity or acquisition approval. The report is local and unsent; no download is approved.</p>',
          '<details><summary>Evidence and execution details</summary><ul>',line('Assessment provenance',mode),
          line('Evidence provenance',context['provenance']),line('Source evidence digest',context['source_evidence_sha256']),
          line('Catalogue evidence digest',context['catalogue_evidence_sha256']),line('Limitations',str(report.get('qualifications','Not recorded'))),
          line('Prose handling',str(report.get('prose_handling','Not recorded'))),line('Earlier application failure',context['prior_failure']),
          '</ul><p>An application failure does not establish film identity or edition.</p></details>',
          '</body></html>']
    return ''.join(body)
