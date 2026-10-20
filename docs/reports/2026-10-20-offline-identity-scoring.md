# Offline evidence-scoring evaluation

## Approved brief and scope

Build and test a numerical evidence-scoring approach against retained reviewed
cases. Show proposed weights, thresholds and changed decisions before production
activation. No downloads. This explicitly authorizes proposing experimental
weights; it does not approve a new production policy. Existing catalog cleanup
work in CODEX_TASK.md remains untouched.

## Implementation

Pure scorer and reproducible evaluator in `research/identity_scoring/`, frozen
sanitized fixtures/results, and regression tests in `test_offline_identity_scoring.py`.
No production module imports the scorer. No new dependency, provider fetch,
scheduler, runtime flag, queue mutation or acquisition integration. Existing
private evidence was read with SQLite read-only connections and exported through
an attribute allowlist; no fresh tracker/TMDb requests were made for this task.

Proposed weights: **title/alias 30, documented year 20, runtime 15, original audio
language 10, tracker IMDb 25**. Maximum 100; contradictions can subtract points. Missing
facts score 0 and never renormalize other weights. Candidate IMDb–TMDb mapping is
a prerequisite, not an extra circular vote when the tracker has no ID.

Runtime earns `15 × max(−1, 1 − abs(source−candidate)/candidate/0.10)`.
Title earns `30 × (2 × normalized edit similarity − 1)`, taking only the best
canonical/alias match and preserving numeric sequel-token protection. Year and
language score their positive/negative weight for agreement/disagreement. Audio
codec, resolution, group and file size score 0. Director/cast/plot/images score 0 in
this initial proposal because independent source annotations are insufficient.

Proposed acceptance: **score ≥ 70 and conservative winning margin ≥ 15**, provided
source/crosswalk/candidate-integrity checks pass. Missing rival fields are assigned
optimistic possible points when computing the margin. Conflicting tracker IDs
still require human review; arithmetic cannot override this boundary. See the
[experiment README](../../research/identity_scoring/README.md) for exact semantics.

## Retained-case replay

| Case | Current identity behavior | Proposed offline result | Points / reason |
| --- | --- | --- | --- |
| Aayirathonnu Nunakal | Generic identification | Identify same movie | 75; documented alias, 2023 later-release date, 104 minutes, Malayalam |
| 2018: Everyone Is a Hero | Review | **Would identify** | **73**; exact alias/year/language, 148 versus 150 minutes, IMDb tt9006564 / TMDb 866440 |
| Bruce Almiighty | Generic typo identification | Identify same movie | 70.71; near title, year, verified tracker ID; no NFO points |
| Madame Bovary | Fresh occurrences require review; existing occurrence closed | Review | Remake 54.92 versus 1949 film 38.68; wrong tracker ID and conflicting source evidence; incomplete alternatives |
| Aberfan | Owner skipped | No automatic identification | 50; missing verified IMDb crosswalk; no reopening |
| Fragmentos | Historical unresolved | Review | Best 60.83; incomplete candidate/crosswalk evidence |
| Syd Barrett Up Close and Personal | Historical unresolved | Review | Best −20; no supported exact mapping |
| Rainbow In Performance | Historical unresolved | Review | Best −35; title/year/runtime disagreements and missing mapping |
| Steve Howe Live Legends | Historical unresolved | Review | Best −8; title/year discrepancies and missing mapping |

Three automatic choices match the available owner-reviewed target labels. **Only
Everyone Is a Hero changes from review to automatic identification.** These are
identity outcomes only, never download decisions. No production statuses changed.
The dataset has four owner-reviewed target labels (including review-only Madame
Bovary), not nine confirmed ground-truth identities. Historical unresolved cases
are refusal controls, not labeled negatives. Earlier Hamnet/Not Not Jazz repairs
are outside this batch; this is not an exhaustive historical benchmark.

Madame's NFO 114 minutes / English was manually transcribed from retained source evidence;
the current parser does not support that layout. Its description instead says
2014 / 118 minutes and lists remake actors. This illustrates why metadata association
cannot be counted as infallible. Black-and-white screenshots influenced the
owner's verdict but are not machine features in this experiment.

## Sensitivity and adversarial probes

Thresholds 65 and 68 makes the six-minute synthetic runtime discrepancy pass. At 70,
Everyone Is a Hero at 73 passes; a five-minute difference in this otherwise identical
150-minute example scores 70, while six minutes scores 69 and requires review.
At 72 Bruce moves back to review; at 75 only Nunakal passes; at 78 none pass.
These boundaries emerge from the sum, not movie-specific minute tolerances.

A margin of 5 or 10 accepts the synthetic close runner-up (gap 11.24); margin of 15 or 20 keeps
it for review. Missing runtime/language on a rival yields an optimistic 75 against
the winner at 73, so the conservative margin is −2 and review is required. Halving the
runtime scale makes the same close rival look easier to beat; doubling it accepts
the six-minute discrepancy. Sensitivity results are saved in full.

Equal weights of 20 each, or shifting 5 points from tracker ID to runtime, sends Bruce
back to review. Shifting 5 points from runtime to title preserves the three observed
choices. There is not enough data to prefer these alternatives statistically.

Twenty synthetic controls cover missing source facts, runtime boundaries,
contradictory attributes, source-ID conflicts, wrong-release NFO, missing mapping,
non-movie candidates, numeric title differences, incomplete retrieval and close
rivals. All satisfy the declared experimental policy, not an empirical accuracy
claim. One additional synthetic blind-spot probe deliberately replaces the sole
candidate with a wrong ID but indistinguishable metadata: it selects the wrong
candidate. No score can recover a correct movie omitted from its inputs.

## Technical verification

Full local suite: **694 tests passed, with two Linux-only skips**. All 15 new
scorer tests passed. Linux CI Python 3.12 and 3.13 passed on implementation
`28eb06f` in draft [PR #78](https://github.com/kolorifer/radarr-festival-list/pull/78).
The final follow-up changes only reporting text. No merge or deployment was run.
A read-only production check confirms clean actor runtime
`658d8f838aed7a03db7d01244254362fba99369a`; actor, collector and research timer
remain active. No notifications or downloads were triggered.

The evaluator is deterministic, refuses
nonfinite/invalid inputs, does not read expected-label fields, and runs with
network sockets blocked. Tests also check source data immutability, repeated-alias
invariance, candidate-order invariance and absence of production imports.

## Recommendation and decisions for review

The proposal addresses the two-minute mismatch without adding a film exception.
It is not a calibrated probability model, and the development examples are too
few to justify a production false-positive rate. Keep production unchanged.
Review the proposed 30/20/15/10/25 weights, 70-point threshold, 15-point margin and runtime curve.
Before enabling automatic decisions, add more independently labeled ambiguous
movies/remakes and evaluate an approved read-only shadow run with reviewable
feature contributions. Keep conflicting IDs review-only and acquisition behind
explicit confirmation. No model training or automatic feedback loop is included.
