# Do their numbers match? Indonesian statistical claims vs official BPS data

Apart Research **AI × Epistemics** sprint, November 2026.

We take sentences in which Indonesian officials, ministries or news media state a headline statistic: inflation,
open unemployment (TPT), poverty rate, or GDP growth. Each one is checked against the official first-release figure
from Statistics Indonesia (BPS).

An LLM only **extracts** `(indicator, period, value)` from the sentence. The **verdict** comes from a deterministic
lookup in a versioned evidence table with a precision-aware rounding rule, so every verdict can be audited and none
can be hallucinated.

Report draft: [`docs/REPORT_DRAFT.md`](docs/REPORT_DRAFT.md). Fact-check page (schema.org ClaimReview): [`docs/claimreview.html`](docs/claimreview.html).

## What is in here

| Path | What it is |
|---|---|
| `data/claims_raw.csv` | 166 candidate claim sentences from 41 articles (URL, article date, preceding sentence) |
| `data/article_dates.csv` | dates recovered by hand for pages without machine-readable dates (with provenance) |
| `data/bps_reference.csv` | evidence table: 104 first-release BPS figures, 2022–2026, each with its BRS URL and a `provenance` tag |
| `data/bps_variants.csv` | 83 *other* figures from the same releases (m-to-m and y-to-d inflation, q-to-q and c-to-c growth), each with the quoted evidence sentence. Used to detect "right number, wrong frame" |
| `data/gold_sheet.csv` | human labels; only rows with `checked` = x count |
| `data/silver_sheet.csv` | blind **LLM** annotation (Claude Opus subagent) of all 166 sentences: provisional coverage + human-vs-LLM κ, never used as gold |
| `data/perturbed_claims.csv`, `data/perturbed_expected.csv` | synthetic benchmark: 105 sentences with known verdicts |
| `src/pipeline.py` | extraction (LLM batched/per-sentence, `regex` naive baseline, `rules` stronger baseline) → lookup → verdict |
| `src/metrics.py` | scores against gold (see Metrics below); with no gold yet, writes a no-gold report |
| `src/perturb.py` | builds and scores the synthetic perturbation benchmark |
| `src/claimreview.py` | exports ClaimReview JSON-LD and the HTML review page |
| `src/update_bps.py` + `.github/workflows/update-bps.yml` | monthly job that reads new BRS releases and opens a PR to append them |
| `src/figures.py` | figures → `figs/` |
| `tools/label.html` | labelling tool (open in a browser, no install) |
| `tests/test_pipeline.py` | 12 plain-assert tests: verdict rule, parsers, metrics, perturbation oracle, data integrity |

**Metrics reported by `src/metrics.py`:**
- bindable and mismatch rates with bootstrap CIs, broken down by indicator, speaker and source;
- extraction P/R/F1 and verdict accuracy and macro-F1 per system;
- false MISMATCH (false accusations) and missed MISMATCH;
- error taxonomy and κ.

## Reproduce

```bash
uv sync
export OPENROUTER_API_KEY=...            # free tier is enough (50 requests/day)
uv run python tests/test_pipeline.py     # 12 tests, offline

# extraction (resumable: already-done claims are skipped)
uv run python src/pipeline.py --model regex
uv run python src/pipeline.py --model rules
uv run python src/pipeline.py --model nvidia/nemotron-3-ultra-550b-a55b:free --batch 20
uv run python src/pipeline.py --model baidu/ernie-5.5-flash-preview:free --batch 20
uv run python src/pipeline.py --model baidu/ernie-5.5-flash-preview:free --batch 20 --e2e   # LLM-as-judge ablation
uv run python src/pipeline.py --model gemini/gemini-flash-latest --batch 20             # GEMINI_API_KEY in env or .env (free tier)

# synthetic perturbation benchmark
uv run python src/perturb.py make
uv run python src/pipeline.py --claims data/perturbed_claims.csv --out-dir results/perturb --model rules
uv run python src/perturb.py score

# labels -> metrics -> figures -> ClaimReview
#   open tools/label.html, load data/gold_sheet.csv, label, download, replace data/gold_sheet.csv
uv run python src/metrics.py             # human gold (falls back to a no-gold report)
uv run python src/metrics.py --silver    # provisional, against the LLM annotator
uv run python src/figures.py
uv run python src/claimreview.py --source gold --review-url https://<user>.github.io/<repo>/claimreview.html

# keep the evidence table current (also runs monthly in GitHub Actions)
uv run playwright install chromium
uv run python src/update_bps.py --dry-run
```

## The verdict rule

`UNVERIFIABLE` if the period is unknown or `(indicator, period)` is not in the table. Otherwise the claim is a
`MATCH` iff `round_half_up(official, d) == stated`, where `d` is the number of decimals the claim itself states.
So "5,1 persen" matches 5.05, while "5,0" and "5,12" do not.

Two bugs caught by the tests:
- Python's float `round(5.05, 1)` returns `5.0`.
- Parsing JSON numbers turns "5,0" into "5".

`ClaimReview` export adds a third rating, **"Angka benar, konteks keliru"** (right number, wrong frame). It is used
when a MISMATCHed number equals another variant from the same BPS release, e.g. a month-to-month inflation figure
presented as inflation.

## Limitations (short)

- One annotator.
- Claims were found by searching for BPS attributions (selection bias).
- Only free LLMs, batched to fit the quota.
- First-release values only; national level; four indicators.
- Coverage gaps:
  - three reference periods are missing or weakly sourced: inflation 2024-08; poverty 2023-09; inflation 2024-12, whose BRS link returns 404;
  - LFM-3 1.7B produced output for only 38/166 sentences;
  - the ERNIE e2e run covers 126/166.

See the report for detail.

## Ethics

A MISMATCH attached to a named official is an accusation. The ClaimReview export defaults to **human gold**
verdicts, and we recommend that no automated verdict be published without a person checking the extracted tuple
and the BRS row.

## License

Code MIT. Claim sentences are short quotations of public statements with source URLs. BPS figures are public
official statistics.
