# Dispatcher weekly quota floor — engineering report

The dispatcher retains each validated quota window's position, duration and
remaining percentage through direct and post-probe reads. It blocks when any
window reaches its own floor: 5% for exactly 10,080 minutes and 15% otherwise.
The pause notification identifies a blocking window and its floor. Invalid or
stale latest telemetry still invokes the existing bounded quota-refresh path;
an unavailable refresh never reserves a task.

Synthetic tests exercise threshold boundaries, both positions, mixed windows,
claim/restart behavior, malformed other windows and existing probe safeguards.
This code does not modify the separate investigator's quota rules. The parent
owns exact-head independent review, CI and selective launcher installation.
