# Bounded daily research allowance

## Authorized brief

Investigate the three queued cases without waiting until October26. Keep requests
bounded, deploy in shadow/review-only operation, and send no notifications or
downloads. Preserve actor matching, explicit download consent and scoring policy.

## Implementation

The existing recurring research ledger now enforces five attempts and25 requests
per rolling24hours instead of seven days. Each evidence version still has at most
five requests and one attempt. Reservations commit before transport; unknown
outcomes count. Existing history, provider cooldown/suspension, confinement,
schedules and the closed original pilot are preserved. No database migration or
reset is needed. Daily budget counters replace misleading weekly report fields.

This increases maximum research throughput sevenfold; it does not promise five
completed investigations daily. Provider failures and missing evidence still stop
work safely. The daily timer is unchanged; boundary timing can defer a case to
the following daily run. Scoring remains shadow-only, with its separate caps and
October27 end unchanged.

## Tests and verification

- Local full suite:716 tests passed, two Linux-only skips,157.621seconds.
- Seedbox full suite:716 tests passed,46.773seconds, including Linux isolation.
- CI Python3.12/3.13 passed on776986f (run39813536130).
- Eight recurring-budget tests cover exact rolling boundary expiry,
  restart/history preservation, unknown reservations, caps, no extra lease at
  exhaustion, provider suspension and no repeated old-version research.
- A private copy of the live ledger leased exactly the three queued cases with
  the new code before deployment. No live ledger was reset or rolled back.

## Deployment result

Implementation **776986f** deployed by replacing only the installed research
worker's `identity_recurring_store.py`; SHA256
`04c61a54699f2918fe4d608794b838f59395b5c25800005a4874840cddcd2992`.
Actor remains **658d8f838aed7a03db7d01244254362fba99369a**, shadow scorer remains
**cf70212**. PR78 stays draft; production scoring is not activated.

Private backup: `~/.local/state/daily-research-o162o_s2`. Config, old worker code,
research/digest databases, report and actions were backed up. Actor was briefly
paused to prevent digest races, then restarted unchanged. Three exact maintenance
report versions received suppressed receipts, not sent receipts. Existing sent
counts did not change. Local/public health200; actor, collector and both timers
active. Collector PID, configuration, other installed code, action/alternative-grab
state, timer definitions and original shadow deadline stayed unchanged. Old
attempt/request rows were compared unchanged after the run. Rollback restores
only the backed-up worker module; never restore old research or approval state.

## Actual intake and results

All three queued cases completed one bounded research attempt: **9 TMDb GETs**,
zero unknown request outcomes, zero cases left queued. Daily usage3/5 attempts
and9/25 requests. These are proposals, not accepted identities.

| Case | Retained research result |
| --- | --- |
| The Beast(2023) | Candidate TMDb914206 / IMDbtt14407336, runtime146min. Details report2024 release date; shadow adapter recognizes2023 in retained date evidence. Other same-title candidates exist; source/local conflict remains. |
| Once Upon a Time in China II(1992) | TMDb10618 / IMDbtt0105839, runtime113min; combined filename title still triggers title conflict. |
| Once Upon a Time in China III(1993) | No supported candidate found using the combined filename title. |

Three bounded shadow validation runs made **6 additional GETs** (one exact tracker
page and one TMDb search per case), within existing independent shadow caps.
All stopped at candidate discovery: the full `Wong Fei Hung … aka …` titles return
no search candidates; broad `The Beast` exceeds the three-candidate limit. No new
complete fresh score was produced. Report retains incomplete snapshot scores:
The Beast50, margin40; ChinaII15, margin15; ChinaIII no candidates. These are
**not fresh evidence scores or probabilities**. Only Genealogies retains its
previous complete fresh100 result. Total shadow coverage is12 snapshots:8
historical and4 genuinely new, including these3 investigations.

## Remaining limitations and review

The weekly wait is removed, but candidate discovery still needs improvement:
generic alias splitting and bounded disambiguation could help without weakening
conflict/review gates. They are not implemented by this budget fix. In particular,
ChinaII's combined title is penalized by the existing title/sequel-token scorer;
this incomplete score must not be interpreted as evidence the film is wrong.
The current refresh diagnostic combines empty and oversized search results.

Failed refreshes may retry hourly within existing40-GET/day shadow allowance.
Research still makes only one attempt per evidence version; missing evidence
requires review or a material update. More than five cases/day can still queue.
No thresholds, source-conflict safeguards, review decisions or download consent
changed. No downloads, identity corrections, Telegram messages or webhook replays
were deliberately triggered. Pilot deadline remainsOctober27 at19:12Warsaw.

## References and project context

[Draft PR78](https://github.com/kolorifer/radarr-festival-list/pull/78),
implementation776986f. PROJECT_STATE and decisionD039 updated. Existing unrelated
CODEX_TASK cleanup assignment preserved; this report archives the current brief.
Monitor now checks queued cases and budget blockers as well as completed scores.
