# Tracker metadata deployment brief

**User instruction:** “Merge PR #42, deploy the tested version, and enable the
TorrentLeech lookup with dedicated private credentials. Verify production health
and matching without starting any downloads.”

## Required outcome

- Merge the CI-verified PR #42 and deploy verified code on the seedbox.
- Provision movie-intel's own private TorrentLeech session through normal login;
  no runtime dependence on another application's cookie database.
- Back up existing configuration and private state; preserve all unrelated
  services, credentials, pending actions, scoring and discovery settings.
- Enable lookup in the running movie-intel process, with private cookie storage.
- Verify local/public health, read-only Radarr connectivity and representative
  source-listing-to-TMDb matching. Do not replay webhook notifications, create
  approval capabilities for tests, submit approvals, run searches or download.
- Keep a verified revision pinned in production. Document actual deployed commit,
  merge references, tests, operational findings and remaining limitations.

## Verification correction

Full listing-path verification found that an HTML FREELEECH badge was treated as
part of the release heading. The narrow engineering correction ignores only the
observed `span.new.label.labelfreeleech` element whose text is exactly FREELEECH;
all release text and other markup still participate in exact matching. It is
covered by positive and negative regressions and independently validated before
deployment. This does not introduce title guessing or change acquisition policy.

The unrelated cleanup assignment in CODEX_TASK.md is outside this task and remains
untouched. Normal already-authorized production notifications continue; they are
distinct from deliberate test notifications and do not approve downloads.
