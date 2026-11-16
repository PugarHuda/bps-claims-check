# Do Their Numbers Match? Checking Indonesian Statistical Claims Against Official BPS Data with LLM Extraction and Deterministic Verdicts

*AI × Epistemics Research Sprint (Apart Research), November 2026. Draft.*

Each `[[...]]` marker is a number that `src/metrics.py` or `src/figures.py` will produce once the human gold labels are in. None of them is estimated here. Every number that appears without a marker comes from `results/pregold_metrics.md`, `results/perturb_metrics.md` or `results/run_log.txt`.

## Abstract

Indonesian officials, ministries and journalists routinely quote headline statistics (inflation, open unemployment, poverty, economic growth) and attribute them to Statistics Indonesia (BPS). We ask three questions about these claims:
1. What fraction can be automatically bound to an official BPS figure?
2. Among those, what fraction disagree with it?
3. How accurately do LLMs do the binding, compared with human labels?

**Data.** We collected 166 candidate claim sentences from 41 Indonesian articles: ministry press releases and national news. We built an evidence table of 104 first-release BPS figures for four national indicators, 2022–2026. Every row carries its *Berita Resmi Statistik* (BRS) URL and was checked against the release in a browser. A second table holds 83 *variant* figures from the same releases: month-on-month and year-to-date inflation, quarter-on-quarter and cumulative growth.

**Method.** The LLM only *extracts* (indicator, period, stated value). Lookup and verdict are deterministic and precision-aware. A claim MATCHes when the official value, rounded half-up to the precision the claim states, equals it.

**Evaluation.** We compare free LLMs and two rule baselines against single-annotator gold labels. Headline results: bindable rate `[[bindable + CI]]`, mismatch rate `[[mismatch + CI]]`, best macro-F1 `[[best F1 + CI]]`.

**Findings.**
- Many apparent mismatches are not wrong numbers. They are **right numbers in the wrong frame**: before gold, 5 of the 8 mismatches flagged by the largest model are exactly the official month-on-month figure.
- On 105 synthetic sentences with known answers, every system, including LLMs judging with the table in their prompt, scores 100%. The difficulty is in real sentences, not in the arithmetic.
- Verdicts export as schema.org ClaimReview (88/88 valid), with a third rating for misframed numbers.

## 1. Introduction

Statistical claims are unusually checkable. For "inflation in October was 1.71 percent" there is exactly one authoritative number, published on a known date. In practice, though, checking is slow, because the checker must decide three things:
- **which statistic** is meant: year-on-year or month-on-month? headline or core? national or provincial?
- **which period**: often implied only by the article date;
- **how much rounding** to tolerate.

Indonesia is a useful test case for three reasons:
- **Attribution.** Government communication cites BPS constantly.
- **Structured truth.** BPS publishes every headline figure in a BRS release with a stable URL and date, so verification can use a small, auditable table instead of open-web retrieval.
- **Language.** Existing numerical fact-checking benchmarks are English.

**Research question (fixed before data collection).** Of quantitative claims by Indonesian officials and institutions that cite BPS data:
1. What fraction can be automatically bound to an official BPS figure?
2. What fraction of those mismatch?
3. How accurately do LLMs do the binding, relative to human labels and a rule baseline?

**Design principle.** LLMs are used only where language understanding is needed. The verdict is computed by a rule a fact-checker can trace to one table row and one rounding comparison. A model can misread a sentence, but it cannot decide that a number is wrong.

**Contributions.**
1. **An Indonesian dataset**:
   - 166 candidate sentences with URLs and dates;
   - a 104-row first-release BPS table and an 83-row variant table, each row with provenance or quoted evidence;
   - human gold labels.
2. **A precision-aware verdict rule**, with tests.
3. **An evaluation that reports false accusations separately.** It also includes bootstrap CIs, an error taxonomy, κ, and a "right number, wrong frame" analysis.
4. **Two stress tests**: an LLM-as-judge ablation and a synthetic perturbation benchmark.
5. **An adoption path**:
   - ClaimReview export with a misframing rating;
   - a monthly job that keeps the evidence table current through reviewed pull requests.

## 2. Related Work

