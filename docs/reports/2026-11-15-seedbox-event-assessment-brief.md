# Seedbox event-driven assessment — active implementation

The owner requested assessment on the seedbox when identification fails, without
Mac dependence or a one-case-per-hour restriction, followed by a corrected
original Telegram notification after independent review. The owner authorizes the
necessary bounded service deployment. Main operates actual secrets, source reads,
cutover and live activation; the existing sole repository writer and reviewer
implement and verify public code with invented fixtures.

## Connected design

A pinned read-only collector adapter drains committed outcome history through a
durable cursor. This begins at collector acceptance: the existing actor has a
pre-persist memory loss window which this change does not erase. Current source
correlation is rechecked before preparation. Successful, superseded and invalid
observations receive retained dispositions; late source correlation remains
pending. Backpressure never advances past an unaccepted page. The activation
watermark/backlog selection is explicit and must be verified by main.

Preparation claims are separate from provider attempts. Source/access failure
before provider allocation remains pending. An atomic provider reservation keeps
its full debit and consumes its case even if interrupted or uncertain. Import all
prior consumed cases/debits, including the unresolved slot35; do not reset legacy
journals. Main reports the Mac automation is now supervision-only. Exact cutover
import and single canonical host queue remain activation requirements.

Reuse the v13 builder, schema, validation and private report. A new explicitly
versioned host authority must authenticate source derivation and finite delegated
credit; it must not generate false human-review or fresh-balance timestamps.
The delegation is limited by an actual freshly observed balance minus preserved
reservations and other allocations, and expires no later than the credit. No
separate weekly USD budget is assumed. The existing fixed Mini reservation applies.
No purchases, cash fallback, downloads or production identity approval.

Keep review as a separate genuine stage. The owner selected independent automated review on the seedbox with later main
audits. It is a separate generated request with its own retained reservation and
receipt, not a claim of personal review or independent source verification. A provider receipt is not a
review. PR204 binds an accepted review to the exact original bot-owned message.

## Credential design and actual host evidence

Main reports systemd257.13 and an invented `systemd-creds --user` encrypted
roundtrip succeeded. An invented `LoadCredentialEncrypted` user-service probe
failed before execution with CREDENTIALS/permission denied. Preserve that failure;
no permission repair or blind replay is proposed.

The systemd257 implementation routes non-root decrypt through credential IPC.
Use the supported user-scoped CLI, exact credential name and real expiry, with
captured pipes inside a disposable runner. Verify this path in the actual service
context with an invented value first. No plaintext persistent file, secret argv,
environment value or diagnostic output is permitted. Main provisions through a
reviewed direct Keychain-to-encryption bridge only after code acceptance.

Sources: [systemd257 credential manual](https://www.freedesktop.org/software/systemd/man/257/systemd-creds.html)
and [v257 implementation](https://raw.githubusercontent.com/systemd/systemd/v257/src/creds/creds.c).

## Current boundary

The connected candidate now includes the serial event worker, immutable original
and crosswalk retention, truthful selected-case coverage, real v13 assessment,
separate generated review, durable private HTML, exact PR204 original-card edit,
finite shared-denial circuits and a genuine native Keychain provisioning entry.
It is unissued: complete failure/installed testing, exact independent review,
supported CI and main host verification remain. No real key/source/provider,
notification or service operation was performed by the repository writer.

A main-issued finite topology grant preserves the accepted sole actor writer and
no-republication assumptions. Host checks verify the selected actor process and
code immediately before edit; they do not claim a fresh global writer audit.
Collector state is rechecked just before irreversible operations, but can advance
after the read-only check; this cannot authorize production identity or downloads.
Weak/outcome-only correlation stays explicitly pending for later collector linkage.

The confined worker permits directory-name traversal for descriptor guards;
file bytes are restricted separately. The collector remains WAL/read-only (existing SHM lock writes); the actor stays
in DELETE journal mode. Its exact private state subtree receives regular-file
read/write/create/remove/truncate rights for SQLite journals, without directory
creation/removal. These rights also cover the existing binding spool; Landlock
cannot subtract a child rule. PR204 and fixed transaction code constrain actual
table/row/file mutations; this is not a kernel filename/table guarantee. Existing
rollback journals cause a local refusal, not silent recovery or durability changes. The fixed
systemd user-scope CLI uses `/run/systemd/io.systemd.Credentials`; ABI6 does not
path-mediate filesystem Unix-socket connects. The final actual confinement probe
must pass using invented credentials before real provisioning/activation.

Preserve the unrelated CODEX_TASK. Main remains the deployment operator.
