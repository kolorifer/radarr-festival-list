# Explicit fourth-slot continuation

`continue-once --previous-evidence OLD --evidence NEW` reuses the existing manual
append-only grant machinery for exactly the retained eight-event history: three
consumed slots, a prior recovery grant and two retained three-cent reservations.
It validates the previous evidence against slot3, both previous attempt journals,
the original directory/file identities and shared ledger, and appends a grant
only for slot4. The original enrollment and every prior record remain intact.
Interrupted setup stays terminal; existing attempt4 paths, extra diagnostics or
unknown historical shapes refuse. Slot5 is not admitted anywhere.

The active prompted, root-locked slot4 session alone obtains a nine-cent ceiling
for the same fixed request/project; each wire check revalidates retained attempt
and credit hashes. Other paths retain their existing five/six-cent behavior.
The new CLI command only grants locally; it cannot prompt or automatically run.
Fresh evidence, secret-input checks, 60-second send authority, all response and
privacy guards and safe failure diagnostics are unchanged.

Invented-history tests cover preservation, one grant, cap and duplicate/restart
refusal, invalid input, interruption, changed prior records/project/evidence,
diagnostic append failure and installed `-m` continuation followed by the real
HTTP/framing/parser using fake socket I/O. Six of seven new tests passed locally;
one stopped in historical fixture setup at `supervised_evidence_changed` before
continuation. Its cause remains unproven and the guard is unchanged; no retry-to-
green. The installed full-path test passed. Independent review and exact-head
supported CI are recorded in the PR; a distinct private-copy rehearsal follows
acceptance rather than overwriting any existing runtime.

Three runtime modules, their manifest and focused tests changed. No actual
journal, evidence, key, service, schedule, account or source operation occurred.
No production behavior, scoring or separate cleanup assignment changed. The
previous remote outcome and actual charge remain unknown; reservations remain.
