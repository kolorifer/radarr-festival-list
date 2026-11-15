# Seedbox event worker — exact deployment inputs and sequence

This is the main operator's runbook, not an activation instruction to an
engineering worker. Repository merge and real deployment remain separate.
Use the accepted final commit/package/manifest recorded in the engineering
checkpoint. Earlier candidate hashes are not deployment authority. Preserve the
existing actor/collector code, schedules, state, claims, consumed cases and credit.
The owner selected automated independent review, followed by later main audits.

## Package and entry

Build public code into a new empty owner-only directory with
`automation.seedbox_package.build(source, destination)` using the existing tested
Python environment. It returns the exact file count and SHA-256 of
`seedbox-runtime.json`. Transfer those exact regular files with directories0700,
files0600, no symlinks/hardlinks; independently verify the manifest and every byte.
The existing host interpreter is the collector venv's Python3.13; use `-I -B`
with site enabled so its existing requests/bs4 are available. No dependency install
or service change is part of package verification.

The literal installed entry is:

```text
PYTHON -I -B CODE/automation/seedbox_bootstrap.py CODE/seedbox-runtime.json MANIFEST_SHA MODE [MODE_ARGUMENTS]
```

Modes (all paths absolute, all SHA values exact):

| Mode | Arguments | Effects |
| --- | --- | --- |
| `verify` | none | Verify complete package and import required closure/dependencies; no source/key/network operation. |
| `provision` | `DESTINATION NOT_AFTER_UTC PROJECT POLICY_SHA SYSTEMD_CREDS_SHA` | One reserved user-scoped encryption from stdin into `project-key.cred`; never place a key in arguments. |
| `bridge` | `BRIDGE_SELECTION_PATH BRIDGE_SELECTION_SHA` | Genuine Mac module entry, no-UI native Keychain lookup then fixed SSH stdin to the exact installed provision entry. |
| `probe` | `INVENTED_CONFIG_PATH INVENTED_CONFIG_SHA` | Actual confined invented credential/dependency/state-file probe; no provider, source HTTP or Telegram calls. |
| `enroll` | `CONFIG_PATH CONFIG_SHA` | One explicit empty canonical queue enrollment, legacy import and lock creation. No provider or sender. |
| `run` | `CONFIG_PATH CONFIG_SHA` | Apply mandatory confinement; hold singleton lock; process durable events serially. |
| `recover` | `STATE OWNER_RECOVERY_PATH OWNER_RECOVERY_SHA` | Retain a material main-verified access recovery; never erase attempts, change credits or retry consumed sends. |

Configuration bytes must be canonical `contracts.encoded(config)` (equivalently
sorted compact JSON with no extra trailing bytes), so their file SHA equals the
binding digest. `enroll` stores the identical selection inside private state.
Do not edit it in place or create another queue to bypass a failure.

## Worker configuration schema

All fields below are required by their selected stage. No field contains the
OpenAI key, bot token, TMDb token or cookie contents.

| Field | Exact meaning |
| --- | --- |
| `kind` | `seedbox_event_worker_v1` |
| `state` | New canonical owner-only worker state directory. One queue only. |
| `initial_cursor` | Explicit accepted collector watermark. Main selected0 to inspect retained backlog; it is not an invitation to replay consumed cases. |
| `collector_identity` | Main's immutable identity digest for the selected collector; use SHA-256 of its canonical database selection. |
| `collector_database` | `{path, identity:[device,inode], journal_mode:"wal"}`; canonical existing inbox DB, with existing safe WAL/SHM. |
| `actor_database` | `{path, identity:[device,inode], journal_mode:"delete"}`; canonical existing `outcomes.sqlite3`. Do not fabricate WAL/SHM/journals or change journal mode. |
| `legacy_consumed_cases` | Exact seven unique case IDs from main's full preserved history, including the unknown attempt. No payload copying or reset. |
| `source_attempt_limit` | Selected finite integer1–3. This limits transient source-preparation retries, not cases per hour. |
| `sources` | Existing exact source-key/name map accepted for actor normalization. |
| `listing_source` | The exact selected source key; no arbitrary tracker origin. |
| `source_configuration` | `{path,sha256}` for the existing private environment file; only the three source keys and existing sender fields are consumed by their own adapters. |
| `cookie_file` | `{path,sha256}` canonical existing dedicated private cookie JSON. Configured home alias must resolve to this same file. |
| `credential` | `{kind:"seedbox_systemd_user_encrypted_v1",path,sha256,project,name:"movie-assessment-api-key",executable_sha256}`; ciphertext path/hash and systemd-creds executable hash. |
| `credit_policy` | The full finite policy below, copied without changing original timestamps. |
| `sender` | The finite topology selection below; not a self-generated fresh main review. |

