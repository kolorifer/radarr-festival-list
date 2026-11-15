# Recurring supervised snapshot intake

## Agreed scope

The owner requested automatic assessment with main reviewing the result and
reporting it to the owner. Main owns the existing hourly Mac heartbeat, current
collector/source/catalogue authentication, Keychain/account evidence, actual
invocation and user-facing delivery. This change adds no scheduler, worker,
credential operation, production activation, seedbox restart or automatic movie
identity/acquisition/Telegram action. The unrelated CODEX_TASK remains untouched.

## Operator API

`automation/recurring_snapshot_operator.py` is an operator-only helper, outside
and separate from the unchanged 47-file v13 runtime. Main verifies this helper,
`automation/snapshot_review_UNISSUED.py`, and the installed runtime before import.
It must run in main's isolated reviewed operator process with the selected runtime
on its import path. It has no autonomous CLI, source reader or provider sender.

Create `Operator(state, journal)` with the existing enrolled account root and a
existing empty owner-only 0700 `state/recurring-intake-v1` journal directory. All journal writes use
the existing append-only, no-follow, bounded History implementation under private
ancestor checks. Lock order is account root then operator journal. Alternate journal locations are refused; prior
root prefixes are preserved and checked. Snapshot pins/freshness are reread after
both locks are held. Keep this same
journal across all cycles; do not reset it to retry an interrupted selection.

1. `select(snapshot_pin, authenticated_reference=actual_observation_reference)`
   validates the current complete collector snapshot. It reserves at most one
   case per UTC hour, using the existing stable `case_id`, never title matching.
   Every historical/captured attempt start is consumed, including failed or
   incomplete attempts. All journal reservations also exclude the same case
   across versions. Conflict reasons identity_conflict, title_conflict,
   year_conflict and local_identity_conflict share priority; newest
   first_observed_at first, stable case_id tie break. Other eligible cases follow.
2. Main independently obtains/verifies current listing/catalogue originals and
   typed observations, exact owner scope, local context, account evidence and
   source disclosure. It constructs the existing v13 **first-mode** authority
   artifact. This helper cannot authenticate facts or replace that gate. If
   unavailable, `blocked(reservation, reason)` records a finite operator-needed
   reason. Other cases may progress in later hours; this case is not retried.
3. `prepare(reservation, authority=pin, account_evidence=pin, runtime=absolute_path,
   python=absolute_real_executable, template=pin, output=private_empty_directory)`
   validates the unchanged trusted v13 gate, exact selected snapshot/case/version,
   account evidence, runtime manifest and original root prefix. It durably records
   intent, then creates the exact existing wrapper with literal per-case pins.
   A crash during preparation remains consumed. The output directory is distinct
   from the empty report destination already selected in the authority.
4. Main independently inspects the returned wrapper and acceptance proposal,
   writes the existing exact main acceptance artifact only after acceptance, and
   invokes that wrapper using the existing `-I -S -B` process and argument.
   The helper never writes acceptance, executes the wrapper or retries a send.
   All existing source freshness, privacy, ownership, Keychain, account/credit,
   root-prefix, prior-attempt and receipt guards remain in the unchanged runner.
5. `pending_review(reservation, report=actual_html_pin)` reads the completed
   first-v13 attempt, correlated receipt and retained answer. It reconstructs the
   expected HTML from the exact retained report and prepared projection/context
   and requires byte equality. It persists pending review, never delivery.
6. Main reads the complete report and records `reviewed(reservation,
   report_sha256=..., html_sha256=..., review_reference=actual_chat_reference,
   observed_at=actual_time)`. Only then may it provide the reviewed report to the
   owner. `delivered(reservation, review_sha256=..., delivery_reference=actual_message,
   delivered_at=actual_time)` records what already happened. A filename, heartbeat,
   worker readback or generated report is not delivery. These main attestations
   cannot be authenticated by local code; the trusted caller remains responsible.

`status()` is a readback of durable stages. On restart inspect those stages and
account history. A reservation/preparation without terminal evidence is uncertain
and not permission to invoke again. A reviewed-but-unacknowledged delivery requires
checking the actual chat before recording its real reference, never blind resend.
Existing runtime refusal of an interrupted prior account attempt remains a genuine
blocker; this helper neither repairs nor discards it. No quota reset or refund.

## Validation checkpoint

The initial six invented intake tests passed (0.280s); the initial full seven-test
set including actual installed first-v13 fake HTTP passed (39.650s). Independent
review requested canonical-journal, locked-freshness and attempt-inode strengthening;
these are implemented with new tests. The strengthened nine-test set passed
43.011s; eight pure tests passed again in 0.521s after root-prefix continuity
and separate-output checks. Covered cases: two cycles/newest conflict, restart deduplication,
blocked-case separation, actual captured/historical start exclusion, stale/bad pins,
review/delivery ordering and root/symlink protections. Installed first-v13 fake HTTP
and exact report/receipt integration passed on the strengthened helper. Exact-head
independent review and supported Python 3.12/3.13 CI gate merge. No private
inputs, real account state, provider call or actual delivery was used.
