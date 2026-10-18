# Stage 2 movie identity research — engineering report

Status: implementation and frozen replay complete; final CI, installed worker
validation and finite live pilot pending. No Stage2 merge or permanent activation.
[Authorized brief](2026-10-18-identity-research-brief.md) ·
[Issue51](https://github.com/kolorifer/radarr-festival-list/issues/51).

## Implementation

Separate private research database, immutable source versions, eligibility admission,
leases/fencing, review-only proposals, retry/awaiting-evidence states and durable
request reservations. Fixed combined100-request/14-case pilot;50 requests/10cases
per invocation. One TMDb provider, no tracker session. Historical assertions first,
fixed find/details/search routes, maximum2 variants/1page per type/3details.
No arbitrary URL, redirect, reconnect, approval or correction API. Local GET-route
checks complement a preconnected verified TLS socket with Landlock ABI6 and
libseccomp denial of all new network connections and protected files. Default-off
manual oneshot service. [Operation and safety boundary](../../deploy/IDENTITY_RESEARCH.md).

Source changes are confined to new research modules/tests/unit/config/runbook and
fixed diagnostic reason codes in the collector service. The running collector
remains unchanged. Original Stage1 schema remains v1 with provisional/unresolved
CHECKs; separate research storage needs no migration or rollback of intake.
Existing movie-intel/reviewed identity/Grab runtime is untouched.

## Stage A evidence

Fresh private inbox snapshot passes SQLite quick_check:460 evidence versions,
349 provisional groups,4 seeds,zero outcome-hook rows. Only4 records carry IMDb
IDs. Observer OFF. These groups are not a denominator of failed identifications.
The single historical storage warning lacks an exception reason, so its cause
remains unknown. Concurrent synthetic import/live/metrics stress can reproduce
SQLITE_BUSY; that is a hypothesis for the historical warning, not attribution.
Tests verify failed transactions are not acknowledged and bounded retry recovers
without partial writes or corruption. Fixed sqlite_busy/full/io/permission/etc
codes avoid exception/payload leakage; diagnostic rollout is not part of the
unchanged collector pilot installation.

Actual boundary feasibility proof on the installed worker location passed ABI6:
protected read/write, symlink, inherited fd, new TCP/IPv6/UDP/Unix sockets and
metadata mutation denied; own config/SQLite WAL allowed. Only the verified TMDb
TLS socket survived. This proof made zero HTTP requests. The initial fixed-env
check rejected Python's injected locale key; explicit LC_ALL fixed the allowlist.

## Frozen evidence results

All4 seeds replayed from private issue44 captures through the research planner;
19 frozen lookups, zero external requests, no missing response in final replay.
An earlier replay exposed one uncaptured competing detail. The manifest now
explicitly prioritizes three already investigated Fragmentos candidates, preserving
all other search IDs and the truncation flag. No response was invented.

- Fragmentos2025: Alejandro Rangel feature remains promising; missing IMDb
  crosswalk and runtime disagreement retained. Other same-name records remain
  competing candidates, never automatically accepted.
- Steve Howe Live Legends: Steve Howe2002 remains promising, with explicit
  title/year issues and absent IMDb association.
- Syd Barrett Up Close and Personal: no supported TMDb target in bounded evidence;
  missing crosswalk, not proof of catalog absence. Nearby films are not substituted.
- Rainbow In Performance: alternative record remains unaccepted; original year,
  edition/runtime/context contradictions retained. Requires human/distributor review.

Private source assertions, candidate IDs and exact provenance stay outside Git.
Existing public corroboration is historical issue44 evidence, not newly fetched
publisher verification. The live section will distinguish fresh TMDb observations.

## Verification and pilot

Pending final verification. No new metadata HTTP requests so far. Full test suite,
CI3.12/3.13, seedbox suite, dependency/scoring/config, actual installed denial and
post-run health results must pass before live pilot success is claimed.

## Remaining operating decisions

No permanent recurring traffic, identity repair, catalog edit, Telegram digest,
review capability or observer activation is authorized here. Candidate selection
is incomplete while the outcome hook is off and source IDs are absent from most
IRC observations. No tracker cookie is provisioned because it carries broader
session capabilities than this worker requires. Original publisher delivery has
no durable retry, so intake coverage remains incomplete.

Recommend a later reviewed schedule/budget, retention policy and human proposal
review interface after measured pilot findings. Keep the present worker disabled
and pilot ledger closed at completion. Do not silently turn retry due times into
a recurring service. Preserve source evidence, separate eligibility from research
yield and require reviewed exact-identity changes through the existing repair path.
