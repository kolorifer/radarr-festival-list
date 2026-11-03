"""Fixed parent-callable one-occurrence pilot. Inert and DISABLED by default.

Only finite invented external systems ship. No real authorizer/project exists;
caller flags, receipts, hashes or fixture objects cannot grant live capability.
The existing dispatcher remains the sole engineering dispatcher; this is a
package operation, never a command interpreter, daemon or second runner.
"""
from dataclasses import dataclass
from datetime import date
import hashlib
from pathlib import Path
import sqlite3
import time
from zoneinfo import ZoneInfo
from identity_research_store import Stop

from .contracts import (MAX_INPUT, Refusal, captured_outcome, decode, digest, encoded,
                        identifier, reconcile, require, shape, stamp, validate_packet)
from .controller import investigate
from .disclosure import project, restore
from .history import FILENAME, History, checked, plan_retired, research_dependency, selected_current
from .installation import RUNTIME_FILES, _read
from .pilot_account import FixtureCounter, FixtureIssuer, PilotAccount
from .research import (FixtureConnection, OfflineResearch, SyntheticClock, SyntheticResearch,
                       provider_material, validate_plan)
from .responses_http import (ENDPOINT, ExplicitCredential, HTTPResult, SimulatedHTTP,
                             SYNTHETIC_CREDENTIAL, SYNTHETIC_PROJECT)
from .responses_protocol import MODEL
from .responses_transport import ResponsesTransport, SimulatedAuthorization
from .review import daily_digest
from .weekly_ledger import ExistingWeeklyLedger, PROFILE

# Process-local identities are enrolled ONLY by make_fixture after exclusive
# creation of new invented state. No receipt/flag/path can enroll existing data.
# This is a fixture fence, never a real site verifier or operational capability.
_INVENTED_STORAGE = set()
_INVENTED_ISSUERS = {}


def fixture_issuer_matches(site, identity):
    """The selected immutable enrollment binds one exact site and issuer."""
    pair = _INVENTED_ISSUERS.get(identity)
    return pair is not None and pair[0] is site and pair[1] is site.issuer and site.issuer.identity == identity


@dataclass(frozen=True)
class FixturePermit:
    project: str
    run: str
    request_hash: str
    local_request_id: str
    simulated: bool = True


class FixtureModelSite:
    """A finite fixture at the fixed-origin HTTP boundary, never network I/O."""
    def __init__(self, response, receipt, issuer_id):
        require(type(response) in (HTTPResult, TimeoutError, KeyboardInterrupt), 'pilot_fixture_response')
        self.response, self.receipt = response, decode(encoded(receipt), 4096)
        self.requests = []
        self.issuer = FixtureIssuer(issuer_id)
        self.observation = None

    def post(self, body, *, project, authorization, timeout):
        require(type(body) is bytes and body == encoded(decode(body, 65536)), 'pilot_noncanonical_wire_body')
        require(type(authorization) is FixturePermit and authorization.simulated is True and
                project == SYNTHETIC_PROJECT == authorization.project and
                authorization.request_hash == digest(decode(body, 65536)) and
                self.receipt['run'] == authorization.run and self.receipt['project'] == project and
                self.receipt['request_hash'] == authorization.request_hash,
                'pilot_http_permit_changed')
        require(not self.requests and 0 < timeout <= 25, 'pilot_http_consumed_or_expired')
        identifier(authorization.local_request_id)
        self.requests.append(dict(endpoint=ENDPOINT, project=project, permit=authorization,
                                  request_hash=authorization.request_hash, local_request_id=authorization.local_request_id))
        if isinstance(self.response, BaseException):
            raise self.response
        body = decode(self.response.body, 32768)
        receipt = dict(self.receipt, issuer=self.issuer.identity, operation='generation',
                       local_request_id=authorization.local_request_id,
                       response_sha256=hashlib.sha256(self.response.body).hexdigest(),
                       usage_hash=digest(body['usage']))
        self.observation = self.issuer._issue(receipt)
        return self.response