- **QuanTemp** (arXiv:2403.17169) is a real-world, open-domain benchmark of numerical claims with web evidence.
- **NUMTEMP** is a multi-domain numerical benchmark. Its best baseline reaches a macro-F1 of about 58.
- **CLEF CheckThat! 2025 Task 3** builds on QuanTemp (True/False/Conflicting against BM25-retrieved evidence). ClaimIQ (arXiv:2509.11492) compares prompted and fine-tuned LLMs on it.

All three are English, retrieve prose evidence, and have the model produce the verdict.

- **ClaimReview** (schema.org) is the markup fact-checkers embed. Google Search and Fact Check Explorer read it.
- **cekfakta.com**, launched in 2018 by 22 Indonesian outlets with Mafindo, is the country's collaborative fact-checking effort.
- AJI Indonesia publishes ClaimReview guidance for newsrooms.

**Our gap:**
- Indonesian language.
- A small, versioned, structured evidence table from a national statistics office.
- A deterministic, precision-aware verdict, so every error is attributable to extraction, to the table, or to the rule.
- Output in the format fact-checkers already publish.

## 3. Data

### 3.1 Claims

We searched for Indonesian articles and press releases stating values of the four indicators, combining indicator names with attributions such as "menurut BPS". This gave 55 URLs (`data/urls.txt`). We fetched them with `trafilatura`. Pages that block scripted clients (ekon.go.id) were saved with a real browser.

A recall-oriented filter kept sentences that mention an indicator and a percentage. The result is **166 sentences from 41 articles**: 25 from government (go.id) releases, the rest from national media.

**Article dates.** trafilatura found no date for any of the 25 ekon.go.id sentences. We read each release's dateline in a browser ("Jakarta, 31 Januari 2025") and recorded the source in `data/article_dates.csv`. This is a selection-relevant fix: without dates, relative periods in government releases could not be resolved.

**Duplicates.** Two sentences appear twice and are counted once.

**Selection bias.** Searching for BPS attributions over-represents claims that *quote* BPS. Our mismatch rate therefore estimates the rate for attributed claims, not for government statements in general. Each gold sentence records a `speaker_type`. We also stratify by source (go.id vs media) and by whether the sentence names BPS: `[[per-stratum tables]]`.

### 3.2 Evidence tables

**`data/bps_reference.csv`: 104 rows**, national, first-release values.

| Indicator | Coverage |
|---|---|
| `inflation_yoy` | 61 rows, monthly 2022-01 to 2026-10, plus annual = December |
| `gdp_growth_yoy` | 23 rows, quarterly 2022-Q1 to 2026-Q3, plus annual |
| `unemployment_rate` | 12 rows, TPT survey months |
| `poverty_rate` | 8 rows, March/September |

Provenance of the rows:

| Provenance | Rows |
|---|---|
| value read on the BRS page | 68 |
| BPS listing title, which states the value | 31 |
| annual = December | 4 |
| search-result title only | 1 |

An independent pass re-opened 12 rows: the five most-referenced periods plus seven random ones. **All 12 values appear on their BRS page in the right frame.** For example, "triwulan III-2024 terhadap triwulan III-2023 tumbuh sebesar 4,95 persen (y-on-y)" is the y-on-y figure, not the 1.50 q-to-q figure in that page's title.

**Known gaps:**
- inflation 2024-08: the page would not load;
- poverty 2023-09: no release found;
- inflation 2024-12 / annual 2024: the stored BRS link returns 404, and the value rests on a search-result title.

**`data/bps_variants.csv`: 83 rows**, read from the same BRS pages for 2024-01 to 2026-10. Each row stores the quoted evidence sentence, and every value appears verbatim in it.

| Variant | Rows |
|---|---|
| inflation month-on-month | 32 |
| inflation year-to-date | 32 |
| GDP q-to-q | 11 |
| GDP c-to-c | 8 |

### 3.3 Gold labels

One annotator (an author, native Indonesian speaker) labels each sentence in `tools/label.html`:
- up to three in-scope (indicator, period, value-as-stated) tuples;
- the speaker type.

Only rows marked `checked` count. To avoid anchoring the annotator:
- the sheet is pre-filled only from the naive regex baseline, never an evaluated LLM;
- the tool can order sentences by how many distinct answers the systems gave, showing the count but not the answers.

The tool was tested end-to-end in a browser (17 scripted checks plus resume). The exported CSV round-trips into `metrics.py` with stated precision intact.

Coverage: `[[n checked / n tuples]]`.

