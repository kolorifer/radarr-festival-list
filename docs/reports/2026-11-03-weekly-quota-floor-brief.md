# Dispatcher weekly quota floor — brief

The owner requested changing the dispatcher's verified weekly Codex quota floor
from 15% to 5%. Keep each other window's existing 15% floor and fail closed on
missing, stale, expired or malformed quota. Apply all windows independently;
do not infer a duration from its position or collapse values before the guard.
Preserve claims, locks, quota probes, schedules and investigator policy.
