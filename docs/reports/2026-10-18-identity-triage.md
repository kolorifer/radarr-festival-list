# Engineering report: issue #47 Stage 1 observation

**Specification:** [approved brief](2026-10-18-identity-triage-brief.md),
[issue #47](https://github.com/kolorifer/radarr-festival-list/issues/47).
**Result:** implementation prepared; production activation blocked by the required
isolation gate. No Stage 2 work. Review and deployment acceptance remain open.
**Verification date:** 2026-10-18.
**Implementation:** [draft PR #48](https://github.com/kolorifer/radarr-festival-list/pull/48),
final runtime **a64b948eedc78a349d31a6dcfea4324cdcdb11b0**. Merge/deployment held.

## What changed

A standalone stdlib receiver stores authenticated release.new metadata in a private
SQLite inbox before acknowledging it. It has no provider lookup, notification,
approval or acquisition code. Separate delivery UUIDs, release fingerprints,
versioned evidence and opaque provisional cases support replay/deduplication while
keeping conflicting identities unresolved. Malformed movie-like records are
quarantined without retaining unsafe text. A default-off bounded observer records
current identity outcomes without controlling the existing action flow.

Explicit local maintenance supports four private seeds, bounded read-only retained
reconciliation, aggregate metrics and consistent private backups. The supplied
service unit hides unrelated home/config/state paths and refuses startup if its
required user namespace cannot be established. The runbook documents activation,
health/coverage gaps, disablement, fixtures, backup and rollback.

| Component | Purpose |
| --- | --- |
| identity_triage_intake.py | Strict projection, schema/source/event checks, quarantine |
| identity_triage_store.py | Transactional inbox, evidence/case correlation, metrics, backup |
| identity_triage_service.py | Bounded loopback receiver, authentication, isolation check |
| identity_triage_observer.py | Default-off bounded current-outcome hook |
| identity_triage_admin.py | Explicit private seed/reconciliation/maintenance commands |
| movie_intel_service.py; deployment_config.py | One observer call and optional configuration preflight |
| test_identity_triage.py | Synthetic intake, failure, recovery and isolation regressions |
| deploy/identity-triage.service; deploy/IDENTITY_TRIAGE.md | Mandatory sandbox and operational runbook |

## Deployment result: blocked, production unchanged

Fresh production check: **30adc20b7d46bbe89bb14728d778d9d1142c57c6**, clean;
movie-intel active/running, NRestarts=0, local/public health 200, 1,909 catalog movies.
Both approved private identity bindings remain configured. Recent five-minute
journal check: zero approval attempts and zero tracebacks. No production checkout,
unit, environment, binding, notifier, filter or action/cache state was changed by
this task. No live replay, notification, approval, Radarr call or download occurred.

The provider's systemd 257 user manager cannot create user namespaces. A transient
probe with PrivateUsers=yes failed **217/USER**, Operation not permitted. A second
probe with InaccessiblePaths alone reported success but silently ignored isolation;
the test process could still access the existing approval store. Therefore deploying
a same-user collector would violate the explicit no-pending-action-access requirement.
No collector unit or release.new route was installed, and no observer flag was enabled.
The transient probes did not stop/restart or alter any production service.

The current service sandbox cannot meet the access-denial gate. A final read-only
kernel capability query found **Landlock ABI6 available**. That is a possible
alternative, not proof of effective collector isolation: no Landlock policy,
launcher, negative-access validation or deployment has been implemented/reviewed.
A supported namespace boundary or a separately designed and reviewed alternative
sandbox is required before activation. This report does not authorize root/provider
changes, new account privileges or weakened isolation.
Merge/deployment are held for review instead of claiming the blocked gate passed.
Production code remains the earlier tested revision. Main is
fb31c6178ba11b64ea6f4164de2d2ce060f38148; its only differences from production are
two documentation files, so existing runtime code matches main. Stage 1 is unmerged
and its implementation tree is not deployed. Code/routing rollback was documented but not exercised against
production because no rollout occurred. Disablement and SQLite recovery were tested
synthetically.

## Installed source and actual intake coverage

Installed autobrr binary SHA256 matches the previously verified official v1.88.0
binary: `eb8e3e466a7b6edef87e8b6aa3372a3be1760c2c23a2772fe1a0a9b35d49158f`.
Verified source: [event schema](https://github.com/autobrr/autobrr/blob/v1.88.0/internal/domain/notification.go),
[publish timing](https://github.com/autobrr/autobrr/blob/v1.88.0/internal/release/service.go),
[webhook transport](https://github.com/autobrr/autobrr/blob/v1.88.0/internal/notification/services/webhook/webhook.go).
release.new is emitted before filters; retained rows may be written only after a
filter with active actions matches. The sender makes one request, no durable resend
outbox. Regenerated webhook UUIDs do not constitute new film identities.

Read-only route inspection found no release.new notifier. Existing Telegram route
contains connection/update events; existing movie-intel webhook contains action
approved/rejected/error events. All were preserved. The enabled indexer is covered
by the new source-pair allowlist design; its identifier/display name were checked.
The actual wire payload on a new live route remains unverified because activation
was blocked. Version/source schema verification is not mislabeled as live capture.

**Actual new live intake: zero.** No service/route was activated. Last-good live
movie delivery remains null in isolated validation metrics. Retained rows and seeds
are separately labeled and never contribute to live delivery-health timestamps.

## Isolated validation against private retained evidence

At the bounded read-only snapshot, autobrr retained 457 rows: 449 movies, 7 TV rows,
1 unknown-type row. Only allowlisted columns were exported to owner-only private
local validation storage; no URLs, raw payloads, credentials or action records.
This is a retained-history sample, not an announcement denominator.

| Measurement | Result |
| --- | --- |
| First retained scan | 457 scanned;446 accepted;4 quarantined;7 rejected |
| Movie coverage in retained sample | 446/449 accepted;3/449 quarantined |
| Quarantine detail | 2 unsafe release-name texts;1 invalid year;1 unknown movie-like type |
| Repeat retained scan | 450 duplicate events;7 TV rejections;no new evidence/cases |
| Four private seeds | 4 accepted;repeat produces 4 duplicate events |
| Final distinct release fingerprints | 446 |
| Final evidence versions | 450 (includes 4 seed assertions linked to retained releases) |
| Final provisional cases | 342, all unresolved |
| Consistent backup | quick_check OK;owner-only files;no overwrite |

The four seeds are Fragmentos, Steve Howe Live Legends, Syd Barrett Up Close and
Personal, and Rainbow In Performance. Each uses retained private source assertions,
original release association, a private-evidence digest and contradiction codes.
All remain unresolved; no candidate TMDb mappings were imported. Private evidence
was available for all four. Different/missing ID assertions intentionally partition
provisional case groups, while the release fingerprint links their evidence versions.
The extra seed versions are corroborating provenance, not four newly resolved films.

Synthetic deduplication:24 simultaneous identical deliveries → 1 accepted + 23
UUID duplicates;16 distinct release deliveries →16 preserved associations within 1
provisional case. Regenerated UUID with identical evidence adds no evidence version;
changed evidence adds a version; out-of-order old evidence reuses the original.
Conflicting film IDs stay separate/unresolved; conflicting reuse of an event UUID
is quarantined (409). Crashes before commit roll back; crashes after commit recover as
duplicates. These synthetic results are separate from retained and live counts.

## Tests and release gates

Final runtime revision **a64b948eedc78a349d31a6dcfea4324cdcdb11b0**:

- Focused Stage 1: **44 tests passed** (12.219s), including the five-second hard
  connection deadline against a client continuously trickling header bytes.
- Full local Python 3.12 suite: **435 tests passed** (181.744s) on the final runtime
  revision. Earlier complete runs passed 433/434 as regressions were added.
- [CI run 39145790474](https://github.com/kolorifer/radarr-festival-list/actions/runs/39145790474):
  **435 tests pass on Python 3.12 and 3.13** (31.299s/31.538s) on that exact revision.
- Dependency check passes. Frozen scoring unchanged: 1,909 candidates, 387 qualified
  (224 existing, 163 new). No dependency changes.
- Private source URL/identity scan passes for all 14 changed files; diff check passes.
- Full new suite was not run in the live production checkout. Synthetic tests use
  isolated temporary stores/HTTP servers; CI provides both supported Python versions.


Covered: accepted/unsupported/source/auth inputs, missing/invalid IDs, malformed and
hostile text, oversized/strict JSON, negative-field redaction, event/evidence/case
correlation, concurrency, real process crash boundaries, actual SQLite-full failure,
busy/capacity/permissions, repeatable migration and unknown version refusal, backup
integrity/overwrite refusal, immediate disable, read-only bounded reconciliation,
four unresolved seeds, observer failure containment and no receiver outbound sockets.
Existing identity/acquisition tests run unchanged in the full suite.

No new dependencies or scoring/policy changes. No deployed runtime SHA for Stage 1.
Production isolation preflight **failed**, intentionally blocking activation. Live
route-health, running collector configuration and passive capture checks are therefore
not passed or fabricated.

## Permissions and other limitations

A first local backup attempt correctly refused a validation directory whose mode
was755. Mode700 was reapplied, and the backup passed. The workspace directory mode
changed again between tool calls, so private validation metadata/stores were moved
to an owner-only directory under /private/tmp; subsequent checks showed directories 700
and files 600. Private data files remained 600; the failure was not bypassed. No
production authentication incident occurred; wrong-auth tests were synthetic only.

Remaining limits: current service-isolation blocker (Landlock alternative unimplemented); no actual release.new capture; retained
DB is incomplete history; no durable publisher retry or observer outbox; source quiet
and lost deliveries cannot be distinguished; missing IDs can fragment provisional
cases; name-fallback release correlation is weaker than a source torrent ID; malformed
records without UUID receive fresh opaque quarantine IDs; conservative unsafe-text
quarantine needs explicit review, not automatic recovery. Store capacity is bounded
without automatic retention deletion. Stage 2 research, review UI/digests, new identity
repairs and upstream durable publishing remain out of scope.

## Handoff

Review the implementation and provider isolation prerequisite before any activation.
The [runbook](../../deploy/IDENTITY_TRIAGE.md) gives the concrete staged procedure and
rollback boundaries. Draft PR #48 and issue #47 remain open; the unrelated CODEX_TASK.md assignment
was preserved. No Stage 2 task or new product decision was started.