**Silver labels (LLM, not human).** No second human annotator was available. A fresh Claude Opus subagent annotated all 166 sentences blind (`data/silver_sheet.csv`):
- it followed written guidelines;
- it saw no system output and no human label;
- it produced 97 tuples, 1 flagged frame-ambiguous.

We use silver labels in two ways:
1. a **provisional full-coverage** report (`results/silver_metrics.md`);
2. a **human-vs-LLM-annotator κ** on the human-checked subset `[[κ]]`, which measures how far LLM labels can stand in for human ones on this task.

Silver labels are not treated as gold anywhere. Because the silver annotator is a Claude model, any comparison against silver favours the Claude systems (§5.2).

## 4. Method

### 4.1 Pipeline and verdict rule

```
sentence (+ preceding sentence, article date)
  → [1] extraction: LLM or rules → [{indicator, period, value-as-stated}]
  → [2] lookup (indicator, period) in bps_reference.csv
  → [3] verdict: MATCH | MISMATCH | UNVERIFIABLE
```

**Extraction scope.** The prompt keeps only national, *realised* figures. It excludes:
- month-on-month, year-to-date (except December), core, component or regional inflation;
- counts of people, urban/rural splits and extreme poverty;
- q-to-q, c-to-c and sectoral growth;
- targets, forecasts, ranges and other countries' figures.

Relative periods are resolved from the article date. The period is `null` if it cannot be determined.

**Verdict.** The claim is UNVERIFIABLE if the period is null or the row is absent. Otherwise it is a MATCH iff `round_half_up(official, d) == stated`, where *d* is the number of decimals the claim states.

Two bugs in a naive implementation were caught by our tests:
- float `round(5.05, 1) = 5.0` would mark a correct "5,1 persen" as wrong;
- parsing JSON numbers erases stated precision ("5,0" → 5).

We use `Decimal` and keep the stated text.

### 4.2 Systems

| System | Description |
|---|---|
| `regex` | naive: keyword → indicator, first "N persen", explicit date → period. Also pre-fills the gold sheet. |
| `rules` | stronger, written from the scope definition only. Handles clauses, out-of-scope cues (m-to-m, y-to-d, q-to-q, core, regional incl. place names, targets incl. Indonesian affixed forms such as *menargetkan*), and relative periods. Unit-tested. |
| Nemotron-3 Ultra 550B-A55B | open-weight, free endpoint |
| ERNIE 5.5 Flash (preview) | free endpoint |
| LFM-3 1.7B | open-weight small reasoning model, free endpoint |
| Claude Sonnet 5.5, Claude Haiku 5.5 | frontier models, run as **fresh, isolated Claude Code subagents** (details below) |

**Claude subagent runs.** Each subagent:
- saw only the identical extraction instructions and `claims_raw.csv`;
- was told not to open model outputs, labels or evidence tables;
- labelled every sentence itself, without scripts or API calls.

This is not an API run at temperature 0, so it is less reproducible. We report it as such.

All LLMs run at temperature 0 on free endpoints, which allow 50 requests per day. To fit the quota:
- sentences are batched (20 per request; 8 for LFM);
- items missing from a reply are retried, not scored.

Gemma 4 31B was rate-limited (HTTP 429) and was not run, because the quota went to the ablation and stress tests below.

### 4.3 LLM-as-judge ablation (e2e)

Nemotron and ERNIE receive the full 104-row table in the prompt and return the verdict themselves under the same written rule. Metrics score their own verdicts. ERNIE's e2e run covers 126/166 sentences: two batches ended at the output limit (`finish_reason=length`) because the table plus 20 sentences is long.

### 4.4 Stress tests

**Synthetic perturbations** (`src/perturb.py`). From 16 official figures (stratified by indicator) we generate **105** Indonesian sentences with known verdicts:

| Variant of the official figure | Expected verdict |
|---|---|
| exact | MATCH |
| rounded to 1 decimal | MATCH |
| truncated where truncation ≠ rounding | MISMATCH |
| last digit +1 | MISMATCH |
| off by 0.5 | MISMATCH |
| attributed to another period with a different value | MISMATCH |
| period before table coverage | UNVERIFIABLE |

Two phrasings per indicator are used.

**Batch size.** Ten real sentences were re-run one per request with ERNIE.

### 4.5 Right number, wrong frame

