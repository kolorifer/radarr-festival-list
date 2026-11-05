# Supervised executable module identity repair

The actual `python -m ai_movie_investigator.supervised_credit` entry executed the
command as `__main__`, while its authorizer imported the canonical module. These
were separate instances of SelectedEvidence and the prompted-credential ContextVar.
After real hidden input the canonical prompt check therefore refused before any
attempt reservation, credit debit or HTTP send. Earlier command tests invoked
an imported `main()` and did not test the executable module boundary.

The repair delegates the executable entry to canonical `main()`. No authority,
credential validation, expiry, ledger, ACL or network check is relaxed. A new
regression installs the declared runtime in a disposable private directory and
executes a genuine `python -m` subprocess through a pseudo-terminal. The test
enters only a dummy credential through real getpass; no-echo is asserted. An
offline HTTP sink exercises the actual authorization check, while independent
socket and DNS tripwires forbid network. Before the repair the fixture observed
the fixed `supervised_prompt_required` code after its prompt; after the repair it
reaches the authorized offline boundary, retains a three-cent fixture debit and
is deliberately stopped without a provider request. Linux positive fixtures use
the existing explicit ACL syscall fixture; runtime ACL checks remain intact.

21 focused executable/command tests passed on bundled Python3.12.14. Existing
reviewer and supported Python3.12/3.13 exact-head CI are required before merge.
The real retained slot1, enrollment, expired evidence, credit ledger and installed
runtime are preserved. No live retry, new slot, evidence refresh, key inspection,
provider access or production change is authorized by this repair.

The retained no-send conclusion follows the reviewed ordering: fsynced attempt
reservation and attempt records, then shared credit debit, must precede HTTP.
None exists for the refused real attempt. The local state does not establish an
independent provider billing audit, which was neither needed nor queried.
