# Offline movie-identity evidence scoring experiment

**Research only. The offline evaluator has no provider client or action integration.**
The separate shadow refresh tools can make bounded provider requests when explicitly
run; they are not activated by this repository integration. No production identity
or download approval is granted.

Run from the repository root with the existing Python environment:

```sh
python -m research.identity_scoring.evaluate --output /tmp/identity-score-results.json
python -m unittest test_offline_identity_scoring -v
```

`cases.json` contains allowlisted frozen metadata from nine retained cases, with
provenance/limitations notes. No tracker URL, credentials, action token or raw
payload is included. `results.json` is reproducible, including the fixture hash,
per-attribute contributions, candidate ranking, guard reasons, sensitivity runs,
20 synthetic controls and one explicit retrieval blind spot. Evaluation labels
are never passed into the score calculation.

## Proposed arithmetic

| Attribute | Maximum points | Comparison |
| --- | ---: | --- |
| Best documented title/alias | 30 | `30 × (2 × similarity − 1)`; Unicode-normalized Levenshtein similarity. Count the best alias once, never repeated title fields. Numeric/roman sequel tokens must agree to contribute title similarity. |
| Documented release year | 20 | +20 when the source year appears in the candidate's documented years; −20 for a documented disagreement; 0 when missing. |
| Source runtime | 15 | `15 × max(−1, 1 − relative_difference / 0.10)`; relative difference uses candidate runtime. |
| Original audio language | 10 | +10 agreement, −10 disagreement, 0 missing. |
| Tracker IMDb association | 25 | +25 agreement, −25 disagreement, 0 absent. A candidate's own IMDb mapping alone earns no points. |

Weights sum to 100. Scores can be negative. They are evidence points, **not
probabilities**. Missing attributes earn zero; never rescale the remaining
attributes to 100. A unique verified IMDb–TMDb movie mapping is required separately.

Audio codec, channel count, resolution, file size and release group receive **0**:
they describe the release, not its movie identity. Director/cast/plot and visual
features also receive 0 in this initial experiment: we do not have enough reliably
source-derived annotations to propose calibrated weights or an image model.
Repeating catalog facts in a tracker-generated description is not independent
corroboration. Candidate cast/director metadata must never masquerade as source
observations.

Proposed automatic-identity threshold: **70 points**, plus a **15-point margin**
over every other retrieved candidate. Margin uses each rival's optimistic upper
score for missing facts that could still be compared to known source facts. Thus
an incompletely described rival does not look artificially easy to beat. A sole
candidate is compared with a zero-point baseline; that does not prove the catalog
contains no unseen alternatives.

Checked source provenance, source-bound NFO facts, movie media type, a verified
crosswalk and a complete candidate set remain prerequisites. Existing source-ID
conflicts remain review-only regardless of score. Unknown integrity flags fail
closed. These are capability/integrity boundaries, not film-specific exceptions.
The experiment does not supply the future production evidence-validation adapter.

## Important outcomes and limitations

Everyone Is a Hero: title 30 + year 20 + runtime 13 + language 10 + source ID 0 = **73**.
Nunakal = **75**. Bruce typo = **70.71**, using the tracker ID and no NFO points.
The only changed real automatic decision is Everyone Is a Hero: review → identify.

Madame Bovary is a counterexample to trusting a high-ranking candidate: the wrong
tracker-linked remake scores 54.92, while the human-selected 1949 film scores 38.68.
The evidence includes a 114-minute NFO, inconsistent remake description and wrong
source ID. The case remains review-only; the numeric model has no equivalent of
the owner's black-and-white screenshot interpretation. Its completed occurrence
review is not reopened or used to train the model.

A synthetic omitted-candidate probe intentionally shows a wrong automatic choice:
if a wrong candidate has indistinguishable visible attributes and the correct
movie is missing from a supposedly complete retrieval, scoring cannot recover it.
This is not a real observed false-positive rate; it exposes the dependency on
candidate retrieval and trustworthy evidence.

The four owner-reviewed identities are development examples, not a held-out test
set. The other five cases have no confirmed positive identity labels. Twenty
synthetic controls check policy mechanics, not statistical accuracy. Thresholds
and weights are hand-proposed here, not learned or calibrated. No safe production
false-positive rate can be inferred. More labeled confusable candidates and a
read-only shadow evaluation would be needed before recommending activation.

## Passive shadow pilot

`python -m research.identity_scoring.shadow --database /private/research.sqlite3
--output /private/shadow/report.json --started UNIX_SECONDS --until UNIX_SECONDS`
reads only retained research proposals and writes a separate comparison report.
The interval is at most seven days. It does not import or alter the production
matcher. See [pilot scope and limitations](../../docs/reports/2026-10-20-identity-scoring-shadow.md).
The runtime socket guard forbids provider calls. Existing historical proposals
are explicitly separated from results arriving during the pilot. Missing retained
provenance remains blocked; numerical scores alone do not constitute identification.

The approved fresh-evidence extension runs as
`python -m research.identity_scoring.refresh --actor-code /path/to/production/code`.
It retains the original pilot deadline and reads the private pilot configuration.
Only the isolated shadow unit uses it; the production matcher remains unchanged.
[Fresh evidence scope and bounds](../../docs/reports/2026-10-21-fresh-shadow-evidence.md).