class FixtureParent:
    """Finite fake owner/repository/collector/site systems, all explicitly local.

    These are independent retained records, not booleans asserting live facts.
    Construction is available for tests only: exact type checks fence all effects
    to FixtureConnection, FixtureCounter and FixtureModelSite. A live parent
    authentication/site verifier remains deliberately unimplemented.
    """
    def __init__(self, *, control, history, ledger_directory, clock, owner_event,
                 repository_record, blob, occurrence_record, site_record,
                 catalogue, counter, model):
        require(type(control) is History and type(history) is History and
                type(clock) is SyntheticClock and control.clock is history.clock is clock,
                'pilot_fixture_state')
        self.control, self.history, self.clock = control, history, clock
        self.ledger_directory = Path(ledger_directory)
        self.owner_event = decode(encoded(owner_event), 16384)
        self.repository_record = decode(encoded(repository_record), 16384)
        self.blob = bytes(blob)
        self.occurrence_record = decode(encoded(occurrence_record), 131072)
        self.site_record = decode(encoded(site_record), 16384)
        self.catalogue, self.counter, self.model = catalogue, counter, model

    def authenticate(self, command):
        e, r = self.owner_event, self.repository_record
        require(e['issuer'] == e['owner'] == r['owner'] and e['repo'] == r['repo'] and
                e['issue'] == r['issue'] == 127 and e['original'] is True and e['edited'] is False,
                'pilot_owner_authentication')
        require(command == e['command'] == 'investigate-one ' + e['blob_sha256'],
                'pilot_original_command_changed')
        require(e['commit'] == r['commit'] and e['tree'] == r['tree'] and
                e['path'] == r['path'] == 'private/selected-pilot.json' and
                r['mode'] == '100644' and r['regular'] is True and
                e['blob_oid'] == r['blob_oid'] == hashlib.sha1(
                    b'blob ' + str(len(self.blob)).encode() + b'\0' + self.blob).hexdigest() and
                e['blob_sha256'] == hashlib.sha256(self.blob).hexdigest() and
                r['blob_sha256'] == e['blob_sha256'] and r['bytes'] == len(self.blob),
                'pilot_private_blob_changed')
        require(e['conflicting_selection'] is False, 'pilot_owner_selection_conflict')
        return decode(self.blob, 131072)


def storage_identity(history):
    checked(history.directory.lstat(), True)
    path = history.directory / FILENAME
    checked(path.lstat())
    return dict(path=str(history.directory), directory=list(history.identity),
                file=[path.stat().st_dev, path.stat().st_ino], filename=FILENAME)


def ledger_identity(directory):
    directory = Path(directory)
    require(directory.is_absolute() and directory.resolve(strict=True) == directory, 'pilot_ledger_path')
    path = directory / ExistingWeeklyLedger.filename
    checked(directory.lstat(), True)
    checked(path.lstat())
    return dict(path=str(directory), directory=[directory.stat().st_dev, directory.stat().st_ino],
                file=[path.stat().st_dev, path.stat().st_ino], filename=path.name)


def code_identity():
    root = Path(__file__).resolve().parent.parent
    return {name: hashlib.sha256(_read(root / name)).hexdigest() for name in RUNTIME_FILES}


