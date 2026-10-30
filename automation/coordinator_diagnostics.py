"""Versioned fixed vocabulary only. Never classify arbitrary exception text."""
import errno

from automation import coordinator as c

REASONS = {
    'acquisition': ('read_complete', 'missing_entry', 'access_denied', 'path_rejected',
                    'path_component_ambiguous', 'nonregular_file', 'byte_limit',
                    'changed_during_read', 'hardlink_rejected', 'io_unknown'),
    'staging': ('staged', 'destination_collision', 'destination_rejected', 'access_denied', 'io_unknown'),
    'identity': ('hash_mismatch',),
    'decoding': ('invalid_json',),
    'provenance': ('time_mismatch', 'revision_mismatch'),
    'freshness': ('stale_evidence', 'future_evidence'),
    'schema': ('invalid_source_schema',),
    'pair': ('incompatible_movie_pair',),
}
SOURCE_IDS = ('engineering', 'investigations', 'research_report', 'parent_status', 'quality_release')
MAX_DIAGNOSTICS = 40


def diagnostic(source, stage, reason):
    value = {'version': 1, 'source': source, 'stage': stage, 'reason': reason}
    validate([value])
    return value


def validate(values):
    c.require(isinstance(values, list) and len(values) <= MAX_DIAGNOSTICS, 'diagnostics_bound')
    seen = set()
    for value in values:
        c.keys(value, 'version source stage reason')
        c.require(type(value['version']) is int and value['version'] == 1
                  and value['source'] in SOURCE_IDS
                  and value['stage'] in REASONS
                  and value['reason'] in REASONS[value['stage']], 'diagnostics_schema')
        key = (value['source'], value['stage'])
        c.require(key not in seen, 'diagnostics_duplicate')
        seen.add(key)
    return values


def acquisition_reason(exc):
    # Explicit typed read failures and errno only; ENOTDIR cannot prove a link.
    from automation.coordinator_io import ReadFailure
    if isinstance(exc, ReadFailure):
        return exc.reason
    if isinstance(exc, OSError):
        return {errno.ENOENT: 'missing_entry', errno.EACCES: 'access_denied',
                errno.EPERM: 'access_denied', errno.ELOOP: 'path_rejected',
                errno.ENOTDIR: 'path_component_ambiguous',
                errno.ENAMETOOLONG: 'path_rejected'}.get(exc.errno, 'io_unknown')
    return 'io_unknown'


class ValidationFailure(ValueError):
    def __init__(self, stage, reason):
        self.stage, self.reason = stage, reason
        super().__init__(reason)


def check(condition, stage, reason):
    if not condition:
        raise ValidationFailure(stage, reason)


def staging_reason(exc):
    if isinstance(exc, OSError):
        return {errno.EEXIST: 'destination_collision', errno.EACCES: 'access_denied',
                errno.EPERM: 'access_denied', errno.ELOOP: 'destination_rejected',
                errno.ENOTDIR: 'destination_rejected'}.get(exc.errno, 'io_unknown')
    return 'destination_rejected'