`credit_policy` has exactly these fields:

```text
kind = seedbox_delegated_credit_v1
model_profile = existing MINI_PROFILE literal from ai_movie_investigator.credit_test
project = the actual selected proj_ account
account_reference = real retained balance/account evidence reference
observed_at = actual balance observation time
balance_usd = [integer numerator, positive denominator]
credit_expires_at = actual promotional credit expiry
delegation fields: delegated_at, expires_at, delegated_usd
prior_reserved_usd = [21,10] (or identical [210,100])
other_allocated_usd = retained allocation to other consumers
balance_evidence_sha256, prior_history_sha256, prior_credit_sha256
exclusive_cutover_reference = actual Mac-writer freeze/cutover evidence
paid_fallback = false
```

The initial observation must precede delegation by no more than900seconds.
Delegation expires no later than the actual credit; no timestamp refresh on read.
Ceiling must fit balance minus preserved reservations and other allocations.
Each assessment and its separate generated review reserves USD0.15 independently;
unknown attempts retain their debit. This is not a weekly USD budget, purchase,
automatic refill or verification of a token invoice.

`sender` requires:

```text
kind = main_selected_actor_topology_v1
revision = 06d17aafefb5a5161364e4bf6f63667a649e1aa3
sole_edit_writer = true
single_serial_pump = true
no_original_binding_republication = true
acceptance_reference = real main topology selection reference
observed_at = actual main selection time
expires_at = finite authority expiry, no later than credit_policy.expires_at
process = {pid, start_ticks, cmdline_sha256}
deployed_files = {relative_name: {path, sha256,
  metadata:[st_dev,st_ino,st_mode,st_uid,st_gid,st_nlink]}}
```

The eight exact relative names are `identity_triage_store.py`,
`identity_triage_intake.py`, `identity_outcome_outbox.py`,
`identity_triage_observer.py`, `retry_telegram.py`,
`torrent_research_evidence.py`, `movie_intel_service.py`, `deploy/run.py`.
File metadata and hashes are read-only pins, not permission to chmod public files.
The host verifies the selected process lifetime and these bytes before each edit.
It does not infer a fresh global writer audit from the PID. The original finite
main grant supplies the exclusive-writer/no-republication assumptions.

## Credential bridge selection

The Mac selection is private canonical JSON with these fields:

```text
kind = seedbox_keychain_bridge_v1
host, user, port = the already approved literal SSH destination
credit_policy = identical accepted policy
not_after_epoch = credit_policy.expires_at
ssh_key = {path, metadata:[st_dev,st_ino,st_uid,st_mode,st_nlink]}
known_hosts = {path,sha256}
state = new empty owner-only one-shot provisioning receipt directory
python = exact selected host venv Python path
bootstrap = exact installed host bootstrap path
manifest_path, manifest_sha256 = accepted installed package
destination = new empty host owner-only encrypted-credential directory
systemd_creds_sha256 = exact actual /usr/bin/systemd-creds bytes
```

Python only checks SSH key metadata/ACLs. `/usr/bin/ssh` alone reads its private
key. Public known-host bytes are hash-pinned. Native Keychain accesses only service
`codex.movie-project.openai`, account equal to the selected project, with no UI or
unlock and the retained five-second watchdog. The bridge has a bounded outer
lifetime and does not log the OpenAI credential. Only encrypted ciphertext and
nonsecret reservations are written. A failed/uncertain reservation is not replayed.

`LoadCredentialEncrypted` failed in the existing host's user-service context;
that result is preserved. This implementation uses the separately verified,
same-user `systemd-creds --user` IPC path, with fixed name/current timestamp/expiry.
No `--allow-null`, historical timestamp, system-scope or privilege escalation.
Reference: systemd257 `src/shared/creds-util.c` uses
`/run/systemd/io.systemd.Credentials` for these calls.

## Final invented host check, then activation

