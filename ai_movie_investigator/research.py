"""Explicit offline catalogue stage. The live bridge is deliberately absent.

Reuses Provider's route/projection and RecurringStore's actual durable ledger.
Only finite data fixtures can be connections. Nothing here discovers a source,
credential, ledger or account; a plan cannot authorize a real operation.
"""
import copy
from dataclasses import dataclass
import time

from identity_recurring_store import RecurringStore
from identity_research_provider import Provider, route, validate_case
from .contracts import (MAX_INPUT, decode, digest, encoded, evidence_row,
                        reconcile, require, scope, shape, stamp, text, validate_packet)
from .history import History, checked, plan_retired, research_dependency

RESEARCH_SECONDS = 60
FIXTURE_TOKEN = 'SIMULATED-CATALOGUE-NOT-A-KEY'


def real_research_refusal(*args, **kwargs):
    return 'research_live_ledger_and_authorization_unimplemented'


def material_for(packet):
    """Exact deterministic correspondence, not equality of two digest schemes.

    No title join. The retained packet's entire material digest is provenance;
    source/intake version and provider-normalized material version stay separate.
    """
    validate_packet(packet)
    f = packet['facts']
    return validate_case(dict(case_id=packet['binding']['case_id'], seed=False,
        eligibility='explicit_unresolved', observed_at=packet['event']['observed_at'] if packet['event'] else 1,
        facts=dict(title=f['title'], year=f['year'], imdb=f['imdb'], tmdb=f['tmdb'],
                   variants=[f['title']], contradictions=['unknown_identity'], director=None, runtime=None),
        provenance=[dict(source='stage1_outcome', digest=digest(packet),
                         observed_at=packet['event']['observed_at'] if packet['event'] else 1)],
        historical_candidates=[]))


def provider_material(item):
    result = {k: copy.deepcopy(v) for k, v in item.items() if k != 'observed_at'}
    result['provenance'] = [{**p, 'observed_at': 1} for p in item['provenance']]
    return result


def select_plan(packet, operations, *, issued_at, expires_at):
    """Trusted supervisor selection, usable only with synthetic capability.

    There is no real-authorizer implementation. Supplying this template, even
    with real-looking hashes/timestamps, does not grant a live capability.
    """
    material = provider_material(material_for(packet))
    plan = dict(schema=1, binding=packet['binding'], packet_hash=digest(packet),
                original_hash=packet['original_hash'], evidence_hash=digest(packet['evidence']),
                decision_hash=digest(packet['decisions']), material=material,
                provider_version=digest(material), operations=operations,
                source_observed_at=packet['event']['observed_at'] if packet['event'] else None,
                issued_at=issued_at, expires_at=expires_at, synthetic=True)
    plan = decode(encoded(plan), MAX_INPUT)
    validate_plan(plan, packet)
    return plan


def validate_plan(plan, packet):
    validate_packet(packet)
    shape(plan, 'schema binding packet_hash original_hash evidence_hash decision_hash material provider_version operations source_observed_at issued_at expires_at synthetic')
    require(type(plan['schema']) is int and plan['schema'] == 1 and plan['synthetic'] is True,
            'research_plan_schema')
    require(scope(plan['binding']) == packet['binding'] and
            plan['packet_hash'] == digest(packet) and plan['original_hash'] == packet['original_hash'] and
            plan['evidence_hash'] == digest(packet['evidence']) and
            plan['decision_hash'] == digest(packet['decisions']), 'research_binding_changed')
    material = provider_material(material_for(packet))
    require(plan['material'] == material and plan['provider_version'] == digest(material),
            'research_material_correspondence')
    require(plan['source_observed_at'] == (packet['event']['observed_at'] if packet['event'] else None),
            'research_source_clock_changed')
    require(0 < stamp(plan['expires_at']) - stamp(plan['issued_at']) <= 300,
            'research_plan_expiry')
    ops = plan['operations']
    require(isinstance(ops, list) and 1 <= len(ops) <= 5, 'research_operation_limit')
    facts = packet['facts']
    selected_evidence = [e for e in packet['evidence'] if e['scope'] == packet['binding'] and e['candidate']]
    selected_ids = {facts['tmdb']} | {e['candidate']['tmdb'] for e in selected_evidence}
    selected_imdb = {facts['imdb'], facts['outcome'].get('asserted_imdb')}
    selected_imdb |= {e['candidate']['imdb'] for e in selected_evidence}
    for index, op in enumerate(ops):
        shape(op, 'kind value')
        kind, value = op['kind'], op['value']
        if kind == 'details' and isinstance(value, dict):
            shape(value, 'from_step id')
            require(type(value['from_step']) is int and 0 <= value['from_step'] < index and
                    ops[value['from_step']]['kind'] in ('find', 'movie_search'), 'research_detail_dependency')
            route(kind, value['id'])
        else:
            route(kind, value)  # Same fixed catalogue GET allowlist as Provider.
            if kind == 'find':
                require(value in selected_imdb and value is not None, 'research_imdb_not_selected')
            elif kind == 'details':
                require(value in selected_ids and value is not None, 'research_detail_not_selected')
            else:
                text(value, 250)
                require(value in material['facts']['variants'], 'research_query_not_selected')
    return plan