A tuple that MISMATCHes its headline statistic is checked against the variant table for the same release. If it equals a variant under the same rounding rule, it is reported as **misframed** rather than wrong. ClaimReview carries this as a third rating, "Angka benar, konteks keliru" (value 3 of 5).

### 4.6 Metrics

**Alignment unit:** (sentence, indicator, stated value). The period is left out of the key, so a wrong period appears as a verdict disagreement.

| Metric | What it reports |
|---|---|
| Headline | bindable rate; mismatch rate among bindable; per indicator and per stratum |
| Per system | extraction P/R/F1; verdict accuracy; macro-F1 over MATCH/MISMATCH/UNVERIFIABLE, with NONE as a fourth confusion label |
| **False MISMATCH** | the system says MISMATCH and gold does not, i.e. a false accusation |
| Missed MISMATCH | the reverse |
| κ | system–system (no gold needed) and annotator–annotator |
| CIs | 95% bootstrap over sentences (2,000 resamples), paired for system scores |
| Error taxonomy | one cause per disagreement, from tuple comparison and cues near the number (see list below) |

Error-taxonomy causes:
- frame confusions: m-to-m, y-to-d, q-to-q/c-to-c;
- scope errors: core/component, regional, target/projection;
- tuple errors: wrong period, wrong value, missed claim.

## 5. Results

### 5.1 How many claims can be checked, and how many are wrong?

`[[headline: bindable rate, mismatch rate, unverifiable — with 95% CI]]` · `[[fig: figs/verdict_by_indicator.png]]` · `[[tables by speaker type, source, BPS attribution]]` · `[[gold MISMATCH split: misframed (by variant) vs wrong number]]`

### 5.2 How accurate are the systems?

`[[table: per system P/R/F1, verdict acc, macro-F1 (CI), false/missed MISMATCH]]` · `[[fig: figs/confusion.png]]` · `[[error taxonomy table]]`

**Provisional, against silver labels** (`results/silver_metrics.md`; 164 sentences, 94 tuples):

*Headline:*
- Bindable rate: 87/94 = 92.6%, 95% CI [86.9, 97.6].
- Mismatch rate among bindable: 1/87 = 1.1%, 95% CI [0.0, 3.8].
- By speaker type, government officials show 0/39 mismatches.

*Systems:*

| System | Extract F1 | Verdict acc | False MISMATCH |
|---|---|---|---|
| Claude Sonnet 5.5 (agent) | 0.99 | 0.99 | 0 |
| Claude Haiku 5.5 (agent) | 0.99 | 0.96 | 0 |
| ERNIE 5.5 Flash | 0.96 | 0.84 | 0 |
| Nemotron-3 Ultra | 0.96 | 0.83 | **7** |
| Nemotron · e2e judge | 0.98 | 0.89 | 0 |
| `rules` | 0.63 | 0.31 | **54** |
| `regex` | 0.54 | 0.29 | **31** |

*Caveats:*
- **Claude's near-perfect scores here are an upper bound.** The silver annotator is itself Claude. `[[human gold decides]]`.
- **Macro-F1 is unstable at this sample size** (silver contains one MISMATCH), so we lead with accuracy and false-MISMATCH counts.

*Two findings that hold regardless of who labels:*
- **The dominant error class is the period**, not the number: 8–16 wrong periods per LLM.
- **The hand-written rule baseline buys recall at the price of false accusations**: 54, more than the naive regex. Writing scope rules by hand does not substitute for language understanding.

**Before gold** (`results/pregold_metrics.md`; system outputs, not accuracy):

| System | Sentences | Tuples | MATCH | MISMATCH | of which = another published variant |
|---|---|---|---|---|---|
| regex (naive) | 164 | 162 | 49 | 32 | 8 (m-to-m 4, y-to-d 2, c-to-c 2) |
| Nemotron-3 Ultra | 164 | 102 | 77 | 8 | **5 (all m-to-m)** |
| Nemotron-3 Ultra · e2e judge | 164 | 93 | 80 | 1 | 0 |
| ERNIE 5.5 Flash | 164 | 95 | 77 | 1 | 0 |
| ERNIE · e2e judge | 124 | 76 | 65 | 1 | 0 |