def _admit(parent, s, *, events=None):
    """Separate authenticated selection, local authority and independent facts."""
    shape(s, 'synthetic repo owner issue issued_at expires_at run namespace project storage reviewed_code job '
          'decision_hash research_plan site_facts quote ceiling evidence_ids '
          'disclosure preview_hash review_date timezone')
    identifier(s['run'])
    identifier(s['namespace'])
    date.fromisoformat(s['review_date'])
    ZoneInfo(s['timezone'])
    require(s['synthetic'] is True and s['repo'] == parent.owner_event['repo'] and
            s['issue'] == 127 and s['owner'] == parent.owner_event['owner'], 'pilot_scope_changed')
    require(stamp(s['issued_at']) <= parent.clock() < stamp(s['expires_at']) and
            0 < s['expires_at'] - s['issued_at'] <= 300, 'pilot_selection_expired')
    require(s['storage'] == dict(control=storage_identity(parent.control),
        history=storage_identity(parent.history), ledger=ledger_identity(parent.ledger_directory)),
        'pilot_storage_changed')
    require(all((kind, digest(identity)) in _INVENTED_STORAGE
                for kind, identity in s['storage'].items()), 'pilot_fixture_storage_unregistered')
    require(s['storage']['control']['directory'] != s['storage']['history']['directory'],
            'pilot_storage_alias')
    require(s['reviewed_code'] == code_identity(), 'pilot_reviewed_code_changed')
    require(s['project'] == SYNTHETIC_PROJECT and parent.site_record == s['site_facts'] and
            parent.site_record['synthetic'] is True and parent.site_record['profile'] == PROFILE and
            parent.site_record['project'] == s['project'] and parent.site_record['model'] == MODEL and
            parent.site_record['quote'] == s['quote'] and
            parent.site_record['namespace'] == s['namespace'] and
            parent.site_record['storage'] == s['storage']['control'], 'pilot_site_facts_unverified')
    require(type(parent.catalogue) is FixtureConnection and type(parent.counter) is FixtureCounter and
            type(parent.model) is FixtureModelSite, 'pilot_external_boundary_unsupported')
    require(fixture_issuer_matches(parent.counter, s['site_facts']['counter_issuer']) and
            fixture_issuer_matches(parent.model, s['site_facts']['model_issuer']) and
            parent.counter.issuer.identity == s['site_facts']['counter_issuer'] and
            parent.model.issuer.identity == s['site_facts']['model_issuer'] and
            parent.counter.issuer.identity != parent.model.issuer.identity, 'pilot_external_issuer_unknown')
    events = parent.history.read() if events is None else events
    original = [e for e in events if e['type'] == 'intake' and e['job'] == s['job']]
    require(len(original) == 1, 'pilot_selected_intake_unknown')
    p = validate_packet(original[0]['packet'])
    selected_current(events, s['job'])
    require(p['hash_basis'] == 'captured_bytes' and p['event'] and p['binding']['occurrence'],
            'pilot_original_bytes_required')
    o = parent.occurrence_record
    raw = bytes.fromhex(o['original_hex'])
    receipt = o['delivery_receipt']
    require(s['job'] in o['eligible_unresolved_jobs'] and o['packet_hash'] == s['job'] and
            digest(p) == s['job'] and p['facts']['outcome']['status'] in ('unresolved','needs_review') and
            p['facts']['route'] == 'eligible' and
            reconcile(p, parent.clock())['admission'] == 'eligible', 'pilot_not_unresolved_eligible')
    require(hashlib.sha256(raw).hexdigest() == receipt['event_sha256'] == p['original_hash'] and
            receipt['event_id'] == p['event']['id'] == p['binding']['occurrence']['event_id'] and
            receipt['delivery_id'] == p['binding']['occurrence']['delivery_id'] and
            receipt['collector_version'] == p['binding']['version'] and
            receipt['source'] == p['binding']['source'] and receipt['release_case'] == p['binding']['case_id'] and
            receipt['delivered'] is True, 'pilot_independent_delivery_binding')
    rebuilt = captured_outcome(raw, sources=o['sources'], binding=p['binding'], evidence=o['evidence'],
        decisions=o['decisions'], trusted_issuers=o['trusted_issuers'])
    require(rebuilt == p and s['decision_hash'] == digest(o['decisions']), 'pilot_original_history_changed')
    validate_plan(s['research_plan'], p)
    require(s['research_plan']['schema'] == 2 and
            s['research_plan']['native_item'] == o['native_item'] and
            receipt['native_item_hash'] == digest(o['native_item']) and
            o['native_receipt']['event_sha256'] == p['original_hash'] and
            o['native_receipt']['delivery_id'] == receipt['delivery_id'] and
            o['native_receipt']['native_item_hash'] == receipt['native_item_hash'] and
            o['native_receipt']['collector_version'] == receipt['collector_version'], 'pilot_native_binding')
    require(s['research_plan']['material'] == provider_material(o['native_item']), 'pilot_native_material_changed')
    require(not plan_retired(events, s['job'], digest(s['research_plan'])), 'research_plan_revoked')
    return p