@dataclass(frozen=True)
class SyntheticResearch:
    packet_hash: str
    plan_hash: str


class FixtureConnection:
    """Strict finite wire DATA, never a callback, URL opener or subclass hook."""
    def __init__(self, rows):
        require(isinstance(rows, list) and 1 <= len(rows) <= 5, 'research_fixture_limit')
        self.rows = []
        for row in rows:
            shape(row, 'kind value status body fault')
            route(row['kind'], row['value'])
            require(type(row['status']) is int and row['status'] in
                    (200, 301, 302, 307, 308, 401, 403, 404, 429, 500, 503), 'research_fixture_status')
            require(row['fault'] in (None, 'send_timeout', 'send_interrupt', 'response_interrupt'),
                    'research_fixture_fault')
            body = row['body'] if type(row['body']) is bytes else encoded(row['body'])
            require(len(body) <= 1048576, 'research_fixture_size')
            self.rows.append(dict(path=route(row['kind'], row['value']), status=row['status'],
                                  body=body, fault=row['fault']))
        self.requests = []
        self.pending = None

    def request(self, method, path, *, headers):
        require(method == 'GET' and headers == {'Authorization': 'Bearer ' + FIXTURE_TOKEN,
                'Accept': 'application/json'}, 'research_fixture_request')
        require(self.pending is None and self.rows and self.rows[0]['path'] == path,
                'research_fixture_path_changed')
        row = self.rows.pop(0)
        self.requests.append(dict(method=method, path=path))
        self.pending = row
        if row['fault'] == 'send_interrupt':
            raise KeyboardInterrupt()
        if row['fault'] == 'send_timeout':
            raise TimeoutError()

    def getresponse(self):
        require(self.pending is not None, 'research_fixture_response')
        row, self.pending = self.pending, None
        if row['fault'] == 'response_interrupt':
            raise KeyboardInterrupt()
        return _FixtureResponse(row)

    def close(self):
        self.pending = None


class _FixtureResponse:
    def __init__(self, row):
        self.status, self.body = row['status'], row['body']

    def getheader(self, name, default=None):
        return {'Content-Type': 'application/json', 'Content-Length': str(len(self.body)),
                'Retry-After': '900'}.get(name, default)

    def read(self, limit):
        return self.body[:limit]


