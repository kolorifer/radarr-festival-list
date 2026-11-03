"""Existing-ledger-only adapter for repository recurring-v1 WEEKLY policy.

No constructor, schema creation, admission, migration or reconciliation scan.
An installed daily profile is deliberately unsupported. The parent must also
pin the actual code closure and file identities; a schema/export is not that proof.
"""
from pathlib import Path
import sqlite3
from identity_recurring_store import RecurringStore
from .contracts import digest, require
from .history import checked

PROFILE = 'repository-recurring-v1-weekly-5cases-25gets-5perversion'
SCHEMA = '0112ce1ff897f07634c18e0e42115703e13e59d56230dcc867ab09f41ad3ef55'


class ExistingWeeklyLedger(RecurringStore):
    def __init__(self, directory, *, clock, profile):
        require(profile == PROFILE, 'pilot_ledger_profile_unknown')
        self.directory = Path(directory)
        require(self.directory.is_absolute() and self.directory.resolve(strict=True) == self.directory,
                'pilot_ledger_path')
        checked(self.directory.lstat(), True)
        self.path = self.directory / self.filename
        checked(self.path.lstat())  # absent is an error, never creates a ledger
        self.clock = clock
        self.pin = self.path.stat().st_dev, self.path.stat().st_ino
        # Inspect unknown profiles read-only, before inherited tx() can select
        # WAL mode. Even a journal-mode conversion would be an unapproved change.
        c = sqlite3.connect(self.path.as_uri() + '?mode=ro', uri=True, timeout=1)
        try:
            schema = [list(r) for r in c.execute("select type,name,tbl_name,sql from sqlite_master "
                                                "where name not like 'sqlite_%' order by name")]
            require(c.execute('pragma user_version').fetchone()[0] == 1 and digest(schema) == SCHEMA and
                    c.execute('pragma journal_mode').fetchone()[0] == 'wal',
                    'pilot_ledger_schema_unknown')
            self.check()
        finally:
            c.close()

    def check(self):
        super().check()
        require((self.path.stat().st_dev, self.path.stat().st_ino) == self.pin,
                'pilot_ledger_replaced')

    def admit(self, item):
        require(False, 'pilot_existing_ledger_only')

    def reconcile(self, items):
        require(False, 'pilot_existing_ledger_only')
