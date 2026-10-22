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

## Verification and deployment

In progress. Regression tests cover rolling boundary expiry, restart/history
preservation, unknown requests, reservation caps and blocking before a new lease.
