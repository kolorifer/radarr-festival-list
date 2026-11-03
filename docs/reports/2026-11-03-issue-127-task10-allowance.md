# Issue #127 Task 10 allowance — engineering report

The dispatcher admits one exact new Task 10 owner body only after the original
nine slots and claims and the unchanged retained Task 9 snapshot are verified.
It binds the mixed historical launcher revisions to their individual claim refs,
rechecks the assignment and retained checkout before reservation, and checks
the snapshot again before launching a Terra/high child. Claims, locks, quotas,
no-replay behavior, other caps and unrelated model routes remain unchanged.

Offline synthetic tests exercise exact assignment and embedded prior review,
claim and retained-state drift, pre-reservation supersession, the intercepted
Terra/high launch and unrelated routes. No live worker, provider or model call
is made by these tests. The parent separately rehearses the actual offline
prompt and required local inputs and obtains independent review and CI before
the authorized installation and any Task 10 commissioning.