- **Misframing is concrete.** Nemotron's m-to-m reads are 0.08 (Oct 2024), 0.28 (Oct 2025), 0.17 (Nov 2025), 0.64 (Dec 2025) and 0.30 (Nov 2024). Each equals the official m-to-m figure in that month's BRS. Two more of its mismatches come from the same sentences: 0.17 for Oct 2023, and 0.44 for Dec 2024, whose BRS page returns 404. Both fall outside the variant table, so they stay counted as wrong numbers. 5/8 is therefore a lower bound. The source sentences present them as plain "inflasi" or "realisasi inflasi", e.g. *"Pada Desember 2025, realisasi inflasi menyentuh 0,64 persen, setelah November berada pada level 0,17 persen"*. Whether a careful reader would take these as year-on-year is what gold decides `[[gold verdict for these sentences]]`.
- **The naive baseline would accuse.** It reads "inflasi tahun kalender (year-to-date) … 2,17 persen" as September year-on-year inflation and reports a mismatch with the official 3.28.
- **Agreement.** Verdict-level κ between Nemotron and ERNIE is 0.68. Between either LLM and the naive regex it is ≈0.1, and with the `rules` baseline 0.21–0.28 (`figs/agreement_kappa.png`).
- **LFM-3 1.7B** returned output for only 38/166 sentences. Other batches ended with empty content and `finish_reason=length`, even with low reasoning effort and 8 sentences per request.

### 5.3 Does a deterministic verdict beat an LLM judge?

**On synthetic sentences, no difference: every system scores 100%.** We tested five systems on all 105 sentences and all seven perturbation types, including the subtle "truncated vs rounded" case:
- the deterministic rule given the true tuple;
- `rules` extraction;
- ERNIE extraction;
- the ERNIE e2e judge;
- the Nemotron e2e judge.

There are 0 false accusations and 0 missed errors. The arithmetic of matching a stated figure to a table is not where systems fail.

**On real sentences, the judge changes the answers.** Nemotron as e2e judge reports 1 MISMATCH where its own extractions, under the deterministic rule, gave 8. Its verdict κ with its own pipeline is 0.68, versus 0.90 for ERNIE. With the answer key in the prompt, the model stops reading month-on-month figures as year-on-year. That would reduce false accusations if those reads were wrong, but it would also *hide* real mismatches if a speaker had actually misstated a number. `[[gold: false vs missed MISMATCH, pipeline vs e2e]]` decides which.

The deterministic design keeps the extraction visible either way.

### 5.4 Robustness checks

- **Article dates.** Re-running Nemotron and ERNIE on the 25 government sentences with recovered dates gave identical verdicts to the runs without dates (10 MATCH + 1 UNVERIFIABLE per model). Those sentences state their periods explicitly.
- **Batching.** For 10 sentences re-run one per request, ERNIE's extracted tuples were identical to the batched run: 10/10, κ = 1.0. The sample is small. It rules out a large batching effect for ERNIE, not a small one.
- **Batching leaks values across items.** We checked every extracted value against its own sentence and the preceding one. Number words count, e.g. "dua persen".
  - **ERNIE attached 2 of its 95 values to sentences that do not contain them.** Both appear verbatim in *neighbouring sentences of the same 20-item batch*:
    - 5.61 comes from c0072, the item directly before.
    - 5.47 comes from c0076–c0078.
  - No other system has such values: Nemotron, Claude agents, rules and regex all have 0.

  The 10-sentence batch-size test did not catch this. A grounding check did.

  This is also the mechanism by which untrusted scraped text could forge another item's answer. The pipeline therefore strips item markers from scraped text and flags every ungrounded value (`grounded: false`) instead of trusting it.

## 6. Discussion

**For fact-checkers:**
1. Ask "which statistic?" before "is the number right?". In our data the clearest source of apparent error is frame: month-on-month or year-to-date figures written as "inflation".
2. A naive pattern matcher is not a safe filter. Most of its MISMATCHes are not wrong numbers, and each one would be a public accusation.
3. Model agreement is not accuracy. Only gold and the false-MISMATCH count show whether a system can be trusted.

**Adoption.** `src/claimreview.py` writes ClaimReview JSON-LD and an HTML review page (`docs/claimreview.html`, servable by GitHub Pages) in which every item's `url` anchors to its card:
- all 88 items from a test export pass validator.schema.org with zero errors;
- the page was checked in a browser (anchors resolve, no horizontal scroll at 375 px);
- a "misframed" verdict becomes a distinct rating, so a newsroom does not have to publish a right number as "false".