class SingleResponsesTransport(ResponsesTransport):
    def __init__(self, parent, selection, packet, guard):
        self.parent, self.selection, self.guard = parent, selection, guard
        self.account = PilotAccount(parent.control, selection, parent.counter, parent.model)
        super().__init__(enabled=True, http=SimulatedHTTP([]),
            credential=ExplicitCredential(SYNTHETIC_CREDENTIAL),
            authorization=SimulatedAuthorization(encoded(packet), selection['issued_at'], selection['expires_at']),
            clock=parent.clock)

    def _body(self, payload, schema):
        # Original local validator checks exact packet/decisions/lookups. Its
        # unminimized body is never sent or used as a preview.
        super()._body(payload, schema)
        return project(decode(payload, MAX_INPUT), run=self.selection['run'], disclosure=self.selection['disclosure'])

    def final_boundary(self, events):
        self.guard(events)

    def prepare(self, payload, *, schema):
        self.guard()
        reservation = super().prepare(payload, schema=schema)
        body = self.pending[0]
        require(digest(decode(body, 65536)) == self.selection['preview_hash'], 'pilot_preview_changed')
        self.generation_id = reservation['local_request_id']
        self.account.reserve(body, self.generation_id)
        reservation['monetary_reservation'] = 'parent-selected-TEST-account'
        self.pending = (body, reservation, self.pending[2])
        return reservation

    def _post(self, body, *, timeout):
        self.guard()
        self.account.send(body, self.generation_id)
        permit = FixturePermit(self.selection['project'], self.selection['run'], digest(decode(body, 65536)), self.generation_id)
        result = self.parent.model.post(body, project=self.selection['project'], authorization=permit, timeout=timeout)
        self.returned_response_sha256 = hashlib.sha256(result.body).hexdigest()
        return result

    def complete(self, payload, *, schema, timeout):
        answer = super().complete(payload, schema=schema, timeout=timeout)
        # Settle known transport usage even if currentness/retirement will now
        # reject the proposal. Unknown receipts retain the entire reservation.
        self.account.settle(self.last_accounting, self.parent.model.observation, self.returned_response_sha256)
        self.guard()
        restored = restore(decode(answer), run=self.selection['run'], disclosure=self.selection['disclosure'],
                           binding_hash=digest(decode(self.authorization.packet_json, MAX_INPUT)['binding']))
        return encoded(restored)


