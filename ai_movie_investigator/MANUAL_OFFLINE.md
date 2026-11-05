# Manual offline diagnostic

This deliberately separate rehearsal exercises the existing disclosure projection, simulated HTTP boundary, response parser, result validator and synthetic spending history. It does not enter the pilot, construct a real event, access a provider or determine a movie identity. The built-in response is invented. Its request contains only the title, source year, asserted IMDb and reason; other packet facts remain in the local report and are not evaluated by a model.

Use an explicitly selected owner-only JSON packet matching `read_packet` and an **existing, empty, owner-only** output directory, both on a path that passes owner, mode, no-symlink and ACL checks. Paths must be absolute and canonical. The program exclusively creates `report.json` and an isolated synthetic history. It refuses reuse of an existing directory containing files. Do not put an actual investigator history there. Example:

```sh
python -m ai_movie_investigator.manual_offline --input /absolute/private/input.json --output-dir /absolute/private/empty-directory
```

The report records the packet hash, stated source hashes and facts, unknown event and decision scope, historical observation and export clocks, partial status, and the narrow reported search result. The program validates the supplied hash syntax but does **not** authenticate the underlying source artifacts: the operator must independently verify their bytes and provenance. Normalized projections are not captured event bytes. A report is private; the checks protect against unsafe permissions and accidental replacement, not a malicious process running as the same user.

A synthetic ceiling and accounting exercise existing fixture-only spending; they do not prove a real price, budget, quota or usage. Unknown simulated responses retain the synthetic reservation; no retry occurs. A fresh directory never grants permission to repeat a real acquisition or send. The `--live` option unconditionally refuses before reading an input or discovering credentials. A live route is not implemented; any future work requires independently verified explicit authority, account and project, controlled credential injection, enforceable live budget, current occurrence and decision scope, and separate review. Nothing here changes existing pilot admission or production behavior.

The filesystem integration tests require a fixture path that passes the real owner, mode and ACL guard. If the hosted runner offers none, those tests explicitly skip rather than weakening or mocking the guard; the live-refusal test still runs. Run the focused suite on a suitably private host to exercise the complete path.

## Explicit selected read handoff

For supervised prepare/complete, an operator may supply a private selector JSON
with exactly `case_id`, `version`, and `title` (the exact allowed title disclosure).
It is data, not permission to select a different real occurrence or access a new
source. The optional packaged `source_case.collect` and `source_observer.probe`
reuse the reviewed bounded SQL and reconciliation; a separately reviewed host
adapter still owns fixed source paths, read-only connections, no-create controls,
source identity checks and pinned transport. They do not discover credentials,
scan for cases or grant live access. The existing title-conflict route remains
the only supported source outcome; other routes refuse rather than falling back.

After that authorized adapter produces a completed observation, use the existing
CLI with absolute private paths:

```sh
python -m ai_movie_investigator.manual_offline --prepare --selector /absolute/private/selector.json --input /absolute/private/historical.json --companion /absolute/private/observation.json --output-dir /absolute/private/empty-directory
```

The selector, historical input and companion must agree; all three original
files are frozen and bound. Complete the same prepared directory using `--complete`,
`--reply` and `--provenance` as before. Normalized event and delivery identifiers
remain private. An observed pending absence is not delivery proof, a fresh read
does not refresh old movie evidence, and no result approves identity reuse or a
download. Runs without `--selector` retain the previous historical behavior.
