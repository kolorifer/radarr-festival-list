"""Fixed per-child partitions for rows returned by the two live SQLite reads.

The trusted one-shot supervisor starts at most one collector and one observer;
their nonrefundable partitions total at most 4,128 rows. This bounds rows
delivered to the Python query code, including schema/pragma results and the
collector recheck. It does not count SQLite's internal rows visited while
evaluating a query, nor rows in the disposable preflight.
"""
import sqlite3

_CAPS = {'collector': 4096, 'observer': 32}
TOTAL_RETURNED_ROWS = 4128


class RowLimitExceeded(RuntimeError):
    pass


def factory(role):
    if (type(role) is not str or role not in _CAPS or
            sum(_CAPS.values()) != TOTAL_RETURNED_ROWS):
        raise ValueError('row_partition_invalid')
    remaining = _CAPS[role]

    def consume(cursor, row):
        nonlocal remaining
        if remaining <= 0:
            raise RowLimitExceeded('row_partition_exhausted')
        remaining -= 1
        return sqlite3.Row(cursor, row) if role == 'collector' else row

    return consume
