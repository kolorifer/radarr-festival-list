"""Pure adapters and strict, capability-free data contracts.

Caller-selected sources, decision issuers and occurrence receipts are trust inputs;
neither movie text nor a model may choose them. No collector database is opened.
"""
import copy
import hashlib
import json
import math
import re

from identity_triage_intake import normalize, safe_text, unique_object
from identity_triage_store import digest
from identity_selection import route
from torrent_research_evidence import validate as validate_torrent

MAX_INPUT = 49152
MAX_OUTPUT = 8192
MAX_EVIDENCE = 24
MAX_DECISIONS = 32
STATUSES = ('supported_candidate', 'unresolved', 'blocked', 'intentionally_skipped')


class Refusal(ValueError):
    """Fixed public reason codes only; never stringify untrusted exceptions."""


def require(condition, reason):
    if not condition:
        raise Refusal(reason)


def encoded(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(',', ':'),
                          ensure_ascii=True, allow_nan=False).encode()
    except (ValueError, TypeError, RecursionError):
        raise Refusal('invalid_json') from None


def decode(raw, limit=MAX_OUTPUT):
    require(isinstance(raw, (str, bytes)) and len(raw) <= limit, 'size_limit')
    try:
        value = json.loads(raw, object_pairs_hook=unique_object,
                           parse_constant=lambda _: require(False, 'invalid_json'))
        require(len(encoded(value)) <= limit, 'size_limit')
        return value
    except (ValueError, UnicodeError, RecursionError):
        raise Refusal('invalid_json') from None


def shape(value, keys):
    require(isinstance(value, dict) and set(value) == set(keys.split()), 'schema')


def text(value, limit=512):
    try:
        result = safe_text(value, limit)
        # Private paths, credential labels and image URLs have no place in this
        # envelope. Callers project/redact evidence before this boundary.
        require(not re.search(r'[/\\]|\b(?:secret|passkey|password|cookie|bearer|credential|api_key)\b',
                              result, re.I), 'unsafe_text')
        return result
    except (ValueError, TypeError):
        raise Refusal('unsafe_text') from None