class OfflineResearch:
    def __init__(self, *, enabled=False, history=None, store=None, connection=None,
                 authorization=None, monotonic=time.monotonic):
        self.enabled, self.history, self.store = enabled, history, store
        self.connection, self.authorization = connection, authorization
        self.monotonic = monotonic

    def preflight(self):
        if self.enabled is not True:
            return 'research_disabled'
        if type(self.authorization) is not SyntheticResearch or type(self.connection) is not FixtureConnection:
            return real_research_refusal()
        if type(self.store) is not RecurringStore or type(self.history) is not History:
            return 'research_shared_store_required'
        if type(self.store.clock) is not SyntheticClock or self.history.clock is not self.store.clock:
            return 'research_synthetic_clock_required'
        return None

    def run(self, job, plan):
        refusal = self.preflight()
        require(refusal is None, refusal or 'research_denied')
        plan = decode(encoded(plan), MAX_INPUT)
        plan_hash = digest(plan)
        require(self.authorization == SyntheticResearch(plan['packet_hash'], plan_hash),
                'research_selection_changed')
        started = self.monotonic()
        last_tick, current = started, stamp(self.history.clock())
        packet = next((e['packet'] for e in self.history.read()
                       if e['type'] == 'intake' and e['job'] == job), None)
        require(packet is not None, 'unknown_job')
        validate_plan(plan, packet)
        selected_decisions = digest(reconcile(packet, current)['prior_decisions'])
        pin = [(p.lstat().st_dev, p.lstat().st_ino) for p in (self.store.directory, self.store.path)]

        def check_ledger():
            self.store.check()
            require(self.store.directory.resolve(strict=True) == self.store.directory and
                    pin == [(p.lstat().st_dev, p.lstat().st_ino)
                            for p in (self.store.directory, self.store.path)], 'research_ledger_replaced')
            checked(self.store.directory.lstat(), True)
            checked(self.store.path.lstat())

        def guard(events, selected=job):
            nonlocal last_tick, current
            tick = self.monotonic()
            # Rollback never extends a deadline or refreshes source evidence.
            current = stamp(max(stamp(self.history.clock()), current + max(0, tick - last_tick)))
            last_tick = max(last_tick, tick)
            require(tick - started < RESEARCH_SECONDS and
                    plan['issued_at'] <= current < plan['expires_at'], 'research_deadline')
            require(self.store.clock() >= current - .001 and self.store.clock() <= current + .001,
                    'research_ledger_clock_changed')
            check_ledger()
            latest = [e for e in events if e['type'] == 'intake' and
                      e['packet']['binding']['case_id'] == packet['binding']['case_id']][-1]
            require(latest['job'] == selected, 'research_case_superseded')
            require(not plan_retired(events, job, plan_hash),
                    'research_plan_revoked')
            reconciliation = reconcile(packet, current)
            require(reconciliation['admission'] == 'eligible', 'research_case_ineligible')
            require(digest(reconciliation['prior_decisions']) == selected_decisions,
                    'research_decision_applicability_changed')
            require(packet['event'] and packet['event']['observed_at'] <= current,
                    'research_source_clock_unverified')
            source_rows = [r for r in packet['evidence']
                           if r['kind'] == 'source' and r['scope'] == packet['binding']]
            require(bool(source_rows) and all(r['observed_at'] <= current and
                    r['expires_at'] is not None and current < r['expires_at'] for r in source_rows),
                    'research_source_freshness_unverified')
            return current

        # Selection is consumed before lease/provider operations, including an
        # interrupted start. No plan rename creates another same-job attempt.
        with self.history.transaction(write=True) as (events, append):
            at = guard(events)
            require(not any(e['type'] == 'research_started' and e['binding'] == packet['binding'] for e in events),
                    'research_attempt_consumed')
            append(dict(type='research_started', at=at, job=job, plan_hash=plan_hash,
                        binding=packet['binding'], provider_version=plan['provider_version'], plan=plan, synthetic=True))
        # Admission happens only in the explicit synthetic demonstration setup;
        # the broker never creates a replacement ledger, admits or resets jobs.
        with self.store.tx() as c:
            row = c.execute('select j.*,e.material from jobs j join evidence e on e.version=j.version '
                            'where j.status="queued" order by j.due,j.case_id limit 1').fetchone()
            require(row is not None and row['case_id'] == plan['binding']['case_id'] and
                    row['version'] == plan['provider_version'] and
                    decode(row['material'], MAX_INPUT) == plan['material'], 'research_ledger_material_unbound')
        run = self.store.start()
        results, receipts = [], []
        try:
            lease = self.store.lease(run)
            require(lease is not None and lease['case_id'] == plan['binding']['case_id'] and
                    lease['version'] == plan['provider_version'] and lease['item'] == plan['material'],
                    'research_lease_unbound')
            broker = self

            class BoundStore:
                def reserve(self, selected_run, token, key):
                    with broker.history.transaction(write=True) as (events, append):
                        at = guard(events)
                        require(selected_run == run and token == lease['token'] and key == expected_key,
                                'research_reservation_changed')
                        request, cached = broker.store.reserve(run, token, key)
                        # Cache history must bind the same selected occurrence
                        # and plan. A generic shared title cache is no authority.
                        cached_receipts = [e for e in events if e['type'] == 'research_observed' and
                                           e['plan_hash'] == plan_hash and e['binding'] == packet['binding'] and
                                           e['key'] == key and e['result'] == cached]
                        require(cached is None or bool(cached_receipts), 'research_cache_unbound')
                        provenance.update(request=request, cache_of=digest(cached_receipts[-1]) if cached else None,
                                          reserved_at=at, key=key, lease=token, run=run)
                        append(dict(type='research_reserved', at=at, job=job, plan_hash=plan_hash,
                                    binding=packet['binding'], provider_version=lease['version'],
                                    provenance=dict(provenance), synthetic=True))
                        return request, cached

                def record(self, request, key, result):
                    # Always retain provider quota effects, even when a response
                    # is too late to be used by the investigator.
                    check_ledger()
                    try:
                        safe_projection(result.get('data'))
                        require(len(encoded(result)) <= 12000, 'research_projection_limit')
                    except ValueError:
                        at = result['observed_at']
                        result.clear()
                        result.update(reason='malformed_response', observed_at=at)
                    broker.store.record(request, key, result)

            def advance(seconds):
                # Provider's shared cooldown is real ledger state. The finite
                # fixture has an explicit virtual clock, no actual sleep/I/O.
                require(type(self.store.clock) is SyntheticClock and
                        self.history.clock is self.store.clock, 'research_synthetic_clock_required')
                self.store.clock.advance(seconds)

            provider = Provider(BoundStore(), run, self.connection, FIXTURE_TOKEN,
                                clock=self.store.clock, sleep=advance)
            for index, op in enumerate(plan['operations']):
                with self.history.transaction() as (events, _):
                    guard(events)
                value = op['value']
                if isinstance(value, dict):
                    prior = results[value['from_step']]
                    rows = prior['data'].get('movies', prior['data'].get('results', []))
                    require(value['id'] in {r['id'] for r in rows if r['type'] == 'movie'},
                            'research_detail_not_returned')
                    value = value['id']
                expected_key = digest([op['kind'], value])
                provenance = dict(ledger_epoch='recurring-v1', ledger_identity=digest(pin),
                                  source_version=packet['binding']['version'], material_version=lease['version'])
                result = provider.get(lease, op['kind'], value)
                with self.history.transaction(write=True) as (events, append):
                    at = guard(events)
                    require(result['reason'] == 'ok', 'research_provider_' + result['reason'])
                    require(stamp(result['observed_at']) <= at < stamp(result['expires_at']),
                            'research_evidence_stale_or_future')
                    # Validate all projected descriptive strings before they
                    # enter durable evidence; never retain a raw provider body.
                    safe_projection(result['data'])
                    require(len(encoded(result)) <= 12000, 'research_projection_limit')
                    receipt = dict(type='research_observed', at=at, job=job, binding=packet['binding'],
                                   plan_hash=plan_hash, step=index, kind=op['kind'], value=value, key=expected_key,
                                   original_hash=packet['original_hash'], provenance=dict(provenance),
                                   result=result, synthetic=True)
                    append(receipt)
                    results.append(result)
                    receipts.append(receipt)
            with self.history.transaction() as (events, _):
                guard(events)
            enriched = enriched_packet(packet, receipts)
            self.store.finish(lease, dict(reason='candidate_review', evidence_hash=digest(receipts), synthetic=True))
            dependency = dict(original_job=job, binding=packet['binding'], plan_hash=plan_hash,
                              receipts=[digest(r) for r in receipts])
            new_job, _ = self.history.intake(enriched, guard=guard, research_binding=dependency)
            with self.history.transaction(write=True) as (events, append):
                guard(events, selected=new_job)
                require(all(current < r['result']['expires_at'] for r in receipts), 'research_evidence_expired')
                research_dependency(events, new_job, completing=True)
                append(dict(type='research_complete', at=current, job=new_job, original_job=job,
                            plan_hash=plan_hash, receipts=[digest(r) for r in receipts],
                            simulated_gets=sum(r['provenance']['request'] is not None for r in receipts), synthetic=True))
            return new_job, enriched, receipts
        finally:
            # Cleanup must never reopen a replaced ledger after an earlier
            # guard refused it. Leave the original run/attempt consumed.
            check_ledger()
            self.store.end(run)


