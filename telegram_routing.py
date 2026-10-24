"""Per-notification routing, isolated across HTTP/worker threads."""
from contextlib import contextmanager
from contextvars import ContextVar
import os

_ROUTE=ContextVar('telegram_notification_route',default=None)
SETTINGS={'add_grab':'TELEGRAM_ADD_GRAB_TOPIC_ID','alternative':'TELEGRAM_GRAB_ANYWAY_TOPIC_ID'}

@contextmanager
def notification_route(kind):
    token=_ROUTE.set(kind if kind in SETTINGS else _ROUTE.get())
    try:yield
    finally:_ROUTE.reset(token)


def topic_fields(default):
    setting=SETTINGS.get(_ROUTE.get())
    value=(os.environ.get(setting,'').strip() if setting else '') or default
    if not value:return {}
    try:
        number=int(value)
        if number<=0:raise ValueError()
        return {'message_thread_id':number}
    except (ValueError,TypeError):raise RuntimeError('Telegram topic must be a positive integer') from None
