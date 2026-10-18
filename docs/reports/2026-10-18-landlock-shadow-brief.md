# Issue #49: bounded Landlock attempt and conditional shadow deployment

The user authorizes one focused feasibility pass and one integration/validation
pass to resolve PR #48's isolation blocker. If required isolation and every Stage1
acceptance gate pass, merge the reviewed PR and deploy observation only. Stop for
owner review if a fundamental blocker requires extensive redesign.

Source: [issue #49](https://github.com/kolorifer/radarr-festival-list/issues/49),
building on [Stage1](2026-10-18-identity-triage-brief.md). Preserve existing services,
both reviewed identity bindings, action state and notification/filter settings.
Only a separate authenticated loopback release.new route may be added. Outcome
observer may remain off. No provider/root/account privilege changes, credentials
rotation, Stage2 work, provider research, new mappings, live notification/approval,
Radarr calls or downloads. Report actual denial proofs and distinguish synthetic,
retained and real intake. Existing unrelated CODEX_TASK remains untouched.

[Report](2026-10-18-landlock-shadow.md) and [runbook](../../deploy/IDENTITY_TRIAGE.md).

Completed: minimal boundary passed, PR48 merged and separate shadow collector
deployed. The report distinguishes retained/seed results from3 actual live movie
deliveries and records the remaining operational limits.
