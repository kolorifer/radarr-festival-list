# Engineering report: local launcher quota repair

**Specification:** [Completed brief](2026-10-25-launcher-quota-repair-brief.md).
**Result:** repaired locally; live quota check succeeds; existing task remains eligible.
**Base revision:** `564a022`, installed `main` checkout.
**Verification date:** 2026-10-25, local macOS host.

## Confirmed cause

The installed quota probe exits 0 in the LaunchAgent environment and produces
fresh quota telemetry. The account currently reports a weekly primary window
(`window_minutes=10080`) and no secondary window. The old parser accepted only
`primary.window_minutes == 300`; its last matching five-hour record was from
2026-10-18 and had expired. It therefore discarded successful fresh observations
and raised QUOTA_UNAVAILABLE. Its generic error misleadingly suggested checking
authentication. Interactive sign-in is **not required**.

The initial probe inside this chat's filesystem/process sandbox failed to
initialize its in-process app-server with EPERM. Repeating it with host execution
permissions and the installed environment succeeded. That diagnostic sandbox
restriction was separate from the launcher's actual parser defect.

Only numeric quota metadata and sanitized error categories were exposed. No
credential files or private conversation contents were displayed or copied.
The official [rate-limit protocol](https://learn.chatgpt.com/docs/app-server#6-rate-limits-chatgpt)
describes account-provided window durations and an optional secondary window;
primary is not guaranteed to represent five hours.

## Installed environment

- Checkout: `/Users/andrey/radarr-festival-list-worker`.
- LaunchAgent: `/Users/andrey/Library/LaunchAgents/com.kolorifer.github-codex-worker.plist`.
- Invocation: `/usr/bin/python3 automation/github_worker.py --repo /Users/andrey/radarr-festival-list-worker --once`.
- Python: `/usr/bin/python3`, version 3.9.6; standard-library launcher, no runtime virtual environment.
- Codex: `/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex`, version `0.164.0-alpha.11.1`.
- GitHub CLI: `/usr/local/bin/gh`; Git: `/usr/bin/git`.
- Agent HOME: `/Users/andrey`; its PATH resolves the executables above.
- Cadence: 60 seconds. Agent definition, environment and cadence were not changed.

## Changes

| Component | Change |
| --- | --- |
| `automation/github_worker.py` | Validate the newest Codex quota snapshot; accept account-provided positive window lengths; use the lowest remaining percentage across primary/secondary. Reject malformed, stale and expired data. Remove the unsupported authentication diagnosis and five-hour-specific pause wording. |
| `test_github_worker.py` | Six regression tests covering weekly quotas, both window orders, invalid newest data, invalid secondary, unrelated metered buckets, threshold and duplicate execution. |
| `automation/README.md` | Describe variable quota windows and fail-closed selection. |
| Project state and archived brief/report | Record the local diagnosis, repair and evidence. |

The exact `remaining <= 15` gate is unchanged. Five-hour maximum observation age,
future timestamp tolerance, probe isolation, 30-minute cooldown, lock handling,
local reservation-before-claim, create-only remote claims and duplicate suppression
remain in place. No Radarr, scoring, Telegram or seedbox service/code was changed.
The unrelated `docs/CODEX_TASK.md` assignment was preserved and not executed.

## Verification

- Original installed isolated probe: exit 0, while the old parser still refused
  its fresh weekly telemetry. Initial observation: 13% used / 87% remaining.
- Installed repaired `Runner.refresh_quota()`: succeeded, **86% remaining** at
  final live check. It naturally cleared only `quota-refresh.json`, as designed
  when trustworthy current telemetry exists.
- Issue #86 task 1: original owner task still selected by read-only preview;
  existing local consumed list empty; remote claim-ref count zero before repair.
  No task was recreated, no claim reset and no research worker was started by
  this repair. Clean-checkout preview is repeated after the local repair commit.
- State-file SHA256 and inode unchanged. Both dispatcher and issue lock SHA256
  values and inodes unchanged. Issue #86 directory contents unchanged.
- The existing dispatcher lock was held during diagnostics/install, without
  truncating or replacing its file, to exclude automatic execution during repair.
- Synthetic weekly quota lifecycle: 87% and 16% remaining launch once over two
  polls; 15% and 0% launch zero times and remain unconsumed.
- Focused launcher/policy/communication suite: **110 tests passed**; final quota
  regression suite (including the additional lifecycle case): **16 passed**.
- Full final suite in isolated Python 3.9.6 virtual environment:
  `python -m unittest -v`: **322 tests passed, no skips**, 109.001 seconds.
- First full run had 10 EPERM errors from sandbox-denied localhost HTTP fixtures.
  The host-permission rerun above passed all 322; no production endpoints used.
- `python -m pip check`: no broken requirements. Dependencies were installed only
  in the temporary test environment, not into the launcher or production runtime.
- Source installation hashes matched the tested files; `git diff --check` passed.

## Deployment and limitations

The tested files are installed directly into the dedicated local launcher and
recorded in a local commit so its dirty-checkout protection remains satisfied.
No remote push, PR, service deployment, task publication or claim operation is
part of this repair. The existing scheduler resumes after the temporary diagnostic
lock is released. Existing task #86 can then proceed through the unchanged
reservation and atomic-claim sequence at most once. Its research execution and
completion are separate from this launcher verification and are not claimed here.

The containing local Git commit records the repair. To roll back the code, revert
that commit in the dedicated checkout while excluding concurrent launcher work;
never restore/reset task journals or delete claim refs. The parser still depends
on the local Codex token-count telemetry format; missing or unusable data continues
to fail closed.