The export defaults to gold verdicts and skips UNVERIFIABLE.

**A maintained evaluation.** BPS releases on a fixed calendar. `src/update_bps.py` reads the newest BRS titles with a headless browser (the listing is rendered client-side) and appends new headline figures. It never overwrites a stored value, under the first-release policy, and it flags differences as possible revisions. A monthly GitHub Action runs it with the tests and opens a **pull request**, so a person confirms every new number.

On 16 Nov 2026 a live run parsed the three newest headline releases and found all three already in the table with identical values:

| Indicator | Period | Value |
|---|---|---|
| TPT | Aug 2026 | 4.75 |
| GDP growth | 2026-Q3 | 5.47 |
| inflation | Oct 2026 | 3.23 |

Verdicts are recomputed from the current table, so stored extractions are re-scored without re-running models.

**What did not work:**
- LFM-3 1.7B could not complete the task.
- Gemma 4 was rate-limited.
- The ERNIE e2e run hit the output limit on two batches.
- Batching was forced by the free quota.

## 7. Limitations

- **Single human annotator.** The second annotator is an LLM (Claude Opus, blind), which is reported as such and never used as gold. Comparisons against silver favour the Claude systems.
- **Claude systems ran as Claude Code subagents**, not through an API with fixed decoding parameters, so they are less reproducible than the OpenRouter runs.
- **Selection bias** toward BPS-attributed claims. Speeches, debates and social media are out of sample.
- **Small n**: 166 sentences, `[[n]]` gold tuples. CIs are reported.
- **Models:** free endpoints only, no frontier closed model, batched prompting.
- **Coverage:** partial for LFM (38/166) and ERNIE e2e (126/166); systems are scored on what they processed.
- **Evidence:** first-release only; three periods missing or weakly sourced; national level; four indicators.
- **Variants:** 2024-01 onward only. A misframed claim about an earlier period is counted as a wrong number.
- **Strict rule:** one unit off in the last stated decimal is a MISMATCH.
- **Synthetic benchmark:** fluent, single-figure sentences. It tests the verdict step, not the ambiguity of real text.

## References

- QuanTemp: a real-world open-domain benchmark for fact-checking numerical claims. arXiv:2403.17169 (2024).
- NUMTEMP: a real-world benchmark to verify claims with statistical and temporal expressions.
- ClaimIQ at CheckThat! 2025: comparing prompted and fine-tuned language models for verifying numerical claims. arXiv:2509.11492 (2025).
- Google Search Central. Fact check (ClaimReview) structured data.
- schema.org. ClaimReview.
- Google News Initiative. CekFakta: collaborative fact-checking in Indonesia (2018).
- AJI Indonesia. ClaimReview: panduan media untuk kredibilitas informasi (2025).
- Badan Pusat Statistik. Berita Resmi Statistik, bps.go.id (accessed November 2026).

## Appendix A. Dual-use and ethical considerations

**False accusation is the main harm.** A MISMATCH attached to a named official is an accusation of error, and automated systems produce such verdicts wrongly. In our data the naive baseline flags 32 mismatches, of which 8 are exactly another published variant. We therefore:
- report false MISMATCH separately;
- default the ClaimReview export to human-verified verdicts;
- give misframed numbers their own rating;
- recommend that no automated verdict be published without a person checking the extracted tuple and the BRS row.

A MISMATCH means the stated number differs from the first-release figure for the statistic we inferred. It does not mean the speaker lied.

**Misuse as a "verified" stamp.** "Sesuai data BPS" could be applied selectively to favourable claims, or lend a true number's credibility to a misleading frame. The misframing rating keeps the second case visible. Publishing the full claim set and all verdicts addresses the first.

**An LLM judge with the answer key can rationalise.** In our ablation the judge's verdicts drifted toward agreement with the table (§5.3). A system that quietly "corrects" a speaker's frame can hide real misstatements. This is a reason to keep extraction and judgment separate in fact-checking tools.

**Dependence on the official source.** BPS is ground truth only for "does the claim match the official figure". This is not a judgement on BPS methodology.

**Data and privacy.**
- Public statements by public officials and institutions, stored as short quotations with URLs.
- No private individuals.
- Article text cached locally for extraction only.
- No personal data in model prompts.
