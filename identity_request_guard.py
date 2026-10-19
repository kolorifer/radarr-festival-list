"""Optional per-context gate for extra retry traffic; ordinary actor calls unchanged."""
from contextvars import ContextVar
from contextlib import contextmanager

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