1. Verify the exact accepted installed package using `verify` above.
2. In a separate disposable private fixture area, provision only the literal
   invented value `sk-SYNTHETIC_FIXTURE`, project `proj_invented_fixture`, through
   the same installed `provision` entry. Never substitute a real key for this test.
3. Construct an invented configuration with `kind=seedbox_invented_probe_v1`;
   select that ciphertext and its real provision receipt. Supply fixture source
   configuration/cookie files, a fixture WAL collector DB with its writer kept
   alive so WAL/SHM exist, and a fixture DELETE-mode actor DB. Supply the selected
   process PID for proc-file grants and fixture `sender.deployed_files`. Add
   `denied_fixture_file`, a private fixture file outside every granted subtree.
   The actual selected credential executable and existing Python are unchanged.
4. Execute `probe` in the same actual user-service environment and confinement
   as the final unit. It must decrypt exactly the invented value, create/read
   retained evidence, and deny the ungranted fixture file. No model/source/bot call.
   Linux CI separately tests actual rollback-journal creation/commit/removal and
   collector read-only behavior where ABI6 is available. Journals observed before our open refuse locally. This is not atomic with
   subsequent SQLite lock acquisition; SQLite governs a concurrent appearance.
   An observed normal actor transaction gets up to three bounded local rechecks,
   then explicit operator inspection, without a credential-failure claim.
5. Main performs actual secure bridge provisioning only after exact code review,
   required checks and this invented actual-host check. Verify ciphertext and
   nonsecret provision receipts; construct final canonical worker selection.
6. `enroll` once with the exact seven consumed IDs, original legacy hashes and
   original USD2.10 reservations. Verify retained selection, inode bindings and
   canonical singleton before starting the service. Mac assessment execution
   stays frozen; main audit supervision is separate.
7. Render the concrete unit with `automation.seedbox_unit.render(...)`, binding
   the exact installed bootstrap, manifest and config paths/hashes. Install and
   start only this new bounded user unit through main's authorized deployment.
   It uses clean environment, the existing Python, no core dumps, no new privileges,
   bounded restart policy and mandatory application confinement. No actor or
   collector restart, schedule or production identity change is requested here.
8. Inspect retained state/report/receipt after real work. Confirm only the exact
   original card was edited; record receiver acknowledgement as sender-return
   evidence, never personal ingestion. Main later audits the report and review.

## Filesystem and failure facts

The queue is singleton and serial, with inotify hints and a durable cursor; there
is no one-case/hour restriction. Collector acceptance is the intake boundary;
the actor's existing pre-persist loss window remains. Weak/outcome-only linkage
gets an explicit waiting record and is reconsidered when collector evidence
changes. Missing listing/IMDb/crosswalk/ambiguity is case-specific, with no forced
identity or provider request. Directory names are traversable for descriptor
checks; file bytes have separate grants.

The actor's DELETE-mode transaction needs a future rollback-journal filename.
Landlock cannot grant an absent filename. Its narrow actor-state subtree therefore
has regular-file read/write/create/remove/truncate rights, also inherited by the
existing message-binding spool. No directory creation/removal is granted there.
Trusted fixed Outbox/PR204 logic constrains actual SQLite table/row changes and
never writes bindings. This is explicitly not a kernel filename/table guarantee.
No producer code/config writes or unrelated directory writes are granted.

Source429 retains a cross-case cooldown in the same durable denial record;
there is no separate-write crash gap. Shared source/auth/credential/provider
401/403/429 or bot401/403 blocks new affected work across cases; case-specific gaps
do not open that circuit. Provider429 is not interpreted as evidence that credits
can be purchased or retried. Main's material access-recovery evidence may resume
future work; consumed provider/sender attempts remain consumed. A circuit recovery
is private JSON with `kind=main_verified_shared_access_recovery_v1`, exact
`circuit_sha256`, `configuration_sha256`, actual `observed_at`,
`material_change=access_restored` and a real `observation_reference`. It does not
change policy, refill credit, alter source grants or reset state.

Every successful assessment has exact retained originals, crosswalk and report
bytes; a missing HTML file is reconstructed and hash-checked from those bytes
before review/delivery. Failures retain finite diagnostics, no raw error bodies or
secret URLs. Report/evidence/attempt records are not deleted on restart. No uncertain
provider or original-message edit is automatically replayed.