class SyntheticClock:
    def __init__(self, value):
        self.value = stamp(value)

    def __call__(self):
        return self.value

    def advance(self, seconds):
        require(type(seconds) in (int, float) and 0 <= seconds <= 60, 'research_clock_advance')
        self.value += seconds


def safe_projection(value):
    if isinstance(value, str):
        # JSON escaping can hide an echo from Provider's raw-byte check. This
        # route has only this fixed synthetic credential; no real key is read.
        require(FIXTURE_TOKEN not in value, 'research_credential_echo')
        text(value, 512)
    elif isinstance(value, dict):
        for child in value.values():
            safe_projection(child)
    elif isinstance(value, list):
        for child in value:
            safe_projection(child)


def enriched_packet(packet, receipts):
    """Deterministic projection shared by the broker and locked handoff verifier."""
    enriched = copy.deepcopy(packet)
    for receipt in receipts:
        data = receipt['result']['data']
        candidate = (dict(imdb=data['imdb'], tmdb=data['id'])
                     if receipt['kind'] == 'details' and data['imdb'] else None)
        catalogue_rows = ([data] if receipt['kind'] == 'details' else
                          data.get('movies', []) + data.get('tv', []) + data.get('results', []))
        claims = ['title'] if catalogue_rows else []
        if any(r.get('date') and len(r['date']) >= 4 and r['date'][:4].isdigit()
               for r in catalogue_rows):
            claims.append('year')
        if candidate:
            claims.append('crosswalk')
        row = dict(id='research-' + str(receipt['step']), kind='catalogue', scope=packet['binding'],
                   observed_at=receipt['result']['observed_at'], expires_at=receipt['result']['expires_at'],
                   provenance=dict(origin='SIMULATED_catalogue', digest=digest(receipt)), candidate=candidate,
                   text='Synthetic catalogue ' + receipt['kind'] + ' evidence ' + encoded(data).decode(),
                   claims=claims, image_references=0)
        enriched['evidence'].append(evidence_row(row))
    validate_packet(enriched)
    return enriched
