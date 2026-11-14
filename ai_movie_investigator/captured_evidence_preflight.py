"""Offline evidence derivation from independently selected exact artifacts.

This is a pure preflight, not authorization, external-source verification,
network access, or a way to modify an existing prepared captured request.
"""
import hashlib
from .contracts import decode, digest, evidence_row, identifier, require, scope, shape, stamp, target


def verified_observation(raw, pin, kind):
    """Parse bytes only after main has independently selected the exact digest.

    The digest establishes byte identity, not truth, origin, or source access.
    """
    shape(pin, 'sha256 origin observed_at expires_at')
    require(isinstance(raw, bytes) and 0 < len(raw) <= 65536, 'observation_size')
    require(hashlib.sha256(raw).hexdigest() == pin['sha256'], 'observation_digest')
    identifier(pin['origin']); stamp(pin['observed_at'])
    if pin['expires_at'] is not None:
        require(stamp(pin['expires_at']) >= pin['observed_at'], 'observation_expiry')
    value = decode(raw, 65536)
    require(isinstance(value, dict) and value.get('kind') == kind, 'observation_kind')
    return value


def derive_candidate_evidence(binding, catalogue_raw, catalogue_pin, source_raw, source_pin, attestation, *, now):
    """Derive assertions from exact observations selected by a trusted supervisor.

    The caller must authenticate the pinned main-reviewed derivation record and
    independently verify the original artifacts, retrieval and occurrence mapping;
    the function neither authenticates an external page nor searches it. Source
    must explicitly assert the same IMDb identity for this exact occurrence;
    a title/year match or a producer outcome label is insufficient.
    """
    scope(binding); stamp(now)
    require(binding['occurrence'] is not None, 'source_occurrence_required')
    shape(catalogue_pin,'sha256 origin observed_at expires_at');shape(source_pin,'sha256 origin observed_at expires_at')
    for pin in (catalogue_pin,source_pin):
        stamp(pin['observed_at'])
        require(pin['expires_at'] is not None,'observation_stale')
        stamp(pin['expires_at'])
    shape(attestation, 'kind binding catalogue_sha256 source_sha256 catalogue_pin_sha256 source_pin_sha256 catalogue_original_sha256 source_original_sha256 local_context_sha256 source_occurrence_verified provenance_reviewed attested_at expires_at')
    require(attestation['kind']=='main_reviewed_source_derivation_v1' and attestation['binding']==binding and
        attestation['catalogue_sha256']==catalogue_pin['sha256'] and attestation['source_sha256']==source_pin['sha256'] and
        attestation['catalogue_pin_sha256']==digest(catalogue_pin) and attestation['source_pin_sha256']==digest(source_pin) and
        attestation['source_occurrence_verified'] is True and attestation['provenance_reviewed'] is True and
        stamp(attestation['attested_at'])<=now<stamp(attestation['expires_at']) and
        all(p['expires_at'] is not None and p['observed_at']<=attestation['attested_at'] and p['expires_at']<=attestation['expires_at'] for p in (catalogue_pin,source_pin)), 'source_attestation_required')
    from .contracts import hash_id
    hash_id(attestation['catalogue_original_sha256']);hash_id(attestation['source_original_sha256']);hash_id(attestation['local_context_sha256'])
    cat = verified_observation(catalogue_raw, catalogue_pin, 'catalogue_external_ids')
    source = verified_observation(source_raw, source_pin, 'source_release_identity')
    shape(cat, 'kind imdb tmdb'); shape(source, 'kind binding asserted_imdb')
    candidate = target(dict(imdb=cat['imdb'], tmdb=cat['tmdb']))
    require(source['binding'] == binding and source['asserted_imdb'] == candidate['imdb'], 'source_identity_unproven')
    for pin in (catalogue_pin, source_pin):
        require(pin['observed_at'] <= now and pin['expires_at'] is not None and now < pin['expires_at'], 'observation_stale')
    def row(name, kind, pin, claims, label):
        return evidence_row(dict(id=name, kind=kind, scope=binding, observed_at=pin['observed_at'],
            expires_at=pin['expires_at'], provenance=dict(origin=pin['origin'], digest=pin['sha256']),
            candidate=dict(candidate), text=label, claims=claims, image_references=0))
    return [row('bound_catalogue', 'catalogue', catalogue_pin, ['crosswalk'], 'Supervisor selected catalogue external identifiers.'),
            row('bound_source', 'source', source_pin, ['source_identity'], 'Supervisor selected source assertion for the same occurrence and identity.')]


