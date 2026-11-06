# Historical reasoning headroom: implementation and verification

A new `observe_incomplete_output_with_reasoning_headroom` purpose binds a
canonical private owner authorization with `max_output_tokens: 25000`. Its
predecessor must have the recorded finite output-limit refusal at parsing and
the original 4,096 allowance. Existing purposes, hashes and historical outcomes
are preserved. One-child and duplicate protections apply across purposes.

Only the selected root-locked historical grant can supply 25,000 to the operator
and credit reservation. The parser derives its limit from the actual observed
HTTP object in that session, not a caller flag or model name. Response echo,
usage, permit, receipt and local report remain correlated to the same request.
The actual generation request changes only its allowance and correlation aliases.
Synthetic and generic defaults stay at 4,096; envelope, answer size, timing,
privacy and reasoning behavior are unchanged.

At the exact Nano rates, conservative 400,000 input tokens cost $0.02 and 25,000
output tokens cost $0.01. The existing $0.03 reservation covers both exactly;
unknown, failed and successful outcomes retain the full reservation. This is a
technical upper-bound reservation, not independent billing proof.

Official documentation fetched November 6, 2026:
- [Reasoning headroom](https://developers.openai.com/api/docs/guides/reasoning#allocating-space-for-reasoning): the generation allowance includes reasoning, visible output and formatting; the initial recommendation is at least 25,000 tokens. An incomplete response can arrive without visible output.
- [Exact Nano profile](https://developers.openai.com/api/docs/models/gpt-5-nano): 400,000 context, $0.05/million input and $0.40/million output. The selected deprecated snapshot is preserved; there is no automatic model replacement.

This does not explain earlier failures or promise completion. Tests use invented
history, fake Keychain, full fake HTTP framing and an independent socket audit
tripwire. Independent review and exact supported CI are acceptance gates, with
results retained in the PR. No live operation or production deployment is part
of this repository change. Unrelated task and project documents are preserved.

Initial focused local run: six of seven tests passed, including installed success,
wrong echo, denied credential, exact request comparison and altered-authority
refusals. The incomplete test refused during fixture setup on the retained macOS
ctime guard. Two added checks passed: no-session/model-only parser widening and
installed 25,001-token usage refusal. No metadata guard was changed or bypassed.
Independent review caught a generic parser import-closure regression before
publication; the import remains conditional on an HTTP result. Expanded
predecessors are explicitly refused before allocating any further renewal.
