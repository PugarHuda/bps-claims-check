# Claude subagent runs: raw outputs and exact instructions

Claude Sonnet 5.5 and Haiku 5.5 were run as fresh Claude Code subagents, not through the API. This folder keeps the
raw outputs and the exact instructions so the runs can be inspected and repeated.

- `batch_prompt.txt`: the extraction instructions. They are identical to `pipeline.BATCH_PROMPT`, which every
  other model received.
- `agent_{sonnet,haiku}.jsonl`: raw answers on `data/claims_raw.csv`, 166 items.
- `hard_{sonnet,haiku}.jsonl`: raw answers on `data/perturbed_hard_claims.csv`, 39 items.

**Task instruction given to each subagent:**

- Read only `batch_prompt.txt` and the claims CSV.
- Open no other project file (results/, gold or silver sheets, BPS tables, src/).
- Judge every item yourself, without scripts, regexes or API calls.
- Keep `value` as the string exactly as stated.
- Write one JSON line per item, in file order.

**How outputs were normalised:** with `pipeline.clean()`, then verdicts were recomputed by `pipeline.verdict()`.
The results are in `results/extract_anthropic__claude-*__agent.jsonl` and
`results/perturb_hard/extract_anthropic__claude-*__agent.jsonl`.

**Caveats:**
- Decoding parameters are not controlled, so repeated runs can differ.
- The reference annotator (Claude Opus) is from the same model family.
