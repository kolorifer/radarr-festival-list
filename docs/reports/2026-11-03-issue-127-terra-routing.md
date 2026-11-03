# Issue #127 corrective worker model — engineering report

The dispatcher builds the existing coding command with `gpt-6.1-terra` only
for the repository, issue and task recognized by the exact retained Task 9
allowance. The Task 9 instruction still selects high reasoning. Other task
commands and the separate quota probe retain `gpt-6.1-sol`. The dispatcher
retains its existing claims, locks, quota, isolation and continuation checks.

The offline tests intercept the actual subprocess launch, verify its model,
reasoning and sandbox flags, and check unrelated issue/repository launches and
the quota probe. They do not invoke an actual model or consume a worker slot.
The local Codex model catalog advertises Terra and high reasoning; this alone
does not establish entitlement or successful inference in the dispatcher.

This repository change does not install the dispatcher or commission Task 9.
The exact selective launcher candidate, verification results and rollback
baseline are retained in the coordinator's private checkpoint. Installation
requires separate authorization. Live investigator use, real-case access,
provider calls, spending and activation remain separately restricted.
