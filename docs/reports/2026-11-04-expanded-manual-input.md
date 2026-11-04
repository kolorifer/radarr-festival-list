# Engineering report: expanded historical manual input

**Result:** Offline input-loss correction, with live routes unchanged.
**Specification:** [completed brief](2026-11-04-expanded-manual-input-brief.md).

## Behavior

The previous manual adapter discarded useful retained catalogue and source
observations. The new historical_retained_case envelope is privately parsed into
an expanded typed packet. build_request, used by the existing rehearsal, adds
those fields to the actual model input. This is an offline request template;
no model or provider was invoked and no simulated answer is a new identification.

The allowlist preserves selected find, movie-search and details observations,
exact candidate IDs, titles, director/cast, dates, runtime, clocks and conflicts.
Description year and duration are parsed into typed values; description cast is
accepted only as exact names in the selected structured catalogue. Other tail
text stays private and is marked unparsed. NFO durations retain container, video,
audio and subtitle labels rather than collapsing them into competing film lengths.
The request records expired/future/unknown observation status, occurrence and
export clocks, source dependence, partial/truncated evidence, unknown currentness
and approvals, and explicit missing/omitted fields. Hashes establish correspondence,
not provider authenticity. The operator separately verified the retained source.

No raw NFO, description prose, image URL, case/version hash or private path enters
the expanded request. Existing privacy string checks and bounded arrays apply.
Legacy packets keep their 16 KiB limit and explicit incomplete-evidence label;
the new single-case envelope is capped at 64 KiB, retained case at 48 KiB and
expanded packet at 16 KiB. Existing private path, ACL, inode and exclusive-output
checks remain. Source/provider/network calls and all real activation remain refused.

## Validation

Focused tests cover source envelope -> parser -> actual request with independently
specified expected values; 105-minute audiovisual versus 104-minute subtitle
streams; catalogue crosswalk, director/cast, observation/expiry and partial facts;
missing fields; bad hashes/bindings; private text and cast-tail exclusion; duplicate
methods; size limits; future clocks; legacy incompleteness; and actual rehearsal
request capture to the fixture-only transport. The constructed request is retained
in the private report, with its SHA-256, and independently compared with the
selected original retained case. Supported exact-head CI is required before merge.

## Scope and limits

Only manual_offline.py and focused tests change executable behavior. This optional
offline module is not in the installed production runtime closure. No production
manifest, admission fence, disclosure.project default or live transport changes.
The output validator still refuses unsupported current candidates: an expired
historical proposal is not converted to current authenticated evidence. Supervised
chat assessments remain separately labeled and are not simulated transport output.

The containing PR/commit supplies review and CI references. The unrelated current
task and historical project-state document remain unchanged; this sanitized report
records this correction. No deployment, worker, claim or API-credit assumption.
