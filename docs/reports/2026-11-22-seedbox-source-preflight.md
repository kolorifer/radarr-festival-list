# Installed source preflight

The pinned worker bootstrap accepts a local diagnostic mode.

```text
PYTHON -I -B CODE/automation/seedbox_bootstrap.py CODE/seedbox-runtime.json MANIFEST_SHA source-preflight CONFIG_PATH CONFIG_SHA
```

Use the installed interpreter, manifest and selected configuration for the
worker being diagnosed. The command exits zero on local success and one on
refusal. It emits one JSON record with a finite stage and reason. It checks
the package and configuration pins, private state and selected actor guards,
static source dependencies and readable CA bundle, then the selected source
configuration and cookie inputs under Landlock.

This mode applies the existing selected-path confinement with file writes and
TCP connections denied. It does not open SQLite or read the queue, call any
external source, decrypt provider credentials or change the source circuit.
A pass establishes only that the local inputs and dependencies passed at
inspection time. External source authentication and full source access remain
unverified. The diagnostic cannot determine the cause of an earlier failure.

The ordinary acquisition path shares the local input checks and keeps its
existing outcomes and request behavior. The diagnostic output includes no
credential values, paths, exception messages or private case details.