def run_pilot(parent=None, *, command=None, enabled=False):
    """The sole fixed pilot operation. Returns one private review record.

    No CLI, generic callback/URL/root override, real permit, environment lookup,
    daemon or recovery runner. All fake external effects occur after admission.
    """
    require(enabled is True, 'pilot_disabled')
    require(type(parent) is FixtureParent, 'pilot_real_parent_verifier_unimplemented')
    try:
        s = parent.authenticate(command)
        original = _admit(parent, s)
    except Refusal:
        raise
    except (OSError, ValueError, KeyError, TypeError):
        raise Refusal('pilot_admission_contract_invalid') from None
    # Hold the existing control lock and the ledger's write transaction while
    # checking the current oldest native job and appending the pilot claim.
    # The later selected lease repeats its gates atomically before any GET.
    try:
        ledger = ExistingWeeklyLedger(parent.ledger_directory, clock=parent.clock, profile=s['site_facts']['profile'])
        with parent.control.transaction(write=True) as (control_events, append):
            require(not any(e['type'] == 'pilot_claim' for e in control_events), 'pilot_run_already_consumed')
            # Keep the original occurrence current while the ledger is checked
            # and the control claim is appended. Lock order: control, history,
            # ledger; research's existing nested order is history then ledger.
            with parent.history.transaction() as (history_events, _):
                _admit(parent, s, events=history_events)
                with ledger.tx() as c:
                    plan = s['research_plan']
                    row = c.execute('select j.*,e.material from jobs j join evidence e on e.version=j.version '
                                    'where j.status="queued" and j.due<=? order by j.due,j.case_id limit 1',
                                    (parent.clock(),)).fetchone()
                    require(row is not None and row['case_id'] == plan['binding']['case_id'] and
                            row['version'] == plan['provider_version'] and
                            decode(row['material'], MAX_INPUT) == plan['material'] and
                            not c.execute('select 1 from attempts where version=?', (row['version'],)).fetchone(),
                            'pilot_ledger_material_unbound')
                    require(parent.authenticate(command) == s, 'pilot_selection_changed')
                    _admit(parent, s, events=history_events)
                    append(dict(type='pilot_claim', at=parent.clock(), run=s['run'], namespace=s['namespace'],
                                project=s['project'], selection_hash=digest(s), selection=s,
                                owner_event=parent.owner_event, repository_record=parent.repository_record,
                                selection_blob_hex=parent.blob.hex(),
                                occurrence_record=parent.occurrence_record, simulated=True))
    except Refusal:
        raise
    except (OSError, ValueError, KeyError, TypeError, Stop, sqlite3.Error):
        raise Refusal('pilot_preclaim_ledger_refused') from None
    started = time.monotonic()
    last_current = parent.clock()
    original_decisions = digest(reconcile(original, last_current)['prior_decisions'])
    retained_occurrence_hash = digest(parent.occurrence_record)
    retained_counter, retained_model = parent.counter, parent.model
    derived = None

    def guard(events=None, *, check_current=True):
        nonlocal last_current
        last_current = max(last_current, parent.clock(), s['issued_at'] + time.monotonic() - started)
        require(last_current < s['expires_at'] and time.monotonic() - started < 120, 'pilot_expired')
        require(parent.authenticate(command) == s, 'pilot_selection_changed')
        require(parent.site_record == s['site_facts'] and parent.counter is retained_counter and
                parent.model is retained_model and
                fixture_issuer_matches(parent.counter, s['site_facts']['counter_issuer']) and
                fixture_issuer_matches(parent.model, s['site_facts']['model_issuer']) and
                parent.counter.issuer.identity == s['site_facts']['counter_issuer'] and
                parent.model.issuer.identity == s['site_facts']['model_issuer'], 'pilot_external_facts_changed')
        require(digest(parent.occurrence_record) == retained_occurrence_hash, 'pilot_original_history_changed')
        require(s['storage'] == dict(control=storage_identity(parent.control), history=storage_identity(parent.history),
                ledger=ledger_identity(parent.ledger_directory)), 'pilot_storage_changed')
        require(code_identity() == s['reviewed_code'], 'pilot_reviewed_code_changed')
        events = parent.history.read() if events is None else events
        if check_current:
            selected_current(events, derived or s['job'])
        require(not plan_retired(events, s['job'], digest(s['research_plan'])), 'research_plan_revoked')
        if derived:
            research_dependency(events, derived)
        require(digest(reconcile(original, last_current)['prior_decisions']) == original_decisions,
                'pilot_decisions_changed')

    try:
        guard()
        broker = OfflineResearch(enabled=True, history=parent.history, store=ledger, connection=parent.catalogue,
            authorization=SyntheticResearch(digest(original), digest(s['research_plan'])), monotonic=parent.clock,
            boundary_guard=lambda events: guard(events, check_current=False))
        derived, packet, receipts = broker.run(s['job'], s['research_plan'])
        guard()
        transport = SingleResponsesTransport(parent, s, packet, guard)
        result = investigate(parent.history, derived, s['run'], transport, preselected=s['evidence_ids'])
        guard()
        review = daily_digest(parent.history, selected_date=s['review_date'], timezone=s['timezone'])
        review['pilot_accounting'] = [e for e in parent.control.read() if e['type'] in
            ('pilot_count_reserved','pilot_count_settled','pilot_model_reserved','pilot_model_settled','pilot_usage_observed')]
        review['text'] += '\nSIMULATED fixed pilot: one selected occurrence; at most one generation. ' + \
            'TEST accounting is retained; unknown charges hold their maximum. ' + \
            'No real identification, scoring decision, acquisition permission or live readiness.'
        # The exact durable, timestamped result (not the controller return copy)
        # and review bytes bind the archive to the selected destination.
        with parent.history.transaction(write=True) as (events, append):
            guard(events)
            selected_current(events, derived)
            research_dependency(events, derived)
            require(parent.clock() < s['expires_at'], 'pilot_expired')
            stored = [e for e in events if e['type'] == 'result' and e['job'] == derived]
            require(len(stored) == 1, 'pilot_result_missing')
            record = dict(type='pilot_review', at=parent.clock(), run=s['run'], job=derived,
                selection_hash=digest(s), result_hash=digest(stored[0]), review=review,
                review_hash=digest(review), archive_identity=s['storage']['history'], simulated=True,
                real_ready=False, production_identity_verified=False, download_consent=False)
            append(record)
        with parent.control.transaction(write=True) as (_, append):
            append(dict(type='pilot_terminal', at=parent.clock(), run=s['run'], result_hash=record['result_hash'],
                        review_hash=record['review_hash'], archive_hash=digest(record), simulated=True))
        return record
    except (Refusal, OSError, ValueError, KeyError, TypeError, Stop) as exc:
        reason = str(exc) if isinstance(exc, Refusal) else 'pilot_shared_ledger_refused' if isinstance(exc, Stop) else 'pilot_local_contract_failed'
        with parent.control.transaction(write=True) as (_, append):
            append(dict(type='pilot_failed_unknown', at=parent.clock(), run=s['run'], reason=reason, simulated=True))
        raise Refusal(reason) from None
