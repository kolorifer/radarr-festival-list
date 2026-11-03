"""Invented finite systems for exercising the FIXED run_pilot entry point.

This is setup DATA for tests, never a real receipt, authorization or operation.
Ledger ingestion happens here, independently of the existing-only pilot adapter.
"""
import copy
import hashlib
import uuid
from pathlib import Path

from identity_recurring_store import RecurringStore
from identity_research_provider import projection
from torrent_research_evidence import fingerprint
from .catalogue_replay import fixture_rows
from .contracts import captured_outcome, digest, encoded
from .controller import INSTRUCTIONS
from .disclosure import aliases, evidence_alias, project, row_view
from .history import History
from .parent_pilot import (FixtureParent, FixtureModelSite, code_identity,
                           ledger_identity, storage_identity, _INVENTED_STORAGE, _INVENTED_ISSUERS)
from .pilot_account import COVERAGE, FixtureCounter
from .replay import NOW, owner_decision, synthetic_case
from .research import FixtureConnection, SyntheticClock, select_plan
from .responses_http import SYNTHETIC_PROJECT
from .responses_replay import simulated_response
from .spending import POLICY
from .weekly_ledger import PROFILE


def make_fixture(directory, *, number=1278, status='supported_candidate', conflict=False):
    root = Path(directory).resolve(strict=True)
    for name in ('control', 'history', 'catalogue'):
        (root / name).mkdir(mode=0o700)
    clock = SyntheticClock(NOW)
    control = History(root / 'control', clock=clock)
    history = History(root / 'history', clock=clock)
    for h in (control, history):
        with h.transaction(write=True):
            pass
    # Independently populated native ledger: NOT material_for(packet), and not
    # admitted via any pilot method. Includes torrent material and real-shaped
    # native provenance that differ from Task6's packet-derived reconstruction.
    raw, binding, evidence = synthetic_case(number)
    te = dict(version=1, description=dict(text='Synthetic source assertion', digest=fingerprint('Synthetic source assertion')),
              nfo=dict(text='Duration : 91 min', digest=fingerprint('Duration : 91 min')),
              images=[], unavailable_images=0, truncated=False)
    raw['data']['outcome']['torrent_evidence'] = te
    if conflict:
        raw['data']['release']['meta_imdb'] = 'tt9000128'
        raw['data']['outcome'].update(status='needs_review', reason='identity_conflict', asserted_imdb='tt9000127')
    raw_bytes = encoded(raw) + b'\n'  # Original byte identity differs from canonical object.
    evidence = [r for r in evidence if r['kind'] == 'source']
    revoked = owner_decision(binding, 'intentionally_skipped', evidence=evidence)
    revoked.update(revision=2, revoked_at=NOW-10)
    previous = owner_decision(binding, 'completed_occurrence', evidence=evidence)
    previous.update(id='prior-review', scope=copy.deepcopy(binding))
    previous['scope']['occurrence']['delivery_id'] = 'prior-delivery'
    decisions = [revoked, previous]
    packet = captured_outcome(raw_bytes, sources={'synthetic':'Synthetic Index'}, binding=binding,
        evidence=evidence, decisions=decisions, trusted_issuers=['synthetic_owner'])
    job, _ = history.intake(packet)
    native = dict(case_id=binding['case_id'], seed=False, eligibility='identifier_conflict' if conflict else 'explicit_unresolved',
        observed_at=packet['event']['observed_at'], facts=dict(title='Synthetic Harbor', year=2026,
        imdb='tt9000128' if conflict else None, tmdb=None, variants=['Synthetic Harbor'],
        contradictions=['identifier_conflict'] if conflict else ['unknown_identity'], director=None,
        runtime=None, torrent_evidence=copy.deepcopy(te)), historical_candidates=[],
        provenance=[dict(source='stage1_outcome', digest=hashlib.sha256(raw_bytes).hexdigest(),
                         observed_at=packet['event']['observed_at']),
                    dict(source='stored_source_assertion', digest=digest(te), observed_at=NOW-100)])
    populated = RecurringStore(root / 'catalogue', clock=clock)
    populated.admit(native)
    plan = select_plan(packet, [dict(kind='movie_search',value='Synthetic Harbor'),
        dict(kind='details',value=dict(from_step=0,id=9000127))], native_item=native,
        issued_at=NOW, expires_at=NOW+120)
    run = 'SIMULATED-fixed-pilot-' + str(number)
    rows = fixture_rows()
    rows[1]['body']['runtime'] = 91
    catalogue_view = dict(kind='catalogue', candidate=dict(imdb='tt9000127',tmdb=9000127),
        claims=['title','year','crosswalk'], facts=dict(id=9000127,imdb='tt9000127',title='Synthetic Harbor',
        original_title=None,date='2026-01-01',type='movie',runtime=91))
    f = packet['facts']
    disclosure = dict(facts=dict(title=f['title'],year=f['year'],imdb=f['imdb'],tmdb=f['tmdb'],
        asserted_imdb=f['outcome'].get('asserted_imdb'), asserted_tmdb=f['outcome'].get('asserted_tmdb'),
        contradiction=f['outcome']['reason']),
        rows={'source-1':dict(view=row_view(evidence[0]),original_hash=digest(evidence[0])),
              'research-1':dict(view=catalogue_view,original_hash=None)})
    # Independent owner's approved expected projection. Actual returned catalogue
    # facts must equal it; the pilot cannot approve its own new observations.
    expected_catalogue = dict(id='research-1',kind='catalogue',claims=catalogue_view['claims'],
        candidate=catalogue_view['candidate'], provenance=dict(origin='SIMULATED_catalogue'),
        text='Synthetic catalogue details evidence ' + encoded(projection('details',rows[1]['body'],9000127)).decode())
    expected_prompt = dict(facts=packet['facts'], query_results=[dict(rows=[evidence[0]]),dict(rows=[expected_catalogue])],
                           reconciliation=dict(conflicting_ids=conflict))
    body = project(expected_prompt, run=run, disclosure=disclosure)
    wire_hash = digest(__import__('json').loads(body))
    storage = dict(control=storage_identity(control),history=storage_identity(history),
                   ledger=ledger_identity(root/'catalogue'))
    # Every component above was exclusively created in this function. There is
    # deliberately no API to enroll a caller's existing path or claimed receipt.
    _INVENTED_STORAGE.update((kind, digest(identity)) for kind, identity in storage.items())
    quote = dict(identity='SIMULATED-independent-quote-8', currency='TEST-USD', policy=POLICY,
        coverage=COVERAGE, ancillary='none', output_bound=4096, request_hash=wire_hash,
        input=[1,100000],cache_read=[1,200000],cache_write=[1,50000],output=[1,10000],count_maximum_fee=[1,1000000])
    count = dict(project=SYNTHETIC_PROJECT,run=run,coverage=COVERAGE,request_hash=wire_hash,
                 input_tokens=1200,fee=[1,1000000],known=True,request_id='SIMULATED-count-8')
    model_receipt = dict(project=SYNTHETIC_PROJECT,run=run,request_hash=wire_hash,
        request_id='req_SIMULATED_8',response_id='resp_SIMULATED_8',known=True)
    counter_issuer = 'counter-' + uuid.uuid4().hex
    model_issuer = 'model-' + uuid.uuid4().hex
    site = dict(synthetic=True,profile=PROFILE,project=SYNTHETIC_PROJECT,model='gpt-6.1-sol',
        quote=quote, namespace='SIMULATED-parent-project-run-8',storage=storage['control'],
        counter_issuer=counter_issuer,model_issuer=model_issuer)
    s = dict(synthetic=True,repo='invented-owner/invented-movies',owner='invented-owner',issue=127,
        issued_at=NOW,expires_at=NOW+120,run=run,namespace=site['namespace'],project=SYNTHETIC_PROJECT,
        storage=storage,reviewed_code=code_identity(),job=job,decision_hash=digest(decisions),
        research_plan=plan,site_facts=site,quote=quote,ceiling=[1,1],
        evidence_ids=['source-1','research-1'],disclosure=disclosure,preview_hash=wire_hash,
        review_date='2026-10-31',timezone='Europe/Warsaw')
    blob = encoded(s)
    sha = hashlib.sha256(blob).hexdigest()
    oid = hashlib.sha1(b'blob '+str(len(blob)).encode()+b'\0'+blob).hexdigest()
    repo = dict(repo=s['repo'],owner=s['owner'],issue=127,commit='1'*40,tree='2'*40,
        path='private/selected-pilot.json',mode='100644',regular=True,blob_oid=oid,blob_sha256=sha,bytes=len(blob))
    event = dict(repo=s['repo'],owner=s['owner'],issue=127,issuer=s['owner'],original=True,edited=False,
        command='investigate-one '+sha,commit=repo['commit'],tree=repo['tree'],path=repo['path'],
        blob_oid=oid,blob_sha256=sha,conflicting_selection=False)
    delivery = dict(event_sha256=hashlib.sha256(raw_bytes).hexdigest(),event_id=raw['id'],
        delivery_id=binding['occurrence']['delivery_id'],collector_version=binding['version'],
        source=binding['source'],release_case=binding['case_id'],delivered=True,native_item_hash=digest(native))
    occurrence = dict(original_hex=raw_bytes.hex(),delivery_receipt=delivery,packet_hash=job,
        eligible_unresolved_jobs=[job],sources={'synthetic':'Synthetic Index'},evidence=evidence,decisions=decisions,
        trusted_issuers=['synthetic_owner'],native_item=native,native_receipt=dict(event_sha256=delivery['event_sha256'],
            delivery_id=delivery['delivery_id'],native_item_hash=digest(native),collector_version=binding['version']))
    reply = dict(binding_hash=aliases(run),kind='final',lookups=[],result=dict(status=status,
        candidate=dict(imdb='tt9000127',tmdb=9000127) if status=='supported_candidate' else None,
        alternatives=[],citations=[dict(evidence_id=evidence_alias(run,'source-1'),claim='source_identity'),
                                  dict(evidence_id=evidence_alias(run,'research-1'),claim='crosswalk')],
        rationale='The supplied synthetic source assertion and catalogue crosswalk agree.',
        uncertainty='Edition, runtime and source assertions need independent verification. No score or acquisition decision.',
        next_action='verify_source_runtime_edition'))
    parent = FixtureParent(control=control,history=history,ledger_directory=root/'catalogue',clock=clock,
        owner_event=event,repository_record=repo,blob=blob,occurrence_record=occurrence,site_record=site,
        catalogue=FixtureConnection(rows),counter=FixtureCounter(count, counter_issuer),
        model=FixtureModelSite(simulated_response(reply,8),model_receipt,model_issuer))
    assert counter_issuer not in _INVENTED_ISSUERS and model_issuer not in _INVENTED_ISSUERS
    _INVENTED_ISSUERS.update({counter_issuer: (parent.counter, parent.counter.issuer),
                              model_issuer: (parent.model, parent.model.issuer)})
    return parent