def identifier(value):
    require(isinstance(value, str) and re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', value), 'identifier')
    return value


def hash_id(value):
    require(isinstance(value, str) and re.fullmatch(r'[a-f0-9]{64}', value), 'hash')
    return value


def stamp(value):
    require(type(value) in (int, float) and math.isfinite(value) and 0 < value < 10**11, 'timestamp')
    return value


def target(value):
    shape(value, 'imdb tmdb')
    require(isinstance(value['imdb'], str) and re.fullmatch(r'tt[0-9]{7,10}', value['imdb']), 'imdb')
    require(type(value['tmdb']) is int and 0 < value['tmdb'] < 2**31, 'tmdb')
    return value


def scope(value):
    shape(value, 'source case_id version occurrence')
    identifier(value['source'])
    require(isinstance(value['case_id'], str) and re.fullmatch(r'outcome-[a-f0-9]{64}', value['case_id']), 'case_id')
    hash_id(value['version'])
    if value['occurrence'] is not None:
        shape(value['occurrence'], 'event_id delivery_id')
        identifier(value['occurrence']['event_id'])
        delivery = value['occurrence']['delivery_id']
        require((type(delivery) is int and delivery > 0) or
                (isinstance(delivery, str) and re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', delivery)), 'delivery_id')
    return value


def evidence_row(row):
    shape(row, 'id kind scope observed_at expires_at provenance candidate text claims image_references')
    identifier(row['id'])
    require(row['kind'] in ('catalogue', 'source', 'shadow'), 'evidence_kind')
    scope(row['scope'])
    stamp(row['observed_at'])
    if row['expires_at'] is not None:
        require(stamp(row['expires_at']) >= row['observed_at'], 'evidence_expiry')
    shape(row['provenance'], 'origin digest')
    identifier(row['provenance']['origin'])
    hash_id(row['provenance']['digest'])
    if row['candidate'] is not None:
        target(row['candidate'])
    text(row['text'], 2000)
    require(isinstance(row['claims'], list) and len(row['claims']) <= 8, 'claims')
    require(len(set(row['claims'])) == len(row['claims']), 'claims')
    require(not set(row['claims']) - {'title', 'year', 'crosswalk', 'source_identity',
                                     'runtime', 'edition', 'shadow_success'}, 'claims')
    require(type(row['image_references']) is int and 0 <= row['image_references'] <= 6, 'images')
    return row


def decision_row(row):
    shape(row, 'id revision issuer provenance decided_at scope evidence_ids evidence_hashes kind chosen_target supersedes revoked_at expires_at')
    identifier(row['id'])
    require(type(row['revision']) is int and row['revision'] >= 1, 'decision_revision')
    identifier(row['issuer'])
    shape(row['provenance'], 'origin digest')
    identifier(row['provenance']['origin'])
    hash_id(row['provenance']['digest'])
    stamp(row['decided_at'])
    scope(row['scope'])
    require(row['kind'] in ('confirmed_identity', 'intentionally_skipped', 'completed_occurrence', 'technical_gap'), 'decision_kind')
    require(isinstance(row['evidence_ids'], list) and 1 <= len(row['evidence_ids']) <= MAX_EVIDENCE, 'decision_evidence')
    for eid in row['evidence_ids']:
        identifier(eid)
    require(isinstance(row['evidence_hashes'], dict) and set(row['evidence_hashes']) == set(row['evidence_ids']), 'decision_evidence_hashes')
    for value in row['evidence_hashes'].values():
        hash_id(value)
    if row['chosen_target'] is not None:
        target(row['chosen_target'])
    require((row['chosen_target'] is not None) == (row['kind'] == 'confirmed_identity'), 'decision_target')
    if row['supersedes'] is not None:
        identifier(row['supersedes'])
        require(row['supersedes'] != row['id'], 'decision_supersession')
    for key in ('revoked_at', 'expires_at'):
        if row[key] is not None:
            require(stamp(row[key]) >= row['decided_at'], 'decision_time')
    return row


def _packet(binding, event, facts, evidence, decisions, trusted_issuers, original_hash, hash_basis):
    scope(binding)
    require(isinstance(evidence, list) and len(evidence) <= MAX_EVIDENCE, 'evidence_limit')
    require(isinstance(decisions, list) and len(decisions) <= MAX_DECISIONS, 'decision_limit')
    for row in evidence:
        evidence_row(row)
    require(len({r['id'] for r in evidence}) == len(evidence), 'duplicate_evidence_id')
    for row in decisions:
        decision_row(row)
    require(len({r['id'] for r in decisions}) == len(decisions), 'duplicate_decision_id')
    require(isinstance(trusted_issuers, (tuple, list)) and len(trusted_issuers) <= 8, 'trusted_issuers')
    for issuer in trusted_issuers:
        identifier(issuer)
    packet = dict(schema=1, binding=binding, event=event, facts=facts,
                  evidence=evidence, decisions=decisions, trusted_issuers=list(trusted_issuers),
                  original_hash=original_hash, hash_basis=hash_basis)
    require(len(encoded(packet)) <= MAX_INPUT, 'input_limit')
    return copy.deepcopy(packet)


def validate_packet(packet):
    shape(packet, 'schema binding event facts evidence decisions trusted_issuers original_hash hash_basis')
    require(type(packet['schema']) is int and packet['schema'] == 1, 'packet_version')
    hash_id(packet['original_hash'])
    require(packet['hash_basis'] in ('captured_bytes', 'canonical_json_object', 'legacy_canonical_snapshot'), 'hash_basis')
    binding = scope(packet['binding'])
    event = packet['event']
    if event is not None:
        shape(event, 'id observed_at input_hash')
        identifier(event['id'])
        stamp(event['observed_at'])
        require(event['input_hash'] == packet['original_hash'], 'event_hash_changed')
        if binding['occurrence'] is not None:
            require(event['id'] == binding['occurrence']['event_id'], 'event_mismatch')
    else:
        require(binding['occurrence'] is None, 'legacy_occurrence_invented')
    f = packet['facts']
    require(isinstance(f, dict) and set(f) - {'retained_torrent_hash', 'image_references'} ==
            {'title', 'year', 'imdb', 'tmdb', 'release_key_basis', 'outcome', 'route'}, 'facts_schema')
    text(f['title'], 250)
    require(type(f['year']) is int and 1888 <= f['year'] <= 2100, 'year')
    require(f['release_key_basis'] in ('unknown', 'external_id', 'name_fallback'), 'source_basis')
    from identity_triage_intake import OUTCOME_STATUSES, CATEGORIES, REASONS
    o = f['outcome']
    require(isinstance(o, dict) and {'status', 'category', 'reason'} <= set(o) and
            not set(o) - {'status', 'category', 'reason', 'asserted_imdb', 'asserted_tmdb'}, 'outcome_schema')
    require(o['status'] in OUTCOME_STATUSES and o['category'] in CATEGORIES and o['reason'] in REASONS, 'outcome_codes')
    require(f['route'] in ('eligible', 'review_only', 'retry_later', 'unmatched', 'quarantine',
                           'unassessed', 'verified', 'routine', 'reviewed_occurrence', 'existing_seed'), 'route')
    for row in (f, dict(imdb=o.get('asserted_imdb'), tmdb=o.get('asserted_tmdb'))):
        require(row['imdb'] is None or isinstance(row['imdb'], str) and re.fullmatch(r'tt[0-9]{7,10}', row['imdb']), 'imdb')
        require(row['tmdb'] is None or type(row['tmdb']) is int and 0 < row['tmdb'] < 2**31, 'tmdb')
    if 'retained_torrent_hash' in f:
        hash_id(f['retained_torrent_hash'])
    if 'image_references' in f:
        require(type(f['image_references']) is int and 0 <= f['image_references'] <= 6, 'images')
    _packet(binding, event, f, packet['evidence'], packet['decisions'], packet['trusted_issuers'], packet['original_hash'], packet['hash_basis'])
    return packet


def captured_outcome(envelope, *, sources, binding, evidence, decisions, trusted_issuers=()):
    """Side-effect-free import of an actual observer-shaped captured envelope.

    binding.version is the caller's exact collector version, not a guessed
    replacement. A real delivery receipt is required for a bound occurrence.
    Only original hashes and capability-free projections are retained.
    """
    hash_basis = 'canonical_json_object'
    if isinstance(envelope, (bytes, str)):
        raw = envelope.encode() if isinstance(envelope, str) else envelope
        require(len(raw) <= 65536, 'input_limit')
        original_hash = hashlib.sha256(raw).hexdigest()
        envelope = decode(raw, 65536)
        hash_basis = 'captured_bytes'
    else:
        original_hash = digest(envelope)
    require(len(encoded(envelope)) <= 65536, 'input_limit')
    shape(envelope, 'version event id timestamp data')
    shape(envelope['data'], 'release indexer outcome')
    require(not set(envelope['data']['release']) - {'type', 'protocol', 'implementation', 'title', 'year', 'name',
                                                 'external_id', 'meta_imdb', 'meta_tmdb'}, 'release_fields')
    shape(envelope['data']['indexer'], 'identifier name')
    record = normalize(envelope, sources, 'outcome')
    require(not record.get('reason'), 'quarantined_outcome')
    scope(binding)
    require(binding['source'] == record['metadata']['source'] and
            binding['case_id'] == 'outcome-' + record['release'], 'source_case_mismatch')
    if binding['occurrence'] is not None:
        require(binding['occurrence']['event_id'] == record['event_id'], 'event_mismatch')
    m = record['metadata']
    # Do not retain source IDs, source URLs, image URLs or arbitrary raw fields.
    facts = {k: m[k] for k in ('title', 'year', 'imdb', 'tmdb', 'release_key_basis')}
    text(facts['title'], 250)
    outcome = {k: v for k, v in record['outcome'].items() if k != 'torrent_evidence'}
    facts.update(outcome=outcome, route=route(outcome))
    if outcome['reason'] == 'tmdb_mapping_missing' and not (outcome.get('asserted_imdb') or m['imdb']):
        facts['route'] = 'quarantine'
    if 'torrent_evidence' in record['outcome']:
        te = validate_torrent(record['outcome']['torrent_evidence'])
        # The controller never mistakes a reference count for visual analysis.
        facts['retained_torrent_hash'] = digest(te)
        facts['image_references'] = len(te['images'])
    return _packet(binding, dict(id=record['event_id'], observed_at=record['time'],
                                input_hash=original_hash), facts, evidence, decisions,
                   trusted_issuers, original_hash, hash_basis)


def legacy_snapshot(case, *, source, evidence, decisions, trusted_issuers=()):
    """Import the existing selection.snapshot case; missing receipts stay unknown."""
    shape(case, 'case_id version observed_at first_observed_at title year route reason correlation original_type source_identity')
    stamp(case['observed_at'])
    text(case['title'], 250)
    require(type(case['year']) is int and 1888 <= case['year'] <= 2100, 'year')
    identity = case['source_identity']
    shape(identity, 'imdb tmdb asserted_imdb asserted_tmdb')
    for key in ('imdb', 'asserted_imdb'):
        require(identity[key] is None or isinstance(identity[key], str) and
                re.fullmatch(r'tt[0-9]{7,10}', identity[key]), 'imdb')
    for key in ('tmdb', 'asserted_tmdb'):
        require(identity[key] is None or type(identity[key]) is int and 0 < identity[key] < 2**31, 'tmdb')
    from identity_triage_intake import REASONS
    from identity_research_handoff import ROUTES
    require(case['route'] in ROUTES and case['reason'] in REASONS, 'legacy_route')
    facts = dict(title=case['title'], year=case['year'], imdb=identity['imdb'], tmdb=identity['tmdb'],
                 release_key_basis='unknown', route=case['route'],
                 outcome=dict(status='unresolved', category='other', reason=case['reason'],
                              asserted_imdb=identity['asserted_imdb'], asserted_tmdb=identity['asserted_tmdb']))
    return _packet(dict(source=source, case_id=case['case_id'], version=case['version'], occurrence=None),
                   None, facts, evidence, decisions, trusted_issuers, digest(case), 'legacy_canonical_snapshot')


def reconcile(packet, now):
    """Join scoped owner decisions and dated shadow knowledge before AI admission."""
    stamp(now)
    binding = packet['binding']
    evidence = {r['id']: r for r in packet['evidence']}
    trusted = [r for r in packet['decisions'] if r['issuer'] in packet['trusted_issuers'] and r['decided_at'] <= now]
    # Superseded history stays superseded even if its replacement later expires
    # or is revoked. Never revive a persistent decision implicitly.
    replaced = {r['supersedes'] for r in trusted if r['supersedes']}
    active = []
    prior = []
    for r in packet['decisions']:
        state = ('untrusted' if r not in trusted else
                 'superseded' if r['id'] in replaced else
                 'revoked' if r['revoked_at'] is not None and r['revoked_at'] <= now else
                 'expired' if r['expires_at'] is not None and r['expires_at'] <= now else
                 'scope_changed_or_unbound' if binding['occurrence'] is None or r['scope'] != binding else
                 'evidence_changed_or_missing' if any(e not in evidence or evidence[e]['scope'] != binding
                                                      or digest(evidence[e]) != r['evidence_hashes'][e]
                                                      or evidence[e]['observed_at'] > r['decided_at'] for e in r['evidence_ids']) else
                 'applicable')
        prior.append(dict(decision=r, applicability=state))
        if state == 'applicable':
            active.append(r)
    shadows = [dict(evidence=r, freshness='stale' if r['expires_at'] is not None and r['expires_at'] <= now
                    else 'dated_retained') for r in packet['evidence'] if r['kind'] == 'shadow']
    result = dict(prior_decisions=prior, shadow_knowledge=shadows, disposition='missing_disposition',
                  known_identity=None, operational_closure=False, novelty='unknown', admission='eligible')
    if binding['occurrence'] is None:
        result.update(admission='blocked', disposition='legacy_occurrence_unknown')
    elif packet['facts']['release_key_basis'] != 'external_id':
        result.update(admission='blocked', disposition='source_binding_unverified')
    elif any(r['kind'] == 'intentionally_skipped' for r in active):
        result.update(admission='intentionally_skipped', disposition='owner_skipped')
    elif any(r['kind'] == 'completed_occurrence' for r in active):
        result.update(admission='intentionally_skipped', disposition='reviewed_occurrence')
    else:
        chosen = [r['chosen_target'] for r in active if r['kind'] == 'confirmed_identity']
        if chosen:
            result['disposition'] = 'owner_confirmed_source_verification_pending'
            if len({digest(t) for t in chosen}) != 1:
                result.update(admission='blocked', disposition='conflicting_owner_decisions')
            else:
                result['known_identity'] = chosen[0]
        elif any(r['kind'] == 'technical_gap' for r in active):
            result['disposition'] = 'technical_gap'
        elif prior:
            result['disposition'] = 'no_applicable_disposition'
    ids = packet['facts']
    result['conflicting_ids'] = any(ids.get(k) and ids['outcome'].get('asserted_' + k)
                                    and ids[k] != ids['outcome']['asserted_' + k] for k in ('imdb', 'tmdb'))
    if ids['route'] in ('routine', 'verified'):
        result.update(admission='intentionally_skipped', disposition='existing_' + ids['route'])
    elif ids['route'] in ('quarantine', 'unassessed') and result['admission'] == 'eligible':
        result.update(admission='blocked', disposition='outcome_not_admitted')
    if packet['event'] and packet['event']['observed_at'] > now + 300:
        result.update(admission='blocked', disposition='outcome_clock_unverified')
    return result