def assemble_successor_packet(original, catalogue_raw, catalogue_pin, source_raw,
                              source_pin, attestation, *, now):
    """Pure proposal only; trust and new append-only authorization are external.

    Old evidence/decisions, occurrence and captured event are unchanged. Existing
    candidate-free rows remain candidate-free and cannot become citations for a
    supported candidate. New rows use distinct IDs and only explicit ID claims.
    """
    import copy
    from .contracts import validate_packet, MAX_EVIDENCE
    validate_packet(original)
    added=derive_candidate_evidence(original['binding'], catalogue_raw, catalogue_pin,
                                    source_raw, source_pin, attestation, now=now)
    ids={r['id'] for r in original['evidence']}
    require(not ids.intersection(r['id'] for r in added), 'evidence_id_collision')
    require(len(original['evidence'])+len(added)<=MAX_EVIDENCE, 'evidence_limit')
    packet=copy.deepcopy(original);packet['evidence'].extend(added)
    validate_packet(packet)
    return packet


def preflight_successor(original, catalogue_raw, catalogue_pin, source_raw,
                        source_pin, attestation, *, now, purpose=None):
    """Build a proposal and strict factual view, without any state write/send.

    This is not yet a prepared captured request or an activation grant. The
    existing captured route must explicitly bind this projection before use.
    """
    from .new_case import admitted, projection
    packet=assemble_successor_packet(original,catalogue_raw,catalogue_pin,
                                     source_raw,source_pin,attestation,now=now)
    rec=admitted(packet,packet['binding'],now,purpose=purpose)
    candidate=packet['evidence'][-1]['candidate']
    require(not rec['conflicting_ids'],'conflicting_ids_require_review')
    facts=packet['facts'];outcome=facts['outcome']
    require(all(value is None or value==candidate[key] for key in ('imdb','tmdb')
        for value in (facts.get(key),outcome.get('asserted_'+key))), 'conflicting_ids_require_review')
    require(rec['known_identity'] in (None,candidate),'owner_target_conflict')
    data,supplied=strict_factual_projection(packet,rec,now)
    return dict(packet=packet,projection=data,candidate=candidate,
                citation_eligibility=data['citation_eligibility'])


def strict_factual_projection(packet, rec, now):
    """Minimized view for a separately authenticated, materially enriched job."""
    from .new_case import projection
    data,supplied=projection(packet,rec,now)
    bound={row['id']:row for row in packet['evidence'] if row['id'] in ('bound_catalogue','bound_source')}
    require(set(bound)=={'bound_catalogue','bound_source'}, 'source_identity_unproven')
    catalogue=bound['bound_catalogue'];source=bound['bound_source'];candidate=catalogue['candidate']
    require(candidate is not None and source['candidate']==candidate and catalogue['kind']=='catalogue' and
        source['kind']=='source' and catalogue['claims']==['crosswalk'] and source['claims']==['source_identity'] and
        all(r['scope']==packet['binding'] and r['observed_at']<=now and r['expires_at'] is not None and now<r['expires_at'] for r in bound.values()),
        'source_identity_unproven')
    facts=packet['facts'];outcome=facts['outcome']
    require(not rec['conflicting_ids'] and rec['known_identity'] in (None,candidate) and
        all(value is None or value==candidate[key] for key in ('imdb','tmdb')
            for value in (facts.get(key),outcome.get('asserted_'+key))), 'conflicting_ids_require_review')
    for row in data['evidence']:
        row['text']='Retained scoped evidence; inspect typed claims and candidate.'
    aliases={r['id']:alias for alias,r in supplied.items()}
    require(set(bound)<=set(aliases),'source_identity_unproven')
    data['citation_eligibility']=dict(catalogue=[aliases['bound_catalogue']],source=[aliases['bound_source']])
    return data,supplied


def validate_attested_citations(result, data):
    """Positive output may rely only on the two explicitly attested aliases."""
    require(not result['alternatives'], 'attested_alternatives_unavailable')
    if result['status'] != 'supported_candidate':return
    eligible=data['citation_eligibility'];allowed={(eligible['catalogue'][0],'crosswalk'),(eligible['source'][0],'source_identity')}
    cites=result['citations']
    actual={(c['evidence_id'],c['claim']) for c in cites}
    require(actual==allowed and len(cites)==2, 'attested_citations_required')
