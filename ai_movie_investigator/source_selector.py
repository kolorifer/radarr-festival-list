"""Explicit selector and selected-artifact handoff, not a source access grant."""
from .contracts import decode, require
from .manual_offline import read_private, parse_packet
from .source_case import validate_selector, Refused
from .source_output import validate


def read_selector(path):
    return validate_selector(decode(read_private(path, 4096), 4096))


def pair(selector, historical_raw):
    validate_selector(selector)
    packet, _ = parse_packet(historical_raw)
    require(all(packet[k] == selector[k] for k in ('case_id', 'version', 'title')), 'selected_historical_mismatch')
    return packet


def validate_artifact(raw, selector):
    validate_selector(selector)
    envelope = decode(raw, 32768)
    require(type(envelope) is dict and envelope.get('case') == selector['case_id']
            and envelope.get('version') == selector['version'], 'selected_artifact_mismatch')
    require(set(envelope) == {'status', 'case', 'version', 'source_file_size_bound', 'result', 'observer_journal_mode'}
            and envelope['status'] == 'completed' and type(envelope['source_file_size_bound']) is int
            and envelope['source_file_size_bound'] == 33554432
            and envelope['observer_journal_mode'] in ('delete', 'wal'), 'selected_artifact_shape')
    validate(envelope['result'], envelope['result'].get('event_uuid'), selector)
    require(envelope['result']['status'] == 'ok', 'selected_read_refused')
    return envelope
