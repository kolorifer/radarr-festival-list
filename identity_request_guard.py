"""Optional per-context gate for extra retry traffic; ordinary actor calls unchanged."""
from contextvars import ContextVar
from contextlib import contextmanager

_FRESH = ContextVar("identity_fresh_metadata", default=False)


def fresh_metadata_required():
    return _FRESH.get()


@contextmanager
def fresh_metadata(enabled=True):
    token = _FRESH.set(enabled)
    try:
        yield
    finally:
        _FRESH.reset(token)


_GATE = ContextVar('identity_request_gate', default=None)


def reserve(provider):
    gate = _GATE.get()
    if gate is not None:
        gate.reserve(provider)


def cooldown(provider, seconds=0, auth=False):
    gate = _GATE.get()
    if gate is not None:
        gate.cooldown(provider, seconds, auth)


@contextmanager
def guarded(gate):
    token = _GATE.set(gate)
    try:
        yield
    finally:
        _GATE.reset(token)
