# Unique-identity rival bounds in shadow

## Approved scope

Implement the proposed generic comparison improvements starting with The Beast:
realistic rival upper bounds, consistent unique IMDb evidence, bounded detail
prioritization and unseen-page treatment. No changed weights, thresholds or
request caps; actual conflicting IDs remain blocked. Shadow only, no downloads
or notifications. Preserve unrelated active CODEX_TASK and separately authorized
Grab confirmation actor work.

## Implementation

Fresh targeted discovery can carry a unique checked tracker/movie mapping into
the scorer only after validating search-response integrity. The leading candidate
must have full title/year/identity points, positive runtime and film-language
support, checked source/NFO binding and no conflict blocks. A known second
candidate asserting the same IMDb contradicts uniqueness and keeps review.

Under that explicit unique-mapping assumption a different candidate cannot earn
the source-ID25 points. Its maximum is75, or50 if an explicitly different IMDb
already contributes minus25. Search-only title/year differences do NOT reduce
that maximum: missing aliases/dates remain unknown. Detailed rivals retain any
stronger existing bound. Unseen paginated results have the same75 ceiling, rather
than disappearing or masquerading as a completed search. The report records
search completeness, the bound and its assumption. Missing proof, malformed
pagination and contradictory summaries do not enable this refinement.

The four-detail limit is unchanged. Candidates are prioritized by upper score,
then existing title/year relevance; direct verified IDs remain first. The worker
still inspects up to four details, rather than using early stopping to skip all
rival checks. This deliberately retains opportunities to find contradictory
catalog records while staying inside the existing budget. No additional search
or detail requests, new score weights, or movie-specific exceptions.

`scorer.py` applies and audits bounds. `fresh.py` passes checked mapping evidence
only for valid targeted discovery. `refresh.py` records query integrity and uses
upper scores for detail priority. Production actor code is untouched.

## Retained Beast replay

Read-only replay of the30 retained candidates gives TMDb914206 / IMDbtt14407336,
score100, margin25, unseen upper75, would-identify. All30 remain visible. The
retained source-ID25 and absence of crosswalk blocks establish the earlier unique
mapping result under the previous implementation; this replay does not refresh
or independently re-query that mapping. The current exact occurrence was checked
and the installed actor catalog has one agreeing record. The local-conflict guard
then clears, leaving no replay blockers. Zero provider requests and no live
report, queue, identity or approval mutation. This is a policy replay of retained
evidence, not a new live score.

## Limits

Uniqueness is conditional on the checked provider mapping, not proof that a
catalog can never contain an undiscovered duplicate or bad metadata. Known
contradictory mappings remain review-only. Scores are evidence points, not
probabilities. Weak leaders can still fail the15-point margin against75.
Actual source-ID conflicts and the installed-catalog recheck remain mandatory.
Existing bounded refresh/freshness rules determine when live results change.


## Validation and deployment

Runtime **d04608bde5d8d3be119aa07de4136ce33dbbccd8** passed763 local tests
(163.691s,two Linux-only skips),763 seedbox tests(47.230s), and bothPython3.12/3.13
CI jobs(run40099956169). Eight new bounds tests cover duplicate mappings, missing
proof, weak leaders, unseen bounds, ID conflicts and unchanged weights. Two
additional targeted tests cover malformed pagination and contradictory summaries;
all10 bounds tests pass locally. These extra tests accompany this report without
changing the tested runtime code. Existing targeted-discovery expectations now
assert visible rivals and explicitly audited unseen bounds rather than an
unconditional pagination rejection. Ordinary historical scoring fixtures pass.

Exact archive deployed in shadow with source hashes verified. Private backup
edition-shadow-backup-75xjfc89. Eight bounds tests pass from the installed archive;
health200, actor/collector/research timer active, existing shadow timer resumed.
Actor remains **f34cd4d401cedf1be671b11b00ba86bcc30bf15e**, including separately
authorized Grab confirmation work. Protected configuration/actions, actor code,
research timer, pilot and request/refresh ledgers are unchanged. No provider
requests, notifications or downloads from deployment. No fresh run forced.

Live retained scores remain unchanged until normal admission. Monitor now knows
the offline Beast25-point-margin result and watches the first fresh result with
bound and local-catalog audits. PR78 remains draft; no production activation.
Rollback switches shadow unit to bade2d6 and preserves state. Unrelated active
CODEX_TASK remains intact. The preceding documentation-only CI run16d1f1e had
an unrelated concurrent SQLite test error; the exact deployed revision passes
both CI environments and local/seedbox full suites.
